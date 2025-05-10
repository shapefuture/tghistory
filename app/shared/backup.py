import os
import glob
import tarfile
import gzip
import json
import time
import logging
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime

from app.shared.redis_client import get_redis_connection
from app import config

logger = logging.getLogger("backup")

class BackupManager:
    @staticmethod
    def backup_session_files(backup_dir: Optional[str] = None) -> Tuple[bool, str]:
        logger.debug(f"[ENTRY] backup_session_files called: backup_dir={backup_dir}")
        try:
            if not backup_dir:
                backup_dir = os.path.join(config.settings.OUTPUT_DIR_PATH, "backups")
            logger.debug(f"Resolved backup_dir={backup_dir}")
            os.makedirs(backup_dir, exist_ok=True)
            session_path = config.settings.TELEGRAM_SESSION_PATH
            logger.debug(f"Session path: {session_path}")
            if not os.path.exists(session_path):
                logger.error(f"Session file not found: {session_path}")
                return False, f"Session file not found: {session_path}"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"session_backup_{timestamp}.tar.gz"
            backup_path = os.path.join(backup_dir, backup_filename)
            logger.debug(f"Creating tar.gz backup: {backup_path}")
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(session_path, arcname=os.path.basename(session_path))
                for related_file in glob.glob(f"{session_path}*"):
                    if related_file != session_path:
                        tar.add(related_file, arcname=os.path.basename(related_file))
            logger.info(f"Session backup created: {backup_path}")
            logger.debug(f"[EXIT] backup_session_files returning (True, {backup_path})")
            return True, backup_path
        except Exception as e:
            logger.error(f"[ERROR] Session backup failed: {e}", exc_info=True)
            return False, f"Session backup failed: {str(e)}"

    @staticmethod
    def backup_redis_data(
        backup_dir: Optional[str] = None, 
        key_patterns: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        logger.debug(f"[ENTRY] backup_redis_data called: backup_dir={backup_dir}, key_patterns={key_patterns}")
        try:
            if not backup_dir:
                backup_dir = os.path.join(config.settings.OUTPUT_DIR_PATH, "backups")
            logger.debug(f"Resolved backup_dir={backup_dir}")
            os.makedirs(backup_dir, exist_ok=True)
            if not key_patterns:
                key_patterns = ["request:*", "user:*"]
            logger.debug(f"Using key_patterns: {key_patterns}")
            redis_conn = get_redis_connection(config.settings)
            backup_data = {}
            all_keys = set()
            for pattern in key_patterns:
                keys = redis_conn.keys(pattern)
                logger.debug(f"Pattern {pattern} matched keys: {keys}")
                all_keys.update([k.decode() if isinstance(k, bytes) else k for k in keys])
            logger.debug(f"Backing up keys: {all_keys}")
            for key in all_keys:
                try:
                    key_type = redis_conn.type(key).decode()
                    logger.debug(f"Key {key}: type={key_type}")
                    if key_type == "string":
                        value = redis_conn.get(key)
                        backup_data[key] = {
                            "type": "string",
                            "value": value.decode() if isinstance(value, bytes) else value
                        }
                    elif key_type == "hash":
                        hash_data = redis_conn.hgetall(key)
                        backup_data[key] = {
                            "type": "hash",
                            "value": {
                                k.decode() if isinstance(k, bytes) else k: 
                                v.decode() if isinstance(v, bytes) else v
                                for k, v in hash_data.items()
                            }
                        }
                    elif key_type == "list":
                        list_data = redis_conn.lrange(key, 0, -1)
                        backup_data[key] = {
                            "type": "list",
                            "value": [
                                item.decode() if isinstance(item, bytes) else item
                                for item in list_data
                            ]
                        }
                    elif key_type == "set":
                        set_data = redis_conn.smembers(key)
                        backup_data[key] = {
                            "type": "set",
                            "value": [
                                item.decode() if isinstance(item, bytes) else item
                                for item in set_data
                            ]
                        }
                    elif key_type == "zset":
                        zset_data = redis_conn.zrange(key, 0, -1, withscores=True)
                        backup_data[key] = {
                            "type": "zset",
                            "value": [
                                {
                                    "member": item[0].decode() if isinstance(item[0], bytes) else item[0],
                                    "score": item[1]
                                }
                                for item in zset_data
                            ]
                        }
                    ttl = redis_conn.ttl(key)
                    if ttl > 0:
                        backup_data[key]["ttl"] = ttl
                except Exception as key_exc:
                    logger.error(f"[ERROR] Failed to backup key {key}: {key_exc}", exc_info=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"redis_backup_{timestamp}.json.gz"
            backup_path = os.path.join(backup_dir, backup_filename)
            logger.debug(f"Writing backup to {backup_path}")
            with gzip.open(backup_path, "wt", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2)
            logger.info(f"Redis backup created: {backup_path} ({len(all_keys)} keys)")
            logger.debug(f"[EXIT] backup_redis_data returning (True, {backup_path})")
            return True, backup_path
        except Exception as e:
            logger.error(f"[ERROR] Redis backup failed: {e}", exc_info=True)
            return False, f"Redis backup failed: {str(e)}"

    @staticmethod
    def restore_redis_backup(backup_path: str, overwrite: bool = False) -> Tuple[bool, str]:
        logger.debug(f"[ENTRY] restore_redis_backup called: backup_path={backup_path}, overwrite={overwrite}")
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return False, f"Backup file not found: {backup_path}"
            redis_conn = get_redis_connection(config.settings)
            with gzip.open(backup_path, "rt", encoding="utf-8") as f:
                backup_data = json.load(f)
            stats = {"processed": 0, "skipped": 0, "errors": 0}
            for key, data in backup_data.items():
                try:
                    if not overwrite and redis_conn.exists(key):
                        stats["skipped"] += 1
                        logger.debug(f"Skipped restoring key {key}: already exists and overwrite=False")
                        continue
                    key_type = data["type"]
                    value = data["value"]
                    ttl = data.get("ttl")
                    if key_type == "string":
                        redis_conn.set(key, value)
                    elif key_type == "hash":
                        redis_conn.delete(key)
                        if value:
                            redis_conn.hset(key, mapping=value)
                    elif key_type == "list":
                        redis_conn.delete(key)
                        if value:
                            redis_conn.rpush(key, *value)
                    elif key_type == "set":
                        redis_conn.delete(key)
                        if value:
                            redis_conn.sadd(key, *value)
                    elif key_type == "zset":
                        redis_conn.delete(key)
                        if value:
                            for item in value:
                                redis_conn.zadd(key, {item["member"]: item["score"]})
                    if ttl is not None and ttl > 0:
                        redis_conn.expire(key, ttl)
                    stats["processed"] += 1
                    logger.debug(f"Restored key {key}")
                except Exception as e:
                    logger.error(f"Error restoring key {key}: {e}", exc_info=True)
                    stats["errors"] += 1
            result_msg = (
                f"Restore completed: {stats['processed']} keys processed, "
                f"{stats['skipped']} keys skipped, {stats['errors']} errors"
            )
            logger.info(result_msg)
            logger.debug(f"[EXIT] restore_redis_backup: {result_msg}")
            return stats["errors"] == 0, result_msg
        except Exception as e:
            logger.error(f"[ERROR] Redis restore failed: {e}", exc_info=True)
            return False, f"Redis restore failed: {str(e)}"

    @staticmethod
    def apply_retention_policy(
        backup_dir: Optional[str] = None,
        days_to_keep: int = 30,
        min_backups_to_keep: int = 5
    ) -> Tuple[bool, str]:
        logger.debug(f"[ENTRY] apply_retention_policy called: backup_dir={backup_dir}, days_to_keep={days_to_keep}, min_backups_to_keep={min_backups_to_keep}")
        try:
            if not backup_dir:
                backup_dir = os.path.join(config.settings.OUTPUT_DIR_PATH, "backups")
            if not os.path.exists(backup_dir):
                logger.info("Backup directory does not exist, nothing to clean")
                return True, "Backup directory does not exist, nothing to clean"
            backup_files = []
            for filename in os.listdir(backup_dir):
                if filename.endswith((".tar.gz", ".json.gz")):
                    file_path = os.path.join(backup_dir, filename)
                    mtime = os.path.getmtime(file_path)
                    backup_files.append((file_path, mtime))
            backup_files.sort(key=lambda x: x[1], reverse=True)
            cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
            files_to_keep = backup_files[:min_backups_to_keep]
            files_to_delete = [
                file_path for file_path, mtime in backup_files[min_backups_to_keep:]
                if mtime < cutoff_time
            ]
            deleted_count = 0
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    logger.debug(f"Deleted old backup file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete backup file {file_path}: {e}", exc_info=True)
            result_msg = (
                f"Retention policy applied: kept {len(files_to_keep)} files, "
                f"deleted {deleted_count} old files"
            )
            logger.info(result_msg)
            logger.debug(f"[EXIT] apply_retention_policy: {result_msg}")
            return True, result_msg
        except Exception as e:
            logger.error(f"[ERROR] Failed to apply retention policy: {e}", exc_info=True)
            return False, f"Failed to apply retention policy: {str(e)}"

    @staticmethod
    def cleanup_old_files(
        output_dir: Optional[str] = None,
        days_to_keep: int = 7,
        file_patterns: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        logger.debug(f"[ENTRY] cleanup_old_files called: output_dir={output_dir}, days_to_keep={days_to_keep}, file_patterns={file_patterns}")
        try:
            if not output_dir:
                output_dir = config.settings.OUTPUT_DIR_PATH
            if not os.path.exists(output_dir):
                logger.info("Output directory does not exist, nothing to clean")
                return True, "Output directory does not exist, nothing to clean"
            if not file_patterns:
                file_patterns = ["participants_*.txt"]
            cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
            deleted_count = 0
            checked_count = 0
            for pattern in file_patterns:
                for file_path in glob.glob(os.path.join(output_dir, pattern)):
                    checked_count += 1
                    try:
                        mtime = os.path.getmtime(file_path)
                        if mtime < cutoff_time:
                            os.remove(file_path)
                            deleted_count += 1
                            logger.debug(f"Deleted old output file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to check/delete file {file_path}: {e}", exc_info=True)
            result_msg = (
                f"Cleanup completed: {deleted_count} files deleted "
                f"out of {checked_count} checked"
            )
            logger.info(result_msg)
            logger.debug(f"[EXIT] cleanup_old_files: {result_msg}")
            return True, result_msg
        except Exception as e:
            logger.error(f"[ERROR] Cleanup failed: {e}", exc_info=True)
            return False, f"Cleanup failed: {str(e)}"
