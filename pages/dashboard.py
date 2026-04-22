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

st.title("Tableau de bord des fraudes alimentaires dans l'UE")

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

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total suspicions", f"{len(filtered_data):,}")
with col2:
    if "origin" in filtered_data.columns:
        st.metric("Pays concernés", f"{filtered_data['origin'].nunique()}")
with col3:
    if (
        "product_category" in filtered_data.columns
        and not filtered_data["product_category"].empty
    ):
        top_cat = filtered_data["product_category"].value_counts().idxmax()
        st.metric("Catégorie #1", top_cat)
    else:
        st.metric("Catégorie #1", "N/A")
with col4:
    if "fraud_type" in filtered_data.columns and not filtered_data["fraud_type"].empty:
        top_fraud = filtered_data["fraud_type"].value_counts().idxmax()
        st.metric("Fraude #1", top_fraud)
    else:
        st.metric("Fraude #1", "N/A")

st.divider()

tab1, tab2, tab3 = st.tabs(["Par catégorie", "Par type de fraude", "Catégorisation"])

with tab1:
    fig_cat = create_fraud_by_category_chart(filtered_data)
    st.plotly_chart(fig_cat, use_container_width=True)

with tab2:
    fig_type = create_fraud_by_type_chart(filtered_data)
    st.plotly_chart(fig_type, use_container_width=True)

with tab3:
    fig_cattype = create_fraud_category_chart(filtered_data)
    st.plotly_chart(fig_cattype, use_container_width=True)

if "date" in filtered_data.columns and len(filtered_data["date"].dropna().unique()) > 1:
    st.subheader("Évolution dans le temps")
    fig_trend = create_timeline_chart(filtered_data)
    st.plotly_chart(fig_trend, use_container_width=True)

with st.expander("Aperçu des données"):
    display_cols = [
        "product_category",
        "commodity",
        "issue",
        "origin",
        "fraud_type",
        "date",
    ]
    available_cols = [c for c in display_cols if c in filtered_data.columns]
    st.dataframe(
        filtered_data[available_cols].head(50),
        use_container_width=True,
        hide_index=True,
    )

    csv = filtered_data[available_cols].to_csv(index=False).encode("utf-8")
    st.download_button("Exporter CSV", csv, "fraudes_filtrees.csv", "text/csv")
