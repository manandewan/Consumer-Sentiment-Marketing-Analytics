import math
import numpy as np


class Cell:
    """Represents a single player sub-cell in Agar.io."""

    MIN_MASS = 10.0
    SPLIT_MIN_MASS = 36.0

    def __init__(self, cell_id, player_id, x, y, mass=10.0, vx=0.0, vy=0.0):
        self.id = cell_id
        self.player_id = player_id
        self.x = float(x)
        self.y = float(y)
        self.mass = float(mass)
        self.vx = float(vx)
        self.vy = float(vy)
        self.radius = self.calc_radius(self.mass)
        self.merge_cooldown = 0.0  # seconds until this cell can merge with sibling cells

    @staticmethod
    def calc_radius(mass):
        return math.sqrt(max(1.0, mass) * 100.0)

    def update_radius(self):
        self.radius = self.calc_radius(self.mass)

    def get_max_speed(self):
        # Larger mass = slower movement speed
        return 20.0 * (self.mass ** -0.44) * 10.0

    def step(self, target_x, target_y, dt=0.05, map_width=2000.0, map_height=2000.0):
        # Update cooldown
        if self.merge_cooldown > 0:
            self.merge_cooldown = max(0.0, self.merge_cooldown - dt)

        # Apply impulse velocity decay (friction)
        drag = 0.90
        self.vx *= drag
        self.vy *= drag

        # Compute direction vector towards target
        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.hypot(dx, dy)

        if dist > 1e-4:
            nx = dx / dist
            ny = dy / dist
            max_speed = self.get_max_speed()
            # Accelerate towards target
            accel = 300.0 * dt
            self.vx += nx * accel
            self.vy += ny * accel

            # Clamp speed if not boosting from split
            speed = math.hypot(self.vx, self.vy)
            if speed > max_speed and math.hypot(self.vx, self.vy) < max_speed * 3:
                scale = max_speed / speed
                self.vx *= scale
                self.vy *= scale

        # Position update
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Map boundary collision
        self.x = max(self.radius, min(map_width - self.radius, self.x))
        self.y = max(self.radius, min(map_height - self.radius, self.y))


class Virus:
    """Represents a Virus entity on the board."""

    def __init__(self, virus_id, x, y, mass=100.0):
        self.id = virus_id
        self.x = float(x)
        self.y = float(y)
        self.mass = float(mass)
        self.radius = math.sqrt(self.mass * 100.0)
        self.fed_count = 0

    def feed(self, mass_added=12.0):
        self.fed_count += 1
        self.mass += mass_added
        self.radius = math.sqrt(self.mass * 100.0)
        if self.fed_count >= 7:
            self.fed_count = 0
            self.mass = 100.0
            self.radius = math.sqrt(self.mass * 100.0)
            return True  # Split/shoot new virus
        return False


class EjectedMass:
    """Represents mass ejected by a player (W key)."""

    def __init__(self, eject_id, player_id, x, y, vx, vy, mass=12.0):
        self.id = eject_id
        self.player_id = player_id
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.mass = float(mass)
        self.radius = math.sqrt(self.mass * 100.0)

    def step(self, dt=0.05, map_width=2000.0, map_height=2000.0):
        self.vx *= 0.85
        self.vy *= 0.85
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x = max(self.radius, min(map_width - self.radius, self.x))
        self.y = max(self.radius, min(map_height - self.radius, self.y))


class Food:
    """Represents a passive food pellet."""

    def __init__(self, food_id, x, y, mass=1.0):
        self.id = food_id
        self.x = float(x)
        self.y = float(y)
        self.mass = float(mass)
        self.radius = math.sqrt(self.mass * 100.0)


