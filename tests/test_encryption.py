import os
import tempfile
from pathlib import Path
from pyrage import x25519
import pyrage
from main import encrypt_file


def test_encrypt_file_basic(temp_dir):
    source_file = Path(temp_dir) / "test.txt"
    source_file.write_text("sensitive data")
    
    identity = x25519.Identity.generate()
    recipient = identity.to_public()
    
    encrypted_path = encrypt_file(str(source_file), str(recipient))
    
    assert os.path.exists(encrypted_path)
    assert encrypted_path.endswith('.age')
    
    with open(encrypted_path, 'rb') as f:
        encrypted_data = f.read()
    
    decrypted = pyrage.decrypt(encrypted_data, [identity])
    assert decrypted == b"sensitive data"


def test_encrypt_file_large_content(temp_dir):
    source_file = Path(temp_dir) / "large.txt"
    large_content = "x" * 1024 * 1024
    source_file.write_text(large_content)
    
    identity = x25519.Identity.generate()
    recipient = identity.to_public()
    
    encrypted_path = encrypt_file(str(source_file), str(recipient))
    
    assert os.path.exists(encrypted_path)
    
    with open(encrypted_path, 'rb') as f:
        encrypted_data = f.read()
    
    decrypted = pyrage.decrypt(encrypted_data, [identity])
    assert decrypted.decode() == large_content


def test_encrypt_file_binary_content(temp_dir):
    source_file = Path(temp_dir) / "binary.dat"
    binary_content = bytes(range(256))
    source_file.write_bytes(binary_content)
    
    identity = x25519.Identity.generate()
    recipient = identity.to_public()
    
    encrypted_path = encrypt_file(str(source_file), str(recipient))
    
    with open(encrypted_path, 'rb') as f:
        encrypted_data = f.read()
    
    decrypted = pyrage.decrypt(encrypted_data, [identity])
    assert decrypted == binary_content


def test_encrypt_file_preserves_original(temp_dir):
    source_file = Path(temp_dir) / "test.txt"
    source_file.write_text("data")
    
    identity = x25519.Identity.generate()
    recipient = identity.to_public()
    
    encrypt_file(str(source_file), str(recipient))
    
    assert os.path.exists(source_file)
    assert source_file.read_text() == "data"


def test_encrypt_file_creates_age_extension(temp_dir):
    source_file = Path(temp_dir) / "backup.tar.zst"
    source_file.write_bytes(b"compressed data")
    
    identity = x25519.Identity.generate()
    recipient = identity.to_public()
    
    encrypted_path = encrypt_file(str(source_file), str(recipient))
    
    assert encrypted_path == f"{source_file}.age"
    assert Path(encrypted_path).name == "backup.tar.zst.age"


def test_encrypt_file_invalid_recipient(temp_dir):
    import pytest
    
    source_file = Path(temp_dir) / "test.txt"
    source_file.write_text("data")
    
    with pytest.raises(Exception):
        encrypt_file(str(source_file), "invalid_recipient_key")


def test_encrypt_file_nonexistent_file(temp_dir):
    import pytest
    
    identity = x25519.Identity.generate()
    recipient = identity.to_public()
    
    with pytest.raises(Exception):
        encrypt_file(str(Path(temp_dir) / "nonexistent.txt"), str(recipient))


def test_encrypt_file_empty_file(temp_dir):
    source_file = Path(temp_dir) / "empty.txt"
    source_file.write_text("")
    
    identity = x25519.Identity.generate()
    recipient = identity.to_public()
    
    encrypted_path = encrypt_file(str(source_file), str(recipient))
    
    with open(encrypted_path, 'rb') as f:
        encrypted_data = f.read()
    
    decrypted = pyrage.decrypt(encrypted_data, [identity])
    assert decrypted == b""
