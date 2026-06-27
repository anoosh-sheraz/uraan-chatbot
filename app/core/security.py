from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

_nlp_engine = NlpEngineProvider(nlp_configuration={
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
}).create_engine()

_analyzer = AnalyzerEngine(nlp_engine=_nlp_engine, supported_languages=["en"])
_anonymizer = AnonymizerEngine()

_ENTITIES = [
    "PERSON",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "LOCATION",
    "DATE_TIME",
    "US_SSN",
    "CREDIT_CARD",
    "MEDICAL_LICENSE",
    "NRP",
]

_OPERATORS = {
    "PERSON":          OperatorConfig("replace", {"new_value": "[NAME]"}),
    "PHONE_NUMBER":    OperatorConfig("replace", {"new_value": "[PHONE]"}),
    "EMAIL_ADDRESS":   OperatorConfig("replace", {"new_value": "[EMAIL]"}),
    "LOCATION":        OperatorConfig("replace", {"new_value": "[LOCATION]"}),
    "DATE_TIME":       OperatorConfig("replace", {"new_value": "[DATE]"}),
    "US_SSN":          OperatorConfig("replace", {"new_value": "[SSN]"}),
    "CREDIT_CARD":     OperatorConfig("replace", {"new_value": "[CARD]"}),
    "MEDICAL_LICENSE": OperatorConfig("replace", {"new_value": "[MED_ID]"}),
}


def scrub_pii(text: str) -> str:
    """Analyze text for PII and return a fully anonymized string."""
    results = _analyzer.analyze(text=text, entities=_ENTITIES, language="en")
    if not results:
        return text
    return _anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators=_OPERATORS,
    ).text
