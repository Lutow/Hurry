"""
Module de recherche floue pour les stations de métro parisien.
Contient des fonctions pour rechercher des stations par nom avec tolérance aux erreurs de frappe,
suggestions d'alternatives et création de messages d'erreur conviviaux.
"""

import re
import unicodedata
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """
    Normalise un texte en supprimant les accents, caractères spéciaux et en convertissant en minuscules.
    
    Args:
        text: Texte à normaliser
        
    Returns:
        Texte normalisé
    """
    if not text:
        return ""
    
    # Supprimer les accents
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Convertir en minuscules
    text = text.lower()
    
    # Remplacer les caractères spéciaux par des espaces
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Normaliser les espaces multiples
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def calculate_similarity_score(query: str, station_name: str) -> float:
    """
    Calcule un score de similarité entre une requête et un nom de station.
    Combine plusieurs métriques pour une meilleure précision.
    Version améliorée pour éviter les confusions entre noms similaires.
    
    Args:
        query: Requête de recherche normalisée
        station_name: Nom de la station normalisé
        
    Returns:
        Score de similarité entre 0.0 et 1.0
    """
    if not query or not station_name:
        return 0.0
    
    # Correspondance exacte = score parfait
    if query == station_name:
        return 1.0
    
    # Score de base avec SequenceMatcher
    base_score = SequenceMatcher(None, query, station_name).ratio()
    
    # GROS BONUS pour correspondance exacte (insensible à la casse)
    if query.lower() == station_name.lower():
        return 0.99  # Quasi-parfait pour éviter les égalités
    
    # GROS BONUS pour correspondance au début (mais seulement si significatif)
    if station_name.startswith(query) and len(query) >= 3:
        base_score += 0.4
    elif query in station_name:
        # Bonus moindre si la requête est juste contenue quelque part
        base_score += 0.1
    
    # Analyse des mots
    query_words = set(query.split())
    station_words = set(station_name.split())
    
    if query_words and station_words:
        # Correspondance exacte de mots
        exact_word_matches = len(query_words.intersection(station_words))
        total_query_words = len(query_words)
        
        # Si TOUS les mots de la requête sont dans la station, gros bonus
        if exact_word_matches == total_query_words and total_query_words > 1:
            base_score += 0.5
        elif exact_word_matches > 0:
            word_ratio = exact_word_matches / total_query_words
            base_score += word_ratio * 0.3
    
    # PÉNALITÉ pour les noms très différents en longueur
    length_diff = abs(len(query) - len(station_name))
    if length_diff > len(query):  # Si la station est beaucoup plus longue
        base_score *= 0.8
    
    # PÉNALITÉ supplémentaire pour éviter les confusions du type "porte de X" vs "porte de Y"
    if "porte de" in query and "porte de" in station_name:
        # Vérifier si les mots après "porte de" sont différents
        query_after_porte = query.replace("porte de ", "").strip()
        station_after_porte = station_name.replace("porte de ", "").strip()
        
        if query_after_porte != station_after_porte:
            # Si les fins sont très différentes, pénaliser fortement
            after_similarity = SequenceMatcher(None, query_after_porte, station_after_porte).ratio()
            if after_similarity < 0.6:  # Seuil strict
                base_score *= 0.3  # Grosse pénalité
    
    return min(base_score, 1.0)


