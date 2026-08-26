import math
import numpy as np
try:
    import gymnasium as gym
    from gymnasium import spaces
    from pettingzoo import ParallelEnv
except ImportError:
    # Lightweight self-contained fallback for environment spaces
    class DummySpace:
        def __init__(self, low=None, high=None, shape=None, dtype=None):
            self.low = low
            self.high = high
            self.shape = shape if shape is not None else (len(low) if hasattr(low, '__len__') else ())
            self.dtype = dtype

    class DummySpacesModule:
        Box = DummySpace

    spaces = DummySpacesModule()

    class ParallelEnv:
        """Base fallback for PettingZoo ParallelEnv."""
        pass


from environment.physics import AgarPhysics, Cell, Virus, Food, EjectedMass


class AgarioEnv(ParallelEnv):
    """
    Vectorized Multi-Agent Agar.io Environment following PettingZoo Parallel API standard.
    """

    metadata = {"name": "agario_v0", "render_modes": ["human", "rgb_array"]}
    OBS_DIM = 512

    def __init__(
        self,
        num_agents=16,
        map_width=2000.0,
        map_height=2000.0,
        max_food=500,
        max_viruses=15,
        max_steps=1000,
        dt=0.05,
    ):
        super().__init__()
        self.num_agents = num_agents
        self.map_width = map_width
        self.map_height = map_height
        self.max_food = max_food
        self.max_viruses = max_viruses
        self.max_steps = max_steps
        self.dt = dt

        self.physics = AgarPhysics(
            map_width=map_width,
            map_height=map_height,
            max_food=max_food,
            max_viruses=max_viruses,
        )

        self.possible_agents = [f"agent_{i}" for i in range(num_agents)]
        self.agents = list(self.possible_agents)

        # Action space per agent: Box continuous [dx, dy, split, eject]
        # dx, dy in [-1, 1], split in [0, 1] (threshold > 0.5), eject in [0, 1] (threshold > 0.5)
        self.action_spaces = {
            agent: spaces.Box(
                low=np.array([-1.0, -1.0, 0.0, 0.0], dtype=np.float32),
                high=np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32),
                dtype=np.float32,
            )
            for agent in self.possible_agents
        }

        # Observation space per agent: Continuous vector 256 floats
        self.observation_spaces = {
            agent: spaces.Box(
                low=-10.0,
                high=10.0,
                shape=(self.OBS_DIM,),
                dtype=np.float32,
            )
            for agent in self.possible_agents
        }

        # Game State
        self.player_cells = {}      # agent_id -> list of Cell objects
        self.food_pellets = []       # list of Food objects
        self.viruses = []            # list of Virus objects
        self.ejected_masses = []     # list of EjectedMass objects
        self.step_count = 0
        self.agent_mass_history = {} # agent_id -> float

    def reset(self, seed=None, options=None):
        if seed is not None:
            np.random.seed(seed)

        self.agents = list(self.possible_agents)
        self.step_count = 0

        self.player_cells = {}
        self.agent_mass_history = {}
        self.food_pellets = []
        self.viruses = []
        self.ejected_masses = []

        # Spawn initial food & viruses
        self.food_pellets = self.physics.spawn_food([])
        self.viruses = self.physics.spawn_viruses([])

        # Spawn player initial cell
        for agent in self.agents:
            x = np.random.uniform(100.0, self.map_width - 100.0)
            y = np.random.uniform(100.0, self.map_height - 100.0)
            cell = self.physics.create_cell(agent, x, y, mass=20.0)
            self.player_cells[agent] = [cell]
            self.agent_mass_history[agent] = 20.0

        observations = {agent: self._get_obs(agent) for agent in self.agents}
        infos = {agent: {} for agent in self.agents}

        return observations, infos

    def _get_agent_center_and_mass(self, agent):
        cells = self.player_cells.get(agent, [])
        if not cells:
            return 0.0, 0.0, 0.0
        total_mass = sum(c.mass for c in cells)
        cx = sum(c.x * c.mass for c in cells) / total_mass
        cy = sum(c.y * c.mass for c in cells) / total_mass
        return cx, cy, total_mass

    def _get_obs(self, agent):
        obs = np.zeros(self.OBS_DIM, dtype=np.float32)
        cells = self.player_cells.get(agent, [])
        if not cells:
            return obs

        cx, cy, total_mass = self._get_agent_center_and_mass(agent)
        view_dist = 600.0

        # Primary cell
        primary = max(cells, key=lambda c: c.mass)

        # 1. Self Status & Multi-Cell Dynamics (14 floats)
        num_cells = len(cells)
        ready_mass = sum(c.mass for c in cells if c.merge_cooldown <= 0.0)
        phi_merge = ready_mass / max(1.0, total_mass)

        weighted_cooldown = sum(c.mass * c.merge_cooldown for c in cells) / (30.0 * max(1.0, total_mass))
        variance_dist = sum(c.mass * ((c.x - cx)**2 + (c.y - cy)**2) for c in cells) / max(1.0, total_mass)
        r_spread = math.sqrt(max(0.0, variance_dist)) / view_dist

        hhi_mass = sum((c.mass / max(1.0, total_mass))**2 for c in cells)
        min_mass = min(c.mass for c in cells)
        max_mass = max(c.mass for c in cells)
        mass_contrast = min_mass / max(1.0, max_mass)

        # 4-Wall Proximity & Corner Trapping Computation
        d_left = max(0.0, (cx - primary.radius) / self.map_width)
        d_right = max(0.0, (self.map_width - cx - primary.radius) / self.map_width)
        d_top = max(0.0, (cy - primary.radius) / self.map_height)
        d_bottom = max(0.0, (self.map_height - cy - primary.radius) / self.map_height)

        min_wall_dist = min(d_left, d_right, d_top, d_bottom)
        if min_wall_dist == d_left:
            nx_wall, ny_wall = 1.0, 0.0
        elif min_wall_dist == d_right:
            nx_wall, ny_wall = -1.0, 0.0
        elif min_wall_dist == d_top:
            nx_wall, ny_wall = 0.0, 1.0
        else:
            nx_wall, ny_wall = 0.0, -1.0

        dx_min = min(d_left, d_right)
        dy_min = min(d_top, d_bottom)
        corner_dist = math.hypot(dx_min, dy_min)
        c_corner = max(0.0, 1.0 - (corner_dist / 0.25))

        h_pin = 0.0
        for opp_id, opp_cells in self.player_cells.items():
            if opp_id == agent:
                continue
            for oc in opp_cells:
                if oc.mass >= primary.mass * 1.15:
                    d_opp = math.hypot(oc.x - cx, oc.y - cy)
                    if 1e-4 < d_opp <= view_dist:
                        rx_opp = (oc.x - cx) / d_opp
                        ry_opp = (oc.y - cy) / d_opp
                        pin_dot = rx_opp * nx_wall + ry_opp * ny_wall
                        if pin_dot > 0:
                            hazard = pin_dot * (1.0 - (d_opp / view_dist)) * (1.0 - min(1.0, min_wall_dist * 4.0))
                            if hazard > h_pin:
                                h_pin = hazard

        blocked_arc = (1.0 - min(1.0, min_wall_dist * 4.0)) * 0.5 + (0.25 if c_corner > 0.5 else 0.0) + (h_pin * 0.25)
        theta_escape = max(0.0, 1.0 - min(1.0, blocked_arc))

        # Mass Decay & Foraging Efficiency Computation
        decay_mass_per_tick = sum(0.0002 * c.mass for c in cells if c.mass > 20.0)
        decay_per_sec = decay_mass_per_tick * 20.0
        gamma_decay = decay_per_sec / max(1.0, total_mass)

        prev_mass = self.agent_mass_history.get(agent, total_mass)
        mass_delta_step = total_mass - prev_mass
        m_delta_norm = np.clip(mass_delta_step / (0.05 * max(1.0, total_mass) + 1.0), -1.0, 1.0)

        gross_intake = mass_delta_step + decay_mass_per_tick
        net_efficiency = math.tanh((gross_intake / (decay_mass_per_tick + 1e-4)) - 1.0)

        r_single = math.sqrt(max(1.0, total_mass) * 100.0)
        sum_radii = sum(c.radius for c in cells)
        kappa_sweep = min(4.0, sum_radii / max(1.0, r_single))
        kappa_sweep_norm = (kappa_sweep - 1.0) / 3.0

        # Mass Ejection & Baiting Trap Computation
        can_eject = 1.0 if primary.mass >= 36.0 else 0.0

        b_bait = 0.0
        split_mass = primary.mass / 2.0
        split_radius = math.sqrt(max(1.0, split_mass) * 100.0)
        split_reach = (primary.radius + 300.0 + split_radius) / view_dist

        for opp_id, opp_cells in self.player_cells.items():
            if opp_id == agent:
                continue
            for oc in opp_cells:
                if 0.3 * primary.mass <= oc.mass <= 0.8 * primary.mass:
                    d_opp = math.hypot(oc.x - cx, oc.y - cy) / view_dist
                    touch_d = (primary.radius + oc.radius) / view_dist
                    if touch_d < d_opp <= split_reach:
                        bait_val = 1.0 - (d_opp / max(1e-4, split_reach))
                        if bait_val > b_bait:
                            b_bait = bait_val

        f_transfer = (total_mass - primary.mass) / max(1.0, total_mass) if len(cells) >= 2 else 0.0

        d_eject_sum = 0.0
        for em in self.ejected_masses:
            d_em = math.hypot(em.x - cx, em.y - cy) / view_dist
            if d_em <= 1.0:
                d_eject_sum += (em.mass / 12.0) / (d_em + 0.1)
        d_eject_density = min(1.0, d_eject_sum / 20.0)

        # Global Server Leaderboard Rank & Arena Dominance Computation
        all_agent_masses = []
        for a_id in self.possible_agents:
            a_cells = self.player_cells.get(a_id, [])
            if a_cells:
                a_mass = sum(c.mass for c in a_cells)
                a_primary = max(a_cells, key=lambda c: c.mass)
                cx_a = sum(c.x * c.mass for c in a_cells) / a_mass
                cy_a = sum(c.y * c.mass for c in a_cells) / a_mass
                all_agent_masses.append((a_id, a_mass, cx_a, cy_a))

        all_agent_masses.sort(key=lambda item: item[1], reverse=True)

        total_arena_mass = sum(item[1] for item in all_agent_masses)
        leader_id, leader_mass, leader_cx, leader_cy = all_agent_masses[0] if all_agent_masses else (agent, total_mass, cx, cy)

        agent_rank = 1
        for rank_idx, (a_id, m, _, _) in enumerate(all_agent_masses):
            if a_id == agent:
                agent_rank = rank_idx + 1
                break

        r_rank = (agent_rank - 1) / max(1, len(all_agent_masses) - 1)
        is_leader = 1.0 if agent_rank == 1 else 0.0
        sigma_dominance = total_mass / max(1.0, total_arena_mass)
        r_leader_mass = total_mass / max(1.0, leader_mass)

        dx_leader = (leader_cx - cx) / view_dist
        dy_leader = (leader_cy - cy) / view_dist
        d_leader = math.hypot(leader_cx - cx, leader_cy - cy) / view_dist

        obs[0] = math.log(max(1.0, total_mass)) / 10.0
        obs[1] = num_cells / 16.0
        obs[2] = (cx / self.map_width) * 2.0 - 1.0
        obs[3] = (cy / self.map_height) * 2.0 - 1.0
        obs[4] = primary.vx / 500.0
        obs[5] = primary.vy / 500.0
        obs[6] = phi_merge                            # Fraction of mass ready to re-combine
        obs[7] = min(1.0, weighted_cooldown)          # Mass-weighted merge cooldown
        obs[8] = min(1.0, r_spread)                   # Spatial spread radius of gyration
        obs[9] = hhi_mass                             # Mass concentration / unified state index
        obs[10] = primary.radius / 300.0
        obs[11] = d_left                              # Left wall distance
        obs[12] = d_right                             # Right wall distance
        obs[13] = d_top                               # Top wall distance
        obs[14] = d_bottom                            # Bottom wall distance
        obs[15] = c_corner                            # Corner trap vulnerability metric [0, 1]
        obs[16] = h_pin                               # Opponent wall pinning hazard score [0, 1]
        obs[17] = theta_escape                        # Unobstructed directional escape arc [0, 1]
        obs[18] = gamma_decay * 250.0                 # Normalized mass decay rate [0, 1]
        obs[19] = m_delta_norm                        # Mass delta velocity [-1, 1]
        obs[20] = net_efficiency                      # Metabolic intake efficiency [-1, 1]
        obs[21] = kappa_sweep_norm                    # Multi-cell sweep width multiplier [0, 1]
        obs[22] = can_eject                           # Ejection capability flag [0, 1]
        obs[23] = b_bait                              # Baiting trap opportunity score [0, 1]
        obs[24] = f_transfer                          # Sibling fast-feed mass ratio [0, 1]
        obs[25] = d_eject_density                     # Ejected mass density potential [0, 1]
        obs[26] = r_rank                              # Normalized leaderboard rank [0, 1]
        obs[27] = is_leader                           # #1 Leader flag [0, 1]
        obs[28] = sigma_dominance                     # Arena mass dominance share [0, 1]
        obs[29] = r_leader_mass                       # Relative mass ratio vs #1 leader [0, 1]
        obs[30] = dx_leader                           # Relative dx to server leader
        obs[31] = dy_leader                           # Relative dy to server leader
        obs[32] = d_leader                            # Normalized distance to server leader

        idx = 33  # Self & Global status buffer end (jump to food at index 33)

        # 2. Food Pellets: 30 Nearest Pellets + 8-Sector Histogram + Macro Centroid (60 + 13 = 73 floats)
        food_dists = []
        h_food = np.zeros(8, dtype=np.float32)
        sum_gx, sum_gy = 0.0, 0.0
        food_x_sum, food_y_sum = 0.0, 0.0
        total_food_count = len(self.food_pellets)

        for f in self.food_pellets:
            fx_rel = f.x - cx
            fy_rel = f.y - cy
            d_pixels = math.hypot(fx_rel, fy_rel)
            d = d_pixels / view_dist

            if d <= 1.0:
                food_dists.append((d, fx_rel / view_dist, fy_rel / view_dist))

            food_x_sum += f.x
            food_y_sum += f.y

            denom = d_pixels**2 + 100.0
            sum_gx += fx_rel / denom
            sum_gy += fy_rel / denom

            angle = math.atan2(fy_rel, fx_rel)
            sector_idx = int(math.floor((angle + math.pi) / (math.pi / 4.0))) % 8
            weight = math.exp(-d_pixels / view_dist)
            h_food[sector_idx] += weight

        h_food = np.clip(h_food / 20.0, 0.0, 1.0)

        if total_food_count > 0:
            dx_food_cm = (food_x_sum / total_food_count - cx) / self.map_width
            dy_food_cm = (food_y_sum / total_food_count - cy) / self.map_height
        else:
            dx_food_cm, dy_food_cm = 0.0, 0.0

        g_norm = math.hypot(sum_gx, sum_gy)
        if g_norm > 1e-4:
            gx_food, gy_food = sum_gx / g_norm, sum_gy / g_norm
        else:
            gx_food, gy_food = 0.0, 0.0

        rho_local_food = min(1.0, len(food_dists) / 30.0)

        food_dists.sort(key=lambda item: item[0])
        for d, dx, dy in food_dists[:30]:
            obs[idx] = dx
            obs[idx + 1] = dy
            idx += 2

        # Fill 13 Macro Food Density floats
        for k in range(8):
            obs[idx + k] = h_food[k]
        obs[idx + 8] = dx_food_cm
        obs[idx + 9] = dy_food_cm
        obs[idx + 10] = gx_food
        obs[idx + 11] = gy_food
        obs[idx + 12] = rho_local_food

        idx = 106  # Jump to food buffer end (33 + 60 + 13 = 106)

        # 3. Top 10 Nearest Viruses (10 * 6 = 60 floats)
        virus_dists = []
        for v in self.viruses:
            dx = (v.x - cx) / view_dist
            dy = (v.y - cy) / view_dist
            d = math.hypot(dx, dy)
            if d <= 1.5:
                fed_ratio = getattr(v, 'fed_count', 0) / 7.0
                touch_radius = primary.radius + v.radius
                dist_pixels = d * view_dist

                if primary.mass <= v.mass:
                    v_threat = 1.0  # Safe sanctuary shield
                elif primary.mass > v.mass * 1.15:
                    v_threat = -max(0.0, 1.0 - (dist_pixels / max(1.0, touch_radius)))
                else:
                    v_threat = 0.0

                # Virus Sniping collinearity alignment with nearest vulnerable opponent
                snipe_align = 0.0
                dist_to_v = math.hypot(v.x - cx, v.y - cy)
                if dist_to_v > 1e-4:
                    ux, uy = (v.x - cx) / dist_to_v, (v.y - cy) / dist_to_v
                    best_dot = 0.0
                    for opp_id, opp_cells in self.player_cells.items():
                        if opp_id == agent:
                            continue
                        for oc in opp_cells:
                            if oc.mass > v.mass * 1.15:
                                v_to_opp_d = math.hypot(oc.x - v.x, oc.y - v.y)
                                if 1e-4 < v_to_opp_d <= 800.0:
                                    wx, wy = (oc.x - v.x) / v_to_opp_d, (oc.y - v.y) / v_to_opp_d
                                    dot = ux * wx + uy * wy
                                    if dot > best_dot:
                                        best_dot = dot
                    snipe_align = max(0.0, best_dot)

                virus_dists.append((d, dx, dy, v.mass / 100.0, fed_ratio, v_threat, snipe_align))

        virus_dists.sort(key=lambda item: item[0])
        for d, dx, dy, vm, fed_ratio, v_threat, snipe_align in virus_dists[:10]:
            obs[idx] = dx
            obs[idx + 1] = dy
            obs[idx + 2] = vm
            obs[idx + 3] = fed_ratio
            obs[idx + 4] = v_threat
            obs[idx + 5] = snipe_align
            idx += 6
        idx = 166  # Jump to virus buffer end (106 + 60 = 166)

        # 4. Top 16 Nearest Opponent Cells (16 * 12 = 192 floats)
        opp_dists = []
        for opp_id, opp_cells in self.player_cells.items():
            if opp_id == agent or not opp_cells:
                continue
            for oc in opp_cells:
                dx = (oc.x - cx) / view_dist
                dy = (oc.y - cy) / view_dist
                d_pixels = math.hypot(oc.x - cx, oc.y - cy)
                d = d_pixels / view_dist
                if d <= 2.0:
                    m_ratio = oc.mass / max(1.0, primary.mass)
                    eat_flag = 1.0 if primary.mass >= oc.mass * 1.15 else (-1.0 if oc.mass >= primary.mass * 1.15 else 0.0)

                    # Split-Kill Reach Signal
                    split_mass = primary.mass / 2.0
                    split_radius = math.sqrt(max(1.0, split_mass) * 100.0)
                    split_reach = (primary.radius + 300.0 + split_radius) / view_dist
                    can_split_eat = (primary.mass >= 36.0) and (split_mass >= oc.mass * 1.15)

                    opp_split_mass = oc.mass / 2.0
                    opp_split_radius = math.sqrt(max(1.0, opp_split_mass) * 100.0)
                    opp_split_reach = (oc.radius + 300.0 + opp_split_radius) / view_dist
                    can_be_split_eaten = (oc.mass >= 36.0) and (opp_split_mass >= primary.mass * 1.15)

                    split_kill_sig = 0.0
                    if can_split_eat and d <= split_reach:
                        split_kill_sig = 1.0 - (d / max(1e-4, split_reach))
                    elif can_be_split_eaten and d <= opp_split_reach:
                        split_kill_sig = -1.0 + (d / max(1e-4, opp_split_reach))

                    # Motion & Vector Interception Signals
                    rel_vx = (oc.vx - primary.vx) / 500.0
                    rel_vy = (oc.vy - primary.vy) / 500.0

                    rx = dx / max(1e-4, d)
                    ry = dy / max(1e-4, d)

                    v_closing = -(rel_vx * rx + rel_vy * ry)

                    net_closing_speed = 600.0 - (v_closing * 500.0)
                    tau_intercept = min(2.0, d_pixels / max(100.0, net_closing_speed))

                    x_lead = oc.x + oc.vx * tau_intercept
                    y_lead = oc.y + oc.vy * tau_intercept
                    dx_lead = (x_lead - cx) / view_dist
                    dy_lead = (y_lead - cy) / view_dist

                    opp_dists.append((
                        d, dx, dy, m_ratio, eat_flag, oc.vx / 500.0, oc.vy / 500.0,
                        split_kill_sig, rel_vx, rel_vy, v_closing, dx_lead, dy_lead
                    ))

        opp_dists.sort(key=lambda item: item[0])
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
        idx = 338  # Jump to opp buffer end (146 + 192 = 338)

        # 5. Top 5 Ejected Mass Pellets (5 * 3 = 15 floats)
        eject_dists = []
        for em in self.ejected_masses:
            dx = (em.x - cx) / view_dist
            dy = (em.y - cy) / view_dist
            d = math.hypot(dx, dy)
            if d <= 1.0:
                eject_dists.append((d, dx, dy, em.mass / 12.0))
        eject_dists.sort(key=lambda item: item[0])
        for d, dx, dy, em_m in eject_dists[:5]:
            if idx + 3 <= self.OBS_DIM:
                obs[idx] = dx
                obs[idx + 1] = dy
                obs[idx + 2] = em_m
                idx += 3

        return obs

    def step(self, actions):
        self.step_count += 1
        rewards = {agent: 0.0 for agent in self.agents}
        terminations = {agent: False for agent in self.agents}
        truncations = {agent: False for agent in self.agents}
        infos = {agent: {} for agent in self.agents}

        # Compute pre-step distance metrics for dense potential-based reward shaping
        prev_food_dists = {}
        prev_predator_dists = {}
        for agent in self.agents:
            if agent in self.player_cells and self.player_cells[agent]:
                cx, cy, total_m = self._get_agent_center_and_mass(agent)

                # Distance to nearest food pellet
                if self.food_pellets:
                    min_f_d = min(math.hypot(f.x - cx, f.y - cy) for f in self.food_pellets)
                    prev_food_dists[agent] = min_f_d

                # Distance to nearest larger predator cell
                pred_dists = []
                for opp_id, opp_cells in self.player_cells.items():
                    if opp_id == agent:
                        continue
                    for oc in opp_cells:
                        if oc.mass >= total_m * 1.15:
                            pred_dists.append(math.hypot(oc.x - cx, oc.y - cy))
                if pred_dists:
                    prev_predator_dists[agent] = min(pred_dists)

        # Step 1: Process Agent Actions
        for agent, act in actions.items():
            if agent not in self.player_cells or not self.player_cells[agent]:
                continue

            dx, dy, split_val, eject_val = act[0], act[1], act[2], act[3]
            cx, cy, _ = self._get_agent_center_and_mass(agent)

            # Target position
            target_x = cx + dx * 600.0
            target_y = cy + dy * 600.0

            # Step cells movement
            cells = list(self.player_cells[agent])
            for c in cells:
                c.step(target_x, target_y, dt=self.dt, map_width=self.map_width, map_height=self.map_height)

            # Handle Split action
            if split_val > 0.5:
                new_cells = []
                for c in cells:
                    new_c = self.physics.split_cell(c, target_x, target_y, self.player_cells[agent])
                    if new_c:
                        new_cells.append(new_c)
                self.player_cells[agent].extend(new_cells)
                rewards[agent] -= 0.02  # Action cost for splitting

            # Handle Eject Mass action
            if eject_val > 0.5:
                for c in cells:
                    em = self.physics.eject_mass(c, target_x, target_y)
                    if em:
                        self.ejected_masses.append(em)
                rewards[agent] -= 0.02  # Action cost for ejecting mass

        # Step 2: Step Ejected Mass physics
        for em in self.ejected_masses:
            em.step(dt=self.dt, map_width=self.map_width, map_height=self.map_height)

        # Step 3: Same-Player Sibling Cell Merging
        for agent, cells in self.player_cells.items():
            if len(cells) <= 1:
                continue
            merged = []
            skip_indices = set()
            for i in range(len(cells)):
                if i in skip_indices:
                    continue
                c1 = cells[i]
                for j in range(i + 1, len(cells)):
                    if j in skip_indices:
                        continue
                    c2 = cells[j]
                    if c1.merge_cooldown == 0.0 and c2.merge_cooldown == 0.0:
                        dist = math.hypot(c1.x - c2.x, c1.y - c2.y)
                        if dist < (c1.radius + c2.radius) * 0.7:
                            # Merge c2 into c1
                            c1.mass += c2.mass
                            c1.update_radius()
                            skip_indices.add(j)
                merged.append(c1)
            self.player_cells[agent] = merged

        # Step 4: Food Pellet Eating Collision
        remaining_food = []
        for f in self.food_pellets:
            eaten = False
            for agent, cells in self.player_cells.items():
                for c in cells:
                    dist = math.hypot(c.x - f.x, c.y - f.y)
                    if dist < c.radius:
                        c.mass += f.mass
                        c.update_radius()
                        rewards[agent] += 1.0  # Increased food reward to incentivize growth
                        eaten = True
                        break
                if eaten:
                    break
            if not eaten:
                remaining_food.append(f)
        self.food_pellets = remaining_food

        # Step 5: Virus Collision
        for agent, cells in list(self.player_cells.items()):
            new_player_cells = list(cells)
            for c in cells:
                for v in self.viruses:
                    dist = math.hypot(c.x - v.x, c.y - v.y)
                    if dist < c.radius + v.radius * 0.5:
                        popped = self.physics.handle_virus_collision(c, v, new_player_cells)
                        if popped:
                            rewards[agent] -= 2.0
            self.player_cells[agent] = new_player_cells

        # Step 6: Inter-Player Cell Consumption
        active_agents = list(self.player_cells.keys())
        for i in range(len(active_agents)):
            a1 = active_agents[i]
            cells1 = self.player_cells.get(a1, [])
            for j in range(len(active_agents)):
                if i == j:
                    continue
                a2 = active_agents[j]
                cells2 = self.player_cells.get(a2, [])
                for c1 in list(cells1):
                    for c2 in list(cells2):
                        if c1.mass >= c2.mass * 1.15:
                            dist = math.hypot(c1.x - c2.x, c1.y - c2.y)
                            if dist < c1.radius - c2.radius * 0.3:
                                # c1 eats c2
                                c1.mass += c2.mass
                                c1.update_radius()
                                rewards[a1] += 10.0 + (c2.mass * 0.15)
                                rewards[a2] -= 15.0
                                if c2 in cells2:
                                    cells2.remove(c2)

        # Step 7: Post-Step Potential-Based Reward Shaping & Survival Bonus
        for agent in self.agents:
            if agent in self.player_cells and self.player_cells[agent]:
                rewards[agent] += 0.01  # Survival step bonus

                cx, cy, total_m = self._get_agent_center_and_mass(agent)

                # Food Bee-Lining Potential Reward
                if agent in prev_food_dists and self.food_pellets:
                    curr_min_f_d = min(math.hypot(f.x - cx, f.y - cy) for f in self.food_pellets)
                    delta_f = prev_food_dists[agent] - curr_min_f_d
                    rewards[agent] += (delta_f / 600.0) * 5.0  # Dense positive reward for moving toward food

                # Predator Avoidance Potential Reward
                if agent in prev_predator_dists:
                    pred_dists = []
                    for opp_id, opp_cells in self.player_cells.items():
                        if opp_id == agent:
                            continue
                        for oc in opp_cells:
                            if oc.mass >= total_m * 1.15:
                                pred_dists.append(math.hypot(oc.x - cx, oc.y - cy))
                    if pred_dists:
                        curr_min_p_d = min(pred_dists)
                        delta_p = curr_min_p_d - prev_predator_dists[agent]
                        rewards[agent] += (delta_p / 600.0) * 8.0  # Positive for fleeing away, negative for approaching predator

        # Step 8: Mass Decay & Check Eliminations
        for agent in list(self.agents):
            cells = self.player_cells.get(agent, [])
            if not cells:
                terminations[agent] = True
                rewards[agent] -= 20.0
                infos[agent]["eliminated"] = True
            else:
                for c in cells:
                    if c.mass > 20.0:
                        c.mass *= 0.9998
                        c.update_radius()
                # Continuous mass delta reward
                _, _, curr_mass = self._get_agent_center_and_mass(agent)
                prev_mass = self.agent_mass_history.get(agent, 20.0)
                mass_delta = curr_mass - prev_mass
                rewards[agent] += mass_delta * 0.10
                self.agent_mass_history[agent] = curr_mass

        # Step 8: Respawn Food & Viruses
        self.food_pellets = self.physics.spawn_food(self.food_pellets)
        self.viruses = self.physics.spawn_viruses(self.viruses)

        # Check truncation
        is_truncated = self.step_count >= self.max_steps
        if is_truncated:
            for agent in self.agents:
                truncations[agent] = True

        # Filter out terminated agents
        self.agents = [a for a in self.agents if not (terminations[a] or truncations[a])]

        observations = {agent: self._get_obs(agent) for agent in self.possible_agents}

        return observations, rewards, terminations, truncations, infos
