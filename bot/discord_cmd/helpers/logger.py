from logging import FileHandler, Formatter, getLogger, INFO

def setup_logger(name, log_file, level=INFO):
    handler = FileHandler(log_file,encoding='utf-8')        
    handler.setFormatter(Formatter('[%(asctime)s] %(levelname)s: %(message)s'))
    logger = getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger

logger = setup_logger('logger', './log/bot.log')