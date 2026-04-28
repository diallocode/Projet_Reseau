# test_sens1.py
import socket
import json
import time

# Connexion vers ton processus C (port 5001)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print("=== TEST SENS 1 : Python → Réseau ===\n")

# Test 1 : message move
msg = {"type": "move", "id": 1005, "x": 51.5, "y": 42.0}
sock.sendto(json.dumps(msg).encode(), ("127.0.0.1", 5001))
print(f"Envoyé : {json.dumps(msg)}")
time.sleep(0.5)

# Test 2 : message init
msg = {"type": "init", "player_id": 2}
sock.sendto(json.dumps(msg).encode(), ("127.0.0.1", 5001))
print(f"Envoyé : {json.dumps(msg)}")
time.sleep(0.5)

# Test 3 : message damage
msg = {"type": "damage", "id": 2010, "hp": 45}
sock.sendto(json.dumps(msg).encode(), ("127.0.0.1", 5001))
print(f"Envoyé : {json.dumps(msg)}")
time.sleep(0.5)

# Test 4 : message handshake
msg = {
    "type": "handshake",
    "player_id": 2,
    "units": [
        {"id": 2000, "type": "Knight", "x": 55.0, "y": 40.0, "hp": 120},
        {"id": 2001, "type": "Pikeman", "x": 56.0, "y": 40.0, "hp": 80}
    ]
}
sock.sendto(json.dumps(msg).encode(), ("127.0.0.1", 5001))
print(f"Envoyé : {json.dumps(msg)}")
time.sleep(0.5)

# Test 5 : JSON malformé (doit être ignoré sans crash)
sock.sendto(b"ceci n'est pas du json", ("127.0.0.1", 5001))
print(f"Envoyé : JSON malformé (doit être ignoré)")

sock.close()
print("\n=== FIN DES TESTS ===")