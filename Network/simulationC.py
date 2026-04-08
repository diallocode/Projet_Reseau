import socket
import json
import time

# Utilise les mêmes constantes que ton projet
HOST = "127.0.0.1"
PORT = 5000 

def start_mock_c():
    # Création du socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    print(f"--- Simulateur C prêt sur {HOST}:{PORT} ---")

    # 1. Attendre le "Hello" du NetworkManager
    data, addr = sock.recvfrom(1024)
    print(f"Reçu de Python: {data.decode()}")

    # 2. Répondre avec l'ID d'initialisation
    init_msg = {"type": "init", "player_id": 42}
    sock.sendto(json.dumps(init_msg).encode(), addr)
    print(f"Envoyé à Python: Initialisation ID 42")

    time.sleep(1) # Petite pause pour simuler le délai réseau

    # 3. Simuler l'envoi d'un "Gros Message" de config
    units_config = {
        "type": "handshake",
        "units": [
            {"id": i, "type": "Knight", "x": 10.5 + i, "y": 20.0, "hp": 100} 
            for i in range(50) # On génère 50 unités d'un coup
        ]
    }
    sock.sendto(json.dumps(units_config).encode(), addr)
    print(f"Envoyé à Python: 50 unités générées ({len(json.dumps(units_config))} octets)")

    # 4. Simuler un mouvement simple
    time.sleep(2)
    move_msg = {"type": "move", "id": 0, "x": 15.0, "y": 25.0}
    sock.sendto(json.dumps(move_msg).encode(), addr)
    print("Envoyé à Python: Un mouvement d'unité")

if __name__ == "__main__":
    start_mock_c()