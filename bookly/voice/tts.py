"""Cartesia TTS over WebSocket, raw 8 kHz mu-law (what Twilio plays).

One socket per call; each utterance is its own context so chunks stream as
they're generated. Docs: https://docs.cartesia.ai/api-reference/tts/websocket
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import uuid
from typing import AsyncIterator

from websockets.asyncio.client import connect

VERSION = "2026-08-14"
URL = f"wss://api.cartesia.ai/tts/websocket?cartesia_version={VERSION}"
OUTPUT = {"container": "raw", "encoding": "pcm_mulaw", "sample_rate": 8000}


class TTS:
    def __init__(self):
        self.ws = None
        self.queues: dict[str, asyncio.Queue] = {}
        self._reader: asyncio.Task | None = None
        self.model = os.environ.get("CARTESIA_MODEL", "sonic-3.6")
        self.voice = os.environ["CARTESIA_VOICE_ID"]

    async def start(self) -> None:
        self.ws = await connect(URL, additional_headers={"X-API-Key": os.environ["CARTESIA_API_KEY"],
                                                         "Cartesia-Version": VERSION}, max_size=None)
        self._reader = asyncio.create_task(self._read())

    async def _read(self) -> None:
        async for raw in self.ws:
            msg = json.loads(raw)
            q = self.queues.get(msg.get("context_id"))
            if q is None:
                continue
            if msg.get("type") == "chunk" and msg.get("data"):
                await q.put(base64.b64decode(msg["data"]))
            if msg.get("type") == "error":
                await q.put(RuntimeError(f"Cartesia: {msg.get('title')}: {msg.get('message')}"))
            if msg.get("done") or msg.get("type") in ("done", "error"):
                await q.put(None)

    async def stream(self, text: str, ctx: str | None = None) -> AsyncIterator[bytes]:
        """Yield mu-law audio chunks for `text` as Cartesia produces them."""
        ctx = ctx or uuid.uuid4().hex
        q: asyncio.Queue = asyncio.Queue()
        self.queues[ctx] = q
        await self.ws.send(json.dumps({
            "model_id": self.model, "transcript": text, "voice": {"id": self.voice},
            "output_format": OUTPUT, "context_id": ctx, "continue": False, "language": "en",
        }))
        try:
            while True:
                item = await q.get()
                if item is None:
                    return
                if isinstance(item, Exception):
                    raise item
                yield item
        finally:
            self.queues.pop(ctx, None)

    async def cancel(self, ctx: str) -> None:
        """Barge-in: stop generating this context and end its stream."""
        q = self.queues.get(ctx)
        if q is None:
            return
        try:
            await self.ws.send(json.dumps({"context_id": ctx, "cancel": True}))
        except Exception:
            pass
        await q.put(None)

    async def synth(self, text: str) -> bytes:
        return b"".join([c async for c in self.stream(text)])

    async def close(self) -> None:
        if self.ws:
            await self.ws.close()
