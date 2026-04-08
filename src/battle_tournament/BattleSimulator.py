# tournament/BattleSimulator.py

from util.ScenarioMaker import ScenarioMaker
from model.Battlefield import Battlefield
from model.Battle import Battle
from Constant import ROWS, COLS
from model.General import General
import traceback
from view.GUI import GUI


class BattleSimulator:
    """
    Class to simulate one only fight between to AI (generals).
    """

    def simulate(self, AI1, AI2, scenario: dict) -> str:
        """
        Simulate a fight without GUI and inputs.
        Return the winner's name ; AI1, AI2, 'draw'
        """

        # Scenario creation
        scenario_maker = ScenarioMaker(scenario, AI1, AI2)
        data = scenario_maker.get_data()

        troupes = data["all_units"]     # on recupere les units

        # Battlefield
        battlefield = Battlefield(ROWS, COLS, troupes) 
        
        # Generals
        general1 = data["general1"]
        general2 = data["general2"]

        
        # Battle without GUI
        battle = Battle(general1, general2, battlefield)

        # battle.start() return General object (winner) or None (draw)
        winner_obj = battle.start(True)

        # Winner determination logic
        if winner_obj is None:
            return "draw"

        if winner_obj is general1:
            return "general1"
        if winner_obj is general2:
            return "general2"

        return "draw"
