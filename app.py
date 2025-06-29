from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict
import uvicorn

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

class DraftManager:
    def __init__(self):
        self.players_pool = []  # 可選球員清單（可在前端傳入）
        self.teams: Dict[str, List[str]] = {"A": [], "B": []}
        self.turn = "A"
        self.round = 1
        self.max_rounds = 10
        self.finished = False

    def reset(self):
        self.teams = {"A": [], "B": []}
        self.turn = "A"
        self.round = 1
        self.finished = False

    def pick(self, team: str, player: str):
        if self.finished or self.turn != team:
            return False
        self.teams[team].append(player)
        self.turn = "B" if team == "A" else "A"
        self.round += 1
        if self.round > self.max_rounds:
            self.finished = True
        return True

    def status(self):
        return {
            "teams": self.teams,
            "turn": self.turn,
            "round": self.round,
            "finished": self.finished,
        }

draft = DraftManager()

class ConnectionManager:
    def __init__(self):
        self.connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.connections.remove(websocket)

    async def send_to_all(self, data: dict):
        for conn in self.connections:
            await conn.send_json(data)

manager = ConnectionManager()

@app.get("/")
async def index():
    with open("static/index.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await manager.send_to_all({"type": "state", **draft.status()})
    try:
        while True:
            msg = await websocket.receive_json()
            if msg["type"] == "pick":
                team = msg["team"]
                player = msg["player"]
                if draft.pick(team, player):
                    await manager.send_to_all({"type": "state", **draft.status()})
            elif msg["type"] == "reset":
                draft.reset()
                await manager.send_to_all({"type": "state", **draft.status()})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
