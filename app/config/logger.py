import logging

def setup_logger():
    logfmt = '%(asctime)s <%(levelname)s> %(message)s'
    
    # 创建一个handler，用于输出到控制台
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(logfmt))

    # 创建一个handler，用于输出到文件
    file_handler = logging.FileHandler('service.log', encoding="utf-8", mode="a")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(logfmt))

    # 创建一个日志记录器
    logger = logging.getLogger('')
    logger.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # 设置 apscheduler 的日志级别为 error
    apscheduler_logger = logging.getLogger('apscheduler')
    apscheduler_logger.setLevel(logging.ERROR)
    apscheduler_logger.addHandler(console_handler)
    apscheduler_logger.addHandler(file_handler)

    # 获取 apscheduler.job 的日志记录器
    job_logger = logging.getLogger('apscheduler.job')
    job_logger.setLevel(logging.ERROR)

    # 获取 apscheduler.executors.default 的日志记录器
    default_executor_logger = logging.getLogger('apscheduler.executors.default')
    default_executor_logger.setLevel(logging.ERROR)

    # 获取 apscheduler.schedulers.background 的日志记录器
    background_scheduler_logger = logging.getLogger('apscheduler.schedulers.background')
    background_scheduler_logger.setLevel(logging.ERROR)

    # 获取 apscheduler.schedulers.blocking 的日志记录器
    blocking_scheduler_logger = logging.getLogger('apscheduler.schedulers.blocking')
    blocking_scheduler_logger.setLevel(logging.ERROR)

    return logger

# 在模块被导入时，配置日志记录器
logger = setup_logger()