"""Client representant un vehicule prioritaire."""

import socket
import sys
import time

HOST = "127.0.0.1"
PORT = 5000


def main():
    nom = sys.argv[1] if len(sys.argv) > 1 else "Ambulance"
    direction = sys.argv[2].upper() if len(sys.argv) > 2 else "N"
    try:
        with socket.create_connection((HOST, PORT), timeout=5) as client:
            client_file = client.makefile("r", encoding="utf-8")
            client.sendall(f"IDENTITE|{nom}|urgence|{direction}\n".encode("utf-8"))
            print(f"{nom} arrive par la route {direction} et demande la priorite.")
            client_file.readline()
            client.sendall(b"URGENCE\n")
            reponse = client_file.readline().strip()
            if reponse == "PASSAGE_AUTORISE":
                print("Carrefour : PASSAGE_AUTORISE")
                position = 0
                while position < 100:
                    client.sendall(b"AVANCE\n")
                    progression = client_file.readline().strip().split("|")
                    if len(progression) == 2 and progression[0] in ("POSITION", "ATTENTE"):
                        position = int(progression[1])
                        position_affichee = max(0, position)
                        if progression[0] == "ATTENTE":
                            print(f"{nom} : carrefour occupe, j'attends.")
                        else:
                            print(f"{nom} : progression {position_affichee} %")
                    time.sleep(0.4)
                client.sendall(b"TERMINE\n")
                print(f"{nom} a termine son passage.")
    except (ConnectionRefusedError, TimeoutError):
        print("Impossible de joindre le carrefour. Lancez carrefour.py d'abord.")
    except OSError as erreur:
        print(f"Connexion interrompue : {erreur}")


if __name__ == "__main__":
    main()