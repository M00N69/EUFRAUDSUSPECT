import os
import re
import requests
from datetime import datetime
import PyPDF2
import pdfplumber
import pandas as pd
from bs4 import BeautifulSoup
import tempfile
import streamlit as st

def download_latest_report(save_dir="./data/pdf_reports"):
    """
    Télécharge le dernier rapport disponible sur le site de l'UE
    """
    # URL de la page contenant les liens vers les rapports
    base_url = "https://food.ec.europa.eu/food-safety/acn/ffn-monthly_en"
    
    try:
        # Créer le répertoire de sauvegarde s'il n'existe pas
        # Utiliser un chemin relatif et s'assurer que le répertoire data existe d'abord
        os.makedirs("./data", exist_ok=True)
        os.makedirs(save_dir, exist_ok=True)
    except Exception as e:
        # En cas d'erreur lors de la création du répertoire, utiliser un répertoire temporaire
        st.warning(f"Erreur lors de la création du répertoire de sauvegarde: {str(e)}")
        temp_dir = tempfile.mkdtemp()
        save_dir = temp_dir
        st.info(f"Utilisation du répertoire temporaire: {save_dir}")
    
    try:
        # Récupération de la page
        st.info("Récupération de la page des rapports...")
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
            st.error("Aucun lien de rapport PDF trouvé sur la page.")
            return None, "Aucun lien de rapport PDF trouvé sur la page."
        
        st.info(f"Liens PDF trouvés: {len(pdf_links)}")
        for i, link in enumerate(pdf_links[:5]):  # Afficher jusqu'à 5 liens
            st.write(f"Lien {i+1}: {link}")
        
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
        
        st.info(f"URL complète du PDF: {full_url}")
        
        # Extraire le nom du fichier de l'URL
        filename = os.path.basename(latest_pdf_link)
        local_path = os.path.join(save_dir, filename)
        
        st.info(f"Téléchargement du PDF vers: {local_path}")
        
        # Télécharger le fichier
        pdf_response = requests.get(full_url, stream=True)
        pdf_response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            for chunk in pdf_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        st.success(f"PDF téléchargé avec succès: {filename}")
        
        # Extraire la date du rapport (format: YYYY-MM)
        match = re.search(r'(\d{4})[-_]?(\d{2})', filename)
        if match:
            year, month = match.groups()
            report_date = f"{year}-{month}"
            st.info(f"Date extraite du nom de fichier: {report_date}")
        else:
            # Si on ne peut pas extraire la date du nom de fichier,
            # essayer de l'extraire du contenu du PDF
            st.info("Extraction de la date depuis le contenu du PDF...")
            report_date = extract_date_from_pdf(local_path)
            if not report_date:
                # Utiliser la date actuelle comme dernier recours
                now = datetime.now()
                report_date = f"{now.year}-{now.month:02d}"
                st.warning(f"Impossible d'extraire la date, utilisation de la date actuelle: {report_date}")
            else:
                st.info(f"Date extraite du contenu du PDF: {report_date}")
        
        return local_path, report_date
        
    except Exception as e:
        st.error(f"Erreur lors du téléchargement du rapport: {str(e)}")
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
    except Exception as e:
        st.error(f"Erreur lors de l'extraction de la date du PDF: {str(e)}")
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
        st.info(f"Ouverture du PDF: {pdf_path}")
        with pdfplumber.open(pdf_path) as pdf:
            st.info(f"PDF ouvert avec succès. {len(pdf.pages)} pages trouvées.")
            
            # Extraction du nombre total de suspicions (généralement sur la première ou deuxième page)
            for page_num in range(min(2, len(pdf.pages))):
                page = pdf.pages[page_num]
                text = page.extract_text()
                
                match = re.search(r'THIS MONTH (\d+) SUSPICIONS WERE RETRIEVED', text)
                if match:
                    extracted_data['total_suspicions'] = int(match.group(1))
                    st.info(f"Nombre total de suspicions trouvé: {extracted_data['total_suspicions']}")
                    break
            
            # Extraction des tableaux de données pour les différentes catégories de fraude
            suspicions = []
            
            st.info("Analyse des tableaux de données...")
            # Tables à partir de la page 3
            for page_num in range(2, len(pdf.pages)):
                page = pdf.pages[page_num]
                tables = page.extract_tables()
                
                st.info(f"Page {page_num+1}: {len(tables)} tableaux trouvés.")
                
                for table_idx, table in enumerate(tables):
                    if not table or len(table) <= 1:
                        continue
                    
                    # Vérifier si c'est un en-tête ou un tableau de données
                    header_row = table[0]
                    if not header_row:
                        continue
                    
                    # Afficher les en-têtes trouvés pour le débogage
                    headers_str = ', '.join([str(h) for h in header_row if h])
                    st.info(f"Tableau {table_idx+1}, en-têtes: {headers_str}")
                    
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
                    
                    st.info(f"Type de fraude détecté: {fraud_type}")
                    
                    # En-têtes attendus dans les tableaux
                    expected_headers = ["CLASSIFICATION", "PRODUCT CATEGORY", "COMMODITY", "ISSUE", "ORIGIN", "NOTIFIED BY"]
                    
                    # Vérifier si c'est bien un tableau de données pertinent
                    if any(header in ' '.join(str(h) for h in header_row if h) for header in expected_headers):
                        # Déterminer les indices des colonnes
                        header_indices = {}
                        for i, cell in enumerate(header_row):
                            if cell in expected_headers:
                                header_indices[cell] = i
                        
                        st.info(f"Colonnes trouvées: {', '.join(header_indices.keys())}")
                        
                        # S'il manque des colonnes clés, continuer
                        if len(header_indices) < 3:
                            st.warning(f"Pas assez de colonnes pertinentes ({len(header_indices)}), ce tableau est ignoré.")
                            continue
                        
                        rows_processed = 0
                        # Traiter chaque ligne (sauf l'en-tête)
                        for row in table[1:]:
                            # Ignorer les lignes vides
                            if not row or all(cell is None or cell.strip() == "" for cell in row if isinstance(cell, str)):
                                continue
                            
                            suspicion = {
                                'fraud_type': fraud_type,
                                'classification': row[header_indices.get('CLASSIFICATION', 0)] if 'CLASSIFICATION' in header_indices and len(row) > header_indices.get('CLASSIFICATION', 0) else "",
                                'product_category': row[header_indices.get('PRODUCT CATEGORY', 1)] if 'PRODUCT CATEGORY' in header_indices and len(row) > header_indices.get('PRODUCT CATEGORY', 1) else "",
                                'commodity': row[header_indices.get('COMMODITY', 2)] if 'COMMODITY' in header_indices and len(row) > header_indices.get('COMMODITY', 2) else "",
                                'issue': row[header_indices.get('ISSUE', 3)] if 'ISSUE' in header_indices and len(row) > header_indices.get('ISSUE', 3) else "",
                                'origin': row[header_indices.get('ORIGIN', 4)] if 'ORIGIN' in header_indices and len(row) > header_indices.get('ORIGIN', 4) else "",
                                'notified_by': row[header_indices.get('NOTIFIED BY', 5)] if 'NOTIFIED BY' in header_indices and len(row) > header_indices.get('NOTIFIED BY', 5) else ""
                            }
                            
                            # Nettoyage des données
                            for key, value in suspicion.items():
                                if value is None:
                                    suspicion[key] = ""
                                elif isinstance(value, str):
                                    suspicion[key] = value.strip()
                            
                            suspicions.append(suspicion)
                            rows_processed += 1
                        
                        st.info(f"{rows_processed} lignes traitées dans ce tableau.")
            
            extracted_data['suspicions'] = suspicions
            st.success(f"Extraction terminée. {len(suspicions)} suspicions extraites au total.")
            
    except Exception as e:
        st.error(f"Erreur lors de l'extraction des données du PDF: {str(e)}")
    
    return extracted_data

