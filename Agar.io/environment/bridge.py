import json
import asyncio
import websockets


class AgarioBridgeServer:
    """
    WebSocket RPC Bridge server streaming game engine state to web visualizers or external agents.
    """

    def __init__(self, env, host="0.0.0.0", port=8080):
        self.env = env
        self.host = host
        self.port = port
        self.connected_clients = set()

    def serialize_state(self):
        """Serializes current environment state into a JSON-serializable dictionary."""
        agents_data = {}
        for agent_id, cells in self.env.player_cells.items():
            agents_data[agent_id] = [
                {
                    "id": int(c.id),
                    "x": float(round(c.x, 1)),
                    "y": float(round(c.y, 1)),
                    "mass": float(round(c.mass, 1)),
                    "radius": float(round(c.radius, 1)),
                    "vx": float(round(c.vx, 1)),
                    "vy": float(round(c.vy, 1)),
                    "cooldown": float(round(c.merge_cooldown, 1)),
                }
                for c in cells
            ]

        food_data = [
            {"x": float(round(f.x, 1)), "y": float(round(f.y, 1))}
            for f in self.env.food_pellets
        ]

        virus_data = [
            {"x": float(round(v.x, 1)), "y": float(round(v.y, 1)), "mass": float(round(v.mass, 1)), "radius": float(round(v.radius, 1))}
            for v in self.env.viruses
        ]

        eject_data = [
            {"x": float(round(em.x, 1)), "y": float(round(em.y, 1)), "mass": float(round(em.mass, 1))}
            for em in self.env.ejected_masses
        ]

        return {
            "type": "state_update",
            "step": int(self.env.step_count),
            "map_width": float(self.env.map_width),
            "map_height": float(self.env.map_height),
            "players": agents_data,
            "food": food_data,
            "viruses": virus_data,
            "ejected": eject_data,
        }

    async def register(self, websocket):
        self.connected_clients.add(websocket)
        # Send initial config
        init_msg = {
            "type": "init",
            "map_width": self.env.map_width,
            "map_height": self.env.map_height,
            "max_steps": self.env.max_steps,
        }
        await websocket.send(json.dumps(init_msg))

    async def unregister(self, websocket):
        self.connected_clients.discard(websocket)

    async def broadcast_state(self):
        if not self.connected_clients:
            return
        state_msg = json.dumps(self.serialize_state())
        active_clients = [c for c in list(self.connected_clients) if not getattr(c, 'closed', False)]
        if active_clients:
            await asyncio.gather(
                *[client.send(state_msg) for client in active_clients],
                return_exceptions=True
            )

    async def handler(self, websocket, path=None):
        await self.register(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                # Handle incoming action if client is playing as an external agent
                if data.get("type") == "action":
                    agent_id = data.get("agent_id")
                    action = data.get("action")
                    # Action routing handled in main loop
        except websockets.ConnectionClosedError:
            pass
        finally:
            await self.unregister(websocket)
