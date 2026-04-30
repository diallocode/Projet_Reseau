from Constant import STATS_FILEPATH
import os
from util.Functions import readStatsFromFile
from model.Unit import Unit

"""
UnitsFactory module.

Responsibilities / Contract:
- Role: Load unit statistics from a CSV file and instantiate unit objects (Knight, Pikeman, Crossbowman).
- Preconditions:
  * STATS_FILEPATH points to a CSV file located in the same package directory.
  * The CSV file has a header followed by lines with fields:
    unit_type,hp,type_Attack,attack,armor,pierce_armor,range,line_of_sight,speed,attack_Delay,reload_time,accuracy
- Postconditions:
  * self.stats is a dict mapping unit type -> stat dictionary with properly typed values (int/float/str).
- Side effects:
  * Reads from the filesystem during initialization.
- Errors:
  * FileNotFoundError if the stats file cannot be opened.
  * ValueError if a line has an unexpected number of fields or a numeric conversion fails.
"""


class UnitsFactory:
    """
    Factory class responsible for creating unit instances dynamically.

    Responsibilities / Contract:
    - Role: Load unit statistics from a CSV file and instantiate units (e.g., Knight, Pikeman, Crossbowman)
      defined under model.units.<UnitType>.
    - Preconditions:
      * STATS_FILEPATH points to a valid CSV file located in the same package directory.
      * The CSV file contains 12 comma-separated fields:
        unit_type, hp, type_Attack, attack, armor, pierce_armor,
        range, line_of_sight, speed, attack_Delay, reload_time, accuracy
    - Postconditions:
      * self.stats is a dictionary mapping each unit type to its stats dictionary.
    - Side effects:
      * Reads a CSV file from the filesystem during initialization.
    - Errors:
      * FileNotFoundError if the CSV file cannot be opened.
      * ValueError if the CSV format is invalid or a numeric conversion fails.
    """

    def __init__(self):
        """Initialize the UnitsFactory by loading stats from a CSV file."""
        path = os.path.dirname(__file__)
        self.stats = readStatsFromFile(os.path.join(path, STATS_FILEPATH))



    def create_unit(self, id: int, unit_type: str):
        """
        Dynamically create a unit instance based on its type and predefined stats.

        Args:
            id (int): Identifier of the army (1 or 2).
            unit_type (str): The name of the unit class to instantiate (e.g., "Knight").

        Returns:
            Unit: An instantiated unit object with proper attributes.

        Raises:
            ValueError: If the unit type or its class cannot be found.
        """
        # Ensure the unit type exists in loaded stats
        if unit_type not in self.stats:
            raise ValueError(f"Unit type {unit_type} not found in stats file")

        # Retrieve stats and map them to Unit dataclass fields
        s = self.stats[unit_type]
        kwargs = {
            "id": id,
            "name": unit_type,
            "symbol": unit_type[0],
            "hp": s["hp"],
            "type_attack": s["type_Attack"],
            "attack": s["attack"],
            "armor": s["armor"],
            "pierce_armor": s["pierce_armor"],
            "range": s["range"],
            "line_of_sight": s["line_of_sight"],
            "speed": s["speed"],
            "attack_delay": s["attack_Delay"],
            "reload_time": s["reload_time"],
            "accuracy": s["accuracy"],
            "position": None
        }

        # Instantiate and return the unit
        return Unit(**kwargs)
