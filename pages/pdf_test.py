import streamlit as st
import pandas as pd
import pdfplumber
import PyPDF2
import re
import os
import tempfile
import traceback
from urllib.parse import urlparse
import requests
from io import BytesIO
import numpy as np

# Tenter d'importer des bibliothèques alternatives
try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False

try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    TABULA_AVAILABLE = False

try:
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTTextContainer, LTChar, LTRect, LTFigure, LTTextBoxHorizontal
    PDFMINER_AVAILABLE = True
except ImportError:
    PDFMINER_AVAILABLE = False

try:
    import pytesseract
    from pdf2image import convert_from_path
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

st.set_page_config(page_title="Test d'extraction PDF", layout="wide")

# Fonctions utilitaires
def clean_dataframe_for_display(df):
    """Nettoie un DataFrame pour l'affichage dans Streamlit"""
    # Créer une copie pour ne pas modifier l'original
    df_clean = df.copy()
    
    # Vérifier et réparer les en-têtes dupliqués
    if df_clean.columns.duplicated().any():
        cols = pd.Series(df_clean.columns)
        for i in range(len(cols)):
            mask = cols.iloc[:i].eq(cols.iloc[i])
            if mask.any():
                cols.iloc[i] = f"{cols.iloc[i]}_{i}"
        df_clean.columns = cols
    
    # Convertir toutes les colonnes en string
    for col in df_clean.columns:
        try:
            df_clean[col] = df_clean[col].fillna("").astype(str)
        except:
            # Si la conversion échoue, créer une nouvelle colonne
            df_clean[f"{col}_str"] = df_clean[col].apply(lambda x: str(x) if x is not None else "")
            df_clean = df_clean.drop(columns=[col])
    
    return df_clean

def detect_fraud_section(text):
    """Détecte la section de fraude dans le texte"""
    fraud_section_patterns = [
        (r"1\.?\s*PRODUCT\s+TAMPERING", "Product tampering"),
        (r"2\.?\s*RECORD\s+TAMPERING", "Record tampering"),
        (r"3\.?\s*OTHER\s+NON-COMPLIANCES", "Other non-compliances")
    ]
    
    for pattern, fraud_type in fraud_section_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return fraud_type
    
    # Méthode alternative pour les cas où le format numéroté n'est pas trouvé
    if "PRODUCT TAMPERING" in text:
        return "Product tampering"
    elif "RECORD TAMPERING" in text:
        return "Record tampering"
    elif "OTHER NON-COMPLIANCES" in text:
        return "Other non-compliances"
    
    return None

# Fonctions d'extraction
def extract_with_pdfplumber(pdf_path, page_range=None):
    """Extraction avec pdfplumber"""
    results = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Déterminer les pages à traiter
            if page_range:
                pages_to_process = range(page_range[0]-1, min(page_range[1], len(pdf.pages)))
            else:
                pages_to_process = range(len(pdf.pages))
            
            current_fraud_type = None
            
            for page_idx in pages_to_process:
                st.write(f"Traitement de la page {page_idx+1}...")
                page = pdf.pages[page_idx]
                
                # Extraction du texte complet
                text = page.extract_text()
                
                # Déterminer la section de fraude
                detected_fraud_type = detect_fraud_section(text)
                if detected_fraud_type:
                    current_fraud_type = detected_fraud_type
                    st.info(f"Type de fraude détecté sur la page {page_idx+1}: {current_fraud_type}")
                
                # Extraction des tableaux
                tables = page.extract_tables()
                
                for table_idx, table in enumerate(tables):
                    if not table or len(table) <= 1:
                        continue
                    
                    # Vérifier les en-têtes
                    header_row = table[0]
                    header_text = ", ".join([str(h) for h in header_row if h])
                    
                    try:
                        # Créer des noms de colonnes uniques si besoin
                        header_cols = []
                        for i, h in enumerate(header_row):
                            if h is None or h == "":
                                h = f"Column_{i}"
                            if h in header_cols:
                                h = f"{h}_{i}"
                            header_cols.append(h)
                        
                        # Créer le DataFrame avec les colonnes nettoyées
                        df = pd.DataFrame(table[1:], columns=header_cols)
                        df['_fraud_type'] = current_fraud_type
                        df['_page'] = page_idx + 1
                        df['_table'] = table_idx + 1
                    except Exception as e:
                        st.warning(f"Erreur lors de la création du DataFrame: {str(e)}")
                        # Créer un DataFrame minimal en cas d'erreur
                        df = pd.DataFrame({
                            '_page': [page_idx + 1],
                            '_table': [table_idx + 1],
                            '_fraud_type': [current_fraud_type],
                            'error': ["Erreur de conversion du tableau"]
                        })
                    
                    results.append({
                        "page": page_idx + 1,
                        "table": table_idx + 1,
                        "headers": header_text,
                        "fraud_type": current_fraud_type,
                        "dataframe": df,
                        "raw_data": table,
                        "method": "pdfplumber-basic"
                    })
        
        return results
    
    except Exception as e:
        st.error(f"Erreur pdfplumber: {str(e)}")
        st.error(traceback.format_exc())
        return []

