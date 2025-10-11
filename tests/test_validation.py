import pytest
from unittest.mock import Mock, patch, MagicMock
from main import validate_destination_connectivity, validate_destinations


def test_destination_connectivity_success():
    mock_op = Mock()
    mock_op.write = Mock()
    mock_op.read = Mock(return_value=b'test')
    mock_op.delete = Mock()
    
    with patch('main.create_dest_operator', return_value=mock_op):
        dest = {
            'service': 's3',
            'root': 'backups/',
            'storage': {'bucket': 'test-bucket'}
        }
        
        result = validate_destination_connectivity(dest)
        
        assert result is True
        mock_op.write.assert_called_once()
        mock_op.read.assert_called_once()
        mock_op.delete.assert_called_once()


def test_destination_connectivity_write_failure():
    mock_op = Mock()
    mock_op.write = Mock(side_effect=Exception("Write failed"))
    
    with patch('main.create_dest_operator', return_value=mock_op):
        dest = {
            'service': 's3',
            'root': 'backups/',
            'storage': {'bucket': 'test-bucket'}
        }
        
        result = validate_destination_connectivity(dest)
        
        assert result is False


def test_destination_connectivity_read_failure():
    mock_op = Mock()
    mock_op.write = Mock()
    mock_op.read = Mock(side_effect=Exception("Read failed"))
    
    with patch('main.create_dest_operator', return_value=mock_op):
        dest = {
            'service': 's3',
            'root': 'backups/',
            'storage': {'bucket': 'test-bucket'}
        }
        
        result = validate_destination_connectivity(dest)
        
        assert result is False


def test_destination_connectivity_data_mismatch():
    mock_op = Mock()
    mock_op.write = Mock()
    mock_op.read = Mock(return_value=b'wrong_data')
    
    with patch('main.create_dest_operator', return_value=mock_op):
        dest = {
            'service': 's3',
            'root': 'backups/',
            'storage': {'bucket': 'test-bucket'}
        }
        
        result = validate_destination_connectivity(dest)
        
        assert result is False


def test_validate_destinations_all_success():
    destinations = [
        {'service': 's3', 'root': 'backups/', 'storage': {'bucket': 'bucket1'}},
        {'service': 'azblob', 'root': 'backups/', 'storage': {'container': 'container1'}},
    ]
    
    with patch('main.validate_destination_connectivity', return_value=True):
        result = validate_destinations(destinations)
        
        assert result is True


def test_validate_destinations_partial_failure():
    destinations = [
        {'service': 's3', 'root': 'backups/', 'storage': {'bucket': 'bucket1'}},
        {'service': 'azblob', 'root': 'backups/', 'storage': {'container': 'container1'}},
    ]
    
    def mock_connectivity(dest):
        if dest['service'] == 's3':
            return True
        return False
    
    with patch('main.validate_destination_connectivity', side_effect=mock_connectivity):
        result = validate_destinations(destinations)
        
        assert result is False


def test_validate_destinations_all_failure():
    destinations = [
        {'service': 's3', 'root': 'backups/', 'storage': {'bucket': 'bucket1'}},
        {'service': 'azblob', 'root': 'backups/', 'storage': {'container': 'container1'}},
    ]
    
    with patch('main.validate_destination_connectivity', return_value=False):
        result = validate_destinations(destinations)
        
        assert result is False


def test_validate_destinations_empty_root():
    mock_op = Mock()
    mock_op.write = Mock()
    mock_op.read = Mock(return_value=b'test')
    mock_op.delete = Mock()
    
    with patch('main.create_dest_operator', return_value=mock_op):
        dest = {
            'service': 's3',
            'root': '',
            'storage': {'bucket': 'test-bucket'}
        }
        
        result = validate_destination_connectivity(dest)
        
        assert result is True
        call_args = mock_op.write.call_args[0]
        assert call_args[0] == '.simple-backup-test'
