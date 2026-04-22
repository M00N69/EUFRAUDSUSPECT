import streamlit as st
import pandas as pd

dm = st.session_state.data_manager
filters = st.session_state.get("filters", {})

st.title("Détails des suspicions")

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

display_cols = [
    c
    for c in [
        "source_id",
        "product_category",
        "commodity",
        "issue",
        "origin",
        "fraud_type",
        "date",
        "link_source",
    ]
    if c in filtered_data.columns
]

col1, col2 = st.columns([3, 1])
with col1:
    st.caption(f"{len(filtered_data)} suspicions affichées sur {len(dm.data)} totales")
with col2:
    csv = filtered_data[display_cols].to_csv(index=False).encode("utf-8")
    st.download_button("Exporter CSV", csv, "fraudes_detail.csv", "text/csv")

st.dataframe(
    filtered_data[display_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "source_id": st.column_config.TextColumn("ID", width="small"),
        "product_category": st.column_config.TextColumn("Catégorie", width="medium"),
        "commodity": st.column_config.TextColumn("Produit", width="medium"),
        "issue": st.column_config.TextColumn("Problème", width="large"),
        "origin": st.column_config.TextColumn("Pays", width="small"),
        "fraud_type": st.column_config.TextColumn("Type fraude", width="medium"),
        "date": st.column_config.TextColumn("Période", width="small"),
        "link_source": st.column_config.LinkColumn("Source", width="small"),
    }
    if "link_source" in display_cols
    else None,
)

if st.checkbox("Afficher les statistiques détaillées"):
    tab1, tab2, tab3 = st.tabs(["Par catégorie", "Par pays", "Par type"])

    with tab1:
        if "product_category" in filtered_data.columns:
            cat_stats = filtered_data["product_category"].value_counts().reset_index()
            cat_stats.columns = ["Catégorie", "Nombre"]
            st.dataframe(cat_stats, use_container_width=True, hide_index=True)

    with tab2:
        if "origin" in filtered_data.columns:
            origin_stats = filtered_data["origin"].value_counts().reset_index()
            origin_stats.columns = ["Pays", "Nombre"]
            st.dataframe(origin_stats, use_container_width=True, hide_index=True)

    with tab3:
        if "fraud_type" in filtered_data.columns:
            fraud_stats = filtered_data["fraud_type"].value_counts().reset_index()
            fraud_stats.columns = ["Type de fraude", "Nombre"]
            st.dataframe(fraud_stats, use_container_width=True, hide_index=True)
