"""Local regular-AO companion. No database writes, networking or authentication."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent
import frida
from prefs import read_selection

kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.OpenProcess.argtypes = [ctypes.c_uint, ctypes.c_bool, ctypes.c_uint]
kernel.OpenProcess.restype = ctypes.c_void_p
kernel.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_uint)]
kernel.CloseHandle.argtypes = [ctypes.c_void_p]
kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
kernel.CreateMutexW.restype = ctypes.c_void_p


def identity(pid):
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        code = ctypes.c_uint()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != 259:
            return None
        text = ctypes.create_unicode_buffer(32768)
        size = ctypes.c_uint(len(text))
        return Path(text.value) if kernel.QueryFullProcessImageNameW(handle, 0, text, ctypes.byref(size)) else None
    finally:
        kernel.CloseHandle(handle)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--stop', action='store_true')
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    data_root = args.config.resolve().parent
    stop = data_root/'stop.request'
    if args.stop:
        stop.touch()
        return
    mutex = kernel.CreateMutexW(None, False, 'Local\\AOUArmorLiveCompanion')
    if not mutex:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:
        kernel.CloseHandle(mutex)
        return
    stop.unlink(missing_ok=True)
    target = Path(config['game'])/'AnarchyOnline.exe'
    expected_hashes = {name.lower(): value for name,value in config['hashes'].items()}
    for name, expected in config['hashes'].items():
        if hashlib.sha256((target.parent/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Unsupported client build: '+name)
    device = frida.get_local_device()
    session = script = None
    pid = None
    initialized = False
    state = {'status': 'waiting-for-game'}

    def report(**values):
        state.update(values)
        temporary = data_root/'controller-status.tmp'
        temporary.write_text(json.dumps(state, indent=2))
        os.replace(temporary, data_root/'controller-status.json')

    def message(value, data):
        payload = value.get('payload', {})
        if value.get('type') == 'error':
            report(status='error', error=value.get('description'))
        elif payload.get('event') == 'armor-applied':
            report(status='live', selection=payload['selection'],
                   targets=[{'id': r['id'], 'mode': r['mode']} for r in payload['targets']], error=None)
        elif payload.get('event') == 'armor-error':
            report(status='error', error=payload['error'])

    def detach(restore):
        nonlocal session, script, initialized
        if script:
            try:
                if restore and initialized:
                    script.exports_sync.restore()
                    deadline = time.monotonic()+3
                    while time.monotonic()<deadline:
                        if script.exports_sync.status()['restored']:
                            break
                        time.sleep(.1)
                    else:
                        report(error='Restore awaits a render frame; last GPU choice remains until resource reload')
                script.exports_sync.dispose()
                script.unload()
            except frida.InvalidOperationError:
                pass  # Process already exited; its native resources no longer exist.
        if session:
            try:
                session.detach()
            except frida.InvalidOperationError:
                pass
        session = script = None
        initialized = False

    report(status='waiting-for-game', error=None)
    try:
        while not stop.exists():
            if pid and identity(pid) != target:
                detach(False)
                pid = None
                report(status='waiting-for-game')
            if pid is None:
                candidates = [p.pid for p in device.enumerate_processes()
                              if p.name.lower() == target.name.lower() and identity(p.pid) == target]
                if len(candidates)>1:
                    report(status='waiting', error='Multiple regular AO clients; close extras')
                elif candidates:
                    pid = candidates[0]
            if pid:
                try:
                    if not session:
                        session = device.attach(pid)
                        if identity(pid) != target:
                            raise ValueError('Target identity changed during attach')
                    if not script:
                        ready = session.create_script("rpc.exports={modules(){return ['Cheetah.dll','Utils.dll','DisplaySystem.dll'].map(n=>Process.findModuleByName(n)).filter(m=>m!==null).map(m=>({name:m.name,path:m.path}));}};")
                        try:
                            ready.load()
                            modules = ready.exports_sync.modules()
                        finally:
                            ready.unload()
                        if len(modules)!=3:
                            time.sleep(2)
                            continue
                        for module in modules:
                            loaded = Path(module['path'])
                            if loaded != target.parent/module['name'] or hashlib.sha256(loaded.read_bytes()).hexdigest() != expected_hashes[module['name'].lower()]:
                                raise ValueError('Loaded renderer identity differs from verified files')
                        candidate = session.create_script((ROOT/'runtime.js').read_text())
                        candidate.on('message', message)
                        try:
                            candidate.load()
                        except BaseException:
                            candidate.unload()
                            raise
                        script = candidate
                    if not initialized:
                        choices = config.get('resume_selection') or read_selection(Path(config['preferences']))
                        bases = {'omni_af':'stock','tank':'stock'}
                        result = script.exports_sync.initialize(str(data_root/'runtime-textures.json'), choices, bases)
                        initialized = result['ready']
                        if initialized and 'resume_selection' in config:
                            del config['resume_selection']
                            temporary=args.config.with_suffix('.tmp')
                            temporary.write_text(json.dumps(config,indent=2))
                            os.replace(temporary,args.config)
                        if not initialized:
                            report(status='waiting-for-armor')
                except frida.InvalidOperationError:
                    detach(False)
                    pid = None
                except frida.RPCException as error:
                    report(status='waiting-for-renderer', error=str(error))
            time.sleep(2)
    finally:
        detach(True)
        report(status='stopped')
        kernel.CloseHandle(mutex)


if __name__ == '__main__':
    main()
