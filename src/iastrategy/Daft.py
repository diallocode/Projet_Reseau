import math
from iastrategy.Strategy import Strategy
from Constant import EPSILON, UNIT_RADIUS


class Daft(Strategy):
    """
    A basic aggressive AI strategy focusing on proximity-based engagement.

    The Daft strategy follows a 'nearest-neighbor' logic: every unit 
    independently identifies the closest hostile target and attempts 
    to close the distance or attack.

    Rules:
    1. If a unit is already attacking a living target, it maintains the order.
    2. If idle, it targets the nearest enemy unit on the battlefield.
    3. If the target is within range, it initiates an attack.
    4. If the target is out of range, it moves directly toward the enemy's position.
    """


    def __repr__(self):
        """Returns the identifier string 'Daft' for logging and UI."""
        return "Daft"

    def play(self, general, battlefield):
        """
        Orchestrates unit behavior for the given general.
        
        Calculates distances for melee (using unit radius) and ranged 
        units to decide between issuing 'move' or 'attack' commands.
        """

        for unit in general.get_my_units(battlefield):

            if not unit.is_alive():
                continue

            if unit.current_order == "attack" and unit.target_unit and unit.target_unit.is_alive():
                continue

            target = self._find_nearest_enemy(unit, battlefield)
            if not target:
                continue

            dist = unit.distance_to(target)
            contact_range = unit.range + UNIT_RADIUS*2
            
            if dist <= contact_range + EPSILON:
                unit.set_order("attack", target=target)
                continue

            tx, ty = target.position
            unit.set_order("move", target_pos=(tx, ty))
