import importlib
from math import floor
from model.Battle import Battle
from model.Battlefield import Battlefield
from Constant import ROWS, COLS
from model.General import General
from util.UnitsFactory import UnitsFactory
from view.GUI import GUI
from util.Functions import create_strategy


class Lanchester:
    """
    Symmetric battle scenario designed to test Lanchester's Laws.
    
    This class sets up a controlled engagement between two armies of 
    unequal sizes (N vs 2N) to observe how numerical superiority 
    scales with unit effectiveness.

    Attributes:
        unit_type (str): The archetype of units used (e.g., 'Knight').
        N (int): Base unit count for the first army.
        army1_positions (list): Starting coordinates for Army 1.
        army2_positions (list): Starting coordinates for Army 2.
        units_factory (UnitsFactory): Component used to instantiate units.
        army1_units (list): List of units belonging to Army 1.
        army2_units (list): List of units belonging to Army 2.
        troupes (dict): Global mapping of unit IDs to unit instances.
        general1 (General): Controller for the smaller army.
        general2 (General): Controller for the larger army.
    """

    def __init__(self, unit_type, N, strat):
        """
        Initializes the scenario, generates symmetric positions, 
        and assigns a specific strategy to both generals.
        """
        self.unit_type = unit_type
        self.N = N

        # Position placeholders for both armies
        self.army1_positions = []
        self.army2_positions = []

        # Generate symmetric formation layouts
        self.create_positions()

        # Unit factory instance
        self.units_factory = UnitsFactory()

        # Create both armies
        self.army1_units = []
        self.army2_units = []
        self.create_units()

        self.troupes = {}
        for unit in self.army1_units + self.army2_units:
            self.troupes[unit.id] = unit

        # display troops
        #for uid, unit in self.troupes.items():
        #    print(f"Unit ID: {uid}, Type: {unit.name}, Position: {unit.position}")
        #exit()
        # Create generals and assign strategy
        #try:
         #   mod = importlib.import_module(f"scenario.{strat}")
          #  cls = getattr(mod, strat)
            
        #except Exception as e:
         #   raise ValueError(f"Unknown IA name '{strat}' and dynamic import failed: {e}")

        strategy = create_strategy(strat)
        self.general1 = General("General 1",1, strategy)
        self.general2 = General("General 2",2, strategy)
        
    # ===================================================================
    #                       UNIT CREATION
    # ===================================================================
    def create_units(self):
        """
        Instantiates units for both armies and assigns their 
        pre-calculated spatial coordinates.
        """
        # Instantiate units
        self.army1_units = [
            self.units_factory.create_unit(i, self.unit_type)
            for i in range(self.N)
        ]
        self.army2_units = [
            self.units_factory.create_unit(i+1000, self.unit_type)
            for i in range(2 * self.N)
        ]

        # Assign precomputed positions
        for i, pos in enumerate(self.army1_positions):
            self.army1_units[i].position = pos
        for i, pos in enumerate(self.army2_positions):
            self.army2_units[i].position = pos

    # ===================================================================
    #                       POSITION GENERATION
    # ===================================================================
    def generate_positions(self, nb_units, start_line, first_army=True):
        """
        Calculates a grid-based formation for an army.
        
        Args:
            nb_units (int): Total units to place.
            start_line (int): Vertical offset for the formation.
            first_army (bool): If True, places units on the left; otherwise on the right.
            
        Returns:
            list: A list of (row, col) tuples.
        """
        positions = []
        per_line = (nb_units // 5) + 1  # approximate number of columns per row

        for i in range(floor(nb_units / per_line) + 2):
            for j in range(per_line):
                if len(positions) >= nb_units:
                    break

                if first_army:
                    positions.append((start_line + i, (COLS // 2) - 5 - j))
                else:
                    positions.append((start_line + i, (COLS // 2) + 5 + j))

        return positions

    def create_positions(self):
        """
        Orchestrates the creation of starting positions for both 
        armies around the battlefield's center line.
        """
        self.army1_positions = self.generate_positions(self.N, 4, True)
        self.army2_positions = self.generate_positions(2 * self.N, 4, False)

    # ===================================================================
    #                       SCENARIO EXECUTION
    # ===================================================================
    def run(self):
        """
        Executes the battle simulation and returns the final 
        count of surviving units from Army 2.

        Returns:
            int: Number of living units in General 2's army at the end.
        """
        battlefield = Battlefield(COLS, ROWS, self.troupes)#generate_heightmap(COLS, ROWS))

        #view = GUI(battlefield, [self.general1, self.general2])
        battle = Battle(self.general1, self.general2, battlefield)
        battle.start()

        return self.general2.get_unit_alive_number(battlefield)