def extract_with_pdfplumber_advanced(pdf_path, page_range=None):
    """Extraction améliorée avec pdfplumber et gestion des cellules fusionnées"""
    results = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Déterminer les pages à traiter
            if page_range:
                pages_to_process = range(page_range[0]-1, min(page_range[1], len(pdf.pages)))
            else:
                pages_to_process = range(len(pdf.pages))
            
            # Variables pour suivre l'état entre les pages
            current_fraud_type = None
            current_classification = None
            last_values = {}  # Pour les cellules fusionnées
            
            for page_idx in pages_to_process:
                st.write(f"Traitement avancé de la page {page_idx+1}...")
                page = pdf.pages[page_idx]
                text = page.extract_text()
                
                # Déterminer le type de fraude
                detected_fraud_type = detect_fraud_section(text)
                if detected_fraud_type:
                    current_fraud_type = detected_fraud_type
                    # Réinitialiser les valeurs au changement de section
                    last_values = {}
                    current_classification = None
                    st.info(f"Type de fraude détecté sur la page {page_idx+1}: {current_fraud_type}")
                
                # Extraire les tableaux
                tables = page.extract_tables()
                
                for table_idx, table in enumerate(tables):
                    if not table or len(table) <= 1:
                        continue
                    
                    # Vérifier les en-têtes
                    header_row = table[0]
                    
                    # Traitement des en-têtes pour correspondance approximative
                    expected_headers = ["CLASSIFICATION", "PRODUCT CATEGORY", "COMMODITY", "ISSUE", "ORIGIN", "NOTIFIED BY"]
                    header_indices = {}
                    
                    for i, cell in enumerate(header_row):
                        if not cell:
                            continue
                        cell_str = str(cell).strip().upper()
                        for expected in expected_headers:
                            if expected in cell_str or cell_str in expected:
                                header_indices[expected] = i
                                break
                    
                    # S'il manque trop de colonnes, passer au suivant
                    if len(header_indices) < 3:
                        continue
                    
                    # Traiter les lignes de données avec gestion des cellules fusionnées
                    processed_rows = [header_row]  # Commencer avec l'en-tête
                    table_last_values = {}  # Valeurs pour ce tableau spécifique
                    
                    for row in table[1:]:
                        # Ignorer les lignes vides
                        if not row or all(not cell or (isinstance(cell, str) and cell.strip() == "") for cell in row):
                            continue
                        
                        # Créer une ligne traitée avec propagation des valeurs
                        processed_row = list(row)  # Copie de la ligne
                        
                        # Mettre à jour les valeurs non vides
                        for i, cell in enumerate(row):
                            if cell and isinstance(cell, str) and cell.strip():
                                table_last_values[i] = cell.strip()
                            elif i in table_last_values and i in [header_indices.get('CLASSIFICATION', -1), header_indices.get('PRODUCT CATEGORY', -1)]:
                                # Propager les valeurs pour les cellules fusionnées (uniquement pour certaines colonnes)
                                processed_row[i] = table_last_values[i]
                        
                        # Ajouter un champ pour le type de fraude
                        processed_row.append(current_fraud_type)
                        
                        processed_rows.append(processed_row)
                    
                    # Ajouter "FRAUD TYPE" à l'en-tête
                    processed_header = list(header_row)
                    processed_header.append("FRAUD TYPE")
                    
                    try:
                        # Créer un DataFrame
                        df = pd.DataFrame(processed_rows[1:], columns=processed_header)
                        
                        results.append({
                            "page": page_idx + 1,
                            "table": table_idx + 1,
                            "headers": ", ".join([str(h) for h in processed_header if h]),
                            "fraud_type": current_fraud_type,
                            "dataframe": df,
                            "raw_data": processed_rows,
                            "method": "pdfplumber-advanced"
                        })
                    except Exception as e:
                        st.warning(f"Erreur lors de la création du DataFrame avancé: {str(e)}")
        
        return results
    
    except Exception as e:
        st.error(f"Erreur pdfplumber avancé: {str(e)}")
        st.error(traceback.format_exc())
        return []

