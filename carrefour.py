"""Serveur TCP et interface graphique du carrefour intelligent."""

import socket
import threading
from dataclasses import dataclass

from PySide6.QtCore import QObject, QLibraryInfo, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

HOST = "127.0.0.1"
PORT = 5000


@dataclass
class Vehicule:
    nom: str
    type_vehicule: str
    direction: str
    prioritaire: bool = False
    progression: int = 0


class EtatCarrefour(QObject):
    change = Signal()

    def __init__(self):
        super().__init__()
        self.verrou = threading.Lock()
        self.feux = {"N": "VERT", "S": "VERT", "E": "ROUGE", "O": "ROUGE"}
        self.vehicules: dict[str, Vehicule] = {}
        self.priorite: str | None = None
        self.message = "Trafic normal"
        self.prochaine_direction = 0
        self.phase = "NS_VERT"
        self.temps_phase = 0

    def notifier(self, message: str | None = None):
        with self.verrou:
            if message:
                self.message = message
        self.change.emit()

    def etat_feu(self, direction: str) -> str:
        with self.verrou:
            return self.feux.get(direction, "ROUGE")

    def changer_feux(self, direction_prioritaire: str | None):
        with self.verrou:
            if direction_prioritaire:
                self.feux = {direction: "VERT" if direction == direction_prioritaire else "ROUGE"
                             for direction in ("N", "S", "E", "O")}
                self.priorite = direction_prioritaire
                self.phase = "URGENCE"
            else:
                self.feux = {"N": "VERT", "S": "VERT", "E": "ROUGE", "O": "ROUGE"}
                self.priorite = None
                self.phase = "NS_VERT"
                self.temps_phase = 0


