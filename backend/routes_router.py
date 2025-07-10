from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import heapq
import time
import logging
import math
from difflib import SequenceMatcher
from datetime import datetime, timedelta
from backend.utils.logger import log_info, log_warning, log_error, log_debug, normalize_text
from backend.utils.schedule_calculator import MetroScheduleCalculator

router = APIRouter(prefix="/api")

# Configurer le logger standard pour ce module
logger = logging.getLogger(__name__)


class PathFinder:
    """
    Classe optimisée pour trouver les plus courts chemins dans le graphe du métro parisien.
    Implémente A* avec fallback vers Dijkstra pour une recherche efficace et robuste.
    """

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calcule la distance géodésique entre deux points en utilisant la formule de Haversine.
        Utilisée comme heuristique pour l'algorithme A*.

        Args:
            lat1, lon1: Coordonnées du premier point (en degrés)
            lat2, lon2: Coordonnées du deuxième point (en degrés)

        Returns:
            Distance en kilomètres
        """
        # Rayon de la Terre en kilomètres
        R = 6371.0

        # Conversion en radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Différences
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        # Formule de Haversine
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    @staticmethod
    def _get_heuristic_cost(graph, current_station: str, target_station: str) -> float:
        """
        Calcule le coût heuristique entre deux stations pour A*.
        Utilise la distance géodésique comme estimation optimiste.

        Args:
            graph: Instance du graphe
            current_station: Station actuelle
            target_station: Station de destination

        Returns:
            Coût heuristique (distance en km / vitesse moyenne estimée)
        """
        try:
            # Récupérer les coordonnées des stations
            current_coords = graph.stations.get(current_station)
            target_coords = graph.stations.get(target_station)

            if not current_coords or not target_coords:
                return 0.0  # Heuristique nulle si pas de coordonnées

            # Distance géodésique en kilomètres
            distance_km = PathFinder.haversine_distance(
                current_coords['lat'], current_coords['lon'],
                target_coords['lat'], target_coords['lon']
            )

            # Estimation du temps basée sur vitesse moyenne du métro (30 km/h)
            # et temps de correspondance moyen (2 minutes)
            estimated_time = distance_km / 30 * 60  # en minutes

            # Normaliser par rapport au coût unitaire d'une arête (2 minutes par station)
            return estimated_time / 2.0

        except Exception as e:
            log_warning(f"Erreur dans le calcul heuristique: {e}")
            return 0.0

    @staticmethod
    def a_star_pathfinding(graph, start_station: str, end_station: str,
                           prefer_line_continuity: bool = True) -> Optional[Dict[str, Any]]:
        """
        Implémentation optimisée de l'algorithme A* pour la recherche de chemin.

        Args:
            graph: Instance du graphe
            start_station: Station de départ
            end_station: Station d'arrivée
            prefer_line_continuity: Si True, pénalise les changements de ligne

        Returns:
            Dictionnaire contenant le chemin et le coût, ou None si aucun chemin
        """
        if start_station not in graph.nodes or end_station not in graph.nodes:
            missing = []
            if start_station not in graph.nodes:
                missing.append(f"depart: {start_station}")
            if end_station not in graph.nodes:
                missing.append(f"arrivee: {end_station}")
            log_warning(f"Station(s) non trouvee(s) avec A*: {', '.join(missing)}")
            return None

        # Si départ = arrivée
        if start_station == end_station:
            return {"path": [start_station], "distance": 0.0}

        # Structures pour A*
        # g_score: coût réel depuis le départ
        g_score = {node: float('infinity') for node in graph.nodes}
        g_score[start_station] = 0.0

        # f_score: g_score + heuristique
        f_score = {node: float('infinity') for node in graph.nodes}
        f_score[start_station] = PathFinder._get_heuristic_cost(graph, start_station, end_station)

        # Prédécesseurs pour reconstruction du chemin
        came_from = {}

        # Ligne utilisée pour arriver à chaque nœud (pour pénaliser les changements)
        previous_lines = {start_station: None}

        # File de priorité: (f_score, g_score, station, previous_line)
        open_set = [(f_score[start_station], 0.0, start_station, None)]

        # Ensemble des stations visitées
        closed_set = set()

        # Statistiques de performance
        nodes_explored = 0

        while open_set:
            # Récupérer la station avec le plus petit f_score
            current_f, current_g, current_station, current_line = heapq.heappop(open_set)

            # Si station déjà visitée, ignorer
            if current_station in closed_set:
                continue

            # Marquer comme visitée
            closed_set.add(current_station)
            nodes_explored += 1

            # Si destination atteinte
            if current_station == end_station:
                log_info(f"A* trouvé un chemin en explorant {nodes_explored} nœuds")

                # Reconstruction du chemin
                path = []
                current = current_station
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start_station)
                path.reverse()

                return {
                    "path": path,
                    "distance": g_score[end_station]
                }

            # Explorer les voisins
            for neighbor in graph.get_neighbors(current_station):
                if neighbor in closed_set:
                    continue

                # Coût de l'arête
                neighbor_line = graph.get_line_between_stations(current_station, neighbor)
                edge_cost = 1.0  # Coût de base

                # Pénalité pour changement de ligne
                if (prefer_line_continuity and current_line is not None and
                        neighbor_line != current_line and neighbor_line != "transfer"):
                    edge_cost += 0.2  # Pénalité modérée pour changement

                # Calcul du nouveau g_score
                tentative_g_score = g_score[current_station] + edge_cost

                # Si ce chemin est meilleur
                if tentative_g_score < g_score[neighbor]:
                    # Enregistrer le meilleur chemin
                    came_from[neighbor] = current_station
                    g_score[neighbor] = tentative_g_score
                    previous_lines[neighbor] = neighbor_line

                    # Calculer f_score avec heuristique
                    h_cost = PathFinder._get_heuristic_cost(graph, neighbor, end_station)
                    f_score[neighbor] = tentative_g_score + h_cost

                    # Ajouter à la file de priorité
                    heapq.heappush(open_set, (f_score[neighbor], tentative_g_score, neighbor, neighbor_line))

        # Aucun chemin trouvé
        log_warning(f"A* n'a trouvé aucun chemin après avoir exploré {nodes_explored} nœuds")
        return None

    @staticmethod
    def dijkstra_pathfinding(graph, start_station: str, end_station: str,
                             prefer_line_continuity: bool = True) -> Optional[Dict[str, Any]]:
        """
        Implémentation optimisée de l'algorithme de Dijkstra comme fallback pour A*.
        Version plus robuste et déterministe.

        Args:
            graph: Instance du graphe
            start_station: Station de départ
            end_station: Station d'arrivée
            prefer_line_continuity: Si True, pénalise les changements de ligne

        Returns:
            Dictionnaire contenant le chemin et le coût, ou None si aucun chemin
        """
        if start_station not in graph.nodes or end_station not in graph.nodes:
            missing = []
            if start_station not in graph.nodes:
                missing.append(f"depart: {start_station}")
            if end_station not in graph.nodes:
                missing.append(f"arrivee: {end_station}")
            log_warning(f"Station(s) non trouvee(s) avec Dijkstra: {', '.join(missing)}")
            return None

        # Si départ = arrivée
        if start_station == end_station:
            return {"path": [start_station], "distance": 0.0}

        # Structures pour Dijkstra
        distances = {node: float('infinity') for node in graph.nodes}
        distances[start_station] = 0.0

        # Prédécesseurs pour reconstruction du chemin
        predecessors = {node: None for node in graph.nodes}

        # Ligne utilisée pour arriver à chaque nœud
        previous_lines = {node: None for node in graph.nodes}

        # File de priorité: (distance, station, previous_line)
        priority_queue = [(0.0, start_station, None)]

        # Ensemble des stations visitées
        visited = set()

        # Statistiques de performance
        nodes_explored = 0

        while priority_queue:
            current_distance, current_station, current_line = heapq.heappop(priority_queue)

            # Si station déjà visitée, ignorer
            if current_station in visited:
                continue

            # Marquer comme visitée
            visited.add(current_station)
            nodes_explored += 1

            # Si destination atteinte
            if current_station == end_station:
                log_info(f"Dijkstra trouvé un chemin en explorant {nodes_explored} nœuds")

                # Reconstruction du chemin
                path = []
                current = end_station
                while current is not None:
                    path.append(current)
                    current = predecessors[current]
                path.reverse()

                return {
                    "path": path,
                    "distance": distances[end_station]
                }

            # Explorer les voisins
            for neighbor in graph.get_neighbors(current_station):
                if neighbor in visited:
                    continue

                # Coût de l'arête
                neighbor_line = graph.get_line_between_stations(current_station, neighbor)
                edge_cost = 1.0  # Coût de base

                # Pénalité pour changement de ligne
                if (prefer_line_continuity and current_line is not None and
                        neighbor_line != current_line and neighbor_line != "transfer"):
                    edge_cost += 0.15  # Pénalité légèrement plus faible que A*

                # Calcul de la nouvelle distance
                new_distance = current_distance + edge_cost

                # Si ce chemin est meilleur
                if new_distance < distances[neighbor]:
                    distances[neighbor] = new_distance
                    predecessors[neighbor] = current_station
                    previous_lines[neighbor] = neighbor_line
                    heapq.heappush(priority_queue, (new_distance, neighbor, neighbor_line))

        # Aucun chemin trouvé
        log_warning(f"Dijkstra n'a trouvé aucun chemin après avoir exploré {nodes_explored} nœuds")
        return None

    @staticmethod
    def find_optimal_path(graph, start_station: str, end_station: str,
                          prefer_line_continuity: bool = True) -> Optional[Dict[str, Any]]:
        """
        Méthode principale pour trouver le chemin optimal.
        Utilise A* en priorité avec fallback vers Dijkstra si A* échoue.

        Args:
            graph: Instance du graphe
            start_station: Station de départ
            end_station: Station d'arrivée
            prefer_line_continuity: Si True, pénalise les changements de ligne

        Returns:
            Dictionnaire contenant le chemin et le coût, ou None si aucun chemin
        """
        start_time = time.time()

        # Tentative avec A*
        try:
            log_info("Tentative de recherche avec A*...")
            result = PathFinder.a_star_pathfinding(graph, start_station, end_station, prefer_line_continuity)

            if result is not None:
                execution_time = time.time() - start_time
                log_info(f"A* réussie en {execution_time:.3f}s - Chemin de {len(result['path'])} stations")
                return result
            else:
                log_warning("A* n'a pas trouvé de chemin, passage à Dijkstra...")

        except Exception as e:
            log_error(f"Erreur avec A*: {e}, passage à Dijkstra...")

        # Fallback vers Dijkstra
        try:
            log_info("Recherche avec Dijkstra (fallback)...")
            result = PathFinder.dijkstra_pathfinding(graph, start_station, end_station, prefer_line_continuity)

            if result is not None:
                execution_time = time.time() - start_time
                log_info(f"Dijkstra réussie en {execution_time:.3f}s - Chemin de {len(result['path'])} stations")
                return result
            else:
                log_error("Dijkstra n'a pas trouvé de chemin non plus")

        except Exception as e:
            log_error(f"Erreur avec Dijkstra: {e}")

        return None

    @staticmethod
    def find_multiple_paths(graph, start_station: str, end_station: str,
                            max_paths: int = 3) -> List[Dict[str, Any]]:
        """
        Trouve plusieurs chemins alternatifs en utilisant des variations d'A*/Dijkstra.
        Plus efficace et robuste que l'algorithme de Yen pour les grands graphes.

        Args:
            graph: Instance du graphe
            start_station: Station de départ
            end_station: Station d'arrivée
            max_paths: Nombre maximum de chemins à retourner

        Returns:
            Liste des chemins trouvés, triés par coût croissant
        """
        paths = []

        # 1. Chemin optimal standard
        optimal_path = PathFinder.find_optimal_path(graph, start_station, end_station, prefer_line_continuity=True)
        if optimal_path:
            paths.append(optimal_path)

        # 2. Chemin sans préférence pour la continuité de ligne (plus de correspondances possibles)
        if len(paths) < max_paths:
            alternative_path = PathFinder.find_optimal_path(graph, start_station, end_station,
                                                            prefer_line_continuity=False)
            if alternative_path and not PathFinder._paths_are_equivalent(optimal_path, alternative_path):
                paths.append(alternative_path)

        # 3. Chemin avec pénalité réduite pour les changements de ligne
        if len(paths) < max_paths:
            # Modifiez temporairement les coûts pour explorer d'autres options
            # Cette approche est plus simple et efficace que l'algorithme de Yen
            relaxed_path = PathFinder._find_path_with_modified_costs(graph, start_station, end_station,
                                                                     penalty_factor=0.05)
            if relaxed_path and not any(PathFinder._paths_are_equivalent(relaxed_path, p) for p in paths):
                paths.append(relaxed_path)

        # Trier par coût et retourner
        paths.sort(key=lambda x: x["distance"])
        return paths[:max_paths]

    @staticmethod
    def _paths_are_equivalent(path1: Optional[Dict], path2: Optional[Dict], threshold: float = 0.1) -> bool:
        """
        Vérifie si deux chemins sont équivalents (même coût et chemin similaire).
        """
        if not path1 or not path2:
            return False

        # Vérifier si les coûts sont très proches
        cost_diff = abs(path1["distance"] - path2["distance"])
        if cost_diff > threshold:
            return False

        # Vérifier si les chemins ont des longueurs similaires
        len_diff = abs(len(path1["path"]) - len(path2["path"]))
        if len_diff > 2:  # Tolérance de 2 stations
            return False

        # Vérifier la similarité des stations (au moins 70% en commun)
        set1 = set(path1["path"])
        set2 = set(path2["path"])
        common = len(set1.intersection(set2))
        total = len(set1.union(set2))

        similarity = common / total if total > 0 else 0
        return similarity > 0.7

    @staticmethod
    def _find_path_with_modified_costs(graph, start_station: str, end_station: str,
                                       penalty_factor: float = 0.05) -> Optional[Dict[str, Any]]:
        """
        Trouve un chemin avec des coûts modifiés pour explorer des alternatives.
        """
        # Utilise Dijkstra avec une pénalité très réduite pour les changements de ligne
        if start_station not in graph.nodes or end_station not in graph.nodes:
            return None

        if start_station == end_station:
            return {"path": [start_station], "distance": 0.0}

        distances = {node: float('infinity') for node in graph.nodes}
        distances[start_station] = 0.0
        predecessors = {node: None for node in graph.nodes}
        previous_lines = {node: None for node in graph.nodes}

        priority_queue = [(0.0, start_station, None)]
        visited = set()

        while priority_queue:
            current_distance, current_station, current_line = heapq.heappop(priority_queue)

            if current_station in visited:
                continue

            visited.add(current_station)

            if current_station == end_station:
                path = []
                current = end_station
                while current is not None:
                    path.append(current)
                    current = predecessors[current]
                path.reverse()

                return {"path": path, "distance": distances[end_station]}

            for neighbor in graph.get_neighbors(current_station):
                if neighbor in visited:
                    continue

                neighbor_line = graph.get_line_between_stations(current_station, neighbor)
                edge_cost = 1.0

                # Pénalité très réduite pour changement de ligne
                if (current_line is not None and neighbor_line != current_line and
                        neighbor_line != "transfer"):
                    edge_cost += penalty_factor

                new_distance = current_distance + edge_cost

                if new_distance < distances[neighbor]:
                    distances[neighbor] = new_distance
                    predecessors[neighbor] = current_station
                    previous_lines[neighbor] = neighbor_line
                    heapq.heappush(priority_queue, (new_distance, neighbor, neighbor_line))

        return None    @staticmethod
    def create_detailed_route_info(graph, route_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crée des informations détaillées sur un trajet pour le calculateur d'horaires
        
        Args:
            graph: Instance du graphe
            route_data: Données de base du trajet (contient "path" et "distance")
            
        Returns:
            Dict avec les informations détaillées du trajet
        """
        path = route_data["path"]
        if len(path) < 2:
            return {"path": []}
        
        segments = []
        
        # Analyser chaque segment du trajet
        for i in range(len(path) - 1):
            from_station = path[i]
            to_station = path[i + 1]
            
            # Récupérer les informations de la ligne
            line = graph.get_line_between_stations(from_station, to_station)
            
            # Nettoyer le nom de la ligne
            if line in ["?", "transfer", "Correspondance"]:
                line = "Correspondance"
            
            # Créer le segment
            segment = {
                "from_station": graph.get_station_name(from_station),
                "to_station": graph.get_station_name(to_station),
                "from_station_id": from_station,
                "to_station_id": to_station,
                "travel_time": 2,  # Temps de base entre 2 stations (2 minutes)
                "route_info": {
                    "short_name": line
                }
            }
            
            segments.append(segment)
        
        return {
            "path": segments,
            "total_distance": route_data["distance"]
        }

    # ================== MÉTHODES DÉPRÉCIÉES (pour compatibilité) ==================

    @staticmethod
    def dijkstra_with_line_continuity(graph, start_station, end_station, prefer_line_continuity=True):
        """
        DÉPRÉCIÉE: Utilise find_optimal_path à la place.
        Maintenue pour compatibilité avec l'ancien code.
        """
        log_warning("dijkstra_with_line_continuity est dépréciée, utilisez find_optimal_path")
        return PathFinder.find_optimal_path(graph, start_station, end_station, prefer_line_continuity)

    @staticmethod
    def dijkstra(graph, start_station, end_station):
        """
        DÉPRÉCIÉE: Utilise find_optimal_path à la place.
        Maintenue pour compatibilité avec l'ancien code.
        """
        log_warning("dijkstra est dépréciée, utilisez find_optimal_path")
        return PathFinder.find_optimal_path(graph, start_station, end_station, prefer_line_continuity=True)

    @staticmethod
    def yen_k_shortest_paths(graph, start_station, end_station, k=2):
        """
        DÉPRÉCIÉE: Remplacée par find_multiple_paths qui est plus efficace.
        Maintenue pour compatibilité avec l'ancien code.
        """
        log_warning("yen_k_shortest_paths est dépréciée, utilisez find_multiple_paths")
        return PathFinder.find_multiple_paths(graph, start_station, end_station, max_paths=min(k, 3))

    @staticmethod
    def process_routes_for_frontend(graph, routes):
        """
        Traite les routes brutes pour les présenter dans un format adapté au frontend.
        Logique améliorée pour détecter correctement les vraies correspondances et calculer le CO2.
        """
        processed_routes = []

        for route_data in routes:
            path = route_data["path"]
            route_info = {
                "duration": round(route_data["distance"] * 2),  # Arrondi à l'entier près
                "transfers": 0,
                "segments": [],
                "co2": 0.0  # Initialiser le CO2 total
            }

            if len(path) < 2:
                continue

            # Calculer le CO2 total pour tout le trajet
            total_co2 = 0.0
            for i in range(len(path) - 1):
                from_station = path[i]
                to_station = path[i + 1]
                # Récupérer le CO2 pour cette arête
                edge_co2 = graph.get_co2_between_stations(from_station, to_station)
                total_co2 += edge_co2

            route_info["co2"] = round(total_co2, 1) # Arrondi à 1 décimale

            # Analyser le chemin pour détecter les lignes et nettoyer les données
            path_with_lines = []

            for i in range(len(path) - 1):
                from_station = path[i]
                to_station = path[i + 1]
                line = graph.get_line_between_stations(from_station, to_station)
                
                # LOG DEBUG: Ajouter des logs détaillés pour comprendre le problème
                from_name = graph.get_station_name(from_station)
                to_name = graph.get_station_name(to_station)
                # log_debug(f"Connexion {i}: {from_name} -> {to_name} | ligne détectée: '{line}'")

                path_with_lines.append({
                    "from": from_station,
                    "to": to_station,
                    "line": line,
                    "is_unknown": line in ["?", "transfer", "Correspondance"],
                })

            # LOG DEBUG: Afficher le path_with_lines complet
            # log_debug(f"Path avec lignes détecté: {[(graph.get_station_name(step['from']), graph.get_station_name(step['to']), step['line'], step['is_unknown']) for step in path_with_lines]}")

            # Étape 1: Inférer les lignes manquantes en regardant le contexte et corriger les erreurs
            for i, step in enumerate(path_with_lines):
                if step["is_unknown"]:
                    from_name = graph.get_station_name(step["from"])
                    to_name = graph.get_station_name(step["to"])
                    # log_debug(f"Tentative d'inférence pour connexion inconnue: {from_name} -> {to_name}")
                    
                    # Chercher la ligne précédente valide
                    prev_line = None
                    for j in range(i - 1, -1, -1):
                        if not path_with_lines[j]["is_unknown"]:
                            prev_line = path_with_lines[j]["line"]
                            break

                    # Chercher la ligne suivante valide
                    next_line = None
                    for j in range(i + 1, len(path_with_lines)):
                        if not path_with_lines[j]["is_unknown"]:
                            next_line = path_with_lines[j]["line"]
                            break

                    # log_debug(f"  Ligne précédente: {prev_line}, Ligne suivante: {next_line}")

                    # Si les lignes précédente et suivante sont identiques, c'est probablement une continuité
                    if prev_line and next_line and prev_line == next_line:
                        # log_debug(f"  -> Inférence: connexion continue sur ligne {prev_line}")
                        step["line"] = prev_line
                        step["is_unknown"] = False
                        step["inferred"] = True
                    else:
                        # Dernière tentative: vérifier si les deux stations sont directement connectées sur une même ligne
                        # en examinant tous les voisins directs
                        from_neighbors = graph.get_neighbors(step["from"])
                        if step["to"] in from_neighbors:
                            # Il y a une connexion directe, récupérer toutes les lignes possibles
                            all_lines = set()
                            
                            # Parcourir toutes les arêtes entre ces deux stations
                            for neighbor in from_neighbors:
                                if neighbor == step["to"]:
                                    line = graph.get_line_between_stations(step["from"], step["to"])
                                    if line not in ["?", "transfer", "Correspondance"]:
                                        all_lines.add(line)
                            
                            # Si une ligne spécifique est trouvée, l'utiliser
                            if len(all_lines) == 1:
                                inferred_line = list(all_lines)[0]
                                # log_debug(f"  -> Inférence par connexion directe: ligne {inferred_line}")
                                step["line"] = inferred_line
                                step["is_unknown"] = False
                                step["inferred"] = True
                            elif len(all_lines) > 1:
                                # S'il y a plusieurs lignes possibles, choisir celle qui correspond au contexte
                                if prev_line in all_lines:
                                    # log_debug(f"  -> Inférence par contexte précédent: ligne {prev_line}")
                                    step["line"] = prev_line
                                    step["is_unknown"] = False
                                    step["inferred"] = True
                                elif next_line in all_lines:
                                    # log_debug(f"  -> Inférence par contexte suivant: ligne {next_line}")
                                    step["line"] = next_line
                                    step["is_unknown"] = False
                                    step["inferred"] = True
                                else:
                                    pass  # log_debug(f"  -> Plusieurs lignes possibles {all_lines}, garder comme transfert")
                            else:
                                # Cas spécial : si prev_line et next_line sont identiques et correspondent à une ligne valide,
                                # et qu'il s'agit d'une connexion directe marquée comme transfer, 
                                # alors c'est probablement une continuité de ligne mal étiquetée
                                if (prev_line and next_line and prev_line == next_line and
                                    prev_line not in ["?", "transfer", "Correspondance"]):
                                    # log_debug(f"  -> Inférence par continuité de ligne: {prev_line} (transfert mal étiqueté)")
                                    step["line"] = prev_line
                                    step["is_unknown"] = False
                                    step["inferred"] = True
                                else:
                                    pass  # log_debug(f"  -> Pas d'inférence possible, reste comme transfert")
                        else:
                            pass  # log_debug(f"  -> Pas de connexion directe, reste comme transfert")

            # Étape 2: Grouper les segments par ligne continue de manière intelligente
            segments = []
            current_segment = None

            def are_same_logical_line(line1, line2):
                """Vérifie si deux identifiants de ligne correspondent à la même ligne logique"""
                result = False
                
                if line1 == line2:
                    result = True
                elif line1 and line2:
                    # Nettoyer les noms de ligne pour enlever les variations
                    clean_line1 = line1.replace("bis", "B").replace("Bis", "B")
                    clean_line2 = line2.replace("bis", "B").replace("Bis", "B")
                    
                    # Extraire le numéro principal (exemple: "3", "3B", "7", "7B")
                    import re
                    pattern = r'^(\d+[AB]?)'
                    match1 = re.match(pattern, clean_line1)
                    match2 = re.match(pattern, clean_line2)
                    
                    if match1 and match2:
                        result = match1.group(1) == match2.group(1)
                
                # log_debug(f"Comparaison ligne: '{line1}' vs '{line2}' -> {result}")
                return result

            for step in path_with_lines:
                if step["is_unknown"]:
                    # Si c'est encore inconnu après inférence, c'est probablement un vrai transfert
                    # Mais seulement si c'est entre deux stations différentes
                    if step["from"] != step["to"]:
                        from_name = graph.get_station_name(step["from"])
                        to_name = graph.get_station_name(step["to"])
                        # log_debug(f"Ajout d'un transfert: {from_name} -> {to_name}")
                        
                        if current_segment is not None:
                            segments.append(current_segment)
                            current_segment = None

                        # Ajouter le transfert comme segment séparé
                        segments.append({
                            "line": "Correspondance à pied",
                            "from": step["from"],
                            "to": step["to"],
                            "stops": 1,
                            "is_transfer": True
                        })
                    else:
                        from_name = graph.get_station_name(step["from"])
                        # log_debug(f"Ignorer transfert fictif sur la même station: {from_name}")
                    # Si from == to, ignorer ce "transfert" fictif
                else:
                    # C'est une connexion de ligne valide
                    from_name = graph.get_station_name(step["from"])
                    to_name = graph.get_station_name(step["to"])
                    
                    # Utiliser la logique améliorée pour détecter la même ligne logique
                    if current_segment is None or not are_same_logical_line(current_segment["line"], step["line"]):
                        # Commencer un nouveau segment
                        # log_debug(f"Nouveau segment: {from_name} -> {to_name} (ligne: {step['line']})")
                        if current_segment is not None:
                            segments.append(current_segment)

                        current_segment = {
                            "line": step["line"],
                            "from": step["from"],
                            "to": step["to"],
                            "stops": 1,
                            "is_transfer": False,
                            "stations": [step["from"], step["to"]]
                        }
                    else:
                        # Continuer le segment existant (même ligne logique)
                        # log_debug(f"Continuer segment existant: {from_name} -> {to_name} (ligne: {step['line']})")
                        current_segment["to"] = step["to"]
                        current_segment["stops"] += 1
                        current_segment["stations"].append(step["to"])

            # Finaliser le dernier segment
            if current_segment is not None:
                segments.append(current_segment)

            # Si aucun segment, créer un segment basique
            if not segments:
                segments.append({
                    "line": "Métro",
                    "from": path[0],
                    "to": path[-1],
                    "stops": len(path) - 1,
                    "is_transfer": False
                })

            # Convertir pour le frontend
            for segment in segments:
                route_segment = {
                    "line": segment["line"],
                    "from": graph.get_station_name(segment["from"]),
                    "to": graph.get_station_name(segment["to"]),
                    "stops": segment["stops"]
                }

                if segment.get("is_transfer", False):
                    route_segment["type"] = "transfer"

                route_info["segments"].append(route_segment)

            # Compter les vraies correspondances (changements de ligne réels + transferts)
            real_line_segments = [s for s in segments if not s.get("is_transfer", False)]
            transfer_segments = [s for s in segments if s.get("is_transfer", False)]

            # Correspondances = changements de ligne + transferts
            correspondances = max(0, len(real_line_segments) - 1) + len(transfer_segments)
            route_info["transfers"] = correspondances
            processed_routes.append(route_info)

        return processed_routes

    @staticmethod
    def deduplicate_routes(routes):
        """
        Élimine les trajets identiques et incohérents en comparant les segments.
        Retourne une liste de trajets uniques et logiques.
        CORRECTION: Ajout de logs pour diagnostiquer les filtrages.
        """
        unique_routes = []
        seen_routes = set()
        filtered_count = 0

        log_debug(f"Début déduplication: {len(routes)} routes à analyser")

        for i, route in enumerate(routes):
            # Vérifier d'abord si le trajet est logique
            if not PathFinder._is_route_logical(route):
                filtered_count += 1
                log_debug(f"Route {i + 1} filtrée car illogique: {route.get('segments', [])}")
                continue

            # Créer une signature unique pour ce trajet basée sur les segments
            segments_signature = []
            for segment in route["segments"]:
                seg_key = (
                    segment["line"],
                    segment["from"],
                    segment["to"],
                    segment.get("type", "normal")
                )
                segments_signature.append(seg_key)

            # Convertir en tuple pour pouvoir l'utiliser comme clé de set
            route_signature = tuple(segments_signature)

            # Si on n'a pas encore vu ce trajet, l'ajouter
            if route_signature not in seen_routes:
                seen_routes.add(route_signature)
                unique_routes.append(route)
                log_debug(f"Route {i + 1} gardée: {len(route['segments'])} segments")
            else:
                log_debug(f"Route {i + 1} dupliquée, ignorée")

        log_info(f"Déduplication terminée: {len(unique_routes)} routes uniques gardées, {filtered_count} filtrées")

        # SÉCURITÉ: Si toutes les routes ont été filtrées mais qu'on en avait au départ
        if len(unique_routes) == 0 and len(routes) > 0:
            log_warning("ATTENTION: Toutes les routes ont été filtrées ! Retour de la première route originale.")
            return [routes[0]]  # Retourner au moins la première route

        return unique_routes

    @staticmethod
    def _is_route_logical(route):
        """
        Vérifie si un trajet est logique (pas de transferts absurdes).
        ATTENTION: Cette fonction doit être peu restrictive pour éviter de supprimer tous les chemins.
        """
        segments = route["segments"]

        if not segments:
            return False

        # CORRECTION: Être moins strict sur les filtres pour éviter de supprimer tous les chemins

        # Seuls les cas vraiment problématiques sont filtrés :

        # 1. Vérifier qu'il n'y a pas plus de 3 segments identiques consécutifs (cas extrême)
        consecutive_identical = 0
        for i in range(len(segments) - 1):
            current = segments[i]
            next_seg = segments[i + 1]

            if (current["line"] == next_seg["line"] and
                    current["from"] == next_seg["from"] and
                    current["to"] == next_seg["to"] and
                    current.get("type", "normal") == next_seg.get("type", "normal")):
                consecutive_identical += 1
                if consecutive_identical >= 2:  # Plus de 2 segments identiques consécutifs
                    return False
            else:
                consecutive_identical = 0

        # 2. Vérifier qu'il n'y a pas de boucles infinies (plus de 20 segments = suspect)
        if len(segments) > 20:
            log_warning(f"Trajet avec {len(segments)} segments, possiblement une boucle")
            return False

        # SUPPRESSION DES FILTRES TROP STRICTS :
        # - Les transferts au début/fin peuvent être légitimes (stations avec plusieurs quais)
        # - Les transferts intra-station sont normaux pour les correspondances
        # - Les segments courts sont normaux dans le métro parisien

        return True

        return processed_routes


