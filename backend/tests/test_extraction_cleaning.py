from app.agents.ext import ExtractionAgent

agent = ExtractionAgent(api_key="test")


def test_issuer_name_keeps_names_containing_stop_words():
    assert agent._clean_issuer_name("Viacom Academy") == "Viacom Academy"
    assert agent._clean_issuer_name("Google Career Certificates from Coursera") == "Coursera"
    assert agent._clean_issuer_name("issued by Udemy") == "Udemy"


def test_issuer_url_rejects_dangerous_schemes():
    assert agent._clean_issuer_url("javascript:alert(1)") is None
    assert agent._clean_issuer_url("data:text/html,x") is None
    assert agent._clean_issuer_url("coursera.org/verify/ABC").startswith("https://")


def test_certificate_id_cleaning():
    assert agent._clean_certificate_id("AB CD 12 34") == "ABCD1234"
    assert agent._clean_certificate_id(None) is None