def extract_with_camelot(pdf_path, page_range=None):
    """Extraction avec camelot-py (si disponible)"""
    if not CAMELOT_AVAILABLE:
        st.warning("Camelot n'est pas installé. Utilisez `pip install camelot-py opencv-python` pour l'installer.")
        return []
    
    results = []
    
    try:
        # Définir la plage de pages
        if page_range:
            pages = f"{page_range[0]}-{page_range[1]}"
        else:
            pages = 'all'
        
        # Extraire les tableaux en mode lattice (bordures)
        st.info("Extraction avec Camelot en mode 'lattice'...")
        lattice_tables = camelot.read_pdf(pdf_path, pages=pages, flavor='lattice')
        st.info(f"Camelot (lattice) a trouvé {len(lattice_tables)} tableaux.")
        
        for i, table in enumerate(lattice_tables):
            df = table.df
            
            # Déterminer le type de fraude à partir du texte de la page
            fraud_type = "Unknown"
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    page_idx = int(table.page) - 1
                    if page_idx < len(pdf.pages):
                        text = pdf.pages[page_idx].extract_text()
                        detected_fraud_type = detect_fraud_section(text)
                        if detected_fraud_type:
                            fraud_type = detected_fraud_type
            except:
                pass
            
            results.append({
                "page": table.page,
                "table": i + 1,
                "headers": ", ".join(df.iloc[0].tolist()),
                "fraud_type": fraud_type,
                "dataframe": df,
                "raw_data": df.values.tolist(),
                "accuracy": table.accuracy,
                "method": "camelot-lattice"
            })
        
        # Extraire les tableaux en mode stream (sans bordures)
        st.info("Extraction avec Camelot en mode 'stream'...")
        stream_tables = camelot.read_pdf(pdf_path, pages=pages, flavor='stream')
        st.info(f"Camelot (stream) a trouvé {len(stream_tables)} tableaux.")
        
        for i, table in enumerate(stream_tables):
            df = table.df
            
            # Déterminer le type de fraude à partir du texte de la page
            fraud_type = "Unknown"
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    page_idx = int(table.page) - 1
                    if page_idx < len(pdf.pages):
                        text = pdf.pages[page_idx].extract_text()
                        detected_fraud_type = detect_fraud_section(text)
                        if detected_fraud_type:
                            fraud_type = detected_fraud_type
            except:
                pass
            
            results.append({
                "page": table.page,
                "table": i + 1,
                "headers": ", ".join(df.iloc[0].tolist()),
                "fraud_type": fraud_type,
                "dataframe": df,
                "raw_data": df.values.tolist(),
                "accuracy": table.accuracy,
                "method": "camelot-stream"
            })
        
        return results
    
    except Exception as e:
        st.error(f"Erreur camelot: {str(e)}")
        st.error(traceback.format_exc())
        return []

def extract_with_tabula(pdf_path, page_range=None):
    """Extraction avec tabula-py (si disponible)"""
    if not TABULA_AVAILABLE:
        st.warning("Tabula n'est pas installé. Utilisez `pip install tabula-py` pour l'installer.")
        return []
    
    results = []
    
    try:
        # Définir la plage de pages
        if page_range:
            pages = list(range(page_range[0], page_range[1] + 1))
        else:
            pages = 'all'
        
        # Extraire les tableaux
        st.info("Extraction avec Tabula...")
        tables = tabula.read_pdf(pdf_path, pages=pages, multiple_tables=True)
        st.info(f"Tabula a trouvé {len(tables)} tableaux.")
        
        for i, df in enumerate(tables):
            if not df.empty:
                # Déterminer la page
                page_num = "Unknown"
                if page_range and isinstance(pages, list) and len(pages) == 1:
                    page_num = pages[0]
                else:
                    # Tenter de déterminer la page
                    try:
                        # La logique varie selon la version de tabula
                        page_num = pages[i] if isinstance(pages, list) and i < len(pages) else "Unknown"
                    except:
                        pass
                
                # Déterminer le type de fraude
                fraud_type = "Unknown"
                try:
                    with pdfplumber.open(pdf_path) as pdf:
                        if page_num != "Unknown":
                            page_idx = page_num - 1
                            if page_idx < len(pdf.pages):
                                text = pdf.pages[page_idx].extract_text()
                                detected_fraud_type = detect_fraud_section(text)
                                if detected_fraud_type:
                                    fraud_type = detected_fraud_type
                except:
                    pass
                
                results.append({
                    "page": page_num,
                    "table": i + 1,
                    "headers": ", ".join(df.columns.tolist()),
                    "fraud_type": fraud_type,
                    "dataframe": df,
                    "raw_data": df.values.tolist(),
                    "method": "tabula"
                })
        
        return results
    
    except Exception as e:
        st.error(f"Erreur tabula: {str(e)}")
        st.error(traceback.format_exc())
        return []

