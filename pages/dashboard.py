import streamlit as st
import pandas as pd
from plotly import graph_objects as go
from visualizations import (
    create_fraud_by_category_chart,
    create_fraud_by_type_chart,
    create_country_choropleth,
    create_fraud_category_chart,
    create_timeline_chart,
)
from utils import format_date_display

st.set_page_config(layout="wide", page_title="Tableau de bord - EUFRAUDSUSPECT")

dm = st.session_state.data_manager
filters = st.session_state.get("filters", {})

filtered = dm.filter_data(
    start_date=filters.get("start_date"),
    end_date=filters.get("end_date"),
    categories=filters.get("categories"),
    fraud_types=filters.get("fraud_types"),
    origins=filters.get("origins"),
)

all_data = dm.data

st.markdown(
    """
<style>
    .kpi-card {
        background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 16px;
        padding: 1.5rem 1rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border: 1px solid #eaeaea;
        text-align: center;
        transition: transform 0.2s;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.12);
    }
    .kpi-label {
        font-size: 0.75rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.5rem;
    }
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: #d32f2f;
        margin: 0;
    }
    .kpi-sub {
        font-size: 0.7rem;
        color: #999;
        margin-top: 0.3rem;
    }
    .section-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    .section-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #212121;
        border-left: 4px solid #d32f2f;
        padding-left: 0.75rem;
        margin: 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("Tableau de bord")
st.caption("Surveillance des fraudes alimentaires dans l'UE")

col1, col2, col3, col4 = st.columns(4, gap="medium")

with col1:
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="kpi-label">Total suspicions</div>
        <div class="kpi-value">{len(all_data):,}</div>
        <div class="kpi-sub">base complete</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with col2:
    n_countries = all_data["origin"].nunique() if "origin" in all_data.columns else 0
    top_country = (
        all_data["origin"].value_counts().idxmax()
        if "origin" in all_data.columns and not all_data["origin"].empty
        else "N/A"
    )
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="kpi-label">Pays d'origine</div>
        <div class="kpi-value">{n_countries}</div>
        <div class="kpi-sub">#1: {top_country}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with col3:
    n_cats = (
        all_data["product_category"].nunique()
        if "product_category" in all_data.columns
        else 0
    )
    top_cat = (
        all_data["product_category"].value_counts().idxmax()
        if "product_category" in all_data.columns
        and not all_data["product_category"].empty
        else "N/A"
    )
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="kpi-label">Categories</div>
        <div class="kpi-value" style="font-size:1.6rem">{top_cat[:25]}</div>
        <div class="kpi-sub">{n_cats} uniques</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with col4:
    n_fraud = (
        all_data["fraud_type"].nunique() if "fraud_type" in all_data.columns else 0
    )
    top_fraud = (
        all_data["fraud_type"].value_counts().idxmax()
        if "fraud_type" in all_data.columns and not all_data["fraud_type"].empty
        else "N/A"
    )
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="kpi-label">Type de fraude</div>
        <div class="kpi-value" style="font-size:1.6rem">{top_fraud[:25]}</div>
        <div class="kpi-sub">{n_fraud} types</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

if "date" in all_data.columns:
    dates_sorted = sorted(all_data["date"].dropna().unique())
    if len(dates_sorted) > 0:
        st.caption(
            f"Periode: {dates_sorted[0]} → {dates_sorted[-1]}  |  Filtres dans la sidebar"
        )

st.divider()

if filtered.empty:
    st.warning(
        "Aucune donnee avec les filtres actuels. Modifiez les filtres dans la sidebar."
    )
    st.stop()

tab_kpi, tab_geo, tab_trends = st.tabs(
    ["Vue d'ensemble", "Carte mondiale", "Tendances"]
)

with tab_kpi:
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(
            '<div class="section-title">Top 15 categories</div>', unsafe_allow_html=True
        )
        fig_cat = create_fraud_by_category_chart(filtered, max_categories=15)
        st.plotly_chart(fig_cat, use_container_width=True, height=480)
    with col_b:
        st.markdown(
            '<div class="section-title">Repartition par type</div>',
            unsafe_allow_html=True,
        )
        fig_type = create_fraud_by_type_chart(filtered)
        st.plotly_chart(fig_type, use_container_width=True, height=480)

    st.markdown(
        '<div class="section-title">Categorisation des fraudes</div>',
        unsafe_allow_html=True,
    )
    fig_categ = create_fraud_category_chart(filtered)
    st.plotly_chart(fig_categ, use_container_width=True)

with tab_geo:
    st.markdown(
        '<div class="section-title">Carte des origines</div>', unsafe_allow_html=True
    )
    fig_map = create_country_choropleth(filtered)
    st.plotly_chart(fig_map, use_container_width=True, height=600)

    if "origin" in filtered.columns:
        top20 = filtered["origin"].value_counts().head(20).reset_index()
        top20.columns = ["Pays", "Suspicions"]
        st.markdown(
            '<div class="section-title">Top 20 pays</div>', unsafe_allow_html=True
        )
        st.bar_chart(top20.set_index("Pays"), color="#d32f2f", height=350)

with tab_trends:
    st.markdown(
        '<div class="section-title">Evolution mensuelle</div>', unsafe_allow_html=True
    )
    fig_time = create_timeline_chart(filtered)
    st.plotly_chart(fig_time, use_container_width=True, height=400)

    if "fraud_type" in filtered.columns:
        st.markdown(
            '<div class="section-title">Types de fraude dans le temps</div>',
            unsafe_allow_html=True,
        )
        fig_time_type = create_timeline_by_fraud_type(filtered)
        st.plotly_chart(fig_time_type, use_container_width=True, height=400)

st.divider()
st.subheader("Statistiques completes")

display_cols = [
    "date",
    "origin",
    "product_category",
    "commodity",
    "fraud_type",
    "issue",
]
avail = [c for c in display_cols if c in filtered.columns]

col_stat1, col_stat2 = st.columns(2)
with col_stat1:
    st.caption(f"{len(filtered)} suspicions filtree")
with col_stat2:
    csv = filtered[avail].to_csv(index=False).encode("utf-8")
    st.download_button(
        "Exporter CSV", csv, "fraudes.csv", "text/csv", icon=":material/save:"
    )

st.dataframe(
    filtered[avail].head(100),
    use_container_width=True,
    hide_index=True,
    height=400,
    column_config={
        "date": st.column_config.TextColumn("Periode", width="small"),
        "origin": st.column_config.TextColumn("Pays", width="small"),
        "product_category": st.column_config.TextColumn("Categorie", width="medium"),
        "commodity": st.column_config.TextColumn("Produit", width="small"),
        "fraud_type": st.column_config.TextColumn("Type", width="medium"),
        "issue": st.column_config.TextColumn("Description", width="large"),
    },
)
