"""Fernet JSON encrypt/decrypt for BYOK secrets."""

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException

from app.core.config import Settings
from app.core.secret_box import decrypt_json, encrypt_json


@pytest.fixture
def settings() -> Settings:
    return Settings(credentials_fernet_key=Fernet.generate_key().decode())


def test_encrypt_decrypt_round_trip(settings: Settings):
    payload = {"app_key": "abc12345", "app_secret": "super-secret"}
    token = encrypt_json(payload, settings)
    assert token != payload["app_secret"]
    assert decrypt_json(token, settings) == payload


def test_missing_key_fails_closed():
    with pytest.raises(HTTPException) as caught:
        encrypt_json({"app_key": "x"}, Settings(credentials_fernet_key=""))
    assert caught.value.status_code == 503
    assert caught.value.detail["code"] == "credentials_key_missing"


def test_tampered_ciphertext_fails(settings: Settings):
    token = encrypt_json({"app_key": "abc"}, settings)
    with pytest.raises(HTTPException) as caught:
        decrypt_json(token[:-4] + "xxxx", settings)
    assert caught.value.status_code == 500
    assert caught.value.detail["code"] == "credentials_decrypt_failed"
