import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal, Bernoulli


class RecurrentPPOActorCritic(nn.Module):
    """
    Recurrent PPO Actor-Critic Network featuring an MLP feature extractor,
    LSTM temporal memory cell, continuous movement action head, and Bernoulli split/eject heads.
    """

    def __init__(self, obs_dim=512, hidden_dim=256):
        super().__init__()
        self.obs_dim = obs_dim
        self.hidden_dim = hidden_dim

        # Feature Extractor MLP
        self.feature_mlp = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
        )

        # Recurrent LSTM Core
        self.lstm = nn.LSTMCell(hidden_dim, hidden_dim)

        # Actor Policy Heads
        # Continuous movement dx, dy
        self.actor_move_mean = nn.Linear(hidden_dim, 2)
        self.actor_move_logstd = nn.Parameter(torch.zeros(1, 2))

        # Discrete Split & Eject actions
        self.actor_split = nn.Linear(hidden_dim, 1)
        self.actor_eject = nn.Linear(hidden_dim, 1)

        # Critic Value Head
        self.critic_value = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.SiLU(),
            nn.Linear(hidden_dim // 2, 1),
        )

    def init_lstm_state(self, batch_size=1, device=None):
        if device is None:
            device = next(self.parameters()).device
        return (
            torch.zeros(batch_size, self.hidden_dim, device=device),
            torch.zeros(batch_size, self.hidden_dim, device=device),
        )

    def forward(self, obs, lstm_state):
        """
        Forward pass for a single time step.
        obs: [batch_size, obs_dim]
        lstm_state: tuple (hx, cx)
        """
        features = self.feature_mlp(obs)
        hx, cx = self.lstm(features, lstm_state)

        # Movement mean (tanh -> [-1, 1])
        move_mean = torch.tanh(self.actor_move_mean(hx))
        move_std = torch.exp(self.actor_move_logstd).expand_as(move_mean)

        # Split and Eject probabilities
        split_prob = torch.sigmoid(self.actor_split(hx))
        eject_prob = torch.sigmoid(self.actor_eject(hx))

        # State value estimate
        value = self.critic_value(hx)

        return move_mean, move_std, split_prob, eject_prob, value, (hx, cx)

    def get_action(self, obs, lstm_state, deterministic=False):
        """
        Sample actions from policy for rollout collection.
        obs: [batch_size, obs_dim]
        """
        move_mean, move_std, split_prob, eject_prob, value, next_lstm = self.forward(obs, lstm_state)

        move_dist = Normal(move_mean, move_std)
        split_dist = Bernoulli(split_prob)
        eject_dist = Bernoulli(eject_prob)

        if deterministic:
            move_action = move_mean
            split_action = (split_prob > 0.5).float()
            eject_action = (eject_prob > 0.5).float()
        else:
            move_action = move_dist.sample()
            split_action = split_dist.sample()
            eject_action = eject_dist.sample()

        # Clamp continuous movement action
        move_action = torch.clamp(move_action, -1.0, 1.0)

        # Compute combined log probabilities
        move_log_prob = move_dist.log_prob(move_action).sum(dim=-1, keepdim=True)
        split_log_prob = split_dist.log_prob(split_action)
        eject_log_prob = eject_dist.log_prob(eject_action)

        total_log_prob = move_log_prob + split_log_prob + eject_log_prob

        action_vector = torch.cat([move_action, split_action, eject_action], dim=-1)

        return action_vector, total_log_prob, value, next_lstm

    def evaluate_actions(self, obs_seq, initial_lstm_state, action_seq, done_mask=None):
        """
        Evaluate sequences of observations and actions during PPO updates.
        obs_seq: [seq_len, batch_size, obs_dim]
        action_seq: [seq_len, batch_size, 4]
        """
        seq_len, batch_size, _ = obs_seq.shape
        hx, cx = initial_lstm_state

        log_probs = []
        values = []
        entropies = []

        for t in range(seq_len):
            obs_t = obs_seq[t]
            action_t = action_seq[t]

            if done_mask is not None:
                hx = hx * (1.0 - done_mask[t])
                cx = cx * (1.0 - done_mask[t])

            move_mean, move_std, split_prob, eject_prob, val, (hx, cx) = self.forward(obs_t, (hx, cx))

            move_action = action_t[:, :2]
            split_action = (action_t[:, 2:3] > 0.5).float()
            eject_action = (action_t[:, 3:4] > 0.5).float()

            move_dist = Normal(move_mean, move_std)
            split_dist = Bernoulli(split_prob)
            eject_dist = Bernoulli(eject_prob)

            move_lp = move_dist.log_prob(move_action).sum(dim=-1, keepdim=True)
            split_lp = split_dist.log_prob(split_action)
            eject_lp = eject_dist.log_prob(eject_action)

            tot_lp = move_lp + split_lp + eject_lp

            tot_entropy = (
                move_dist.entropy().sum(dim=-1, keepdim=True)
                + split_dist.entropy()
                + eject_dist.entropy()
            )

            log_probs.append(tot_lp)
            values.append(val)
            entropies.append(tot_entropy)

        log_probs = torch.stack(log_probs, dim=0)
        values = torch.stack(values, dim=0)
        entropies = torch.stack(entropies, dim=0)

        return log_probs, values, entropies