def find_best_station_matches(stations: Dict[str, Dict], name_query: str, 
                            max_results: int = 5, min_score: float = 0.6) -> List[Tuple[str, float]]:
    """
    Trouve les meilleures correspondances de stations pour une requête donnée.
    Version améliorée avec seuil plus strict pour éviter les confusions.
    
    Args:
        stations: Dictionnaire des stations {station_id: {name, lat, lon, ...}}
        name_query: Nom de la station recherchée
        max_results: Nombre maximum de résultats à retourner
        min_score: Score minimum pour qu'une station soit considérée comme correspondante (augmenté à 0.6)
        
    Returns:
        Liste de tuples (station_id, score) triée par score décroissant
    """
    if not name_query or not stations:
        return []
    
    # Normaliser la requête
    normalized_query = normalize_text(name_query)
    
    matches = []
    
    # D'abord, chercher une correspondance exacte
    exact_matches = []
    for station_id, station_data in stations.items():
        station_name = station_data.get('name', '')
        if not station_name:
            continue
        
        # Normaliser le nom de la station
        normalized_station_name = normalize_text(station_name)
        
        # Vérifier correspondance exacte (priorité absolue)
        if normalized_query == normalized_station_name:
            exact_matches.append((station_id, 1.0))
        elif normalized_query.lower() == normalized_station_name.lower():
            exact_matches.append((station_id, 0.99))
    
    # Si on a des correspondances exactes, les retourner en priorité
    if exact_matches:
        logger.info(f"Correspondance exacte trouvée pour '{name_query}'")
        return exact_matches[:max_results]
    
    # Sinon, recherche floue avec seuil plus strict
    for station_id, station_data in stations.items():
        station_name = station_data.get('name', '')
        if not station_name:
            continue
        
        # Normaliser le nom de la station
        normalized_station_name = normalize_text(station_name)
        
        # Calculer le score de similarité
        score = calculate_similarity_score(normalized_query, normalized_station_name)
        
        # Ajouter seulement si le score dépasse le minimum (maintenant 0.6)
        if score >= min_score:
            matches.append((station_id, score))
    
    # Trier par score décroissant et limiter les résultats
    matches.sort(key=lambda x: x[1], reverse=True)
    
    logger.info(f"Recherche floue '{name_query}': {len(matches)} correspondances trouvées (seuil: {min_score})")
    if matches:
        best_match = matches[0]
        best_station_name = stations[best_match[0]].get('name', 'Unknown')
        logger.info(f"Meilleure correspondance: '{best_station_name}' (score: {best_match[1]:.2f})")
    
    return matches[:max_results]


def suggest_station_alternatives(stations: Dict[str, Dict], query: str, 
                               max_suggestions: int = 3) -> List[str]:
    """
    Suggère des alternatives de stations pour une requête qui n'a pas de correspondance exacte.
    
    Args:
        stations: Dictionnaire des stations
        query: Requête de recherche
        max_suggestions: Nombre maximum de suggestions
        
    Returns:
        Liste des noms de stations suggérées
    """
    if not query or not stations:
        return []
    
    # Utiliser find_best_station_matches avec un score minimum plus bas
    matches = find_best_station_matches(stations, query, 
                                      max_results=max_suggestions * 2, 
                                      min_score=0.1)
    
    suggestions = []
    for station_id, score in matches[:max_suggestions]:
        station_name = stations[station_id].get('name', '')
        if station_name and station_name not in suggestions:
            suggestions.append(station_name)
    
    return suggestions


def create_user_friendly_error_message(original_query: str, suggestions: List[str]) -> str:
    """
    Crée un message d'erreur convivial avec des suggestions.
    
    Args:
        original_query: Requête originale de l'utilisateur
        suggestions: Liste des suggestions de stations
        
    Returns:
        Message d'erreur formaté
    """
    if not suggestions:
        return f"Aucune station trouvée pour '{original_query}'. Vérifiez l'orthographe."
    
    if len(suggestions) == 1:
        return f"Station '{original_query}' introuvable. Vouliez-vous dire '{suggestions[0]}' ?"
    
    suggestions_text = "', '".join(suggestions[:-1]) + f"' ou '{suggestions[-1]}'"
    return f"Station '{original_query}' introuvable. Vouliez-vous dire '{suggestions_text}' ?"


def find_station_by_partial_name(stations: Dict[str, Dict], partial_name: str) -> List[str]:
    """
    Trouve les stations dont le nom contient une partie du nom recherché.
    Utile pour les recherches par autocomplétion.
    
    Args:
        stations: Dictionnaire des stations
        partial_name: Partie du nom à rechercher
        
    Returns:
        Liste des IDs de stations correspondantes
    """
    if not partial_name or not stations:
        return []
    
    normalized_partial = normalize_text(partial_name)
    matches = []
    
    for station_id, station_data in stations.items():
        station_name = station_data.get('name', '')
        normalized_station_name = normalize_text(station_name)
        
        if normalized_partial in normalized_station_name:
            matches.append(station_id)
    
    return matches


