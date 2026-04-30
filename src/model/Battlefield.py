import math
import time
import random
from Constant import UNIT_RADIUS
from Network.NetworkManager import NetworkManager
from model.General import General
from util.Functions import create_strategy

# Délai maximum (en secondes) avant de forcer le déverrouillage d'une unité
LOCK_TIMEOUT = 3.0


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
        Dictionnaire mapping unit_id -> Unit.
    diplomacy : dict
        Mapping player_id -> {other_player_id -> relationship}.
    """

    def __init__(self, width: float, height: float, generaux: list, troupes: dict,
                 network_manager: NetworkManager, heightmap=None) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("Width and height must be positive.")

        self.troupes = {}
        self.width = width
        self.height = height
        self.heightmap = heightmap
        self.generaux = generaux
        self.nb_pb_incoherence_handled = 0
        self.network_manager = network_manager
        self.diplomacy = {}

        self.create_troupe(troupes)

    # ==========================================================
    #                   DIPLOMACY
    # ==========================================================

    def set_relationship(self, player1_id, player2_id, relationship):
        """Définit la relation (ex: 'ally', 'enemy') entre deux joueurs."""
        self.diplomacy.setdefault(player1_id, {})[player2_id] = relationship
        self.diplomacy.setdefault(player2_id, {})[player1_id] = relationship

    def _handle_alliance(self, msg):
        player_id = msg.get("player_id")
        ally_id = msg.get("ally_id")
        self.set_relationship(player_id, ally_id, "ally")

    # ==========================================================
    #                   UNIT MANAGEMENT
    # ==========================================================

    def create_troupe(self, units_dict):
        """Ajoute un dictionnaire d'unités au champ de bataille."""
        if not isinstance(units_dict, dict):
            raise ValueError("units_dict should be a dictionary {id: unit_obj}")
        self.troupes.update(units_dict)
        for unit in units_dict.values():
            unit.battlefield = self
            self.check_unit_position(unit)

    def check_unit_position(self, unit):
        """Vérifie que la position d'une unité est dans les limites du champ de bataille."""
        if unit.position is not None and not self.is_valid_position(unit.position):
            raise ValueError(
                f"Invalid position {unit.position} for unit {unit} "
                f"(battlefield {self.width}x{self.height})"
            )

    def remove_unit(self, unit_id):
        """Retire une unité du champ de bataille par son ID."""
        unit = self.troupes.pop(unit_id, None)
        if unit:
            unit.position = None

    def get_unit_at(self, position):
        """Retourne l'unité vivante à la position donnée (dans un rayon de 2*UNIT_RADIUS)."""
        for unit in self.troupes.values():
            if not unit.is_alive() or unit.position is None:
                continue
            if math.dist(unit.position, position) <= UNIT_RADIUS * 2:
                return unit
        return None

    # ==========================================================
    #                   POSITION MANAGEMENT
    # ==========================================================

    def is_valid_position(self, position):
        x, y = position
        return 0.0 <= x < self.width and 0.0 <= y < self.height

    def clamp_position(self, position):
        """Empêche une unité de sortir du champ de bataille."""
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
        my_owner = unit.id // 1000  # ID du joueur propriétaire 
        
        
        enemies = []

        for target_id, target_unit in self.troupes.items():
            if not target_unit.is_alive():
                continue
            
            if target_unit.id // 1000 == my_owner:
                continue  # Skip units from the same player

            target_owner = target_unit.id // 1000
            
           
            # Résolution diplomatique
            # Par défaut, dans un jeu de guerre sauvage, les inconnus sont des ennemis
            relationship = "enemy" 
            
            # Si on a défini une relation spécifique avec ce joueur, on l'applique
            if my_owner in self.diplomacy and target_owner in self.diplomacy[my_owner]:
                relationship = self.diplomacy[my_owner][target_owner]

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
    #                   LOCK MANAGEMENT
    # ==========================================================

    def _lock_unit(self, unit):
        """Verrouille une unité et enregistre l'horodatage du verrou."""
        print(f"[Lock] Unité {unit.id} verrouillée pour action réseau.")
        unit.network_locked = True
        unit.lock_timestamp = time.time()

    def _unlock_unit(self, unit_id_or_unit):
        """
        Déverrouille une unité de façon sécurisée.
        Accepte un ID ou une référence directe à l'unité.
        """
        print(f"[Unlock] Unité {unit_id_or_unit} déverrouillée.")
        if isinstance(unit_id_or_unit, int):
            unit = self.troupes.get(unit_id_or_unit)
        else:
            unit = unit_id_or_unit

        if unit:
            unit.network_locked = False
            unit.lock_timestamp = 0.0

    def _check_lock_timeout(self, unit):
        """
        Déverrouille l'unité si son verrou a expiré (protection contre les locks permanents).
        Retourne True si l'unité a été déverrouillée par timeout.
        """
        if unit.network_locked:
            elapsed = time.time() - getattr(unit, 'lock_timestamp', 0)
            if elapsed > LOCK_TIMEOUT:
                print(f"[Timeout] Unité {unit.id} déverrouillée après {elapsed:.1f}s.")
                self._unlock_unit(unit)
                return True
        return False

    # ==========================================================
    #                   UPDATE CYCLE
    # ==========================================================

    def _update_single_unit(self, unit, general, dt):
        """
        Met à jour une unité pour un tick de simulation.
        Retourne True si l'unité est morte (à retirer).
        """
        if not unit.is_alive():
            unit.network_locked = False
            return True

        # Déverrouillage automatique en cas de timeout
        self._check_lock_timeout(unit)

        # Appartenance de l'unité : on se base uniquement sur network_owner
        my_unit = (getattr(unit, 'network_owner', -1) == general.id)

        if my_unit:
            if not unit.network_locked:
                if unit.current_order == "move" and unit.target_pos:
                    unit.update(dt)

                elif unit.current_order == "attack" and unit.target_unit:
                    target = unit.target_unit
                    if not target.is_alive():
                        unit.current_order = None
                        unit.target_unit = None
                    elif getattr(target, 'network_owner', -1) == general.id:
                        # On possède déjà la cible : attaque directe
                        unit.update(dt)
                    else:
                        # On doit d'abord récupérer la propriété de la cible
                        self.network_manager.send_to_c({
                            "type": "property_request",
                            "unit_id": unit.id,
                            "actual_owner": target.network_owner,
                            "ask_property_owner": general.id,
                            "target_unit_actual_owner": target.network_owner,
                            "target_unit_id": target.id,
                            "dest_x": target.position[0],
                            "dest_y": target.position[1],
                            "action": "attack",
                            "damage": unit.compute_damage(unit, target)
                        })
                        self._lock_unit(unit)
                        self.nb_pb_incoherence_handled += 1

        else:
            # Unité appartenant à un autre joueur : on interpole seulement
            unit.update(dt)

        # Serrage de position en fin de tick
        if unit.position:
            unit.position = self.clamp_position(unit.position)

        return not unit.is_alive()

    def update(self, general, dt):
        """Met à jour toutes les unités du champ de bataille pour un tick."""
        all_units = list(self.troupes.values())
        ids_to_remove = []

        for unit in all_units:
            if unit.is_alive():
                is_dead = self._update_single_unit(unit, general, dt)
                if is_dead:
                    ids_to_remove.append(unit.id)
            else:
                ids_to_remove.append(unit.id)

        for uid in ids_to_remove:
            self.remove_unit(uid)

    # ==========================================================
    #                   NETWORK EVENT HANDLING
    # ==========================================================

    def push_network_event(self, event_data):
        """Envoie un événement réseau au processus C."""
        self.network_manager.send_to_c(event_data)

    def _handle_unit_update(self, msg):
        """
        Met à jour l'état d'une unité à partir d'un message réseau entrant.
        Format attendu : {"type": "update", "id": 2010, "hp": 45,
                          "network_owner": 1, "x": 50.5, "y": 42.0, current_order: "move", target_unit: unit, target_pos: (x,y)}
        """
        unit_id = msg.get("id")
        if unit_id not in self.troupes:
            return

        unit = self.troupes[unit_id]

        if "hp" in msg:
            unit.hp = msg["hp"]
        if "network_owner" in msg:
            unit.network_owner = msg["network_owner"]
        if "x" in msg and "y" in msg:
            unit.target_pos = (msg["x"], msg["y"])
            unit.current_order = "move"

        if unit.hp <= 0:
            unit.hp = 0
            unit.current_order = None
            unit.target_unit = None
            self.remove_unit(unit_id)
        if "current_order" in msg:
            unit.current_order = msg["current_order"]
        if "target_unit" in msg:
            target_unit_id = msg["target_unit"]
        if "target_pos" in msg:
            unit.target_pos = msg["target_pos"]

    def _handle_property_request(self, msg, general):
        """
        Traite une demande de propriété émise par le processus C.

        Format attendu :
        {
            "type": "property_request",
            "unit_id": <int>,
            "target_unit_id": <int>,
            "actual_owner": <int>,
            "target_unit_actual_owner": <int>,
            "ask_property_owner": <int>,
            "action": "attack" | "move" | "info",
            "dest_x": <float>,
            "dest_y": <float>,
            "damage": <float>
        }
        """
        print(f"[PropertyRequest] {msg}")

        action = msg.get("action")

        # L'unité à céder dépend de l'action
        owned_unit_id = msg.get("target_unit_id") if action == "attack" else msg.get("unit_id")

        if owned_unit_id not in self.troupes:
            print(f"[PropertyRequest] Unité inconnue ID {owned_unit_id}")
            return

        owned_unit = self.troupes[owned_unit_id]

        if owned_unit.network_owner != general.id:
            print(
                f"[PropertyRequest] Unité {owned_unit_id} non contrôlée "
                f"(appartient à {owned_unit.network_owner})"
            )
            return

        # Transfert de propriété
        owned_unit.network_owner = msg.get("ask_property_owner", owned_unit.network_owner)

        self.push_network_event({
            "type": "property_answer",
            "unit_id": msg.get("unit_id"),
            "target_unit_id": msg.get("target_unit_id"),
            "actual_owner": owned_unit.network_owner,
            "hp": owned_unit.hp,
            "x": owned_unit.position[0] if owned_unit.position else None,
            "y": owned_unit.position[1] if owned_unit.position else None,
            "action": action,
            "dest_x": msg.get("dest_x"),
            "dest_y": msg.get("dest_y"),
            "damage": msg.get("damage"),
            "target_unit_actual_owner": msg.get("target_unit_actual_owner")
        })

    def _handle_property_answer(self, msg, general):
        """
        Traite la réponse à une demande de propriété.

        Format attendu :
        {
            "type": "property_answer",
            "unit_id": <int>,
            "target_unit_id": <int>,
            "actual_owner": <int>,
            "hp": <float>,
            "x": <float>, "y": <float>,
            "action": "attack" | "move" | "info",
            "dest_x": <float>, "dest_y": <float>,
            "damage": <float>,
            "target_unit_actual_owner": <int>
        }
        """
        print(f"[PropertyAnswer] {msg}")

        unit_id = msg.get("unit_id")
        unit = self.troupes.get(unit_id)

        # --- Vérifications préliminaires ---
        if not unit:
            print(f"[PropertyAnswer] Unité attaquante inconnue ID {unit_id}")
            return

        if msg.get("actual_owner") != general.id:
            print(
                f"[PropertyAnswer] Réponse ignorée : unité cible appartient "
                f"à {msg.get('actual_owner')}, pas à {general.id}"
            )
            # On déverrouille quand même pour éviter un blocage
            self._unlock_unit(unit)
            return

        action = msg.get("action")
        target_unit_id = msg.get("target_unit_id")

        try:
            if action == "attack":
                self._apply_attack(msg, unit, target_unit_id, general)

            elif action == "move":
                self._apply_move(msg, unit, general)

            elif action == "info":
                # "info" sert à récupérer la propriété de l'attaquant avant d'attaquer
                # On re-émet ensuite une vraie property_request d'attaque
                escalated = self._apply_info_then_attack(msg, unit, general)
                if escalated:
                    return  # L'unité reste verrouillée jusqu'à la réponse d'attaque

            else:
                print(f"[PropertyAnswer] Action inconnue : {action}")

        finally:
            # Déverrouillage garanti dans tous les cas sauf si on a re-verrouillé
            # pour l'escalade info→attack (géré par _apply_info_then_attack)
            if unit and not getattr(unit, 'network_locked', False):
                pass  # Déjà déverrouillé ou jamais verrouillé
            elif action != "info":
                self._unlock_unit(unit)

    # --- Sous-méthodes de _handle_property_answer ---

    def _apply_attack(self, msg, unit, target_unit_id, general):
        """Applique les dégâts à la cible et synchronise le réseau si elle meurt."""
        target_unit = self.troupes.get(target_unit_id)
        if not target_unit:
            print(f"[Attack] Cible inconnue ID {target_unit_id}")
            self._unlock_unit(unit)
            return

        # Synchronisation de l'état reçu
        target_unit.network_owner = general.id
        target_unit.hp = msg["hp"]
        if msg.get("x") is not None and msg.get("y") is not None:
            target_unit.position = (msg["x"], msg["y"])

        # Application des dégâts
        damage = msg.get("damage", 0)
        target_unit.hp -= damage
        print(f"[Attack] Unité {target_unit.id} reçoit {damage} dégâts → HP restant : {target_unit.hp}")

        if target_unit.hp <= 0:
            target_unit.hp = 0
            target_unit.current_order = None
            target_unit.target_unit = None
            self.push_network_event({
                "type": "update",
                "id": target_unit.id,
                "hp": 0,
                "network_owner": target_unit.network_owner,
                "x": target_unit.position[0] if target_unit.position else None,
                "y": target_unit.position[1] if target_unit.position else None,
            })
            self.remove_unit(target_unit.id)

        self._unlock_unit(unit)

    def _apply_move(self, msg, unit, general):
        """Applique un ordre de mouvement à une unité après transfert de propriété."""
        unit.network_owner = general.id
        unit.hp = msg["hp"]

        if unit.hp <= 0:
            unit.hp = 0
            unit.current_order = None
            unit.target_unit = None
            self.remove_unit(unit.id)
            # remove_unit appelle already self._unlock_unit implicitement via position = None
            return

        if msg.get("x") is not None and msg.get("y") is not None:
            unit.position = (msg["x"], msg["y"])

        unit.current_order = "move"
        unit.target_pos = (msg.get("dest_x"), msg.get("dest_y"))
        self._unlock_unit(unit)
        unit.update(0)  # Application immédiate de la nouvelle direction

    def _apply_info_then_attack(self, msg, unit, general):
        """
        Phase "info" : on a récupéré la propriété de l'attaquant.
        On émet maintenant la vraie property_request d'attaque sur la cible.
        Retourne True si l'unité a été re-verrouillée (escalade réussie).
        """
        unit.network_owner = general.id
        unit.hp = msg["hp"]

        if msg.get("x") is not None and msg.get("y") is not None:
            unit.position = (msg["x"], msg["y"])

        if unit.hp <= 0:
            unit.hp = 0
            unit.current_order = None
            unit.target_unit = None
            self.push_network_event({
                "type": "update",
                "id": unit.id,
                "hp": 0,
                "network_owner": unit.network_owner,
                "x": unit.position[0] if unit.position else None,
                "y": unit.position[1] if unit.position else None,
            })
            self.remove_unit(unit.id)
            self._unlock_unit(unit)
            return False

        # Escalade vers l'attaque effective
        self.network_manager.send_to_c({
            "type": "property_request",
            "unit_id": unit.id,
            "actual_owner": msg.get("target_unit_actual_owner"),
            "ask_property_owner": general.id,
            "target_unit_actual_owner": msg.get("target_unit_actual_owner"),
            "target_unit_id": msg.get("target_unit_id"),
            "dest_x": msg.get("dest_x"),
            "dest_y": msg.get("dest_y"),
            "action": "attack",
            "damage": msg.get("damage")
        })
        self._lock_unit(unit)  # On reste verrouillé jusqu'à la réponse d'attaque
        return True

    # ==========================================================
    #                   PLAYER CONNECTION / DISCONNECTION
    # ==========================================================

    def informe_battlefield_state(self, general: General):
        """
        Envoie l'état de nos propres unités au processus C pour synchronisation initiale.
        """
        units_data = [
            {
                "id": unit.id,
                "type": unit.name,
                "x": unit.position[0],
                "y": unit.position[1],
                "hp": unit.hp,
                "network_owner": general.id
            }
            for unit in self.troupes.values()
            if unit.position is not None and unit.is_alive()
            and unit.id // 1000 == general.id
        ]
        self.push_network_event({
            "type": "acknowledgment",
            "player_id": general.id,
            "units": units_data
        })

    def _integrate_remote_player(self, player_id: int, remote_units: list):
        """
        Logique commune d'intégration d'un joueur distant (handshake ou acknowledgment).
        Supprime les anciennes unités du joueur si présentes, puis les recrée.
        """
        from util.UnitsFactory import UnitsFactory
        factory = UnitsFactory()

        # Nettoyage des anciennes unités de ce joueur (reconnexion)
        stale_ids = [
            uid for uid, u in self.troupes.items()
            if getattr(u, 'network_owner', -1) == player_id
        ]
        for uid in stale_ids:
            self.remove_unit(uid)

        for u_data in remote_units:
            unit_id = u_data["id"]
            unit_type = u_data["type"]
            new_unit = factory.create_unit(unit_id, unit_type)
            new_unit.position = (u_data["x"], u_data["y"])
            new_unit.hp = u_data["hp"]
            new_unit.network_owner = player_id
            new_unit.battlefield = self
            self.troupes[unit_id] = new_unit
            print(f"  ↳ Unité {unit_id} ({unit_type}) pour joueur {player_id} intégrée.")

        print(
            f"[Intégration] Joueur {player_id} : {len(remote_units)} unités ajoutées. "
            f"Total sur le champ : {len(self.troupes)}"
        )

    def _handle_new_player(self, data, general, ack):
        """
        Intègre l'armée d'un nouvel arrivant (handshake).
        Si ack=False, on répond avec notre propre état.
        """
        player_id = data["player_id"]
        print(f"[Handshake] Nouveau joueur {player_id}")

        self.generaux.append(
            General(f"General {player_id}", player_id, create_strategy(data.get("ia_strategy")))
        )
        self._integrate_remote_player(player_id, data.get("units", []))

        if not ack:
            self.informe_battlefield_state(general)

    def _handle_acknowledgment(self, data):
        """
        Intègre l'armée d'un joueur existant reçue en réponse à notre handshake.
        """
        player_id = data["player_id"]
        print(f"[Acknowledgment] Joueur {player_id}")
        self._integrate_remote_player(player_id, data.get("units", []))

    def _handle_disconnect(self, data):
        """
        Nettoie le champ de bataille lorsqu'un joueur se déconnecte.
        """
        player_id = data["player_id"]
        ids_to_remove = [
            uid for uid, unit in self.troupes.items()
            if getattr(unit, 'network_owner', -1) == player_id
        ]
        for uid in ids_to_remove:
            self.remove_unit(uid)
        print(f"[Disconnect] Joueur {player_id} retiré : {len(ids_to_remove)} unités supprimées.")

    # ==========================================================
    #                   MAINTENANCE
    # ==========================================================

    def resetBattlefield(self):
        """Vide toutes les unités et réinitialise leurs positions."""
        for unit in self.troupes.values():
            unit.position = None
        self.troupes.clear()

    # ==========================================================
    #                   ELEVATION
    # ==========================================================

    def get_height(self, x, y):
        """Retourne la hauteur interpolée bilinéairement à la position (x, y)."""
        if not self.heightmap:
            return 0

        x = max(0, min(self.width - 1, x))
        y = max(0, min(self.height - 1, y))

        x0, y0 = int(math.floor(x)), int(math.floor(y))
        x1 = min(x0 + 1, int(self.width) - 1)
        y1 = min(y0 + 1, int(self.height) - 1)

        dx, dy = x - x0, y - y0

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
        """Retourne True si aucune unité vivante n'occupe la position donnée."""
        for other in self.troupes.values():
            if other is unit or not other.is_alive():
                continue
            if math.hypot(pos[0] - other.position[0], pos[1] - other.position[1]) < UNIT_RADIUS * 2:
                return False
        return True

    # ==========================================================
    #                   REPRESENTATION
    # ==========================================================

    def __repr__(self):
        return f"Battlefield {self.width:.1f}x{self.height:.1f} with {len(self.troupes)} units"