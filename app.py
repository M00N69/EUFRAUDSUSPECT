with st.sidebar:
    st.title("EUFRAUDSUSPECT")
    st.caption("Surveillance des fraudes alimentaires dans l'UE")

    # Initialisation du data manager si pas déjà fait
    if "data_manager" not in st.session_state:
        with st.spinner("Chargement des données..."):
            st.session_state.data_manager = DataManager()

    if "last_update_check" not in st.session_state:
        st.session_state.last_update_check = None
    if "ai_conversation" not in st.session_state:
        st.session_state.ai_conversation = []
    if "filters" not in st.session_state:
        st.session_state.filters = {}

    dm = st.session_state.data_manager
    has_data = dm.data is not None and not dm.data.empty
