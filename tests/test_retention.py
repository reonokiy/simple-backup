from datetime import datetime, timedelta
from main import parse_backup_timestamp, apply_retention_policy, list_backups


def test_parse_backup_timestamp_standard_format():
    filename = 'backup_myapp_20240315_143022.tar.gz'
    timestamp = parse_backup_timestamp(filename)
    
    assert timestamp is not None
    assert timestamp.year == 2024
    assert timestamp.month == 3
    assert timestamp.day == 15
    assert timestamp.hour == 14
    assert timestamp.minute == 30
    assert timestamp.second == 22


def test_parse_backup_timestamp_simple_format():
    filename = '20240315_143022.tar.gz'
    timestamp = parse_backup_timestamp(filename)
    
    assert timestamp is not None
    assert timestamp.year == 2024
    assert timestamp.month == 3
    assert timestamp.day == 15


def test_parse_backup_timestamp_iso_format():
    filename = 'backup_2024-03-15T14:30:22.tar.gz'
    timestamp = parse_backup_timestamp(filename)
    
    assert timestamp is not None
    assert timestamp.year == 2024
    assert timestamp.month == 3
    assert timestamp.day == 15


def test_parse_backup_timestamp_no_match():
    filename = 'random_file.tar.gz'
    timestamp = parse_backup_timestamp(filename)
    
    assert timestamp is None


def test_parse_backup_timestamp_encrypted():
    filename = 'backup_myapp_20240315_143022.tar.zst.age'
    timestamp = parse_backup_timestamp(filename)
    
    assert timestamp is not None
    assert timestamp.year == 2024


def test_apply_retention_policy_daily():
    now = datetime.now()
    backups = [
        {'path': f'backup_{i}.tar.gz', 'timestamp': now - timedelta(days=i), 'size': 1024}
        for i in range(10)
    ]
    
    to_delete = apply_retention_policy(backups, daily=3)
    
    kept_count = len(backups) - len(to_delete)
    assert kept_count >= 3


def test_apply_retention_policy_weekly():
    now = datetime.now()
    backups = []
    
    for week in range(8):
        timestamp = now - timedelta(weeks=week)
        backups.append({
            'path': f'backup_week_{week}.tar.gz',
            'timestamp': timestamp,
            'size': 1024
        })
    
    to_delete = apply_retention_policy(backups, weekly=4)
    
    kept_count = len(backups) - len(to_delete)
    assert kept_count >= 4


def test_apply_retention_policy_monthly():
    backups = []
    
    for month in range(12):
        timestamp = datetime(2024, 12 - month, 15, 12, 0, 0) if 12 - month > 0 else datetime(2023, 12 + (12 - month), 15, 12, 0, 0)
        backups.append({
            'path': f'backup_month_{month}.tar.gz',
            'timestamp': timestamp,
            'size': 1024
        })
    
    to_delete = apply_retention_policy(backups, monthly=6)
    
    kept_count = len(backups) - len(to_delete)
    assert kept_count >= 6


def test_apply_retention_policy_yearly():
    backups = []
    
    for year in range(5):
        timestamp = datetime(2024 - year, 6, 15, 12, 0, 0)
        backups.append({
            'path': f'backup_year_{year}.tar.gz',
            'timestamp': timestamp,
            'size': 1024
        })
    
    to_delete = apply_retention_policy(backups, yearly=3)
    
    kept_count = len(backups) - len(to_delete)
    assert kept_count >= 3


def test_apply_retention_policy_max_backups():
    now = datetime.now()
    backups = [
        {'path': f'backup_{i}.tar.gz', 'timestamp': now - timedelta(hours=i), 'size': 1024}
        for i in range(20)
    ]
    
    to_delete = apply_retention_policy(backups, max_backups=5, daily=0, weekly=0, monthly=0, yearly=0)
    
    kept_count = len(backups) - len(to_delete)
    assert kept_count == 5


def test_apply_retention_policy_combined():
    now = datetime.now()
    backups = []
    
    for day in range(30):
        backups.append({
            'path': f'backup_day_{day}.tar.gz',
            'timestamp': now - timedelta(days=day),
            'size': 1024
        })
    
    to_delete = apply_retention_policy(
        backups,
        max_backups=3,
        daily=7,
        weekly=2
    )
    
    kept_count = len(backups) - len(to_delete)
    assert kept_count >= 3


def test_apply_retention_policy_empty_backups():
    to_delete = apply_retention_policy([], daily=7)
    
    assert len(to_delete) == 0


def test_apply_retention_policy_no_deletion_needed():
    now = datetime.now()
    backups = [
        {'path': f'backup_{i}.tar.gz', 'timestamp': now - timedelta(days=i), 'size': 1024}
        for i in range(3)
    ]
    
    to_delete = apply_retention_policy(backups, daily=7)
    
    assert len(to_delete) == 0


def test_apply_retention_policy_multiple_same_day():
    now = datetime.now()
    backups = [
        {'path': f'backup_{i}.tar.gz', 'timestamp': now - timedelta(hours=i), 'size': 1024}
        for i in range(5)
    ]
    
    to_delete = apply_retention_policy(backups, daily=1)
    
    kept = [b for b in backups if b not in to_delete]
    assert len(kept) >= 1


def test_apply_retention_policy_preserves_most_recent():
    now = datetime.now()
    backups = [
        {'path': 'backup_0.tar.gz', 'timestamp': now, 'size': 1024},
        {'path': 'backup_1.tar.gz', 'timestamp': now - timedelta(days=100), 'size': 1024},
    ]
    
    to_delete = apply_retention_policy(backups, max_backups=1)
    
    kept = [b for b in backups if b not in to_delete]
    assert len(kept) >= 1
    assert kept[0]['path'] == 'backup_0.tar.gz'
