import pandas as pd
from datetime import datetime
import re
import requests
from io import BytesIO

def format_date(date_str):
    """
    Formate une date pour l'affichage
    """
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m")
        return date_obj.strftime("%B %Y")
    except:
        return date_str

def clean_text(text):
    """
    Nettoie un texte (supprime les caractères spéciaux, espaces multiples, etc.)
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Supprimer les caractères spéciaux
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Supprimer les espaces multiples
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def categorize_fraud_issue(issue):
    """
    Catégorise un problème de fraude en catégories plus générales
    """
    issue = issue.lower() if isinstance(issue, str) else ""
    
    if any(keyword in issue for keyword in ['pesticide', 'residue', 'mrl', 'chlorpyrifos', 'chemical']):
        return "Résidus chimiques"
    
    elif any(keyword in issue for keyword in ['additive', 'colorant', 'e 1', 'e 2', 'e 3', 'e 4', 'e 5']):
        return "Additifs non conformes"
    
    elif any(keyword in issue for keyword in ['origin', 'document', 'certificate', 'label', 'traceability']):
        return "Problèmes documentaires"
    
    elif any(keyword in issue for keyword in ['unauthorized', 'not authorized', 'illegal']):
        return "Substances non autorisées"
    
    elif any(keyword in issue for keyword in ['substitution', 'adulteration']):
        return "Adultération"
    
    else:
        return "Autres problèmes"

def get_country_code(country_name):
    """
    Obtient le code ISO 3166-1 alpha-3 d'un pays à partir de son nom
    """
    # Dictionnaire de correspondance pour les cas spéciaux
    special_cases = {
        'UK': 'GBR',
        'USA': 'USA',
        'Republic of Côte d\'Ivoire': 'CIV',
        'Bosnia and Herzegovina': 'BIH',
        'Russia': 'RUS',
        'Taiwan': 'TWN',
        'United Arab Emirates': 'ARE',
        'Türkiye': 'TUR',
        'South Korea': 'KOR',
        'Republic of Korea': 'KOR',
    }
    
    if country_name in special_cases:
        return special_cases[country_name]
    
    # Si le pays n'est pas dans les cas spéciaux, utiliser une API ou une bibliothèque pour la conversion
    # Ceci est une implémentation simplifiée
    return country_name[:3].upper()

def parse_month_year(text):
    """
    Extrait un mois et une année à partir d'un texte
    """
    months = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    # Chercher un motif: "Month YYYY" ou "MM-YYYY" ou "YYYY-MM"
    patterns = [
        r'(\w+)\s+(\d{4})',      # Month YYYY
        r'(\d{1,2})[/-](\d{4})',  # MM-YYYY
        r'(\d{4})[/-](\d{1,2})'   # YYYY-MM
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            if pattern == patterns[0]:  # Month YYYY
                month_str = groups[0].lower()
                if month_str in months:
                    month = months[month_str]
                    year = int(groups[1])
                    return year, month
            elif pattern == patterns[1]:  # MM-YYYY
                month = int(groups[0])
                year = int(groups[1])
                return year, month
            else:  # YYYY-MM
                year = int(groups[0])
                month = int(groups[1])
                return year, month
    
    return None, None

def download_image(url):
    """
    Télécharge une image à partir d'une URL
    """
    try:
        response = requests.get(url)
        return BytesIO(response.content)
    except:
        return None