class AgarPhysics:
    """Core physics engine for vectorized Agar.io simulation."""

    def __init__(self, map_width=2000.0, map_height=2000.0, max_food=500, max_viruses=15):
        self.map_width = map_width
        self.map_height = map_height
        self.max_food = max_food
        self.max_viruses = max_viruses
        self.cell_id_counter = 0
        self.virus_id_counter = 0
        self.eject_id_counter = 0
        self.food_id_counter = 0

    def create_cell(self, player_id, x, y, mass=10.0, vx=0.0, vy=0.0):
        self.cell_id_counter += 1
        return Cell(self.cell_id_counter, player_id, x, y, mass, vx, vy)

    def create_virus(self, x, y, mass=100.0):
        self.virus_id_counter += 1
        return Virus(self.virus_id_counter, x, y, mass)

    def create_ejected_mass(self, player_id, x, y, vx, vy, mass=12.0):
        self.eject_id_counter += 1
        return EjectedMass(self.eject_id_counter, player_id, x, y, vx, vy, mass)

    def spawn_food(self, current_food_list):
        needed = self.max_food - len(current_food_list)
        if needed <= 0:
            return current_food_list
        
        xs = np.random.uniform(20.0, self.map_width - 20.0, size=needed)
        ys = np.random.uniform(20.0, self.map_height - 20.0, size=needed)
        for i in range(needed):
            self.food_id_counter += 1
            current_food_list.append(Food(self.food_id_counter, xs[i], ys[i]))
        return current_food_list

    def spawn_viruses(self, current_virus_list):
        needed = self.max_viruses - len(current_virus_list)
        if needed <= 0:
            return current_virus_list

        xs = np.random.uniform(100.0, self.map_width - 100.0, size=needed)
        ys = np.random.uniform(100.0, self.map_height - 100.0, size=needed)
        for i in range(needed):
            current_virus_list.append(self.create_virus(xs[i], ys[i]))
        return current_virus_list

    def split_cell(self, cell, target_x, target_y, player_cells):
        """Splits a cell in half in the direction of (target_x, target_y)."""
        if cell.mass < Cell.SPLIT_MIN_MASS or len(player_cells) >= 16:
            return None

        split_mass = cell.mass / 2.0
        cell.mass = split_mass
        cell.update_radius()

        dx = target_x - cell.x
        dy = target_y - cell.y
        dist = math.hypot(dx, dy)
        if dist < 1e-4:
            nx, ny = 1.0, 0.0
        else:
            nx, ny = dx / dist, dy / dist

        boost_speed = 600.0
        vx = nx * boost_speed
        vy = ny * boost_speed

        new_x = cell.x + nx * cell.radius
        new_y = cell.y + ny * cell.radius
        new_cell = self.create_cell(cell.player_id, new_x, new_y, split_mass, vx, vy)
        
        cooldown = 18.0 + split_mass * 0.02
        cell.merge_cooldown = cooldown
        new_cell.merge_cooldown = cooldown
        return new_cell

    def eject_mass(self, cell, target_x, target_y):
        """Ejects mass from cell (W key)."""
        if cell.mass < 36.0:
            return None

        cell.mass -= 16.0
        cell.update_radius()

        dx = target_x - cell.x
        dy = target_y - cell.y
        dist = math.hypot(dx, dy)
        if dist < 1e-4:
            nx, ny = 1.0, 0.0
        else:
            nx, ny = dx / dist, dy / dist

        vx = nx * 500.0
        vy = ny * 500.0
        start_x = cell.x + nx * (cell.radius + 10.0)
        start_y = cell.y + ny * (cell.radius + 10.0)

        return self.create_ejected_mass(cell.player_id, start_x, start_y, vx, vy)

    def handle_virus_collision(self, cell, virus, player_cells):
        """Pops a cell when touching a virus if cell mass > virus mass."""
        if cell.mass <= virus.mass * 1.15:
            return False  # Small cell can hide under virus

        # Cell pops into multiple smaller pieces up to max 16 cells per player
        max_splits = min(16 - len(player_cells), 8)
        if max_splits <= 0:
            return False

        piece_mass = max(Cell.MIN_MASS, cell.mass / (max_splits + 1))
        cell.mass = piece_mass
        cell.update_radius()

        for i in range(max_splits):
            angle = (2.0 * math.pi / max_splits) * i
            nx, ny = math.cos(angle), math.sin(angle)
            vx, vy = nx * 400.0, ny * 400.0
            new_cell = self.create_cell(
                cell.player_id,
                cell.x + nx * cell.radius,
                cell.y + ny * cell.radius,
                piece_mass,
                vx, vy
            )
            new_cell.merge_cooldown = 20.0
            player_cells.append(new_cell)

        cell.merge_cooldown = 20.0
        return True