def extract_with_pdfminer(pdf_path, page_range=None):
    """Extraction avec PDFMiner (si disponible)"""
    if not PDFMINER_AVAILABLE:
        st.warning("PDFMiner n'est pas installé. Utilisez `pip install pdfminer.six` pour l'installer.")
        return []
    
    results = []
    
    try:
        st.info("Extraction avec PDFMiner...")
        
        # Extract pages
        pages = list(extract_pages(pdf_path))
        
        # Filter pages by range if provided
        if page_range:
            filtered_pages = pages[page_range[0]-1:page_range[1]]
        else:
            filtered_pages = pages
        
        for page_idx, page in enumerate(filtered_pages):
            actual_page_num = page_idx + (page_range[0] if page_range else 1)
            st.write(f"Traitement de la page {actual_page_num} avec PDFMiner...")
            
            # Extract text content
            text_content = ""
            tables_data = []
            current_table = []
            current_line = []
            last_y = None
            
            # Sort text elements by y-coordinate (top to bottom)
            text_elements = [element for element in page if isinstance(element, LTTextContainer)]
            text_elements.sort(key=lambda e: -e.y0)  # Sort top to bottom
            
            for element in text_elements:
                text_content += element.get_text() + "\n"
                
                # Collect potential table data
                text = element.get_text().strip()
                if text:
                    if last_y is None:
                        last_y = element.y0
                    
                    # If this is a new line (y position changed significantly)
                    if abs(element.y0 - last_y) > 5:
                        if current_line:
                            current_table.append(current_line)
                            current_line = []
                        last_y = element.y0
                    
                    current_line.append(text)
            
            # Add the last line if any
            if current_line:
                current_table.append(current_line)
            
            # Add the table if it has at least 2 rows
            if len(current_table) >= 2:
                tables_data.append(current_table)
            
            # Detect fraud type
            fraud_type = detect_fraud_section(text_content)
            
            # Process tables
            for table_idx, table_data in enumerate(tables_data):
                # Try to convert to DataFrame
                try:
                    # Normalize row lengths
                    max_cols = max(len(row) for row in table_data)
                    normalized_table = [row + [''] * (max_cols - len(row)) for row in table_data]
                    
                    # Use first row as header
                    headers = normalized_table[0]
                    data_rows = normalized_table[1:]
                    
                    # Create DataFrame
                    df = pd.DataFrame(data_rows, columns=headers)
                    
                    results.append({
                        "page": actual_page_num,
                        "table": table_idx + 1,
                        "headers": ", ".join(headers),
                        "fraud_type": fraud_type,
                        "dataframe": df,
                        "raw_data": table_data,
                        "method": "pdfminer"
                    })
                except Exception as e:
                    st.warning(f"Erreur lors de la création du DataFrame pour la table {table_idx+1}: {str(e)}")
        
        return results
    
    except Exception as e:
        st.error(f"Erreur PDFMiner: {str(e)}")
        st.error(traceback.format_exc())
        return []

