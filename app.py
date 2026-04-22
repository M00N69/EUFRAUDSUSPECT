import streamlit as st
from db_adapter import DataManager
from pdf_processor import check_for_new_report, force_download_latest_report
from datetime import datetime

st.set_page_config(
    page_title="EUFRAUDSUSPECT — Surveillance des fraudes alimentaires UE",
    page_icon="🍲",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "data_manager" not in st.session_state:
    with st.spinner("Chargement des données..."):
        st.session_state.data_manager = DataManager()

if "last_update_check" not in st.session_state:
    st.session_state.last_update_check = None
if "ai_conversation" not in st.session_state:
    st.session_state.ai_conversation = []
if "filters" not in st.session_state:
    st.session_state.filters = {}

dm = st.session_state.data_manager

dashboard = st.Page("pages/dashboard.py", title="Tableau de bord", icon="📊")
geo = st.Page("pages/geo_analysis.py", title="Analyse géographique", icon="🌍")
trends = st.Page("pages/trends.py", title="Tendances", icon="📈")
details = st.Page("pages/details.py", title="Détails des suspicions", icon="📋")
extraction = st.Page("pages/pdf_extraction.py", title="Extraction PDF", icon="🔍")
ai_page = st.Page("pages/ai_analysis.py", title="Analyse IA", icon="🤖")
guide = st.Page("pages/guide.py", title="Guide utilisateur", icon="📖")

pg = st.navigation(
    {
        "Analyse": [dashboard, geo, trends, details],
        "Outils": [extraction, ai_page],
        "Aide": [guide],
    }
)

with st.sidebar:
    st.title("EUFRAUDSUSPECT")
    st.caption("Surveillance des fraudes alimentaires dans l'UE")

    dm = st.session_state.data_manager
    has_data = dm.data is not None and not dm.data.empty

    if has_data:
        dates = dm.get_available_dates()
        years = sorted(set(d[:4] for d in dates if d))
        year_options = ["Toutes"] + years
        selected_year = st.selectbox("Année", year_options, index=0)

        if selected_year == "Toutes":
            filtered_dates = dates
        else:
            filtered_dates = [d for d in dates if d.startswith(selected_year)]

        if len(filtered_dates) > 1:
            start_date, end_date = st.select_slider(
                "Période",
                options=filtered_dates,
                value=(filtered_dates[0], filtered_dates[-1]),
            )
        elif len(filtered_dates) == 1:
            start_date = end_date = filtered_dates[0]
            st.info(f"Période: {filtered_dates[0]}")
        else:
            start_date = end_date = None

        all_categories = dm.get_product_categories()
        if all_categories:
            selected_categories = st.multiselect(
                "Catégories",
                all_categories,
                default=[],
                help=f"{len(all_categories)} catégories disponibles",
            )
        else:
            selected_categories = []

        all_fraud_types = dm.get_fraud_types()
        if all_fraud_types:
            selected_fraud_types = st.multiselect(
                "Types de fraude",
                all_fraud_types,
                default=[],
            )
        else:
            selected_fraud_types = []

        all_origins = dm.get_origins()
        if all_origins:
            selected_origins = st.multiselect(
                "Pays d'origine",
                all_origins,
                default=[],
            )
        else:
            selected_origins = []

        st.session_state.filters = {
            "start_date": start_date,
            "end_date": end_date,
            "categories": selected_categories,
            "fraud_types": selected_fraud_types,
            "origins": selected_origins,
        }

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "Vérifier nouveaux rapports",
                use_container_width=True,
                icon="🔄",
            ):
                with st.spinner("Vérification en cours..."):
                    try:
                        result = check_for_new_report(dm)
                        dm.reload()
                        if result:
                            st.success("Nouveau rapport ajouté !")
                        else:
                            st.info("Aucun nouveau rapport disponible.")
                        st.session_state.last_update_check = datetime.now()
                    except Exception as e:
                        st.error(f"Erreur: {e}")
        with col2:
            if st.button("Forcer mise à jour PDF", use_container_width=True, icon="📥"):
                with st.spinner("Téléchargement..."):
                    try:
                        if force_download_latest_report(dm):
                            st.success("Rapport téléchargé et extrait !")
                            dm.reload()
                            st.rerun()
                        else:
                            st.error("Échec du téléchargement.")
                    except Exception as e:
                        st.error(f"Erreur: {e}")

        if st.session_state.last_update_check:
            st.caption(
                f"Dernière vérif: {st.session_state.last_update_check.strftime('%d/%m/%Y %H:%M')}"
            )

    else:
        st.warning(
            "Aucune donnée. Cliquez sur 'Forcer mise à jour PDF' pour télécharger le dernier rapport."
        )
        if st.button("Forcer mise à jour PDF", icon="📥"):
            with st.spinner("Téléchargement..."):
                try:
                    if force_download_latest_report(dm):
                        dm.reload()
                        st.success("Rapport téléchargé ! Redémarrage...")
                        st.rerun()
                    else:
                        st.error("Échec.")
                except Exception as e:
                    st.error(f"Erreur: {e}")

        st.session_state.filters = {
            "start_date": None,
            "end_date": None,
            "categories": [],
            "fraud_types": [],
            "origins": [],
        }

pg.run()
