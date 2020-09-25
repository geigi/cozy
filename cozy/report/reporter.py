import traceback

from cozy.report.log_level import LogLevel

from multiprocessing.pool import ThreadPool as Pool

from cozy.report.report_to_loki import report

report_pool = Pool(5)

def info(component: str, message: str):
    report_pool.apply_async(report, [component, LogLevel.INFO, message, None])


def warning(component: str, message: str):
    report_pool.apply_async(report, [component, LogLevel.WARNING, message, None])


def error(component: str, message: str):
    report_pool.apply_async(report, [component, LogLevel.ERROR, message, None])


def exception(component: str, exception: Exception, message=None):
    if not message:
        message = traceback.format_exc()

    report_pool.apply_async(report, [component, LogLevel.ERROR, message, exception])


def close():
    report_pool.close()
    report_pool.terminate()
