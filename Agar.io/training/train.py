import os
import time
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np

from environment.agario_env import AgarioEnv
from models.recurrent_ppo import RecurrentPPOActorCritic
from training.league import LeagueManager, HeuristicBot


class PPOTrainer:
    """
    Recurrent PPO Multi-Arena Training Pipeline with Self-Play League.
    """

    def __init__(
        self,
        num_arenas=4,
        num_agents_per_arena=16,
        rollout_steps=128,
        lr=3e-4,
        gamma=0.99,
        gae_lambda=0.95,
        ppo_epochs=4,
        mini_batch_size=64,
        clip_eps=0.2,
        ent_coef=0.01,
        vf_coef=0.5,
        device="cpu",
    ):
        self.num_arenas = num_arenas
        self.num_agents = num_agents_per_arena
        self.rollout_steps = rollout_steps
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.ppo_epochs = ppo_epochs
        self.mini_batch_size = mini_batch_size
        self.clip_eps = clip_eps
        self.ent_coef = ent_coef
        self.vf_coef = vf_coef
        self.device = torch.device(device)

        # Create Parallel Environments
        self.envs = [
            AgarioEnv(num_agents=num_agents_per_arena, max_steps=rollout_steps)
            for _ in range(num_arenas)
        ]

        # Model & Optimizer
        self.obs_dim = AgarioEnv.OBS_DIM
        self.model = RecurrentPPOActorCritic(obs_dim=self.obs_dim).to(self.device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=lr)

        # League Manager
        self.league = LeagueManager()

    def train_iteration(self, iter_num):
        """Executes a full rollout collection and PPO update iteration across all arenas."""
        self.model.train()
        start_time = time.time()

        all_obs = []
        all_actions = []
        all_log_probs = []
        all_rewards = []
        all_values = []
        all_dones = []

        total_steps = 0
        arena_rewards = []

        for env in self.envs:
            obs, _ = env.reset()
            # Initialize LSTM state per agent
            lstm_states = {
                agent: self.model.init_lstm_state(batch_size=1, device=self.device)
                for agent in env.possible_agents
            }
            # Heuristic bots
            heuristic_bots = {
                agent: HeuristicBot(agent) for agent in env.possible_agents
            }
            roles = self.league.assign_arena_roles(num_agents=self.num_agents)

            env_obs, env_actions, env_log_probs, env_rewards, env_values, env_dones = [], [], [], [], [], []

            for step in range(self.rollout_steps):
                actions = {}
                step_log_probs = {}
                step_values = {}

                for agent in env.agents:
                    if agent not in obs:
                        continue
                    obs_tensor = torch.tensor(obs[agent], dtype=torch.float32, device=self.device).unsqueeze(0)
                    role_type, ckpt_path = roles.get(agent, ("main_agent", None))

                    if role_type == "heuristic_bot":
                        act = heuristic_bots[agent].get_action(obs[agent])
                        actions[agent] = act
                        step_log_probs[agent] = torch.zeros(1, 1, device=self.device)
                        step_values[agent] = torch.zeros(1, 1, device=self.device)
                    else:
                        with torch.no_grad():
                            act_tensor, log_prob, val, next_lstm = self.model.get_action(
                                obs_tensor, lstm_states[agent]
                            )
                            lstm_states[agent] = next_lstm
                            actions[agent] = act_tensor.cpu().numpy()[0]
                            step_log_probs[agent] = log_prob
                            step_values[agent] = val

                next_obs, rewards, terminations, truncations, infos = env.step(actions)

                # Store rollout step data for main_agent entries
                for agent in env.possible_agents:
                    if roles.get(agent, ("main_agent", None))[0] == "main_agent":
                        if agent in obs and agent in actions:
                            env_obs.append(obs[agent])
                            env_actions.append(actions[agent])
                            env_log_probs.append(step_log_probs[agent].item())
                            env_rewards.append(rewards.get(agent, 0.0))
                            env_values.append(step_values[agent].item())
                            done = terminations.get(agent, False) or truncations.get(agent, False)
                            env_dones.append(done)
                            total_steps += 1

                obs = next_obs
                if not env.agents:
                    break

            arena_rewards.append(sum(env_rewards))
            if env_obs:
                all_obs.extend(env_obs)
                all_actions.extend(env_actions)
                all_log_probs.extend(env_log_probs)
                all_rewards.extend(env_rewards)
                all_values.extend(env_values)
                all_dones.extend(env_dones)

        if not all_obs:
            return {"mean_reward": 0.0, "fps": 0.0}

        # Convert to Tensors
        obs_t = torch.tensor(np.array(all_obs), dtype=torch.float32, device=self.device)
        actions_t = torch.tensor(np.array(all_actions), dtype=torch.float32, device=self.device)
        old_log_probs_t = torch.tensor(np.array(all_log_probs), dtype=torch.float32, device=self.device).unsqueeze(1)
        rewards_t = torch.tensor(np.array(all_rewards), dtype=torch.float32, device=self.device)
        values_t = torch.tensor(np.array(all_values), dtype=torch.float32, device=self.device)
        dones_t = torch.tensor(np.array(all_dones), dtype=torch.float32, device=self.device)

        # Compute GAE Advantages & Returns
        returns_t, advantages_t = self._compute_gae(rewards_t, values_t, dones_t)
        advantages_t = (advantages_t - advantages_t.mean()) / (advantages_t.std() + 1e-8)

        # Perform PPO Optimization Updates
        num_samples = obs_t.size(0)
        policy_loss_epoch = 0.0
        value_loss_epoch = 0.0

        for _ in range(self.ppo_epochs):
            indices = np.random.permutation(num_samples)
            for start in range(0, num_samples, self.mini_batch_size):
                end = min(start + self.mini_batch_size, num_samples)
                mb_idx = indices[start:end]

                mb_obs = obs_t[mb_idx]
                mb_actions = actions_t[mb_idx]
                mb_old_log_probs = old_log_probs_t[mb_idx]
                mb_returns = returns_t[mb_idx].unsqueeze(1)
                mb_advantages = advantages_t[mb_idx].unsqueeze(1)

                # Reshape for sequence evaluation
                mb_obs_seq = mb_obs.unsqueeze(0)
                mb_actions_seq = mb_actions.unsqueeze(0)
                init_lstm = self.model.init_lstm_state(batch_size=len(mb_idx), device=self.device)

                new_log_probs, new_values, entropies = self.model.evaluate_actions(
                    mb_obs_seq, init_lstm, mb_actions_seq
                )
                new_log_probs = new_log_probs[0]
                new_values = new_values[0]
                entropies = entropies[0]

                # Policy Loss with Ratio Clipping
                ratios = torch.exp(new_log_probs - mb_old_log_probs)
                surr1 = ratios * mb_advantages
                surr2 = torch.clamp(ratios, 1.0 - self.clip_eps, 1.0 + self.clip_eps) * mb_advantages
                policy_loss = -torch.min(surr1, surr2).mean()

                # Value Loss
                value_loss = F.mse_loss(new_values, mb_returns)

                # Total Combined Loss
                loss = policy_loss + self.vf_coef * value_loss - self.ent_coef * entropies.mean()

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=0.5)
                self.optimizer.step()

                policy_loss_epoch += policy_loss.item()
                value_loss_epoch += value_loss.item()

        elapsed = time.time() - start_time
        fps = total_steps / max(1e-4, elapsed)
        mean_reward = np.mean(arena_rewards)

        # Checkpoint saving & League update
        if not hasattr(self, 'best_reward'):
            self.best_reward = -9999.0

        if mean_reward > self.best_reward:
            self.best_reward = mean_reward
            best_path = os.path.join(self.league.checkpoint_dir, "best_model.pt")
            torch.save(self.model.state_dict(), best_path)
            print(f"🔥 New Best Model Saved! Mean Reward: {mean_reward:.2f}")

        if iter_num % 10 == 0 and iter_num > 0:
            self.league.save_checkpoint(self.model, iter_num)

        return {
            "iter": iter_num,
            "mean_reward": mean_reward,
            "policy_loss": policy_loss_epoch / (self.ppo_epochs * max(1, num_samples // self.mini_batch_size)),
            "value_loss": value_loss_epoch / (self.ppo_epochs * max(1, num_samples // self.mini_batch_size)),
            "fps": fps,
            "total_steps": total_steps,
        }

    def _compute_gae(self, rewards, values, dones):
        """Computes Generalized Advantage Estimation (GAE)."""
        num_steps = len(rewards)
        advantages = torch.zeros(num_steps, device=self.device)
        last_gae = 0.0

        for t in reversed(range(num_steps)):
            if t == num_steps - 1:
                next_non_terminal = 1.0 - dones[t]
                next_value = 0.0
            else:
                next_non_terminal = 1.0 - dones[t]
                next_value = values[t + 1]

            delta = rewards[t] + self.gamma * next_value * next_non_terminal - values[t]
            last_gae = delta + self.gamma * self.gae_lambda * next_non_terminal * last_gae
            advantages[t] = last_gae

        returns = advantages + values
        return returns, advantages
