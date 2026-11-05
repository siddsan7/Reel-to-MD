"""Windows kill-on-close containment, queried without persisted process IDs."""
import ctypes
import hashlib
import os
from pathlib import Path

_handles = []


def _name(root):
    key = hashlib.sha256(str(Path(root).resolve()).casefold().encode()).hexdigest()
    return "Local\\ReelToMD-" + key


def _kernel():
    from ctypes import wintypes as w
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    for name, args, result in [
        ("CreateJobObjectW", [ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
        ("OpenJobObjectW", [w.DWORD, w.BOOL, w.LPCWSTR], w.HANDLE),
        ("SetInformationJobObject", [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL),
        ("QueryInformationJobObject", [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p], w.BOOL),
        ("AssignProcessToJobObject", [w.HANDLE, w.HANDLE], w.BOOL),
        ("GetCurrentProcess", [], w.HANDLE), ("CloseHandle", [w.HANDLE], w.BOOL),
    ]:
        fn = getattr(kernel, name)
        fn.argtypes, fn.restype = args, result
    return kernel


def contain_worker(root):
    if os.name != "nt":
        return  # POSIX recovery requires explicit process-check acknowledgment.
    from ctypes import wintypes as w
    size = ctypes.c_size_t
    class Basic(ctypes.Structure):
        _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                    ("flags", w.DWORD), ("minimum", size), ("maximum", size),
                    ("active_limit", w.DWORD), ("affinity", size), ("priority", w.DWORD), ("scheduling", w.DWORD)]
    class Extended(ctypes.Structure):
        _fields_ = [("basic", Basic), ("io", ctypes.c_uint64 * 6),
                    ("process_memory", size), ("job_memory", size), ("peak_process", size), ("peak_job", size)]
    kernel = _kernel()
    handle = kernel.CreateJobObjectW(None, _name(root))
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    info = Extended()
    info.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel.SetInformationJobObject(handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
        error = ctypes.get_last_error()
        kernel.CloseHandle(handle)
        raise ctypes.WinError(error)
    if not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess()):
        error = ctypes.get_last_error()
        kernel.CloseHandle(handle)
        raise ctypes.WinError(error)
    _handles.append(handle)  # Retained until process exit; never inherited.


def contained_processes(root):
    if os.name != "nt":
        return False
    from ctypes import wintypes as w
    class Accounting(ctypes.Structure):
        _fields_ = [("times", ctypes.c_int64 * 4), ("faults", w.DWORD),
                    ("total", w.DWORD), ("active", w.DWORD), ("terminated", w.DWORD)]
    kernel = _kernel()
    handle = kernel.OpenJobObjectW(4, False, _name(root))
    if not handle:
        if ctypes.get_last_error() == 2:
            return False
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        info = Accounting()
        if not kernel.QueryInformationJobObject(handle, 1, ctypes.byref(info), ctypes.sizeof(info), None):
            raise ctypes.WinError(ctypes.get_last_error())
        return info.active > 0
    finally:
        kernel.CloseHandle(handle)
