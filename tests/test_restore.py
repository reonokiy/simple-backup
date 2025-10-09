import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from main import decrypt_file, extract_archive, restore, list_available_backups
from pyrage import x25519


@pytest.fixture
def temp_dir():
    tmp = tempfile.mkdtemp()
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def age_keys():
    identity = x25519.Identity.generate()
    recipient = identity.to_public()
    return {
        'identity': str(identity),
        'recipient': str(recipient),
        'identity_obj': identity,
        'recipient_obj': recipient
    }


def test_decrypt_file_success(temp_dir, age_keys):
    import pyrage
    
    encrypted_path = os.path.join(temp_dir, "test.txt.age")
    plaintext = b"Hello, World!"
    
    encrypted = pyrage.encrypt(plaintext, [age_keys['recipient_obj']])
    with open(encrypted_path, 'wb') as f:
        f.write(encrypted)
    
    decrypted_path = decrypt_file(encrypted_path, age_keys['identity'])
    
    assert os.path.exists(decrypted_path)
    assert decrypted_path == os.path.join(temp_dir, "test.txt")
    
    with open(decrypted_path, 'rb') as f:
        assert f.read() == plaintext


def test_decrypt_file_no_age_extension(temp_dir, age_keys):
    import pyrage
    
    encrypted_path = os.path.join(temp_dir, "test.txt")
    plaintext = b"Hello, World!"
    
    encrypted = pyrage.encrypt(plaintext, [age_keys['recipient_obj']])
    with open(encrypted_path, 'wb') as f:
        f.write(encrypted)
    
    decrypted_path = decrypt_file(encrypted_path, age_keys['identity'])
    
    assert os.path.exists(decrypted_path)
    assert decrypted_path == os.path.join(temp_dir, "test.txt.decrypted")
    
    with open(decrypted_path, 'rb') as f:
        assert f.read() == plaintext


def test_decrypt_file_wrong_key(temp_dir, age_keys):
    import pyrage
    
    encrypted_path = os.path.join(temp_dir, "test.txt.age")
    plaintext = b"Hello, World!"
    
    encrypted = pyrage.encrypt(plaintext, [age_keys['recipient_obj']])
    with open(encrypted_path, 'wb') as f:
        f.write(encrypted)
    
    wrong_identity = x25519.Identity.generate()
    
    with pytest.raises(Exception):
        decrypt_file(encrypted_path, str(wrong_identity))


def test_extract_tar_gz(temp_dir):
    import tarfile
    
    source_dir = os.path.join(temp_dir, "source")
    os.makedirs(source_dir)
    
    test_file = os.path.join(source_dir, "test.txt")
    with open(test_file, 'w') as f:
        f.write("test content")
    
    archive_path = os.path.join(temp_dir, "archive.tar.gz")
    with tarfile.open(archive_path, 'w:gz') as tar:
        tar.add(source_dir, arcname="source")
    
    dest_dir = os.path.join(temp_dir, "extracted")
    os.makedirs(dest_dir)
    
    result = extract_archive(archive_path, dest_dir)
    
    assert result is True
    extracted_file = os.path.join(dest_dir, "source", "test.txt")
    assert os.path.exists(extracted_file)
    with open(extracted_file, 'r') as f:
        assert f.read() == "test content"


def test_extract_tar_bz2(temp_dir):
    import tarfile
    
    source_dir = os.path.join(temp_dir, "source")
    os.makedirs(source_dir)
    
    test_file = os.path.join(source_dir, "test.txt")
    with open(test_file, 'w') as f:
        f.write("test content")
    
    archive_path = os.path.join(temp_dir, "archive.tar.bz2")
    with tarfile.open(archive_path, 'w:bz2') as tar:
        tar.add(source_dir, arcname="source")
    
    dest_dir = os.path.join(temp_dir, "extracted")
    os.makedirs(dest_dir)
    
    result = extract_archive(archive_path, dest_dir)
    
    assert result is True
    extracted_file = os.path.join(dest_dir, "source", "test.txt")
    assert os.path.exists(extracted_file)


def test_extract_tar_xz(temp_dir):
    import tarfile
    
    source_dir = os.path.join(temp_dir, "source")
    os.makedirs(source_dir)
    
    test_file = os.path.join(source_dir, "test.txt")
    with open(test_file, 'w') as f:
        f.write("test content")
    
    archive_path = os.path.join(temp_dir, "archive.tar.xz")
    with tarfile.open(archive_path, 'w:xz') as tar:
        tar.add(source_dir, arcname="source")
    
    dest_dir = os.path.join(temp_dir, "extracted")
    os.makedirs(dest_dir)
    
    result = extract_archive(archive_path, dest_dir)
    
    assert result is True
    extracted_file = os.path.join(dest_dir, "source", "test.txt")
    assert os.path.exists(extracted_file)


