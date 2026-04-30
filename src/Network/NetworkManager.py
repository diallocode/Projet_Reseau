import threading # Plus moderne que _thread
import socket
import queue
import json
from Constant import HOST, PORT
import os

MYPORT = 5003

class NetworkManager:
    def __init__(self, host=HOST, port=PORT): 
        self.message_queue = queue.Queue()
        self.my_player_id = None
        
        # 1. Setup UDP
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # On augmente le buffer de réception au niveau de l'OS (optionnel mais recommandé)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        # On définit l'adresse du C
        self.c_address = (host, port)

        # On bind notre socket à MYPORT pour recevoir les messages du C
        self.socket.bind((HOST, MYPORT))

        # 2. Handshake (Phase bloquante)
        self.wait_initialization()

        # 3. Lancement du thread (Utilisation de threading.Thread)
        self.listener_thread = threading.Thread(target=self.listen_for_messages, daemon=True)
        self.listener_thread.start()


    def wait_initialization(self):
        print("Initialisation locale de l'ID joueur...")
        try:
            # 1. Tentative de récupération du PID
            id_joueur = os.getpid()
            
            # 2. Vérification de la validité de l'ID
            if id_joueur is None or id_joueur <= 0:
                raise ValueError("L'OS a renvoyé un PID invalide.")

            # 3. Assignation
            self.my_player_id = id_joueur
            print(f"ID attribué (PID) : {self.my_player_id}")

            # 4. Notification au processus C
            # Même si l'ID est local, le C doit savoir qui on est pour nous router les messages
            self.send_to_c({"type": "connected", "player_id": self.my_player_id})

        except OSError as e:
            print(f"Erreur système lors de la récupération du PID : {e}")
            self.my_player_id = 0 # Valeur par défaut pour éviter 'None'
        except Exception as e:
            print(f"Erreur inattendue : {e}")
            self.my_player_id = 0
        
            
    def listen_for_messages(self):
        while True:
            try:
                # Augmenté à 65535 pour les gros messages de config
                data, _ = self.socket.recvfrom(65535)
                if not data: continue
            
                msg = json.loads(data.decode('utf-8'))
                self.message_queue.put(msg)
            except Exception as e:
                print(f"Erreur d'écoute : {e}")
                break

    def send_to_c(self, message):
        try:
            data = json.dumps(message).encode('utf-8')
            # sendto retourne le nombre d'octets envoyés
            sent_bytes = self.socket.sendto(data, self.c_address)
            print(f"[Network] {sent_bytes} octets envoyés à C : {message}")
        except Exception as e:
            print(f"[Network] Erreur envoi : {e}")
            
    def get_messages(self):
        """
        Dépile et retourne tous les messages actuellement dans la file d'attente.
        C'est une méthode non-bloquante.
        """
        messages = []
        # Tant que la file n'est pas vide, on retire le message le plus ancien
        while not self.message_queue.empty():
            try:
                # get_nowait() retire l'élément sans bloquer le programme
                msg = self.message_queue.get_nowait()
                messages.append(msg)
            except queue.Empty:
                break

        return messages
