class General:
    """
    Represent a general who control its units.
    """

    def __init__(self, name, general_id, strategy) -> None:
        """
        Initialise general.

        Parameters
        ----------
        name : str
            General's name.
        general_id : int
            ID (ex: 0 or 1000) who defined camp.
        strategy : Strategy
            Logic decision

        Raises
        ------
        ValueError
            If `name` is empty or if `army`/`strategy` are invalid types.
        """
        if not isinstance(name, str) or not name.strip():
            raise ValueError("General name must be a non-empty string.")
        self.name = name
        self.id = general_id  # Use to filter units for its army (< 1000 ou >= 1000)
        self.strategy = strategy

    # ==========================================================
    #                   UNIT ACCESS 
    # ==========================================================
    def get_my_units(self, battlefield):
        """
        Dynamic recover of general's unit in battlefield.

        Recover unit in camp [(ID-1)*1000, ID*1000[
        """

        lower_bound = (self.id - 1) * 1000
        upper_bound = self.id * 1000

        # Global filter of unit dictionary
        return [
            unit for uid, unit in battlefield.troupes.items()
            if lower_bound <= uid < upper_bound and unit.is_alive()
        ]


    # ==========================================================
    #                   MAIN BEHAVIOR LOOP
    # ==========================================================
    def play(self, battlefield):
        """
        Executes the general's strategy for one simulation step.

        Delegates tactical decisions to the current strategy, allowing it to
        update the army’s orders based on battlefield conditions.

        Parameters
        ----------
        battlefield : Battlefield
            The environment where the battle takes place.
        dt : float
            Delta time (seconds elapsed since the last frame).
        """
        # Ask the strategy to decide the next actions for this frame
        self.strategy.play(self, battlefield)

    # ==========================================================
    #                   STATISTICS
    # ==========================================================

    def getStats(self, battlefield):
        """
        Calculate aggregate position of units sous son commandement.
        """
        my_units = self.get_my_units(battlefield)

        if not my_units:
            return {"count": 0, "total_hp": 0, "avg_hp": 0}

        total_hp = sum(u.hp for u in my_units if hasattr(u, 'hp'))

        return {
            "count": len(my_units),
            "total_hp": total_hp,
            "avg_hp": total_hp / len(my_units)
        }

  
    def get_stats_by_unit_type(self, battlefield):
        """
        Returns a dictionary with the number of alive units for each unit type.
        """
        stats = {}
        my_units = self.get_my_units(battlefield)

        for unit in my_units:
            unit_type = unit.name
            if unit_type not in stats:
                stats[unit_type] = 0
            stats[unit_type] += 1

        return stats

    # ==========================================================
    #                   UNIT ALIVE NUMBER
    # ==========================================================
    def get_unit_alive_number(self, battlefield):
        """
        Count the number of alive units.
        """
        return len(self.get_my_units(battlefield))

    # ==========================================================
    #                   DEFEATED DETECTION
    # ==========================================================
    def is_defeated(self, battlefield):
        """
        Detect if the army is defeated.
        """
        if self.get_unit_alive_number(battlefield) == 0:
            return True
        return False

    def __repr__(self):
        return f"General {self.name} (ID Group: {self.id})"