def test_extract_tar(temp_dir):
    import tarfile
    
    source_dir = os.path.join(temp_dir, "source")
    os.makedirs(source_dir)
    
    test_file = os.path.join(source_dir, "test.txt")
    with open(test_file, 'w') as f:
        f.write("test content")
    
    archive_path = os.path.join(temp_dir, "archive.tar")
    with tarfile.open(archive_path, 'w') as tar:
        tar.add(source_dir, arcname="source")
    
    dest_dir = os.path.join(temp_dir, "extracted")
    os.makedirs(dest_dir)
    
    result = extract_archive(archive_path, dest_dir)
    
    assert result is True
    extracted_file = os.path.join(dest_dir, "source", "test.txt")
    assert os.path.exists(extracted_file)


def test_extract_tar_zst(temp_dir):
    import tarfile
    import compression.zstd
    
    source_dir = os.path.join(temp_dir, "source")
    os.makedirs(source_dir)
    
    test_file = os.path.join(source_dir, "test.txt")
    with open(test_file, 'w') as f:
        f.write("test content")
    
    tar_path = os.path.join(temp_dir, "archive.tar")
    with tarfile.open(tar_path, 'w') as tar:
        tar.add(source_dir, arcname="source")
    
    archive_path = os.path.join(temp_dir, "archive.tar.zst")
    with open(tar_path, 'rb') as f_in:
        with open(archive_path, 'wb') as f_out:
            f_out.write(compression.zstd.compress(f_in.read()))
    
    os.remove(tar_path)
    
    dest_dir = os.path.join(temp_dir, "extracted")
    os.makedirs(dest_dir)
    
    result = extract_archive(archive_path, dest_dir)
    
    assert result is True
    extracted_file = os.path.join(dest_dir, "source", "test.txt")
    assert os.path.exists(extracted_file)


def test_extract_zip(temp_dir):
    import zipfile
    
    source_dir = os.path.join(temp_dir, "source")
    os.makedirs(source_dir)
    
    test_file = os.path.join(source_dir, "test.txt")
    with open(test_file, 'w') as f:
        f.write("test content")
    
    archive_path = os.path.join(temp_dir, "archive.zip")
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(test_file, "source/test.txt")
    
    dest_dir = os.path.join(temp_dir, "extracted")
    os.makedirs(dest_dir)
    
    result = extract_archive(archive_path, dest_dir)
    
    assert result is True
    extracted_file = os.path.join(dest_dir, "source", "test.txt")
    assert os.path.exists(extracted_file)


def test_extract_gzip(temp_dir):
    import gzip
    
    test_content = b"test content"
    
    archive_path = os.path.join(temp_dir, "test.txt.gz")
    with gzip.open(archive_path, 'wb') as f:
        f.write(test_content)
    
    dest_dir = os.path.join(temp_dir, "extracted")
    os.makedirs(dest_dir)
    
    result = extract_archive(archive_path, dest_dir)
    
    assert result is True
    extracted_file = os.path.join(dest_dir, "test.txt")
    assert os.path.exists(extracted_file)
    with open(extracted_file, 'rb') as f:
        assert f.read() == test_content


def test_extract_unsupported_format(temp_dir):
    archive_path = os.path.join(temp_dir, "archive.unknown")
    with open(archive_path, 'w') as f:
        f.write("test")
    
    dest_dir = os.path.join(temp_dir, "extracted")
    os.makedirs(dest_dir)
    
    with pytest.raises(ValueError, match="Unsupported archive format"):
        extract_archive(archive_path, dest_dir)


