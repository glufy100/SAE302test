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
            passage_autorise = False
            for _ in range(12):
                reponse = client_file.readline().strip()
                if not reponse:
                    break
                morceaux = reponse.split("|")
                if morceaux[0] != "FEU":
                    continue
                if morceaux[2] == "VERT":
                    print(f"{nom} : feu vert, je traverse.")
                    passage_autorise = True
                    break
                print(f"{nom} : feu rouge, j'attends.")
                time.sleep(2)
                client.sendall(b"ETAT\n")

            if not passage_autorise:
                print(f"{nom} : attente trop longue, je reste au feu.")
                return
            position = 0
            while position < 100:
                client.sendall(b"AVANCE\n")
                reponse = client_file.readline().strip().split("|")
                if len(reponse) == 2 and reponse[0] in ("POSITION", "ATTENTE"):
                    position = int(reponse[1])
                    if reponse[0] == "ATTENTE":
                        print(f"{nom} : carrefour occupe, j'attends.")
                    else:
                        print(f"{nom} : progression {position} %")
                time.sleep(0.4)
            client.sendall(b"TERMINE\n")
            print(f"{nom} a traverse le carrefour.")
    except (ConnectionRefusedError, TimeoutError):
        print("Impossible de joindre le carrefour. Lancez carrefour.py d'abord.")
    except OSError as erreur:
        print(f"Connexion interrompue : {erreur}")


def main():
    try:
        quantite = int(sys.argv[1]) if len(sys.argv) > 1 else 1
        if quantite < 1:
            raise ValueError
    except ValueError:
        print("Utilisation : python voiture.py <quantite>")
        return

    voitures = [threading.Thread(target=simuler_voiture, args=(numero,))
                for numero in range(1, quantite + 1)]
    for voiture in voitures:
        voiture.start()
    for voiture in voitures:
        voiture.join()


if __name__ == "__main__":
    main()