def extract_with_tesseract(pdf_path, page_range=None):
    """Extraction avec Tesseract OCR (si disponible)"""
    if not TESSERACT_AVAILABLE:
        st.warning("Tesseract ou pdf2image n'est pas installé. Utilisez `pip install pytesseract pdf2image` pour les installer.")
        st.warning("Vous devez également installer Tesseract OCR sur votre système.")
        return []
    
    results = []
    
    try:
        st.info("Conversion du PDF en images pour OCR...")
        
        # Définir la plage de pages
        if page_range:
            pages = list(range(page_range[0], page_range[1] + 1))
        else:
            pages = None
        
        # Convertir les pages en images
        images = convert_from_path(pdf_path, first_page=page_range[0] if page_range else 1, 
                                   last_page=page_range[1] if page_range else None)
        
        st.info(f"OCR sur {len(images)} pages...")
        
        for i, image in enumerate(images):
            page_num = i + (page_range[0] if page_range else 1)
            st.write(f"OCR sur la page {page_num}...")
            
            # Extraire le texte avec OCR
            text = pytesseract.image_to_string(image)
            
            # Détecter les tableaux avec pytesseract
            try:
                # Utiliser pytesseract pour extraire les données tabulaires
                tables_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DATAFRAME)
                
                # Traiter les données pour identifier les lignes et colonnes
                tables_data = tables_data[tables_data['conf'] > 50]  # Filtrer par confiance
                
                # Grouper par lignes (block_num ou ligne)
                grouped = tables_data.groupby('block_num')
                
                table_data = []
                for block, group in grouped:
                    # Trier par position horizontale
                    sorted_group = group.sort_values('left')
                    row_text = sorted_group['text'].tolist()
                    if row_text and any(row_text):
                        table_data.append(row_text)
                
                # Détecter le type de fraude
                fraud_type = detect_fraud_section(text)
                
                if len(table_data) >= 2:  # Au moins en-tête + une ligne
                    try:
                        # Normaliser le nombre de colonnes
                        max_cols = max(len(row) for row in table_data)
                        normalized_table = [row + [''] * (max_cols - len(row)) for row in table_data]
                        
                        # Utiliser la première ligne comme en-tête
                        headers = normalized_table[0]
                        data_rows = normalized_table[1:]
                        
                        df = pd.DataFrame(data_rows, columns=headers)
                        
                        results.append({
                            "page": page_num,
                            "table": 1,  # Simplifié pour cet exemple
                            "headers": ", ".join([str(h) for h in headers if h]),
                            "fraud_type": fraud_type,
                            "dataframe": df,
                            "raw_data": table_data,
                            "method": "tesseract-ocr"
                        })
                    except Exception as e:
                        st.warning(f"Erreur lors de la création du DataFrame OCR: {str(e)}")
            except Exception as e:
                st.warning(f"Erreur OCR sur la page {page_num}: {str(e)}")
        
        return results
    
    except Exception as e:
        st.error(f"Erreur Tesseract: {str(e)}")
        st.error(traceback.format_exc())
        return []

def extract_with_custom_algo(pdf_path, page_range=None):
    """Extraction personnalisée avec gestion des cellules fusionnées optimisée pour les rapports UE"""
    results = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Déterminer les pages à traiter
            if page_range:
                pages_to_process = range(page_range[0]-1, min(page_range[1], len(pdf.pages)))
            else:
                pages_to_process = range(len(pdf.pages))
            
            # Variables pour suivre l'état entre les pages
            current_fraud_type = None
            current_classification = None
            last_values = {}  # Pour les cellules fusionnées
            
            for page_idx in pages_to_process:
                st.write(f"Traitement personnalisé de la page {page_idx+1}...")
                page = pdf.pages[page_idx]
                text = page.extract_text()
                
                # Déterminer le type de fraude de façon plus robuste
                fraud_section_patterns = [
                    (r"1\.?\s*PRODUCT\s+TAMPERING", "Product tampering"),
                    (r"2\.?\s*RECORD\s+TAMPERING", "Record tampering"),
                    (r"3\.?\s*OTHER\s+NON-COMPLIANCES", "Other non-compliances")
                ]
                
                for pattern, fraud_type in fraud_section_patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        current_fraud_type = fraud_type
                        # Réinitialiser les valeurs au changement de section
                        last_values = {}
                        current_classification = None
                        st.info(f"Type de fraude détecté sur la page {page_idx+1}: {current_fraud_type}")
                        break
                
                if current_fraud_type is None and any(keyword in text for keyword in ["PRODUCT TAMPERING", "RECORD TAMPERING", "OTHER NON-COMPLIANCES"]):
                    for keyword, fraud_type in [
                        ("PRODUCT TAMPERING", "Product tampering"),
                        ("RECORD TAMPERING", "Record tampering"),
                        ("OTHER NON-COMPLIANCES", "Other non-compliances")
                    ]:
                        if keyword in text:
                            current_fraud_type = fraud_type
                            last_values = {}
                            current_classification = None
                            st.info(f"Type de fraude détecté (méthode alternative) sur la page {page_idx+1}: {current_fraud_type}")
                            break
                
                # Extraire les tableaux
                tables = page.extract_tables()
                
                for table_idx, table in enumerate(tables):
                    if not table or len(table) <= 1:
                        continue
                    
                    # Vérifier les en-têtes
                    header_row = table[0]
                    
                    # En-têtes attendus dans le rapport
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
                    
                    # Vérifier si c'est un tableau de données pertinent
                    if len(header_indices) < 3:
                        continue
                    
                    # Créer une copie du tableau pour le traitement
                    processed_table = [row[:] for row in table]
                    
                    # Initialiser les dernières valeurs connues pour ce tableau
                    table_last_values = {}
                    
                    # Traiter chaque ligne pour gérer les cellules fusionnées
                    for row_idx in range(1, len(processed_table)):
                        row = processed_table[row_idx]
                        
                        # Traiter les cellules vides qui devraient reprendre la valeur précédente
                        for col_name, col_idx in header_indices.items():
                            if col_idx < len(row):
                                # Pour les colonnes où on propage les valeurs (Classification, Product Category)
                                if col_name in ["CLASSIFICATION", "PRODUCT CATEGORY"]:
                                    if not row[col_idx] or (isinstance(row[col_idx], str) and row[col_idx].strip() == ""):
                                        if col_idx in table_last_values:
                                            row[col_idx] = table_last_values[col_idx]
                                    else:
                                        table_last_values[col_idx] = row[col_idx]
                        
                        # Mettre à jour la classification courante
                        if 'CLASSIFICATION' in header_indices:
                            idx = header_indices['CLASSIFICATION']
                            if idx < len(row) and row[idx] and isinstance(row[idx], str) and row[idx].strip():
                                current_classification = row[idx].strip()
                        
                        # Ajouter le type de fraude à la ligne
                        row.append(current_fraud_type)
                    
                    # Ajouter une colonne pour le type de fraude à l'en-tête
                    processed_table[0].append("FRAUD TYPE")
                    
                    try:
                        # Créer un DataFrame avec les données traitées
                        df = pd.DataFrame(processed_table[1:], columns=processed_table[0])
                        
                        # Nettoyer les noms de colonnes (supprimer les espaces de début/fin)
                        df.columns = [col.strip() if isinstance(col, str) else col for col in df.columns]
                        
                        results.append({
                            "page": page_idx + 1,
                            "table": table_idx + 1,
                            "headers": ", ".join([str(h) for h in processed_table[0] if h]),
                            "fraud_type": current_fraud_type,
                            "dataframe": df,
                            "raw_data": processed_table,
                            "method": "custom-eu-report"
                        })
                    except Exception as e:
                        st.warning(f"Erreur lors de la création du DataFrame: {str(e)}")
        
        return results
    
    except Exception as e:
        st.error(f"Erreur dans l'algorithme personnalisé: {str(e)}")
        st.error(traceback.format_exc())
        return []

