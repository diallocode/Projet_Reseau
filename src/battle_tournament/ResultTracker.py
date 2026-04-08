# tournament/ResultTracker.py

class ResultTracker:

    """
    Outside of aggressive mode, we climb
    
    This class centralises the recording of each battle and organises
    data according to three levels of precision: overall, by opponent, 
    and by scenario.
    
    Attributes:
        generals (list): List of tuples (id, name) identifying each participant.
        summary (dict): Overall statistics accumulated by general.
        vs (dict): Head-to-Head Matrix.
        per_scenario (list): Detailed history of results for each scenario tested.
    """


    def __init__(self, indexed_generals):
        """
        Initialise all data result structures with zero.
        """
        self.generals = indexed_generals
        # Statistics of each general
        self.summary = {g: {"wins": 0, "losses": 0, "draws": 0, "matches": 0} for g in indexed_generals}
        # Face to face statistics
        self.vs = {g: {h: {"wins": 0, "losses": 0, "draws": 0, "matches": 0} for h in indexed_generals} for g in indexed_generals}
        # List to store detailed results per scenario
        self.per_scenario = []

    def get_results(self):
        """Return complete results structure for the report."""
        return {
            "summary": self.summary,
            "vs": self.vs,
            "per_scenario": self.per_scenario
        }

    def init_scenario_summary(self, scenario):
        """Initialise results structure for new scenario."""
        return {
            "scenario": scenario,
            "matrix": {
                g: {
                    h: {"wins": 0, "losses": 0, "draws": 0, "matches": 0}
                    for h in self.generals
                }
                for g in self.generals
            }
        }

    def register_result(self, scen_summary, p1, p2, winner_pos):
        """
        Records the outcome of a battle and updates the four affected counters.
        
        Args:
            scen_summary (dict): The dictionary of results for the current scenario.
            p1 (tuple): Tuple (id, name) of the first general.
            p2 (tuple): Tuple (id, name) of the second general.
            winner_pos (str): Result ("general1", "general2" ou "draw").
            
        Update logic :
            Increments the specific matrix of the current scenario.
            Updates the overall summary for each general.
            Updates the historical comparison matrix (vs) between p1 and p2.
        """

        # Update specific matrix of scenario
        m = scen_summary["matrix"][p1][p2]

        # Update results
        if winner_pos == "draw":
            # Update for g1 vs g2 in scenario matrix
            m["draws"] += 1
            m["matches"] += 1

            # Update global aggregates
            self.summary[p1]["draws"] += 1
            self.summary[p1]["matches"] += 1
            self.summary[p2]["draws"] += 1
            self.summary[p2]["matches"] += 1
            self.vs[p1][p2]["draws"] += 1
            self.vs[p1][p2]["matches"] += 1
            self.vs[p2][p1]["draws"] += 1
            self.vs[p2][p1]["matches"] += 1
            return

        if winner_pos == "general1":
            # Update for g1 vs g2 in scenario matrix
            m["wins"] += 1
            m["matches"] += 1

            # Update global aggregates
            self.summary[p1]["wins"] += 1
            self.summary[p1]["matches"] += 1
            self.summary[p2]["losses"] += 1
            self.summary[p2]["matches"] += 1
            self.vs[p1][p2]["wins"] += 1
            self.vs[p1][p2]["matches"] += 1
            self.vs[p2][p1]["losses"] += 1
            self.vs[p2][p1]["matches"] += 1
            return

        if winner_pos == "general2":
            # Same logic for g2 winner
            m["losses"] += 1
            m["matches"] += 1

            self.summary[p2]["wins"] += 1
            self.summary[p2]["matches"] += 1
            self.summary[p1]["losses"] += 1
            self.summary[p1]["matches"] += 1
            self.vs[p2][p1]["wins"] += 1
            self.vs[p2][p1]["matches"] += 1
            self.vs[p1][p2]["losses"] += 1
            self.vs[p1][p2]["matches"] += 1
            return
