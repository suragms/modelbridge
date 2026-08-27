from app.auth.encryption import (
    decrypt_secret,
    encrypt_secret,
    generate_api_key,
    get_key_prefix,
    hash_api_key,
)


class TestAPIKeyGeneration:
    def test_generate_api_key_prefix(self):
        key = generate_api_key()
        assert key.startswith("mb_")

    def test_generate_api_key_length(self):
        key = generate_api_key()
        assert len(key) > 10

    def test_hash_api_key(self):
        key = "mb_test_key"
        hashed = hash_api_key(key)
        assert hashed != key
        assert len(hashed) == 64  # SHA256 hex

    def test_hash_api_key_deterministic(self):
        key = "mb_test_key"
        h1 = hash_api_key(key)
        h2 = hash_api_key(key)
        assert h1 == h2

    def test_get_key_prefix(self):
        key = "mb_abcdefghijklmnopqrstuvwxyz"
        prefix = get_key_prefix(key)
        assert prefix.endswith("...")
        assert len(prefix) == 13  # 10 chars + "..."


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        plaintext = "super-secret-api-key-12345"
        encrypted = encrypt_secret(plaintext)
        assert encrypted != plaintext
        decrypted = decrypt_secret(encrypted)
        assert decrypted == plaintext

    def test_different_encryptions_different_ciphertext(self):
        plaintext = "same-secret"
        e1 = encrypt_secret(plaintext)
        e2 = encrypt_secret(plaintext)
        assert e1 != e2  # Due to random IV
