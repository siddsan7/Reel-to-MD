"""Atomic persistence under transient Windows reader locks."""
import os
import threading
import time

import pytest

from reel_to_md import storage


def test_transient_replace_denial_keeps_old_data_until_commit(tmp_path,monkeypatch):
    path=tmp_path/'record.json';path.write_text('old',encoding='utf-8')
    real=storage.os.replace;calls=[];delays=[]
    def replace(source,dest):
        calls.append(True)
        if len(calls)<=3:
            assert path.read_text(encoding='utf-8')=='old'
            raise PermissionError('temporary reader lock')
        return real(source,dest)
    monkeypatch.setattr(storage.os,'replace',replace);monkeypatch.setattr(storage.time,'sleep',delays.append)
    storage.write_text(path,'new café 東京')
    assert path.read_text(encoding='utf-8')=='new café 東京'
    assert len(calls)>1 and 0<sum(delays)<=0.6
    assert not list(tmp_path.glob('*.tmp'))


def test_permanent_denial_is_bounded_and_preserves_old_record(tmp_path,monkeypatch):
    path=tmp_path/'record.json';path.write_text('old',encoding='utf-8');delays=[]
    def deny(*args):raise PermissionError('permanent denial')
    monkeypatch.setattr(storage.os,'replace',deny);monkeypatch.setattr(storage.time,'sleep',delays.append)
    with pytest.raises(PermissionError):storage.write_text(path,'new')
    assert path.read_text(encoding='utf-8')=='old' and 0<sum(delays)<=0.6
    assert not list(tmp_path.glob('*.tmp'))


def test_other_replace_errors_are_not_retried(tmp_path,monkeypatch):
    delays=[]
    def fail(*args):raise FileNotFoundError('invalid destination')
    monkeypatch.setattr(storage.os,'replace',fail);monkeypatch.setattr(storage.time,'sleep',delays.append)
    with pytest.raises(FileNotFoundError):storage.write_text(tmp_path/'record','new')
    assert delays==[] and not list(tmp_path.glob('*.tmp'))


@pytest.mark.skipif(os.name!='nt',reason='Windows sharing semantics')
def test_real_windows_reader_can_release_before_atomic_commit(tmp_path):
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    kernel.CreateFileW.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
    path=tmp_path/'record.json';storage.write_text(path,'old')
    handle=kernel.CreateFileW(str(path),0x80000000,1,None,3,0x80,None)
    assert handle not in (None,ctypes.c_void_p(-1).value)
    def release():
        time.sleep(0.12)
        kernel.CloseHandle(handle)
    reader=threading.Thread(target=release);reader.start()
    try:storage.write_text(path,'new')
    finally:reader.join()
    assert path.read_text(encoding='utf-8')=='new'
    assert not list(tmp_path.glob('*.tmp'))
