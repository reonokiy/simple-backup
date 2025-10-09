import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from main import create_source_operator, create_dest_operator, backup_file, list_files_recursive


def test_create_source_operator(temp_dir):
    op = create_source_operator(temp_dir)
    
    assert op is not None


def test_create_dest_operator_fs(monkeypatch, temp_dir):
    monkeypatch.setenv('FS_ROOT', temp_dir)
    
    op = create_dest_operator('fs')
    
    assert op is not None


def test_create_dest_operator_s3(monkeypatch):
    monkeypatch.setenv('S3_BUCKET', 'my-bucket')
    monkeypatch.setenv('S3_REGION', 'us-east-1')
    monkeypatch.setenv('S3_ACCESS_KEY_ID', 'test-key')
    monkeypatch.setenv('S3_SECRET_ACCESS_KEY', 'test-secret')
    
    op = create_dest_operator('s3')
    
    assert op is not None


def test_create_dest_operator_unsupported():
    import pytest
    
    with pytest.raises(ValueError, match="Unsupported service type"):
        create_dest_operator('unsupported_service')


def test_backup_file_success():
    src_op = Mock()
    dest_op = Mock()
    src_op.read.return_value = b"file content"
    
    result = backup_file(src_op, dest_op, 'file.txt', '')
    
    assert result is True
    src_op.read.assert_called_once_with('file.txt')
    dest_op.write.assert_called_once_with('file.txt', b"file content")


def test_backup_file_with_dest_root():
    src_op = Mock()
    dest_op = Mock()
    src_op.read.return_value = b"file content"
    
    result = backup_file(src_op, dest_op, 'file.txt', 'backups/')
    
    assert result is True
    dest_op.write.assert_called_once_with('backups/file.txt', b"file content")


def test_backup_file_failure():
    src_op = Mock()
    dest_op = Mock()
    src_op.read.side_effect = Exception("Read error")
    
    result = backup_file(src_op, dest_op, 'file.txt', '')
    
    assert result is False


def test_list_files_recursive():
    op = Mock()
    
    file_entry1 = Mock()
    file_entry1.path = 'file1.txt'
    file_metadata1 = Mock()
    file_metadata1.is_file.return_value = True
    file_metadata1.is_dir.return_value = False
    
    file_entry2 = Mock()
    file_entry2.path = 'file2.txt'
    file_metadata2 = Mock()
    file_metadata2.is_file.return_value = True
    file_metadata2.is_dir.return_value = False
    
    op.list.return_value = [file_entry1, file_entry2]
    op.stat.side_effect = [file_metadata1, file_metadata2]
    
    files = list_files_recursive(op, '')
    
    assert len(files) == 2
    assert 'file1.txt' in files
    assert 'file2.txt' in files


def test_list_files_recursive_with_dirs():
    op = Mock()
    
    dir_entry = Mock()
    dir_entry.path = 'subdir'
    dir_metadata = Mock()
    dir_metadata.is_file = False
    dir_metadata.is_dir = True
    
    file_entry = Mock()
    file_entry.path = 'subdir/file.txt'
    file_metadata = Mock()
    file_metadata.is_file = True
    file_metadata.is_dir = False
    
    op.list.side_effect = [[dir_entry], [file_entry]]
    op.stat.side_effect = [dir_metadata, file_metadata]
    
    files = list_files_recursive(op, '')
    
    assert len(files) == 1
    assert 'subdir/file.txt' in files


def test_list_files_recursive_error_handling():
    op = Mock()
    op.list.side_effect = Exception("List error")
    
    files = list_files_recursive(op, '')
    
    assert len(files) == 0
