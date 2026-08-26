import os
import json
import asyncio
import math
import time
import websockets
import torch
import numpy as np

from models.recurrent_ppo import RecurrentPPOActorCritic
from environment.agario_env import AgarioEnv


class LiveAgarioBridge:
    """
    Live WebSockets Bridge Server connecting trained PyTorch MARL Recurrent PPO Model
    to live browser tabs running agar.io via Chrome Extension.
    """

    def __init__(self, model_path="checkpoints/best_model.pt", port=8081):
        self.port = port
        self.device = torch.device("cpu")

        # Load Recurrent PPO Policy Model
        self.model = RecurrentPPOActorCritic(obs_dim=AgarioEnv.OBS_DIM).to(self.device)
        if os.path.exists(model_path):
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
            print(f"🏆 Loaded Trained Model Weights from '{model_path}'")
        else:
            print(f"⚠️ Model checkpoint '{model_path}' not found, running with initialized policy")

        # Opponent coordinate tracking history to calculate velocities dynamically
        self.prev_opponents = []
        self.prev_time = time.time() if 'time' in globals() else 0.0

        self.model.eval()
        self.lstm_state = self.model.init_lstm_state(batch_size=1, device=self.device)

    def state_to_obs_vector(self, state_dict):
        """Converts incoming browser state dictionary to 512-dimensional observation vector."""
        obs = np.zeros(AgarioEnv.OBS_DIM, dtype=np.float32)

        cx = state_dict.get("cx", 400.0)
        cy = state_dict.get("cy", 300.0)
        view_dist = 600.0

        # Calculate player mass based on canvas-scraped radius: mass = (r^2) / 100
        player_r = state_dict.get("player_radius", 20.0)
        player_mass = max(10.0, (player_r ** 2) / 100.0)

        # 1. Self Status (Indices 0..32)
        obs[0] = math.log(player_mass) / 10.0
        obs[1] = 1.0 / 16.0  # Cell count fraction
        obs[2] = (cx / 2000.0) * 2.0 - 1.0
        obs[3] = (cy / 2000.0) * 2.0 - 1.0
        obs[6] = 1.0  # Ready to merge fraction
        obs[10] = player_r / 300.0
        obs[11] = 0.5  # Left wall
        obs[12] = 0.5  # Right wall
        obs[13] = 0.5  # Top wall
        obs[14] = 0.5  # Bottom wall
        obs[17] = 1.0  # Full unobstructed escape arc
        obs[22] = 1.0  # Can eject
        obs[25] = 0.0  # Ejected mass density potential

        # 2. Food Pellets (60 floats starting at index 33)
        food_list = state_dict.get("food", [])
        food_dists = []
        h_food = np.zeros(8, dtype=np.float32)
        sum_gx, sum_gy = 0.0, 0.0
        food_x_sum, food_y_sum = 0.0, 0.0

        for f in food_list:
            fx_rel = f.get("x", 0.0)
            fy_rel = f.get("y", 0.0)
            dx = fx_rel / view_dist
            dy = fy_rel / view_dist
            d = math.hypot(dx, dy)

            if d <= 1.0:
                food_dists.append((d, dx, dy))

            food_x_sum += fx_rel
            food_y_sum += fy_rel

            denom = (d * view_dist)**2 + 100.0
            sum_gx += fx_rel / denom
            sum_gy += fy_rel / denom

            angle = math.atan2(fy_rel, fx_rel)
            sector_idx = int(math.floor((angle + math.pi) / (math.pi / 4.0))) % 8
            h_food[sector_idx] += math.exp(-d)

        h_food = np.clip(h_food / 20.0, 0.0, 1.0)
        food_dists.sort(key=lambda item: item[0])

        idx = 33
        for d, dx, dy in food_dists[:30]:
            obs[idx] = dx
            obs[idx + 1] = dy
            idx += 2

        # 8-Sector density + Macro Centroid (13 floats starting at index 93)
        idx = 93
        for k in range(8):
            obs[idx + k] = h_food[k]
        if food_list:
            obs[idx + 8] = (food_x_sum / len(food_list)) / 2000.0
            obs[idx + 9] = (food_y_sum / len(food_list)) / 2000.0
        g_norm = math.hypot(sum_gx, sum_gy)
        if g_norm > 1e-4:
            obs[idx + 10] = sum_gx / g_norm
            obs[idx + 11] = sum_gy / g_norm
        obs[idx + 12] = min(1.0, len(food_dists) / 30.0)

        # 3. Viruses (60 floats starting at index 106)
        virus_list = state_dict.get("viruses", [])
        virus_dists = []
        for v in virus_list:
            vx_rel = v.get("x", 0.0)
            vy_rel = v.get("y", 0.0)
            v_mass = v.get("mass", 100.0)
            dx = vx_rel / view_dist
            dy = vy_rel / view_dist
            d = math.hypot(dx, dy)
            if d <= 1.5:
                virus_dists.append((d, dx, dy, v_mass / 100.0))

        virus_dists.sort(key=lambda item: item[0])
        idx = 106
        for d, dx, dy, vm in virus_dists[:10]:
            obs[idx] = dx
            obs[idx + 1] = dy
            obs[idx + 2] = vm
            obs[idx + 4] = 1.0 if vm > 0.8 else 0.0  # Safe sanctuary shield approximation
            idx += 6

        # 4. Opponents (192 floats starting at index 166)
        opp_list = state_dict.get("opponents", [])
        opp_dists = []

        curr_time = time.time()
        dt = max(0.001, curr_time - self.prev_time)
        self.prev_time = curr_time

        tracked_opponents = []

        for o in opp_list:
            ox_rel = o.get("x", 0.0)
            oy_rel = o.get("y", 0.0)
            orad = o.get("mass", 20.0)
            o_mass = max(1.0, (orad ** 2) / 100.0)

            # Match with previous frame to find velocity
            vx, vy = 0.0, 0.0
            best_d = 50.0
            for prev_o in self.prev_opponents:
                dist = math.hypot(ox_rel - prev_o["x"], oy_rel - prev_o["y"])
                if dist < best_d:
                    best_d = dist
                    vx = (ox_rel - prev_o["x"]) / dt
                    vy = (oy_rel - prev_o["y"]) / dt

            tracked_opponents.append({"x": ox_rel, "y": oy_rel, "r": orad, "mass": o_mass, "vx": vx, "vy": vy})

        self.prev_opponents = tracked_opponents

        for to in tracked_opponents:
            dx = to["x"] / view_dist
            dy = to["y"] / view_dist
            d_pixels = math.hypot(to["x"], to["y"])
            d = d_pixels / view_dist

            if d <= 2.0:
                om = to["mass"]
                m_ratio = om / max(1.0, player_mass)
                eat_flag = 1.0 if player_mass >= om * 1.15 else (-1.0 if om >= player_mass * 1.15 else 0.0)

                # Split-Kill Reach Signal
                split_mass = player_mass / 2.0
                split_radius = math.sqrt(max(1.0, split_mass) * 100.0)
                split_reach = (player_r + 300.0 + split_radius) / view_dist
                can_split_eat = (player_mass >= 36.0) and (split_mass >= om * 1.15)

                opp_split_mass = om / 2.0
                opp_split_radius = math.sqrt(max(1.0, opp_split_mass) * 100.0)
                opp_split_reach = (to["r"] + 300.0 + opp_split_radius) / view_dist
                can_be_split_eaten = (om >= 36.0) and (opp_split_mass >= player_mass * 1.15)

                split_kill_sig = 0.0
                if can_split_eat and d <= split_reach:
                    split_kill_sig = 1.0 - (d / max(1e-4, split_reach))
                elif can_be_split_eaten and d <= opp_split_reach:
                    split_kill_sig = -1.0 + (d / max(1e-4, opp_split_reach))

                # Motion & Vector Interception Signals
                rel_vx = to["vx"] / 500.0
                rel_vy = to["vy"] / 500.0
                rx = dx / max(1e-4, d)
                ry = dy / max(1e-4, d)
                v_closing = -(rel_vx * rx + rel_vy * ry)

                net_closing_speed = 600.0 - (v_closing * 500.0)
                tau_intercept = min(2.0, d_pixels / max(100.0, net_closing_speed))

                x_lead = to["x"] + to["vx"] * min(2.0, max(0.0, tau_intercept))
                y_lead = to["y"] + to["vy"] * min(2.0, max(0.0, tau_intercept))
                dx_lead = x_lead / view_dist
                dy_lead = y_lead / view_dist

                opp_dists.append((
                    d, dx, dy, m_ratio, eat_flag, to["vx"] / 500.0, to["vy"] / 500.0,
                    split_kill_sig, rel_vx, rel_vy, v_closing, dx_lead, dy_lead
                ))

        opp_dists.sort(key=lambda item: item[0])
        idx = 166
        for item in opp_dists[:16]:
            (d, dx, dy, m_ratio, eat_flag, ovx, ovy, sk_sig, rel_vx, rel_vy, v_closing, dx_lead, dy_lead) = item
            obs[idx] = dx
            obs[idx + 1] = dy
            obs[idx + 2] = m_ratio
            obs[idx + 3] = eat_flag
            obs[idx + 4] = ovx
            obs[idx + 5] = ovy
            obs[idx + 6] = d
            obs[idx + 7] = sk_sig
            obs[idx + 8] = rel_vx
            obs[idx + 9] = rel_vy
            obs[idx + 10] = v_closing
            obs[idx + 11] = dx_lead
            idx += 12

        return obs

        return obs

    async def handle_connection(self, websocket, path=None):
        print(f"🔌 Browser Extension Connected to Live Bridge Server!")
        try:
            async for message in websocket:
                data = json.loads(message)
                if data.get("type") == "live_state":
                    # Convert live state to 512-dim observation tensor
                    obs_vec = self.state_to_obs_vector(data)
                    obs_t = torch.tensor(obs_vec, dtype=torch.float32, device=self.device).unsqueeze(0)

                    # Model forward pass
                    with torch.no_grad():
                        action_t, _, _, next_lstm = self.model.get_action(obs_t, self.lstm_state)
                        self.lstm_state = next_lstm

                    action = action_t.cpu().numpy()[0]

                    # Send action response back to Chrome Extension
                    response = {
                        "type": "action",
                        "action": [
                            float(round(action[0], 3)),
                            float(round(action[1], 3)),
                            float(round(action[2], 3)),
                            float(round(action[3], 3)),
                        ]
                    }
                    await websocket.send(json.dumps(response))
        except websockets.ConnectionClosedError:
            print("🔌 Browser Extension Disconnected")
        finally:
            pass

    def start(self):
        print(f"🚀 Live Agar.io AI Inference Server Running at ws://127.0.0.1:{self.port}", flush=True)
        asyncio.run(self.run_server())

    async def run_server(self):
        async with websockets.serve(self.handle_connection, "127.0.0.1", self.port, origins=None):
            print(f"✅ WebSockets Listening on 127.0.0.1:{self.port} (Origins Allowed)", flush=True)
            await asyncio.Future()  # Run forever


if __name__ == "__main__":
    bridge = LiveAgarioBridge()
    bridge.start()
