import logging
from logging import StreamHandler

def setup_logging(level: int = logging.INFO) -> None:
    handler = StreamHandler()
    fmt = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    logging.basicConfig(handlers=[handler], level=level, format=fmt)