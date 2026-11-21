"""AssemblyAI Universal-Streaming (v3) client for Twilio audio (8 kHz mu-law).

Plain WebSocket, no SDK: binary audio frames up, JSON events down.
Docs: https://www.assemblyai.com/docs/api-reference/streaming-api/streaming-api
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Awaitable, Callable
from urllib.parse import urlencode

from websockets.asyncio.client import connect

URL = "wss://streaming.assemblyai.com/v3/ws"
CHUNK_BYTES = 800  # 100 ms of 8 kHz mu-law (1 byte/sample); docs recommend 50-100 ms chunks


class STTStream:
    """One streaming session per call.

    on_final(text, info)  - a finished caller turn (end_of_turn)
    on_speech()           - the caller started talking (used to cancel the silence timer)
    """

    def __init__(self, keyterms: list[str], on_final: Callable[[str, dict], Awaitable[None]],
                 on_speech: Callable[[], Awaitable[None]]):
        params = {
            "sample_rate": 8000,
            "encoding": "pcm_mulaw",
            "speech_model": os.environ.get("ASSEMBLYAI_MODEL", "assemblyai-stt-3-7-realtime-agent"),
            "mode": os.environ.get("ASSEMBLYAI_MODE", "balanced"),
            "keyterms_prompt": json.dumps([k for k in keyterms if len(k) <= 50][:100]),
        }
        self.url = f"{URL}?{urlencode(params)}"
        self.on_final, self.on_speech = on_final, on_speech
        self.ws = None
        self.buf = bytearray()
        self.audio_bytes = 0                  # caller audio received so far (8000 bytes = 1 s)
        self.config: dict = {}
        self._reader: asyncio.Task | None = None
        self._last_partial_order = -1

    async def start(self) -> None:
        self.ws = await connect(self.url, additional_headers={"Authorization": os.environ["ASSEMBLYAI_API_KEY"]},
                                max_size=None)
        self._reader = asyncio.create_task(self._read())

    async def send_audio(self, mulaw: bytes) -> None:
        self.audio_bytes += len(mulaw)
        self.buf += mulaw
        while len(self.buf) >= CHUNK_BYTES:
            chunk, self.buf = bytes(self.buf[:CHUNK_BYTES]), self.buf[CHUNK_BYTES:]
            await self.ws.send(chunk)

    async def _read(self) -> None:
        async for raw in self.ws:
            msg = json.loads(raw)
            t = msg.get("type")
            if t == "Begin":
                self.config = msg.get("configuration", {})
            elif t == "SpeechStarted":
                await self.on_speech()
            elif t == "Turn":
                if not msg.get("end_of_turn"):
                    if msg.get("transcript") and msg.get("turn_order") != self._last_partial_order:
                        self._last_partial_order = msg.get("turn_order")
                        await self.on_speech()
                    continue
                text = (msg.get("transcript") or "").strip()
                if not text:
                    continue
                words = msg.get("words") or []
                info = {"turn_order": msg.get("turn_order"),
                        "eot_confidence": msg.get("end_of_turn_confidence")}
                if words:
                    # How much caller audio had arrived after their last word when the final came back:
                    # endpointing + transcription delay, measured on the audio clock (no wall-clock drift).
                    info["stt_endpoint_ms"] = round(self.audio_bytes / 8 - words[-1]["end"])
                await self.on_final(text, info)
            elif t == "Error":
                raise RuntimeError(f"AssemblyAI error {msg.get('error_code')}: {msg.get('error')}")
            elif t == "Termination":
                return

    async def close(self) -> None:
        if not self.ws:
            return
        try:
            if self.buf:
                await self.ws.send(bytes(self.buf))
            await self.ws.send(json.dumps({"type": "Terminate"}))
            if self._reader:
                await asyncio.wait_for(self._reader, timeout=3)  # let the last final flush
        except Exception:
            pass
        finally:
            await self.ws.close()