# Interface utilisateur
st.title("Test d'extraction de données des rapports de fraude alimentaire UE")

# Chargement du PDF
pdf_source = st.radio(
    "Source du PDF",
    ["Télécharger", "URL", "Exemple prédéfini"],
    horizontal=True
)

pdf_file = None

if pdf_source == "Télécharger":
    uploaded_file = st.file_uploader("Choisir un fichier PDF", type="pdf")
    if uploaded_file:
        # Sauvegarder dans un fichier temporaire
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, "report.pdf")
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        pdf_file = temp_path

elif pdf_source == "URL":
    pdf_url = st.text_input("URL du PDF", "https://food.ec.europa.eu/document/download/d5cfa85c-7d25-4408-99c5-86bea1d3d1e3_en?filename=ff_ffn_monthly-report_202502.pdf")
    
    if pdf_url and st.button("Télécharger depuis URL"):
        try:
            response = requests.get(pdf_url)
            if response.status_code == 200:
                # Sauvegarder dans un fichier temporaire
                temp_dir = tempfile.mkdtemp()
                filename = os.path.basename(urlparse(pdf_url).path) or "report.pdf"
                temp_path = os.path.join(temp_dir, filename)
                with open(temp_path, "wb") as f:
                    f.write(response.content)
                pdf_file = temp_path
                st.success(f"PDF téléchargé avec succès: {filename}")
            else:
                st.error(f"Erreur lors du téléchargement: {response.status_code}")
        except Exception as e:
            st.error(f"Erreur: {str(e)}")

else:  # Exemple prédéfini
    # Option pour un exemple intégré
    st.info("Cette fonctionnalité utilisera un exemple prédéfini du rapport de février 2025.")
    if st.button("Utiliser l'exemple prédéfini"):
        try:
            # URL du rapport de février 2025
            example_url = "https://food.ec.europa.eu/document/download/d5cfa85c-7d25-4408-99c5-86bea1d3d1e3_en?filename=ff_ffn_monthly-report_202502.pdf"
            response = requests.get(example_url)
            if response.status_code == 200:
                # Sauvegarder dans un fichier temporaire
                temp_dir = tempfile.mkdtemp()
                temp_path = os.path.join(temp_dir, "example_report.pdf")
                with open(temp_path, "wb") as f:
                    f.write(response.content)
                pdf_file = temp_path
                st.success("Exemple prédéfini téléchargé avec succès")
            else:
                st.error(f"Erreur lors du téléchargement de l'exemple: {response.status_code}")
        except Exception as e:
            st.error(f"Erreur: {str(e)}")

