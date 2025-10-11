import pytest
import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
from main import run_backup_job, main


def test_run_backup_job_success():
    with patch('main.load_config') as mock_load_config, \
         patch('main.backup') as mock_backup, \
         patch('main.validate_destinations') as mock_validate:
        
        mock_load_config.return_value = {
            'source_path': '/test/source',
            'destinations': [{'service': 'fs', 'root': '/test/dest', 'storage': {}}],
            'compression': 'tar.gz',
            'archive_name': 'test',
            'retention_max_backups': 5,
            'retention_daily': 7,
            'retention_weekly': 4,
            'retention_monthly': 6,
            'retention_yearly': 2,
            'encryption_enabled': False,
            'encryption_recipient': None
        }
        
        mock_validate.return_value = True
        
        run_backup_job()
        
        mock_validate.assert_called_once()
        mock_backup.assert_called_once()


def test_run_backup_job_failure():
    with patch('main.load_config') as mock_load_config:
        mock_load_config.side_effect = ValueError("Test error")
        
        run_backup_job()


def test_main_restore_command():
    with patch('main.restore') as mock_restore, \
         patch('sys.argv', ['main.py', 'restore', 'backup.tar.gz', '/dest', '--dest-service', 'fs']):
        
        mock_restore.return_value = True
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0
        mock_restore.assert_called_once_with('backup.tar.gz', '/dest', 'fs', None)


def test_main_restore_command_with_identity():
    with patch('main.restore') as mock_restore, \
         patch('sys.argv', ['main.py', 'restore', 'backup.tar.gz.age', '/dest', '--identity-key', 'AGE-SECRET-KEY-123']):
        
        mock_restore.return_value = True
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0
        mock_restore.assert_called_once_with('backup.tar.gz.age', '/dest', 'fs', 'AGE-SECRET-KEY-123')


def test_main_restore_command_failure():
    with patch('main.restore') as mock_restore, \
         patch('sys.argv', ['main.py', 'restore', 'backup.tar.gz', '/dest']):
        
        mock_restore.return_value = False
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1


def test_main_restore_command_with_env_identity():
    with patch('main.restore') as mock_restore, \
         patch('sys.argv', ['main.py', 'restore', 'backup.tar.gz.age', '/dest']), \
         patch.dict(os.environ, {'AGE_IDENTITY_KEY': 'AGE-SECRET-KEY-ENV'}):
        
        mock_restore.return_value = True
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0
        mock_restore.assert_called_once_with('backup.tar.gz.age', '/dest', 'fs', 'AGE-SECRET-KEY-ENV')


def test_main_list_command():
    with patch('main.list_available_backups') as mock_list, \
         patch('sys.argv', ['main.py', 'list', '--dest-service', 'fs', '--dest-root', '/backups']):
        
        mock_list.return_value = []
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0
        mock_list.assert_called_once_with('fs', '/backups')


def test_main_list_command_defaults():
    with patch('main.list_available_backups') as mock_list, \
         patch('sys.argv', ['main.py', 'list']):
        
        mock_list.return_value = []
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0
        mock_list.assert_called_once_with('fs', '')


def test_main_backup_command_one_time():
    with patch('main.load_config') as mock_load_config, \
         patch('main.backup') as mock_backup, \
         patch('sys.argv', ['main.py']):
        
        mock_load_config.return_value = {
            'source_path': '/test/source',
            'dest_service': 'fs',
            'dest_root': '/test/dest',
            'compression': 'tar.gz',
            'archive_name': 'test',
            'cron_schedule': None,
            'retention_max_backups': 5,
            'retention_daily': 7,
            'retention_weekly': 4,
            'retention_monthly': 6,
            'retention_yearly': 2,
            'encryption_enabled': False,
            'encryption_recipient': None
        }
        mock_backup.return_value = True
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 0
        mock_backup.assert_called_once()


def test_main_backup_command_one_time_failure():
    with patch('main.load_config') as mock_load_config, \
         patch('main.backup') as mock_backup, \
         patch('sys.argv', ['main.py']):
        
        mock_load_config.return_value = {
            'source_path': '/test/source',
            'dest_service': 'fs',
            'dest_root': '/test/dest',
            'compression': 'tar.gz',
            'archive_name': 'test',
            'cron_schedule': None,
            'retention_max_backups': 5,
            'retention_daily': 7,
            'retention_weekly': 4,
            'retention_monthly': 6,
            'retention_yearly': 2,
            'encryption_enabled': False,
            'encryption_recipient': None
        }
        mock_backup.return_value = False
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1


def test_main_backup_command_config_error():
    with patch('main.load_config') as mock_load_config, \
         patch('sys.argv', ['main.py']):
        
        mock_load_config.side_effect = ValueError("Config error")
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1


def test_main_backup_command_with_scheduler():
    with patch('main.load_config') as mock_load_config, \
         patch('main.BlockingScheduler') as mock_scheduler_class, \
         patch('main.signal.signal') as mock_signal, \
         patch('sys.argv', ['main.py']):
        
        mock_load_config.return_value = {
            'source_path': '/test/source',
            'dest_service': 'fs',
            'dest_root': '/test/dest',
            'compression': 'tar.gz',
            'archive_name': 'test',
            'cron_schedule': '0 0 * * *',
            'retention_max_backups': 5,
            'retention_daily': 7,
            'retention_weekly': 4,
            'retention_monthly': 6,
            'retention_yearly': 2,
            'encryption_enabled': False,
            'encryption_recipient': None
        }
        
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        mock_scheduler.start.side_effect = KeyboardInterrupt()
        
        with pytest.raises(KeyboardInterrupt):
            main()
        
        mock_scheduler.add_job.assert_called_once()
        mock_scheduler.start.assert_called_once()
