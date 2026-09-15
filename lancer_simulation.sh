#!/usr/bin/env bash

set -u

DENSITE="${1:-3}"
SERVEUR_PID=""
VOITURES_PID=""
URGENCE_PID=""

arreter_programmes() {
    echo
    echo "[INFO] Arret de la simulation..."
    for pid in "$URGENCE_PID" "$VOITURES_PID" "$SERVEUR_PID"; do
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
}

trap arreter_programmes INT TERM EXIT

echo "=============================================="
echo " Carrefour intelligent - demonstration"
echo "=============================================="
echo "[INFO] Densite de circulation : $DENSITE"
echo "[INFO] Demarrage du serveur et de l'interface..."
PYTHONUNBUFFERED=1 python carrefour.py &
SERVEUR_PID=$!

sleep 2
echo "[INFO] Generation continue des voitures normales."
PYTHONUNBUFFERED=1 python voiture.py "$DENSITE" &
VOITURES_PID=$!

sleep 8
echo "[INFO] Arrivee d'un vehicule prioritaire : ambulance, direction N."
PYTHONUNBUFFERED=1 python urgence.py Ambulance N &
URGENCE_PID=$!

echo "[INFO] Simulation en cours. Appuyer sur Ctrl+C pour quitter."
wait "$SERVEUR_PID"