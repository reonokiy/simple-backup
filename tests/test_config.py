import os
import pytest
from main import load_config


def test_load_config_minimal(monkeypatch):
    monkeypatch.setenv('BACKUP_SOURCE_PATH', '/source')
    monkeypatch.setenv('BACKUP_DEST_SERVICE', 's3')
    
    config = load_config()
    
    assert config['source_path'] == '/source'
    assert config['dest_service'] == 's3'
    assert config['compression'] == 'tar.zst'
    assert config['retention_daily'] == 7
    assert config['retention_weekly'] == 4
    assert config['retention_monthly'] == 6
    assert config['retention_yearly'] == 2
    assert config['encryption_enabled'] is False


def test_load_config_missing_source_path(monkeypatch):
    monkeypatch.setenv('BACKUP_DEST_SERVICE', 's3')
    
    with pytest.raises(ValueError, match="BACKUP_SOURCE_PATH environment variable is required"):
        load_config()


def test_load_config_missing_dest_service(monkeypatch):
    monkeypatch.setenv('BACKUP_SOURCE_PATH', '/source')
    
    with pytest.raises(ValueError, match="BACKUP_DEST_SERVICE environment variable is required"):
        load_config()


def test_load_config_invalid_compression(monkeypatch):
    monkeypatch.setenv('BACKUP_SOURCE_PATH', '/source')
    monkeypatch.setenv('BACKUP_DEST_SERVICE', 's3')
    monkeypatch.setenv('BACKUP_COMPRESSION', 'invalid')
    
    with pytest.raises(ValueError, match="Invalid compression format"):
        load_config()


def test_load_config_valid_compressions(monkeypatch):
    monkeypatch.setenv('BACKUP_SOURCE_PATH', '/source')
    monkeypatch.setenv('BACKUP_DEST_SERVICE', 's3')
    
    valid_formats = ['none', 'tar', 'tar.gz', 'tar.bz2', 'tar.xz', 'tar.zst', 'zip', 'gzip']
    
    for fmt in valid_formats:
        monkeypatch.setenv('BACKUP_COMPRESSION', fmt)
        config = load_config()
        assert config['compression'] == fmt


def test_load_config_encryption_enabled_no_recipient(monkeypatch):
    monkeypatch.setenv('BACKUP_SOURCE_PATH', '/source')
    monkeypatch.setenv('BACKUP_DEST_SERVICE', 's3')
    monkeypatch.setenv('BACKUP_ENCRYPTION_ENABLED', 'true')
    
    with pytest.raises(ValueError, match="BACKUP_ENCRYPTION_RECIPIENT is required when encryption is enabled"):
        load_config()


def test_load_config_encryption_enabled_with_recipient(monkeypatch):
    monkeypatch.setenv('BACKUP_SOURCE_PATH', '/source')
    monkeypatch.setenv('BACKUP_DEST_SERVICE', 's3')
    monkeypatch.setenv('BACKUP_ENCRYPTION_ENABLED', 'true')
    monkeypatch.setenv('BACKUP_ENCRYPTION_RECIPIENT', 'age1test123')
    
    config = load_config()
    
    assert config['encryption_enabled'] is True
    assert config['encryption_recipient'] == 'age1test123'


def test_load_config_encryption_disabled_variations(monkeypatch):
    monkeypatch.setenv('BACKUP_SOURCE_PATH', '/source')
    monkeypatch.setenv('BACKUP_DEST_SERVICE', 's3')
    
    for value in ['false', 'False', 'FALSE', '0', 'no']:
        monkeypatch.setenv('BACKUP_ENCRYPTION_ENABLED', value)
        config = load_config()
        assert config['encryption_enabled'] is False


def test_load_config_retention_settings(monkeypatch):
    monkeypatch.setenv('BACKUP_SOURCE_PATH', '/source')
    monkeypatch.setenv('BACKUP_DEST_SERVICE', 's3')
    monkeypatch.setenv('BACKUP_RETENTION_MAX_BACKUPS', '10')
    monkeypatch.setenv('BACKUP_RETENTION_DAILY', '14')
    monkeypatch.setenv('BACKUP_RETENTION_WEEKLY', '8')
    monkeypatch.setenv('BACKUP_RETENTION_MONTHLY', '12')
    monkeypatch.setenv('BACKUP_RETENTION_YEARLY', '5')
    
    config = load_config()
    
    assert config['retention_max_backups'] == 10
    assert config['retention_daily'] == 14
    assert config['retention_weekly'] == 8
    assert config['retention_monthly'] == 12
    assert config['retention_yearly'] == 5


def test_load_config_dest_root(monkeypatch):
    monkeypatch.setenv('BACKUP_SOURCE_PATH', '/source')
    monkeypatch.setenv('BACKUP_DEST_SERVICE', 's3')
    monkeypatch.setenv('BACKUP_DEST_ROOT', 'backups/prod')
    
    config = load_config()
    
    assert config['dest_root'] == 'backups/prod'


def test_load_config_archive_name(monkeypatch):
    monkeypatch.setenv('BACKUP_SOURCE_PATH', '/source')
    monkeypatch.setenv('BACKUP_DEST_SERVICE', 's3')
    monkeypatch.setenv('BACKUP_ARCHIVE_NAME', 'custom_backup')
    
    config = load_config()
    
    assert config['archive_name'] == 'custom_backup'
