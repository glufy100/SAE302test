# Documentation technique du projet Carrefour intelligent

## 1. Objet du document

Ce document décrit le fonctionnement complet du projet, son architecture logicielle, les interactions réseau, les mécanismes de contrôle et les procédures de lancement et de maintenance.

Il s’adresse à des lecteurs techniques souhaitant comprendre ou faire évoluer la simulation.

---

## 2. Contexte du projet

Le projet a pour objectif de simuler un carrefour intelligent où les véhicules peuvent communiquer avec un système central afin de gérer leur passage de manière sécurisée.

Le cas d’usage principal est le passage d’un véhicule prioritaire comme une ambulance, un pompier ou une voiture de police. Le système doit permettre de réduire le temps d’attente de ce véhicule tout en maintenant la sécurité du carrefour.

---

## 3. Objectifs fonctionnels

### 3.1 Fonctionnement attendu

- Génération de véhicules classiques à intervalle variable.
- Contrôle dynamique des feux selon les phases Nord-Sud et Est-Ouest.
- Gestion d’un mode urgence déclenché par un véhicule prioritaire.
- Blocage des mouvements risqués dans le carrefour.
- Affichage visuel de l’état du carrefour et de la progression des véhicules.

### 3.2 Contraintes

- Communication localisée en TCP sur localhost.
- Respect de la ligne d’arrêt et des distances de sécurité.
- Sécurité des échanges entre serveur et clients.
- Possibilité d’observer la simulation via une interface utilisateur.

---

## 4. Architecture logicielle

### 4.1 Vue d’ensemble

Le projet se compose de trois programmes Python distincts :

- un serveur central, responsable de la simulation,
- des clients voiture standard,
- un client véhicule prioritaire.

### 4.2 Schéma architectural

```text
+--------------------+
|  Interface Qt      |
|  carrefour.py      |
|  - affiche feux    |
|  - affiche trafic  |
+---------+----------+
          |
          | TCP / Socket
          v
+--------------------+
|  Serveur central   |
|  EtatCarrefour     |
|  ServeurCarrefour  |
|  - cycle feux      |
|  - logique voiture |
|  - gestion priorite|
+--------------------+
          |
          +------------+---------------------+
          |                                  |
          v                                  v
+------------------+                +----------------------+
| Voiture standard |                | Véhicule prioritaire  |
| voiture.py       |                | urgence.py            |
| - IDENTITE       |                | - IDENTITE            |
| - AVANCE         |                | - URGENCE             |
| - TERMINE        |                | - AVANCE              |
+------------------+                +----------------------+
```

---

## 5. Détail des composants

## 5.1 Serveur central

### Fichier concerné

- [carrefour.py](carrefour.py)

### Rôle

Le serveur central a plusieurs responsabilités :

- écouter les connexions réseau,
- créer un objet représentant chaque véhicule,
- stocker l’état global du carrefour,
- mettre à jour les feux et la phase de circulation,
- appliquer la logique de priorité,
- envoyer les réponses aux clients,
- rafraîchir l’interface graphique.

### Structure interne

#### EtatCarrefour

La classe EtatCarrefour contient l’état partagé du système :

- feux : état actuel des feux pour N, S, E, O,
- vehicules : dictionnaire des véhicules actifs,
- priorite : direction actuellement prioritaire,
- message : message d’état affiché dans l’interface,
- phase : phase courante du cycle de circulation,
- temps_phase : compteur de durée de phase.

Elle hérite de QObject et expose un signal change pour notifier les changements à la vue Qt.

#### ServeurCarrefour

Cette classe :

- crée le socket TCP,
- écoute les demandes de connexion,
- lance un thread par client,
- interprète les commandes reçues,
- déclenche les actions selon la commande.

#### FenetreCarrefour

La fenêtre principale :

- affiche le carrefour,
- affiche l’état et le nombre de véhicules,
- lance un timer pour alternancer les phases normales,
- interrompt le cycle normal lors d’une priorité.

---

## 5.2 Véhicule standard

### Fichier concerné

- [voiture.py](voiture.py)

### Rôle

Le client voiture standard simule la présence d’un véhicule normal dans la file d’attente. Il n’a pas de logique de décision avancée : il suit les ordres du serveur.

### Fonctionnement

- connexion au port 5000,
- envoi d’un message IDENTITE avec nom, type et direction,
- boucle de progression :
  - envoi AVANCE
  - réception d’une réponse du serveur : POSITION ou ATTENTE
- arrêt du parcours à 100 % puis envoi TERMINE.

### Paramètre de densité

Le programme attend un entier représentant le niveau de trafic. Par exemple :

```bash
python voiture.py 3
```

Plus la densité est élevée, plus les voitures apparaissent rapidement.

---

## 5.3 Véhicule prioritaire

### Fichier concerné

- [urgence.py](urgence.py)

### Rôle

Le client prioritaire simule une ambulance ou tout autre véhicule urgent. Son comportement est plus spécifique :

- envoi de IDENTITE avec type urgence,
- demande de priorité avec URGENCE,
- autorisation de passage par PASSAGE_AUTORISE,
- progression jusqu’à la fin du carrefour,
- terminaison puis retour au cycle normal.

### Paramètres

```bash
python urgence.py Ambulance N
```

- premier argument : nom du véhicule,
- second argument : direction d’arrivée, parmi N, S, E, O.

---

## 6. Logique des feux

Les feux sont gérés sous forme de dictionnaire :

```python
self.feux = {"N": "VERT", "S": "VERT", "E": "ROUGE", "O": "ROUGE"}
```

Le cycle normal suit cette séquence :

