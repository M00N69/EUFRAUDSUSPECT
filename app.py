import streamlit as st
import pandas as pd
import os
import sqlite3
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

from data_manager import DataManager
from visualizations import create_fraud_by_category_chart, create_fraud_by_type_chart
from pdf_processor import check_for_new_report, force_download_latest_report
from ai_analyzer import analyze_with_mistral

# Configuration de la page
st.set_page_config(
    page_title="Surveillance des fraudes alimentaires UE",
    page_icon="🍲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisation de la session state
if 'data_manager' not in st.session_state:
    st.session_state.data_manager = DataManager()
if 'last_update_check' not in st.session_state:
    st.session_state.last_update_check = None

# Fonction pour vérifier les mises à jour
def check_updates():
    with st.spinner("Vérification des nouveaux rapports..."):
        try:
            new_report_added = check_for_new_report(st.session_state.data_manager)
            if new_report_added:
                st.success("Nouveau rapport ajouté à la base de données!")
                # Rechargement des données
                st.session_state.data_manager.load_data()
            else:
                st.info("Aucun nouveau rapport disponible.")
            st.session_state.last_update_check = datetime.now()
        except Exception as e:
            st.error(f"Erreur lors de la vérification: {str(e)}")

# Sidebar avec les contrôles
with st.sidebar:
    st.title("🧪 Surveillance des fraudes alimentaires UE")
    
    # Bouton de mise à jour manuelle
    if st.button("Vérifier les nouveaux rapports"):
        check_updates()
    
    # Affichage de la dernière mise à jour
    if st.session_state.last_update_check:
        st.write(f"Dernière vérification: {st.session_state.last_update_check.strftime('%d/%m/%Y %H:%M')}")
    
    st.markdown("---")
    
    # Filtres
    st.subheader("Filtres")
    
    # Sélection de la période
    all_dates = st.session_state.data_manager.get_available_dates()
    
    # Vérifier si nous avons des dates disponibles
    if len(all_dates) > 1:  # Besoin d'au moins 2 dates pour le slider
        start_date, end_date = st.select_slider(
            "Période d'analyse",
            options=all_dates,
            value=(all_dates[0], all_dates[-1])
        )
    elif len(all_dates) == 1:
        st.write(f"Période disponible: {all_dates[0]}")
        start_date = end_date = all_dates[0]
    else:
        st.write("Aucune période disponible. Veuillez télécharger des rapports.")
        start_date = end_date = None
    
    # Sélection des catégories de produits
    all_categories = st.session_state.data_manager.get_product_categories()
    if len(all_categories) > 0:
        selected_categories = st.multiselect(
            "Catégories de produits",
            options=all_categories,
            default=all_categories[:min(5, len(all_categories))]  # Par défaut, les 5 premières catégories ou moins
        )
    else:
        selected_categories = []
        st.write("Aucune catégorie disponible.")
    
    # Sélection des types de fraude
    all_fraud_types = st.session_state.data_manager.get_fraud_types()
    if len(all_fraud_types) > 0:
        selected_fraud_types = st.multiselect(
            "Types de fraude",
            options=all_fraud_types,
            default=all_fraud_types  # Par défaut, tous les types
        )
    else:
        selected_fraud_types = []
        st.write("Aucun type de fraude disponible.")
    
    st.markdown("---")
    
    # Section analyse IA
    st.subheader("Analyse IA (Mistral)")
    api_key = st.text_input("Clé API Mistral", type="password")
    ai_query = st.text_area("Question pour l'analyse", placeholder="Ex: Quelles sont les tendances récentes des fraudes dans la catégorie 'fruits et légumes'?")
    run_ai_analysis = st.button("Exécuter l'analyse IA")

# Vérification automatique des mises à jour au lancement
if st.session_state.last_update_check is None:
    check_updates()

# Vérifier si des données existent
has_data = not (st.session_state.data_manager.data is None or st.session_state.data_manager.data.empty)

if not has_data:
    st.info("Aucune donnée n'est encore disponible. Veuillez lancer une vérification pour télécharger le dernier rapport.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Télécharger le rapport le plus récent"):
            check_updates()
    with col2:
        if st.button("Forcer le téléchargement (ignorer les vérifications)"):
            with st.spinner("Téléchargement forcé en cours..."):
                success = force_download_latest_report(st.session_state.data_manager)
                if success:
                    st.success("Rapport téléchargé et ajouté avec succès! Rechargez la page pour voir les données.")
                else:
                    st.error("Échec du téléchargement forcé.")
    
    # Afficher les détails techniques pour le débogage
    if st.checkbox("Afficher les détails techniques"):
        st.write("Informations sur la base de données :")
        db_info = {}
        db_info["Chemin de la base"] = st.session_state.data_manager.db_path
        db_info["Base existe"] = os.path.exists(st.session_state.data_manager.db_path)
        
        if os.path.exists(st.session_state.data_manager.db_path):
            try:
                conn = sqlite3.connect(st.session_state.data_manager.db_path)
                c = conn.cursor()
                
                c.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = c.fetchall()
                db_info["Tables"] = [t[0] for t in tables]
                
                for table in db_info["Tables"]:
                    c.execute(f"SELECT COUNT(*) FROM {table}")
                    count = c.fetchone()[0]
                    db_info[f"Nombre d'enregistrements dans {table}"] = count
                
                conn.close()
            except Exception as e:
                db_info["Erreur d'accès à la base"] = str(e)
        
        st.json(db_info)
    
    # Afficher un message d'attente et arrêter l'exécution du reste de l'application
    st.stop()

# Corps principal de l'application
st.title("📊 Tableau de bord des fraudes alimentaires dans l'UE")

# Filtrage des données selon les sélections
filtered_data = st.session_state.data_manager.filter_data(
    start_date=start_date,
    end_date=end_date,
    categories=selected_categories,
    fraud_types=selected_fraud_types
)

# Vérifier si nous avons des données filtrées
if filtered_data.empty:
    st.warning("Aucune donnée disponible avec les filtres actuels. Essayez de modifier vos filtres.")
    st.stop()

# Affichage des KPIs
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_suspicions = filtered_data['total_suspicions'].sum() if 'total_suspicions' in filtered_data.columns else 0
    st.metric("Total des suspicions", f"{total_suspicions}")

with col2:
    total_countries = filtered_data['origin'].nunique() if 'origin' in filtered_data.columns else 0
    st.metric("Pays d'origine concernés", f"{total_countries}")

with col3:
    top_category = filtered_data['product_category'].value_counts().idxmax() if 'product_category' in filtered_data.columns and not filtered_data['product_category'].empty else "N/A"
    st.metric("Catégorie la plus signalée", top_category)

with col4:
    top_fraud = filtered_data['fraud_type'].value_counts().idxmax() if 'fraud_type' in filtered_data.columns and not filtered_data['fraud_type'].empty else "N/A" 
    st.metric("Type de fraude le plus fréquent", top_fraud)

# Graphiques principaux
st.subheader("Répartition des suspicions par catégorie de produit")
fig_category = create_fraud_by_category_chart(filtered_data)
st.plotly_chart(fig_category, use_container_width=True)

st.subheader("Répartition par type de fraude")
fig_fraud_type = create_fraud_by_type_chart(filtered_data)
st.plotly_chart(fig_fraud_type, use_container_width=True)

# Carte des pays d'origine
if 'origin' in filtered_data.columns and not filtered_data['origin'].empty:
    st.subheader("Distribution géographique des origines")
    country_counts = filtered_data['origin'].value_counts().reset_index()
    country_counts.columns = ['country', 'count']
    
    try:
        fig_map = px.choropleth(
            country_counts, 
            locations="country",
            locationmode="country names",
            color="count", 
            hover_name="country",
            color_continuous_scale=px.colors.sequential.Plasma,
            title="Nombre de suspicions par pays d'origine"
        )
        st.plotly_chart(fig_map, use_container_width=True)
    except Exception as e:
        st.warning(f"Impossible de créer la carte géographique. Certains noms de pays peuvent être non reconnus.")

# Tendances temporelles
if 'date' in filtered_data.columns and len(filtered_data['date'].unique()) > 1:
    st.subheader("Évolution des suspicions dans le temps")
    time_trend = filtered_data.groupby('date').size().reset_index(name='count')
    
    fig_trend = px.line(
        time_trend, 
        x='date', 
        y='count',
        title="Évolution du nombre de suspicions au fil du temps",
        labels={'count': 'Nombre de suspicions', 'date': 'Date'}
    )
    st.plotly_chart(fig_trend, use_container_width=True)

# Section Tableau détaillé
st.subheader("Détails des suspicions")
# Sélection des colonnes pertinentes pour l'affichage
display_columns = ['product_category', 'commodity', 'issue', 'origin', 'notified_by', 'fraud_type', 'date']
display_data = filtered_data[display_columns] if all(col in filtered_data.columns for col in display_columns) else filtered_data
st.dataframe(display_data, use_container_width=True)

# Section analyse IA
if run_ai_analysis:
    st.subheader("Résultats de l'analyse IA")
    if api_key:
        with st.spinner("Analyse en cours..."):
            ai_result = analyze_with_mistral(api_key, ai_query, filtered_data)
            st.markdown(ai_result)
    else:
        st.error("Veuillez entrer une clé API Mistral pour utiliser la fonctionnalité d'analyse IA.")

# Footer
st.markdown("---")
st.markdown("Source des données: [Commission Européenne - Rapports mensuels sur les suspicions de fraude agroalimentaire](https://food.ec.europa.eu/food-safety/acn/ffn-monthly_en)")
st.markdown("Application mise à jour automatiquement à chaque nouveau rapport mensuel")
