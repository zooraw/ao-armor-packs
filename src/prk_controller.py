"""PRK companion: watch its two UI choices and update owned ao-vk sidecars."""
import argparse
import json
from pathlib import Path
import threading
import time
import frida
from controller import identity,kernel
from database import atomic,digest
from prefs import read_selection
from prk_materials import switch


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--stop',action='store_true')
    args=parser.parse_args();config=json.loads(args.config.read_text());state=args.config.parent
    stop=state/'stop.request'
    if args.stop:stop.touch();return
    mutex=kernel.CreateMutexW(None,False,'Local\\PRKArmorLiveCompanion')
    import ctypes
    if not mutex:raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error()==183:kernel.CloseHandle(mutex);return
    stop.unlink(missing_ok=True)
    client=Path(config['client']);target=client/'AnarchyOnline.exe'
    for name,expected in config['hashes'].items():
        if digest((client/name).read_bytes())!=expected:raise ValueError('Unsupported PRK file: '+name)
    rows=config['files'];choices=read_selection(Path(config['preferences']));lock=threading.RLock()
    session=script=None;pid=None;status={'status':'waiting-for-game','selection':choices}
    def report(**values):
        with lock:
            status.update(values);atomic(state/'controller-status.json',(json.dumps(status,indent=2)+'\n').encode())
    def apply():
        with lock:
            try:report(targets=switch(rows,choices),selection=dict(choices),error=None)
            except Exception as error:report(status='error',error=str(error))
    def message(value,data):
        if value.get('type')=='error':report(status='error',error=value.get('description'));return
        payload=value.get('payload',{})
        if payload.get('event')=='armor-choice':
            with lock:
                choices[payload['group']]=payload['enabled'];apply()
    def detach():
        nonlocal session,script
        if script:
            try:script.exports_sync.dispose();script.unload()
            except frida.InvalidOperationError:pass
        if session:
            try:session.detach()
            except frida.InvalidOperationError:pass
        session=script=None
    try:
        apply();report(status='waiting-for-game')
        device=frida.get_local_device()
        while not stop.exists():
            if pid and identity(pid)!=target:
                detach();pid=None;report(status='waiting-for-game')
            if pid is None:
                found=[p.pid for p in device.enumerate_processes() if p.name.lower()==target.name.lower() and identity(p.pid)==target]
                if len(found)>1:report(status='waiting',error='Multiple PRK clients; close extras')
                elif found:pid=found[0]
            if pid and not script:
                try:
                    if not session:session=device.attach(pid)
                    if identity(pid)!=target:raise ValueError('PRK process identity changed')
                    check=session.create_script("rpc.exports={modules(){return ['Utils.dll','randy31.dll'].map(n=>Process.findModuleByName(n)).filter(m=>m).map(m=>({name:m.name,path:m.path}));}};")
                    try:check.load();modules=check.exports_sync.modules()
                    finally:check.unload()
                    if len(modules)!=2:time.sleep(2);continue
                    for module in modules:
                        if Path(module['path'])!=client/module['name']:raise ValueError('PRK loaded DLL outside selected client')
                    script=session.create_script((Path(__file__).parent/'prk_watch.js').read_text())
                    script.on('message',message);script.load();ready=script.exports_sync.ready()
                    if not ready['hotReload']:
                        report(status='restart-required',error='Start PRK through its armor shortcut to enable material hot reload')
                    else:report(status='live',error=None)
                except frida.InvalidOperationError:detach();pid=None
                except frida.RPCException as error:report(status='error',error=str(error));detach();pid=None
            time.sleep(2)
    finally:
        detach()
        try:switch(rows,{'omni_af':False,'tank':False})
        finally:report(status='stopped');kernel.CloseHandle(mutex)


if __name__=='__main__':main()
