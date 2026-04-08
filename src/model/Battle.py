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
    """
    Bataille P2P : un général local + N généraux distants ajoutés dynamiquement.
    """

    def __init__(self, local_general: General, battlefield: Battlefield, view: View = None, datafile: str = None):
        self.battlefield = battlefield
        self.local_general = local_general
        self.remote_generals = []       # Ajoutés au fur et à mesure via add_remote_general()
        self.winner = None
        self.paused = False
        self.collectStats = False
        self.view = view
        self.logger = Logger(datafile) if datafile else None
        self.terminal_view = None
        self._queued_battle = None
        self.should_exit = False

        if self.view and hasattr(self.view, 'clock'):
            self.mode_terminal = False
        elif self.view:
            self.mode_terminal = True

        self.speed = 1 if self.view else HEADLESS_SPEEDUP

    # ===================================================================
    #              GESTION DES PARTICIPANTS DISTANTS
    # ===================================================================
    def add_remote_general(self, general: General, units: dict):
        """
        Appelé quand un nouveau joueur rejoint la partie via le réseau.
        Ajoute ses unités au battlefield et enregistre son général.
        """
        self.remote_generals.append(general)
        self.battlefield.create_troupe(units)
        if self.view and hasattr(self.view, 'generaux'):
            self.view.generaux.append(general)

    def get_all_generals(self):
        return [self.local_general] + self.remote_generals

    # ===================================================================
    #                      BOUCLE PRINCIPALE
    # ===================================================================

    def start(self, is_tourney=False):
        """
        Boucle principale de la bataille (Version 1 : Répartie & Best-Effort).
        """
        # --- Initialisation des outils de temps ---
        clock = pygame.time.Clock()
        running = True
        
        # Stats et monitoring
        axis_x, axis_y = [], []
        i = 0
        frames = 0
        max_frames = FPS * 600 if not self.view else None # Limite à 10min hors GUI
        
        # Pour la détection de match nul (stalemate)
        prev_alive = {g.id: g.get_unit_alive_number(self.battlefield) for g in self.get_all_generals()}
        no_change_frames = 0
        max_no_change_frames = FPS * 30 # 30 secondes sans mort = stalemate

        print(f"Lancement de la bataille V1 (Joueur local: {self.local_general.name})")

        # ===================================================================
        # BOUCLE UNIQUE (Fusion de l'attente et du combat pour la V1)
        # ===================================================================
        while running:
            # 1. Gestion du temps (Delta Time)
            if self.view and hasattr(self.view, 'clock'):
                dt = self.view.clock.tick(FPS) / 1000
            elif self.view:
                time.sleep(1.0 / FPS)
                dt = 1.0 / FPS
            else:
                dt = clock.tick(FPS * self.speed) / 1000

            # 2. Communication avec le processus C (Entrant)
            # On vérifie si le module réseau a reçu de nouveaux joueurs ou ordres
            # [C'est ici que tes collègues du C injectent des données via add_remote_general]
            self.check_for_network_updates() 

            # 3. Gestion des entrées utilisateur (Keyboard/Mouse)
            self.handle_event()

            # 4. Gestion des sauvegardes/chargements mis en file d'attente
            if self._queued_battle is not None:
                self._apply_loaded_battle(self._queued_battle)
                self._queued_battle = None
                self.should_exit = False

            # 5. Logique de Simulation (Si pas en pause et pas de vainqueur)
            if not self.paused and self.winner is None:
                
                # Faire jouer chaque général présent (Local + Distants reçus)
                # En V1, on simule en "best-effort" localement [cite: 162]
                for general in self.get_all_generals():
                    general.play(self.battlefield)
                    if self.logger:
                        self.logger.log_info_from_general(general, self.battlefield)

                # Mise à jour physique des positions et des combats
                self.battlefield.update(dt)

                # Vérification des conditions de victoire/défaite
                alive = [g for g in self.get_all_generals() if not g.is_defeated(self.battlefield)]

                if len(alive) == 1 and len(self.remote_generals) > 0:
                    self.winner = alive[0]
                    msg = f"The winner is {self.winner.name}!"
                    print(msg) if not self.logger else self.logger.log(msg)
                    if self.view:
                        self.view.set_winner(self.winner)
                    if self.view is None:
                        running = False

                elif len(alive) == 0:
                    print("Draw — all armies defeated simultaneously.")
                    running = False

                # Gestion spécifique au mode tournoi (Timeouts)
                if is_tourney:
                    frames += 1
                    current_alive = {g.id: g.get_unit_alive_number(self.battlefield) for g in self.get_all_generals()}
                    if current_alive == prev_alive:
                        no_change_frames += 1
                    else:
                        no_change_frames = 0
                        prev_alive = current_alive

                    if no_change_frames >= max_no_change_frames or (max_frames and frames >= max_frames):
                        print("End of simulation (Stalemate or Timeout).")
                        running = False

                # Collecte de statistiques
                if self.collectStats:
                    i += 1
                    axis_x.append(i)
                    for idx, g in enumerate(self.get_all_generals()):
                        while len(axis_y) <= idx: axis_y.append([])
                        axis_y[idx].append(g.get_unit_alive_number(self.battlefield))

            # 6. Rendu graphique
            if self.view:
                self.view.update()
                
            # Sortie propre si vainqueur détecté avec GUI
            if self.winner is not None and self.view is not None:
                running = False

        # --- Fin de la boucle : Écran de résultat ou Stats ---
        self.show_end_screen(clock)
        
        if self.collectStats:
            plot(axis_x, axis_y, "Battle Stats", "Frames", "Units", 
                 [g.name for g in self.get_all_generals()], show=True, save_folder_path=PLOTS_FOLDER)

        return self.winner

    
    def show_end_screen(self, clock):
        """ Gère l'attente sur l'écran de fin pour éviter la fermeture brutale. """
        if self.view and self.winner is not None:
            exit_loop = True
            while exit_loop:
                clock.tick(FPS)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                        exit_loop = False
                self.view.update()
    # ===================================================================
    #                         EVENTS
    # ===================================================================
    def handle_event(self):
        if not self.view or not hasattr(self.view, 'screen'):
            return

        reporter = GameSnapshotReporter(self.local_general, self.remote_generals, self.battlefield)
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    self.paused = True
                    if self.view:
                        self.view.pause = True
                    webbrowser.open(f"file://{reporter.generate_snapshot(f'Frame {FPS}')}")

                elif event.key == pygame.K_F11:
                    try:
                        from util.SaveManager import SaveManager
                        path = SaveManager.save_battlepass(self)
                        print(f"Quick save → {path}")
                    except Exception as e:
                        print(f"Quick save failed: {e}")

                elif event.key == pygame.K_F12:
                    try:
                        from util.SaveManager import SaveManager
                        self._queued_battle = SaveManager.load_battle(view_factory=None)
                        self.should_exit = True
                    except Exception as e:
                        print(f"Quick load failed: {e}")

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

                elif event.key == pygame.K_F9:
                    if isinstance(self.view, GUI):
                        pygame.display.quit()
                        self.view = Console(self.battlefield)
                    else:
                        pygame.display.quit()
                        self.view = GUI(self.battlefield, self.get_all_generals(), False)

        if keys[pygame.K_F1] and self.view:
            self.view.hide_info_pannel()
        elif keys[pygame.K_F4] and self.view:
            self.view.show_info_pannel()

    # ===================================================================
    #                         LOAD
    # ===================================================================
    def _apply_loaded_battle(self, loaded_battle):
        self.local_general = loaded_battle.local_general
        self.remote_generals = loaded_battle.remote_generals
        self.battlefield = loaded_battle.battlefield
        self.winner = None
        self.paused = loaded_battle.paused

        if self.view:
            self.view.battlefield = self.battlefield
            if hasattr(self.view, 'generaux'):
                self.view.generaux = self.get_all_generals()
            if hasattr(self.view, 'winner'):
                self.view.winner = None

            camera_state = getattr(loaded_battle, 'camera_state', None)
            if camera_state:
                for attr in ['zoom_factor', 'zoom_x', 'zoom_y']:
                    if hasattr(self.view, attr) and attr in camera_state:
                        setattr(self.view, attr, camera_state[attr])

    def check_for_network_updates(self):
        
        pass