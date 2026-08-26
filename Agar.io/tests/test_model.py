import unittest
import torch
from models.recurrent_ppo import RecurrentPPOActorCritic


class TestRecurrentPPO(unittest.TestCase):

    def setUp(self):
        self.model = RecurrentPPOActorCritic(obs_dim=512, hidden_dim=256)

    def test_forward_and_action(self):
        obs = torch.randn(4, 512)
        lstm_state = self.model.init_lstm_state(batch_size=4)
        actions, log_probs, values, next_lstm = self.model.get_action(obs, lstm_state)

        self.assertEqual(actions.shape, (4, 4))
        self.assertEqual(log_probs.shape, (4, 1))
        self.assertEqual(values.shape, (4, 1))
        self.assertEqual(next_lstm[0].shape, (4, 256))

    def test_evaluate_actions(self):
        obs_seq = torch.randn(16, 4, 512)
        action_seq = torch.randn(16, 4, 4)
        init_lstm = self.model.init_lstm_state(batch_size=4)

        log_probs, values, entropies = self.model.evaluate_actions(obs_seq, init_lstm, action_seq)

        self.assertEqual(log_probs.shape, (16, 4, 1))
        self.assertEqual(values.shape, (16, 4, 1))
        self.assertEqual(entropies.shape, (16, 4, 1))


if __name__ == "__main__":
    unittest.main()
