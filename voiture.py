"""Client representant une voiture normale."""

import socket
import sys
import time

HOST = "127.0.0.1"
PORT = 5000
DIRECTIONS = ("N", "S", "E", "O")


def main():
    nom = sys.argv[1] if len(sys.argv) > 1 else f"Voiture-{int(time.time()) % 1000}"
    direction = sys.argv[2].upper() if len(sys.argv) > 2 else DIRECTIONS[int(time.time()) % 4]
    try:
        with socket.create_connection((HOST, PORT), timeout=5) as client:
            client_file = client.makefile("r", encoding="utf-8")
            client.sendall(f"IDENTITE|{nom}|voiture|{direction}\n".encode("utf-8"))
            print(f"{nom} arrive par la route {direction}.")
            for _ in range(12):
                reponse = client_file.readline().strip()
                if not reponse:
                    break
                morceaux = reponse.split("|")
                if morceaux[0] != "FEU":
                    continue
                if morceaux[2] == "VERT":
                    print(f"{nom} : feu vert, je traverse.")
                    break
                print(f"{nom} : feu rouge, j'attends.")
                time.sleep(2)
                client.sendall(b"ETAT\n")
    except (ConnectionRefusedError, TimeoutError):
        print("Impossible de joindre le carrefour. Lancez carrefour.py d'abord.")
    except OSError as erreur:
        print(f"Connexion interrompue : {erreur}")


if __name__ == "__main__":
    main()