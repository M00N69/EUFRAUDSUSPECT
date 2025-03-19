import streamlit as st
import pandas as pd
import os
import sqlite3
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

from data_manager import DataManager
from visualizations import create_fraud_by_category_chart, create_fraud_by_type_chart
from pdf_processor import check_for_new_report
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
        new_report_added = check_for_new_report(st.session_state.data_manager)
        if new_report_added:
            st.success("Nouveau rapport ajouté à la base de données!")
            # Rechargement des données
            st.session_state.data_manager.load_data()
        else:
            st.info("Aucun nouveau rapport disponible.")
        st.session_state.last_update_check = datetime.now()

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
    start_date, end_date = st.select_slider(
        "Période d'analyse",
        options=all_dates,
        value=(all_dates[0], all_dates[-1])
    )
    
    # Sélection des catégories de produits
    all_categories = st.session_state.data_manager.get_product_categories()
    selected_categories = st.multiselect(
        "Catégories de produits",
        options=all_categories,
        default=all_categories[:5]  # Par défaut, les 5 premières catégories
    )
    
    # Sélection des types de fraude
    all_fraud_types = st.session_state.data_manager.get_fraud_types()
    selected_fraud_types = st.multiselect(
        "Types de fraude",
        options=all_fraud_types,
        default=all_fraud_types  # Par défaut, tous les types
    )
    
    st.markdown("---")
    
    # Section analyse IA
    st.subheader("Analyse IA (Mistral)")
    api_key = st.text_input("Clé API Mistral", type="password")
    ai_query = st.text_area("Question pour l'analyse", placeholder="Ex: Quelles sont les tendances récentes des fraudes dans la catégorie 'fruits et légumes'?")
    run_ai_analysis = st.button("Exécuter l'analyse IA")

# Vérification automatique des mises à jour au lancement
if st.session_state.last_update_check is None:
    check_updates()

# Corps principal de l'application
st.title("📊 Tableau de bord des fraudes alimentaires dans l'UE")

# Filtrage des données selon les sélections
filtered_data = st.session_state.data_manager.filter_data(
    start_date=start_date,
    end_date=end_date,
    categories=selected_categories,
    fraud_types=selected_fraud_types
)

# Affichage des KPIs
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_suspicions = filtered_data['total_suspicions'].sum() if 'total_suspicions' in filtered_data.columns else len(filtered_data)
    st.metric("Total des suspicions", f"{total_suspicions}")

with col2:
    total_countries = filtered_data['origin'].nunique() if 'origin' in filtered_data.columns else 0
    st.metric("Pays d'origine concernés", f"{total_countries}")

with col3:
    top_category = filtered_data['product_category'].value_counts().idxmax() if 'product_category' in filtered_data.columns else "N/A"
    st.metric("Catégorie la plus signalée", top_category)

with col4:
    top_fraud = filtered_data['fraud_type'].value_counts().idxmax() if 'fraud_type' in filtered_data.columns else "N/A" 
    st.metric("Type de fraude le plus fréquent", top_fraud)

# Graphiques principaux
st.subheader("Répartition des suspicions par catégorie de produit")
fig_category = create_fraud_by_category_chart(filtered_data)
st.plotly_chart(fig_category, use_container_width=True)

st.subheader("Répartition par type de fraude")
fig_fraud_type = create_fraud_by_type_chart(filtered_data)
st.plotly_chart(fig_fraud_type, use_container_width=True)

# Carte des pays d'origine
if 'origin' in filtered_data.columns:
    st.subheader("Distribution géographique des origines")
    country_counts = filtered_data['origin'].value_counts().reset_index()
    country_counts.columns = ['country', 'count']
    
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

# Tendances temporelles
if 'date' in filtered_data.columns:
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
st.dataframe(filtered_data, use_container_width=True)

# Section analyse IA
if run_ai_analysis and api_key:
    st.subheader("Résultats de l'analyse IA")
    with st.spinner("Analyse en cours..."):
        ai_result = analyze_with_mistral(api_key, ai_query, filtered_data)
        st.markdown(ai_result)
elif run_ai_analysis and not api_key:
    st.error("Veuillez entrer une clé API Mistral pour utiliser la fonctionnalité d'analyse IA.")

# Footer
st.markdown("---")
st.markdown("Source des données: [Commission Européenne - Rapports mensuels sur les suspicions de fraude agroalimentaire](https://food.ec.europa.eu/food-safety/acn/ffn-monthly_en)")
st.markdown("Application mise à jour automatiquement à chaque nouveau rapport mensuel")
