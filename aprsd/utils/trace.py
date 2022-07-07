import abc
import functools
import inspect
import logging
import time
import types


VALID_TRACE_FLAGS = {"method", "api"}
TRACE_API = False
TRACE_METHOD = False
TRACE_ENABLED = False
LOG = logging.getLogger("APRSD")


def trace(*dec_args, **dec_kwargs):
    """Trace calls to the decorated function.

    This decorator should always be defined as the outermost decorator so it
    is defined last. This is important so it does not interfere
    with other decorators.

    Using this decorator on a function will cause its execution to be logged at
    `DEBUG` level with arguments, return values, and exceptions.

    :returns: a function decorator
    """

    def _decorator(f):

        func_name = f.__name__

        @functools.wraps(f)
        def trace_logging_wrapper(*args, **kwargs):
            filter_function = dec_kwargs.get("filter_function")
            logger = LOG

            # NOTE(ameade): Don't bother going any further if DEBUG log level
            # is not enabled for the logger.
            if not logger.isEnabledFor(logging.DEBUG) or not TRACE_ENABLED:
                return f(*args, **kwargs)

            all_args = inspect.getcallargs(f, *args, **kwargs)

            pass_filter = filter_function is None or filter_function(all_args)

            if pass_filter:
                logger.debug(
                    "==> %(func)s: call %(all_args)r",
                    {
                        "func": func_name,
                        "all_args": str(all_args),
                    },
                )

            start_time = time.time() * 1000
            try:
                result = f(*args, **kwargs)
            except Exception as exc:
                total_time = int(round(time.time() * 1000)) - start_time
                logger.debug(
                    "<== %(func)s: exception (%(time)dms) %(exc)r",
                    {
                        "func": func_name,
                        "time": total_time,
                        "exc": exc,
                    },
                )
                raise
            total_time = int(round(time.time() * 1000)) - start_time

            if isinstance(result, dict):
                mask_result = result
            elif isinstance(result, str):
                mask_result = result
            else:
                mask_result = result

            if pass_filter:
                logger.debug(
                    "<== %(func)s: return (%(time)dms) %(result)r",
                    {
                        "func": func_name,
                        "time": total_time,
                        "result": mask_result,
                    },
                )
            return result

        return trace_logging_wrapper

    if len(dec_args) == 0:
        # filter_function is passed and args does not contain f
        return _decorator
    else:
        # filter_function is not passed
        return _decorator(dec_args[0])


def trace_api(*dec_args, **dec_kwargs):
    """Decorates a function if TRACE_API is true."""

    def _decorator(f):
        @functools.wraps(f)
        def trace_api_logging_wrapper(*args, **kwargs):
            if TRACE_API:
                return trace(f, *dec_args, **dec_kwargs)(*args, **kwargs)
            return f(*args, **kwargs)

        return trace_api_logging_wrapper

    if len(dec_args) == 0:
        # filter_function is passed and args does not contain f
        return _decorator
    else:
        # filter_function is not passed
        return _decorator(dec_args[0])


def trace_method(f):
    """Decorates a function if TRACE_METHOD is true."""

    @functools.wraps(f)
    def trace_method_logging_wrapper(*args, **kwargs):
        if TRACE_METHOD:
            return trace(f)(*args, **kwargs)
        return f(*args, **kwargs)

    return trace_method_logging_wrapper


class TraceWrapperMetaclass(type):
    """Metaclass that wraps all methods of a class with trace_method.

    This metaclass will cause every function inside of the class to be
    decorated with the trace_method decorator.

    To use the metaclass you define a class like so:
    class MyClass(object, metaclass=utils.TraceWrapperMetaclass):
    """

    def __new__(cls, classname, bases, class_dict):
        new_class_dict = {}
        for attribute_name, attribute in class_dict.items():
            if isinstance(attribute, types.FunctionType):
                # replace it with a wrapped version
                attribute = functools.update_wrapper(
                    trace_method(attribute),
                    attribute,
                )
            new_class_dict[attribute_name] = attribute

        return type.__new__(cls, classname, bases, new_class_dict)


class TraceWrapperWithABCMetaclass(abc.ABCMeta, TraceWrapperMetaclass):
    """Metaclass that wraps all methods of a class with trace."""


def setup_tracing(trace_flags):
    """Set global variables for each trace flag.

    Sets variables TRACE_METHOD and TRACE_API, which represent
    whether to log methods or api traces.

    :param trace_flags: a list of strings
    """
    global TRACE_METHOD
    global TRACE_API
    global TRACE_ENABLED

    try:
        trace_flags = [flag.strip() for flag in trace_flags]
    except TypeError:  # Handle when trace_flags is None or a test mock
        trace_flags = []
    for invalid_flag in set(trace_flags) - VALID_TRACE_FLAGS:
        LOG.warning("Invalid trace flag: %s", invalid_flag)
    TRACE_METHOD = "method" in trace_flags
    TRACE_API = "api" in trace_flags
    TRACE_ENABLED = True
