from app.agents.verification.matching import (
    name_match_score, id_in_text, looks_blocked, normalize_id,
)


def test_full_name_matches():
    ok, score = name_match_score("Roopak Krishna", "This certifies that Roopak Krishna completed the course")
    assert ok and score == 1.0


def test_name_tokens_far_apart_do_not_match():
    filler = " ".join(["lorem"] * 40)
    ok, score = name_match_score("John Smith", f"John {filler} Smith")
    assert not ok and score < 1.0


def test_single_token_name_is_never_verified():
    ok, score = name_match_score("John", "John completed the course")
    assert not ok and score <= 0.5


def test_ocr_typo_tolerated():
    ok, _ = name_match_score("Krishnamurthy Iyer", "Awarded to Krishnamurthi Iyer today")
    assert ok


def test_accents_ignored():
    ok, _ = name_match_score("José García", "Jose Garcia")
    assert ok


def test_different_person_fails():
    ok, _ = name_match_score("Alice Walker", "Certificate awarded to Bob Marley")
    assert not ok


def test_id_requires_length_and_containment():
    assert id_in_text("ABCD-1234-EFGH", "ID: abcd1234efgh")
    assert not id_in_text("1234", "1234")          # too short to be meaningful
    assert not id_in_text("ABCD1234EFGH", "ABCD1234EFGX")


def test_normalize_id():
    assert normalize_id(" UC-9ba4 3c6a ") == "uc9ba43c6a"


def test_blocked_pages():
    assert looks_blocked("")
    assert looks_blocked("Just a moment... Enable JavaScript and cookies to continue")
    assert not looks_blocked("This certifies that Jane Doe completed " + "content " * 200)
