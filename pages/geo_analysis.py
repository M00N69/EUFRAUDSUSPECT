import streamlit as st
from visualizations import (
    create_country_choropleth,
    create_origin_notifier_heatmap,
    create_fraud_by_category_chart,
)

dm = st.session_state.data_manager
filters = st.session_state.get("filters", {})

st.title("Analyse géographique")

filtered_data = dm.filter_data(
    start_date=filters.get("start_date"),
    end_date=filters.get("end_date"),
    categories=filters.get("categories"),
    fraud_types=filters.get("fraud_types"),
    origins=filters.get("origins"),
)

if filtered_data.empty:
    st.warning("Aucune donnée avec les filtres actuels.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["Carte mondiale", "Heatmap", "Top pays"])

with tab1:
    st.subheader("Distribution géographique des suspicions")
    fig_map = create_country_choropleth(filtered_data)
    st.plotly_chart(fig_map, use_container_width=True)

    if "origin" in filtered_data.columns:
        country_counts = filtered_data["origin"].value_counts().reset_index()
        country_counts.columns = ["Pays", "Nombre"]
        st.dataframe(country_counts, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Relations pays d'origine / pays notifiant")
    fig_heat = create_origin_notifier_heatmap(filtered_data)
    st.plotly_chart(fig_heat, use_container_width=True)

with tab3:
    st.subheader("Suspicions par pays et catégorie")
    if (
        "origin" in filtered_data.columns
        and "product_category" in filtered_data.columns
    ):
        top_n = st.slider("Nombre de pays à afficher", 5, 25, 10)
        top_countries = filtered_data["origin"].value_counts().head(top_n).index
        filtered_by_country = filtered_data[filtered_data["origin"].isin(top_countries)]
        fig = create_fraud_by_category_chart(filtered_by_country)
        st.plotly_chart(fig, use_container_width=True)
