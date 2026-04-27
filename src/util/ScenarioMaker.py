from math import ceil
from model.General import General
from util.UnitsFactory import UnitsFactory
from util.Functions import create_strategy
from Network.NetworkManager import NetworkManager

class ScenarioMaker:
    def __init__(self, scenario, player_id,  iaName):
        self.scenario = scenario
        self.iaName = iaName
        self.player_id = player_id
        self.network_data = {
            "type": "handshake",
            "player_id": self.player_id,
            "units": []
        }
        self.units_factory = UnitsFactory()
        self.all_units  = {}
        self.positions= {}

        self.create_positions()
        self.create_units()
        self.general = self.create_generals()
        
        #self.network_manager.send_to_c(self.network_data)

    def create_positions(self):
        start_line = self.scenario["startLine"]
        start_col = self.scenario["startCol"]
        unit_per_col = self.scenario["unitPerCol"]
        army_distance = self.scenario["armyDistance"]

        # Order of units (from rear to front)
        # Army 1 will have its Knights at the front (to the right of its block).
        unit_order = ["Crossbowman", "Pikeman", "Knight"]

        self.positions = {}

        # =========================================================
        # 1. CALCULATING THE WIDTH OF THE ARMY 1
        # =========================================================
        total_cols_army = 0
        for unit_type in unit_order:
            nb = self.scenario.get(unit_type, 0)
            if nb > 0:
                total_cols_army += ceil(nb / unit_per_col)

        # =========================================================
        # 2. ARMED POSITION 1 (Towards the right)
        # =========================================================
        current_col = start_col
        for unit_type in unit_order:
            nb_units = self.scenario.get(unit_type, 0)
            if nb_units <= 0: continue
            
            self.positions[unit_type] = []
            nb_cols = ceil(nb_units / unit_per_col)
            unit_idx = 0
            
            for c in range(nb_cols):
                col = current_col + c
                for r in range(unit_per_col):
                    if unit_idx < nb_units:
                        self.positions[unit_type].append((start_line + r, col))
                        unit_idx += 1
            current_col += nb_cols


    def create_units(self):
        # Using a set to avoid duplicate technical keys
        unit_keys = ["Crossbowman", "Pikeman", "Knight"]
        local_unit_idx = 0

        for unit_type in unit_keys:
            for pos in self.positions.get(unit_type, []):
                
                # 3. Calcul de l'ID GLOBAL 
                # Ex: Si tu es le joueur 1 -> ID = 1000 + 0 = 1000
                global_unit_id = (self.player_id * 1000) + local_unit_idx
                
                # 4. On crée l'unité avec l'ID Global
                u1 = self.units_factory.create_unit(global_unit_id, unit_type)
                u1.position = pos
                
                # 5. On n'oublie pas d'assigner le network_owner !
                u1.network_owner = self.player_id 
                
                self.all_units[global_unit_id] = u1
                local_unit_idx += 1
                
                self.network_data["units"].append({
                    "id": global_unit_id,
                    "type": u1.name,
                    "x": u1.position[0],
                    "y": u1.position[1],
                    "hp": u1.hp,
                    "network_owner": self.player_id
                })

    def create_generals(self):
        strategy = create_strategy(self.iaName)
        return General(f"General {self.player_id}", self.player_id, strategy)
    

    def get_data(self):
        return {"general": self.general, "my_units": self.all_units, "network_data": self.network_data}