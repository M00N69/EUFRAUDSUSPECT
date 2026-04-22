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
    st.session_state.data_manager = DataManager()
if "last_update_check" not in st.session_state:
    st.session_state.last_update_check = None
if "ai_conversation" not in st.session_state:
    st.session_state.ai_conversation = []

dashboard = st.Page("pages/dashboard.py", title="Tableau de bord", icon="📊")
geo = st.Page("pages/geo_analysis.py", title="Analyse géographique", icon="🗺️")
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
    st.title("🍲 EUFRAUDSUSPECT")
    st.caption("Surveillance des fraudes alimentaires dans l'UE")

    if st.button("Vérifier les nouveaux rapports", use_container_width=True):
        with st.spinner("Vérification..."):
            try:
                new = check_for_new_report(st.session_state.data_manager)
                if new:
                    st.success("Nouveau rapport ajouté !")
                    st.session_state.data_manager.reload()
                else:
                    st.info("Aucun nouveau rapport.")
                st.session_state.last_update_check = datetime.now()
            except Exception as e:
                st.error(f"Erreur: {e}")

    if st.session_state.last_update_check:
        st.caption(
            f"Dernière vérification: {st.session_state.last_update_check.strftime('%d/%m/%Y %H:%M')}"
        )

    dm = st.session_state.data_manager
    has_data = dm.data is not None and not dm.data.empty

    if has_data:
        st.divider()
        st.subheader("Filtres")

        all_dates = dm.get_available_dates()
        if len(all_dates) > 1:
            start_date, end_date = st.select_slider(
                "Période",
                options=all_dates,
                value=(all_dates[0], all_dates[-1]),
            )
        elif len(all_dates) == 1:
            start_date = end_date = all_dates[0]
            st.info(f"Période: {all_dates[0]}")
        else:
            start_date = end_date = None

        all_categories = dm.get_product_categories()
        if all_categories:
            selected_categories = st.multiselect(
                "Catégories de produits",
                all_categories,
                default=all_categories[: min(5, len(all_categories))],
            )
        else:
            selected_categories = []

        all_fraud_types = dm.get_fraud_types()
        if all_fraud_types:
            selected_fraud_types = st.multiselect(
                "Types de fraude",
                all_fraud_types,
                default=all_fraud_types,
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
            "start_date": start_date if has_data else None,
            "end_date": end_date if has_data else None,
            "categories": selected_categories if has_data else [],
            "fraud_types": selected_fraud_types if has_data else [],
            "origins": selected_origins if has_data else [],
        }
    else:
        st.warning(
            "Aucune donnée. Vérifiez les nouveaux rapports ou forcez le téléchargement."
        )
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Forcer le téléchargement"):
                with st.spinner("Téléchargement..."):
                    if force_download_latest_report(st.session_state.data_manager):
                        st.success("Rapport téléchargé ! Rechargement...")
                        st.rerun()
                    else:
                        st.error("Échec du téléchargement.")
        with col2:
            if st.button("Réinitialiser la base"):
                with st.spinner("Réinitialisation..."):
                    try:
                        st.session_state.data_manager.reset_database()
                        st.success("Base réinitialisée !")
                        st.rerun()
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
