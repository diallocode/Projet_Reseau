from Constant import ROWS, COLS, VIEW_ELEVATION
from util.ScenarioMaker import ScenarioMaker
from model.Battlefield import Battlefield
from model.Battle import Battle
from scenario.Lanchester import Lanchester
from view.GUI import GUI
from view.Console import Console
from scenario.ScenarioDataPlotter import PlotLanchester
from battle_tournament.TournamentManager import run_tournament
from util.Functions import parse_units_list, parse_range, get_scenario, create_parser, generate_heightmap
from util.SaveManager import SaveManager


if __name__ == '__main__':

    parser = create_parser()
    args = parser.parse_args()


    if args.command == 'run':
        print(f"Running battle between {args.AI1} and {args.AI2}")

        print(f"Player {args.player_id} — choose your army:")
        scenario = get_scenario()  # Chaque joueur tape son propre dict

        maker = ScenarioMaker(scenario, args.player_id, args.AI)
        data = maker.get_data()

        general = data["general"]
        my_units = data["my_units"]

        battlefield = Battlefield(COLS, ROWS, my_units, generate_heightmap(COLS, ROWS))

        if args.terminal:
            view = Console(battlefield)
        else:
            view = GUI(battlefield, [general], VIEW_ELEVATION)

        if args.datafile:
            battle = Battle(general, battlefield, view, args.datafile)
        else:
            battle = Battle(general, battlefield, view)

        if args.plot:

            battle.collectStats = True

        battle.start()
