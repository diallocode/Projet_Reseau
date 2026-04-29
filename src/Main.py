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
from Network.NetworkManager import NetworkManager

#on fait nos  ajot pour que le main puisse savoir si on fait ./IPC ou IPC.exe selon l'OS
import sys
import subprocess
import os

# --- TÂCHE : Lancement dynamique du processus réseau ---
def launch_network_bridge(port_reseau="5002", port_python_recv="5001", port_python_send="5003"):
    # On détermine l'extension selon l'OS
    extension = ".exe" if sys.platform == "win32" else ""
    
    # On construit le chemin vers le binaire (adapte le chemin selon ton dossier)
    # Si Main.py est dans src/ et IPC dans reseau/
    path_to_c = os.path.join("..", "reseau", f"IPC{extension}")
    
    try:
        print(f"[SYSTEM] Lancement du pont réseau : {path_to_c}")
        # On lance le processus C en arrière-plan
        return subprocess.Popen([path_to_c, port_reseau, port_python_recv, port_python_send])
    except Exception as e:
        print(f"[ERREUR] Impossible de lancer le processus C : {e}")
        return None

if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()

    if args.command == 'run':
        process_c = None
        try:
            # On ne lance le pont C QUE pour une partie réelle
           # process_c = launch_network_bridge() 
            print("Initialisation du pont réseau IPC... en attente  lancer le dans un autre terminal")
            
            network_manager = NetworkManager() 
            player_id = network_manager.my_player_id
            
            print(f"Running battle with {args.AI} Strategy as Player {player_id}")

            scenario_maker = ScenarioMaker(get_scenario(), player_id, args.AI)
            data = scenario_maker.get_data()

            general1 = data.get("general")
            all_units = data.get("my_units")
            network_data = data.get("network_data")

            battlefield = Battlefield(COLS, ROWS, all_units, network_manager, generate_heightmap(COLS, ROWS))

            if args.terminal:
                view = Console(battlefield)
            else:
                view = GUI(battlefield, [general1], VIEW_ELEVATION)

            battle = Battle(general1, battlefield, network_manager, view)

            if args.plot:
                battle.collectStats = True       
            
            # Lancement de la bataille
            battle.start(network_data)
            
        finally:
            # On s'assure que le processus C est bien arrêté quand on quitte 'run'
            if process_c:
                process_c.terminate()
                print("[SYSTEM] Pont réseau fermé.")

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