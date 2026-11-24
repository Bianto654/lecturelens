from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any
from fastapi import WebSocket


class RoomConnectionManager:
    """
    Manages low-latency WebSocket connections per lecture session room.
    Tracks hosts and connected students independently for accurate student counts.
    """

    def __init__(self) -> None:
        self._students: dict[str, dict[WebSocket, str]] = defaultdict(dict)
        self._hosts: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect_student(
        self, session_id: str, websocket: WebSocket, client_id: str
    ) -> int:
        await websocket.accept()
        async with self._lock:
            self._students[session_id][websocket] = client_id
            return len(set(self._students[session_id].values()))

    async def disconnect_student(self, session_id: str, websocket: WebSocket) -> int:
        async with self._lock:
            self._students[session_id].pop(websocket, None)
            if not self._students[session_id]:
                self._students.pop(session_id, None)
                return 0
            return len(set(self._students[session_id].values()))

    async def connect_host(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._hosts[session_id].add(websocket)

    async def disconnect_host(self, session_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._hosts[session_id].discard(websocket)
            if not self._hosts[session_id]:
                self._hosts.pop(session_id, None)

    def student_count(self, session_id: str) -> int:
        clients = self._students.get(session_id)
        if not clients:
            return 0
        return len(set(clients.values()))

    async def broadcast(self, session_id: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._students.get(session_id, {}).keys()) + list(
                self._hosts.get(session_id, set())
            )
        if not targets:
            return

        stale: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)

        if stale:
            async with self._lock:
                for ws in stale:
                    self._students.get(session_id, {}).pop(ws, None)
                    self._hosts.get(session_id, set()).discard(ws)


ws_manager = RoomConnectionManager()
