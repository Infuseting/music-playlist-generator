import logging
import sys

EMOJI_BY_LEVEL = {
    logging.DEBUG: "🐞",
    logging.INFO: "ℹ️",
    logging.WARNING: "⚠️",
    logging.ERROR: "❌",
    logging.CRITICAL: "💥",
}


class EmojiFormatter(logging.Formatter):
    def format(self, record):
        emoji = EMOJI_BY_LEVEL.get(record.levelno, "")
        record.levelname = f"{emoji} {record.levelname}"
        return super().format(record)


def configure_logging(debug: bool = False):
    root = logging.getLogger()
    level = logging.DEBUG if debug else logging.INFO
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    handler.setFormatter(EmojiFormatter(fmt))
    # remove existing handlers
    if root.handlers:
        for h in list(root.handlers):
            root.removeHandler(h)
    root.addHandler(handler)


def get_logger(name: str):
    return logging.getLogger(name)
