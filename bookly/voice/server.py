"""Phone mode: Twilio webhook + media-stream WebSocket.

    .venv/bin/python -m bookly.voice.server          # listens on :8080
    ngrok http --url=$PUBLIC_HOST 8080               # in another terminal

Point the Bookly number's Voice webhook at https://$PUBLIC_HOST/voice (HTTP POST).
"""
from __future__ import annotations

import json
import os
import traceback
from contextlib import asynccontextmanager
from xml.sax.saxutils import quoteattr

import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse, Response
from twilio.request_validator import RequestValidator

import bookly.agent  # noqa: F401  (loads .env on import)
from bookly.voice.call import CallSession, load_phrases

PORT = int(os.environ.get("PORT", "8080"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await load_phrases()
    print(f"[server] phrases cached; webhook https://{os.environ.get('PUBLIC_HOST', '<PUBLIC_HOST>')}/voice")
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/voice")
async def voice(request: Request):
    form = dict(await request.form())
    host = os.environ.get("PUBLIC_HOST", "").strip()
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    if token:  # only Twilio can start a call on our agent
        sig = request.headers.get("X-Twilio-Signature", "")
        if not RequestValidator(token).validate(f"https://{host}/voice", form, sig):
            return PlainTextResponse("invalid signature", status_code=403)
    caller = form.get("From", "")
    twiml = (
        '<?xml version="1.0" encoding="UTF-8"?><Response><Connect>'
        f'<Stream url="wss://{host}/media"><Parameter name="caller" value={quoteattr(caller)}/></Stream>'
        "</Connect></Response>"
    )
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/media")
async def media(ws: WebSocket):
    await ws.accept()
    session: CallSession | None = None
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            ev = msg.get("event")
            if ev == "start":
                st = msg["start"]
                caller = (st.get("customParameters") or {}).get("caller") or None
                session = CallSession(ws, st["streamSid"], st.get("callSid", st["streamSid"]), caller)
                print(f"[call start] {session.agent.call_id} caller={caller}")
                await session.start()
            elif ev == "media" and session and msg["media"].get("track", "inbound") == "inbound":
                await session.on_media(msg["media"]["payload"])
            elif ev == "mark" and session:
                await session.on_mark(msg["mark"]["name"])
            elif ev == "stop":
                break
    except (WebSocketDisconnect, RuntimeError):
        pass
    except Exception:
        traceback.print_exc()
    finally:
        if session:
            await session.close("stream_closed")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
