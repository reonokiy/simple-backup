import os
import tempfile
import pytest
from pathlib import Path
from datetime import datetime
from typing import Generator, Dict, Any, List


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_source_dir(temp_dir: str) -> str:
    source = Path(temp_dir) / "source"
    source.mkdir()
    
    (source / "file1.txt").write_text("content1")
    (source / "file2.txt").write_text("content2")
    
    subdir = source / "subdir"
    subdir.mkdir()
    (subdir / "file3.txt").write_text("content3")
    
    return str(source)


@pytest.fixture
def mock_dest_dir(temp_dir: str) -> str:
    dest = Path(temp_dir) / "dest"
    dest.mkdir()
    return str(dest)


@pytest.fixture
def age_keypair() -> Dict[str, str]:
    from pyrage import x25519  # type: ignore
    identity = x25519.Identity.generate()
    recipient = identity.to_public()
    
    return {
        'identity': str(identity),
        'recipient': str(recipient)
    }


@pytest.fixture
def mock_env(monkeypatch: pytest.MonkeyPatch, mock_source_dir: str, mock_dest_dir: str) -> Dict[str, str]:
    env_vars = {
        'BACKUP_SOURCE_PATH': mock_source_dir,
        'BACKUP_DEST_SERVICE': 'fs',
        'BACKUP_DEST_ROOT': '',
        'FS_ROOT': mock_dest_dir,
        'BACKUP_COMPRESSION': 'tar.zst',
        'BACKUP_RETENTION_MAX_BACKUPS': '5',
        'BACKUP_RETENTION_DAILY': '7',
        'BACKUP_RETENTION_WEEKLY': '4',
        'BACKUP_RETENTION_MONTHLY': '6',
        'BACKUP_RETENTION_YEARLY': '2',
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    return env_vars


@pytest.fixture
def sample_backups() -> List[Dict[str, Any]]:
    now = datetime.now()
    return [
        {'path': 'backup_20240101_120000.tar.gz', 'timestamp': datetime(2024, 1, 1, 12, 0, 0), 'size': 1024},
        {'path': 'backup_20240102_120000.tar.gz', 'timestamp': datetime(2024, 1, 2, 12, 0, 0), 'size': 2048},
        {'path': 'backup_20240201_120000.tar.gz', 'timestamp': datetime(2024, 2, 1, 12, 0, 0), 'size': 1536},
        {'path': 'backup_20240301_120000.tar.gz', 'timestamp': datetime(2024, 3, 1, 12, 0, 0), 'size': 2560},
    ]
