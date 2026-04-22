import streamlit as st
import tempfile
import os
import pdfplumber
from pdf_processor import (
    extract_data_from_pdf,
    download_latest_report,
    _detect_fraud_type,
    _match_headers,
    EU_TABLE_SETTINGS,
)

st.title("Test d'extraction PDF")

tab1, tab2, tab3 = st.tabs(
    ["Télécharger un PDF", "Rapport en ligne", "Résultat d'extraction"]
)

pdf_file = None

with tab1:
    uploaded = st.file_uploader("Choisir un fichier PDF", type="pdf")
    if uploaded:
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, "uploaded_report.pdf")
        with open(temp_path, "wb") as f:
            f.write(uploaded.getvalue())
        pdf_file = temp_path
        st.success("Fichier chargé.")

with tab2:
    if st.button("Télécharger le dernier rapport UE"):
        with st.spinner("Téléchargement..."):
            path, date = download_latest_report()
            if path:
                pdf_file = path
                st.success(f"Rapport téléchargé (date: {date})")
            else:
                st.error(f"Échec: {date}")

with tab3:
    pass

if pdf_file:
    st.divider()

    with st.expander("Aperçu du PDF"):
        try:
            with pdfplumber.open(pdf_file) as pdf:
                st.write(f"Pages: {len(pdf.pages)}")
                page_num = st.number_input(
                    "Page à prévisualiser",
                    min_value=1,
                    max_value=len(pdf.pages),
                    value=1,
                )
                text = pdf.pages[page_num - 1].extract_text() or ""
                st.text(text[:3000])
                if len(text) > 3000:
                    st.caption(f"... ({len(text)} caractères au total)")
        except Exception as e:
            st.error(f"Erreur: {e}")

    if st.button("Lancer l'extraction", type="primary"):
        with st.spinner("Extraction en cours..."):
            result = extract_data_from_pdf(pdf_file)

        suspicions = result.get("suspicions", [])
        total = result.get("total_suspicions", 0)
        confidence = result.get("confidence_score", 0)
        method = result.get("method", "pdfplumber")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Suspicions extraites", len(suspicions))
        with col2:
            st.metric("Total annoncé", total if total > 0 else "N/A")
        with col3:
            if total > 0:
                st.metric("Confiance", f"{confidence * 100:.0f}%")
            else:
                st.metric("Confiance", "N/A")

        if total > 0 and abs(len(suspicions) - total) > total * 0.2:
            st.warning(
                f"Écart important : {len(suspicions)} extraites vs {total} annoncées. "
                "L'extraction peut être incomplète (cellules fusionnées, tableaux complexes)."
            )

        if suspicions:
            import pandas as pd

            df = pd.DataFrame(suspicions)
            st.subheader("Données extraites")
            st.dataframe(df, use_container_width=True, hide_index=True)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Télécharger CSV extrait", csv, "extraction_result.csv", "text/csv"
            )

            if st.button("Ajouter à la base de données"):
                dm = st.session_state.data_manager
                report_date = st.text_input(
                    "Date du rapport (YYYY-MM)", value="2025-01"
                )
                if report_date:
                    success = dm.add_report_data(
                        report_date,
                        pdf_file,
                        result,
                        confidence_score=confidence,
                        extraction_method=method,
                    )
                    if success:
                        st.success("Données ajoutées à la base !")
                    else:
                        st.error("Erreur lors de l'ajout.")
