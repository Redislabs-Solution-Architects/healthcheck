import re

from healthcheck.printer_funcs import Color


def render_result(_result, _func, *_args, **_kwargs):
    """
    Render result.

    :param _result: The result.
    :param _func: The check function executed.
    """
    doc = (_result[2] if len(_result) == 3 else _func.__doc__).split('\n')[0]
    remedy = None
    if _result[0] == '':
        to_print = ['[ ]', doc, '[SKIPPED]']
    elif _result[0] is True:
        to_print = [Color.green('[+]'), doc, Color.green('[SUCCEEDED]')]
    elif _result[0] is False:
        to_print = [Color.red('[-]'), doc, Color.red('[FAILED]')]
        doc = (_result[2] if len(_result) == 3 else _func.__doc__)
        remedy = re.findall(r'Remedy: (.*)', doc, re.MULTILINE)
    elif _result[0] is None:
        to_print = [Color.yellow('[~]'), doc, Color.yellow('[NO RESULT]')]
    elif _result[0] is Exception:
        to_print = [Color.magenta('[*]'), doc, Color.magenta('[ERROR]')]
    else:
        raise NotImplementedError()

    to_print.append(', '.join([str(k) + ': ' + str(v) for k, v in _result[1].items()]))
    if remedy:
        to_print.append(' '.join([Color.cyan('Remedy:'), remedy[0]]))
        print('{} {} {} {} {}'.format(*to_print))
    else:
        print('{} {} {} {}'.format(*to_print))


def render_stats(_stats):
    """
    Render collected statistics.

    :param _stats: A stats collector.
    """
    print('')
    print('total checks run: {}'.format(
        sum([_stats.succeeded, _stats.no_result, _stats.failed, _stats.errors, _stats.skipped])))
    print(f'- {Color.green("succeeded")}: {_stats.succeeded}')
    print(f'- {Color.yellow("no result")}: {_stats.no_result}')
    print(f'- {Color.red("failed")}: {_stats.failed}')
    print(f'- {Color.magenta("errors")}: {_stats.errors}')
    print(f'- skipped: {_stats.skipped}')
