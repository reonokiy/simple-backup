import os
import pytest
import tempfile
import tomllib
from pathlib import Path
from main import load_config


def test_load_config_minimal(monkeypatch):
    monkeypatch.setenv('BACKUP_SOURCE_PATH', '/source')
    monkeypatch.setenv('BACKUP_DEST_SERVICE', 's3')
    
    config = load_config()
    
    assert config['source_path'] == '/source'
    assert config['compression'] == 'tar.zst'
    assert config['retention_daily'] == 7
    assert config['retention_weekly'] == 4
    assert config['retention_monthly'] == 6
    assert config['retention_yearly'] == 2
    assert config['encryption_enabled'] is False
    assert len(config['destinations']) == 1
    assert config['destinations'][0]['service'] == 's3'


def test_load_config_missing_source_path(monkeypatch):
    monkeypatch.setenv('BACKUP_DEST_SERVICE', 's3')
    
    with pytest.raises(ValueError, match="BACKUP_SOURCE_PATH"):
        load_config()


def test_load_config_missing_dest_service(monkeypatch):
    monkeypatch.setenv('BACKUP_SOURCE_PATH', '/source')
    
    with pytest.raises(ValueError, match="At least one destination is required"):
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


def test_load_config_legacy_dest_root(monkeypatch):
    monkeypatch.setenv('BACKUP_SOURCE_PATH', '/source')
    monkeypatch.setenv('BACKUP_DEST_SERVICE', 's3')
    monkeypatch.setenv('BACKUP_DEST_ROOT', 'backups/prod')
    
    config = load_config()
    
    assert config['destinations'][0]['root'] == 'backups/prod'


def test_load_config_archive_name(monkeypatch):
    monkeypatch.setenv('BACKUP_SOURCE_PATH', '/source')
    monkeypatch.setenv('BACKUP_DEST_SERVICE', 's3')
    monkeypatch.setenv('BACKUP_ARCHIVE_NAME', 'custom_backup')
    
    config = load_config()
    
    assert config['archive_name'] == 'custom_backup'


def test_load_config_multiple_destinations_from_file(monkeypatch, tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
source_path = "/source"
compression = "tar.zst"

[[destinations]]
service = "s3"
root = "backups/"

[destinations.storage]
bucket = "bucket1"
region = "us-east-1"

[[destinations]]
service = "azblob"
root = "backups/"

[destinations.storage]
container = "container1"
account_name = "account1"
""")
    
    monkeypatch.chdir(tmp_path)
    
    config = load_config()
    
    assert config['source_path'] == '/source'
    assert len(config['destinations']) == 2
    assert config['destinations'][0]['service'] == 's3'
    assert config['destinations'][0]['root'] == 'backups/'
    assert config['destinations'][0]['storage']['bucket'] == 'bucket1'
    assert config['destinations'][1]['service'] == 'azblob'
    assert config['destinations'][1]['storage']['container'] == 'container1'


def test_load_config_multiple_destinations_yaml(monkeypatch, tmp_path):
    pytest.importorskip("yaml")
    
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
source_path: /source
compression: tar.zst

destinations:
  - service: s3
    root: backups/
    storage:
      bucket: bucket1
      region: us-east-1
  
  - service: gcs
    root: backups/
    storage:
      bucket: bucket2
      credential: /path/to/creds.json
""")
    
    monkeypatch.chdir(tmp_path)
    
    config = load_config()
    
    assert config['source_path'] == '/source'
    assert len(config['destinations']) == 2
    assert config['destinations'][0]['service'] == 's3'
    assert config['destinations'][1]['service'] == 'gcs'
    assert config['destinations'][1]['storage']['credential'] == '/path/to/creds.json'


def test_load_config_legacy_format_backward_compatibility(monkeypatch, tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("""
source_path = "/source"
dest_service = "s3"
dest_root = "backups/"
compression = "tar.gz"

[storage]
bucket = "my-bucket"
region = "us-west-2"
""")
    
    monkeypatch.chdir(tmp_path)
    
    config = load_config()
    
    assert config['source_path'] == '/source'
    assert len(config['destinations']) == 1
    assert config['destinations'][0]['service'] == 's3'
    assert config['destinations'][0]['root'] == 'backups/'
    assert config['destinations'][0]['storage']['bucket'] == 'my-bucket'
    assert config['compression'] == 'tar.gz'
