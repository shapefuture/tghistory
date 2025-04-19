"""
Backup module for managing data retention and backup.

Provides utilities for backing up critical data and implementing
data retention policies.
"""
import os
import time
import logging
import json
import shutil
import gzip
import tarfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
import glob

from app import config
from app.shared.redis_client import get_redis_connection

logger = logging.getLogger("backup")

class BackupManager:
    """Manages backups and data retention"""
    
    @staticmethod
    def backup_session_files(backup_dir: Optional[str] = None) -> Tuple[bool, str]:
        """
        Backup Telegram session files
        
        Args:
            backup_dir: Directory to store backups (default: config.settings.OUTPUT_DIR_PATH/backups)
            
        Returns:
            Tuple[bool, str]: Success status and backup file path or error message
        """
        try:
            # Use default backup dir if none provided
            if not backup_dir:
                backup_dir = os.path.join(config.settings.OUTPUT_DIR_PATH, "backups")
                
            # Create backup directory if it doesn't exist
            os.makedirs(backup_dir, exist_ok=True)
            
            # Get session file path from config
            session_path = config.settings.TELEGRAM_SESSION_PATH
            if not os.path.exists(session_path):
                return False, f"Session file not found: {session_path}"
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"session_backup_{timestamp}.tar.gz"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Create tar.gz archive with session file and related files
            with tarfile.open(backup_path, "w:gz") as tar:
                # Add main session file
                tar.add(session_path, arcname=os.path.basename(session_path))
                
                # Add related files (.session-journal, etc.)
                session_dir = os.path.dirname(session_path)
                session_name = os.path.basename(session_path)
                for related_file in glob.glob(f"{session_path}*"):
                    if related_file != session_path:
                        tar.add(related_file, arcname=os.path.basename(related_file))
            
            logger.info(f"Session backup created: {backup_path}")
            return True, backup_path
            
        except Exception as e:
            error_msg = f"Session backup failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def backup_redis_data(
        backup_dir: Optional[str] = None, 
        key_patterns: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """
        Backup Redis data to a compressed JSON file
        
        Args:
            backup_dir: Directory to store backups (default: config.settings.OUTPUT_DIR_PATH/backups)
            key_patterns: List of key patterns to backup (default: ["request:*", "user:*"])
            
        Returns:
            Tuple[bool, str]: Success status and backup file path or error message
        """
        try:
            # Use default backup dir if none provided
            if not backup_dir:
                backup_dir = os.path.join(config.settings.OUTPUT_DIR_PATH, "backups")
                
            # Create backup directory if it doesn't exist
            os.makedirs(backup_dir, exist_ok=True)
            
            # Default key patterns if none provided
            if not key_patterns:
                key_patterns = ["request:*", "user:*"]
                
            # Connect to Redis
            redis_conn = get_redis_connection(config.settings)
            
            # Store backup data
            backup_data = {}
            
            # Find all keys matching patterns
            all_keys = set()
            for pattern in key_patterns:
                keys = redis_conn.keys(pattern)
                all_keys.update([k.decode() if isinstance(k, bytes) else k for k in keys])
            
            # Backup each key with appropriate type-specific method
            for key in all_keys:
                key_type = redis_conn.type(key).decode()
                
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
                
                # Get TTL if exists
                ttl = redis_conn.ttl(key)
                if ttl > 0:
                    backup_data[key]["ttl"] = ttl
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"redis_backup_{timestamp}.json.gz"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Save to compressed JSON file
            with gzip.open(backup_path, "wt", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2)
            
            logger.info(f"Redis backup created: {backup_path} ({len(all_keys)} keys)")
            return True, backup_path
            
        except Exception as e:
            error_msg = f"Redis backup failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def restore_redis_backup(backup_path: str, overwrite: bool = False) -> Tuple[bool, str]:
        """
        Restore Redis data from a backup file
        
        Args:
            backup_path: Path to the backup file
            overwrite: Whether to overwrite existing keys
            
        Returns:
            Tuple[bool, str]: Success status and result message
        """
        try:
            if not os.path.exists(backup_path):
                return False, f"Backup file not found: {backup_path}"
                
            # Connect to Redis
            redis_conn = get_redis_connection(config.settings)
            
            # Load backup data
            with gzip.open(backup_path, "rt", encoding="utf-8") as f:
                backup_data = json.load(f)
            
            # Track statistics
            stats = {
                "processed": 0,
                "skipped": 0,
                "errors": 0
            }
            
            # Process each key
            for key, data in backup_data.items():
                try:
                    # Check if key exists and should be skipped
                    if not overwrite and redis_conn.exists(key):
                        stats["skipped"] += 1
                        continue
                    
                    key_type = data["type"]
                    value = data["value"]
                    ttl = data.get("ttl")
                    
                    # Restore based on type
                    if key_type == "string":
                        redis_conn.set(key, value)
                    
                    elif key_type == "hash":
                        redis_conn.delete(key)  # Clear existing hash if any
                        if value:  # Only set if not empty
                            redis_conn.hset(key, mapping=value)
                    
                    elif key_type == "list":
                        redis_conn.delete(key)  # Clear existing list
                        if value:  # Only push if not empty
                            redis_conn.rpush(key, *value)
                    
                    elif key_type == "set":
                        redis_conn.delete(key)  # Clear existing set
                        if value:  # Only add if not empty
                            redis_conn.sadd(key, *value)
                    
                    elif key_type == "zset":
                        redis_conn.delete(key)  # Clear existing sorted set
                        if value:  # Only add if not empty
                            for item in value:
                                redis_conn.zadd(key, {item["member"]: item["score"]})
                    
                    # Set TTL if it exists in backup
                    if ttl is not None and ttl > 0:
                        redis_conn.expire(key, ttl)
                    
                    stats["processed"] += 1
                    
                except Exception as e:
                    logger.error(f"Error restoring key {key}: {e}")
                    stats["errors"] += 1
            
            result_msg = (
                f"Restore completed: {stats['processed']} keys processed, "
                f"{stats['skipped']} keys skipped, {stats['errors']} errors"
            )
            logger.info(result_msg)
            return stats["errors"] == 0, result_msg
            
        except Exception as e:
            error_msg = f"Redis restore failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def apply_retention_policy(
        backup_dir: Optional[str] = None,
        days_to_keep: int = 30,
        min_backups_to_keep: int = 5
    ) -> Tuple[bool, str]:
        """
        Apply retention policy to backup files
        
        Args:
            backup_dir: Directory containing backups
            days_to_keep: Number of days to keep backups
            min_backups_to_keep: Minimum number of backups to keep regardless of age
            
        Returns:
            Tuple[bool, str]: Success status and result message
        """
        try:
            # Use default backup dir if none provided
            if not backup_dir:
                backup_dir = os.path.join(config.settings.OUTPUT_DIR_PATH, "backups")
                
            if not os.path.exists(backup_dir):
                return True, "Backup directory does not exist, nothing to clean"
                
            # Find all backup files
            backup_files = []
            
            for filename in os.listdir(backup_dir):
                if filename.endswith((".tar.gz", ".json.gz")):
                    file_path = os.path.join(backup_dir, filename)
                    mtime = os.path.getmtime(file_path)
                    backup_files.append((file_path, mtime))
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # Calculate cutoff date
            cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
            
            # Identify files to delete (older than cutoff, excluding minimum to keep)
            files_to_keep = backup_files[:min_backups_to_keep]
            files_to_delete = [
                file_path for file_path, mtime in backup_files[min_backups_to_keep:]
                if mtime < cutoff_time
            ]
            
            # Delete old files
            deleted_count = 0
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete backup file {file_path}: {e}")
            
            result_msg = (
                f"Retention policy applied: kept {len(files_to_keep)} files, "
                f"deleted {deleted_count} old files"
            )
            logger.info(result_msg)
            return True, result_msg
            
        except Exception as e:
            error_msg = f"Failed to apply retention policy: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def cleanup_old_files(
        output_dir: Optional[str] = None,
        days_to_keep: int = 7,
        file_patterns: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """
        Clean up old files in the output directory
        
        Args:
            output_dir: Directory containing files to clean
            days_to_keep: Number of days to keep files
            file_patterns: Glob patterns for files to clean (default: ["participants_*.txt"])
            
        Returns:
            Tuple[bool, str]: Success status and result message
        """
        try:
            # Use default output dir if none provided
            if not output_dir:
                output_dir = config.settings.OUTPUT_DIR_PATH
                
            if not os.path.exists(output_dir):
                return True, "Output directory does not exist, nothing to clean"
                
            # Default file patterns if none provided
            if not file_patterns:
                file_patterns = ["participants_*.txt"]
                
            # Calculate cutoff date
            cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
            
            # Find and delete old files
            deleted_count = 0
            checked_count = 0
            
            for pattern in file_patterns:
                for file_path in glob.glob(os.path.join(output_dir, pattern)):
                    checked_count += 1
                    
                    try:
                        # Check if file is older than cutoff
                        mtime = os.path.getmtime(file_path)
                        if mtime < cutoff_time:
                            os.remove(file_path)
                            deleted_count += 1
                    except Exception as e:
                        logger.error(f"Failed to check/delete file {file_path}: {e}")
            
            result_msg = (
                f"Cleanup completed: {deleted_count} files deleted "
                f"out of {checked_count} checked"
            )
            logger.info(result_msg)
            return True, result_msg
            
        except Exception as e:
            error_msg = f"Cleanup failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg