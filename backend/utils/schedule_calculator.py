"""
Module pour calculer les horaires de passage des métros basés sur les fréquences
"""

from datetime import datetime, timedelta, time
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class MetroScheduleCalculator:
    """
    Classe pour calculer les horaires de passage des métros basés sur les fréquences
    """
    
    def __init__(self):
        # Fréquences de passages par ligne et par plage horaire (en minutes)
        self.frequencies = {
            "1": {
                "05:30-07:30": 4,
                "07:30-09:30": 2,
                "09:30-16:30": 3,
                "16:30-20:30": 2,
                "20:30-00:39": 4
            },
            "2": {
                "05:30-07:30": 5,
                "07:30-09:30": 3,
                "09:30-16:30": 4,
                "16:30-20:30": 3,
                "20:30-00:42": 6
            },
            "3": {
                "05:30-07:30": 5,
                "07:30-09:30": 3,
                "09:30-16:30": 5,
                "16:30-20:30": 3,
                "20:30-00:44": 5
            },
            "3bis": {
                "05:32-07:30": 6,
                "07:30-09:30": 4,
                "09:30-20:30": 5,
                "20:30-01:11": 8
            },
            "4": {
                "05:30-07:30": 4,
                "07:30-20:30": 3,
                "20:30-01:01": 4
            },
            "5": {
                "05:30-07:30": 5,
                "07:30-09:30": 2,
                "09:30-16:30": 3,
                "16:30-20:30": 2,
                "20:30-00:42": 6
            },
            "6": {
                "05:30-07:30": 4,
                "07:30-09:30": 3,
                "09:30-16:30": 4,
                "16:30-20:30": 3,
                "20:30-00:39": 5
            },
            "7": {
                "05:28-07:30": 8,
                "07:30-09:30": 4,
                "09:30-16:30": 7,
                "16:30-20:30": 5,
                "20:30-00:28": 11
            },
            "7bis": {
                "05:31-07:30": 7,
                "07:30-09:30": 5,
                "09:30-16:30": 5,
                "16:30-20:30": 6,
                "20:30-00:54": 8
            },
            "8": {
                "05:30-07:30": 3,
                "07:30-09:30": 2,
                "09:30-16:30": 4,
                "16:30-20:30": 3,
                "20:30-00:24": 7
            },
            "9": {
                "05:30-07:30": 3,
                "07:30-09:30": 2,
                "09:30-16:30": 3,
                "16:30-20:30": 2,
                "20:30-00:42": 6
            },
            "10": {
                "05:35-07:30": 7,
                "07:30-09:30": 5,
                "09:30-16:30": 6,
                "16:30-20:30": 6,
                "20:30-00:47": 9
            },
            "11": {
                "05:30-07:30": 4,
                "07:30-09:30": 2,
                "09:30-16:30": 3,
                "16:30-20:30": 2,
                "20:30-00:51": 5
            },
            "12": {
                "05:30-07:30": 4,
                "07:30-09:30": 3,
                "09:30-16:30": 4,
                "16:30-20:30": 3,
                "20:30-00:33": 6
            },
            "13": {
                "05:30-07:30": 6,
                "07:30-09:30": 4,
                "09:30-16:30": 6,
                "16:30-20:30": 4,
                "20:30-00:37": 9
            },
            "14": {
                "05:30-07:30": 2,
                "07:30-09:30": 2,
                "09:30-16:30": 4,
                "16:30-20:30": 2,
                "20:30-00:34": 5
            }
        }
    
    def _parse_time(self, time_str: str) -> time:
        """Parse une chaîne de temps au format HH:MM"""
        try:
            if ":" in time_str:
                hours, minutes = map(int, time_str.split(":"))
                # Gérer le cas où les heures dépassent 23 (ex: 24:00 = 00:00 le lendemain)
                if hours >= 24:
                    hours = hours - 24
                return time(hours, minutes)
            else:
                return time(int(time_str), 0)
        except ValueError:
            logger.error(f"Impossible de parser le temps: {time_str}")
            return time(0, 0)
    
    def _time_in_range(self, check_time: time, start_time: time, end_time: time) -> bool:
        """Vérifie si un temps est dans une plage horaire"""
        if start_time <= end_time:
            return start_time <= check_time <= end_time
        else:
            # Cas où la plage traverse minuit
            return check_time >= start_time or check_time <= end_time
    
    def get_frequency_for_time(self, line: str, target_time: time) -> Optional[int]:
        """
        Obtient la fréquence de passage pour une ligne à un moment donné
        
        Args:
            line: Numéro de ligne (str)
            target_time: Heure cible
            
        Returns:
            Fréquence en minutes, ou None si la ligne ne circule pas
        """
        if line not in self.frequencies:
            logger.warning(f"Ligne {line} non trouvée dans les fréquences")
            return None
        
        line_schedule = self.frequencies[line]
        
        for time_range, frequency in line_schedule.items():
            start_str, end_str = time_range.split("-")
            start_time = self._parse_time(start_str)
            end_time = self._parse_time(end_str)
            
            if self._time_in_range(target_time, start_time, end_time):
                return frequency
        
        # Si aucune plage ne correspond, la ligne ne circule pas
        return None
    
    def get_next_departure(self, line: str, current_time: datetime, from_station: str = None, to_station: str = None, graph = None) -> Optional[datetime]:
        """
        Calcule le prochain départ pour une ligne donnée en tenant compte de la direction
        
        Args:
            line: Numéro de ligne
            current_time: Heure actuelle
            from_station: Station de départ (pour déterminer la direction)
            to_station: Station d'arrivée (pour déterminer la direction)
            graph: Instance du graphe pour calculer les temps de trajet depuis le terminus
            
        Returns:
            Heure du prochain départ, ou None si la ligne ne circule pas
        """
        current_time_only = current_time.time()
        frequency = self.get_frequency_for_time(line, current_time_only)
        
        if frequency is None:
            # Ligne ne circule pas, trouver le prochain créneau
            return self._find_next_service_time(line, current_time)
        

        travel_time_from_terminus = 0
        if graph and from_station and line not in ["Correspondance", "Correspondance à pied", "transfer", "?"]:
            travel_time_from_terminus = self._calculate_travel_time_from_terminus(
                line, from_station, to_station, graph
            )
        

        line_schedule = self.frequencies[line]
        current_range_start = None
        
        for time_range, freq in line_schedule.items():
            start_str, end_str = time_range.split("-")
            start_time = self._parse_time(start_str)
            end_time = self._parse_time(end_str)
            
            if self._time_in_range(current_time_only, start_time, end_time):
                current_range_start = start_time
                break
        
        if current_range_start is None:
            return self._find_next_service_time(line, current_time)
        
        # Calculer les minutes écoulées depuis le début de la plage
        current_date = current_time.date()
        range_start_datetime = datetime.combine(current_date, current_range_start)
        
        # Ajuster si la plage commence le jour précédent
        if current_range_start > current_time_only:
            range_start_datetime -= timedelta(days=1)
        
        # Premier départ depuis le terminus
        first_departure_from_terminus = range_start_datetime
        
        # Calculer quand ce premier départ arrive à notre station
        first_arrival_at_station = first_departure_from_terminus + timedelta(minutes=travel_time_from_terminus)
        
        # Maintenant, calculer tous les départs suivants avec la fréquence
        departure_number = 0
        while True:
            # Départ numéro N depuis le terminus
            departure_from_terminus = first_departure_from_terminus + timedelta(minutes=departure_number * frequency)
            
            # Arrivée à notre station
            arrival_at_station = departure_from_terminus + timedelta(minutes=travel_time_from_terminus)
            
            # Si cette arrivée est après l'heure actuelle, c'est notre prochain métro
            if arrival_at_station > current_time:
                # Vérifier que ce départ est encore dans la plage horaire
                departure_time = departure_from_terminus.time()
                end_time = self._parse_time(time_range.split("-")[1])
                
                if self._time_in_range(departure_time, current_range_start, end_time):
                    return arrival_at_station
                else:
                    # Le départ est en dehors de la plage, chercher le prochain service
                    return self._find_next_service_time(line, current_time)
            
            departure_number += 1
            
            # Sécurité : éviter une boucle infinie
            if departure_number > 1000:
                logger.error(f"Trop d'itérations pour calculer le prochain départ de la ligne {line}")
                return self._find_next_service_time(line, current_time)
    
    def _calculate_travel_time_from_terminus(self, line: str, from_station: str, to_station: str, graph) -> float:
        """
        Calcule le temps de trajet depuis le terminus approprié jusqu'à la station de départ
        
        Args:
            line: Numéro de ligne
            from_station: Station de départ
            to_station: Station d'arrivée (pour déterminer la direction)
            graph: Instance du graphe
            
        Returns:
            Temps de trajet en minutes depuis le terminus
        """
        try:
            # Obtenir les terminus de la ligne
            terminus_stations = self._get_line_terminus(line, graph)
            
            if not terminus_stations or len(terminus_stations) < 2:
                # Pas de terminus trouvés, retourner un temps par défaut
                return 5.0  # 5 minutes par défaut
            
            # Déterminer la direction basée sur la destination
            # On choisit le terminus qui nous rapproche de notre destination
            best_terminus = None
            min_total_distance = float('inf')
            
            for terminus in terminus_stations:
                try:
                    # Calculer la distance depuis ce terminus vers notre station de départ
                    distance_to_start = self._calculate_distance_between_stations(terminus, from_station, graph)
                    
                    # Calculer la distance depuis notre station de départ vers la destination
                    distance_to_end = self._calculate_distance_between_stations(from_station, to_station, graph)
                    
                    # Calculer la distance totale depuis ce terminus vers la destination
                    total_distance = distance_to_start + distance_to_end
                    
                    if total_distance < min_total_distance:
                        min_total_distance = total_distance
                        best_terminus = terminus
                        
                except Exception as e:
                    logger.debug(f"Erreur lors du calcul de distance pour terminus {terminus}: {e}")
                    continue
            
            if best_terminus:
                # Calculer le temps de trajet depuis le meilleur terminus
                distance = self._calculate_distance_between_stations(best_terminus, from_station, graph)
                # Convertir la distance en temps (en supposant une vitesse moyenne)
                # La distance dans le graphe est généralement en "unités", on multiplie par 2 pour avoir des minutes
                travel_time = distance * 2
                return max(0, travel_time)  # Au minimum 0 minute
            
        except Exception as e:
            logger.warning(f"Erreur lors du calcul du temps depuis le terminus pour la ligne {line}: {e}")
        
        # Retour par défaut si calcul impossible
        return 5.0
    
    def _get_line_terminus(self, line: str, graph) -> List[str]:
        """
        Obtient les stations terminus d'une ligne
        
        Args:
            line: Numéro de ligne
            graph: Instance du graphe
            
        Returns:
            Liste des stations terminus
        """
        try:
            # Obtenir toutes les stations de la ligne
            line_stations = []
            
            # Parcourir tous les nœuds et arêtes pour trouver les stations de cette ligne
            for node in graph.nodes:
                neighbors = graph.get_neighbors(node)
                for neighbor in neighbors:
                    edge_line = graph.get_line_between_stations(node, neighbor)
                    if edge_line == line:
                        if node not in line_stations:
                            line_stations.append(node)
                        if neighbor not in line_stations:
                            line_stations.append(neighbor)
            
            if not line_stations:
                return []
            
            # Trouver les terminus (stations avec seulement un voisin sur cette ligne)
            terminus_stations = []
            
            for station in line_stations:
                neighbors_on_line = []
                neighbors = graph.get_neighbors(station)
                
                for neighbor in neighbors:
                    edge_line = graph.get_line_between_stations(station, neighbor)
                    if edge_line == line:
                        neighbors_on_line.append(neighbor)
                
                # Si la station n'a qu'un seul voisin sur cette ligne, c'est un terminus
                if len(neighbors_on_line) == 1:
                    terminus_stations.append(station)
            
            return terminus_stations
            
        except Exception as e:
            logger.warning(f"Erreur lors de la recherche des terminus pour la ligne {line}: {e}")
            return []
    
    def _calculate_distance_between_stations(self, station1: str, station2: str, graph) -> float:
        """
        Calcule la distance entre deux stations en utilisant l'algorithme de chemin le plus court
        
        Args:
            station1: Station de départ
            station2: Station d'arrivée  
            graph: Instance du graphe
            
        Returns:
            Distance entre les stations (en unités du graphe)
        """
        try:
            # Utiliser une version simplifiée de Dijkstra pour calculer la distance
            if station1 == station2:
                return 0.0
            
            if station1 not in graph.nodes or station2 not in graph.nodes:
                return float('inf')
            
            # Dijkstra simplifié
            distances = {node: float('inf') for node in graph.nodes}
            distances[station1] = 0.0
            visited = set()
            priority_queue = [(0.0, station1)]
            
            while priority_queue:
                current_distance, current_station = priority_queue.pop(0)
                
                if current_station in visited:
                    continue
                    
                visited.add(current_station)
                
                if current_station == station2:
                    return current_distance
                
                neighbors = graph.get_neighbors(current_station)
                for neighbor in neighbors:
                    if neighbor not in visited:
                        # Distance unitaire entre stations adjacentes
                        edge_distance = 1.0
                        new_distance = current_distance + edge_distance
                        
                        if new_distance < distances[neighbor]:
                            distances[neighbor] = new_distance
                            priority_queue.append((new_distance, neighbor))
                            priority_queue.sort()  # Maintenir l'ordre de priorité
            
            return distances.get(station2, float('inf'))
            
        except Exception as e:
            logger.warning(f"Erreur lors du calcul de distance entre {station1} et {station2}: {e}")
            return float('inf')
    
    def _find_next_service_time(self, line: str, current_time: datetime) -> Optional[datetime]:
        """Trouve le prochain horaire de service pour une ligne"""
        if line not in self.frequencies:
            return None
        
        line_schedule = self.frequencies[line]
        current_time_only = current_time.time()
        current_date = current_time.date()
        
        # Chercher la prochaine plage horaire
        next_services = []
        
        for time_range, frequency in line_schedule.items():
            start_str, end_str = time_range.split("-")
            start_time = self._parse_time(start_str)
            
            # Service aujourd'hui
            service_datetime = datetime.combine(current_date, start_time)
            if service_datetime > current_time:
                next_services.append(service_datetime)
            
            # Service demain
            tomorrow_service = datetime.combine(current_date + timedelta(days=1), start_time)
            next_services.append(tomorrow_service)
        
        if next_services:
            return min(next_services)
        
        return None
    
    def calculate_journey_time_with_schedule(self, route_info: Dict, departure_time: datetime, graph = None) -> Dict:
        """
        Calcule le temps de trajet total en tenant compte des horaires
        
        Args:
            route_info: Information sur l'itinéraire
            departure_time: Heure de départ souhaitée
            graph: Instance du graphe pour calculs avancés
            
        Returns:
            Dict avec les détails du trajet planifié
        """
        if not route_info or "path" not in route_info:
            return {"error": "Informations d'itinéraire manquantes"}
        
        # Grouper les segments par ligne continue
        grouped_segments = self._group_segments_by_line(route_info["path"])
        
        segments = []
        current_time = departure_time
        total_waiting_time = 0
        
        # Traiter chaque segment groupé
        for segment_group in grouped_segments:
            line = segment_group["line"]
            
            # Vérifier si c'est une vraie ligne de métro ou une correspondance
            if line in ["Correspondance", "Correspondance à pied", "transfer", "?", "Transfer"]:
                # Segment de correspondance - traiter comme une marche
                walk_time = segment_group["total_travel_time"]
                
                segments.append({
                    "type": "transfer",
                    "line": "Correspondance à pied",
                    "departure_time": current_time.strftime("%H:%M"),
                    "arrival_time": (current_time + timedelta(minutes=walk_time)).strftime("%H:%M"),
                    "waiting_time": 0,
                    "travel_time": walk_time,
                    "from_station": segment_group["from_station"],
                    "to_station": segment_group["to_station"],
                    "stops": segment_group["stops"]
                })
                
                current_time += timedelta(minutes=walk_time)
                continue
            
            # Calculer le prochain départ pour une vraie ligne de métro
            next_departure = self.get_next_departure(
                line, 
                current_time, 
                segment_group["from_station"], 
                segment_group["to_station"], 
                graph
            )
            
            if next_departure is None:
                # Ligne ne circule pas, retourner une erreur
                return {"error": f"La ligne {line} ne circule pas à l'heure demandée"}
            
            # Temps d'attente
            waiting_time = (next_departure - current_time).total_seconds() / 60
            total_waiting_time += waiting_time
            
            # Temps de trajet du segment groupé
            segment_travel_time = segment_group["total_travel_time"]
            
            # Mise à jour du temps
            segment_end_time = next_departure + timedelta(minutes=segment_travel_time)
            
            segments.append({
                "type": "metro",
                "line": line,
                "departure_time": next_departure.strftime("%H:%M"),
                "arrival_time": segment_end_time.strftime("%H:%M"),
                "waiting_time": round(waiting_time, 1),
                "travel_time": segment_travel_time,
                "from_station": segment_group["from_station"],
                "to_station": segment_group["to_station"],
                "stops": segment_group["stops"]
            })
            
            current_time = segment_end_time
        
        return {
            "departure_time": departure_time.strftime("%H:%M"),
            "arrival_time": current_time.strftime("%H:%M"),
            "total_travel_time": round((current_time - departure_time).total_seconds() / 60, 1),
            "total_waiting_time": round(total_waiting_time, 1),
            "segments": segments
        }
    
    def _group_segments_by_line(self, path_segments: List[Dict]) -> List[Dict]:
        """
        Groupe les segments consécutifs de la même ligne logique
        
        Args:
            path_segments: Liste des segments du trajet
            
        Returns:
            Liste des segments groupés par ligne
        """
        if not path_segments:
            return []

        def are_same_logical_line(line1, line2):
            """Vérifie si deux identifiants de ligne correspondent à la même ligne logique"""
            if line1 == line2:
                return True
            
            # Ignorer les différences mineures et se concentrer sur le numéro de ligne principal
            if line1 and line2:
                # Nettoyer les noms de ligne pour enlever les variations
                clean_line1 = line1.replace("bis", "B").replace("Bis", "B")
                clean_line2 = line2.replace("bis", "B").replace("Bis", "B")
                
                # Extraire le numéro principal (exemple: "3", "3B", "7", "7B")
                import re
                pattern = r'^(\d+[AB]?)'
                match1 = re.match(pattern, clean_line1)
                match2 = re.match(pattern, clean_line2)
                
                if match1 and match2:
                    return match1.group(1) == match2.group(1)
            
            return False

        grouped = []
        current_group = None
        
        for segment in path_segments:
            # Gérer la ligne - elle peut être dans route_info.short_name ou directement dans line
            line = segment.get("route_info", {}).get("short_name", "Unknown")
            if line == "Unknown":
                line = segment.get("line", "Unknown")
            
            # Nettoyer le nom de la ligne
            if line in ["?", "transfer", "Correspondance"]:
                line = "Correspondance"
            
            # Récupérer les noms de stations
            from_station = segment.get("from_station", "")
            to_station = segment.get("to_station", "")
            travel_time = segment.get("travel_time", 2)
            
            # Si c'est la même ligne logique que le groupe actuel, l'étendre
            if (current_group and 
                are_same_logical_line(current_group["line"], line) and 
                line != "Correspondance"):  # Ne pas grouper les correspondances
                
                # Étendre le groupe actuel
                current_group["to_station"] = to_station
                current_group["total_travel_time"] += travel_time
                current_group["stops"] += 1
                current_group["segments"].append(segment)
            else:
                # Finaliser le groupe précédent
                if current_group:
                    grouped.append(current_group)
                
                # Commencer un nouveau groupe
                current_group = {
                    "line": line,
                    "from_station": from_station,
                    "to_station": to_station,
                    "total_travel_time": travel_time,
                    "stops": 1,
                    "segments": [segment]
                }
        
        # Ajouter le dernier groupe
        if current_group:
            grouped.append(current_group)
        
        return grouped
    
    def is_line_running(self, line: str, check_time: time) -> bool:
        """Vérifie si une ligne circule à un moment donné"""
        return self.get_frequency_for_time(line, check_time) is not None
    
    def get_all_lines_status(self, check_time: time) -> Dict[str, bool]:
        """Retourne l'état de toutes les lignes à un moment donné"""
        status = {}
        for line in self.frequencies.keys():
            status[line] = self.is_line_running(line, check_time)
        return status
