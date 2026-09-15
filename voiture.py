"""Client representant une voiture normale."""

import socket
import sys
import threading
import time

HOST = "127.0.0.1"
PORT = 5000


def simuler_voiture(numero: int):
    nom = f"Voiture-{numero}"
    try:
        with socket.create_connection((HOST, PORT), timeout=5) as client:
            client_file = client.makefile("r", encoding="utf-8")
            client.sendall(f"IDENTITE|{nom}|voiture|AUTO\n".encode("utf-8"))
            print(f"{nom} arrive au carrefour.")
            client_file.readline()
            position = 0
            while position < 100:
                client.sendall(b"AVANCE\n")
                reponse = client_file.readline().strip().split("|")
                if len(reponse) == 2 and reponse[0] in ("POSITION", "ATTENTE"):
                    position = int(reponse[1])
                    position_affichee = max(0, position)
                    if reponse[0] == "ATTENTE":
                        print(f"{nom} : carrefour occupe, j'attends.")
                    else:
                        print(f"{nom} : progression {position_affichee} %")
                time.sleep(0.4)
            client.sendall(b"TERMINE\n")
            print(f"{nom} a traverse le carrefour.")
    except (ConnectionRefusedError, TimeoutError):
        print("Impossible de joindre le carrefour. Lancez carrefour.py d'abord.")
    except OSError as erreur:
        print(f"Connexion interrompue : {erreur}")


def main():
    try:
        densite = int(sys.argv[1]) if len(sys.argv) > 1 else 3
        if densite < 1:
            raise ValueError
    except ValueError:
        print("Utilisation : python voiture.py <densite>")
        return

    numero = 1
    try:
        while True:
            voiture = threading.Thread(target=simuler_voiture, args=(numero,), daemon=True)
            voiture.start()
            numero += 1
            time.sleep(max(1.0, 6.0 / densite))
    except KeyboardInterrupt:
        print("Generation des voitures arretee.")


if __name__ == "__main__":
    main()