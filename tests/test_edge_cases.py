import pytest
import os
from unittest.mock import Mock, patch
from datetime import datetime
from main import (
    parse_backup_timestamp,
    list_backups,
    list_available_backups,
    cleanup_old_backups,
    backup
)


def test_parse_backup_timestamp_value_error():
    result = parse_backup_timestamp("backup_20999999_999999.tar.gz")
    assert result is None


def test_parse_backup_timestamp_iso_value_error():
    result = parse_backup_timestamp("backup_2099-99-99T99:99:99.tar.gz")
    assert result is None


@patch('main.create_dest_operator')
def test_list_backups_with_exception(mock_create_dest_op):
    mock_op = Mock()
    mock_op.list.side_effect = Exception("Test error")
    
    result = list_backups(mock_op, '')
    
    assert result == []


@patch('main.list_backups')
@patch('main.create_dest_operator')
def test_list_available_backups_with_exception(mock_create_dest_op, mock_list_backups):
    mock_op = Mock()
    mock_create_dest_op.return_value = mock_op
    mock_list_backups.side_effect = Exception("Test error")
    
    result = list_available_backups('fs', '')
    
    assert result == []


def test_cleanup_old_backups_no_retention_policy():
    mock_op = Mock()
    retention_config = {
        'max_backups': 0,
        'daily': 0,
        'weekly': 0,
        'monthly': 0,
        'yearly': 0,
        'dest_root': ''
    }
    
    cleanup_old_backups(mock_op, retention_config)
    
    mock_op.list.assert_not_called()


@patch('main.list_backups')
def test_cleanup_old_backups_no_backups_found(mock_list_backups):
    mock_op = Mock()
    mock_list_backups.return_value = []
    
    retention_config = {
        'max_backups': 5,
        'daily': 7,
        'weekly': 4,
        'monthly': 6,
        'yearly': 2,
        'dest_root': ''
    }
    
    cleanup_old_backups(mock_op, retention_config)
    
    mock_op.delete.assert_not_called()


@patch('main.apply_retention_policy')
@patch('main.list_backups')
def test_cleanup_old_backups_delete_failure(mock_list_backups, mock_apply_retention):
    mock_op = Mock()
    
    backups = [
        {'path': 'backup1.tar.gz', 'timestamp': datetime(2025, 1, 1), 'size': 1024},
        {'path': 'backup2.tar.gz', 'timestamp': datetime(2025, 1, 2), 'size': 1024}
    ]
    mock_list_backups.return_value = backups
    
    to_delete = [backups[0]]
    mock_apply_retention.return_value = to_delete
    
    mock_op.delete.side_effect = Exception("Delete failed")
    
    retention_config = {
        'max_backups': 1,
        'daily': 0,
        'weekly': 0,
        'monthly': 0,
        'yearly': 0,
        'dest_root': ''
    }
    
    cleanup_old_backups(mock_op, retention_config)
    
    mock_op.delete.assert_called_once_with('backup1.tar.gz')


@patch('main.create_dest_operator')
def test_backup_archive_exception(mock_create_dest_op):
    import tempfile
    import shutil
    
    mock_op = Mock()
    mock_create_dest_op.return_value = mock_op
    mock_op.write.side_effect = Exception("Write failed")
    
    source_dir = tempfile.mkdtemp()
    try:
        with open(os.path.join(source_dir, "test.txt"), 'w') as f:
            f.write("test")
        
        result = backup(source_dir, [{'service': 'fs', 'root': ''}], compression='tar.gz', archive_name='test')
        
        assert result is False
    finally:
        shutil.rmtree(source_dir, ignore_errors=True)


@patch('main.create_source_operator')
@patch('main.create_dest_operator')
def test_backup_no_compression_with_failures(mock_create_dest_op, mock_create_source_op):
    mock_src_op = Mock()
    mock_dest_op = Mock()
    
    mock_create_source_op.return_value = mock_src_op
    mock_create_dest_op.return_value = mock_dest_op
    
    mock_src_op.list.return_value = [Mock(path='file1.txt'), Mock(path='file2.txt')]
    
    def create_mock_metadata(is_file_val):
        metadata = Mock()
        metadata.is_file = is_file_val
        metadata.is_dir = not is_file_val
        return metadata
    
    mock_src_op.stat.side_effect = [
        create_mock_metadata(True),
        create_mock_metadata(True)
    ]
    
    mock_src_op.read.side_effect = [b"content1", Exception("Read failed")]
    
    result = backup('/test/source', [{'service': 'fs', 'root': ''}], compression='tar')
    
    assert result is False
