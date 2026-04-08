from math import ceil
from model.General import General
from util.UnitsFactory import UnitsFactory
from util.Functions import create_strategy

class ScenarioMaker:
    
    """
    Prépare le terrain pour UN participant dans une bataille P2P.
    
    Chaque joueur instancie son propre ScenarioMaker avec :
    - son player_id (0, 1, 2...) qui détermine son bloc d'IDs et sa zone de spawn
    - son nom et sa stratégie IA
    - le scénario commun partagé par tous les participants
    """

    ID_BLOCK_SIZE = 1000  # Cohérent avec Battlefield.get_enemy_units()

    def __init__(self, scenario, player_id, ia_name, player_name=None):
        self.scenario = scenario
        self.player_id = player_id          # 0, 1, 2, 3...
        self.ia_name = ia_name
        self.player_name = player_name or f"General {player_id + 1}"

        self.units_factory = UnitsFactory()
        self.my_units = {}
        self.my_positions = {}

        self.create_positions()
        self.create_units()
        self.general = self.create_general()

    def create_positions(self):
        """
        Calcule la zone de spawn du joueur selon son player_id.
        Chaque armée occupe une colonne de départ décalée.
        """
        start_line = self.scenario["startLine"]
        unit_per_col = self.scenario["unitPerCol"]
        army_distance = self.scenario["armyDistance"]
        unit_order = ["Crossbowman", "Pikeman", "Knight"]

        # Calcul de la largeur d'une armée
        army_width = sum(
            ceil(self.scenario.get(ut, 0) / unit_per_col)
            for ut in unit_order
            if self.scenario.get(ut, 0) > 0
        )

        # Chaque joueur est décalé de (army_width + army_distance) * player_id
        start_col = self.scenario["startCol"] + self.player_id * (army_width + army_distance)

        current_col = start_col
        for unit_type in unit_order:
            nb_units = self.scenario.get(unit_type, 0)
            if nb_units <= 0:
                continue

            self.my_positions[unit_type] = []
            nb_cols = ceil(nb_units / unit_per_col)
            unit_idx = 0

            for c in range(nb_cols):
                col = current_col + c
                for r in range(unit_per_col):
                    if unit_idx < nb_units:
                        self.my_positions[unit_type].append((start_line + r, col))
                        unit_idx += 1
            current_col += nb_cols

    def create_units(self):
        """
        Instancie uniquement les unités de CE joueur.
        Les IDs sont dans le bloc [player_id * 1000, (player_id+1) * 1000[
        """
        base_id = self.player_id * self.ID_BLOCK_SIZE
        unit_id = 0

        for unit_type in ["Crossbowman", "Pikeman", "Knight"]:
            for pos in self.my_positions.get(unit_type, []):
                uid = base_id + unit_id
                unit = self.units_factory.create_unit(uid, unit_type)
                unit.position = pos
                self.my_units[uid] = unit
                unit_id += 1

    def create_general(self):
        """
        Crée le général de CE joueur avec sa stratégie IA.
        general_id = player_id + 1 (cohérent avec l'ancien système : 1 → bloc 0-999)
        """
        strategy = create_strategy(self.ia_name)
        return General(self.player_name, self.player_id + 1, strategy)

    def get_data(self):
        """
        Retourne les données de CE joueur uniquement.
        Le Battlefield sera alimenté par les unités distantes via le réseau.
        """
        return {
            "general": self.general,
            "my_units": self.my_units,
            "player_id": self.player_id,
        }