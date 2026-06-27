from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

_nlp_engine = NlpEngineProvider(nlp_configuration={
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
}).create_engine()

analyzer = AnalyzerEngine(nlp_engine=_nlp_engine, supported_languages=["en"])
anonymizer = AnonymizerEngine()

_SUPPORTED_ENTITIES = [
    "PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS",
    "LOCATION", "DATE_TIME", "NRP",
    "MEDICAL_LICENSE", "US_SSN", "CREDIT_CARD",
]


def anonymize_text(text: str) -> tuple[str, bool]:
    """Returns (anonymized_text, pii_was_detected)."""
    results = analyzer.analyze(
        text=text,
        entities=_SUPPORTED_ENTITIES,
        language="en",
    )
    if not results:
        return text, False

    anonymized = anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators={
            "PERSON": OperatorConfig("replace", {"new_value": "[NAME]"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE]"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL]"}),
            "LOCATION": OperatorConfig("replace", {"new_value": "[LOCATION]"}),
            "DATE_TIME": OperatorConfig("replace", {"new_value": "[DATE]"}),
            "US_SSN": OperatorConfig("replace", {"new_value": "[SSN]"}),
            "CREDIT_CARD": OperatorConfig("replace", {"new_value": "[CARD]"}),
        },
    )
    return anonymized.text, True
