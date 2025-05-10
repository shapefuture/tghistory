import os
import tarfile
import gzip
import json
import tempfile
from unittest.mock import patch, MagicMock
import pytest

from app.shared.backup import BackupManager

def test_backup_session_files_success(tmp_path, monkeypatch):
    fname = tmp_path / "session.session"
    fname.write_text("dummy")
    monkeypatch.setattr("app.config.settings.TELEGRAM_SESSION_PATH", str(fname))
    out_dir = tmp_path / "backups"
    result, path = BackupManager.backup_session_files(str(out_dir))
    assert result is True
    assert os.path.exists(path)
    assert tarfile.is_tarfile(path)

def test_backup_session_files_missing(monkeypatch):
    monkeypatch.setattr("app.config.settings.TELEGRAM_SESSION_PATH", "/nonexistent/path")
    result, msg = BackupManager.backup_session_files("/tmp")
    assert result is False
    assert "not found" in msg

def test_backup_redis_data_success(tmp_path, monkeypatch):
    # Patch redis client
    fake_redis = MagicMock()
    fake_redis.keys.return_value = [b"strkey", b"hashkey"]
    fake_redis.type.side_effect = lambda k: b"string" if k == "strkey" else b"hash"
    fake_redis.get.return_value = b"foo"
    fake_redis.hgetall.return_value = {b"a": b"b"}
    monkeypatch.setattr("app.shared.redis_client.get_redis_connection", lambda _: fake_redis)
    monkeypatch.setattr("app.config.settings.OUTPUT_DIR_PATH", str(tmp_path))
    ok, path = BackupManager.backup_redis_data(str(tmp_path))
    assert ok is True
    with gzip.open(path, "rt") as f:
        data = json.load(f)
        assert "strkey" in data and "hashkey" in data

def test_restore_redis_backup_success(tmp_path, monkeypatch):
    # Prepare backup file
    backup = {
        "strkey": {"type": "string", "value": "foo"},
        "hashkey": {"type": "hash", "value": {"a": "b"}}
    }
    fname = tmp_path / "backup.json.gz"
    with gzip.open(fname, "wt") as f:
        json.dump(backup, f)
    fake_redis = MagicMock()
    fake_redis.exists.return_value = False
    monkeypatch.setattr("app.shared.redis_client.get_redis_connection", lambda _: fake_redis)
    ok, msg = BackupManager.restore_redis_backup(str(fname), overwrite=True)
    assert ok is True
    assert "processed" in msg

def test_apply_retention_policy(tmp_path):
    backupdir = tmp_path / "backups"
    backupdir.mkdir()
    for i in range(10):
        f = backupdir / f"b{i}.tar.gz"
        f.write_text("data")
        os.utime(f, (time.time() - (i+1)*86400, time.time() - (i+1)*86400))
    ok, msg = BackupManager.apply_retention_policy(str(backupdir), days_to_keep=4, min_backups_to_keep=3)
    assert ok is True
    assert "deleted" in msg

def test_cleanup_old_files(tmp_path):
    outdir = tmp_path / "output"
    outdir.mkdir()
    f1 = outdir / "participants_1.txt"
    f1.write_text("data")
    os.utime(f1, (time.time() - 10*86400, time.time() - 10*86400))
    f2 = outdir / "participants_2.txt"
    f2.write_text("data2")
    ok, msg = BackupManager.cleanup_old_files(str(outdir), days_to_keep=5)
    assert ok is True
    assert "deleted" in msg
