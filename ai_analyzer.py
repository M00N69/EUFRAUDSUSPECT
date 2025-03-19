import requests
import json
import pandas as pd

def analyze_with_mistral(api_key, query, data):
    """
    Analyse les données avec Mistral AI API.
    
    Args:
        api_key: Clé API Mistral
        query: Question posée par l'utilisateur
        data: DataFrame contenant les données filtrées
    
    Returns:
        str: Réponse générative de l'analyse
    """
    # Vérification des entrées
    if not api_key or not query:
        return "Veuillez fournir une clé API et une question pour l'analyse."
    
    if data is None or data.empty:
        return "Aucune donnée disponible pour l'analyse."
    
    # Préparer les données pour l'API
    # Convertir le DataFrame en JSON pour passer dans le prompt
    data_sample = data.sample(min(100, len(data))).to_json(orient='records', indent=2)
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    # Extraire quelques statistiques clés
    total_records = len(data)
    top_categories = data['product_category'].value_counts().nlargest(5).to_dict() if 'product_category' in data.columns else {}
    top_origins = data['origin'].value_counts().nlargest(5).to_dict() if 'origin' in data.columns else {}
    top_fraud_types = data['fraud_type'].value_counts().to_dict() if 'fraud_type' in data.columns else {}
    date_range = f"{data['date'].min()} à {data['date'].max()}" if 'date' in data.columns else "non disponible"
    
    # Préparer le prompt pour Mistral
    system_prompt = """
    Vous êtes un expert en analyse des fraudes alimentaires pour la Commission Européenne.
    Analysez les données fournies sur les suspicions de fraude et répondez à la question de manière précise et détaillée.
    Fondez votre analyse uniquement sur les données fournies, sans faire d'hypothèses extérieures.
    Structurez votre réponse de manière claire avec des sections et des points clés.
    """
    
    prompt = f"""
    Question: {query}
    
    Contexte des données analysées:
    - Nombre total de suspicions: {total_records}
    - Période couverte: {date_range}
    - Principales catégories de produits concernées: {json.dumps(top_categories)}
    - Principaux pays d'origine: {json.dumps(top_origins)}
    - Types de fraude: {json.dumps(top_fraud_types)}
    
    Échantillon de données (limité à 100 enregistrements maximum):
    {data_sample}
    
    Veuillez fournir une analyse détaillée qui répond spécifiquement à la question posée.
    """
    
    try:
        # Appel à l'API Mistral
        response = requests.post(
            'https://api.mistral.ai/v1/chat/completions',
            headers=headers,
            json={
                'model': 'mistral-large-latest',  # Utiliser le meilleur modèle disponible
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.3,  # Paramètre de créativité assez bas pour des analyses factuelles
                'max_tokens': 2000   # Réponse détaillée mais pas trop longue
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            return content
        else:
            return f"Erreur lors de l'appel à l'API Mistral: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"Erreur lors de l'analyse IA: {str(e)}"

def get_mistral_signup_info():
    """
    Renvoie les informations sur comment obtenir une clé API Mistral.
    """
    info = """
    ## Comment obtenir une clé API Mistral AI

    1. Rendez-vous sur [la page d'inscription de Mistral AI](https://console.mistral.ai/signup/)
    2. Créez un compte avec votre email
    3. Une fois connecté, accédez à la section API Keys
    4. Générez une nouvelle clé API
    5. Copiez cette clé et collez-la dans le champ approprié de cette application

    **Note**: La clé API est privée et ne doit pas être partagée. Cette application stocke uniquement 
    votre clé temporairement pendant la session en cours.
    """
    return info
