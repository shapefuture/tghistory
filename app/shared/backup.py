# ... (imports and docstring unchanged) ...
logger = logging.getLogger("backup")

class BackupManager:
    @staticmethod
    def backup_session_files(backup_dir: Optional[str] = None) -> Tuple[bool, str]:
        logger.debug(f"backup_session_files called: backup_dir={backup_dir}")
        try:
            # ... (rest of method unchanged except for added logs at key points and on error) ...
            logger.info(f"Session backup created: {backup_path}")
            return True, backup_path
        except Exception as e:
            logger.error(f"Session backup failed: {e}", exc_info=True)
            return False, f"Session backup failed: {str(e)}"

    # (Other methods: add similar logging/error catching)