@router.get("/routes", response_model=Dict[str, Any])
async def find_routes(depart: str, arrivee: str):
    """
    Endpoint pour trouver les trajets entre deux stations
    """
    from backend.main import get_unique_graph
    from backend.utils.fuzzy_search import suggest_station_alternatives, create_user_friendly_error_message

    start_time = time.time()
    log_info(f"Recherche de trajets entre '{depart}' et '{arrivee}'")

    # Récupérer l'instance du graphe
    try:
        graph = get_unique_graph()
        if not graph:
            raise HTTPException(status_code=500, detail="Le graphe n'est pas initialisé")
    except Exception as e:
        log_error(f"Erreur lors de la récupération du graphe: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

    # Nettoyer les noms de stations pour la recherche
    depart_clean = normalize_text(depart).strip().lower()
    arrivee_clean = normalize_text(arrivee).strip().lower()

    # Trouver les stations correspondantes (recherche approximative améliorée)
    depart_matches = graph.find_station_by_name(depart_clean)
    arrivee_matches = graph.find_station_by_name(arrivee_clean)

    # Vérification supplémentaire pour éviter les confusions
    def validate_station_match(original_name: str, station_id: str, graph) -> bool:
        """Valide qu'une correspondance de station est correcte"""
        if not station_id:
            return False

        station_name = graph.get_station_name(station_id)
        original_normalized = normalize_text(original_name).lower()
        station_normalized = normalize_text(station_name).lower()

        # Vérification stricte pour les stations avec "porte de"
        if "porte de" in original_normalized and "porte de" in station_normalized:
            original_after = original_normalized.replace("porte de ", "").strip()
            station_after = station_normalized.replace("porte de ", "").strip()

            # Si les suffixes sont très différents, rejeter
            if original_after != station_after and len(original_after) > 2:
                similarity = SequenceMatcher(None, original_after, station_after).ratio()
                if similarity < 0.7:  # Seuil strict pour éviter charenton->champerret
                    log_warning(
                        f"Correspondance rejetée: '{original_name}' -> '{station_name}' (similarité suffixe: {similarity:.2f})")
                    return False

        return True

    # Gestion des erreurs avec suggestions améliorées
    if not depart_matches:
        try:
            suggestions = suggest_station_alternatives(graph.stations, depart_clean, max_suggestions=3)
            error_message = create_user_friendly_error_message(depart, suggestions)
        except:
            error_message = f"Aucune station trouvée pour '{depart}'"

        log_warning(f"Station de départ non trouvée: {depart} -> {error_message}")
        return {"error": error_message}

    # Validation de la correspondance de départ
    valid_depart_matches = [match for match in depart_matches if validate_station_match(depart, match, graph)]
    if not valid_depart_matches:
        log_warning(f"Correspondance de départ rejetée pour '{depart}'")
        try:
            suggestions = suggest_station_alternatives(graph.stations, depart_clean, max_suggestions=3)
            error_message = create_user_friendly_error_message(depart, suggestions)
        except:
            error_message = f"Aucune station valide trouvée pour '{depart}'"
        return {"error": error_message}

    if not arrivee_matches:
        try:
            suggestions = suggest_station_alternatives(graph.stations, arrivee_clean, max_suggestions=3)
            error_message = create_user_friendly_error_message(arrivee, suggestions)
        except:
            error_message = f"Aucune station trouvée pour '{arrivee}'"

        log_warning(f"Station d'arrivée non trouvée: {arrivee} -> {error_message}")
        return {"error": error_message}

    # Validation de la correspondance d'arrivée
    valid_arrivee_matches = [match for match in arrivee_matches if validate_station_match(arrivee, match, graph)]
    if not valid_arrivee_matches:
        log_warning(f"Correspondance d'arrivée rejetée pour '{arrivee}'")
        try:
            suggestions = suggest_station_alternatives(graph.stations, arrivee_clean, max_suggestions=3)
            error_message = create_user_friendly_error_message(arrivee, suggestions)
        except:
            error_message = f"Aucune station valide trouvée pour '{arrivee}'"
        return {"error": error_message}

    # Prendre la première correspondance valide
    start_station_id = valid_depart_matches[0]
    end_station_id = valid_arrivee_matches[0]

    start_station_name = graph.get_station_name(start_station_id)
    end_station_name = graph.get_station_name(end_station_id)

    log_info(f"Calcul des trajets entre {start_station_name} et {end_station_name}")

    # Recherche des chemins optimaux (remplace l'ancien algorithme de Yen)
    routes = PathFinder.find_multiple_paths(graph, start_station_id, end_station_id, max_paths=5)

    if not routes:
        return {
            "error": f"Aucun trajet trouvé entre {start_station_name} et {end_station_name}"
        }

    # Traiter les routes pour les adapter au format attendu par le frontend
    processed_routes = PathFinder.process_routes_for_frontend(graph, routes)

    # Éliminer les trajets identiques
    unique_routes = PathFinder.deduplicate_routes(processed_routes)

    # CORRECTION: Garantir qu'au moins un chemin soit retourné
    if len(unique_routes) == 0:
        # Si le filtrage a supprimé tous les chemins, retourner au moins le premier chemin trouvé
        if processed_routes:
            log_warning(f"Filtrage trop strict: tous les chemins ont été supprimés. Retour du premier chemin trouvé.")
            final_routes = [processed_routes[0]]  # Garder au moins le premier chemin
        else:
            final_routes = []  # Vraiment aucun chemin trouvé
    elif len(unique_routes) == 1:
        final_routes = unique_routes  # Un seul trajet unique
    else:
        # Garder entre 2 et 5 trajets uniques, en priorisant les plus courts
        final_routes = sorted(unique_routes, key=lambda r: r["duration"])[:min(5, len(unique_routes))]

    execution_time = time.time() - start_time
    log_info(f"{len(final_routes)} trajet(s) unique(s) trouvé(s) en {execution_time:.2f} secondes")

    return {
        "from": start_station_name,
        "to": end_station_name,
        "routes": final_routes
    }


@router.get("/routes-with-schedule", response_model=Dict[str, Any])
async def find_routes_with_schedule(
    depart: str, 
    arrivee: str, 
    departure_time: Optional[str] = Query(None, description="Heure de départ souhaitée au format HH:MM"),
    arrival_time: Optional[str] = Query(None, description="Heure d'arrivée souhaitée au format HH:MM"),
    date: Optional[str] = Query(None, description="Date au format YYYY-MM-DD (défaut: aujourd'hui)")
):
    """
    Endpoint pour trouver les trajets entre deux stations avec prise en compte des horaires
    """
    from backend.main import get_unique_graph
    from backend.utils.fuzzy_search import suggest_station_alternatives, create_user_friendly_error_message

    start_time = time.time()
    log_info(f"Recherche de trajets avec horaires entre '{depart}' et '{arrivee}'")

    # Initialiser le calculateur d'horaires
    schedule_calculator = MetroScheduleCalculator()

    # Récupérer l'instance du graphe
    try:
        graph = get_unique_graph()
        if not graph:
            raise HTTPException(status_code=500, detail="Le graphe n'est pas initialisé")
    except Exception as e:
        log_error(f"Erreur lors de la récupération du graphe: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

    # Traitement de la date et de l'heure
    try:
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        else:
            target_date = datetime.now().date()

        if departure_time:
            departure_dt = datetime.strptime(departure_time, "%H:%M").time()
            target_datetime = datetime.combine(target_date, departure_dt)
        elif arrival_time:
            # Si heure d'arrivée spécifiée, on commencera par calculer comme si c'était un départ
            # puis on ajustera après avoir trouvé la durée du trajet
            arrival_dt = datetime.strptime(arrival_time, "%H:%M").time()
            target_datetime = datetime.combine(target_date, arrival_dt)
        else:
            # Par défaut, maintenant
            target_datetime = datetime.now()

    except ValueError as e:
        return {"error": f"Format de date/heure invalide: {str(e)}"}

    # Nettoyer les noms de stations pour la recherche
    depart_clean = normalize_text(depart).strip().lower()
    arrivee_clean = normalize_text(arrivee).strip().lower()

    # Trouver les stations correspondantes (utilise la même logique que l'endpoint existant)
    depart_matches = graph.find_station_by_name(depart_clean)
    arrivee_matches = graph.find_station_by_name(arrivee_clean)

    # Validation des correspondances (même logique que l'endpoint existant)
    def validate_station_match(original_name: str, station_id: str, graph) -> bool:
        if not station_id:
            return False

        station_name = graph.get_station_name(station_id)
        original_normalized = normalize_text(original_name).lower()
        station_normalized = normalize_text(station_name).lower()

        if "porte de" in original_normalized and "porte de" in station_normalized:
            original_after = original_normalized.replace("porte de ", "").strip()
            station_after = station_normalized.replace("porte de ", "").strip()

            if original_after != station_after and len(original_after) > 2:
                similarity = SequenceMatcher(None, original_after, station_after).ratio()
                if similarity < 0.7:
                    log_warning(
                        f"Correspondance rejetée: '{original_name}' -> '{station_name}' (similarité suffixe: {similarity:.2f})")
                    return False

        return True

    # Gestion des erreurs pour les stations
    if not depart_matches:
        try:
            suggestions = suggest_station_alternatives(graph.stations, depart_clean, max_suggestions=3)
            error_message = create_user_friendly_error_message(depart, suggestions)
        except:
            error_message = f"Aucune station trouvée pour '{depart}'"
        return {"error": error_message}

    valid_depart_matches = [match for match in depart_matches if validate_station_match(depart, match, graph)]
    if not valid_depart_matches:
        try:
            suggestions = suggest_station_alternatives(graph.stations, depart_clean, max_suggestions=3)
            error_message = create_user_friendly_error_message(depart, suggestions)
        except:
            error_message = f"Aucune station valide trouvée pour '{depart}'"
        return {"error": error_message}

    if not arrivee_matches:
        try:
            suggestions = suggest_station_alternatives(graph.stations, arrivee_clean, max_suggestions=3)
            error_message = create_user_friendly_error_message(arrivee, suggestions)
        except:
            error_message = f"Aucune station trouvée pour '{arrivee}'"
        return {"error": error_message}

    valid_arrivee_matches = [match for match in arrivee_matches if validate_station_match(arrivee, match, graph)]
    if not valid_arrivee_matches:
        try:
            suggestions = suggest_station_alternatives(graph.stations, arrivee_clean, max_suggestions=3)
            error_message = create_user_friendly_error_message(arrivee, suggestions)
        except:
            error_message = f"Aucune station valide trouvée pour '{arrivee}'"
        return {"error": error_message}

    # Prendre la première correspondance valide
    start_station_id = valid_depart_matches[0]
    end_station_id = valid_arrivee_matches[0]

    start_station_name = graph.get_station_name(start_station_id)
    end_station_name = graph.get_station_name(end_station_id)

    log_info(f"Calcul des trajets avec horaires entre {start_station_name} et {end_station_name}")

    # Recherche des chemins optimaux
    routes = PathFinder.find_multiple_paths(graph, start_station_id, end_station_id, max_paths=3)

    if not routes:
        return {
            "error": f"Aucun trajet trouvé entre {start_station_name} et {end_station_name}"
        }

    # Traiter les routes avec les horaires - générer plusieurs options temporelles
    scheduled_routes = []
    
    # Générer plusieurs créneaux horaires autour de l'heure demandée
    time_slots = []
    
    if departure_time:
        # Pour un départ, proposer des options toutes les 10-15 minutes
        base_time = target_datetime
        time_slots = [
            base_time - timedelta(minutes=15),
            base_time - timedelta(minutes=8),
            base_time,
            base_time + timedelta(minutes=8),
            base_time + timedelta(minutes=15)
        ]
    elif arrival_time:
        # Pour une arrivée, proposer différents départs en calculant à rebours
        base_time = target_datetime
        # Estimer la durée du trajet le plus rapide
        if routes:
            estimated_duration = routes[0]["distance"] * 2  # 2 minutes par "unité de distance"
            base_departure = base_time - timedelta(minutes=estimated_duration)
            time_slots = [
                base_departure - timedelta(minutes=20),
                base_departure - timedelta(minutes=10),
                base_departure,
                base_departure + timedelta(minutes=10),
                base_departure + timedelta(minutes=20)
            ]
        else:
            time_slots = [target_datetime]
    else:
        # Mode "maintenant" - proposer des options dans les prochaines heures
        base_time = target_datetime
        time_slots = [
            base_time,
            base_time + timedelta(minutes=15),
            base_time + timedelta(minutes=30),
            base_time + timedelta(minutes=45),
            base_time + timedelta(minutes=60)
        ]
    
    # Traiter d'abord les routes avec la logique d'inférence corrigée
    processed_routes = PathFinder.process_routes_for_frontend(graph, routes)
    
    # Fonction pour convertir les segments corrigés en format compatible avec create_detailed_route_info
    def convert_corrected_segments_to_detailed_path(corrected_segments, original_path):
        """Convertit les segments corrigés en format détaillé pour le calculateur d'horaires"""
        detailed_path = []
        
        for segment in corrected_segments:
            # Traiter les correspondances à pied (vraies correspondances)
            if segment.get("type") == "transfer" or segment["line"] == "Correspondance à pied":
                # Ajouter la correspondance à pied avec un temps estimé
                detailed_path.append({
                    "from_station": segment["from"],
                    "to_station": segment["to"],
                    "from_station_id": segment["from"],  # Sera résolu par le calculateur
                    "to_station_id": segment["to"],      # Sera résolu par le calculateur
                    "travel_time": 3,  # Temps estimé pour une correspondance à pied
                    "route_info": {
                        "short_name": "Correspondance"
                    }
                })
                continue
                
            # Trouver les stations correspondantes dans le path original pour les segments de métro
            from_station = segment["from"]
            to_station = segment["to"]
            stops = segment["stops"]
            
            # Créer des segments détaillés pour chaque arrêt
            # Pour un segment de N arrêts, créer N segments individuels
            
            # Trouver les indices dans le path original
            try:
                path_stations = [graph.get_station_name(station_id) for station_id in original_path]
                from_idx = path_stations.index(from_station)
                to_idx = path_stations.index(to_station)
                
                # Créer des segments individuels pour chaque tronçon
                for i in range(from_idx, to_idx):
                    from_station_id = original_path[i]
                    to_station_id = original_path[i + 1]
                    
                    detailed_path.append({
                        "from_station": graph.get_station_name(from_station_id),
                        "to_station": graph.get_station_name(to_station_id),
                        "from_station_id": from_station_id,
                        "to_station_id": to_station_id,
                        "travel_time": 2,  # Temps de base entre 2 stations
                        "route_info": {
                            "short_name": segment["line"]
                        }
                    })
            except (ValueError, IndexError) as e:
                # Si on ne peut pas trouver les stations, créer un segment simple
                log_warning(f"Impossible de détailler le segment {from_station} → {to_station}: {e}")
                detailed_path.append({
                    "from_station": from_station,
                    "to_station": to_station,
                    "from_station_id": from_station,  # Sera résolu par le calculateur
                    "to_station_id": to_station,      # Sera résolu par le calculateur
                    "travel_time": stops * 2,  # Temps estimé
                    "route_info": {
                        "short_name": segment["line"]
                    }
                })
        
        return detailed_path
    
    # Pour chaque créneau horaire, calculer les meilleurs itinéraires
    for slot_time in time_slots:
        for i, (route, processed_route) in enumerate(zip(routes[:2], processed_routes[:2])):  # Limiter à 2 routes par créneau pour éviter trop d'options
            # Convertir les segments corrigés en format détaillé
            corrected_detailed_path = convert_corrected_segments_to_detailed_path(
                processed_route["segments"], 
                route["path"]
            )
            
            # Créer la structure de route avec les segments corrigés
            route_with_corrected_segments = {
                "path": corrected_detailed_path,
                "total_distance": route["distance"]
            }
            
            # Calculer l'itinéraire avec les horaires pour ce créneau
            scheduled_route = schedule_calculator.calculate_journey_time_with_schedule(
                route_with_corrected_segments, slot_time, graph
            )
            
            if "error" not in scheduled_route:
                # Utiliser les informations corrigées de process_routes_for_frontend
                
                # Ajouter les informations de base et l'identifiant de créneau
                scheduled_route.update({
                    "from": start_station_name,
                    "to": end_station_name,
                    "base_duration": processed_route["duration"],  # Utiliser la durée corrigée
                    "duration": round(scheduled_route["total_travel_time"]),  # Durée totale avec horaires
                    "transfers": processed_route["transfers"],  # Utiliser le nombre de correspondances corrigé
                    "co2": processed_route["co2"],  # Utiliser le CO2 corrigé
                    "route_variant": i + 1,  # Variante de route (1, 2, etc.)
                    "time_slot": slot_time.strftime("%H:%M"),  # Créneau horaire de référence
                    "is_requested_time": slot_time == target_datetime or (arrival_time and abs((datetime.combine(target_date, datetime.strptime(scheduled_route["arrival_time"], "%H:%M").time()) - target_datetime).total_seconds()) < 300),  # Dans les 5 minutes de l'heure demandée
                    # Informations nécessaires pour l'affichage sur la carte
                    "path": route["path"],  # Liste des IDs de stations
                    "distance": route["distance"],  # Distance du trajet
                    "detailed_path": corrected_detailed_path,  # Segments détaillés corrigés
                    # Ajouter les segments corrigés pour l'affichage
                    "corrected_segments": processed_route["segments"]  # Segments avec logique d'inférence corrigée
                })
                scheduled_routes.append(scheduled_route)
            else:
                log_debug(f"Impossible de calculer les horaires pour le créneau {slot_time.strftime('%H:%M')}: {scheduled_route['error']}")
    
    if not scheduled_routes:
        # Si aucun trajet n'a pu être calculé avec les horaires, 
        # vérifier si c'est un problème d'heure
        current_time = target_datetime.time()
        lines_status = schedule_calculator.get_all_lines_status(current_time)
        running_lines = [line for line, status in lines_status.items() if status]
        
        if not running_lines:
            return {
                "error": f"Aucune ligne de métro ne circule à {target_datetime.strftime('%H:%M')}. "
                         f"Le service reprend généralement vers 05:30."
            }
        else:
            return {
                "error": f"Impossible de calculer les horaires pour les trajets trouvés à {target_datetime.strftime('%H:%M')}. "
                         f"Les lignes {', '.join(running_lines)} circulent à cette heure."
            }

    # Filtrer et trier les routes
    unique_routes = []
    seen_combinations = set()
    
    for route in scheduled_routes:
        # Créer une signature unique basée sur l'heure de départ et l'itinéraire
        route_signature = (
            route["departure_time"],
            route["arrival_time"], 
            tuple(s.get("line", "") for s in route["segments"]),
            route["transfers"]
        )
        
        if route_signature not in seen_combinations:
            seen_combinations.add(route_signature)
            unique_routes.append(route)
    
    # Trier et attribuer les labels de pertinence
    if departure_time:
        # Trier d'abord par pertinence par rapport à l'heure demandée
        unique_routes.sort(key=lambda r: (
            not r.get("is_requested_time", False),  # Trajets à l'heure demandée en premier
            abs((datetime.combine(target_date, datetime.strptime(r["departure_time"], "%H:%M").time()) - target_datetime).total_seconds()),  # Distance à l'heure demandée
            r["total_travel_time"]  # Puis par durée
        ))
    elif arrival_time:
        unique_routes.sort(key=lambda r: (
            not r.get("is_requested_time", False),  # Trajets à l'heure demandée en premier
            abs((datetime.combine(target_date, datetime.strptime(r["arrival_time"], "%H:%M").time()) - target_datetime).total_seconds()),  # Proximité de l'heure d'arrivée
            r["total_travel_time"]  # Puis par durée
        ))
    else:
        unique_routes.sort(key=lambda r: (
            r["departure_time"],  # Par heure de départ
            r["total_travel_time"]  # Puis par durée
        ))
    
    # Limiter à 3 options et attribuer les labels de pertinence
    final_routes = unique_routes[:3]
    
    # Attribuer les labels de pertinence
    for i, route in enumerate(final_routes):
        if departure_time or arrival_time:
            if i == 0:
                route["option_label"] = "Meilleure option"
            elif len(final_routes) > 1:
                # Pour les options suivantes, déterminer si c'est plus tôt ou plus tard
                requested_time = target_datetime
                if departure_time:
                    route_time = datetime.combine(target_date, datetime.strptime(route["departure_time"], "%H:%M").time())
                else:  # arrival_time
                    route_time = datetime.combine(target_date, datetime.strptime(route["arrival_time"], "%H:%M").time())
                
                if route_time < requested_time:
                    route["option_label"] = "Plus tôt"
                else:
                    route["option_label"] = "Plus tard"
        else:
            # Mode "maintenant" - utiliser une numérotation simple
            route["option_label"] = f"Option {i + 1}"

    execution_time = time.time() - start_time
    log_info(f"{len(final_routes)} trajet(s) avec horaires trouvé(s) en {execution_time:.2f} secondes")

    return {
        "from": start_station_name,
        "to": end_station_name,
        "requested_departure_time": departure_time,
        "requested_arrival_time": arrival_time,
        "date": target_date.strftime("%Y-%m-%d"),
        "routes": final_routes
    }


@router.get("/metro-status", response_model=Dict[str, Any])
async def get_metro_status(time: Optional[str] = Query(None, description="Heure au format HH:MM pour vérifier le statut des lignes")):
    """
    Endpoint pour obtenir le statut des lignes de métro à une heure donnée
    """
    from backend.utils.schedule_calculator import MetroScheduleCalculator
    
    schedule_calculator = MetroScheduleCalculator()
    
    try:
        if time:
            check_time = datetime.strptime(time, "%H:%M").time()
        else:
            check_time = datetime.now().time()
        
        lines_status = schedule_calculator.get_all_lines_status(check_time)
        
        # Ajouter des informations détaillées pour chaque ligne
        detailed_status = {}
        for line, is_running in lines_status.items():
            if is_running:
                frequency = schedule_calculator.get_frequency_for_time(line, check_time)
                next_departure = schedule_calculator.get_next_departure(line, datetime.now().replace(hour=check_time.hour, minute=check_time.minute))
                detailed_status[line] = {
                    "running": True,
                    "frequency": frequency,
                    "next_departure": next_departure.strftime("%H:%M") if next_departure else None
                }
            else:
                next_service = schedule_calculator._find_next_service_time(line, datetime.now().replace(hour=check_time.hour, minute=check_time.minute))
                detailed_status[line] = {
                    "running": False,
                    "frequency": None,
                    "next_service": next_service.strftime("%H:%M") if next_service else None
                }
        
        return {
            "checked_time": time or check_time.strftime("%H:%M"),
            "lines_status": detailed_status,
            "total_lines": len(lines_status),
            "running_lines": len([s for s in lines_status.values() if s])
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Format d'heure invalide: {str(e)}")
    except Exception as e:
        log_error(f"Erreur lors du calcul du statut des métros: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")
