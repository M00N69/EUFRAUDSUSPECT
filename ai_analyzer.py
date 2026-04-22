import logging
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from mistralai import Mistral

    MISTRAL_SDK_AVAILABLE = True
except ImportError:
    MISTRAL_SDK_AVAILABLE = False

import pandas as pd

SYSTEM_PROMPT = """Vous êtes un expert en analyse des fraudes alimentaires pour la Commission Européenne.
Analysez les données fournies sur les suspicions de fraude et répondez à la question de manière précise et détaillée.
Fondez votre analyse uniquement sur les données fournies, sans faire d'hypothèses extérieures.
Structurez votre réponse de manière claire avec des sections et des points clés.
Utilisez le formatage Markdown pour mettre en valeur les éléments importants."""


def analyze_with_mistral(
    api_key: str,
    query: str,
    data: pd.DataFrame,
    conversation_history: list | None = None,
) -> str:
    if not api_key or not query:
        return "Veuillez fournir une clé API et une question pour l'analyse."
    if data is None or data.empty:
        return "Aucune donnée disponible pour l'analyse."

    data_sample = data.sample(min(100, len(data))).to_json(
        orient="records", force_ascii=False
    )
    total_records = len(data)
    top_categories = (
        data["product_category"].value_counts().nlargest(5).to_dict()
        if "product_category" in data.columns
        else {}
    )
    top_origins = (
        data["origin"].value_counts().nlargest(5).to_dict()
        if "origin" in data.columns
        else {}
    )
    top_fraud_types = (
        data["fraud_type"].value_counts().to_dict()
        if "fraud_type" in data.columns
        else {}
    )
    date_range = (
        f"{data['date'].min()} à {data['date'].max()}"
        if "date" in data.columns
        else "non disponible"
    )

    prompt = f"""Question: {query}

Contexte des données analysées:
- Nombre total de suspicions: {total_records}
- Période couverte: {date_range}
- Principales catégories de produits concernées: {top_categories}
- Principaux pays d'origine: {top_origins}
- Types de fraude: {top_fraud_types}

Échantillon de données (limité à 100 enregistrements maximum):
{data_sample}

Veuillez fournir une analyse détaillée qui répond spécifiquement à la question posée."""

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "user", "content": prompt})

    try:
        if MISTRAL_SDK_AVAILABLE:
            client = Mistral(api_key=api_key)
            response = client.chat.complete(
                model="mistral-large-latest",
                messages=messages,
                temperature=0.3,
                max_tokens=2000,
            )
            return response.choices[0].message.content
        else:
            import requests

            resp = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json={
                    "model": "mistral-large-latest",
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 2000,
                },
                timeout=60,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            else:
                return f"Erreur API Mistral ({resp.status_code}): {resp.text[:200]}"
    except Exception as e:
        logger.error("Erreur analyse IA: %s", e)
        return f"Erreur lors de l'analyse IA: {e}"
