import socket
import json

IP = "127.0.0.1"
PORT_ENVOI = 5001      # La bouche de ton code C
PORT_RECEPTION = 5003  # L'oreille de ton code C

# 1. On prépare l'oreille de Python
sock_ecoute = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_ecoute.bind((IP, PORT_RECEPTION))
sock_ecoute.settimeout(2.0) # On écoute pendant max 2 secondes

# 2. On prépare la bouche de Python
sock_envoi = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
demande = json.dumps({"type": "connect"}).encode('utf-8')

print("[AWA] 1. Envoi de la demande de connexion au C...")
sock_envoi.sendto(demande, (IP, PORT_ENVOI))

print("[AWA] 2. Attente de l'ID...")
try:
    data, _ = sock_ecoute.recvfrom(1024)
    print(f"\n✅ [VICTOIRE] Awa a bien reçu la réponse : {data.decode('utf-8')}")
except socket.timeout:
    print("\n❌ [ECHEC] Awa n'a rien reçu sur le port 5003.")
    
sock_ecoute.close()
sock_envoi.close()