import os
import re
import requests
from datetime import datetime
import PyPDF2
import pdfplumber
import pandas as pd
from bs4 import BeautifulSoup
import tempfile

def download_latest_report(save_dir="data/pdf_reports"):
    """
    Télécharge le dernier rapport disponible sur le site de l'UE
    """
    # URL de la page contenant les liens vers les rapports
    base_url = "https://food.ec.europa.eu/food-safety/acn/ffn-monthly_en"
    
    # Créer le répertoire de sauvegarde s'il n'existe pas
    os.makedirs(save_dir, exist_ok=True)
    
    try:
        # Récupération de la page
        response = requests.get(base_url)
        response.raise_for_status()
        
        # Analyse du HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Recherche des liens vers les PDF
        pdf_links = []
        
        # Pattern pour trouver les liens de PDF de rapport mensuel
        pattern = re.compile(r'report.*\d{4}.*\.pdf', re.IGNORECASE)
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if pattern.search(href) and href.endswith('.pdf'):
                pdf_links.append(href)
        
        if not pdf_links:
            return None, "Aucun lien de rapport PDF trouvé sur la page."
        
        # Tri des liens par date (si possible d'extraire la date du nom de fichier)
        latest_pdf_link = pdf_links[0]  # Par défaut, premier lien trouvé
        
        # Téléchargement du PDF
        if latest_pdf_link.startswith('http'):
            full_url = latest_pdf_link
        else:
            # Relativiser l'URL si nécessaire
            if latest_pdf_link.startswith('/'):
                domain = re.match(r'(https?://[^/]+)', base_url).group(1)
                full_url = domain + latest_pdf_link
            else:
                full_url = base_url.rstrip('/') + '/' + latest_pdf_link
        
        # Extraire le nom du fichier de l'URL
        filename = os.path.basename(latest_pdf_link)
        local_path = os.path.join(save_dir, filename)
        
        # Télécharger le fichier
        pdf_response = requests.get(full_url, stream=True)
        pdf_response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            for chunk in pdf_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Extraire la date du rapport (format: YYYY-MM)
        match = re.search(r'(\d{4})[-_]?(\d{2})', filename)
        if match:
            year, month = match.groups()
            report_date = f"{year}-{month}"
        else:
            # Si on ne peut pas extraire la date du nom de fichier,
            # essayer de l'extraire du contenu du PDF
            report_date = extract_date_from_pdf(local_path)
            if not report_date:
                # Utiliser la date actuelle comme dernier recours
                now = datetime.now()
                report_date = f"{now.year}-{now.month:02d}"
        
        return local_path, report_date
        
    except Exception as e:
        return None, f"Erreur lors du téléchargement du rapport: {str(e)}"

