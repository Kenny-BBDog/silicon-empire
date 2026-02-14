"""
Redis Streams Message Bus.

Provides pub/sub-style messaging between agents using Redis Streams.
Each agent subscribes to its own stream, and other agents publish to it.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import redis.asyncio as aioredis

from src.config.settings import get_settings
from src.core.envelope import Envelope


class MessageBus:
    """Redis Streams-based message bus for inter-agent communication."""

    STREAM_PREFIX = "silicon:stream:"
    GROUP_PREFIX = "silicon:group:"

    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None

    async def init(self) -> None:
        """Initialize Redis connection."""
        settings = get_settings()
        self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()

    @property
    def redis(self) -> aioredis.Redis:
        assert self._redis is not None, "MessageBus not initialized"
        return self._redis

    def _stream_name(self, target: str) -> str:
        """Get the stream name for a target agent."""
        return f"{self.STREAM_PREFIX}{target.lower()}"

    # ─── Publishing ───

    async def publish(self, envelope: Envelope) -> str:
        """
        Publish an Envelope to the target agent's stream.
        Returns the message ID.
        """
        stream = self._stream_name(envelope.header.to_node)
        data = {
            "header": envelope.header.model_dump_json(),
            "body": envelope.body,
            "trace_id": envelope.header.trace_id,
        }
        msg_id = await self.redis.xadd(stream, data)
        return msg_id

    async def publish_event(
        self, target: str, event_type: str, payload: dict[str, Any], trace_id: str = ""
    ) -> str:
        """Publish a lightweight event (without full Envelope)."""
        stream = self._stream_name(target)
        data = {
            "event_type": event_type,
            "payload": json.dumps(payload, default=str),
            "trace_id": trace_id,
        }
        return await self.redis.xadd(stream, data)

    # ─── Consuming ───

    async def read_latest(
        self, target: str, count: int = 10
    ) -> list[dict[str, Any]]:
        """Read the latest N messages from a stream."""
        stream = self._stream_name(target)
        try:
            messages = await self.redis.xrevrange(stream, count=count)
        except aioredis.ResponseError:
            return []

        results = []
        for msg_id, data in messages:
            entry = {"id": msg_id, **data}
            if "header" in data:
                entry["header"] = json.loads(data["header"])
            if "payload" in data:
                entry["payload"] = json.loads(data["payload"])
            results.append(entry)
        return results

    async def consume_stream(
        self, target: str, last_id: str = "$", block_ms: int = 5000
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Continuously consume new messages from a stream.
        Yields messages as they arrive (blocking read).
        """
        stream = self._stream_name(target)
        current_id = last_id

        while True:
            try:
                result = await self.redis.xread(
                    {stream: current_id}, count=1, block=block_ms
                )
            except aioredis.ConnectionError:
                break

            if not result:
                continue

            for _stream_name, messages in result:
                for msg_id, data in messages:
                    current_id = msg_id
                    entry = {"id": msg_id, **data}
                    if "header" in data:
                        entry["header"] = json.loads(data["header"])
                    if "payload" in data:
                        entry["payload"] = json.loads(data["payload"])
                    yield entry

    # ─── Stream Management ───

    async def create_consumer_group(self, target: str, group_name: str) -> bool:
        """Create a consumer group for a stream."""
        stream = self._stream_name(target)
        try:
            await self.redis.xgroup_create(stream, group_name, mkstream=True)
            return True
        except aioredis.ResponseError:
            return False  # Group already exists

    async def stream_length(self, target: str) -> int:
        """Get the number of messages in a stream."""
        stream = self._stream_name(target)
        try:
            return await self.redis.xlen(stream)
        except aioredis.ResponseError:
            return 0


# Singleton
_bus: MessageBus | None = None


async def get_bus() -> MessageBus:
    """Get or create the global MessageBus singleton."""
    global _bus
    if _bus is None:
        _bus = MessageBus()
        await _bus.init()
    return _bus
