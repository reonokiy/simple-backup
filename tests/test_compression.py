import os
import tarfile
import zipfile
import gzip
import tempfile
from pathlib import Path
from main import create_archive


def test_create_archive_tar(mock_source_dir):
    archive_path, temp_dir = create_archive(mock_source_dir, 'tar', 'test_backup')
    
    try:
        assert os.path.exists(archive_path)
        assert archive_path.endswith('.tar')
        
        with tarfile.open(archive_path, 'r') as tar:
            members = tar.getnames()
            assert 'source/file1.txt' in members
            assert 'source/file2.txt' in members
            assert 'source/subdir/file3.txt' in members
    finally:
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)


def test_create_archive_tar_gz(mock_source_dir):
    archive_path, temp_dir = create_archive(mock_source_dir, 'tar.gz', 'test_backup')
    
    try:
        assert os.path.exists(archive_path)
        assert archive_path.endswith('.tar.gz')
        
        with tarfile.open(archive_path, 'r:gz') as tar:
            members = tar.getnames()
            assert len(members) > 0
    finally:
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)


def test_create_archive_tar_bz2(mock_source_dir):
    archive_path, temp_dir = create_archive(mock_source_dir, 'tar.bz2', 'test_backup')
    
    try:
        assert os.path.exists(archive_path)
        assert archive_path.endswith('.tar.bz2')
        
        with tarfile.open(archive_path, 'r:bz2') as tar:
            members = tar.getnames()
            assert len(members) > 0
    finally:
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)


def test_create_archive_tar_xz(mock_source_dir):
    archive_path, temp_dir = create_archive(mock_source_dir, 'tar.xz', 'test_backup')
    
    try:
        assert os.path.exists(archive_path)
        assert archive_path.endswith('.tar.xz')
        
        with tarfile.open(archive_path, 'r:xz') as tar:
            members = tar.getnames()
            assert len(members) > 0
    finally:
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)


def test_create_archive_tar_zst(mock_source_dir):
    archive_path, temp_dir = create_archive(mock_source_dir, 'tar.zst', 'test_backup')
    
    try:
        assert os.path.exists(archive_path)
        assert archive_path.endswith('.tar.zst')
        
        file_size = os.path.getsize(archive_path)
        assert file_size > 0
    finally:
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)


def test_create_archive_zip(mock_source_dir):
    archive_path, temp_dir = create_archive(mock_source_dir, 'zip', 'test_backup')
    
    try:
        assert os.path.exists(archive_path)
        assert archive_path.endswith('.zip')
        
        with zipfile.ZipFile(archive_path, 'r') as zipf:
            members = zipf.namelist()
            assert 'source/file1.txt' in members
            assert 'source/file2.txt' in members
            assert 'source/subdir/file3.txt' in members
    finally:
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)


def test_create_archive_gzip_single_file(temp_dir):
    source_file = Path(temp_dir) / "test.txt"
    source_file.write_text("test content")
    
    archive_path, archive_temp_dir = create_archive(str(source_file), 'gzip', 'test_backup')
    
    try:
        assert os.path.exists(archive_path)
        assert archive_path.endswith('.gz')
        
        with gzip.open(archive_path, 'rb') as f:
            content = f.read()
            assert content == b"test content"
    finally:
        if os.path.exists(archive_temp_dir):
            import shutil
            shutil.rmtree(archive_temp_dir)


def test_create_archive_gzip_directory_fails(mock_source_dir):
    import pytest
    
    with pytest.raises(ValueError, match="gzip compression only supports single files"):
        create_archive(mock_source_dir, 'gzip', 'test_backup')


def test_create_archive_auto_name(mock_source_dir):
    archive_path, temp_dir = create_archive(mock_source_dir, 'tar')
    
    try:
        assert os.path.exists(archive_path)
        
        filename = Path(archive_path).stem
        assert filename.startswith('backup_source_')
    finally:
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)


def test_create_archive_custom_name(mock_source_dir):
    archive_path, temp_dir = create_archive(mock_source_dir, 'tar', 'my_custom_backup')
    
    try:
        assert 'my_custom_backup.tar' in archive_path
    finally:
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)


def test_create_archive_unsupported_format(mock_source_dir):
    import pytest
    
    with pytest.raises(ValueError, match="Unsupported compression format"):
        create_archive(mock_source_dir, 'invalid_format')


def test_create_archive_zip_single_file(temp_dir):
    source_file = Path(temp_dir) / "test.txt"
    source_file.write_text("test content")
    
    archive_path, archive_temp_dir = create_archive(str(source_file), 'zip', 'test_backup')
    
    try:
        assert os.path.exists(archive_path)
        assert archive_path.endswith('.zip')
        
        with zipfile.ZipFile(archive_path, 'r') as zipf:
            files = zipf.namelist()
            assert 'test.txt' in files
            content = zipf.read('test.txt')
            assert content == b"test content"
    finally:
        if os.path.exists(archive_temp_dir):
            import shutil
            shutil.rmtree(archive_temp_dir)
