import os
import pygame
from view.View import View
from model.Battlefield import Battlefield
from Constant import ROWS, COLS


class Console(View):
    """ Redraws cells if that changed since last frame. """

    def __init__(self, battlefield: Battlefield):
        self.battlefield = battlefield
        self.winner = None
        pygame.init()
        self.screen = pygame.display.set_mode((1, 1))

        # Color codes ANSI
        self.COLOR_RED = "\033[91m"
        self.COLOR_BLUE = "\033[94m"
        self.COLOR_RESET = "\033[00m"

        # Unit priority: Knight > Pikeman > Crossbowman
        self.unit_priority = {"Knight": 3, "Pikeman": 2, "Crossbowman": 1}

        # Storage of previous state of units
        self.previous_state = {}

        # Variable to clear console to activation
        self.first_clear = True

        # Took terminal dimension
        try:
            terminal_size = os.get_terminal_size()
            self.viewport_width = terminal_size.columns
            self.viewport_height = terminal_size.lines - 1
        except OSError:
            self.viewport_width = 80
            self.viewport_height = 24

        # Camera location initialisation
        self.camera_x = max(0, (COLS - self.viewport_width) // 2)
        self.camera_y = max(0, (ROWS - self.viewport_height) // 2)

    def dominant_unit(self, units_list):
        """
        Calculate dominant unit on a box.
        Priorities : Count > Knight > Pikeman > Crossbowman > Army 1 > Army 2
        """
        if not units_list:
            return None, None

        unit_counts = {}
        for unit in units_list:
            key = (unit['name'], unit['id'])
            unit_counts[key] = unit_counts.get(key, 0) + 1

        max_count = max(unit_counts.values())
        candidates = [k for k, v in unit_counts.items() if v == max_count]

        if len(candidates) == 1:
            unit_name, camp_id = candidates[0]
        else:
            # Tie-breaking
            best_candidate = max(candidates,
                                 key=lambda x:
                                 (self.unit_priority.get(x[0], 0), -x[1]))
            unit_name, camp_id = best_candidate

        symbol = next(unit['symbol'] for unit in units_list
                      if unit['name'] == unit_name and unit['id'] == camp_id)
        color = self.COLOR_RED if unit['id'] // 1000 == 0 else self.COLOR_BLUE

        return symbol, color

    def get_current_positions(self):
        """
        Scan all units and return positions with dominant units.
        """
        positions = {}

        for unit in list(self.battlefield.troupes.values()):
            if unit.is_alive() and unit.position:
                row = int(unit.position[0])
                col = int(unit.position[1])

                if (0 <= row < ROWS) and (0 <= col < COLS):
                    if (row, col) not in positions:
                        positions[(row, col)] = []

                    positions[(row, col)].append({
                        'name': unit.name,
                        'id': unit.id,
                        'symbol': unit.symbol
                    })

        # Calculate dominant for each position
        current_state = {}
        for (row, col), units_list in positions.items():
            symbol, color = self.dominant_unit(units_list)
            if symbol:
                current_state[(row, col)] = (symbol, color)

        return current_state

    def update_changed_cells(self):
        """Update only changed cells."""
        current = self.get_current_positions()

        all_positions = set(self.previous_state.keys()) | set(current.keys())

        for pos in all_positions:
            row, col = pos

            if not (self.camera_y <= row < self.camera_y + self.viewport_height and
                    self.camera_x <= col < self.camera_x + self.viewport_width):
                continue
            
            old_cell = self.previous_state.get(pos)
            new_cell = current.get(pos)

            if old_cell != new_cell:
                screen_row = row - self.camera_y + 1
                screen_col = col - self.camera_x + 1
                print(f"\033[{screen_row};{screen_col}H", end='')

                if new_cell:
                    symbol, color = new_cell
                    print(f"{color}{symbol}{self.COLOR_RESET}",
                          end='',
                          flush=True)
                else:
                    print(' ', end='', flush=True)

        self.previous_state = current

    def set_winner(self, winner):
        """Display the winner."""
        self.winner = winner

    def update(self):
        if self.first_clear:
            os.system('clear' if os.name == 'posix' else 'cls')
            self.first_clear = False
        else:
            self.update_changed_cells()

        if self.winner:
            self.set_winner(self.winner)
