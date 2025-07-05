"""
Fichier interne pour la gestion des logs et la normalisation des messages.
On a ainsi des messages de warning en jaune et des messages d'erreur en rouge.
"""

from colorama import init, Fore, Style
import re
import logging
import unicodedata

# Initialiser colorama pour qu'il fonctionne correctement sur tous les OS
init(autoreset=True)

def normalize_text(text):
    """Remplace les caractères accentués et spéciaux par leurs équivalents sans accent.
    Traite également les problèmes d'encodage courants."""
    if not isinstance(text, str):
        text = str(text)
        
    # Tentative de normalisation Unicode (suppression des accents)
    try:
        # Décompose les caractères accentués puis supprime les marques d'accentuation
        text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    except:
        pass
        
    # Table de correspondance pour les caractères problématiques ou spéciaux restants
    replacements = {
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'à': 'a', 'â': 'a', 'ä': 'a',
        'î': 'i', 'ï': 'i',
        'ô': 'o', 'ö': 'o',
        'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c',
        'œ': 'oe',
        'æ': 'ae',
        'ñ': 'n',
        '�': '_',  # Caractère de remplacement Unicode pour les caractères non reconnus
        'ø': 'o',
    }
    
    for accent, sans_accent in replacements.items():
        text = text.replace(accent, sans_accent)
        text = text.replace(accent.upper(), sans_accent.upper())
    
    # Suppression des caractères non imprimables
    text = ''.join(c for c in text if c.isprintable() or c in ['\n', '\t', '\r'])
    
    return text

def log_info(message):
    """Affiche un message d'information normal."""
    print(normalize_text(message))

def log_debug(message):
    """Affiche un message de debug en gris (uniquement si le niveau de debug est activé)."""
    # Pour l'instant, on désactive les messages de debug pour éviter le spam
    # Décommentez la ligne suivante pour activer les logs de debug
    # print(f"{Fore.LIGHTBLACK_EX}{normalize_text(message)}{Style.RESET_ALL}")
    pass

def log_warning(message):
    """Affiche un message d'avertissement en jaune."""
    print(f"{Fore.YELLOW}{normalize_text(message)}{Style.RESET_ALL}")

def log_error(message):
    """Affiche un message d'erreur en rouge."""
    print(f"{Fore.RED}{normalize_text(message)}{Style.RESET_ALL}")

# Classe pour intercepter et normaliser les logs du module logging standard
class NormalizedFormatter(logging.Formatter):
    """Formateur qui normalise les caractères spéciaux dans les logs."""
    
    def format(self, record):
        # Normaliser le message avant de le formater
        record.msg = normalize_text(record.msg)
        return super().format(record)

def setup_logger(name=None):
    """Configure un logger qui normalise automatiquement les messages.
    
    Args:
        name: Nom optionnel du logger à configurer. Si None, configure le logger racine.
    
    Returns:
        Le logger configuré
    """
    logger = logging.getLogger(name)
    
    # Ne pas ajouter de gestionnaires si déjà configuré
    if not logger.handlers:
        handler = logging.StreamHandler()
        
        # Formateur personnalisé qui normalise les caractères
        formatter = NormalizedFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
    
    return logger
