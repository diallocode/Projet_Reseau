# test_complet.py
import socket
import struct
import json
import time
import threading

ENTETE = "!BBIH"  # id_expediteur(1) type(1) sequence(4) taille(2)

# =====================
# FONCTIONS UTILITAIRES
# =====================

def construire_paquet(type_msg, num_seq, id_expediteur, donnee_json):
    json_bytes = donnee_json.encode()
    entete = struct.pack(ENTETE, id_expediteur, type_msg, num_seq, len(json_bytes))
    return entete + json_bytes

# =====================
# SOCKETS
# =====================

# Envoie vers C (IPC Python→C)
sock_ipc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Envoie vers C (simule réseau entrant)
sock_reseau = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Écoute ce que C envoie à Python (port 5003)
sock_python = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_python.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock_python.bind(("127.0.0.1", 5003))
sock_python.settimeout(2.0)

# =====================
# THREAD : écoute Python en arrière-plan
# =====================

messages_recus = []

def ecouter_python():
    print("[THREAD] En attente de messages pour Python...")
    while True:
        try:
            data, _ = sock_python.recvfrom(4096)
            msg = data.decode()
            messages_recus.append(msg)
            print(f"\n[→ PYTHON A REÇU] {msg} ✅")
        except socket.timeout:
            break
        except Exception as e:
            break

# =====================
# TESTS
# =====================

print("=" * 50)
print("   TEST COMPLET : Sens 1 + Sens 2")
print("=" * 50)

# Démarrer le thread d'écoute
thread = threading.Thread(target=ecouter_python, daemon=True)
thread.start()

time.sleep(0.3)

# --- SENS 1 : Python → Réseau ---
print("\n--- SENS 1 : Python → Réseau ---")

msg1 = {"type": "move", "id": 1005, "x": 51.5, "y": 42.0}
sock_ipc.sendto(json.dumps(msg1).encode(), ("127.0.0.1", 5001))
print(f"[PYTHON ENVOIE] {json.dumps(msg1)}")
time.sleep(0.5)

msg2 = {"type": "init", "player_id": 1}
sock_ipc.sendto(json.dumps(msg2).encode(), ("127.0.0.1", 5001))
print(f"[PYTHON ENVOIE] {json.dumps(msg2)}")
time.sleep(0.5)

msg3 = {"type": "damage", "id": 2010, "hp": 45}
sock_ipc.sendto(json.dumps(msg3).encode(), ("127.0.0.1", 5001))
print(f"[PYTHON ENVOIE] {json.dumps(msg3)}")
time.sleep(0.5)

# --- SENS 2 : Réseau → Python ---
print("\n--- SENS 2 : Réseau → Python ---")

paquet1 = construire_paquet(0, 1, 2, json.dumps({"type": "move", "id": 2000, "x": 10.0, "y": 5.0}))
sock_reseau.sendto(paquet1, ("127.0.0.1", 5002))
print(f"[RÉSEAU ENVOIE] move id=2000")
time.sleep(0.5)

paquet2 = construire_paquet(3, 2, 2, json.dumps({"type": "init", "player_id": 2}))
sock_reseau.sendto(paquet2, ("127.0.0.1", 5002))
print(f"[RÉSEAU ENVOIE] init player_id=2")
time.sleep(0.5)

paquet3 = construire_paquet(4, 3, 2, json.dumps({"type": "damage", "id": 3000, "hp": 30}))
sock_reseau.sendto(paquet3, ("127.0.0.1", 5002))
print(f"[RÉSEAU ENVOIE] damage id=3000")
time.sleep(0.5)

# --- TEST SIMULTANÉ ---
print("\n--- TEST SIMULTANÉ : les deux en même temps ---")

sock_ipc.sendto(json.dumps({"type": "move", "id": 1005, "x": 99.0, "y": 99.0}).encode(), ("127.0.0.1", 5001))
paquet_sim = construire_paquet(0, 4, 3, json.dumps({"type": "move", "id": 4000, "x": 1.0, "y": 1.0}))
sock_reseau.sendto(paquet_sim, ("127.0.0.1", 5002))
print(f"[SIMULTANÉ] Python et Réseau envoient en même temps")
time.sleep(1.0)

# Attendre la fin du thread
thread.join(timeout=3)

# =====================
# RÉSUMÉ
# =====================
print("\n" + "=" * 50)
print(f"   RÉSUMÉ : {len(messages_recus)} message(s) reçus par Python")
for i, msg in enumerate(messages_recus):
    print(f"   [{i+1}] {msg}")
print("=" * 50)

sock_ipc.close()
sock_reseau.close()
sock_python.close()