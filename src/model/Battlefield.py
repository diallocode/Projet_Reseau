import math
import random
from Constant import UNIT_RADIUS

class Battlefield:
    """
    Continuous Real-Time Battlefield Simulation.

    Attributes
    ----------
    width : float
        The battlefield width (horizontal size).
    height : float
        The battlefield height (vertical size).
    troupes : dict
        Dictionnaire mapping army_id -> Army.
    """

    def __init__(self, width: float, height: float, troupes: dict, heightmap=None) -> None:
        """
        Initializes a continuous battlefield.

        Parameters
        ----------
        width : float
        height : float
        troupes : dict
            Initial mapping unit_id -> Unit.
        """
        if width <= 0 or height <= 0:
            raise ValueError("Width and height must be positive.")

       
        self.troupes = {}           # Dictionary will contains id:Unit
        self.width = width
        self.height = height
        self.heightmap = heightmap
        self.create_troupe(troupes)



    # ==========================================================
    #                   UNIT MANAGEMENT
    # ==========================================================
    def create_troupe(self, units_dict):
        """
        Add unit in unit dictionary
        """
        if not isinstance(units_dict, dict):
            raise ValueError("units_dict should be a dictionary {id: unit_obj}")

        # Fast update of dictionary
        self.troupes.update(units_dict)

        # Link the battlefield and check unit positions
        for unit_id, unit in units_dict.items():
            unit.battlefield = self
            self.check_unit_position(unit)


    def check_unit_position(self, unit):
        """
        Check unit position
        """
        if unit.position is not None:
            if not self.is_valid_position(unit.position):
                print(f"Battlefield size: width={self.width}, height={self.height}")
                raise ValueError(f"Invalid position {unit.position} for unit {unit}")


    def remove_unit(self, unit_id):
        """ Remove unit via its id """
        if unit_id in self.troupes:
            self.troupes[unit_id].position = None
            del self.troupes[unit_id]

    def get_unit_at(self, position):
        for unit in self.troupes.values():
            if not unit.is_alive():
                continue
            if unit.position is None:
                continue
            if math.dist(unit.position, position) <= UNIT_RADIUS*2:
                return unit
        return None
    # ==========================================================
    #                   POSITION MANAGEMENT
    # ==========================================================
    def is_valid_position(self, position):
        x, y = position
        # x is horizontal coordinate -> compare with width
        # y is vertical coordinate -> compare with height
        return 0.0 <= x < self.width and 0.0 <= y < self.height

    # prevention of exits from the battlefield
    def clamp_position(self, position):
        x, y = position
        x = max(0.0, min(self.width - 0.001, x))
        y = max(0.0, min(self.height - 0.001, y))
        return (x, y)

    # ==========================================================
    #                   UNIT INTERACTIONS
    # ==========================================================
    def get_enemy_units(self, unit):
        """
        Return enemies and following the next rules for ID :
        - If unit_id < 1000 : enemies have id >= 1000
        - If unit_id >= 1000 : enemies have id < 1000
        """
        if unit is None:
            return []

        # Determine the camp of unit (0, 1, 2...)
        unit_segment = unit.id // 1000
        enemies = []

        for target_id, target_unit in self.troupes.items():
            if not target_unit.is_alive():
                continue

            # If the target is not in the same camp
            target_segment = target_id // 1000
            if unit_segment != target_segment:
                enemies.append(target_unit)

        return enemies


    def find_nearby_enemies(self, unit, radius):
        enemies = self.get_enemy_units(unit)
        nearby = []
        if not unit.position:
            return nearby

        for e in enemies:
            if not e.position:
                continue
            dist = math.dist(unit.position, e.position)     # distance 
            if dist <= radius:
                nearby.append(e)
        return nearby


    # ==========================================================
    #                   UPDATE CYCLE
    # ==========================================================
    def _update_single_unit(self, unit, dt):
        if not unit.is_alive():
            return True
        unit.update(dt)
        if unit.position:
            unit.position = self.clamp_position(unit.position)
        return not unit.is_alive()

    # More nested list paths general->army->units
    def update(self, dt):
        """
        Met à jour toutes les unités directement depuis le dictionnaire.
        """
        # List of units for random mixing
        all_units = list(self.troupes.values())
        random.shuffle(all_units)

        ids_to_remove = []
        for unit in all_units:
            if unit.is_alive():
                is_dead = self._update_single_unit(unit, dt)
                if is_dead:
                    ids_to_remove.append(unit.id)
            else:
                ids_to_remove.append(unit.id)

        # Cleaning
        for uid in ids_to_remove:
            self.remove_unit(uid)

    # ==========================================================
    #                   MAINTENANCE METHODS
    # ==========================================================
    def resetBattlefield(self):
        """ Clear all troup and position """
        for unit in self.troupes.values():
            unit.position = None
        self.troupes = {}

    # ==========================================================
    #                   REPRESENTATION
    # ==========================================================
    def __repr__(self):
        return f"Battlefield {self.width:.1f}x{self.height:.1f} with {len(self.troupes)} armies"


    # ==========================================================
    #                   ELEVATION
    # ==========================================================
    def get_height(self, x, y):
        if not self.heightmap:
            return 0

        x = max(0, min(self.width - 1, x))
        y = max(0, min(self.height - 1, y))

        x0 = int(math.floor(x))
        y0 = int(math.floor(y))
        x1 = min(x0 + 1, self.width - 1)
        y1 = min(y0 + 1, self.height - 1)

        dx = x - x0
        dy = y - y0

        h00 = self.heightmap[y0][x0]
        h10 = self.heightmap[y0][x1]
        h01 = self.heightmap[y1][x0]
        h11 = self.heightmap[y1][x1]

        h0 = h00 * (1 - dx) + h10 * dx
        h1 = h01 * (1 - dx) + h11 * dx
        return h0 * (1 - dy) + h1 * dy


    # ==========================================================
    #                   COLLISION
    # ==========================================================
    def is_position_free(self, unit, pos):
        for other in self.troupes.values():
            if other is unit:
                continue
            if not other.is_alive():
                continue

            dx = pos[0] - other.position[0]
            dy = pos[1] - other.position[1]
            if math.hypot(dx, dy) < UNIT_RADIUS*2:
                return False
        return True
