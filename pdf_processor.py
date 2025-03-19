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
import traceback

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
        
        # Extraire la date du rapport à partir du nom du fichier
        # Rechercher un motif comme "ff_ffn_monthly-report_202502.pdf" pour extraire "2025-02"
        match = re.search(r'report[_-](\d{4})(\d{2})\.pdf', filename, re.IGNORECASE)
        if match:
            year, month = match.groups()
            report_date = f"{year}-{month}"
            st.info(f"Date extraite du nom de fichier: {report_date}")
        else:
            # Essayer un autre motif pour les noms de fichier différents
            match = re.search(r'(\d{4})[_-](\d{2})\.pdf', filename, re.IGNORECASE)
            if match:
                year, month = match.groups()
                report_date = f"{year}-{month}"
                st.info(f"Date extraite du nom de fichier (motif alternatif): {report_date}")
            else:
                # Si on ne peut pas extraire la date du nom de fichier,
                # essayer de l'extraire du contenu du PDF
                st.info("Extraction de la date depuis le contenu du PDF...")
                report_date = extract_date_from_pdf(local_path)
                if not report_date:
                    # Si tout échoue, extraire manuellement du nom du lien
                    # Tenter de trouver la date à partir de l'URL
                    st.warning("Impossible d'extraire la date du PDF, tentative avec l'URL...")
                    url_date_match = re.search(r'(\d{4})(\d{2})\.pdf', full_url)
                    if url_date_match:
                        year, month = url_date_match.groups()
                        report_date = f"{year}-{month}"
                        st.info(f"Date extraite de l'URL: {report_date}")
                    else:
                        # Dernier recours: utiliser la date actuelle
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
    Extrait les données structurées du rapport PDF avec une gestion améliorée des cellules fusionnées
    """
    extracted_data = {
        'total_suspicions': 0,
        'suspicions': []
    }
    
    try:
        st.info(f"Ouverture du PDF: {pdf_path}")
        with pdfplumber.open(pdf_path) as pdf:
            st.info(f"PDF ouvert avec succès. {len(pdf.pages)} pages trouvées.")
            
            # Extraction du nombre total de suspicions
            for page_num in range(min(3, len(pdf.pages))):
                page = pdf.pages[page_num]
                text = page.extract_text()
                
                match = re.search(r'THIS MONTH (\d+) SUSPICIONS WERE RETRIEVED', text)
                if match:
                    extracted_data['total_suspicions'] = int(match.group(1))
                    st.info(f"Nombre total de suspicions trouvé: {extracted_data['total_suspicions']}")
                    break
            
            # Variables pour suivre l'état entre les pages et les tableaux
            current_fraud_type = None
            current_classification = None
            last_values = {}  # Pour stocker les dernières valeurs non vides par colonne
            suspicions = []
            
            # Traiter chaque page à partir de la page 3 (index 2)
            for page_num in range(2, len(pdf.pages)):
                page = pdf.pages[page_num]
                text = page.extract_text()
                
                # Déterminer le type de fraude pour cette page
                # Rechercher des titres de section numérotés
                fraud_section_patterns = [
                    (r"1\.?\s*PRODUCT\s+TAMPERING", "Product tampering"),
                    (r"2\.?\s*RECORD\s+TAMPERING", "Record tampering"),
                    (r"3\.?\s*OTHER\s+NON-COMPLIANCES", "Other non-compliances")
                ]
                
                for pattern, fraud_type in fraud_section_patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        current_fraud_type = fraud_type
                        st.info(f"Type de fraude détecté: {current_fraud_type}")
                        # Réinitialiser les valeurs précédentes lors du changement de section
                        last_values = {}
                        current_classification = None
                        break
                
                # Si aucun pattern n'a matché, essayer une méthode alternative
                if current_fraud_type is None:
                    if "PRODUCT TAMPERING" in text:
                        current_fraud_type = "Product tampering"
                    elif "RECORD TAMPERING" in text:
                        current_fraud_type = "Record tampering"
                    elif "OTHER NON-COMPLIANCES" in text:
                        current_fraud_type = "Other non-compliances"
                
                # Extraire les tableaux
                tables = page.extract_tables()
                st.info(f"Page {page_num+1}: {len(tables)} tableaux trouvés.")
                
                for table_idx, table in enumerate(tables):
                    if not table or len(table) <= 1:
                        continue
                    
                    # Vérifier si c'est un tableau de données pertinent
                    header_row = table[0]
                    if not header_row:
                        continue
                    
                    # Afficher les en-têtes trouvés pour le débogage
                    headers_str = ', '.join([str(h) for h in header_row if h])
                    st.info(f"Tableau {table_idx+1}, en-têtes: {headers_str}")
                    
                    # En-têtes attendus dans les tableaux
                    expected_headers = ["CLASSIFICATION", "PRODUCT CATEGORY", "COMMODITY", "ISSUE", "ORIGIN", "NOTIFIED BY"]
                    
                    # Déterminer les indices des colonnes avec correspondance partielle
                    header_indices = {}
                    for i, cell in enumerate(header_row):
                        if not cell:
                            continue
                        cell_str = str(cell).strip().upper()
                        for expected in expected_headers:
                            if expected in cell_str or cell_str in expected:
                                header_indices[expected] = i
                                break
                    
                    # Afficher les colonnes trouvées
                    st.info(f"Colonnes identifiées: {', '.join(header_indices.keys())}")
                    
                    # S'il manque des colonnes clés, passer au tableau suivant
                    if len(header_indices) < 3:
                        st.warning(f"Pas assez de colonnes pertinentes ({len(header_indices)}), ce tableau est ignoré.")
                        continue
                    
                    # Traiter chaque ligne (sauf l'en-tête)
                    rows_processed = 0
                    for row in table[1:]:
                        # Ignorer les lignes vides
                        if not row or all(not cell or (isinstance(cell, str) and cell.strip() == "") for cell in row):
                            continue
                        
                        # Mettre à jour les dernières valeurs non vides
                        for i, cell in enumerate(row):
                            if cell and isinstance(cell, str) and cell.strip():
                                last_values[i] = cell.strip()
                        
                        # Récupérer la classification de cette ligne ou utiliser la dernière valeur
                        if 'CLASSIFICATION' in header_indices:
                            idx = header_indices['CLASSIFICATION']
                            if idx < len(row) and row[idx] and isinstance(row[idx], str) and row[idx].strip():
                                current_classification = row[idx].strip()
                            else:
                                # Utiliser la dernière valeur connue pour cette colonne
                                row_classification = last_values.get(idx, "")
                                if row_classification:
                                    current_classification = row_classification
                        
                        # Créer un dictionnaire avec les données de la ligne
                        suspicion = {
                            'fraud_type': current_fraud_type or "",
                            'classification': current_classification or "",
                            'product_category': "",
                            'commodity': "",
                            'issue': "",
                            'origin': "",
                            'notified_by': ""
                        }
                        
                        # Remplir les autres champs en utilisant les valeurs existantes ou dernières connues
                        for field, header in [
                            ('product_category', 'PRODUCT CATEGORY'),
                            ('commodity', 'COMMODITY'),
                            ('issue', 'ISSUE'),
                            ('origin', 'ORIGIN'),
                            ('notified_by', 'NOTIFIED BY')
                        ]:
                            if header in header_indices:
                                idx = header_indices[header]
                                if idx < len(row) and row[idx] and isinstance(row[idx], str) and row[idx].strip():
                                    suspicion[field] = row[idx].strip()
                                else:
                                    # Utiliser la dernière valeur connue pour cette colonne si nécessaire
                                    # Sauf pour commodity, issue, origin et notified_by où chaque ligne doit avoir sa propre valeur
                                    if field in ['product_category', 'classification']:
                                        suspicion[field] = last_values.get(idx, "")
                        
                        # Ne pas ajouter les lignes où les champs essentiels sont vides
                        essential_fields = ['product_category', 'commodity', 'issue']
                        if all(suspicion[field] == "" for field in essential_fields):
                            continue
                        
                        suspicions.append(suspicion)
                        rows_processed += 1
                    
                    st.info(f"{rows_processed} lignes traitées dans ce tableau.")
            
            # Vérification de cohérence: le nombre total de suspicions doit correspondre
            if extracted_data['total_suspicions'] > 0 and len(suspicions) > 0:
                st.info(f"Vérification de cohérence: {len(suspicions)} suspicions extraites vs {extracted_data['total_suspicions']} annoncées")
                
                # Si le nombre est très différent, afficher un avertissement
                if abs(len(suspicions) - extracted_data['total_suspicions']) > extracted_data['total_suspicions'] * 0.2:
                    st.warning(f"Écart important entre le nombre de suspicions extraites et le nombre annoncé")
            
            extracted_data['suspicions'] = suspicions
            st.success(f"Extraction terminée. {len(suspicions)} suspicions extraites au total.")
            
    except Exception as e:
        st.error(f"Erreur lors de l'extraction des données du PDF: {str(e)}")
        st.error(traceback.format_exc())
    
    return extracted_data

def post_process_extracted_data(extracted_data):
    """
    Nettoie et normalise les données extraites
    """
    if not extracted_data or 'suspicions' not in extracted_data:
        return extracted_data
    
    suspicions = extracted_data['suspicions']
    processed_suspicions = []
    
    for susp in suspicions:
        # Nettoyer les chaînes de caractères
        for key, value in susp.items():
            if isinstance(value, str):
                # Supprimer les astérisques souvent utilisés comme références
                cleaned_value = re.sub(r'\*+$', '', value.strip())
                # Supprimer les espaces multiples
                cleaned_value = re.sub(r'\s+', ' ', cleaned_value)
                susp[key] = cleaned_value
        
        # Vérifier que l'entrée a un minimum de données valides
        has_product = bool(susp.get('product_category', '').strip())
        has_issue = bool(susp.get('issue', '').strip())
        
        if has_product and has_issue:
            processed_suspicions.append(susp)
    
    extracted_data['suspicions'] = processed_suspicions
    return extracted_data

def try_extract_with_camelot(pdf_path):
    """
    Tente d'extraire les données avec Camelot si disponible
    """
    try:
        import camelot
        st.info("Tentative d'extraction avec Camelot...")
        
        # Extraction avec Camelot en mode "lattice" (tableaux avec bordures)
        tables = camelot.read_pdf(pdf_path, pages='3-end', flavor='lattice')
        st.info(f"{len(tables)} tableaux trouvés avec Camelot (mode lattice)")
        
        if len(tables) == 0:
            # Si aucun tableau n'est trouvé en mode lattice, essayer en mode stream
            tables = camelot.read_pdf(pdf_path, pages='3-end', flavor='stream')
            st.info(f"{len(tables)} tableaux trouvés avec Camelot (mode stream)")
        
        # Traitement des tableaux Camelot
        # Ce code est à compléter selon vos besoins spécifiques
        return True
        
    except ImportError:
        st.info("Camelot n'est pas installé. Utilisation de pdfplumber uniquement.")
        return False
    except Exception as e:
        st.warning(f"Erreur lors de l'utilisation de Camelot: {str(e)}")
        return False

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
        
        # Post-traiter les données extraites
        processed_data = post_process_extracted_data(extracted_data)
        st.write(f"Données extraites et traitées: {len(processed_data.get('suspicions', []))} suspicions")
        
        # Ajouter les données à la base de données
        st.write("Ajout des données à la base...")
        success = data_manager.add_report_data(report_date, pdf_path, processed_data)
        st.write(f"Ajout réussi: {success}")
        
        return success
    except Exception as e:
        st.error(f"Erreur lors de la vérification: {str(e)}")
        st.error(traceback.format_exc())
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
        
        # Post-traiter les données extraites
        processed_data = post_process_extracted_data(extracted_data)
        st.write(f"Données extraites et traitées: {len(processed_data.get('suspicions', []))} suspicions")
        
        # Ajouter les données à la base de données
        st.write("Ajout des données à la base...")
        success = data_manager.add_report_data(report_date, pdf_path, processed_data)
        st.write(f"Ajout réussi: {success}")
        
        return success
    except Exception as e:
        st.error(f"Erreur lors du téléchargement forcé: {str(e)}")
        st.error(traceback.format_exc())
        return False
