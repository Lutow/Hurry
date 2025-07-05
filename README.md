# Hurry

Hurry est une application web innovante de cartographie et d'analyse du réseau de transport en commun parisien, centrée sur le métro. Elle permet de visualiser l'ensemble du réseau sous forme de graphe interactif, de rechercher le plus court trajet entre deux stations, d'afficher un Arbre Couvrant de Poids Minimum (ACPM), de vérifier la connexité du réseau et d'afficher les perturbations en temps réel.

## Fonctionnalités principales

- **Affichage du réseau** : Visualisation interactive de toutes les stations et connexions du métro parisien sur un graphe.
- **Recherche d'itinéraire optimal** : Calcul du plus court chemin entre deux stations, avec prise en compte des correspondances et des temps de trajet réalistes.
- **ACPM (Arbre Couvrant de Poids Minimum)** : Outils d'analyse avancée pour explorer la structure du réseau, détecter les points faibles et visualiser les composantes connexes.
- **Vérification de la connexité** : Vérification automatique que toutes les stations sont accessibles entre elles, avec affichage des éventuelles stations isolées.
- **Perturbations en temps réel** : Affichage des incidents et perturbations en cours sur le réseau (données IDFM/RATP).

## Installation

1. **Installer les dépendances backend**
   ```sh
   pip install -r requirements.txt
   ```

2. **Installer les dépendances frontend**
   ```sh
   cd frontend
   npm install
   cd ..
   ```

3. **Lancer le backend**
   ```sh
   uvicorn backend.main:app --reload
   ```

4. **Lancer le frontend**
   ```sh
   cd frontend
   npm run dev
   ```

## Utilisation

- Accédez à l'interface web via [http://localhost:5173](http://localhost:5173) (ou le port affiché par Vite).
- Recherchez un itinéraire en saisissant les stations de départ et d'arrivée.
- Visualisez le graphe, les itinéraires, la connexité et les perturbations en temps réel.

## Structure du projet

- `backend/` : API FastAPI, calculs de graphe, traitements GTFS, logique métier.
- `frontend/` : Application Vue.js pour l'affichage interactif.
- `graph/IDFM-gtfs/` : Données GTFS (stops, routes, trips, etc.).
- `apply_real_speeds.py`, `update_travel_times.py` : Scripts pour mettre à jour les temps de trajet avec des vitesses réelles.

## Données

Le projet utilise les données GTFS d'Île-de-France Mobilités pour construire le graphe du réseau.
Il utilise également l'API d'Île-de-France Mobilités pour les perturbations.


## Licence

Voir le fichier [LICENSE](LICENSE).