def check_for_new_report(data_manager):
    """
    Vérifie s'il y a un nouveau rapport disponible, le télécharge et l'ajoute à la base de données
    """
    st.write("Démarrage de la vérification des nouveaux rapports...")
    
    # Obtenir la date du dernier rapport dans la base de données
    latest_year, latest_month = data_manager.get_latest_report_date()
    st.write(f"Dernier rapport en base: {latest_year}-{latest_month if latest_month else ''}")
    
    # Télécharger le dernier rapport disponible
    try:
        st.write("Tentative de téléchargement du rapport...")
        pdf_path, report_date = download_latest_report()
        
        if not pdf_path:
            st.warning(f"Échec du téléchargement: {report_date}")
            return False
        
        st.write(f"Rapport téléchargé: {pdf_path}, date: {report_date}")
        
        # Extraire l'année et le mois du rapport téléchargé
        try:
            date_obj = datetime.strptime(report_date, "%Y-%m")
            year = date_obj.year
            month = date_obj.month
            st.write(f"Date extraite: {year}-{month}")
        except Exception as e:
            st.error(f"Erreur lors de l'analyse de la date: {str(e)}")
            return False
        
        # Vérifier si ce rapport est déjà dans la base de données
        if latest_year is not None and latest_month is not None:
            if year < latest_year or (year == latest_year and month <= latest_month):
                st.info(f"Ce rapport ({year}-{month}) est déjà dans la base ou plus ancien que {latest_year}-{latest_month}")
                return False
        
        # Extraire les données du PDF
        st.write("Extraction des données du PDF...")
        extracted_data = extract_data_from_pdf(pdf_path)
        st.write(f"Données extraites: {len(extracted_data.get('suspicions', []))} suspicions")
        
        # Ajouter les données à la base de données
        st.write("Ajout des données à la base...")
        success = data_manager.add_report_data(report_date, pdf_path, extracted_data)
        st.write(f"Ajout réussi: {success}")
        
        return success
    except Exception as e:
        st.error(f"Erreur lors de la vérification: {str(e)}")
        return False

def force_download_latest_report(data_manager):
    """Force le téléchargement du dernier rapport disponible, même s'il existe déjà"""
    try:
        st.write("Téléchargement forcé du rapport...")
        pdf_path, report_date = download_latest_report()
        
        if not pdf_path:
            st.warning(f"Échec du téléchargement: {report_date}")
            return False
        
        st.write(f"Rapport téléchargé: {pdf_path}, date: {report_date}")
        
        # Extraire les données du PDF
        st.write("Extraction des données du PDF...")
        extracted_data = extract_data_from_pdf(pdf_path)
        st.write(f"Données extraites: {len(extracted_data.get('suspicions', []))} suspicions")
        
        # Ajouter les données à la base de données
        st.write("Ajout des données à la base...")
        success = data_manager.add_report_data(report_date, pdf_path, extracted_data)
        st.write(f"Ajout réussi: {success}")
        
        return success
    except Exception as e:
        st.error(f"Erreur lors du téléchargement forcé: {str(e)}")
        return False
