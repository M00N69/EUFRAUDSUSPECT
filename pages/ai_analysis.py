import streamlit as st
from ai_analyzer import analyze_with_mistral

st.title("Analyse IA (Mistral)")

st.markdown("""
Posez vos questions sur les données de fraude alimentaire. L'IA analysera les données filtrées 
et vous fournira une réponse détaillée.

**Conseil** : Soyez précis dans vos questions pour obtenir les meilleures réponses.
""")

api_key = st.text_input(
    "Clé API Mistral",
    type="password",
    help="Votre clé API Mistral. Elle n'est stockée que dans la session en cours.",
)

if api_key:
    st.caption("Clé API fournie. Vous pouvez poser vos questions.")
else:
    with st.expander("Comment obtenir une clé API Mistral ?"):
        st.markdown("""
        1. Créez un compte sur [Mistral AI](https://console.mistral.ai/signup/)
        2. Générez une clé API dans la section **API Keys**
        3. Copiez-la et collez-la ci-dessus

        La clé n'est stockée que temporairement dans votre session.
        """)

filters = st.session_state.get("filters", {})
dm = st.session_state.data_manager
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

st.info(f"Analyse portera sur {len(filtered_data)} suspicions.")

suggested_questions = [
    "Quelles sont les tendances récentes des fraudes ?",
    "Quels sont les produits les plus à risque ?",
    "Quels pays sont les plus fréquemment signalés ?",
    "Y a-t-il des patterns saisonniers dans les fraudes ?",
    "Quelles recommandations pour les contrôles ?",
]

selected_q = st.selectbox("Question suggérée", [""] + suggested_questions)
query = st.text_area(
    "Votre question",
    value=selected_q if selected_q else "",
    placeholder="Ex: Quelles sont les tendances récentes des fraudes alimentaires ?",
)

if st.button("Exécuter l'analyse", type="primary", disabled=not (api_key and query)):
    if not api_key:
        st.error("Clé API requise.")
    elif not query:
        st.error("Question requise.")
    else:
        with st.spinner("Analyse en cours..."):
            result = analyze_with_mistral(
                api_key, query, filtered_data, st.session_state.get("ai_conversation")
            )
            st.session_state.ai_conversation.append({"role": "user", "content": query})
            st.session_state.ai_conversation.append(
                {"role": "assistant", "content": result}
            )

        st.markdown(result)

if st.session_state.ai_conversation:
    st.divider()
    st.subheader("Historique de la conversation")
    if st.button("Effacer l'historique"):
        st.session_state.ai_conversation = []
        st.rerun()

    for msg in st.session_state.ai_conversation:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
