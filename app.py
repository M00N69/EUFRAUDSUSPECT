with st.sidebar:
    st.title("EUFRAUDSUSPECT")
    st.caption("Surveillance des fraudes alimentaires dans l'UE")

    dm = st.session_state.data_manager
    has_data = dm.data is not None and not dm.data.empty

    if has_data:
        dates = dm.get_available_dates()
        years = sorted(set(d[:4] for d in dates if d))
        year_options = ["Toutes"] + years
        selected_year = st.selectbox("Annee", year_options, index=0)

        if selected_year == "Toutes":
            filtered_dates = dates
        else:
            filtered_dates = [d for d in dates if d.startswith(selected_year)]

        if len(filtered_dates) > 1:
            start_date, end_date = st.select_slider(
                "Periode",
                options=filtered_dates,
                value=(filtered_dates[0], filtered_dates[-1]),
            )
        elif len(filtered_dates) == 1:
            start_date = end_date = filtered_dates[0]
            st.info(f"Periode: {filtered_dates[0]}")
        else:
            start_date = end_date = None

        all_categories = dm.get_product_categories()
        if all_categories:
            selected_categories = st.multiselect(
                "Categories",
                all_categories,
                default=[],
                help=f"{len(all_categories)} categories disponibles",
            )
        else:
            selected_categories = []

        all_fraud_types = dm.get_fraud_types()
        if all_fraud_types:
            selected_fraud_types = st.multiselect(
                "Types de fraude",
                all_fraud_types,
                default=[],
            )
        else:
            selected_fraud_types = []

        all_origins = dm.get_origins()
        if all_origins:
            selected_origins = st.multiselect(
                "Pays d'origine",
                all_origins,
                default=[],
            )
        else:
            selected_origins = []

        st.session_state.filters = {
            "start_date": start_date,
            "end_date": end_date,
            "categories": selected_categories,
            "fraud_types": selected_fraud_types,
            "origins": selected_origins,
        }

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "Vérifier nouveaux rapports",
                use_container_width=True,
                icon="🔄",
            ):
                with st.spinner("Vérification en cours..."):
                    try:
                        result = check_for_new_report(dm)
                        dm.reload()
                        if result:
                            st.success("Nouveau rapport ajouté !")
                        else:
                            st.info("Aucun nouveau rapport disponible.")
                        st.session_state.last_update_check = datetime.now()
                    except Exception as e:
                        st.error(f"Erreur: {e}")
        with col2:
            if st.button("Forcer mise à jour PDF", use_container_width=True, icon="📥"):
                with st.spinner("Téléchargement..."):
                    try:
                        if force_download_latest_report(dm):
                            st.success("Rapport téléchargé et extrait !")
                            dm.reload()
                            st.rerun()
                        else:
                            st.error("Échec du téléchargement.")
                    except Exception as e:
                        st.error(f"Erreur: {e}")

        if st.session_state.last_update_check:
            st.caption(
                f"Dernière vérif: {st.session_state.last_update_check.strftime('%d/%m/%Y %H:%M')}"
            )

    else:
        st.warning(
            "Aucune donnée. Cliquez sur 'Forcer mise à jour PDF' pour télécharger le dernier rapport."
        )
        if st.button("Forcer mise à jour PDF", icon="📥"):
            with st.spinner("Téléchargement..."):
                try:
                    if force_download_latest_report(dm):
                        dm.reload()
                        st.success("Rapport téléchargé ! Redémarrage...")
                        st.rerun()
                    else:
                        st.error("Échec.")
                except Exception as e:
                    st.error(f"Erreur: {e}")

        st.session_state.filters = {
            "start_date": None,
            "end_date": None,
            "categories": [],
            "fraud_types": [],
            "origins": [],
        }