class ServeurCarrefour:
    def __init__(self, etat: EtatCarrefour):
        self.etat = etat
        self.socket_serveur: socket.socket | None = None
        self.arret = threading.Event()

    def demarrer(self):
        self.socket_serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_serveur.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket_serveur.bind((HOST, PORT))
        self.socket_serveur.listen()
        print(f"Serveur du carrefour en ecoute sur {HOST}:{PORT}")
        threading.Thread(target=self._accepter_clients, daemon=True).start()

    def _accepter_clients(self):
        while not self.arret.is_set():
            try:
                client, adresse = self.socket_serveur.accept()
            except OSError:
                break
            print(f"Connexion recue depuis {adresse}")
            threading.Thread(target=self._gerer_client, args=(client,), daemon=True).start()

    def _envoyer(self, client: socket.socket, message: str):
        client.sendall((message + "\n").encode("utf-8"))

    def _choisir_direction(self) -> str:
        directions = ("N", "S", "E", "O")
        with self.etat.verrou:
            direction = directions[self.etat.prochaine_direction]
            self.etat.prochaine_direction = (self.etat.prochaine_direction + 1) % len(directions)
        return direction

    @staticmethod
    def _axe(direction: str) -> str:
        return "vertical" if direction in ("N", "S") else "horizontal"

    def _avancer_vehicule(self, client: socket.socket, vehicule: Vehicule):
        with self.etat.verrou:
            prochaine_position = min(vehicule.progression + 10, 100)
            feu_vert = self.etat.feux[vehicule.direction] == "VERT"
            approche_ligne_arret = vehicule.progression < 40 < prochaine_position
            entre_dans_le_carrefour = vehicule.progression < 50 <= prochaine_position
            reponse = ""
            message = ""

            couleur_feu = self.etat.feux[vehicule.direction]
            voitures_devant = [
                autre.progression
                for autre in self.etat.vehicules.values()
                if autre.nom != vehicule.nom
                and autre.direction == vehicule.direction
                and autre.progression > vehicule.progression
            ]
            if voitures_devant:
                position_voiture_devant = min(voitures_devant)
                distance_trop_courte = prochaine_position > position_voiture_devant - 20
                if distance_trop_courte:
                    reponse = f"ATTENTE|{vehicule.progression}"
                    message = f"{vehicule.nom} garde ses distances"

            if not reponse and approche_ligne_arret and not feu_vert:
                vehicule.progression = 40
                reponse = "POSITION|40"
                message = f"{vehicule.nom} attend au feu {couleur_feu.lower()}"
            elif not reponse and vehicule.progression == 40 and not feu_vert:
                reponse = "ATTENTE|40"
                message = f"{vehicule.nom} attend au feu {couleur_feu.lower()}"
            elif not reponse and entre_dans_le_carrefour:
                axe_vehicule = self._axe(vehicule.direction)
                carrefour_occupe = any(
                    autre.nom != vehicule.nom
                    and self._axe(autre.direction) != axe_vehicule
                    and 40 <= autre.progression <= 60
                    for autre in self.etat.vehicules.values()
                )
                if carrefour_occupe:
                    reponse = f"ATTENTE|{vehicule.progression}"
                    message = f"{vehicule.nom} attend avant le carrefour"
            if not reponse:
                vehicule.progression = prochaine_position
                reponse = f"POSITION|{vehicule.progression}"
                progression_visible = max(0, vehicule.progression)
                message = f"{vehicule.nom} traverse ({progression_visible} %)"
        self._envoyer(client, reponse)
        self.etat.notifier(message)

    def _gerer_client(self, client: socket.socket):
        vehicule: Vehicule | None = None
        lecteur = client.makefile("r", encoding="utf-8")
        try:
            for ligne in lecteur:
                morceaux = ligne.strip().split("|")
                commande = morceaux[0]
                if commande == "IDENTITE" and len(morceaux) >= 4:
                    direction = morceaux[3] if morceaux[3] in ("N", "S", "E", "O") else self._choisir_direction()
                    with self.etat.verrou:
                        voitures_meme_direction = sum(
                            autre.direction == direction
                            for autre in self.etat.vehicules.values()
                        )
                    vehicule = Vehicule(morceaux[1], morceaux[2], direction,
                                        progression=-20 * voitures_meme_direction)
                    with self.etat.verrou:
                        self.etat.vehicules[vehicule.nom] = vehicule
                    self._envoyer(client, f"FEU|{vehicule.direction}|{self.etat.etat_feu(vehicule.direction)}")
                    self.etat.notifier(f"{vehicule.nom} est connecte")
                elif commande == "ETAT" and vehicule:
                    self._envoyer(client, f"FEU|{vehicule.direction}|{self.etat.etat_feu(vehicule.direction)}")
                elif commande == "URGENCE" and vehicule:
                    vehicule.prioritaire = True
                    self.etat.changer_feux(vehicule.direction)
                    self._envoyer(client, "PASSAGE_AUTORISE")
                    self.etat.notifier(f"Priorite accordee a {vehicule.nom}")
                    print(f"Demande URGENCE de {vehicule.nom} ({vehicule.direction})")
                elif commande == "AVANCE" and vehicule:
                    self._avancer_vehicule(client, vehicule)
                elif commande == "TERMINE" and vehicule:
                    with self.etat.verrou:
                        vehicule.progression = 100
                    if vehicule.prioritaire:
                        self.etat.changer_feux(None)
                        self.etat.notifier("Trafic normal")
                    print(f"Passage termine pour {vehicule.nom}")
        except (ConnectionResetError, BrokenPipeError, OSError):
            print("Un client s'est deconnecte")
        finally:
            if vehicule:
                with self.etat.verrou:
                    self.etat.vehicules.pop(vehicule.nom, None)
                self.etat.notifier()
            lecteur.close()
            client.close()

    def arreter(self):
        self.arret.set()
        if self.socket_serveur:
            self.socket_serveur.close()


class VueCarrefour(QWidget):
    def __init__(self, etat: EtatCarrefour):
        super().__init__()
        self.etat = etat
        self.setMinimumSize(700, 500)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        with self.etat.verrou:
            feux = self.etat.feux.copy()
            vehicules = list(self.etat.vehicules.values())
        largeur, hauteur = self.width(), self.height()
        centre_x, centre_y = largeur // 2, 220
        painter.fillRect(0, 0, largeur, hauteur, QColor("#eef2f3"))
        painter.setPen(QPen(QColor("#38434a"), 100))
        painter.drawLine(centre_x, 35, centre_x, 405)
        painter.drawLine(100, centre_y, largeur - 100, centre_y)
        painter.setPen(QPen(QColor("#f8faf9"), 2))
        painter.drawLine(centre_x, 35, centre_x, 405)
        painter.drawLine(100, centre_y, largeur - 100, centre_y)
        positions = {"N": (centre_x - 78, 78), "S": (centre_x + 50, 335),
                 "E": (largeur - 155, centre_y - 78), "O": (108, centre_y + 50)}
        for direction, (x, y) in positions.items():
            couleur = {"VERT": "#36a269", "ORANGE": "#f0a52b", "ROUGE": "#d94b4b"}[feux[direction]]
            painter.setBrush(QBrush(QColor(couleur)))
            painter.setPen(QPen(QColor("#20282d"), 2))
            painter.drawEllipse(x, y, 28, 28)
            painter.setPen(QColor("#20282d"))
            painter.drawText(x + 8, y - 8, direction)
        for index, vehicule in enumerate(vehicules):
            progression = max(-0.04, min(1.0, vehicule.progression / 100))
            if vehicule.direction == "N":
                x, y = centre_x - 28, 20 + int(360 * progression)
                largeur_vehicule, hauteur_vehicule = 22, 32
            elif vehicule.direction == "S":
                x, y = centre_x + 6, 380 - int(360 * progression)
                largeur_vehicule, hauteur_vehicule = 22, 32
            elif vehicule.direction == "E":
                x, y = largeur - 125 - int((largeur - 220) * progression), centre_y + 6
                largeur_vehicule, hauteur_vehicule = 32, 22
            else:
                x, y = 95 + int((largeur - 220) * progression), centre_y - 28
                largeur_vehicule, hauteur_vehicule = 32, 22
            painter.setBrush(QBrush(QColor("#e9584f") if vehicule.prioritaire else QColor("#3478bd")))
            painter.setPen(QPen(QColor("#172027"), 1))
            painter.drawRect(x, y, largeur_vehicule, hauteur_vehicule)
            painter.setPen(QColor("#ffffff"))
            identifiant = "U" if vehicule.prioritaire else vehicule.nom.split("-")[-1]
            painter.drawText(x + 3, y + hauteur_vehicule - 6, identifiant)


class FenetreCarrefour(QMainWindow):
    def __init__(self, etat: EtatCarrefour, serveur: ServeurCarrefour):
        super().__init__()
        self.serveur = serveur
        self.setWindowTitle("Carrefour intelligent")
        self.vue = VueCarrefour(etat)
        self.etat_label = QLabel()
        self.connexions_label = QLabel()
        layout = QVBoxLayout()
        layout.addWidget(self.vue)
        layout.addWidget(self.etat_label)
        layout.addWidget(self.connexions_label)
        conteneur = QWidget()
        conteneur.setLayout(layout)
        self.setCentralWidget(conteneur)
        etat.change.connect(self.actualiser)
        self.actualiser()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.changer_cycle_normal)
        self.timer.start(1000)

    def actualiser(self):
        with self.vue.etat.verrou:
            nombre = len(self.vue.etat.vehicules)
            message = self.vue.etat.message
        self.etat_label.setText(f"Etat : {message}")
        self.connexions_label.setText(f"Vehicules connectes : {nombre}")
        self.vue.update()

    def changer_cycle_normal(self):
        with self.vue.etat.verrou:
            if self.vue.etat.priorite is not None:
                return
            self.vue.etat.temps_phase += 1
            phase = self.vue.etat.phase
            temps_phase = self.vue.etat.temps_phase
            if phase == "NS_VERT" and temps_phase >= 6:
                self.vue.etat.phase = "NS_ORANGE"
                self.vue.etat.temps_phase = 0
                self.vue.etat.feux = {"N": "ORANGE", "S": "ORANGE", "E": "ROUGE", "O": "ROUGE"}
                message = "Feux orange Nord-Sud : les voitures terminent leur passage"
            elif phase == "NS_ORANGE" and temps_phase >= 2:
                self.vue.etat.phase = "EO_VERT"
                self.vue.etat.temps_phase = 0
                self.vue.etat.feux = {"N": "ROUGE", "S": "ROUGE", "E": "VERT", "O": "VERT"}
                message = "Trafic Est-Ouest"
            elif phase == "EO_VERT" and temps_phase >= 6:
                self.vue.etat.phase = "EO_ORANGE"
                self.vue.etat.temps_phase = 0
                self.vue.etat.feux = {"N": "ROUGE", "S": "ROUGE", "E": "ORANGE", "O": "ORANGE"}
                message = "Feux orange Est-Ouest : les voitures terminent leur passage"
            elif phase == "EO_ORANGE" and temps_phase >= 2:
                self.vue.etat.phase = "NS_VERT"
                self.vue.etat.temps_phase = 0
                self.vue.etat.feux = {"N": "VERT", "S": "VERT", "E": "ROUGE", "O": "ROUGE"}
                message = "Trafic Nord-Sud"
            else:
                message = None
        if message:
            self.vue.etat.notifier(message)

    def closeEvent(self, event):
        self.serveur.arreter()
        event.accept()


def main():
    plugin_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)
    QApplication.setLibraryPaths([plugin_path])
    application = QApplication([])
    etat = EtatCarrefour()
    serveur = ServeurCarrefour(etat)
    serveur.demarrer()
    fenetre = FenetreCarrefour(etat, serveur)
    fenetre.show()
    application.exec()


if __name__ == "__main__":
    main()