from model.General import General
from view.View import View
from model.Battlefield import Battlefield
from Constant import FPS,PLOTS_FOLDER, HEADLESS_SPEEDUP
from util.Functions import plot
import pygame
from util.Logger import Logger
from .GameSnapshotReporter import GameSnapshotReporter
import webbrowser # For automatic web page
from view.Console import Console
from view.GUI import GUI
import time


class Battle:
    """
    Controller for real-time battle simulations between two Generals.

    Manages the simulation loop, unit updates, victory conditions, 
    user input (GUI/Terminal), and statistical data collection.

    Attributes:
        general1, general2 (General): The opposing commanders.
        battlefield (Battlefield): The combat environment.
        view (View): Optional GUI or Console renderer.
        winner (General): Set once victory conditions are met.
        paused (bool): Current simulation state.
    """


    def __init__(self, general1: General, general2: General, battlefield: Battlefield, view:View = None, datafile: str = None):
        """
        Initializes the battle environment, participants, and optional logger/view.
        """
        self.battlefield = battlefield
        self.general1 = general1
        self.general2 = general2
        self.winner = None
        self.paused = False
        self.collectStats = False
        self.view = view
        self.logger = None
        if datafile:
            self.logger = Logger(datafile)
        self.terminal_view = None
        self._queued_battle = None
        self.should_exit = False
        if self.view and hasattr(self.view, 'clock'):
            self.mode_terminal = False
        elif self.view:
            self.mode_terminal = True
        if not self.view:
            self.speed = HEADLESS_SPEEDUP
        else:  
            self.speed = 1

    # ===================================================================
    #                           MAIN SIMULATION
    # ===================================================================
    def start(self,is_tourney=False):
        """
        Executes the main simulation loop.

        Handles:
        1. Frame-rate timing (Pygame or sleep-based).
        2. Input events and state updates for units/battlefield.
        3. Victory, timeout, and stalemate detection.
        4. Post-battle statistics plotting (if enabled).

        Returns:
            General: The winner of the battle, or None if a draw occurred.
        """

        if self.view and hasattr(self.view, 'screen'):  # GUI has screen attribute
            # Pygame already initialized in GUI.__init__
            pass

        # Initialize statistical tracking variables
        axis_x = []
        axis_y = [[], []]
        i = 0

        running = True
        clock = pygame.time.Clock()
        dt = 0  # Delta time (time between frames, in milliseconds)

        max_frames = FPS * 600000 if not self.view else None  # 60 seconds default in headless
        frames = 0

        prev_alive1 = self.general1.get_unit_alive_number(self.battlefield)
        prev_alive2 = self.general2.get_unit_alive_number(self.battlefield)
        no_change_frames = 0
        max_no_change_frames = FPS * 50000  # 5 seconds of no-change => consider stalemate

        # ==================== Main real-time loop ====================
        while running:

            if self.view and hasattr(self.view, 'clock'):  # GUI has pygame.Clock
                dt =  self.view.clock.tick(FPS) / 1000  # Delta time in seconds
               
            elif self.view:
                # For Console : no pygame, time.sleep using
                time.sleep(1.0 / FPS)  # Framerate simulation
                dt = 1.0 / FPS
            else:
                # Without view mode
                dt = clock.tick(FPS * self.speed) / 1000  # Speed up in headless mode

            self.handle_event()
            if self._queued_battle is not None:
                self._apply_loaded_battle(self._queued_battle)
                self._queued_battle = None
                self.should_exit = False

            if not self.paused and self.winner is None:
                
                for _ in range(self.speed):
                    self.general1.play(self.battlefield)
                    if self.logger:
                        self.logger.log_info_from_general(self.general1, self.battlefield)

                    self.general2.play(self.battlefield)
                    if self.logger:
                        self.logger.log_info_from_general(self.general2, self.battlefield)

                    self.battlefield.update(dt)

                if self.general1.is_defeated(self.battlefield):
                    self.winner = self.general2
                    if self.view is None:
                        running = False
                elif self.general2.is_defeated(self.battlefield):
                    self.winner = self.general1
                    if self.view is None:
                        running = False

                if self.winner:
                    if self.logger :
                        self.logger.log(f"The winner is {self.winner.name}!: {self.winner.strategy}\n")
                    else:
                        print(f"\nThe winner is {self.winner.name} : {self.winner.strategy}!")
                        if isinstance(self.view, Console):
                            return

                    if self.view:
                        self.view.set_winner(self.winner)

                if is_tourney:
                    if repr(self.general1.strategy) == repr(self.general2.strategy) and repr(self.general1.strategy) == "Braindead":
                        print("Braindead VS Braindead. Declaring draw.")
                        self.winner = None
                        running = False
                 # === Stalemate / timeout detection ===

                    frames += 1
                    # Check alive counts and detect lack of progress
                    alive1 = self.general1.get_unit_alive_number(self.battlefield)
                    alive2 = self.general2.get_unit_alive_number(self.battlefield)
                    if alive1 == prev_alive1 and alive2 == prev_alive2:
                        no_change_frames += 1
                    else:
                        no_change_frames = 0
                        prev_alive1, prev_alive2 = alive1, alive2

                        #If not change for a long time -> declare draw and stop
                    if no_change_frames >= max_no_change_frames:
                        print("Stalemate detected (no unit change). Declaring draw.")
                        self.winner = None
                        running = False

                        # Absolute timeout in headless mode
                    if max_frames is not None and frames >= max_frames:
                        print("Match timeout reached. Declaring draw.")
                        self.winner = None
                        running = False

                if self.collectStats:
                    i += 1
                    axis_x.append(i)
                    axis_y[0].append(self.general1.get_unit_alive_number(self.battlefield))
                    axis_y[1].append(self.general2.get_unit_alive_number(self.battlefield))

                if self.view:
                    self.view.update()
                if self.winner is not None and self.view is not None:
                    running = False

        if self.view and self.winner is not None:

            exit_loop = True
            while exit_loop:
                clock.tick(FPS)

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        exit_loop = False
                    elif event.type == pygame.KEYDOWN:
                        # Press ESC to quit win screen
                        if event.key == pygame.K_ESCAPE:
                            exit_loop = False
                # Update screen of winner until user quit
                self.view.update()

        # ==================== Optional data visualization ====================
        if self.collectStats:
            plot(
                axis_x,
                axis_y,
                "Battle Statistics",
                "Time (frames)",
                "Remaining Units",
                [self.general1.strategy, self.general2.strategy],
                show=True,
                save_folder_path=PLOTS_FOLDER,
            )
        return self.winner


    def handle_event(self):
        """
        Processes user inputs and system events.
        
        Supported Keys:
        - TAB: Generate HTML snapshot and pause.
        - P: Toggle Pause.
        - F11 / F12: Quick Save / Quick Load.
        - F9: Switch to Console view.
        - F1 / F4: Toggle UI info panels.
        """
        
        # Skip event handling if no GUI pygame
        if not self.view or not hasattr(self.view, 'screen'):
            return

        # Instance Creation of reporter
        reporter = GameSnapshotReporter(self.general1, self.general2, self.battlefield)

        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return True

            elif event.type == pygame.KEYDOWN:
                #----------------------------------------- FOR TAB ----------------------------------------
                if event.key == pygame.K_TAB:
                    print("\nTAB détectée → snapshot + pause")
                    self.paused = True
                    if self.view:
                        self.view.pause = True # Update view
                    current_time_info = f"Frame {FPS}"

                    file_path = reporter.generate_snapshot(current_time_info)
                    webbrowser.open(f"file://{file_path}")
                #------------------------------------- QUICK SAVE ----------------------------------------
                elif event.key == pygame.K_F11:
                    try:
                        from util.SaveManager import SaveManager
                        path = SaveManager.save_battlepass(self)
                        print(f"\nQuick save written to {path}")
                    except Exception as exc:
                        print(f"\nQuick save failed: {exc}")
                #------------------------------------- QUICK LOAD ----------------------------------------
                elif event.key == pygame.K_F12:
                    try:
                        from util.SaveManager import SaveManager
                        self._queued_battle = SaveManager.load_battle(view_factory=None)
                        self.should_exit = True
                        print("\nQuick load triggered...")
                    except FileNotFoundError:
                        print("\nNo quick save file found.")
                    except Exception as exc:
                        print(f"\nQuick load failed: {exc}")

                #------------------------------------- PAUSE ------------------------------------------------
                elif event.key == pygame.K_p:
                    self.paused = not self.paused
                    if self.view:
                        self.view.pause = self.paused
                        self.view.update()
                #------------------------------------- QUIT (Q) ---------------------------------------------
                elif event.key == pygame.K_o:
                    pygame.quit()
                    exit()
                #---------------------------------- SPEED UP / SLOW DOWN ------------------------------------------
                elif event.key == pygame.K_RIGHT:
                    self.speed += 1
                elif event.key == pygame.K_LEFT:
                    if self.speed > 1:
                        self.speed -= 1
                #---------------------------------- SWITCH VIEW (Q) ------------------------------------------

                elif event.key == pygame.K_F9:
                    if isinstance (self.view, GUI):
                        pygame.display.quit()
                        self.terminal_view = Console(self.battlefield)
                        self.view = self.terminal_view
                    else:
                        pygame.display.quit()
                        self.view = GUI(self.battlefield, [self.general1, self.general2], False)

        if keys[pygame.K_F1] and self.view:
            self.view.hide_info_pannel()
        elif keys[pygame.K_F4] and self.view:
            self.view.show_info_pannel()

    def _apply_loaded_battle(self, loaded_battle):
        self.general1 = loaded_battle.general1
        self.general2 = loaded_battle.general2
        self.battlefield = loaded_battle.battlefield
        self.winner = None
        self.paused = loaded_battle.paused
        if self.view:
            self.view.battlefield = self.battlefield
            if hasattr(self.view, "generaux"):
                self.view.generaux = [self.general1, self.general2]
            if hasattr(self.view, "winner"):
                self.view.winner = None
            camera_state = getattr(loaded_battle, "camera_state", None)
            if camera_state:
                if hasattr(self.view, "zoom_factor") and "zoom_factor" in camera_state:
                    self.view.zoom_factor = camera_state["zoom_factor"]
                if hasattr(self.view, "zoom_x") and "zoom_x" in camera_state:
                    self.view.zoom_x = camera_state["zoom_x"]
                if hasattr(self.view, "zoom_y") and "zoom_y" in camera_state:
                    self.view.zoom_y = camera_state["zoom_y"]
                if hasattr(self.view, "capture_x") and hasattr(self.view, "zoom_x"):
                    self.view.capture_x = self.view.zoom_x
                if hasattr(self.view, "capture_y") and hasattr(self.view, "zoom_y"):
                    self.view.capture_y = self.view.zoom_y
