import os
import csv
from collections import defaultdict
from Constant import STATS_BONUS_FILEPATH


class CSVLoader:
    """
    Utility class for parsing CSV files to populate combat modifier matrices.
    
    This class reads damage and armor bonuses based on the interaction 
    between different unit types (attacker vs. defender).
    """

    def load_bonus_damage_matrix(self,csv_path: str):
        """
        Parses a CSV file to create a nested dictionary of offensive bonuses.
        
        Returns:
            dict: A matrix where keys are attacker names and values are 
                  dictionaries mapping defender names to damage bonus values.
        """

        matrix = defaultdict(dict)
        path = os.path.dirname(__file__)
        os.path.join(path, csv_path)
        with open(csv_path, newline='', encoding='utf-8') as f:
            f.readline()

            reader = csv.DictReader(f, fieldnames=["attacker", "defender", "bonus_damage", "bonus_armor"])
            for row in reader:
                # Skip empty or malformed lines
                if not row["attacker"] or not row["defender"]:
                    continue
                attacker = row["attacker"]
                defender = row["defender"]
                base = 1.0
                try:
                    bonus = float(row["bonus_damage"])
                except ValueError:
                    continue  # Ignore non-numeric values

                matrix[attacker][defender] = bonus
        return dict(matrix)


    def load_bonus_armor_matrix(self, csv_path: str):
        """
        Parses a CSV file to create a nested dictionary of defensive bonuses.
        
        Returns:
            dict: A matrix where keys are attacker names and values are 
                  dictionaries mapping defender names to armor bonus values.
        """

        matrix = defaultdict(dict)
        path = os.path.dirname(__file__)
        os.path.join(path, csv_path)
        with open(csv_path, newline='', encoding='utf-8') as f:
            f.readline()

            reader = csv.DictReader(f, fieldnames=["attacker", "defender", "bonus_damage", "bonus_armor"])
            for row in reader:
                # Skip empty or malformed lines
                if not row["attacker"] or not row["defender"]:
                    continue

                attacker = row["attacker"]
                defender = row["defender"]
                try:
                    bonus_armor = float(row["bonus_armor"])
                except ValueError:
                    continue  # Ignore non-numeric values


                matrix[attacker][defender] = bonus_armor
        return dict(matrix)
