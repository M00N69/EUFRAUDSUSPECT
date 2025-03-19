# EUFRAUDSUSPECT
Suivi des rapports de suspiscion EU
# Surveillance des fraudes alimentaires UE

Une application Streamlit qui surveille et analyse automatiquement les rapports mensuels de fraude alimentaire publiés par la Commission Européenne.

## Fonctionnalités

- **Mise à jour automatique** : L'application vérifie et télécharge automatiquement le dernier rapport disponible
- **Extraction des données** : Traitement et structuration automatique des données à partir des PDFs
- **Visualisations interactives** : Graphiques dynamiques pour explorer les tendances et les patterns
- **Filtrage avancé** : Sélection par date, catégorie de produit, type de fraude
- **Analyse IA** (optionnelle) : Analyse approfondie des données avec Mistral AI

## Installation

1. Cloner ce dépôt :
```
git clone https://github.com/votre-utilisateur/surveillance-fraudes-alimentaires.git
cd surveillance-fraudes-alimentaires
```

2. Installer les dépendances :
```
pip install -r requirements.txt
```

3. Lancer l'application :
```
streamlit run app.py
```

## Structure du projet

```
project_root/
│
├── app.py                    # Application Streamlit principale
├── data_manager.py           # Gestion des données (extraction, stockage)
├── pdf_processor.py          # Traitement des PDF
├── visualizations.py         # Composants de visualisation
├── ai_analyzer.py            # Module d'analyse IA (Mistral)
├── utils.py                  # Fonctions utilitaires
│
├── data/                     # Dossier de données
│   ├── database.sqlite       # Base de données SQLite locale
│   └── pdf_reports/          # Stockage des rapports PDF téléchargés
│
├── .streamlit/               # Configuration Streamlit
│   └── config.toml           # Fichier de configuration Streamlit
│
├── requirements.txt          # Dépendances Python
├── README.md                 # Documentation du projet
└── .gitignore                # Fichiers à ignorer dans Git
```

## Utilisation

1. Démarrez l'application en exécutant `streamlit run app.py`
2. À chaque démarrage, l'application vérifie automatiquement s'il y a un nouveau rapport disponible
3. Utilisez la barre latérale pour sélectionner les filtres de date, de catégories et de types de fraude
4. Explorez les visualisations interactives et les tableaux de données
5. Pour l'analyse IA (optionnelle), entrez votre clé API Mistral et posez votre question

## Fonctionnalité d'analyse IA

Pour utiliser la fonctionnalité d'analyse IA avancée :

1. Créez un compte sur [Mistral AI](https://console.mistral.ai/signup/)
2. Générez une clé API dans votre compte
3. Copiez la clé API dans le champ correspondant dans l'application
4. Posez votre question pour obtenir une analyse approfondie des données

## Déploiement sur Streamlit Cloud

Ce projet est conçu pour être facilement déployable sur Streamlit Cloud :

1. Assurez-vous que votre dépôt est public sur GitHub
2. Connectez-vous à [Streamlit Cloud](https://streamlit.io/cloud)
3. Créez une nouvelle application en sélectionnant votre dépôt
4. Configurez le chemin du fichier principal comme `app.py`
5. Déployez!

## Source des données

Les données proviennent des rapports mensuels sur les suspicions de fraude agroalimentaire publiés par la Commission Européenne sur [leur site officiel](https://food.ec.europa.eu/food-safety/acn/ffn-monthly_en).

## Licence

Ce projet est distribué sous licence MIT. Voir le fichier LICENSE pour plus de détails.
