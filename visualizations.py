import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def create_fraud_by_category_chart(data):
    """
    Crée un graphique de la distribution des suspicions par catégorie de produit
    """
    if data is None or data.empty or 'product_category' not in data.columns:
        # Retourner un graphique vide
        return go.Figure().update_layout(
            title="Données insuffisantes pour créer le graphique"
        )
    
    # Vérifier qu'il y a des valeurs non nulles
    if data['product_category'].isna().all():
        return go.Figure().update_layout(
            title="Aucune donnée de catégorie disponible"
        )
    
    # Compter les occurrences par catégorie
    category_counts = data['product_category'].value_counts().reset_index()
    category_counts.columns = ['category', 'count']
    
    # Trier par nombre de suspicions
    category_counts = category_counts.sort_values('count', ascending=False)
    
    # Créer le graphique à barres horizontales
    fig = px.bar(
        category_counts,
        y='category',
        x='count',
        orientation='h',
        title="Suspicions par catégorie de produit",
        labels={'count': 'Nombre de suspicions', 'category': 'Catégorie de produit'},
        color='count',
        color_continuous_scale=px.colors.sequential.Blues,
    )
    
    # Ajuster la mise en page
    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        xaxis_title="Nombre de suspicions",
        yaxis_title="",
        height=600
    )
    
    return fig

def create_fraud_by_type_chart(data):
    """
    Crée un graphique de la distribution des suspicions par type de fraude
    """
    if data is None or data.empty or 'fraud_type' not in data.columns:
        # Retourner un graphique vide
        return go.Figure().update_layout(
            title="Données insuffisantes pour créer le graphique"
        )
    
    # Vérifier qu'il y a des valeurs non nulles
    if data['fraud_type'].isna().all():
        return go.Figure().update_layout(
            title="Aucune donnée de type de fraude disponible"
        )
    
    # Compter les occurrences par type de fraude
    fraud_counts = data['fraud_type'].value_counts().reset_index()
    fraud_counts.columns = ['type', 'count']
    
    # Créer le graphique en secteurs (pie chart)
    fig = px.pie(
        fraud_counts,
        values='count',
        names='type',
        title="Répartition par type de fraude",
        color_discrete_sequence=px.colors.sequential.Blues_r,
        hole=0.4,
    )
    
    # Ajuster la mise en page
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(
        legend_title="Type de fraude",
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
    )
    
    return fig

def create_detection_source_chart(data):
    """
    Crée un graphique sur les sources de détection des fraudes
    """
    if data is None or data.empty or 'detection_source' not in data.columns:
        return go.Figure().update_layout(
            title="Données insuffisantes pour créer le graphique"
        )
    
    # Vérifier qu'il y a des valeurs non nulles
    if data['detection_source'].isna().all():
        return go.Figure().update_layout(
            title="Aucune donnée de source de détection disponible"
        )
    
    source_counts = data['detection_source'].value_counts().reset_index()
    source_counts.columns = ['source', 'count']
    
    fig = px.bar(
        source_counts,
        x='source',
        y='count',
        title="Sources de détection des fraudes",
        labels={'count': 'Nombre de détections', 'source': 'Source'},
        color='count',
        color_continuous_scale=px.colors.sequential.Teal,
    )
    
    return fig

def create_origin_notifier_heatmap(data):
    """
    Crée une heatmap des relations entre pays d'origine et pays notifiants
    """
    if data is None or data.empty or 'origin' not in data.columns or 'notified_by' not in data.columns:
        return go.Figure().update_layout(
            title="Données insuffisantes pour créer le graphique"
        )
    
    # Vérifier qu'il y a des valeurs non nulles
    if data['origin'].isna().all() or data['notified_by'].isna().all():
        return go.Figure().update_layout(
            title="Données insuffisantes pour créer la heatmap"
        )
    
    # Créer une table croisée dynamique
    try:
        heatmap_data = pd.crosstab(data['origin'], data['notified_by'])
        
        # S'assurer qu'il y a des données
        if heatmap_data.empty:
            return go.Figure().update_layout(
                title="Pas assez de données pour créer la heatmap"
            )
        
        # Filtrer pour garder uniquement les combinaisons les plus fréquentes
        top_origins = data['origin'].value_counts().nlargest(min(15, len(data['origin'].unique()))).index
        top_notifiers = data['notified_by'].value_counts().nlargest(min(10, len(data['notified_by'].unique()))).index
        
        # Vérifier qu'il reste des données après filtrage
        if len(top_origins) == 0 or len(top_notifiers) == 0:
            return go.Figure().update_layout(
                title="Pas assez de données pour créer la heatmap après filtrage"
            )
        
        filtered_heatmap = heatmap_data.loc[
            heatmap_data.index.isin(top_origins),
            heatmap_data.columns.isin(top_notifiers)
        ]
        
        # Vérifier à nouveau si le dataframe filtré est vide
        if filtered_heatmap.empty:
            return go.Figure().update_layout(
                title="Pas assez de données communes pour créer la heatmap"
            )
        
        # Créer la heatmap
        fig = px.imshow(
            filtered_heatmap,
            labels=dict(x="Pays notifiant", y="Pays d'origine", color="Nombre de suspicions"),
            x=filtered_heatmap.columns,
            y=filtered_heatmap.index,
            color_continuous_scale=px.colors.sequential.Blues,
            title="Relations entre pays d'origine et pays notifiants"
        )
        
        fig.update_layout(
            xaxis={'tickangle': 45},
            height=600
        )
        
        return fig
    except Exception as e:
        return go.Figure().update_layout(
            title=f"Erreur lors de la création du graphique: {str(e)}"
        )

def create_timeline_chart(data, time_column='date'):
    """
    Crée un graphique chronologique des suspicions
    """
    if data is None or data.empty or time_column not in data.columns or 'fraud_type' not in data.columns:
        return go.Figure().update_layout(
            title="Données insuffisantes pour créer le graphique"
        )
    
    # Vérifier qu'il y a suffisamment de dates uniques
    if len(data[time_column].unique()) < 2:
        return go.Figure().update_layout(
            title="Pas assez de périodes pour créer un graphique d'évolution"
        )
    
    try:
        # Agréger par date et type de fraude
        time_data = data.groupby([time_column, 'fraud_type']).size().reset_index(name='count')
        
        fig = px.line(
            time_data,
            x=time_column,
            y='count',
            color='fraud_type',
            title="Évolution des suspicions dans le temps par type de fraude",
            labels={'count': 'Nombre de suspicions', time_column: 'Date'}
        )
        
        return fig
    except Exception as e:
        return go.Figure().update_layout(
            title=f"Erreur lors de la création du graphique: {str(e)}"
        )