# Options d'extraction
if pdf_file:
    st.subheader("Options d'extraction")
    
    # Afficher l'aperçu du PDF
    with st.expander("Aperçu du PDF", expanded=False):
        try:
            with pdfplumber.open(pdf_file) as pdf:
                st.write(f"Nombre de pages: {len(pdf.pages)}")
                page_to_preview = st.number_input("Page à prévisualiser", min_value=1, max_value=len(pdf.pages), value=1)
                
                if page_to_preview:
                    page = pdf.pages[page_to_preview-1]
                    st.text(page.extract_text())
        except Exception as e:
            st.error(f"Erreur lors de l'aperçu: {str(e)}")
    
    # Plage de pages
    col1, col2 = st.columns(2)
    with col1:
        start_page = st.number_input("Page de début", min_value=1, value=3)
    with col2:
        try:
            with pdfplumber.open(pdf_file) as pdf:
                max_pages = len(pdf.pages)
        except:
            max_pages = 100
        end_page = st.number_input("Page de fin", min_value=start_page, max_value=max_pages, value=min(start_page+5, max_pages))
    
    page_range = (start_page, end_page)
    
    # Méthodes d'extraction
    available_methods = ["pdfplumber (basique)", "pdfplumber (avancé)", "algorithme personnalisé pour rapports UE"]
    
    if CAMELOT_AVAILABLE:
        available_methods.append("camelot")
    
    if TABULA_AVAILABLE:
        available_methods.append("tabula")
    
    if PDFMINER_AVAILABLE:
        available_methods.append("pdfminer")
    
    if TESSERACT_AVAILABLE:
        available_methods.append("tesseract (OCR)")
    
    methods = st.multiselect(
        "Méthodes d'extraction à tester",
        available_methods,
        default=["pdfplumber (basique)", "algorithme personnalisé pour rapports UE"]
    )
    
    # Options d'affichage
    display_options = st.expander("Options d'affichage", expanded=False)
    with display_options:
        show_raw_data = st.checkbox("Afficher les données brutes", value=False)
        limit_rows = st.number_input("Nombre de lignes à afficher (0 = toutes)", min_value=0, value=10)
    
    if st.button("Lancer l'extraction"):
        with st.spinner("Extraction en cours..."):
            all_results = {}
            
            if "pdfplumber (basique)" in methods:
                st.info("Extraction avec pdfplumber (basique)...")
                all_results["pdfplumber-basique"] = extract_with_pdfplumber(pdf_file, page_range)
            
            if "pdfplumber (avancé)" in methods:
                st.info("Extraction avec pdfplumber (avancé)...")
                all_results["pdfplumber-avancé"] = extract_with_pdfplumber_advanced(pdf_file, page_range)
            
            if "camelot" in methods and CAMELOT_AVAILABLE:
                st.info("Extraction avec camelot...")
                all_results["camelot"] = extract_with_camelot(pdf_file, page_range)
            
            if "tabula" in methods and TABULA_AVAILABLE:
                st.info("Extraction avec tabula...")
                all_results["tabula"] = extract_with_tabula(pdf_file, page_range)
            
            if "pdfminer" in methods and PDFMINER_AVAILABLE:
                st.info("Extraction avec pdfminer...")
                all_results["pdfminer"] = extract_with_pdfminer(pdf_file, page_range)
            
            if "tesseract (OCR)" in methods and TESSERACT_AVAILABLE:
                st.info("Extraction avec tesseract (OCR)...")
                all_results["tesseract"] = extract_with_tesseract(pdf_file, page_range)
            
            if "algorithme personnalisé pour rapports UE" in methods:
                st.info("Extraction avec l'algorithme personnalisé pour rapports UE...")
                all_results["custom-eu"] = extract_with_custom_algo(pdf_file, page_range)
        
        # Afficher les résultats
        st.subheader("Résultats de l'extraction")
        
        if not all_results:
            st.warning("Aucun résultat d'extraction obtenu. Vérifiez les méthodes sélectionnées et les options.")
        else:
            # Tableau récapitulatif
            summary_data = []
            for method, results in all_results.items():
                summary_data.append({
                    "Méthode": method,
                    "Tableaux extraits": len(results),
                    "Pages couvertes": len(set(r["page"] for r in results))
                })
            
            st.write("### Récapitulatif")
            st.dataframe(pd.DataFrame(summary_data))
            
            # Afficher les résultats détaillés par méthode
            for method, results in all_results.items():
                st.write(f"### Méthode: {method}")
                st.write(f"Nombre de tableaux extraits: {len(results)}")
                
                if not results:
                    st.warning(f"Aucun tableau extrait avec la méthode {method}")
                    continue
                
                for i, result in enumerate(results):
                    with st.expander(f"Tableau {i+1} - Page {result['page']} - {result['headers'][:100]}..."):
                        st.write(f"**Type de fraude**: {result.get('fraud_type', 'Non détecté')}")
                        st.write(f"**En-têtes**: {result['headers']}")
                        
                        if 'accuracy' in result:
                            st.write(f"**Précision**: {result['accuracy']:.2f}")
                        
                        # Afficher le DataFrame
                        try:
                            df_clean = clean_dataframe_for_display(result['dataframe'])
                            
                            # Limiter le nombre de lignes si demandé
                            if limit_rows > 0:
                                display_df = df_clean.head(limit_rows)
                            else:
                                display_df = df_clean
                            
                            st.dataframe(display_df)
                            
                            # Option pour télécharger le DataFrame
                            csv = df_clean.to_csv(index=False)
                            st.download_button(
                                label="Télécharger CSV",
                                data=csv,
                                file_name=f"{method}_page{result['page']}_table{result['table']}.csv",
                                mime="text/csv"
                            )
                            
                            # Afficher les données brutes si demandé
                            if show_raw_data:
                                st.write("**Données brutes:**")
                                st.code(str(result['raw_data']))
                        except Exception as e:
                            st.error(f"Erreur lors de l'affichage des données: {str(e)}")

