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
