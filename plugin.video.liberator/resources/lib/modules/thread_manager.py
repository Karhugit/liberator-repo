# -*- coding: utf-8 -*-
from concurrent.futures import ThreadPoolExecutor
import os

def make_thread_list(target, task_list, max_workers=None):
    """Executes a target function with a list of tasks using a temporary thread pool."""
    if not task_list:
        return

    if max_workers is None:
        # Conservative approach for Kodi addon
        cpu_count = os.cpu_count() or 4
        max_workers = min(len(task_list), max(2, cpu_count // 2))  # Use half the cores

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(target, task_list)

def make_thread_list_multi_arg(target, task_list, max_workers=None):
    """Executes a target function with multiple arguments per task using a temporary thread pool."""
    if not task_list:
        return
    if max_workers is None:
        # Conservative approach for Kodi addon
        cpu_count = os.cpu_count() or 4
        max_workers = min(len(task_list), max(2, cpu_count // 2))  # Use half the cores

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(lambda args: target(*args), task_list)

def make_thread_list_enumerate(target, task_list, max_workers=None):
    """Executes a target function with indexed tasks using a temporary thread pool."""
    if not task_list:
        return
    if max_workers is None:
        # Conservative approach for Kodi addon
        cpu_count = os.cpu_count() or 4
        max_workers = min(len(task_list), max(2, cpu_count // 2))  # Use half the cores
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(lambda args: target(*args), enumerate(task_list))