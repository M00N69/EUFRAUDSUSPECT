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

st.set_page_config(page_title="Test d'extraction PDF", layout="wide")

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
            
            for page_idx in pages_to_process:
                st.write(f"Traitement de la page {page_idx+1}...")
                page = pdf.pages[page_idx]
                
                # Extraction du texte complet
                text = page.extract_text()
                
                # Déterminer la section de fraude
                fraud_type = None
                if "1. PRODUCT TAMPERING" in text:
                    fraud_type = "Product tampering"
                elif "2. RECORD TAMPERING" in text:
                    fraud_type = "Record tampering"
                elif "3. OTHER NON-COMPLIANCES" in text:
                    fraud_type = "Other non-compliances"
                
                # Extraction des tableaux
                tables = page.extract_tables()
                
                for table_idx, table in enumerate(tables):
                    if not table or len(table) <= 1:
                        continue
                    
                    # Vérifier les en-têtes
                    header_row = table[0]
                    header_text = ", ".join([str(h) for h in header_row if h])
                    
                    # Convertir en DataFrame pour une meilleure visualisation
                    df = pd.DataFrame(table[1:], columns=header_row)
                    df['_fraud_type'] = fraud_type
                    df['_page'] = page_idx + 1
                    df['_table'] = table_idx + 1
                    
                    results.append({
                        "page": page_idx + 1,
                        "table": table_idx + 1,
                        "headers": header_text,
                        "fraud_type": fraud_type,
                        "dataframe": df,
                        "raw_data": table
                    })
        
        return results
    
    except Exception as e:
        st.error(f"Erreur pdfplumber: {str(e)}")
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
        lattice_tables = camelot.read_pdf(pdf_path, pages=pages, flavor='lattice')
        st.write(f"Camelot (lattice) a trouvé {len(lattice_tables)} tableaux.")
        
        for i, table in enumerate(lattice_tables):
            df = table.df
            results.append({
                "page": table.page,
                "table": i + 1,
                "headers": ", ".join(df.iloc[0].tolist()),
                "fraud_type": "Unknown (to be determined)",
                "dataframe": df,
                "raw_data": df.values.tolist(),
                "accuracy": table.accuracy,
                "method": "camelot-lattice"
            })
        
        # Extraire les tableaux en mode stream (sans bordures)
        stream_tables = camelot.read_pdf(pdf_path, pages=pages, flavor='stream')
        st.write(f"Camelot (stream) a trouvé {len(stream_tables)} tableaux.")
        
        for i, table in enumerate(stream_tables):
            df = table.df
            results.append({
                "page": table.page,
                "table": i + 1,
                "headers": ", ".join(df.iloc[0].tolist()),
                "fraud_type": "Unknown (to be determined)",
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
        tables = tabula.read_pdf(pdf_path, pages=pages, multiple_tables=True)
        st.write(f"Tabula a trouvé {len(tables)} tableaux.")
        
        for i, df in enumerate(tables):
            if not df.empty:
                results.append({
                    "page": "Unknown",  # Tabula ne fournit pas facilement cette info
                    "table": i + 1,
                    "headers": ", ".join(df.columns.tolist()),
                    "fraud_type": "Unknown (to be determined)",
                    "dataframe": df,
                    "raw_data": df.values.tolist(),
                    "method": "tabula"
                })
        
        return results
    
    except Exception as e:
        st.error(f"Erreur tabula: {str(e)}")
        st.error(traceback.format_exc())
        return []

def extract_with_custom_algo(pdf_path, page_range=None):
    """Extraction personnalisée avec gestion des cellules fusionnées"""
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
            processed_tables = []
            
            for page_idx in pages_to_process:
                st.write(f"Traitement de la page {page_idx+1}...")
                page = pdf.pages[page_idx]
                text = page.extract_text()
                
                # Déterminer le type de fraude
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
                        break
                
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
                    
                    for row in table[1:]:
                        # Ignorer les lignes vides
                        if not row or all(not cell or (isinstance(cell, str) and cell.strip() == "") for cell in row):
                            continue
                        
                        # Créer une ligne traitée avec propagation des valeurs
                        processed_row = list(row)  # Copie de la ligne
                        
                        # Mettre à jour les valeurs non vides
                        for i, cell in enumerate(row):
                            if cell and isinstance(cell, str) and cell.strip():
                                last_values[i] = cell.strip()
                            elif i in last_values and i in [header_indices.get('CLASSIFICATION', -1), header_indices.get('PRODUCT CATEGORY', -1)]:
                                # Propager les valeurs pour les cellules fusionnées (uniquement pour certaines colonnes)
                                processed_row[i] = last_values[i]
                        
                        # Ajouter un champ pour le type de fraude
                        processed_row.append(current_fraud_type)
                        
                        processed_rows.append(processed_row)
                    
                    # Ajouter "FRAUD TYPE" à l'en-tête
                    processed_rows[0].append("FRAUD TYPE")
                    
                    # Créer un DataFrame
                    df = pd.DataFrame(processed_rows[1:], columns=processed_rows[0])
                    
                    results.append({
                        "page": page_idx + 1,
                        "table": table_idx + 1,
                        "headers": ", ".join([str(h) for h in processed_rows[0] if h]),
                        "fraud_type": current_fraud_type,
                        "dataframe": df,
                        "raw_data": processed_rows,
                        "method": "custom"
                    })
        
        return results
    
    except Exception as e:
        st.error(f"Erreur custom: {str(e)}")
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
    # Option pour un exemple intégré (à implémenter)
    st.info("Cette fonctionnalité n'est pas encore implémentée. Veuillez utiliser l'une des autres options.")

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
    methods = st.multiselect(
        "Méthodes d'extraction à tester",
        ["pdfplumber", "camelot (si disponible)", "tabula (si disponible)", "algorithme personnalisé"],
        default=["pdfplumber", "algorithme personnalisé"]
    )
    
    if st.button("Lancer l'extraction"):
        all_results = {}
        
        if "pdfplumber" in methods:
            with st.spinner("Extraction avec pdfplumber..."):
                all_results["pdfplumber"] = extract_with_pdfplumber(pdf_file, page_range)
        
        if "camelot (si disponible)" in methods and CAMELOT_AVAILABLE:
            with st.spinner("Extraction avec camelot..."):
                all_results["camelot"] = extract_with_camelot(pdf_file, page_range)
        
        if "tabula (si disponible)" in methods and TABULA_AVAILABLE:
            with st.spinner("Extraction avec tabula..."):
                all_results["tabula"] = extract_with_tabula(pdf_file, page_range)
        
        if "algorithme personnalisé" in methods:
            with st.spinner("Extraction avec l'algorithme personnalisé..."):
                all_results["custom"] = extract_with_custom_algo(pdf_file, page_range)
        
        # Afficher les résultats
        st.subheader("Résultats de l'extraction")
        
        for method, results in all_results.items():
            st.write(f"### Méthode: {method}")
            st.write(f"Nombre de tableaux extraits: {len(results)}")
            
            for i, result in enumerate(results):
                with st.expander(f"Tableau {i+1} - Page {result['page']} - {result['headers'][:100]}..."):
                    st.write(f"**Type de fraude**: {result.get('fraud_type', 'Non détecté')}")
                    st.write(f"**En-têtes**: {result['headers']}")
                    
                    if 'accuracy' in result:
                        st.write(f"**Précision**: {result['accuracy']:.2f}")
                    
                    # Afficher le DataFrame
                    st.dataframe(result['dataframe'])
                    
                    # Option pour télécharger le DataFrame
                    csv = result['dataframe'].to_csv(index=False)
                    st.download_button(
                        label="Télécharger CSV",
                        data=csv,
                        file_name=f"{method}_page{result['page']}_table{result['table']}.csv",
                        mime="text/csv"
                    )

# Informations techniques
with st.expander("Informations techniques"):
    st.write("### Bibliothèques disponibles")
    st.write(f"- pdfplumber: Disponible")
    st.write(f"- camelot-py: {'Disponible' if CAMELOT_AVAILABLE else 'Non disponible'}")
    st.write(f"- tabula-py: {'Disponible' if TABULA_AVAILABLE else 'Non disponible'}")
    
    st.write("### Installation des bibliothèques manquantes")
    st.code("""
# Installation de Camelot
pip install camelot-py opencv-python

# Installation de Tabula
pip install tabula-py
    """)
    
    st.write("### Notes sur les différentes méthodes")
    st.markdown("""
- **pdfplumber**: Simple, adapté pour des tableaux basiques. Peut avoir des difficultés avec les cellules fusionnées.
- **camelot-py**: Plus puissant, deux modes (lattice et stream). Meilleur avec les tableaux complexes.
- **tabula-py**: Basé sur Tabula-Java, bonne performance pour les tableaux structurés.
- **algorithme personnalisé**: Implémentation spécifique pour gérer les cellules fusionnées et la structure du rapport.
    """)
