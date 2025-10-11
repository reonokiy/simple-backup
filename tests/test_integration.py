import os
import tarfile
from pathlib import Path
from pyrage import x25519
import pyrage
from main import backup


def test_integration_backup_tar_to_fs(mock_source_dir, mock_dest_dir, monkeypatch):
    success = backup(
        source_path=mock_source_dir,
        destinations=[{'service': 'fs', 'root': '', 'storage': {'root': mock_dest_dir}}],
        compression='tar',
        archive_name='test_backup'
    )
    
    assert success is True
    
    backup_file = Path(mock_dest_dir) / 'test_backup.tar'
    assert backup_file.exists()
    
    with tarfile.open(backup_file, 'r') as tar:
        members = tar.getnames()
        assert len(members) > 0


def test_integration_backup_tar_gz_to_fs(mock_source_dir, mock_dest_dir, monkeypatch):
    success = backup(
        source_path=mock_source_dir,
        destinations=[{'service': 'fs', 'root': '', 'storage': {'root': mock_dest_dir}}],
        compression='tar.gz',
        archive_name='test_backup'
    )
    
    assert success is True
    
    backup_file = Path(mock_dest_dir) / 'test_backup.tar.gz'
    assert backup_file.exists()


def test_integration_backup_tar_zst_to_fs(mock_source_dir, mock_dest_dir, monkeypatch):
    success = backup(
        source_path=mock_source_dir,
        destinations=[{'service': 'fs', 'root': '', 'storage': {'root': mock_dest_dir}}],
        compression='tar.zst',
        archive_name='test_backup'
    )
    
    assert success is True
    
    backup_file = Path(mock_dest_dir) / 'test_backup.tar.zst'
    assert backup_file.exists()


def test_integration_backup_zip_to_fs(mock_source_dir, mock_dest_dir, monkeypatch):
    success = backup(
        source_path=mock_source_dir,
        destinations=[{'service': 'fs', 'root': '', 'storage': {'root': mock_dest_dir}}],
        compression='zip',
        archive_name='test_backup'
    )
    
    assert success is True
    
    backup_file = Path(mock_dest_dir) / 'test_backup.zip'
    assert backup_file.exists()


def test_integration_backup_with_encryption(mock_source_dir, mock_dest_dir, monkeypatch):
    identity = x25519.Identity.generate()
    recipient = identity.to_public()
    
    success = backup(
        source_path=mock_source_dir,
        destinations=[{'service': 'fs', 'root': '', 'storage': {'root': mock_dest_dir}}],
        compression='tar.gz',
        archive_name='encrypted_backup',
        encryption_enabled=True,
        encryption_recipient=str(recipient)
    )
    
    assert success is True
    
    backup_file = Path(mock_dest_dir) / 'encrypted_backup.tar.gz.age'
    assert backup_file.exists()
    
    with open(backup_file, 'rb') as f:
        encrypted_data = f.read()
    
    decrypted = pyrage.decrypt(encrypted_data, [identity])
    assert len(decrypted) > 0


def test_integration_backup_with_dest_root(mock_source_dir, mock_dest_dir, monkeypatch):
    dest_root = 'backups/prod'
    
    success = backup(
        source_path=mock_source_dir,
        destinations=[{'service': 'fs', 'root': dest_root, 'storage': {'root': mock_dest_dir}}],
        compression='tar',
        archive_name='test_backup'
    )
    
    assert success is True
    
    backup_file = Path(mock_dest_dir) / dest_root / 'test_backup.tar'
    assert backup_file.exists()


def test_integration_backup_with_retention(mock_source_dir, mock_dest_dir, monkeypatch):
    for i in range(10):
        backup(
            source_path=mock_source_dir,
            destinations=[{'service': 'fs', 'root': '', 'storage': {'root': mock_dest_dir}}],
            compression='tar'
        )
    
    retention_config = {
        'max_backups': 5,
        'daily': 0,
        'weekly': 0,
        'monthly': 0,
        'yearly': 0,
        'dest_root': ''
    }
    
    success = backup(
        source_path=mock_source_dir,
        destinations=[{'service': 'fs', 'root': '', 'storage': {'root': mock_dest_dir}}],
        compression='tar',
        retention_config=retention_config
    )
    
    assert success is True
    
    backup_files = list(Path(mock_dest_dir).glob('*.tar'))
    assert len(backup_files) <= 5


def test_integration_backup_tar_format(mock_source_dir, mock_dest_dir, monkeypatch):
    success = backup(
        source_path=mock_source_dir,
        destinations=[{'service': 'fs', 'root': '', 'storage': {'root': mock_dest_dir}}],
        compression='tar'
    )
    
    assert success is True
    
    dest_path = Path(mock_dest_dir)
    archives = list(dest_path.glob('*.tar'))
    assert len(archives) == 1


def test_integration_backup_auto_archive_name(mock_source_dir, mock_dest_dir, monkeypatch):
    success = backup(
        source_path=mock_source_dir,
        destinations=[{'service': 'fs', 'root': '', 'storage': {'root': mock_dest_dir}}],
        compression='tar'
    )
    
    assert success is True
    
    backup_files = list(Path(mock_dest_dir).glob('backup_source_*.tar'))
    assert len(backup_files) == 1