# Informations techniques
with st.expander("Informations techniques"):
    st.write("### Bibliothèques disponibles")
    st.write(f"- pdfplumber: Disponible")
    st.write(f"- camelot-py: {'Disponible' if CAMELOT_AVAILABLE else 'Non disponible'}")
    st.write(f"- tabula-py: {'Disponible' if TABULA_AVAILABLE else 'Non disponible'}")
    st.write(f"- pdfminer.six: {'Disponible' if PDFMINER_AVAILABLE else 'Non disponible'}")
    st.write(f"- pytesseract & pdf2image: {'Disponible' if TESSERACT_AVAILABLE else 'Non disponible'}")
    
    st.write("### Installation des bibliothèques")
    st.code("""
# Bibliothèques de base (déjà dans requirements.txt)
pip install streamlit pandas pdfplumber PyPDF2 requests beautifulsoup4

# Bibliothèques supplémentaires pour l'extraction avancée
pip install camelot-py opencv-python  # Pour Camelot
pip install tabula-py                 # Pour Tabula
pip install pdfminer.six              # Pour PDFMiner
pip install pytesseract pdf2image     # Pour OCR avec Tesseract
    """)
    
    st.write("### Notes sur les différentes méthodes")
    st.markdown("""
- **pdfplumber (basique)**: Extraction simple des tableaux avec pdfplumber.
- **pdfplumber (avancé)**: Extension de pdfplumber avec un meilleur traitement des cellules fusionnées.
- **algorithme personnalisé pour rapports UE**: Optimisé spécifiquement pour les rapports de fraude alimentaire de l'UE.
- **camelot**: Puissant pour les tableaux avec bordures (mode lattice) ou sans bordures (mode stream).
- **tabula**: Basé sur Tabula-Java, bon pour les tableaux à structure claire.
- **pdfminer**: Analyse la disposition et les éléments du PDF pour reconstruire les tableaux.
- **tesseract (OCR)**: Utilise la reconnaissance optique de caractères sur des images converties du PDF.
    """)
    
    st.write("### Comparaison des méthodes")
    comparison_df = pd.DataFrame({
        "Méthode": [
            "pdfplumber (basique)",
            "pdfplumber (avancé)",
            "algorithme personnalisé",
            "camelot",
            "tabula",
            "pdfminer",
            "tesseract (OCR)"
        ],
        "Forces": [
            "Simple, facile à utiliser",
            "Meilleure gestion des cellules fusionnées",
            "Optimisé pour les rapports UE",
            "Excellent pour tableaux complexes",
            "Bonne détection automatique des tableaux",
            "Analyse précise de la disposition",
            "Peut extraire des tables dans des images/scans"
        ],
        "Faiblesses": [
            "Difficulté avec cellules fusionnées",
            "Plus complexe à configurer",
            "Spécifique à ce type de rapport",
            "Nécessite OpenCV",
            "Moins flexible pour structures complexes",
            "Reconstruction manuelle nécessaire",
            "Lent et dépend de la qualité du PDF"
        ]
    })
    st.dataframe(comparison_df)

st.markdown("---")
st.markdown("Auteur: Assistant Claude | Application de test pour l'extraction de données des rapports de fraude alimentaire UE")
