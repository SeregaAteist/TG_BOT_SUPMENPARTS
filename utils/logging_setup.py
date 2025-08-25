# utils/logging_setup.py
import logging

def setup_logging():
    logging.basicConfig(
        format='[%(levelname)s] %(asctime)s | %(name)s | %(message)s',
        level=logging.INFO
    )