def extract_date_from_pdf(pdf_path):
    """
    Tente d'extraire la date du rapport depuis le contenu du PDF
    """
    try:
        with open(pdf_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text = pdf_reader.pages[0].extract_text()
            
            # Chercher un motif de date (mois année)
            months = ['January', 'February', 'March', 'April', 'May', 'June', 
                     'July', 'August', 'September', 'October', 'November', 'December']
            
            for month in months:
                pattern = f"{month}\s+(\d{{4}})"
                match = re.search(pattern, text)
                if match:
                    year = match.group(1)
                    month_num = months.index(month) + 1
                    return f"{year}-{month_num:02d}"
            
            return None
    except:
        return None

def extract_data_from_pdf(pdf_path):
    """
    Extrait les données structurées du rapport PDF
    """
    extracted_data = {
        'total_suspicions': 0,
        'suspicions': []
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Extraction du nombre total de suspicions (généralement sur la première ou deuxième page)
            for page_num in range(min(2, len(pdf.pages))):
                page = pdf.pages[page_num]
                text = page.extract_text()
                
                match = re.search(r'THIS MONTH (\d+) SUSPICIONS WERE RETRIEVED', text)
                if match:
                    extracted_data['total_suspicions'] = int(match.group(1))
                    break
            
            # Extraction des tableaux de données pour les différentes catégories de fraude
            suspicions = []
            
            # Tables à partir de la page 3
            for page_num in range(2, len(pdf.pages)):
                page = pdf.pages[page_num]
                tables = page.extract_tables()
                
                for table in tables:
                    if not table or len(table) <= 1:
                        continue
                    
                    # Vérifier si c'est un en-tête ou un tableau de données
                    header_row = table[0]
                    if not header_row:
                        continue
                    
                    # Identifier le type de fraude (classification) à partir du texte de la page
                    text = page.extract_text()
                    classification = ""
                    
                    # Recherche des titres de section principaux
                    if "PRODUCT TAMPERING" in text:
                        fraud_type = "Product tampering"
                    elif "RECORD TAMPERING" in text:
                        fraud_type = "Record tampering"
                    elif "OTHER NON-COMPLIANCES" in text:
                        fraud_type = "Other non-compliances"
                    else:
                        fraud_type = "Unknown"
                    
                    # En-têtes attendus dans les tableaux
                    expected_headers = ["CLASSIFICATION", "PRODUCT CATEGORY", "COMMODITY", "ISSUE", "ORIGIN", "NOTIFIED BY"]
                    
                    # Vérifier si c'est bien un tableau de données pertinent
                    if any(header in ' '.join(str(h) for h in header_row if h) for header in expected_headers):
                        # Déterminer les indices des colonnes
                        header_indices = {}
                        for i, cell in enumerate(header_row):
                            if cell in expected_headers:
                                header_indices[cell] = i
                        
                        # S'il manque des colonnes clés, continuer
                        if len(header_indices) < 3:
                            continue
                        
                        # Traiter chaque ligne (sauf l'en-tête)
                        for row in table[1:]:
                            # Ignorer les lignes vides
                            if not row or all(cell is None or cell.strip() == "" for cell in row):
                                continue
                            
                            suspicion = {
                                'fraud_type': fraud_type,
                                'classification': row[header_indices.get('CLASSIFICATION', 0)] if 'CLASSIFICATION' in header_indices else "",
                                'product_category': row[header_indices.get('PRODUCT CATEGORY', 1)] if 'PRODUCT CATEGORY' in header_indices else "",
                                'commodity': row[header_indices.get('COMMODITY', 2)] if 'COMMODITY' in header_indices else "",
                                'issue': row[header_indices.get('ISSUE', 3)] if 'ISSUE' in header_indices else "",
                                'origin': row[header_indices.get('ORIGIN', 4)] if 'ORIGIN' in header_indices else "",
                                'notified_by': row[header_indices.get('NOTIFIED BY', 5)] if 'NOTIFIED BY' in header_indices else ""
                            }
                            
                            # Nettoyage des données
                            for key, value in suspicion.items():
                                if value is None:
                                    suspicion[key] = ""
                                elif isinstance(value, str):
                                    suspicion[key] = value.strip()
                            
                            suspicions.append(suspicion)
            
            extracted_data['suspicions'] = suspicions
            
    except Exception as e:
        print(f"Erreur lors de l'extraction des données du PDF: {str(e)}")
    
    return extracted_data

def check_for_new_report(data_manager):
    """
    Vérifie s'il y a un nouveau rapport disponible, le télécharge et l'ajoute à la base de données
    """
    # Obtenir la date du dernier rapport dans la base de données
    latest_year, latest_month = data_manager.get_latest_report_date()
    
    # Télécharger le dernier rapport disponible
    pdf_path, report_date = download_latest_report()
    
    if not pdf_path:
        return False
    
    # Extraire l'année et le mois du rapport téléchargé
    try:
        date_obj = datetime.strptime(report_date, "%Y-%m")
        year = date_obj.year
        month = date_obj.month
    except:
        return False
    
    # Vérifier si ce rapport est déjà dans la base de données
    if latest_year is not None and latest_month is not None:
        if year < latest_year or (year == latest_year and month <= latest_month):
            # Ce rapport est déjà dans la base de données ou plus ancien
            return False
    
    # Extraire les données du PDF
    extracted_data = extract_data_from_pdf(pdf_path)
    
    # Ajouter les données à la base de données
    success = data_manager.add_report_data(report_date, pdf_path, extracted_data)
    
    return success
