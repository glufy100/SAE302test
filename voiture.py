"""Client representant une voiture normale."""

import socket
import sys
import threading
import time

HOST = "127.0.0.1"
PORT = 5000


def simuler_voiture(numero: int):
    nom = f"Voiture-{numero}"
    with socket.create_connection((HOST, PORT)) as client:
        client_file = client.makefile("r", encoding="utf-8")
        client.sendall(f"IDENTITE|{nom}|voiture|AUTO\n".encode("utf-8"))
        print(f"{nom} arrive au carrefour.")
        client_file.readline()
        position = 0
        while position < 100:
            client.sendall(b"AVANCE\n")
            reponse = client_file.readline().strip().split("|")
            if reponse[0] == "ATTENTE":
                print(f"{nom} : j'attends avant le carrefour.")
            else:
                position = int(reponse[1])
                print(f"{nom} : progression {max(0, position)} %")
            time.sleep(0.4)
        client.sendall(b"TERMINE\n")
        print(f"{nom} a traverse le carrefour.")


def main():
    densite = int(sys.argv[1])

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