def get_station_name_variants(station_name: str) -> List[str]:
    """
    Génère des variantes d'un nom de station pour améliorer la recherche.
    
    Args:
        station_name: Nom de la station
        
    Returns:
        Liste des variantes du nom
    """
    if not station_name:
        return []
    
    variants = [station_name]
    
    # Version normalisée
    normalized = normalize_text(station_name)
    if normalized not in variants:
        variants.append(normalized)
    
    # Version sans articles (la, le, les, du, de, des, etc.)
    words = station_name.split()
    articles = {'la', 'le', 'les', 'du', 'de', 'des', 'l', 'd'}
    filtered_words = [word for word in words if word.lower() not in articles]
    if len(filtered_words) < len(words):
        variant_without_articles = ' '.join(filtered_words)
        if variant_without_articles not in variants:
            variants.append(variant_without_articles)
    
    # Version avec abréviations courantes
    abbreviations = {
        'saint': 'st',
        'sainte': 'ste',
        'avenue': 'av',
        'boulevard': 'bd',
        'place': 'pl',
        'gare': 'g'
    }
    
    for full, abbrev in abbreviations.items():
        if full in station_name.lower():
            abbreviated = station_name.lower().replace(full, abbrev)
            if abbreviated not in [v.lower() for v in variants]:
                variants.append(abbreviated.title())
    
    return variants


def advanced_station_search(stations: Dict[str, Dict], query: str, 
                          search_type: str = "fuzzy") -> List[Tuple[str, float, str]]:
    """
    Recherche avancée de stations avec différents types de recherche.
    
    Args:
        stations: Dictionnaire des stations
        query: Requête de recherche
        search_type: Type de recherche ("fuzzy", "exact", "partial", "phonetic")
        
    Returns:
        Liste de tuples (station_id, score, search_method)
    """
    if not query or not stations:
        return []
    
    results = []
    
    if search_type in ["fuzzy", "all"]:
        # Recherche floue standard
        fuzzy_matches = find_best_station_matches(stations, query, max_results=10, min_score=0.2)
        for station_id, score in fuzzy_matches:
            results.append((station_id, score, "fuzzy"))
    
    if search_type in ["exact", "all"]:
        # Recherche exacte (avec normalisation)
        normalized_query = normalize_text(query)
        for station_id, station_data in stations.items():
            normalized_name = normalize_text(station_data.get('name', ''))
            if normalized_query == normalized_name:
                results.append((station_id, 1.0, "exact"))
    
    if search_type in ["partial", "all"]:
        # Recherche partielle
        partial_matches = find_station_by_partial_name(stations, query)
        for station_id in partial_matches:
            # Calculer un score basé sur la longueur de la correspondance
            station_name = normalize_text(stations[station_id].get('name', ''))
            query_norm = normalize_text(query)
            score = len(query_norm) / len(station_name) if station_name else 0
            results.append((station_id, score, "partial"))
    
    # Supprimer les doublons en gardant le meilleur score
    unique_results = {}
    for station_id, score, method in results:
        if station_id not in unique_results or score > unique_results[station_id][1]:
            unique_results[station_id] = (station_id, score, method)
    
    # Convertir en liste et trier par score
    final_results = list(unique_results.values())
    final_results.sort(key=lambda x: x[1], reverse=True)
    
    return final_results


# Fonction utilitaire pour tester le module
def test_fuzzy_search():
    """Fonction de test pour vérifier le bon fonctionnement du module."""
    # Données de test
    test_stations = {
        "1": {"name": "Châtelet-Les Halles"},
        "2": {"name": "République"},
        "3": {"name": "Gare du Nord"},
        "4": {"name": "Place de la Bastille"},
        "5": {"name": "Saint-Germain-des-Prés"},
    }
    
    # Tests
    print("=== Tests du module fuzzy_search ===")
    
    # Test 1: Recherche exacte
    matches = find_best_station_matches(test_stations, "République")
    print(f"Recherche 'République': {matches}")
    
    # Test 2: Recherche avec faute de frappe
    matches = find_best_station_matches(test_stations, "Republique")
    print(f"Recherche 'Republique': {matches}")
    
    # Test 3: Recherche partielle
    matches = find_best_station_matches(test_stations, "Chatelet")
    print(f"Recherche 'Chatelet': {matches}")
    
    # Test 4: Suggestions
    suggestions = suggest_station_alternatives(test_stations, "Bastile")
    print(f"Suggestions pour 'Bastile': {suggestions}")
    
    # Test 5: Message d'erreur
    error_msg = create_user_friendly_error_message("Bastile", suggestions)
    print(f"Message d'erreur: {error_msg}")


if __name__ == "__main__":
    test_fuzzy_search()
