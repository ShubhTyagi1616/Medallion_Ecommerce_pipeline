import logging
import os

def setup_logger(name="PipelineLogger"):
    # create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir, exist_ok=True)

    log_file = os.path.join(logs_dir, f"{name}.log")

    #configure logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # prevent adding multiple handlers if the logger is called multiple times
    if not logger.handlers:
        # create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)

        #console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        # add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    return logger

# quick test when running this file directly
if __name__ == "__main__":
    logger = setup_logger()
    logger.info("Logger has been set up successfully.")