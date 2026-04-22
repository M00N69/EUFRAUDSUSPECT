import streamlit as st

st.title("Guide utilisateur")

st.markdown("""
## EUFRAUDSUSPECT — Guide d'utilisation

### Qu'est-ce que EUFRAUDSUSPECT ?

EUFRAUDSUSPECT est une application de surveillance et d'analyse des fraudes alimentaires 
dans l'Union Européenne. Elle collecte automatiquement les rapports mensuels publiés par la 
Commission Européenne et offre des outils de visualisation, de filtrage et d'analyse.

---

### Source des données

Les données proviennent de deux sources :

1. **CSV principal** (`VISIPILOT veille Food Fraud.csv`) : base de données consolidée contenant 
   l'historique des suspicions de fraude alimentaire mondiale, avec des informations détaillées 
   (pays, catégorie, type de fraude, description, lien source).

2. **Rapports PDF mensuels de l'UE** : rapports officiels publiés par la Commission Européenne 
   sur [leur site](https://food.ec.europa.eu/food-safety/acn/ffn-monthly_en), extraits 
   automatiquement par l'application.

---

### Navigation

L'application est organisée en plusieurs pages accessibles depuis la barre latérale :

#### Analyse

| Page | Description |
|------|-------------|
| **Tableau de bord** | Vue d'ensemble avec KPIs, graphiques par catégorie et type de fraude, évolution temporelle |
| **Analyse géographique** | Carte mondiale des suspicions, heatmap pays d'origine/pays notifiant, analyse par pays |
| **Tendances** | Évolution temporelle globale et par type de fraude, statistiques par période |
| **Détails** | Tableau complet des suspicions avec export CSV, statistiques détaillées |

#### Outils

| Page | Description |
|------|-------------|
| **Extraction PDF** | Tester l'extraction de données depuis un rapport PDF, avec score de confiance |
| **Analyse IA** | Poser des questions en langage naturel sur les données (requiert clé API Mistral) |

---

### Filtres

Utilisez les filtres dans la barre latérale pour affiner l'analyse :

- **Période** : sélectionnez une plage de dates avec le slider
- **Catégories de produits** : filtrez par type de produit (ex: poissons, céréales, huiles)
- **Types de fraude** : filtrez par type de fraude (ex: falsification, marché gris, adultération)
- **Pays d'origine** : filtrez par pays signalé

Les filtres s'appliquent à toutes les pages d'analyse.

---

### Mise à jour des données

1. **Vérification automatique** : au premier lancement, l'application vérifie si un nouveau rapport est disponible
2. **Vérification manuelle** : cliquez sur "Vérifier les nouveaux rapports" dans la sidebar
3. **Téléchargement forcé** : si la vérification échoue, utilisez le bouton "Forcer le téléchargement"
4. **Réinitialisation** : le bouton "Réinitialiser la base" reconstruit la base depuis les CSV

---

### Extraction PDF

La page **Extraction PDF** vous permet de :

1. Charger un rapport PDF local (upload) ou télécharger le dernier rapport en ligne
2. Prévisualiser le contenu du PDF
3. Lancer l'extraction et voir le score de confiance
4. Ajouter les données extraites à la base de données

**Méthode d'extraction** : l'application utilise `pdfplumber` avec des paramètres optimisés 
pour le format des rapports UE (tableaux avec bordures, cellules fusionnées). Un score de 
confiance est calculé en comparant le nombre de suspicions extraites avec le total annoncé 
dans le rapport.

---

### Analyse IA

Pour utiliser l'analyse IA :

1. Obtenez une clé API [Mistral AI](https://console.mistral.ai/signup/)
2. Collez-la dans le champ "Clé API Mistral"
3. Choisissez une question suggérée ou écrivez la vôtre
4. Cliquez sur "Exécuter l'analyse"

L'historique de conversation est conservé pendant la session. Vous pouvez poser des questions 
de suivi pour approfondir l'analyse.

---

### Export des données

Chaque page propose un bouton **"Exporter CSV"** pour télécharger les données filtrées. 
Le format CSV est compatible avec Excel, Google Sheets et la plupart des outils d'analyse.

---

### Gestion de la base de données

- **Source de vérité** : les fichiers CSV dans `data/extracted/` et le CSV principal
- **SQLite** : base locale reconstruite automatiquement au démarrage si vide
- **Persistance** : les CSV sont versionnés dans Git ; SQLite est reconstruit à chaque déploiement
- **Mise à jour mensuelle** : un GitHub Actions vérifie automatiquement les nouveaux rapports

---

### FAQ

**Q : Pourquoi certaines données sont-elles manquantes ?**  
R : L'extraction PDF n'est pas parfaite. Les cellules fusionnées et les tableaux complexes 
peuvent causer des pertes. Vérifiez le score de confiance dans la page Extraction PDF.

**Q : Comment ajouter des données historiques ?**  
R : Placez un fichier CSV `report_YYYY-MM.csv` dans le dossier `data/extracted/` et 
relancez l'application. La base sera reconstruite automatiquement.

**Q : Mes données disparaissent sur Streamlit Cloud ?**  
R : C'est normal — le filesystem est éphémère. Les données sont reconstruites depuis les CSV 
du dépôt Git à chaque redémarrage. Assurez-vous de commiter vos CSV dans `data/extracted/`.

**Q : L'analyse IA est lente ?**  
R : L'analyse dépend de l'API Mistral. Les questions complexes sur de grands jeux de données 
peuvent prendre 10-30 secondes.

---

### Architecture technique

```
EUFRAUDSUSPECT/
├── app.py                  ← Point d'entrée (st.navigation)
├── db_adapter.py           ← Gestion BDD (SQLite + reconstruction CSV)
├── pdf_processor.py        ← Extraction PDF (pdfplumber optimisé)
├── visualizations.py       ← Graphiques Plotly
├── ai_analyzer.py          ← Analyse IA (Mistral SDK)
├── utils.py                ← Utilitaires (codes ISO, formatage)
├── pages/                  ← Pages multi-pages Streamlit
│   ├── dashboard.py
│   ├── geo_analysis.py
│   ├── trends.py
│   ├── details.py
│   ├── pdf_extraction.py
│   ├── ai_analysis.py
│   └── guide.py
├── data/
│   ├── extracted/          ← CSV extraits (source de vérité, commité dans Git)
│   └── database.sqlite     ← BDD locale (ignoré par Git, reconstruit auto)
├── scripts/
│   └── update_data.py      ← Script de mise à jour (GitHub Actions)
└── .github/workflows/
    └── update_data.yml     ← Mise à jour automatique mensuelle
```
""")
