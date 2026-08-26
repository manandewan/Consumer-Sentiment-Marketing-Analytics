import os
import json
import asyncio
import http.server
import socketserver
import threading
import websockets
import torch
import numpy as np

from environment.agario_env import AgarioEnv
from environment.bridge import AgarioBridgeServer
from models.recurrent_ppo import RecurrentPPOActorCritic
from training.league import HeuristicBot


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


class ConfigHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """Extends HTTP Handler to serve /config JSON specifying active WebSocket port."""
    ws_port = 8081

    def do_GET(self):
        if self.path == '/config':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            config_data = json.dumps({'ws_port': ConfigHTTPHandler.ws_port})
            self.wfile.write(config_data.encode('utf-8'))
            return
        super().do_GET()


class VisualizerServer:
    """
    Combines an HTTP Static File Server (for frontend UI) and
    a WebSockets Arena Server running Recurrent PPO model inference live!
    """

    def __init__(self, http_port=8080, ws_port=8081):
        self.http_port = http_port
        self.ws_port = ws_port
        self.env = AgarioEnv(num_agents=16, max_steps=5000)
        self.obs, _ = self.env.reset()
        self.bridge = AgarioBridgeServer(self.env, port=ws_port)

        # PyTorch Model & Hidden State
        self.device = torch.device("cpu")
        self.model = RecurrentPPOActorCritic(obs_dim=AgarioEnv.OBS_DIM).to(self.device)
        self.model.eval()
        self.lstm_states = {
            agent: self.model.init_lstm_state(batch_size=1, device=self.device)
            for agent in self.env.possible_agents
        }
        self.heuristic_bots = {
            agent: HeuristicBot(agent) for agent in self.env.possible_agents
        }

    def start_http_server(self):
        web_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(web_dir)

        for port in [self.http_port, 8082, 8085, 9000]:
            try:
                httpd = ReusableTCPServer(("", port), ConfigHTTPHandler)
                self.http_port = port
                print(f"🌐 Visualizer Dashboard running at http://localhost:{port}")
                httpd.serve_forever()
                break
            except OSError:
                print(f"HTTP Port {port} busy, trying next...")

    async def game_loop(self):
        """Simulates environment using Recurrent PPO model inference and streams at 30 FPS."""
        bound_server = None
        for port in [self.ws_port, 8083, 8086, 8088, 9001]:
            try:
                server_ctx = websockets.serve(self.bridge.handler, "0.0.0.0", port)
                bound_server = await server_ctx.__aenter__()
                self.ws_port = port
                ConfigHTTPHandler.ws_port = port
                print(f"📡 WebSocket Arena Server active on ws://localhost:{port}")
                break
            except OSError:
                print(f"WebSocket Port {port} busy, trying next...")

        if not bound_server:
            print("❌ Error: Could not bind WebSocket server to any port!")
            return

        try:
            while True:
                actions = {}
                for agent in self.env.agents:
                    if agent not in self.obs:
                        continue
                    # 75% Neural Net PPO Policy, 25% Heuristic Bot
                    if int(agent.split("_")[-1]) < 12:
                        obs_t = torch.tensor(self.obs[agent], dtype=torch.float32, device=self.device).unsqueeze(0)
                        with torch.no_grad():
                            act_t, _, _, next_lstm = self.model.get_action(obs_t, self.lstm_states[agent])
                            self.lstm_states[agent] = next_lstm
                            actions[agent] = act_t.numpy()[0]
                    else:
                        actions[agent] = self.heuristic_bots[agent].get_action(self.obs[agent])

                next_obs, rewards, terms, truncs, _ = self.env.step(actions)
                self.obs = next_obs

                if not self.env.agents or self.env.step_count >= self.env.max_steps:
                    self.obs, _ = self.env.reset()
                    self.lstm_states = {
                        a: self.model.init_lstm_state(batch_size=1, device=self.device)
                        for a in self.env.possible_agents
                    }

                await self.bridge.broadcast_state()
                await asyncio.sleep(0.033)  # ~30 FPS server tick rate
        finally:
            await bound_server.close()

    def start(self):
        http_thread = threading.Thread(target=self.start_http_server, daemon=True)
        http_thread.start()
        asyncio.run(self.game_loop())


if __name__ == "__main__":
    server = VisualizerServer()
    server.start()
