import os
import math
import torch
import numpy as np
from models.recurrent_ppo import RecurrentPPOActorCritic


class HeuristicBot:
    """
    Rule-based baseline bot for early-stage self-play stabilization.
    """

    def __init__(self, agent_id):
        self.agent_id = agent_id

    def get_action(self, obs):
        """
        Parses observation array to navigate toward nearest food, flee larger opponents, or split on smaller opponents.
        obs dim: 256
        """
        # Food section starts at index 10 (30 pairs of dx, dy)
        food_dx, food_dy = 0.0, 0.0
        min_dist = 999.0
        for i in range(10, 70, 2):
            dx, dy = obs[i], obs[i + 1]
            if dx == 0.0 and dy == 0.0:
                continue
            d = math.hypot(dx, dy)
            if d < min_dist:
                min_dist = d
                food_dx, food_dy = dx, dy

        split = 0.0
        eject = 0.0

        # Opponent section starts at index 110 (16 tuples of 7 values)
        for i in range(110, 222, 7):
            opp_dx, opp_dy = obs[i], obs[i + 1]
            m_ratio = obs[i + 2]
            eat_flag = obs[i + 3]
            if opp_dx == 0.0 and opp_dy == 0.0:
                continue
            opp_d = math.hypot(opp_dx, opp_dy)

            # If opponent can eat us, flee in opposite direction!
            if eat_flag == -1.0 and opp_d < 0.5:
                food_dx = -opp_dx
                food_dy = -opp_dy
                break

            # If we can eat opponent and close enough, split to capture!
            if eat_flag == 1.0 and opp_d < 0.35 and m_ratio < 0.6:
                food_dx = opp_dx
                food_dy = opp_dy
                split = 1.0
                break

        # Normalize movement direction
        norm = math.hypot(food_dx, food_dy)
        if norm > 1e-4:
            food_dx /= norm
            food_dy /= norm
        else:
            food_dx, food_dy = np.random.uniform(-1, 1), np.random.uniform(-1, 1)

        return np.array([food_dx, food_dy, split, eject], dtype=np.float32)


class LeagueManager:
    """
    Manages self-play league pool, checkpointing, ELO tracking, and arena slot assignments.
    """

    def __init__(self, checkpoint_dir="checkpoints", initial_elo=1200):
        self.checkpoint_dir = checkpoint_dir
        self.initial_elo = initial_elo
        os.makedirs(checkpoint_dir, exist_ok=True)

        self.elo_ratings = {"main_agent": initial_elo, "heuristic_bot": 1000}
        self.checkpoints = [] # list of checkpoint file paths

    def save_checkpoint(self, model, step_num):
        path = os.path.join(self.checkpoint_dir, f"model_step_{step_num}.pt")
        torch.save(model.state_dict(), path)
        name = f"checkpoint_{step_num}"
        self.checkpoints.append((name, path))
        self.elo_ratings[name] = self.elo_ratings["main_agent"]
        print(f"🏆 Saved League Checkpoint: {name} (ELO: {self.elo_ratings[name]:.0f})")

    def load_checkpoint_model(self, path, obs_dim=256, device="cpu"):
        model = RecurrentPPOActorCritic(obs_dim=obs_dim).to(device)
        model.load_state_dict(torch.load(path, map_location=device))
        model.eval()
        return model

    def update_elo(self, agent_a, agent_b, score_a, K=32):
        """
        Updates ELO rating after a head-to-head match.
        score_a: 1.0 for win (ate opponent), 0.5 for draw, 0.0 for loss.
        """
        ra = self.elo_ratings.get(agent_a, self.initial_elo)
        rb = self.elo_ratings.get(agent_b, self.initial_elo)

        ea = 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))
        eb = 1.0 / (1.0 + 10.0 ** ((ra - rb) / 400.0))

        self.elo_ratings[agent_a] = ra + K * (score_a - ea)
        self.elo_ratings[agent_b] = rb + K * ((1.0 - score_a) - eb)

    def assign_arena_roles(self, num_agents=16):
        """
        Assigns roles to agents in an arena instance:
        - 50% Main active learning model
        - 35% Historical league checkpoints (if available)
        - 15% Heuristic baseline bots
        """
        roles = {}
        for i in range(num_agents):
            agent_id = f"agent_{i}"
            rand_val = np.random.rand()
            if rand_val < 0.5 or not self.checkpoints:
                roles[agent_id] = ("main_agent", None)
            elif rand_val < 0.85 and self.checkpoints:
                # Sample a random historical checkpoint
                ckpt_name, ckpt_path = self.checkpoints[np.random.randint(len(self.checkpoints))]
                roles[agent_id] = ("checkpoint", ckpt_path)
            else:
                roles[agent_id] = ("heuristic_bot", None)
        return roles
