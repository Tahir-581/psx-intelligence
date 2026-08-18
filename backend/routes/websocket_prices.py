import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

from backend.database import get_redis

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/prices/{symbol}")
async def price_websocket(websocket: WebSocket, symbol: str) -> None:
    await websocket.accept()
    sym = symbol.upper()
    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"prices:{sym}")

    cached = await redis.get(f"ticker:{sym}:snapshot")
    if cached:
        await websocket.send_text(cached)

    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("data"):
                await websocket.send_text(message["data"])
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"prices:{sym}")
        await pubsub.close()
