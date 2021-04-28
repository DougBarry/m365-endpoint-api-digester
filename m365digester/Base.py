import logging


class Base(object):
    warning_count = 0
    error_count = 0
    logger = None
    config = dict()

    def __init__(self, config: dict = None, logger=None):
        self.logger = logger
        if not config:
            self.config = dict()
        else:
            self.config = config

    def info(self, message: str):
        if not self.logger:
            return
        if not message:
            return
        self.logger.info(message)

    def debug(self, message: str):
        """Log to debug"""
        if not self.logger:
            return
        if not message:
            return
        self.logger.debug(message)

    def error(self, message: str):
        """
        Error counter
        """
        self.error_count += 1
        if not self.logger:
            return
        if not message:
            return
        self.logger.error(message)

    def error_quit(self, message: str) -> int:
        """
        Critical error, spit out error count and quit
        """
        self.error(message)
        self.close_db()
        if self.logger:
            if message:
                self.logger.error(f"Exiting after {self.warning_count} warnings, {self.error_count} errors.")
        return self.error_count

    def warning(self, message: str):
        """
        Warning counter
        """
        self.warning_count += 1
        if not self.logger:
            return
        if not message:
            return
        self.logger.warning(message)
