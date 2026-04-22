import streamlit as st
import pandas as pd
from visualizations import (
    create_fraud_by_category_chart,
    create_fraud_by_type_chart,
    create_country_choropleth,
    create_fraud_category_chart,
)
from utils import format_date_display

st.set_page_config(layout="wide")

dm = st.session_state.data_manager
filters = st.session_state.get("filters", {})

filtered_data = dm.filter_data(
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
    .eu-header {
        background: linear-gradient(135deg, #b71c1c 0%, #d32f2f 50%, #c62828 100%);
        padding: 2rem 2rem 1.5rem;
        border-radius: 0 0 16px 16px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .eu-header h1 {
        margin: 0 0 0.25rem;
        font-size: 1.8rem;
        font-weight: 700;
    }
    .eu-header p {
        margin: 0;
        opacity: 0.85;
        font-size: 0.95rem;
    }
    .kpi-card {
        background: white;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        border: 1px solid #f0f0f0;
        text-align: center;
    }
    .kpi-card .label {
        font-size: 0.75rem;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.4rem;
    }
    .kpi-card .value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #b71c1c;
    }
    .kpi-card .sub {
        font-size: 0.72rem;
        color: #aaa;
        margin-top: 0.25rem;
    }
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #212121;
        margin-bottom: 0.75rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #d32f2f;
        display: inline-block;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        font-weight: 500;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="eu-header">
    <h1>EUFRAUDSUSPECT</h1>
    <p>Surveillance des fraudes alimentaires dans l'Union Europeenne</p>
</div>
""",
    unsafe_allow_html=True,
)

col1, col2, col3, col4 = st.columns([1, 1, 1, 1], gap="small")

top_cat_label = ""
top_cat_count = 0
top_fraud_label = ""
top_fraud_count = 0
top_country = ""

if all_data is not None and not all_data.empty:
    total = len(all_data)
    nb_countries = all_data["origin"].nunique()
    nb_categories = all_data["product_category"].nunique()
    nb_fraud_types = all_data["fraud_type"].nunique()
    nb_dates = (
        len(all_data["date"].dropna().unique()) if "date" in all_data.columns else 0
    )
    date_range = (
        f"{all_data['date'].min()} - {all_data['date'].max()}"
        if "date" in all_data.columns and nb_dates > 0
        else ""
    )

    cat_counts = all_data["product_category"].value_counts()
    top_cat_label = cat_counts.index[0] if len(cat_counts) > 0 else "N/A"
    top_cat_count = int(cat_counts.iloc[0]) if len(cat_counts) > 0 else 0

    fraud_counts = all_data["fraud_type"].value_counts()
    top_fraud_label = fraud_counts.index[0] if len(fraud_counts) > 0 else "N/A"
    top_fraud_count = int(fraud_counts.iloc[0]) if len(fraud_counts) > 0 else 0

    country_counts = all_data["origin"].value_counts()
    top_country = country_counts.index[0] if len(country_counts) > 0 else "N/A"
else:
    total = nb_countries = nb_categories = nb_fraud_types = 0
    date_range = ""
    top_cat_label = top_fraud_label = top_country = "N/A"
    top_cat_count = top_fraud_count = 0

with col1:
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="label">Total suspicions</div>
        <div class="value">{total:,}</div>
        <div class="sub">sur {nb_dates} periode{"s" if nb_dates != 1 else ""}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="label">Pays concernes</div>
        <div class="value">{nb_countries}</div>
        <div class="sub">#1: {top_country}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="label">Categorie principale</div>
        <div class="value" style="font-size:1.1rem">{top_cat_label[:30]}</div>
        <div class="sub">{top_cat_count} signalements</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="label">Type de fraude dominant</div>
        <div class="value" style="font-size:1.1rem">{top_fraud_label[:30]}</div>
        <div class="sub">{top_fraud_count} cas</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

if date_range:
    st.caption(
        f"Periode couverte: {date_range}  |  Filtrez les donnees dans la barre laterale"
    )

st.divider()

if filtered_data.empty:
    st.warning(
        "Aucune donnee avec les filtres actuels. Modifiez vos filtres dans la barre laterale."
    )
    st.stop()

st.markdown(
    '<div class="section-title">Repartition par categorie de produit</div>',
    unsafe_allow_html=True,
)
fig_cat = create_fraud_by_category_chart(filtered_data)
st.plotly_chart(fig_cat, use_container_width=True, height=450)

tab_type, tab_map, tab_categ = st.tabs(
    ["Par type de fraude", "Carte mondiale", "Categorisation"]
)

with tab_type:
    fig_type = create_fraud_by_type_chart(filtered_data)
    st.plotly_chart(fig_type, use_container_width=True)

with tab_map:
    fig_map = create_country_choropleth(filtered_data)
    st.plotly_chart(fig_map, use_container_width=True)

with tab_categ:
    fig_categ = create_fraud_category_chart(filtered_data)
    st.plotly_chart(fig_categ, use_container_width=True)

st.divider()
st.subheader("Apercu des donnees")

display_cols = [
    "product_category",
    "commodity",
    "issue",
    "origin",
    "fraud_type",
    "date",
]
available_cols = [c for c in display_cols if c in filtered_data.columns]
col_btn, col_cnt = st.columns([4, 1])
with col_cnt:
    st.caption(f"{len(filtered_data)} suspicions")
with col_btn:
    csv_data = filtered_data[available_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        "Exporter CSV",
        csv_data,
        "fraudes_filtrees.csv",
        "text/csv",
        use_container_width=True,
    )

st.dataframe(
    filtered_data[available_cols].head(50),
    use_container_width=True,
    hide_index=True,
    height=350,
)
