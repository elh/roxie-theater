from functools import wraps
import time
import json
import traceback
from typing import Optional
from typing import Protocol
from datetime import datetime, timezone
import copy
import inspect


class Logger(Protocol):
    def log(self, **kwargs) -> None: ...


class JSONLogger:
    def __init__(self, **kwargs) -> None:
        self.kwargs = copy.deepcopy(kwargs)

    def with_kwargs(self, **kwargs) -> Logger:
        return JSONLogger(**self.kwargs | kwargs)

    def log(self, **kwargs) -> None:
        rec = (
            {"timestamp": datetime.now(timezone.utc).isoformat()} | self.kwargs | kwargs
        )
        print(json.dumps(rec))


def log_func(kwarg_keys: Optional[list[str]] = None):
    """
    NOTE: this has gotten very magical (and inefficient) but fun
    """

    def wrapper(func):
        @wraps(func)
        def decorator(*args, **kwargs):
            now = datetime.now(timezone.utc)
            start_time = now.timestamp()
            now_rfc3339 = now.isoformat()

            if "logger" in kwargs:
                logger = kwargs["logger"]
            else:
                logger = JSONLogger()

            if kwarg_keys is not None:
                logged_kwargs = {k: v for k, v in kwargs.items() if k in kwarg_keys}
            else:
                logged_kwargs = {}

            signature = inspect.signature(func)
            kwargs = {
                k: v
                for k, v in kwargs.items()
                if k != "logger" or k in signature.parameters
            }

            try:
                result = func(*args, **kwargs)
                duration = datetime.now(timezone.utc).timestamp() - start_time

                rec = {
                    "message": "function call",
                    "function": func.__name__,
                    "timestamp": now_rfc3339,
                    "duration": duration,
                    "kwargs": logged_kwargs,
                }
                logger.log(**rec)
                return result

            except Exception as e:
                duration = datetime.now(timezone.utc).timestamp() - start_time

                rec = {
                    "message": "function call",
                    "function": func.__name__,
                    "timestamp": now_rfc3339,
                    "duration": duration,
                    "kwargs": logged_kwargs,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
                logger.log(**rec)
                raise e

        return decorator

    return wrapper
