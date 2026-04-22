# EUFRAUDSUSPECT

Surveillance et analyse des fraudes alimentaires dans l'Union Européenne.

Application Streamlit qui collecte, extrait et analyse les rapports mensuels de fraude alimentaire publiés par la Commission Européenne, enrichis par une base de données consolidée (VISIPILOT).

## Fonctionnalités

- **Données consolidées** : Base VISIPILOT de 1500+ suspicions de fraude alimentaire mondiale
- **Mise à jour automatique** : Téléchargement et extraction des rapports PDF mensuels de l'UE
- **Visualisations interactives** : Tableau de bord, cartes, tendances, heatmaps
- **Filtrage avancé** : Par date, catégorie, type de fraude, pays d'origine
- **Analyse IA** : Questions en langage naturel via Mistral AI (optionnel)
- **Export CSV** : Téléchargement des données filtrées depuis chaque page
- **Guide intégré** : Documentation complète accessible dans l'application

## Installation

```bash
git clone https://github.com/votre-utilisateur/eufraudsuspect.git
cd eufraudsuspect
pip install -r requirements.txt
streamlit run app.py
```

## Structure du projet

```
eufraudsuspect/
├── app.py                    # Point d'entrée (st.navigation multi-pages)
├── db_adapter.py             # Gestion BDD (SQLite + reconstruction CSV)
├── pdf_processor.py          # Extraction PDF (pdfplumber optimisé UE)
├── visualizations.py         # Graphiques Plotly
├── ai_analyzer.py            # Analyse IA (Mistral SDK)
├── utils.py                  # Utilitaires (codes ISO pays, formatage)
├── pages/
│   ├── dashboard.py          # Tableau de bord (KPIs + graphiques)
│   ├── geo_analysis.py       # Analyse géographique (cartes + heatmap)
│   ├── trends.py             # Tendances temporelles
│   ├── details.py            # Tableau interactif des suspicions
│   ├── pdf_extraction.py     # Test d'extraction PDF
│   ├── ai_analysis.py        # Interface Mistral
│   └── guide.py              # Guide utilisateur
├── data/
│   ├── extracted/            # CSV extraits (source de vérité, commité Git)
│   └── database.sqlite       # BDD locale (reconstruit auto, ignoré Git)
├── scripts/
│   └── update_data.py        # Script mise à jour (GitHub Actions)
└── .github/workflows/
    └── update_data.yml        # Mise à jour mensuelle automatique
```

## Gestion des données

| Composant | Rôle | Persistant ? |
|-----------|------|-------------|
| CSV source (VISIPILOT) | Base consolidée historique | Oui (Git) |
| `data/extracted/*.csv` | Rapports mensuels extraits | Oui (Git) |
| `database.sqlite` | Cache pour les requêtes | Non (reconstruit) |

La base SQLite est reconstruite automatiquement au démarrage si vide, à partir des CSV. Sur Streamlit Cloud, elle est recréée à chaque déploiement.

## Déploiement sur Streamlit Cloud

1. Poussez le dépôt sur GitHub (les CSV dans `data/extracted/` sont inclus)
2. Créez une app sur [Streamlit Cloud](https://streamlit.io/cloud)
3. Point d'entrée : `app.py`
4. Déployez

## Source des données

- Rapports mensuels UE : [Commission Européenne](https://food.ec.europa.eu/food-safety/acn/ffn-monthly_en)
- Base consolidée : fichier VISIPILOT

## Licence

MIT
