import unittest
import numpy as np
from environment.agario_env import AgarioEnv


class TestAgarioEnv(unittest.TestCase):

    def setUp(self):
        self.env = AgarioEnv(num_agents=8, max_steps=50)

    def test_reset(self):
        obs, infos = self.env.reset(seed=42)
        self.assertEqual(len(obs), 8)
        for agent_id, ob in obs.items():
            self.assertEqual(ob.shape, (AgarioEnv.OBS_DIM,))

    def test_step(self):
        self.env.reset(seed=42)
        actions = {
            agent: np.array([0.5, -0.5, 0.0, 0.0], dtype=np.float32)
            for agent in self.env.agents
        }
        obs, rewards, terms, truncs, infos = self.env.step(actions)
        self.assertIn("agent_0", obs)
        self.assertIn("agent_0", rewards)


if __name__ == "__main__":
    unittest.main()
