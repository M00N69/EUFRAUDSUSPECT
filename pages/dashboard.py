import streamlit as st
import pandas as pd
from visualizations import (
    create_fraud_by_category_chart,
    create_fraud_by_type_chart,
    create_fraud_category_chart,
    create_timeline_chart,
)

dm = st.session_state.data_manager
filters = st.session_state.get("filters", {})

st.title("Tableau de bord")
st.caption("Surveillance des fraudes alimentaires dans l'Union Européenne")

filtered_data = dm.filter_data(
    start_date=filters.get("start_date"),
    end_date=filters.get("end_date"),
    categories=filters.get("categories"),
    fraud_types=filters.get("fraud_types"),
    origins=filters.get("origins"),
)

if filtered_data.empty:
    st.warning(
        "Aucune donnée avec les filtres actuels. Modifiez vos filtres dans la sidebar."
    )
    st.stop()

total = len(filtered_data)
nb_countries = (
    filtered_data["origin"].nunique() if "origin" in filtered_data.columns else 0
)
nb_categories = (
    filtered_data["product_category"].nunique()
    if "product_category" in filtered_data.columns
    else 0
)
nb_fraud_types = (
    filtered_data["fraud_type"].nunique()
    if "fraud_type" in filtered_data.columns
    else 0
)

col1, col2, col3, col4 = st.columns(4, gap="medium")
with col1:
    st.metric(
        "Suspicions",
        f"{total:,}",
        help="Nombre total de suspicions correspondant aux filtres",
    )
with col2:
    st.metric("Pays", f"{nb_countries}", help="Nombre de pays d'origine distincts")
with col3:
    st.metric("Catégories", f"{nb_categories}", help="Nombre de catégories de produits")
with col4:
    st.metric(
        "Types de fraude",
        f"{nb_fraud_types}",
        help="Nombre de types de fraude distincts",
    )

top_cat = (
    filtered_data["product_category"].value_counts().idxmax()
    if "product_category" in filtered_data.columns
    and not filtered_data["product_category"].empty
    else "N/A"
)
top_fraud = (
    filtered_data["fraud_type"].value_counts().idxmax()
    if "fraud_type" in filtered_data.columns and not filtered_data["fraud_type"].empty
    else "N/A"
)

col5, col6 = st.columns(2, gap="medium")
with col5:
    st.info(f"**Catégorie la plus signalée** : {top_cat}")
with col6:
    st.info(f"**Type de fraude le plus fréquent** : {top_fraud}")

st.divider()

tab1, tab2, tab3 = st.tabs(
    ["Par catégorie de produit", "Par type de fraude", "Catégorisation des fraudes"]
)

with tab1:
    fig_cat = create_fraud_by_category_chart(filtered_data)
    st.plotly_chart(fig_cat, use_container_width=True)

with tab2:
    col_pie, col_bar = st.columns([1, 1])
    with col_pie:
        fig_type = create_fraud_by_type_chart(filtered_data)
        st.plotly_chart(fig_type, use_container_width=True)
    with col_bar:
        fig_cattype = create_fraud_category_chart(filtered_data)
        st.plotly_chart(fig_cattype, use_container_width=True)

with tab3:
    if "fraud_type" in filtered_data.columns:
        from utils import categorize_fraud_issue

        ft_counts = filtered_data["fraud_type"].value_counts().head(15).reset_index()
        ft_counts.columns = ["Type de fraude", "Nombre"]
        st.dataframe(ft_counts, use_container_width=True, hide_index=True)

if "date" in filtered_data.columns and len(filtered_data["date"].dropna().unique()) > 1:
    st.subheader("Evolution dans le temps")
    fig_trend = create_timeline_chart(filtered_data)
    st.plotly_chart(fig_trend, use_container_width=True)

with st.expander("Apercu des donnees et export"):
    display_cols = [
        "product_category",
        "commodity",
        "issue",
        "origin",
        "fraud_type",
        "date",
        "link_source",
    ]
    available_cols = [c for c in display_cols if c in filtered_data.columns]

    col_export1, col_export2 = st.columns([3, 1])
    with col_export1:
        st.caption(f"{len(filtered_data)} suspicions affichees")
    with col_export2:
        csv = filtered_data[available_cols].to_csv(index=False).encode("utf-8")
        st.download_button(
            "Exporter CSV",
            csv,
            "fraudes_filtrees.csv",
            "text/csv",
            use_container_width=True,
        )

    st.dataframe(
        filtered_data[available_cols].head(100),
        use_container_width=True,
        hide_index=True,
        column_config={
            "link_source": st.column_config.LinkColumn("Source", width="small"),
        }
        if "link_source" in available_cols
        else None,
    )
