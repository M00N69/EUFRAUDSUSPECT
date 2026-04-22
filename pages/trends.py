import streamlit as st
from visualizations import create_timeline_chart, create_timeline_by_fraud_type

dm = st.session_state.data_manager
filters = st.session_state.get("filters", {})

st.title("Tendances temporelles")

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

if (
    "date" not in filtered_data.columns
    or len(filtered_data["date"].dropna().unique()) < 2
):
    st.info("Pas assez de périodes pour afficher des tendances.")
    st.stop()

tab1, tab2 = st.tabs(["Évolution globale", "Par type de fraude"])

with tab1:
    fig = create_timeline_chart(filtered_data)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    fig = create_timeline_by_fraud_type(filtered_data)
    st.plotly_chart(fig, use_container_width=True)

with st.expander("Statistiques par période"):
    if "date" in filtered_data.columns:
        stats = (
            filtered_data.groupby("date")
            .agg(
                total=("date", "count"),
                pays_uniques=("origin", "nunique"),
                categories_uniques=("product_category", "nunique"),
            )
            .reset_index()
        )
        stats.columns = ["Période", "Nb suspicions", "Nb pays", "Nb catégories"]
        st.dataframe(stats, use_container_width=True, hide_index=True)

        csv = stats.to_csv(index=False).encode("utf-8")
        st.download_button("Exporter les stats", csv, "tendances_stats.csv", "text/csv")
