import math
from iastrategy.Strategy import Strategy
from Constant import EPSILON, UNIT_RADIUS

class Smart(Strategy):
    """
    Smart Strategy:
    - Elite units (Knights/Crossbowmen) gain elevation at map edges.
    - Pikemen hold the center as a defensive screen.
    - Any attack on elite units triggers a global forced assault.
    - Switches to aggressive mode after prolonged inactivity or forced assault.
    """

    def __init__(self):
        super().__init__()
        self.idle_frames = 0
        self.safe_high_ground = None
        self.safe_high_ground_x = None
        self.forced_assault = False

    def __repr__(self):
        return "Smart"

    def play(self, general, battlefield):
        my_units = [u for u in general.get_my_units(battlefield) if u.is_alive()]
        if not my_units:
            return

        # 1. DETERMINE OUR SUMMIT (Map edge closest to spawn)
        if not self.safe_high_ground:
            avg_x = sum(u.position[0] for u in my_units) / len(my_units)
            self.safe_high_ground_x = 0.0 if avg_x < battlefield.width / 2 else battlefield.width - 0.5
            self.safe_high_ground = True

        # 2. AGGRESSIVE MODE MANAGEMENT (Global)
        if not self.forced_assault:
            for u in my_units:
                if u.name in ["Knight", "Crossbowman"]:
                    attacker = getattr(u, "last_attacker", None)
                    if attacker and attacker.is_alive():
                        self.forced_assault = True
                        break

        any_unit_attacking = any(u.current_order == "attack" for u in my_units)
        self.idle_frames = 0 if any_unit_attacking else self.idle_frames + 1
        
        # Aggressive mode is true if timer > 1000 OR if forced assault
        aggressive_mode = (self.idle_frames > 1500) or self.forced_assault

        # 3. UNIT LOGIC
        for unit in my_units:
            target = self._find_nearest_enemy(unit, battlefield)
            if not target:
                continue
                
            dist_to_target = unit.distance_to(target)
            my_safe_pos = (self.safe_high_ground_x, unit.position[1])

            # --- PIKEMAN: Constant damming ---
            if unit.name == "Pikeman":
                if dist_to_target <= unit.range + UNIT_RADIUS * 2 + EPSILON:
                    unit.set_order("attack", target=target)
                else:
                    unit.set_order("move", target_pos=target.position)
                continue # Moving on to the next unit

            # --- ELITE: Knights & Crossbowmen ---
            if aggressive_mode:
                if unit.type_attack == "Melee":
                    if dist_to_target <= unit.range + UNIT_RADIUS * 2 + EPSILON:
                        unit.set_order("attack", target=target)
                    else:
                        unit.set_order("move", target_pos=target.position)
                else:
                    # Distance Logic
                    enemies = [e for e in battlefield.get_enemy_units(unit) if e.is_alive()]
                    enemies_in_range = [e for e in enemies if unit.distance_to(e) <= unit.range + UNIT_RADIUS * 2 + EPSILON]

                    if enemies_in_range:
                        best_local_target = min(enemies_in_range, key=lambda e: e.hp)
                        unit.set_order("attack", target=best_local_target)
                    elif enemies:
                        nearest_target = min(enemies, key=lambda e: unit.distance_to(e))
                        unit.set_order("move", target_pos=nearest_target.position)
            else:
                # Outside of aggressive mode, we climb
                unit.set_order("move", target_pos=my_safe_pos)

  
