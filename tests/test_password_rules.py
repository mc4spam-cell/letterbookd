import pytest
from django.core.exceptions import ValidationError

from users.validators import (
    CharacterClassesValidator,
    ConsecutiveSubstringValidator,
    shares_run,
)


def test_shares_run_no_overlap():
    assert not shares_run("brandnew", "Zx9!KbqmPr7Lv2n$a8Q", 7)


def test_shares_run_exact_8_chars():
    # "admin123" = 8 car. communs
    assert shares_run("admin1234@example.com", "admin1234!XyZabc", 7)


def test_shares_run_case_insensitive():
    assert shares_run("Bonjour12", "bonjour12XY", 7)


def test_shares_run_below_threshold():
    # 7 car. en commun max → OK
    assert not shares_run("abcdefg", "abcdefg999999", 7)


class FakeUser:
    def __init__(self, email="", display_name=""):
        self.email = email
        self.display_name = display_name


def test_consecutive_validator_rejects_email_substring():
    v = ConsecutiveSubstringValidator()
    user = FakeUser(email="alice1234@example.com", display_name="alice")
    with pytest.raises(ValidationError):
        v.validate("alice1234-ZxY!99", user=user)


def test_consecutive_validator_allows_short_overlap():
    v = ConsecutiveSubstringValidator()
    user = FakeUser(email="alice@x.y", display_name="alice")
    # "alice" = 5 car., sous le seuil
    v.validate("aliceQX8!motpass", user=user)


def test_character_classes_rejects_missing_class():
    v = CharacterClassesValidator()
    with pytest.raises(ValidationError):
        v.validate("alllowercase1234!")  # pas de majuscule


def test_character_classes_accepts_all_classes():
    v = CharacterClassesValidator()
    v.validate("Abcdef1234!xyz")
