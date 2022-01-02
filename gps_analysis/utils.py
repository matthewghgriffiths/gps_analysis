
import sys
import logging
from typing import Callable, Dict, TypeVar, Tuple, Any
from contextlib import nullcontext

from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    from concurrent.futures import ProcessPoolExecutor
except ModuleNotFoundError:
    pass

_pyodide = "pyodide" in sys.modules


_MSH_STR_FORMAT = "{minutes:02d}:{seconds:02d}.{hundredths:02d}"
_HMSH_STR_FORMAT = "{hours}:{minutes:02d}:{seconds:02d}.{hundredths:02d}"
def strfmtsplit(tdelta, hours=False):
    components = tdelta.components._asdict()
    components['hundredths'] = tdelta.components.milliseconds // 10
    if tdelta.components.hours or hours:
        return _HMSH_STR_FORMAT.format(**components)
    else:
        return _MSH_STR_FORMAT.format(**components)

def unflatten_json(entity, key=()):
    if isinstance(entity, dict):
        for k, val in entity.items():
            yield from unflatten_json(val, key + (k,))
    elif isinstance(entity, list):
        for i, elem in enumerate(entity):
            yield from unflatten_json(elem, key + (i,))
    else:
        yield key, entity

K = TypeVar("K")
A = TypeVar('A')
V = TypeVar('V')
def map_concurrent(
    func: Callable[..., V],
    inputs: Dict[K, Tuple],
    threaded: bool = True,
    max_workers: int = 10,
    show_progress: bool = True,
    raise_on_err: bool = False,
    **kwargs,
) -> Tuple[Dict[K, V], Dict[K, Exception]]:
    """
    This function is equalivant to calling,
    >>> output = {k: func(*args, **kwargs) for k, args in inputs.items()}
    except that the function is called using either `ThreadPoolExecutor` 
    if `threaded=True` or a `ProcessPoolExecutor` otherwise.
    The function returns a tuple of `(output, errors)` where errors returns
    the errors that happened during the calling of any of the functions. So
    the function will run all the other work before 
    The function also generates a status bar indicating the progress of the
    computation.
    Alternatively if `raise_on_err=True` then the function will reraise the
    same error.
    Examples
    --------
    >>> import time
    >>> def do_work(arg):
    ...     time.sleep(0.5)
    ...     return arg
    >>> inputs = {i: (i,) for i in range(20)}
    >>> output, errors = map_concurrent(do_work, inputs)
    100%|███████████████████| 20/20 [00:01<00:00, 19.85it/s, completed=18]
    >>> len(output), len(errors)
    (20, 0)
    >>> def do_work2(arg):
    ...     time.sleep(0.5)
    ...     if arg == 5:
    ...         raise(ValueError('something went wrong'))
    ...     return arg
    >>> output, errors = map_concurrent(do_work2, inputs)
    100%|████████| 20/20 [00:01<00:00, 19.86it/s, completed=18, nerrors=1]
    >>> len(output), len(errors)
    (19, 1)
    >>> errors
{5: ValueError('something went wrong')}
    >>> try:
    ...     output, errors = map_concurrent(
    ...         do_work2, inputs, raise_on_err=True)
    ... except ValueError:
    ...     print("task failed successfully!")
    ...
    45%|█████████▍           | 9/20 [00:00<00:00, 17.71it/s, completed=5]
    task failed!
    """
    output = {}
    errors = {}

    Executor = ThreadPoolExecutor if threaded else ProcessPoolExecutor

    if show_progress:
        from tqdm.auto import tqdm
        pbar = tqdm(total=len(inputs))
    else:
        pbar = nullcontext()
    with Executor(max_workers=max_workers) as executor, pbar:
        work = {
            executor.submit(func, *args, **kwargs): k
            for k, args in inputs.items()
        }
        status: Dict[str, Any] = {}
        for future in as_completed(work):
            status['completed'] = key = work[future]
            if show_progress:
                pbar.update(1)
                pbar.set_postfix(**status)
            try:
                output[key] = future.result()
            except Exception as exc:
                if raise_on_err:
                    raise exc
                else:
                    logging.warning(f"{key} experienced error {exc}")
                    errors[key] = exc
                    status['nerrors'] = len(errors)

    return output, errors
    

def _map_singlethreaded(
    func: Callable[..., V],
    inputs: Dict[K, Tuple],
    threaded: bool = True,
    max_workers: int = 10,
    show_progress: bool = True,
    raise_on_err: bool = False,
    **kwargs,
) -> Tuple[Dict[K, V], Dict[K, Exception]]:
    output = {}
    errors = {}

    status: Dict[str, Any] = {}
    if show_progress:
        from tqdm.auto import tqdm
        pbar = tqdm(total=len(inputs))
    else:
        pbar = nullcontext()

    with pbar:
        for key, args in inputs.items():
            try:
                output[key] = func(*args, **kwargs)
            except Exception as exc:
                if raise_on_err:
                    raise exc
                else:
                    logging.warning(f"{key} experienced error {exc}")
                    errors[key] = exc
                    status['nerrors'] = len(errors)

            if show_progress:
                pbar.update(1)
                pbar.set_postfix(**status)

    return output, errors


if _pyodide:
    map_concurrent = _map_singlethreaded