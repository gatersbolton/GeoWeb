import json
from typing import Dict

import pandas as pd
from fastapi import WebSocket
from concurrent.futures import ThreadPoolExecutor

# 全局状态
calculation_results: Dict[str, dict] = {}
progress_messages: Dict[str, dict] = {}
last_printed_percentage: Dict[str, float] = {}


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_progress(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(message))
            except:
                self.disconnect(session_id)


manager = ConnectionManager()

# 线程池
executor = ThreadPoolExecutor(max_workers=2)


def make_progress_message(message: str, percentage=None):
    return {
        "type": "progress",
        "message": message,
        "percentage": percentage,
        "timestamp": pd.Timestamp.now().isoformat(),
    }


