# tournament/TournamentManager.py
from .ResultTracker import ResultTracker
from .BattleSimulator import BattleSimulator
from .ReportGenerator import ReportGenerator
from util.Functions import load_scenarios



class TournamentManager:
    """
    Manage the progress and global logic tournament.
    """
    def __init__(self, generals, scenarios_config, rounds=1, alternating=False):
        self.generals = generals  
        self.indexed_generals = list(enumerate(generals)) # liste de tuples
        self.scenarios = load_scenarios(scenarios_config)
        self.rounds = rounds
        self.alternating = alternating
        self.tracker = ResultTracker(self.indexed_generals)  
        self.simulator = BattleSimulator()
        self.reporter = ReportGenerator()


    def run(self):
        """Launch tournament"""

        print("Tournament start...")

        # Tounament loop
        for scen in self.scenarios:

            # Initialisation of scenario results
            scen_summary = self.tracker.init_scenario_summary(scen)

            for id1, name1 in self.indexed_generals:
                for id2, name2 in self.indexed_generals:
                    for r in range(self.rounds):
                        # We alternate depending on the round.
                        if not self.alternating or r % 2 == 0:
                            p1_id, p1_name = id1, name1
                            p2_id, p2_name = id2, name2
                        else:
                            p1_id, p1_name = id2, name2
                            p2_id, p2_name = id1, name1

                        winner_pos = self.simulator.simulate(p1_name, p2_name, scen)

                        # We pass the tuples (Ids, name) to the tracker to avoid overcounting.
                        self.tracker.register_result(scen_summary, (p1_id, p1_name), (p2_id, p2_name), winner_pos)

            # Adding scenario results to the global tracker
            self.tracker.per_scenario.append(scen_summary)
            print(f"End of scenario. Resume : {scen_summary['matrix']}")


        # Report generation
        final_results = self.tracker.get_results()
        report_path = self.reporter.generate(final_results, self.indexed_generals)
        print("Tournament finished. Report saved:", report_path)

        return report_path


def run_tournament(args):
    # Recover user input arguments
    generals = args.G
    scenarios_config = args.scenarios
    rounds = getattr(args, "rounds", 1)
    is_na = getattr(args, "not_alternating", False)

    manager = TournamentManager(
        generals=generals,
        scenarios_config=scenarios_config,
        rounds=rounds,
        alternating=(not is_na)
    )

    return manager.run()
