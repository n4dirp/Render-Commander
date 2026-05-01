import logging
import time

SCRIPT_NAME = "render_script"
LOG_LEVEL = logging.INFO


class PrefixedFormatter(logging.Formatter):
    """Formatter with relative timestamp + script prefix."""

    def __init__(self, script_name):
        super().__init__()
        self.start_time = time.time()
        self.script_name = script_name

    def format(self, record):
        rel_time = record.created - self.start_time
        minutes, seconds = divmod(rel_time, 60)

        timestamp = "%02d:%06.3f" % (int(minutes), seconds)
        name_field = "%-16s" % self.script_name
        message = record.getMessage()

        return "%s  %s | %s" % (timestamp, name_field, message)


def setup_logger():
    log = logging.getLogger(SCRIPT_NAME)
    log.setLevel(LOG_LEVEL)

    if log.hasHandlers():
        log.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(PrefixedFormatter(script_name=SCRIPT_NAME))

    log.addHandler(handler)
    log.propagate = False

    return log


log = setup_logger()
