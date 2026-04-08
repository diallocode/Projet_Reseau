from abc import ABC, abstractmethod
import math


class Strategy(ABC):
    """
    Abstract base class for strategies.
    
    Provides core utilities for unit navigation, enemy targeting, 
    and spatial management during the battle.
    """

    @abstractmethod
    def play(self,general, battlefield):
        """Execute the strategy logic for all units of the given general."""
        pass


    MIN_SEPARATION = 1.0  # Minimum allowed distance between allied units (Hérité de Daft)
    
    def _find_nearest_enemy(self, unit, battlefield):
        enemies = [e for e in battlefield.get_enemy_units(unit) if e.is_alive()]
        if not enemies: return None
        return min(enemies, key=lambda e: unit.distance_to(e))
   
   

    def _find_free_position(self, base_pos, assigned_positions, battlefield):
        """
        Calculates a nearby valid position to avoid unit overlapping.
        Uses a radial search to maintain MIN_SEPARATION from already assigned spots.
        """
        bx, by = base_pos
        radius = 0
        step = 0.3          # Radial search increment
        max_radius = 3.0    # Maximum search radius (prevents large detours)

        while radius <= max_radius:
            # Test several angular offsets around the base position
            for angle in range(0, 360, 20):
                rad = math.radians(angle)
                x = bx + math.cos(rad) * radius
                y = by + math.sin(rad) * radius
                candidate = (x, y)

                if not battlefield.is_valid_position(candidate):
                    continue

                # Ensure candidate is not too close to any assigned position
                too_close = any(
                    math.hypot(x - px, y - py) < self.MIN_SEPARATION
                    for px, py in assigned_positions
                )
                if not too_close:
                    return candidate

            radius += step

        # Fallback: use the original position if no free spot found
        return base_pos

  
    def _find_nearest_enemy(self, unit, battlefield):
        enemies = [e for e in battlefield.get_enemy_units(unit) if e.is_alive()]
        if not enemies: return None
        return min(enemies, key=lambda e: unit.distance_to(e))
    
