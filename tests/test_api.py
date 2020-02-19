def test_api_rules(app):
    """
    Ensure that the API has exactly the endpoints we expect.
    """
    expected_endpoints = {
        "/",
        "/api-docs",
        "/downloadable_files",
        "/downloadable_files/download_url",
        "/downloadable_files/filter_facets",
        '/downloadable_files/<regex("[0-9]+"):id>',
        "/info/assays",
        "/info/analyses",
        "/info/manifests",
        "/info/extra_data_types",
        "/info/templates/<template_family>/<template_type>",
        "/ingestion/validate",
        "/ingestion/upload_manifest",
        "/ingestion/upload_assay",
        "/ingestion/upload_analysis",
        "/ingestion/extra-assay-metadata",
        "/ingestion/poll_upload_merge_status",
        "/permissions",
        '/permissions/<regex("[0-9]+"):id>',
        "/trial_metadata",
        '/trial_metadata/<regex("[a-zA-Z0-9_-]+"):trial_id>',
        "/upload_jobs",
        '/upload_jobs/<regex("[0-9]+"):id>',
        "/users",
        "/users/self",
        '/users/<regex("[0-9]+"):id>',
        "/new_users",
        '/new_users/<regex("[0-9]+"):id>',
    }

    # Check that every endpoint is expected, and has the expected allowed methods.
    for rule in app.url_map._rules:
        assert rule.rule in expected_endpoints
