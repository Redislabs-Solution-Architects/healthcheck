import sys

from healthcheck.common_funcs import get_parameter_map_name


class Color(object):
    """
    Color class.

    Use ASCII escape codes to colorize terminal output.
    """

    @staticmethod
    def black(_text):
        return '\033[0;30m' + _text + '\033[0m'

    @staticmethod
    def red(_text):
        return '\033[0;31m' + _text + '\033[0m'

    @staticmethod
    def green(_text):
        return '\033[0;32m' + _text + '\033[0m'

    @staticmethod
    def yellow(_text):
        return '\033[0;33m' + _text + '\033[0m'

    @staticmethod
    def blue(_text):
        return '\033[0;34m' + _text + '\033[0m'

    @staticmethod
    def magenta(_text):
        return '\033[0;35m' + _text + '\033[0m'

    @staticmethod
    def cyan(_text):
        return '\033[0;36m' + _text + '\033[0m'

    @staticmethod
    def white(_text):
        return '\033[0;37m' + _text + '\033[0m'


def print_list(_suites):
    """
    Print check list.

    :param _suites: The list of check suites.
    """
    for suite in _suites:
        print(f'{Color.green("Suite")}: {suite.__doc__}')
        for check_name in filter(lambda x: x.startswith('check_'), dir(suite)):
            check_func = getattr(suite, check_name)
            parts = [f'{Color.yellow("-")}', check_func.__doc__]
            if '_params' in check_func.__code__.co_varnames:
                parts.append(Color.red("[params]"))
            print(' '.join(parts))
        print('')


def print_msg(_msg):
    """
    Print neutral message.

    :param _msg: The neutral message.
    """
    print(Color.white(_msg), file=sys.stderr, flush=True)


def print_success(_msg):
    """
    Print a success message.

    :param _msg: The success message.
    """
    print(Color.green(_msg), file=sys.stderr, flush=True)


def print_warning(_msg):
    """
    Print a warning message.

    :param _msg: The warning message.
    """
    print(Color.yellow(_msg), file=sys.stderr, flush=True)


def print_error(_msg, _ex=None):
    """
    Print an error message.

    :param _msg: The error message.
    :param _ex: An optional exception.
    """
    parts = [_msg]
    if _ex:
        if hasattr(_ex, 'reason'):
            if isinstance(_ex.reason, str):
                parts.append(_ex.reason)
            else:
                parts.append(_ex.reason.strerror)
        elif hasattr(_ex, 'strerror'):
            parts.append(_ex.strerror)
        elif hasattr(_ex, 'stderr'):
            parts.append(_ex.stderr)
        else:
            parts.append(_ex.args[0])

    print(Color.red(' '.join(parts)), file=sys.stderr, flush=True)
