from abc import ABC, abstractmethod
from dataclasses import dataclass
import math
from model.Battlefield import Battlefield
import random
from Constant import STATS_BONUS_FILEPATH, EPSILON, K_ELEVATION_H, K_ELEVATION_D
from util.CSVLoader import CSVLoader


BONUS_DAMAGE_MATRIX = CSVLoader().load_bonus_armor_matrix(STATS_BONUS_FILEPATH)
BONUS_AMOR_MATRIX = CSVLoader().load_bonus_damage_matrix(STATS_BONUS_FILEPATH)


@dataclass
class Unit(ABC):
    """Abstract base class representing an RTS unit with real-time movement and combat logic."""

    id: int
    name: str
    symbol: str
    hp: int
    type_attack: str                # "melee" or "ranged"
    attack: int
    armor: int
    pierce_armor: int
    range: float                    # Attack range
    line_of_sight: float
    speed: float                    # Movement speed
    attack_delay: float             # Time until next attack
    reload_time: float              # Attack cooldown
    accuracy: float                 # Probability of successful hit
    position: tuple[float, float]   # (x, y)

    current_order: str = None       # "move" or "attack"
    target_unit: "Unit" = None
    target_pos: tuple[float, float] = None
    battlefield:Battlefield = None
    
    last_attacker: "Unit" = None    # Unit that last attacked this unit (for Braindead strategy)

    # ------------------------------------------------------------------
    # CORE STATUS & UTILITY
    # ------------------------------------------------------------------
    def is_alive(self):
        """Check if the unit's hit points are above zero."""
        return self.hp > 0

    def take_damage(self, damage, attacker=None):
        """Reduce HP by damage amount and clear orders if the unit dies."""
        self.hp -= damage
        self.last_attacker = attacker

        if self.hp <= 0:
            self.hp = 0
            self.current_order = None
            self.target_unit = None
            self.target_pos = None

    def set_order(self, order_type: str, target=None, target_pos=None):
        """Assign a new 'move' or 'attack' command with associated targets."""
        self.current_order = order_type
        self.target_unit = target
        self.target_pos = target_pos

    def has_active_order(self):
        """Check if the unit currently has a pending command."""
        return self.current_order is not None

    # ------------------------------------------------------------------
    # UPDATE LOOP
    # ------------------------------------------------------------------
    def update(self, dt):
        """Advance unit logic (cooldowns, movement, or combat) based on elapsed time."""
        if not self.is_alive():
            return

        # Cooldown reduction
        if self.attack_delay > 0:
            self.attack_delay -= dt

        # Order execution
        if self.current_order == "move":
            self._update_move(dt)

        elif self.current_order == "attack":
            self._update_attack(dt)

    # ------------------------------------------------------------------
    # MOVEMENT
    # ------------------------------------------------------------------
    def _update_move(self, dt):
        """
        Execute movement toward target_pos.
        Includes slope speed penalties and basic lateral obstacle avoidance.
        """
        if not self.target_pos:
            self.current_order = None
            return

        x, y = self.position
        tx, ty = self.target_pos

        # Direction vector
        dir_x = tx - x
        dir_y = ty - y
        dist = math.hypot(dir_x, dir_y)

        if dist <= EPSILON:
            # Already at destination
            self.position = (tx, ty)
            self.current_order = None
            return

        # Normalize direction
        dir_x /= dist
        dir_y /= dist

        # Calculate tentative new position
        step = self.speed * dt
        new_x = x + dir_x * step
        new_y = y + dir_y * step

        # --- Adjust step for elevation ---
        current_height = self.battlefield.get_height(x, y)
        new_height = self.battlefield.get_height(new_x, new_y)
        height_diff = new_height - current_height
        
        # Speed adjusted according to slope (slowing down on uphill slopes, no acceleration on downhill slopes)
        if height_diff > 0:

            slope_factor = 1 / (1 + height_diff)  # Simple model, can tune
            step *= slope_factor
            new_x = x + dir_x * step
            new_y = y + dir_y * step

        new_pos = (new_x, new_y)

                # Tentative directe
        if self._try_move(new_pos):
            return

        # === Lateral avoidance ===
        # Perpendicular vector
        perp_x = -dir_y
        perp_y = dir_x

        # Intensity of avoidance
        side_step = step * 0.7

        # Left
        left_pos = (
            x + perp_x * side_step,
            y + perp_y * side_step
        )

        if self._try_move(left_pos):
            return

        # Right
        right_pos = (
            x - perp_x * side_step,
            y - perp_y * side_step
        )

        if self._try_move(right_pos):
            return

    def _try_move(self, new_pos):
        """
        Applique le mouvement si la position est valide et libre.
        """
        # Safety: The position must be within limits.
        if not self.battlefield.is_valid_position(new_pos):
            return False

        # Collision detection
        blocker = self.battlefield.get_unit_at(new_pos)
        
        # If a blocker is found and it is not us
        if blocker and blocker.id != self.id:
            if blocker.is_alive() and self.is_enemy(blocker):
                # Automatic engagement if it is an enemy
                self.set_order("attack", target=blocker)
            return False # We stop no matter what (ally or enemy)
            
        self.position = new_pos
        return True

    def is_enemy(self, other: "Unit") -> bool:
        """Determine if another unit belongs to the opposing team based on ID."""
        return (self.id // 1000) != (other.id // 1000)
    # ------------------------------------------------------------------
    # ATTACKING
    # ------------------------------------------------------------------
    def _update_attack(self, dt):
        """Handle attack state: monitor target status and trigger attacks when ready."""
        target = self.target_unit
        if not target or not target.is_alive() or not target.position:
            self.current_order = None
            self.target_unit = None
            return
        # In range → attack when cooldown ready
        if self.attack_delay <= 0:
            self._try_attack(target)
            self.attack_delay = self.reload_time

    def _try_attack(self, target):
        """Execute an attack roll and apply damage if the hit is successful."""
        if not target or not target.is_alive() or not target.position:
            return
        if random.random() <= self.accuracy:
            damage = self.compute_damage(self, target)
            target.take_damage(damage, attacker=self)


    def distance_to(self, other_unit):
        """Calculate the Euclidean distance to another unit.""" 
        x, y = self.position
        ox, oy = other_unit.position
        return math.hypot(x - ox, y - oy)

    def compute_damage(self, attacker, defender):
        """
        Calculate final damage considering base stats, type bonuses, 
        armor mitigation, and elevation modifiers.
        """
        base_damage = attacker.attack
        damage_bonus = BONUS_DAMAGE_MATRIX[attacker.name][defender.name]
        armor_bonus = BONUS_DAMAGE_MATRIX[defender.name][attacker.name]

        if attacker.type_attack == "melee":
            armor_value = defender.armor
        else:
            armor_value = defender.pierce_armor

        raw_damage = max(
            0.0,
            (base_damage + damage_bonus) - (armor_value + armor_bonus)
        )

        attacker_h = self.battlefield.get_height(*attacker.position)
        defender_h = self.battlefield.get_height(*defender.position)

        if attacker_h > defender_h:
            raw_damage *= K_ELEVATION_H
        elif attacker_h < defender_h:
            raw_damage *= K_ELEVATION_D

        return raw_damage

    def __repr__(self):
        """Return a readable summary of the unit for debugging."""
        return f"{self.name} {self.id} ({self.hp}hp @ {self.position})"
