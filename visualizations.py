import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def create_fraud_by_category_chart(
    data: pd.DataFrame, max_categories: int = 20
) -> go.Figure:
    if data is None or data.empty or "product_category" not in data.columns:
        return go.Figure().update_layout(title="Données insuffisantes")
    if data["product_category"].isna().all():
        return go.Figure().update_layout(title="Aucune donnée de catégorie disponible")

    category_counts = (
        data["product_category"].value_counts().head(max_categories).reset_index()
    )
    category_counts.columns = ["category", "count"]
    category_counts = category_counts.sort_values("count", ascending=True)

    fig = px.bar(
        category_counts,
        y="category",
        x="count",
        orientation="h",
        title="Suspicions par catégorie de produit",
        labels={"count": "Nombre de suspicions", "category": ""},
        color="count",
        color_continuous_scale=px.colors.sequential.Blues,
    )
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        height=max(400, len(category_counts) * 28),
    )
    fig.update_coloraxes(showscale=False)
    return fig


def create_fraud_by_type_chart(data: pd.DataFrame) -> go.Figure:
    if data is None or data.empty or "fraud_type" not in data.columns:
        return go.Figure().update_layout(title="Données insuffisantes")
    if data["fraud_type"].isna().all():
        return go.Figure().update_layout(
            title="Aucune donnée de type de fraude disponible"
        )

    fraud_counts = data["fraud_type"].value_counts().reset_index()
    fraud_counts.columns = ["type", "count"]

    fig = px.pie(
        fraud_counts,
        values="count",
        names="type",
        title="Répartition par type de fraude",
        color_discrete_sequence=px.colors.sequential.Blues_r,
        hole=0.4,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(
        legend_title="Type de fraude",
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
    )
    return fig


def create_country_choropleth(data: pd.DataFrame) -> go.Figure:
    if data is None or data.empty or "origin" not in data.columns:
        return go.Figure().update_layout(title="Données insuffisantes")

    from utils import get_country_code

    country_counts = data["origin"].value_counts().reset_index()
    country_counts.columns = ["country", "count"]
    country_counts["iso_code"] = country_counts["country"].apply(get_country_code)
    country_counts = country_counts[country_counts["iso_code"] != ""]

    if country_counts.empty:
        return go.Figure().update_layout(
            title="Impossible de mapper les pays (codes ISO manquants)"
        )

    fig = px.choropleth(
        country_counts,
        locations="iso_code",
        color="count",
        hover_name="country",
        color_continuous_scale=px.colors.sequential.Plasma,
        title="Suspicions par pays d'origine",
    )
    fig.update_layout(
        geo=dict(showframe=False, showcoastlines=True, projection_type="natural earth")
    )
    return fig


def create_origin_notifier_heatmap(data: pd.DataFrame) -> go.Figure:
    if (
        data is None
        or data.empty
        or "origin" not in data.columns
        or "notified_by" not in data.columns
    ):
        return go.Figure().update_layout(title="Données insuffisantes")
    if data["origin"].isna().all() or data["notified_by"].isna().all():
        return go.Figure().update_layout(title="Données insuffisantes pour la heatmap")

    try:
        top_origins = data["origin"].value_counts().nlargest(15).index
        top_notifiers = data["notified_by"].value_counts().nlargest(10).index
        filtered = data[
            data["origin"].isin(top_origins) & data["notified_by"].isin(top_notifiers)
        ]

        if filtered.empty:
            return go.Figure().update_layout(title="Pas assez de données communes")

        heatmap_data = pd.crosstab(filtered["origin"], filtered["notified_by"])
        fig = px.imshow(
            heatmap_data,
            labels=dict(x="Pays notifiant", y="Pays d'origine", color="Nombre"),
            color_continuous_scale=px.colors.sequential.Blues,
            title="Relations pays d'origine / pays notifiant",
        )
        fig.update_layout(xaxis={"tickangle": 45}, height=600)
        return fig
    except Exception as e:
        return go.Figure().update_layout(title=f"Erreur: {e}")


def create_timeline_chart(data: pd.DataFrame) -> go.Figure:
    if data is None or data.empty or "date" not in data.columns:
        return go.Figure().update_layout(title="Données insuffisantes")
    if len(data["date"].dropna().unique()) < 2:
        return go.Figure().update_layout(title="Pas assez de périodes")

    time_data = data.groupby("date").size().reset_index(name="count")
    time_data = time_data.sort_values("date")

    fig = px.line(
        time_data,
        x="date",
        y="count",
        title="Évolution des suspicions dans le temps",
        labels={"count": "Nombre de suspicions", "date": "Période"},
        markers=True,
    )
    fig.update_traces(line=dict(width=3), marker=dict(size=8))
    fig.update_layout(xaxis_title="", yaxis_title="Nombre de suspicions")
    return fig


def create_timeline_by_fraud_type(data: pd.DataFrame) -> go.Figure:
    if (
        data is None
        or data.empty
        or "date" not in data.columns
        or "fraud_type" not in data.columns
    ):
        return go.Figure().update_layout(title="Données insuffisantes")
    if len(data["date"].dropna().unique()) < 2:
        return go.Figure().update_layout(title="Pas assez de périodes")

    time_data = data.groupby(["date", "fraud_type"]).size().reset_index(name="count")
    time_data = time_data.sort_values("date")

    fig = px.line(
        time_data,
        x="date",
        y="count",
        color="fraud_type",
        title="Évolution par type de fraude",
        labels={"count": "Nombre", "date": "Période", "fraud_type": "Type"},
        markers=True,
    )
    fig.update_layout(legend_title="Type de fraude")
    return fig


def create_fraud_category_chart(data: pd.DataFrame) -> go.Figure:
    if data is None or data.empty or "fraud_type" not in data.columns:
        return go.Figure().update_layout(title="Données insuffisantes")

    from utils import categorize_fraud_issue

    data_copy = data.copy()
    data_copy["fraud_category"] = data_copy["issue"].apply(categorize_fraud_issue)
    cat_counts = data_copy["fraud_category"].value_counts().reset_index()
    cat_counts.columns = ["category", "count"]

    fig = px.bar(
        cat_counts,
        x="category",
        y="count",
        title="Catégorisation des types de fraude",
        labels={"count": "Nombre", "category": ""},
        color="count",
        color_continuous_scale=px.colors.sequential.Teal,
    )
    fig.update_coloraxes(showscale=False)
    fig.update_layout(xaxis={"tickangle": 30})
    return fig
