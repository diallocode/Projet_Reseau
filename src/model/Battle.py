from Network.NetworkManager import NetworkManager
from model.General import General
from view.View import View
from model.Battlefield import Battlefield
from Constant import FPS, PLOTS_FOLDER, HEADLESS_SPEEDUP
from util.Functions import plot
import pygame
from util.Logger import Logger
from .GameSnapshotReporter import GameSnapshotReporter
import webbrowser
from view.Console import Console
from view.GUI import GUI
import time


class Battle:

    def __init__(self, general: General, battlefield: Battlefield, network_manager: NetworkManager, view: View = None):
        self.battlefield = battlefield
        self.general = general
        self.paused = False
        self.view = view
        self._last_network_send = 0
        self.should_exit = False

        if self.view and hasattr(self.view, 'clock'):
            self.mode_terminal = False
        elif self.view:
            self.mode_terminal = True

   # ===================================================================
   #                           MAIN SIMULATION
   # ===================================================================
    def start(self, network_data, is_tourney=False):
        if self.view and hasattr(self.view, 'screen'):  # GUI has screen attribute
            # Pygame already initialized in GUI.__init__
            pass

        running = True
        clock = pygame.time.Clock()
        dt = 0  # Delta time (time between frames, in milliseconds)
        start = False
       # ==================== Main real-time loop ====================
        while running:
            if start:
                if self.view and hasattr(self.view, 'clock'):  # GUI has pygame.Clock
                    dt =  self.view.clock.tick(FPS) / 1000  # Delta time in seconds
                elif self.view:
                    # For Console : no pygame, time.sleep using
                    time.sleep(1.0 / FPS)  # Framerate simulation
                    dt = 1.0 / FPS
                else:
                    # Without view mode
                    dt = clock.tick(FPS * self.speed) / 1000  # Speed up in headless mode    
                for msg in self.network_manager.get_messages():
                    if msg["type"] == "handshake":
                        print(f"Handshake reçu pour le player {msg['player_id']} avec {len(msg['units'])} unités")
                        self.battlefield._handle_new_player(msg, self.general)
                    elif msg["type"] == "update":
                        print(f"Update reçu pour l'unité {msg['id']} du player {msg['network_owner']}")
                        self.battlefield._handle_unit_update(msg)
                    elif msg["type"] == "player_disconnected":
                        self.battlefield._handle_disconnect(msg)
                    elif msg["type"] == "acknowledgment":
                        print(f"Acknowledgment reçu pour le message")
                        self.battlefield._handle_acknowledgment(msg)
                    else:
                        print(f"Message inconnu reçu : {msg}")
                self.handle_event()
                if not self.paused:
                    for _ in range(self.speed):
                        self.general.play(self.battlefield)
                        self.battlefield.update(self.general,dt)
                    if self.view:
                        self.view.update()
            else:
                self.network_manager.send_to_c(network_data)
                start = True
        if self.view:
            exit_loop = True
            while exit_loop:
                clock.tick(FPS)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        exit_loop = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            exit_loop = False
                self.view.update()

    # ===================================================================
    #                           RÉSEAU
    # ===================================================================
    def _send_handshake(self):
        """Annonce notre armée complète à l'adversaire au démarrage."""
        units_data = []
        for unit in self.battlefield.troupes.values():
            if unit.position is None or not unit.is_alive():
                continue
            if unit.id // 1000 != self.general.id:
                continue
            units_data.append({
                "id": unit.id,
                "type": unit.name,
                "x": unit.position[0],
                "y": unit.position[1],
                "hp": unit.hp,
                "network_owner": self.general.id
            })
        self.network_manager.send_to_c({
            "type": "handshake",
            "player_id": self.general.id,
            "units": units_data
        })
        print(f"[Réseau] Handshake envoyé avec {len(units_data)} unités.")

    def _send_update(self):
        """Envoie les positions de nos unités, max 10 fois par seconde."""
        now = time.time()
        if now - self._last_network_send < 0.1:
            return
        self._last_network_send = now

        for unit in self.battlefield.troupes.values():
            if unit.position is None or not unit.is_alive():
                continue
            if unit.id // 1000 != self.general.id:
                continue
            self.network_manager.send_to_c({
                "type": "update",
                "id": unit.id,
                "x": unit.position[0],
                "y": unit.position[1],
                "hp": unit.hp,
                "network_owner": self.general.id
            })

    # ===================================================================
    #                           EVENTS
    # ===================================================================
    def handle_event(self):
        if not self.view or not hasattr(self.view, 'screen'):
            return

        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return True

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    print("\nTAB détectée → snapshot + pause")
                    self.paused = True
                    if self.view:
                        self.view.pause = True
                    current_time_info = f"Frame {FPS}"
                    webbrowser.open(f"file://{file_path}")

                elif event.key == pygame.K_F11:
                    try:
                        from util.SaveManager import SaveManager
                        path = SaveManager.save_battlepass(self)
                        print(f"\nQuick save written to {path}")
                    except Exception as exc:
                        print(f"\nQuick save failed: {exc}")

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

                elif event.key == pygame.K_p:
                    self.paused = not self.paused
                    if self.view:
                        self.view.pause = self.paused
                        self.view.update()

                elif event.key == pygame.K_o:
                    pygame.quit()
                    exit()

                elif event.key == pygame.K_RIGHT:
                    self.speed += 1

                elif event.key == pygame.K_LEFT:
                    if self.speed > 1:
                        self.speed -= 1

        if keys[pygame.K_F1] and self.view:
            self.view.hide_info_pannel()
        elif keys[pygame.K_F4] and self.view:
            self.view.show_info_pannel()

    # ===================================================================
    #                           SAVE / LOAD
    # ===================================================================
    def _apply_loaded_battle(self, loaded_battle):
        self.general = loaded_battle.general
        self.battlefield = loaded_battle.battlefield
        self.winner = None
        self.paused = loaded_battle.paused
        if self.view:
            self.view.battlefield = self.battlefield
            if hasattr(self.view, "generaux"):
                self.view.generaux = [self.general]
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