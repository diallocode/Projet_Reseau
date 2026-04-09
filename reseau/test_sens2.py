# test_sens2.py
import socket
import struct
import json
import time

# Format de l'entête UDP de C2 :
# uint8  id_expediteur  (1 octet)
# uint8  type_message   (1 octet)
# uint32 num_sequence   (4 octets)
# uint16 taille_payload (2 octets)
ENTETE = "!BBIH"  # ! = big-endian

def envoyer_paquet(sock, type_msg, num_seq, donnee_json):
    json_bytes = donnee_json.encode()
    taille = len(json_bytes)
    # Construire l'entête
    entete = struct.pack(ENTETE, 
        2,          # id_expediteur = joueur 2
        type_msg,   # type du message
        num_seq,    # numéro de séquence
        taille      # taille du JSON
    )
    # Coller entête + JSON et envoyer sur le port réseau
    paquet = entete + json_bytes
    sock.sendto(paquet, ("127.0.0.1", 5002))
    print(f"[ENVOYÉ] type={type_msg} seq={num_seq} json={donnee_json}")

# Socket pour envoyer vers le réseau (port 5002)
sock_envoi = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Socket pour écouter ce que ton C transmet à Python (port 5003)
sock_python = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_python.bind(("127.0.0.1", 5003))
sock_python.settimeout(2.0)

print("=== TEST SENS 2 : Réseau → Python ===\n")

# Test 1 : MOVE (type 0)
msg = {"type": "move", "id": 2000, "x": 10.0, "y": 5.0}
envoyer_paquet(sock_envoi, 0, 1, json.dumps(msg))

try:
    data, _ = sock_python.recvfrom(4096)
    print(f"[PYTHON A REÇU] {data.decode()} ✅\n")
except socket.timeout:
    print("[ERREUR] Python n'a rien reçu ❌\n")

time.sleep(0.5)

# Test 2 : INIT (type 3)
msg = {"type": "init", "player_id": 2}
envoyer_paquet(sock_envoi, 3, 2, json.dumps(msg))

try:
    data, _ = sock_python.recvfrom(4096)
    print(f"[PYTHON A REÇU] {data.decode()} ✅\n")
except socket.timeout:
    print("[ERREUR] Python n'a rien reçu ❌\n")

sock_envoi.close()
sock_python.close()
print("=== FIN DES TESTS ===")