import logging
import multiprocessing as mp
from typing import Callable, Iterable, List


def get_cpu_count() -> int:
    """
    Get amount of CPUs available for multi-processing.

    :return:
    """
    return mp.cpu_count()


def run_with_multi_processing(func: Callable, iterable: Iterable, n_cpu: int) -> List:
    """
    Run a function for each element in an iterable with multi-processing.

    :param func:
    :param iterable:
    :param n_cpu:
    :return:
    """
    logging.info(f"Starting multi-processing with {n_cpu} CPUs.")
    with mp.Pool(processes=n_cpu) as pool:
        try:
            results: List = pool.starmap(func, iterable)
        except TypeError as e:
            logging.warning(
                "Failed to use starmap for parallelization, trying map now..."
            )
            logging.debug(e)
            try:
                results: List = pool.map(func, iterable)
            except TypeError as e:
                logging.debug("Failed to run function in parallel.")
                logging.debug(e)
                raise Exception("Failed to run function in parallel.")
    return results
