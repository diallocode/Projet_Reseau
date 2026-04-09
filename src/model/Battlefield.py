import math
import random
from Constant import UNIT_RADIUS
from Network.NetworkManager import NetworkManager

class Battlefield:
    """
    Continuous Real-Time Battlefield Simulation.

    Attributes
    ----------
    width : float
        The battlefield width (horizontal size).
    height : float
        The battlefield height (vertical size).
    troupes : dict
        Dictionnaire mapping army_id -> Army.
    """

    def __init__(self, width: float, height: float, troupes: dict, network_manager:NetworkManager, heightmap=None) -> None:
        """
        Initializes a continuous battlefield.

        Parameters
        ----------
        width : float
        height : float
        troupes : dict
            Initial mapping unit_id -> Unit.
        """
        if width <= 0 or height <= 0:
            raise ValueError("Width and height must be positive.")

       
        self.troupes = {}           # Dictionary will contains id:Unit
        self.width = width
        self.height = height
        self.heightmap = heightmap
        self.create_troupe(troupes)
        self.network_manager = network_manager
        self.diplomacy = {}         # New attribute for diplomacy management

    def set_relationship(self, player1_id, player2_id, relationship):
        """Définit la relation (ex: alliance) entre deux joueurs."""
        if player1_id not in self.diplomacy:
            self.diplomacy[player1_id] = {}
        self.diplomacy[player1_id][player2_id] = relationship

    # ==========================================================
    #                   UNIT MANAGEMENT
    # ==========================================================
    def create_troupe(self, units_dict):
        """
        Add unit in unit dictionary
        """
        if not isinstance(units_dict, dict):
            raise ValueError("units_dict should be a dictionary {id: unit_obj}")

        # Fast update of dictionary
        self.troupes.update(units_dict)

        # Link the battlefield and check unit positions
        for unit_id, unit in units_dict.items():
            unit.battlefield = self
            self.check_unit_position(unit)


    def check_unit_position(self, unit):
        """
        Check unit position
        """
        if unit.position is not None:
            if not self.is_valid_position(unit.position):
                print(f"Battlefield size: width={self.width}, height={self.height}")
                raise ValueError(f"Invalid position {unit.position} for unit {unit}")


    def remove_unit(self, unit_id):
        """ Remove unit via its id """
        if unit_id in self.troupes:
            self.troupes[unit_id].position = None
            del self.troupes[unit_id]

    def get_unit_at(self, position):
        for unit in self.troupes.values():
            if not unit.is_alive():
                continue
            if unit.position is None:
                continue
            if math.dist(unit.position, position) <= UNIT_RADIUS*2:
                return unit
        return None
    # ==========================================================
    #                   POSITION MANAGEMENT
    # ==========================================================
    def is_valid_position(self, position):
        x, y = position
        # x is horizontal coordinate -> compare with width
        # y is vertical coordinate -> compare with height
        return 0.0 <= x < self.width and 0.0 <= y < self.height

    # prevention of exits from the battlefield
    def clamp_position(self, position):
        x, y = position
        x = max(0.0, min(self.width - 0.001, x))
        y = max(0.0, min(self.height - 0.001, y))
        return (x, y)

    # ==========================================================
    #                   UNIT INTERACTIONS
    # ==========================================================
    def get_enemy_units(self, unit):
        """
        Retourne la liste des ennemis en fonction de l'appartenance réseau
        et des alliances diplomatiques en cours.
        """
        if unit is None:
            return []

        # On utilise notre nouvel attribut réseau !
        my_owner = getattr(unit, 'network_owner', unit.id // 1000)
        enemies = []

        for target_id, target_unit in self.troupes.items():
            if not target_unit.is_alive():
                continue
            
            if target_unit.id // 1000 == my_owner:
                continue  # Skip units from the same player

            #target_owner = getattr(target_unit, 'network_owner', target_id // 1000)

            # Résolution diplomatique
            # Par défaut, dans un jeu de guerre sauvage, les inconnus sont des ennemis
            relationship = "enemy" 
            
            # Si on a défini une relation spécifique avec ce joueur, on l'applique
            #if my_owner in self.diplomacy and target_owner in self.diplomacy[my_owner]:
            #    relationship = self.diplomacy[my_owner][target_owner]

            # Si c'est bien un ennemi, on l'ajoute à la liste des cibles
            if relationship == "enemy":
                enemies.append(target_unit)

        return enemies


    def find_nearby_enemies(self, unit, radius):
        enemies = self.get_enemy_units(unit)
        nearby = []
        if not unit.position:
            return nearby

        for e in enemies:
            if not e.position:
                continue
            dist = math.dist(unit.position, e.position)     # distance 
            if dist <= radius:
                nearby.append(e)
        return nearby


    # ==========================================================
    #                   UPDATE CYCLE
    # ==========================================================
    def _update_single_unit(self, unit, dt):
        if not unit.is_alive():
            return True
        print(f"Ordre actuel de l'unité {unit.id}: {unit.current_order}, cible: {unit.target_unit.id if unit.target_unit else 'None'}")
        unit.update(dt)
        if unit.position:
            unit.position = self.clamp_position(unit.position)
        return not unit.is_alive()

    # More nested list paths general->army->units
    def update(self,general, dt):
        """
        Met à jour toutes les unités directement depuis le dictionnaire.
        """
        # List of units for random mixing
        all_units = general.get_my_units(self)

        ids_to_remove = []
        for unit in all_units:
            if unit.is_alive():
                is_dead = self._update_single_unit(unit, dt)
                if is_dead:
                    ids_to_remove.append(unit.id)
            else:
                ids_to_remove.append(unit.id)

        # Cleaning
        for uid in ids_to_remove:
            self.remove_unit(uid)

    # ==========================================================
    #                   MAINTENANCE METHODS
    # ==========================================================
    def resetBattlefield(self):
        """ Clear all troup and position """
        for unit in self.troupes.values():
            unit.position = None
        self.troupes = {}

    # ==========================================================
    #                   REPRESENTATION
    # ==========================================================
    def __repr__(self):
        return f"Battlefield {self.width:.1f}x{self.height:.1f} with {len(self.troupes)} armies"


    # ==========================================================
    #                   ELEVATION
    # ==========================================================
    def get_height(self, x, y):
        if not self.heightmap:
            return 0

        x = max(0, min(self.width - 1, x))
        y = max(0, min(self.height - 1, y))

        x0 = int(math.floor(x))
        y0 = int(math.floor(y))
        x1 = min(x0 + 1, self.width - 1)
        y1 = min(y0 + 1, self.height - 1)

        dx = x - x0
        dy = y - y0

        h00 = self.heightmap[y0][x0]
        h10 = self.heightmap[y0][x1]
        h01 = self.heightmap[y1][x0]
        h11 = self.heightmap[y1][x1]

        h0 = h00 * (1 - dx) + h10 * dx
        h1 = h01 * (1 - dx) + h11 * dx
        return h0 * (1 - dy) + h1 * dy


    # ==========================================================
    #                   COLLISION
    # ==========================================================
    def is_position_free(self, unit, pos):
        for other in self.troupes.values():
            if other is unit:
                continue
            if not other.is_alive():
                continue

            dx = pos[0] - other.position[0]
            dy = pos[1] - other.position[1]
            if math.hypot(dx, dy) < UNIT_RADIUS*2:
                return False
        return True

    def informe_battlefield_state(self):
        """
        Envoie l'état actuel du champ de bataille au processus C pour synchronisation.
        """
        units_data = []
        for unit in self.troupes.values():
            if unit.position is None or not unit.is_alive():
                continue
            if unit.id // 1000 != self.general.player_id:
                continue  # On n'envoie que nos unités pour éviter les conflits de données
            units_data.append({
                "id": unit.id,
                "type": unit.name,
                "x": unit.position[0],
                "y": unit.position[1],
                "hp": unit.hp,
                "network_owner": self.general.player_id
            })

        message = {
            "type": "acknowledgment",
            "player_id": self.general.player_id,
            "units": units_data
        }
        self.network_manager.send_to_c(message)
    
    def _handle_new_player(self, data):
        """
        Intègre l'armée d'un nouvel arrivant sur la carte locale.
        data ressemble à : {"type": "handshake", "player_id": 2, "units": [...]}
        """
        
        "Supprimer tous les unités de ce joueur s'il existe déjà (cas de reconnexion)"
        units = self.troupes.values()
        for unit in list(units):  # list() pour éviter la modification pendant l'itération
            if getattr(unit, 'network_owner', -1) == data["player_id"]:
                self.remove_unit(unit.id)
        
        player_id = data["player_id"]
        remote_units = data["units"]
        from util.UnitsFactory import UnitsFactory

        factory = UnitsFactory()

        for u_data in remote_units:
            unit_id = u_data["id"] 
            unit_type = u_data["type"]
            
            # Création de l'unité
            new_unit = factory.create_unit(unit_id, unit_type)
            print(f"Création de l'unité {unit_id} de type {unit_type} pour le joueur {player_id}")
            
            # Forçage de l'état réseau
            new_unit.position = (u_data["x"], u_data["y"])
            new_unit.hp = u_data["hp"]
            new_unit.network_owner = player_id 
            new_unit.battlefield = self
            
            # Ajout au champ de bataille (risque de collision)
            self.troupes[unit_id] = new_unit
        print(f"Troupes après intégration du joueur {player_id}: {len(self.troupes)} unités sur le champ de bataille.")
            
        print(f"L'armée du joueur {player_id} a rejoint la bataille !")
        
        self.informe_battlefield_state()
        
    def _handle_disconnect(self, data):
        """
        Nettoie le champ de bataille lorsqu'un joueur se déconnecte.
        """
        player_id = data["player_id"]
        
      
        ids_to_remove = [
            uid for uid, unit in self.battlefield.troupes.items() 
            if getattr(unit, 'network_owner', -1) == player_id
        ]
        
        # On utilise la méthode existante pour les retirer proprement
        for uid in ids_to_remove:
            self.battlefield.remove_unit(uid)
            
        print(f"Le Joueur {player_id} s'est retiré ! {len(ids_to_remove)} unités ont fui le champ de bataille.")
        
        
    def _handle_unit_update(self, msg):
        """
        Met à jour l'état d'une unité sur la carte locale à partir d'un message réseau.
        Format attendu : {"type": "update", "id": 2010, "hp": 45, "network_owner": 1, "x": 50.5, "y": 42.0}
        """
        unit_id = msg.get("id")

        # Vérification de sécurité : l'unité existe-t-elle sur notre carte ?
        if unit_id not in self.troupes:
            # Optionnel : Tu peux décommenter le print pour débugger
            # print(f"[Réseau] Ignoré : Mise à jour pour l'unité inconnue ou morte ID {unit_id}")
            return

        # Récupération de l'unité cible
        unit = self.troupes[unit_id]

        # Mise à jour des valeurs (avec fallback sur les valeurs actuelles si manquantes)
        if "hp" in msg:
            unit.hp = msg["hp"]
        
        if "network_owner" in msg:
            unit.network_owner = msg["network_owner"]
            
        if "x" in msg and "y" in msg:
            unit.position = (msg["x"], msg["y"])

        # Nettoyage immédiat si le réseau nous informe de sa mort
        if unit.hp <= 0:
            unit.hp = 0
            # On purge ses ordres pour qu'elle arrête de bouger/attaquer instantanément
            unit.current_order = None
            unit.target_unit = None            
            self.remove_unit(unit_id)
    
    def push_network_event(self, event_data):
        print(f"Préparation d'un événement réseau : {event_data}")
        self.network_manager.send_to_c(event_data)