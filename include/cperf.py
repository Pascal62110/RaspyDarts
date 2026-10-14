# -*- coding: utf-8 -*-
"""
Performance measures, inactive unless a file named "perf" exists in the game folder
when the game starts (touch perf / rm perf, then restart the game).

Results are written every 10 seconds in logs/perf.log :
    name : number of calls, calls per second, mean / max duration in ms
Each dart detected on the target is also written with the time its contact stayed closed.
"""

import os
import time
from functools import wraps

from include import cpaths

ENABLED = os.path.exists(os.path.join(cpaths.ROOT_DIR, 'perf'))

PERIOD = 10

_log_file = None
_stats = {}
_period_start = time.perf_counter()


def _write(line):
    global _log_file
    if _log_file is None:
        os.makedirs(os.path.join(cpaths.ROOT_DIR, 'logs'), exist_ok=True)
        _log_file = open(os.path.join(cpaths.ROOT_DIR, 'logs', 'perf.log'), 'a', buffering=1)
        _log_file.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} : start of measures ===\n")
    _log_file.write(f"{time.strftime('%H:%M:%S')} {line}\n")


def _flush_if_due(now):
    '''
    Write the summary of the last period, if it is over
    '''
    global _period_start
    elapsed = now - _period_start
    if elapsed < PERIOD:
        return
    _period_start = now
    for name in sorted(_stats):
        count, total, maximum = _stats[name]
        if count == 0:
            continue
        if total > 0:
            _write(f"{name} : {count} calls, {count / elapsed:.1f}/s, mean {total / count * 1000:.3f} ms, max {maximum * 1000:.3f} ms")
        else:
            _write(f"{name} : {count} calls, {count / elapsed:.1f}/s")
    _stats.clear()


def add(name, duration=0.0):
    '''
    Record one call of name, and its duration in seconds if any
    '''
    now = time.perf_counter()
    count, total, maximum = _stats.get(name, (0, 0.0, 0.0))
    _stats[name] = (count + 1, total + duration, max(maximum, duration))
    _flush_if_due(now)


def event(text):
    '''
    Write a single event (a dart, for example)
    '''
    _write(text)


def timed(name):
    '''
    Decorator : measures each call of the function. Without the "perf" file, the
    function is left untouched (no cost at all)
    '''
    def decorator(function):
        if not ENABLED:
            return function

        @wraps(function)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                add(name, time.perf_counter() - start)
        return wrapper
    return decorator
