import streamlit as st
import pandas as pd
from utils import format_date_display, get_country_code

dm = st.session_state.data_manager
filters = st.session_state.get("filters", {})

st.title("Details des suspicions")
st.caption(f"{len(dm.data)} suspicions dans la base  |  Filtrez dans la barre laterale")

filtered_data = dm.filter_data(
    start_date=filters.get("start_date"),
    end_date=filters.get("end_date"),
    categories=filters.get("categories"),
    fraud_types=filters.get("fraud_types"),
    origins=filters.get("origins"),
)

if filtered_data.empty:
    st.warning("Aucune donnee avec les filtres actuels.")
    st.stop()

show_cols = ["date", "origin", "product_category", "commodity", "fraud_type", "issue"]
available = [c for c in show_cols if c in filtered_data.columns]

col_btn, col_cnt, col_top = st.columns([3, 1, 1])
with col_cnt:
    st.caption(f"{len(filtered_data)} suspicions")
with col_top:
    if "date" in available:
        top_date = filtered_data["date"].value_counts().idxmax()
        st.caption(
            f"Max: {top_date} ({filtered_data['date'].value_counts().max()} cas)"
        )

with col_btn:
    csv_data = filtered_data[available].to_csv(index=False).encode("utf-8")
    st.download_button(
        "Exporter CSV",
        csv_data,
        "suspicions_detail.csv",
        "text/csv",
        use_container_width=True,
        icon="💾",
    )

if "date" in filtered_data.columns:
    date_stats = filtered_data.groupby("date").size().reset_index(name="cas")
    date_stats = date_stats.sort_values("date")
    date_stats["cumul"] = date_stats["cas"].cumsum()
    top_5_dates = date_stats.tail(5)
    st.bar_chart(
        top_5_dates.set_index("date")["cas"],
        horizontal=False,
        color="#d32f2f",
    )
    st.caption("5 dernieres periodes")

col1, col2 = st.columns([3, 1])

with col1:
    sel = st.dataframe(
        filtered_data[available],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode=["single-row"],
        height=500,
        column_config={
            "date": st.column_config.TextColumn(
                "Periode",
                width="small",
            ),
            "origin": st.column_config.TextColumn(
                "Pays",
                width="small",
            ),
            "product_category": st.column_config.TextColumn(
                "Categorie",
                width="medium",
            ),
            "commodity": st.column_config.TextColumn(
                "Produit",
                width="small",
            ),
            "fraud_type": st.column_config.TextColumn(
                "Type de fraude",
                width="medium",
            ),
            "issue": st.column_config.TextColumn(
                "Description",
                width="large",
            ),
        },
    )

with col2:
    if sel and sel["selection"]["selected_rows"]:
        row = sel["selection"]["selected_rows"][0]
        idx = row["_row"]
        full_row = filtered_data.iloc[idx]

        st.markdown("### Details")
        if "origin" in full_row.index:
            code = get_country_code(str(full_row["origin"]))
            st.metric(
                "Pays", f"{full_row['origin']} ({code})" if code else full_row["origin"]
            )
        if "product_category" in full_row.index:
            st.metric("Categorie", full_row["product_category"])
        if "commodity" in full_row.index:
            st.metric("Produit", full_row["commodity"])
        if "fraud_type" in full_row.index:
            st.metric("Type", full_row["fraud_type"])
        if "issue" in full_row.index:
            with st.expander("Description"):
                st.text(full_row["issue"])
        if "link_source" in filtered_data.columns:
            link = full_row.get("link_source", "")
            if link and str(link).startswith("http"):
                st.link_button("Voir la source", link, use_container_width=True)

if "product_category" in filtered_data.columns:
    with st.expander("Top categories par pays"):
        top_n = st.slider("Nombre de pays", 5, 30, 10)
        top_countries = filtered_data["origin"].value_counts().head(top_n).index
        sub = filtered_data[filtered_data["origin"].isin(top_countries)]
        pivot = pd.crosstab(sub["origin"], sub["product_category"])
        st.dataframe(pivot, use_container_width=True)

st.divider()
st.subheader("Statistiques")

tab_cat, tab_pays, tab_fraud = st.tabs(["Categorie", "Pays", "Type de fraude"])

with tab_cat:
    if "product_category" in filtered_data.columns:
        cats = filtered_data["product_category"].value_counts().reset_index()
        cats.columns = ["Categorie", "Nombre"]
        st.dataframe(cats, use_container_width=True, hide_index=True, height=400)

with tab_pays:
    if "origin" in filtered_data.columns:
        origins = filtered_data["origin"].value_counts().reset_index()
        origins.columns = ["Pays", "Nombre"]
        st.dataframe(origins, use_container_width=True, hide_index=True, height=400)

with tab_fraud:
    if "fraud_type" in filtered_data.columns:
        frauds = filtered_data["fraud_type"].value_counts().reset_index()
        frauds.columns = ["Type de fraude", "Nombre"]
        st.dataframe(frauds, use_container_width=True, hide_index=True, height=400)
