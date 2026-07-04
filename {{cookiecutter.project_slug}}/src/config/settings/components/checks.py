EXTRA_CHECKS = {
    "checks": [
        "field-choices-constraint",
        "field-default-null",
        "field-file-upload-to",
        "field-help-text-gettext",
        "field-null",
        "field-related-name",
        "field-text-null",
        "field-verbose-name",
        "field-verbose-name-gettext",
        "field-verbose-name-gettext-case",
        "model-admin",
        "no-unique-together",
        {"id": "field-foreign-key-db-index", "when": "always"},
        {"id": "model-attribute", "attrs": ["__str__"]},
        {"id": "model-meta-attribute", "attrs": ["ordering"]},
    ]
}
