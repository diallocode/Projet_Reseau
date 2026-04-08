import threading # Plus moderne que _thread
import socket
import queue
import json
from src.Constant import HOST, PORT

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

        # 2. Handshake (Phase bloquante)
        self.wait_initialization()

        # 3. Lancement du thread (Utilisation de threading.Thread)
        self.listener_thread = threading.Thread(target=self.listen_for_messages, daemon=True)
        self.listener_thread.start()

    def wait_initialization(self):
        print("En attente du processus C pour recevoir l'ID...")
        # On envoie un petit "Hello" au C pour qu'il connaisse notre port
        self.send_to_c({"type": "hello"})
        
        # On attend la réponse (Buffer de 65k pour être large)
        data, _ = self.socket.recvfrom(65535)
        msg = json.loads(data.decode('utf-8'))
        
        if msg.get("type") == "init":
            self.my_player_id = msg.get("player_id")
            print(f"ID reçu : {self.my_player_id}")

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
            # En UDP on utilise sendto vers l'adresse du C
            data = json.dumps(message).encode('utf-8')
            self.socket.sendto(data, self.c_address)
        except Exception as e:
            print(f"Erreur envoi : {e}")