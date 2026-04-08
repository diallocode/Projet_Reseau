from Constant import ROWS, COLS, VIEW_ELEVATION
from model import NetworkManager
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

        print("Initialisation du pont réseau IPC...")
        
        # 1. Le jeu se met en pause ici jusqu'à recevoir l'ID
        network_manager = NetworkManager(port=5000) 
        player_id = network_manager.my_player_id
        
        print(f"Running battle with {args.AI1} Strategy as Player {player_id}")

        # 2. On passe le fameux player_id au ScenarioMaker !
        scenario_maker = ScenarioMaker(get_scenario(), args.AI1, player_id)
        data = scenario_maker.get_data()

        general1 = data.get("general1")
        all_units = data.get("all_units")

        battlefield = Battlefield(COLS, ROWS, all_units, generate_heightmap(COLS, ROWS))

        # 3. Initialisation de la vue (Console ou GUI)
        if args.terminal:
            view = Console(battlefield)
        else:
            # Note : Tu pourras adapter les généraux à afficher
            view = GUI(battlefield, [general1], VIEW_ELEVATION)

        # 4. On passe le network_manager à la Battle pour qu'elle puisse lire les messages
        battle = Battle(general1, None, battlefield, view, network_manager)

        if args.plot:
            battle.collectStats = True

        battle.start()


    if args.command == 'load':
        view_factory = (lambda bf: GUI(bf)) if args.gui else None
        battle = SaveManager.load_battle(args.savefile, view_factory=view_factory)
        battle.start()

    if args.command == 'tourney':
        print(f"Running tournament with AIs: {args.G}, scenarios: {args.scenarios}, rounds: {args.rounds}")
        run_tournament(args) # Call run_tournament function

    if args.command == 'plot':

        units_type = parse_units_list(args.units_type)

        ranges = parse_range(args.ranges)

        print("Automated scenario start with parameters:\n")
        print(f"AI: {args.AI} plotter={args.plotter} scenario={args.scenario}\n")
        print(f"units_type={units_type} range={ranges} rounds={args.rounds}\n")
        print("Running..........................................................")


        data = {}
        for unit_type in units_type:
            for n in ranges:
                scenario = eval(args.scenario)
                data[unit_type, n] = scenario(unit_type, n, args.AI).run()

        plotter = eval(args.plotter)
        plotter(data)

