# EUFRAUDSUSPECT

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://eufraudsuspect.streamlit.app)
[![GitHub Actions](https://github.com/M00N69/EUFRAUDSUSPECT/actions/workflows/update_data.yml/badge.svg)](https://github.com/M00N69/EUFRAUDSUSPECT/actions/workflows/update_data.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Data: 1500+ records](https://img.shields.io/badge/Data-1500%2B%20records-blue.svg)]()

**Surveillance et analyse des fraudes alimentaires dans l'Union Européenne**

Application interactive de suivi des suspicions de fraude alimentaire, alimentée par les rapports mensuels de la Commission Européenne et la base consolidée VISIPILOT.

## Fonctionnalités

- **Données consolidées** : 1500+ suspicions de fraude alimentaire mondiale (source VISIPILOT)
- **Mise à jour automatique** : Téléchargement et extraction des rapports PDF mensuels de l'UE
- **7 pages interactives** : Tableau de bord, carte mondiale, tendances, détails, extraction PDF, analyse IA, guide
- **Visualisations Plotly** : Graphiques, cartes choroplèthes, heatmaps, timelines
- **Filtrage avancé** : Par date, catégorie de produit, type de fraude, pays d'origine
- **Analyse IA** : Questions en langage naturel via Mistral AI (optionnel)
- **Export CSV** : Téléchargement depuis chaque page
- **Mise à jour mensuelle** : GitHub Actions automatique

## Démo

[Lancer l'application sur Streamlit Cloud](https://eufraudsuspect.streamlit.app)

## Installation

```bash
git clone https://github.com/M00N69/EUFRAUDSUSPECT.git
cd EUFRAUDSUSPECT
pip install -r requirements.txt
streamlit run app.py
```

## Pages de l'application

| Page | Description |
|------|-------------|
| Tableau de bord | KPIs, graphiques par catégorie/type, évolution temporelle |
| Analyse géographique | Carte mondiale, heatmap origine/notifiant, top pays |
| Tendances | Évolution globale et par type de fraude |
| Détails des suspicions | Tableau complet avec export CSV |
| Extraction PDF | Test d'extraction avec score de confiance |
| Analyse IA | Interface Mistral avec conversation multi-tours |
| Guide utilisateur | Documentation intégrée complète |

## Gestion des données

| Composant | Rôle | Persistant ? |
|-----------|------|:------------:|
| CSV VISIPILOT | Base consolidée historique (1500+ lignes) | Oui (Git) |
| `data/extracted/*.csv` | Rapports mensuels extraits des PDF | Oui (Git) |
| `database.sqlite` | Cache pour les requêtes SQL | Non (reconstruit) |

La base SQLite est reconstruite automatiquement au démarrage à partir des CSV. Sur Streamlit Cloud, elle est recréée à chaque déploiement.

## Déploiement sur Streamlit Cloud

1. Forkez ou clonez ce dépôt
2. Allez sur [share.streamlit.io](https://share.streamlit.io)
3. Créez une nouvelle app → sélectionnez `M00N69/EUFRAUDSUSPECT`
4. Point d'entrée : `app.py`
5. Déployez

## Source des données

- **Rapports mensuels UE** : [Commission Européenne](https://food.ec.europa.eu/food-safety/acn/ffn-monthly_en)
- **Base consolidée** : Fichier VISIPILOT (1500+ entrées, 2020-2025)

## Structure du projet

```
EUFRAUDSUSPECT/
├── app.py                    # Point d'entrée (st.navigation)
├── db_adapter.py             # Gestion BDD (SQLite + reconstruction CSV)
├── pdf_processor.py          # Extraction PDF (pdfplumber optimisé)
├── visualizations.py         # Graphiques Plotly
├── ai_analyzer.py            # Analyse IA (Mistral SDK)
├── utils.py                  # Codes ISO 180+ pays, formatage
├── pages/                    # 7 pages Streamlit
├── data/extracted/           # CSV extraits (source de vérité)
├── scripts/update_data.py    # Mise à jour GitHub Actions
└── .github/workflows/        # Mise à jour mensuelle auto
```

## Licence

[MIT](LICENSE)