1. NS_VERT
2. NS_ORANGE
3. EO_VERT
4. EO_ORANGE
5. retour à NS_VERT

Chaque phase a une durée fixe dans le timer Qt :

- 6 secondes pour le vert,
- 2 secondes pour l’orange.

Lorsqu’une priorité est demandée, le système remplace immédiatement le cycle par une logique d’urgence :

```python
self.etat.feux = {
    direction: "VERT" if direction == vehicule.direction else "ROUGE"
    for direction in ("N", "S", "E", "O")
}
```

Ensuite, une fois la fin de passage détectée, le serveur remet les feux en mode normal.

---

## 7. Logique de circulation

### 7.1 Gestion de la progression

Chaque véhicule est caractérisé par :

- nom,
- type_vehicule,
- direction,
- prioritaire,
- progression,
- engagee.

La progression évolue par incréments de 10, jusqu’à 100. Le serveur détermine si le véhicule doit :

- avancer,
- attendre,
- s’arrêter avant la ligne d’arrêt,
- rester bloqué si le carrefour est occupé.

### 7.2 Sécurité et priorité

Le code applique plusieurs règles :

- distance de sécurité avec les véhicules précédents,
- arrêt à la ligne d’arrêt si le feu est rouge,
- attente si le feu est orange lors d’une approche,
- blocage du passage si une voie perpendiculaire est déjà engagée,
- interprétation de la règle de priorité à droite,
- interdiction de lancer un mouvement dangereux dans le carrefour.

---

## 8. Protocole de communication TCP

### 8.1 Type de socket

Le projet utilise des sockets TCP standard Python.

- host : 127.0.0.1
- port : 5000

### 8.2 Commandes réseau

Le serveur interprète des commandes textuelles séparées par le caractère |.

#### Commandes envoyées par le client

- IDENTITE|nom|type|direction
- ETAT
- AVANCE
- URGENCE
- TERMINE

#### Commandes envoyées par le serveur

- FEU|direction|couleur
- POSITION|pourcentage
- ATTENTE|pourcentage
- PASSAGE_AUTORISE

### 8.3 Exemple d’échange complet

```text
Client -> Serveur : IDENTITE|Voiture-1|voiture|AUTO
Serveur -> Client : FEU|N|VERT

Client -> Serveur : AVANCE
Serveur -> Client : POSITION|12

Client -> Serveur : AVANCE
Serveur -> Client : ATTENTE|30

Client -> Serveur : TERMINE
```

---

## 9. Gestion des threads

Le serveur se base sur plusieurs threads :

- un thread principal pour l’interface graphique,
- un thread d’écoute des clients,
- un thread par client connecté,
- un thread de timer pour les changements de phase.

Chaque client est géré indépendamment, ce qui permet d’avoir du trafic simultané.

Le verrou `self.verrou` de type `threading.Lock` protège les données partagées de l’état du carrefour et évite les conflits entre threads.

---

## 10. Interface utilisateur

### 10.1 Bibliothèque utilisée

Le projet utilise PySide6, le binding Qt pour Python.

### 10.2 Éléments affichés

La fenêtre principale affiche :

- l’état du trafic,
- l’état courant des feux,
- le nombre de véhicules connectés,
- la progression des véhicules sur les routes.

Le rendu 2D est dessiné manuellement dans le paintEvent de la vue. Les véhicules sont représentés par des rectangles, les feux par des cercles colorés.

---

## 11. Démarrage du projet

### 11.1 Prérequis

- Python 3.x
- pip
- environnement virtuel recommandé

### 11.2 Installation

```bash
git clone <URL_DU_REPOSITORY>
cd SAE302
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 11.3 Lancement manuel

Terminal 1 :

```bash
python carrefour.py
```

Terminal 2 :

```bash
python voiture.py 3
```

Terminal 3 :

```bash
python urgence.py Ambulance N
```

### 11.4 Lancement automatique

```bash
chmod +x lancer_simulation.sh
./lancer_simulation.sh 3
```

Le script lance le serveur puis génère automatiquement des voitures et un véhicule prioritaire.

---

## 12. Scénario de démonstration

Le scénario standard est le suivant :

1. Le serveur se lance et ouvre l’interface.
2. Des voitures normales sont créées selon la densité.
3. Une ambulance arrive sur une direction donnée.
4. Elle envoie une demande de priorité.
5. Le serveur force le feu vert et autorise le passage.
6. L’ambulance traverse le carrefour.
7. Après TERMINE, le système revient au cycle normal.

---

## 13. Points d’amélioration possibles

Le projet peut être enrichi avec :

- un stockage d’historique des événements dans SQLite,
- des statistiques de trafic et de temps d’attente,
- une meilleure gestion des collisions multi-voies,
- une configuration du cycle des feux via fichier de paramètres,
- des parcours plus réalistes selon les véhicules et leurs priorités,
- un environnement de tests automatisés.

---

## 14. Limites actuelles

Le système est orienté démonstration pédagogique. Il ne vise pas une simulation de trafic ultra-réaliste. Certaines limites sont visibles :

- gestion simplifiée des intersections,
- priorité logicielle non standardisée,
- absence d’historique durable,
- absence de tests automatisés sur les règles de circulation.

---

## 15. Conclusion

Le projet Carrefour intelligent illustre un système de signalisation dynamique basé sur la communication réseau et la logique d’automatisation. Il met en œuvre le principe d’un carrefour piloté par un serveur central capable de gérer des flux normaux et des demandes prioritaires en temps réel.

C’est une application concrète de programmation réseau, de concurrence, de développement d’interface graphique et de logique de contrôle.
