import socket
import json
import time

# Utilise les mêmes constantes que ton projet
HOST = "127.0.0.1"
PORT = 7000 

def start_mock_c():
    # Création du socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    print(f"--- Simulateur C prêt sur {HOST}:{PORT} ---")

    # 1. Attendre le "Hello" du NetworkManager
    data, addr = sock.recvfrom(1024)
    print(f"Reçu de Python: {data.decode()}")

    # 2. Répondre avec l'ID d'initialisation
    init_msg = {"type": "init", "player_id": 1}
    sock.sendto(json.dumps(init_msg).encode(), addr)
    print(f"Envoyé à Python: Initialisation ID 1")

    time.sleep(20) # Petite pause pour simuler le délai réseau

    # 3. Simuler l'envoi d'un "Gros Message" de config
    units_config = {
        "type": "handshake",
        "player_id": 2,
        "units": [
            {"id": i + 2000, "type": "Knight", "x": 50 + i, "y": 42.0, "hp": 100} 
            for i in range(10) # On génère 5 unités d'un coup
        ]
    }
    sock.sendto(json.dumps(units_config).encode(), addr)
    print(f"Envoyé à Python: 5 unités générées ({len(json.dumps(units_config))} octets)")

    # 4. Simuler un mouvement simple
    time.sleep(2)
    for i in range(10):
        move_msg = {"type": "update","id": i + 2000, "hp": 45, "network_owner": 2, "x": 50.0+i,"y": 40.0}
        sock.sendto(json.dumps(move_msg).encode(), addr)
        print("Envoyé à Python: Un mouvement d'unité")
        time.sleep(2) # Pause entre les mouvements 

if __name__ == "__main__":
    start_mock_c()