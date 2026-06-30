def get_transparency_label(result: str) -> str:
    """
    Return the reader-facing transparency label for an attribution result.

    result should be one of:
    - "likely_ai"
    - "likely_human"
    - "uncertain"
    """

    labels = {
        "likely_ai": (
            "Provenance Guard found strong signals that this text was likely generated "
            "or heavily shaped by AI. This label is based on automated analysis and may "
            "be appealed by the creator."
        ),
        "likely_human": (
            "Provenance Guard found strong signals that this text was likely written "
            "primarily by a person. This label is based on automated analysis and is "
            "not a guarantee of authorship."
        ),
        "uncertain": (
            "Provenance Guard could not determine a confident attribution for this text. "
            "The available signals were mixed, so readers should treat the authorship as uncertain."
        ),
    }

    return labels.get(result, labels["uncertain"])