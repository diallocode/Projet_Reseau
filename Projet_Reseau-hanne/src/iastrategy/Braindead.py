from iastrategy.Strategy import Strategy
from Constant import EPSILON, UNIT_RADIUS

class Braindead(Strategy):
    """
    Simple reactive strategy.

    Behavior:
    - If the unit is attacked, it retaliates against the attacker.
      - If the attacker is out of range, the unit moves toward it.
    - If not attacked, the unit attacks the nearest enemy only if it is in range.
    - Otherwise, the unit remains idle.
    """

    def __repr__(self) -> str:
        """Return the strategy name."""
        return "Braindead"

    def play(self, general, battlefield):
       
        for unit in general.get_my_units(battlefield):

            if not unit.is_alive():
                continue

            # Do not override a valid ongoing attack
            if (
                unit.current_order == "attack"
                and unit.target_unit
                and unit.target_unit.is_alive()
            ):
                continue

            # Reactive behavior: retaliate if attacked
            attacker = getattr(unit, "last_attacker", None)
            if attacker and attacker.is_alive():
                dist = unit.distance_to(attacker)
                contact_range = unit.range + UNIT_RADIUS * 2

                if dist <= contact_range + EPSILON:
                    unit.set_order("attack", target=attacker)
                else:
                    unit.set_order("move", target_pos=attacker.position)
                continue

            # Passive behavior: attack only if an enemy is already in range
            target = self._find_nearest_enemy(unit, battlefield)
            if not target:
                continue

            dist = unit.distance_to(target)
            contact_range = unit.range + UNIT_RADIUS * 2

            if dist <= contact_range + EPSILON:
                unit.set_order("attack", target=target)
                continue

            # No threat, no action
            unit.current_order = None