@patch('main.create_dest_operator')
def test_restore_unencrypted_tar_gz(mock_create_dest_op, temp_dir):
    import tarfile
    
    source_dir = os.path.join(temp_dir, "source")
    os.makedirs(source_dir)
    
    test_file = os.path.join(source_dir, "test.txt")
    with open(test_file, 'w') as f:
        f.write("test content")
    
    archive_path = os.path.join(temp_dir, "backup.tar.gz")
    with tarfile.open(archive_path, 'w:gz') as tar:
        tar.add(source_dir, arcname="source")
    
    with open(archive_path, 'rb') as f:
        archive_data = f.read()
    
    mock_op = Mock()
    mock_op.read.return_value = archive_data
    mock_create_dest_op.return_value = mock_op
    
    dest_dir = os.path.join(temp_dir, "restored")
    
    result = restore("backup.tar.gz", dest_dir, "fs", None)
    
    assert result is True
    restored_file = os.path.join(dest_dir, "source", "test.txt")
    assert os.path.exists(restored_file)
    with open(restored_file, 'r') as f:
        assert f.read() == "test content"


@patch('main.create_dest_operator')
def test_restore_encrypted_tar_gz(mock_create_dest_op, temp_dir, age_keys):
    import tarfile
    import pyrage
    
    source_dir = os.path.join(temp_dir, "source")
    os.makedirs(source_dir)
    
    test_file = os.path.join(source_dir, "test.txt")
    with open(test_file, 'w') as f:
        f.write("test content")
    
    archive_path = os.path.join(temp_dir, "backup.tar.gz")
    with tarfile.open(archive_path, 'w:gz') as tar:
        tar.add(source_dir, arcname="source")
    
    with open(archive_path, 'rb') as f:
        archive_data = f.read()
    
    encrypted_data = pyrage.encrypt(archive_data, [age_keys['recipient_obj']])
    
    mock_op = Mock()
    mock_op.read.return_value = encrypted_data
    mock_create_dest_op.return_value = mock_op
    
    dest_dir = os.path.join(temp_dir, "restored")
    
    result = restore("backup.tar.gz.age", dest_dir, "fs", age_keys['identity'])
    
    assert result is True
    restored_file = os.path.join(dest_dir, "source", "test.txt")
    assert os.path.exists(restored_file)
    with open(restored_file, 'r') as f:
        assert f.read() == "test content"


@patch('main.create_dest_operator')
def test_restore_encrypted_no_identity_key(mock_create_dest_op, temp_dir):
    mock_op = Mock()
    mock_op.read.return_value = b"encrypted data"
    mock_create_dest_op.return_value = mock_op
    
    dest_dir = os.path.join(temp_dir, "restored")
    
    result = restore("backup.tar.gz.age", dest_dir, "fs", None)
    
    assert result is False


@patch('main.create_dest_operator')
def test_restore_creates_dest_directory(mock_create_dest_op, temp_dir):
    import tarfile
    
    source_dir = os.path.join(temp_dir, "source")
    os.makedirs(source_dir)
    
    test_file = os.path.join(source_dir, "test.txt")
    with open(test_file, 'w') as f:
        f.write("test content")
    
    archive_path = os.path.join(temp_dir, "backup.tar.gz")
    with tarfile.open(archive_path, 'w:gz') as tar:
        tar.add(source_dir, arcname="source")
    
    with open(archive_path, 'rb') as f:
        archive_data = f.read()
    
    mock_op = Mock()
    mock_op.read.return_value = archive_data
    mock_create_dest_op.return_value = mock_op
    
    dest_dir = os.path.join(temp_dir, "nonexistent", "restored")
    
    result = restore("backup.tar.gz", dest_dir, "fs", None)
    
    assert result is True
    assert os.path.exists(dest_dir)


@patch('main.list_backups')
@patch('main.create_dest_operator')
def test_list_available_backups(mock_create_dest_op, mock_list_backups, temp_dir):
    from datetime import datetime
    
    mock_backups = [
        {
            'path': 'backup1.tar.gz',
            'timestamp': datetime(2025, 1, 1, 12, 0, 0),
            'size': 1024 * 1024
        },
        {
            'path': 'backup2.tar.gz',
            'timestamp': datetime(2025, 1, 2, 12, 0, 0),
            'size': 2048 * 1024
        }
    ]
    
    mock_list_backups.return_value = mock_backups
    mock_op = Mock()
    mock_create_dest_op.return_value = mock_op
    
    result = list_available_backups('fs', '')
    
    assert len(result) == 2
    assert result[0]['path'] == 'backup1.tar.gz'
    assert result[1]['path'] == 'backup2.tar.gz'


@patch('main.list_backups')
@patch('main.create_dest_operator')
def test_list_available_backups_empty(mock_create_dest_op, mock_list_backups):
    mock_list_backups.return_value = []
    mock_op = Mock()
    mock_create_dest_op.return_value = mock_op
    
    result = list_available_backups('fs', '')
    
    assert len(result) == 0
