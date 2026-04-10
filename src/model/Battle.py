from Network.NetworkManager import NetworkManager
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

   def __init__(self, general: General, battlefield: Battlefield, network_manager: NetworkManager , view:View = None):
       """
       Initializes the battle environment, participants, and optional logger/view.
       """
       self.battlefield = battlefield
       self.general = general
       self.paused = False
       self.view = view
     
       self.should_exit = False
       if self.view and hasattr(self.view, 'clock'):
           self.mode_terminal = False
       elif self.view:
           self.mode_terminal = True
           
       if not self.view:
           self.speed = HEADLESS_SPEEDUP
       else: 
           self.speed = 1
       self.network_manager: NetworkManager = network_manager


   # ===================================================================
   #                           MAIN SIMULATION
   # ===================================================================
   def start(self,is_tourney=False):
        if self.view and hasattr(self.view, 'screen'):  # GUI has screen attribute
            # Pygame already initialized in GUI.__init__
            pass
        running = True
        clock = pygame.time.Clock()
        dt = 0  # Delta time (time between frames, in milliseconds)

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
                    print(f"Acknowledgment reçu pour le message ID {msg['message_id']} du player {msg['player_id']}")
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
        if self.view:
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
                self.view.update()

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


       if keys[pygame.K_F1] and self.view:
           self.view.hide_info_pannel()
       elif keys[pygame.K_F4] and self.view:
           self.view.show_info_pannel()


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




