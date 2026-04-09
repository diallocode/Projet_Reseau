import threading # Plus moderne que _thread
import socket
import queue
import json
from Constant import HOST, PORT

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
        print("En attente du processus C pour recevoir l'ID...")
        self.send_to_c({"type": "connect"})
        
        while self.my_player_id is None: # On boucle tant qu'on n'a pas l'ID
            try:
                # On attend la réponse
                data, _ = self.socket.recvfrom(65535)
                print("bha un truc quoi!")
                msg = json.loads(data.decode('utf-8'))
                
                if msg.get("type") == "connected":
                    self.my_player_id = msg.get("player_id")
                    print(f"ID reçu avec succès : {self.my_player_id}")
                    return self.my_player_id # On retourne l'ID
            except Exception as e:
                print(f"Erreur durant l'initialisation : {e}")
                # Optionnel: ajouter un petit sleep ou une limite d'essais
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
