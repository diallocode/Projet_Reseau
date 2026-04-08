import threading
import queue
import json
import socket # (Ou la librairie IPC que tu utiliseras)

class NetworkManager:
    
    def __init__(self, port=5000):
        self.message_queue = queue.Queue()
        self.my_player_id = None
        
        # 1. Connexion au processus C (ex: via un socket TCP local)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("127.0.0.1", port))
        
        # 2. On attend l'ID en bloquant l'exécution (Handshake)
        self._wait_for_initialization()
        
        # 3. SEULEMENT MAINTENANT, on lance le thread d'écoute asynchrone
        self.listener_thread = threading.Thread(target=self._listen_to_c_process, daemon=True)
        self.listener_thread.start()

    def _wait_for_initialization(self):
        """Bloque le script jusqu'à ce que le C nous donne notre ID."""
        print("En attente du processus C pour recevoir notre ID...")
        
        # recv() est bloquant. Le programme s'arrête ici tant qu'il n'y a rien.
        data = self.sock.recv(1024).decode('utf-8')
        msg = json.loads(data)
        
        if msg.get("type") == "init":
            self.my_player_id = msg.get("player_id")
            print(f"Connexion établie ! Le processus C m'a attribué l'ID : {self.my_player_id}")
        else:
            raise ValueError("Le premier message du C doit être l'initialisation (type: init).")

    def _listen_to_c_process(self):
        """La boucle infinie qui tournera en tâche de fond pendant la partie."""
        while True:
            try:
                data = self.sock.recv(4096).decode('utf-8')
                if not data:
                    break # Connexion perdue
                
                # S'il y a plusieurs messages dans le buffer, on les sépare
                # (Attention, en TCP, les messages peuvent se coller)
                msg = json.loads(data)
                self.message_queue.put(msg)
            except Exception as e:
                print(f"Erreur réseau : {e}")
                break

    def get_messages(self):
        """Dépile tous les messages reçus pour la frame en cours."""
        messages = []
        while not self.message_queue.empty():
            messages.append(self.message_queue.get())
        return messages