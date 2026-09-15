# Carrefour intelligent

Projet réalisé dans le cadre de la SAE 302 – Développer des applications communicantes.

## Présentation

Ce projet consiste à réaliser une simulation simple d'un **carrefour intelligent et connecté**.

L'objectif est de permettre à un **véhicule prioritaire** (pompier, ambulance, police...) de communiquer avec le carrefour afin de faciliter son passage et réduire son temps d'attente.

La communication entre les différents programmes est réalisée avec des **sockets Python**.

## Technologies utilisées

- Python 3.13
- PySide6
- Sockets
- Threads
- Git / GitHub

## Installation

### 1. Cloner le projet

```bash
git clone <URL_DU_REPOSITORY>
cd <NOM_DU_PROJET>
```

### 2. Créer l'environnement virtuel

```bash
python -m venv .venv
```

### 3. Activer l'environnement virtuel

**Linux / macOS :**

```bash
source .venv/bin/activate
```

**Windows :**

```bash
.venv\Scripts\activate
```

### 4. Installer les dépendances

```bash
pip install -r requirements.txt
```

## Lancement

Ouvrir plusieurs terminaux dans le dossier du projet :

```bash
python carrefour.py
python voiture.py 3
python urgence.py Ambulance N
```

Le premier programme ouvre la fenêtre du carrefour et écoute sur `127.0.0.1:5000`.
Le nombre `3` indique la densité de circulation. Les voitures sont générées en continu,
et une densité plus élevée réduit le délai entre deux apparitions. Le serveur choisit
automatiquement les routes, donc il n'est pas nécessaire d'indiquer une direction. Les voitures normales
avancent jusqu'à la ligne d'arrêt, attendent au feu orange ou rouge, puis traversent
quand le feu est vert. Le véhicule
prioritaire envoie `URGENCE`, le serveur met sa direction au vert, répond
`PASSAGE_AUTORISE`, puis revient au cycle normal après `TERMINE`.

Les voitures restent visibles pendant leur traversée : leur position avance progressivement
sur toute la route jusqu'à `100 %`. Le serveur bloque l'entrée d'une route perpendiculaire
si une autre voiture occupe déjà le centre du carrefour, afin d'éviter les collisions.

Pour tester le scénario complet, lancer d'abord `carrefour.py`, puis deux ou trois
commandes `voiture.py`, et enfin `urgence.py`. Les connexions, les changements de
feux et le nombre de véhicules sont visibles dans la fenêtre et dans le terminal du
serveur. Fermer la fenêtre du carrefour arrête proprement le serveur.
