"""Install, inspect or remove the separately installed AO armor package."""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from PIL import Image
import frida
import database as db
import integration
from textures import decode_fctx,encode
from controller import identity

REPO=Path(__file__).resolve().parent.parent


def write_json(path,data):
    db.atomic(path,(json.dumps(data,indent=2)+'\n').encode())


def running(game):
    target=Path(game)/'AnarchyOnline.exe'
    return any(p.name.lower()==target.name.lower() and identity(p.pid)==target
               for p in frida.get_local_device().enumerate_processes())


def stop(state):
    config=state/'config.json'
    if not config.exists():return
    status=state/'controller-status.json'
    (state/'stop.request').touch()
    deadline=time.monotonic()+5
    while status.exists() and json.loads(status.read_text())['status']!='stopped' and time.monotonic()<deadline:
        time.sleep(.1)
    if status.exists() and json.loads(status.read_text())['status']!='stopped':
        raise ValueError('Companion has not stopped; close it before changing installation')


def apply_gui(changes):
    for path,data in changes.items():
        if data is None:path.unlink(missing_ok=True)
        else:db.atomic(path,data)


def install(args):
    state=args.state.resolve();state.mkdir(parents=True,exist_ok=True)
    marker=state/'installed.json'
    game=args.game.resolve();gui=args.gui.resolve();preferences=args.preferences.resolve()
    pack=json.loads((REPO/'packs/omni-af/pack.json').read_text())
    for name,expected in pack['client_hashes'].items():
        if db.digest((game/name).read_bytes())!=expected:
            raise ValueError('Unsupported client build: '+name)
    if not preferences.is_file():raise ValueError('Select the exact local account Prefs.xml; credentials are not needed')
    if marker.exists():
        installed=json.loads(marker.read_text())
        if installed['game']!=str(game) or installed['gui']!=str(gui):
            raise ValueError('State belongs to a different installation')
        _,_,_,current=db.snapshot(game);db.assert_owned(current,installed['installed_hashes'])
        for row in json.loads((state/'runtime-textures.json').read_text()):
            if db.digest(Path(row['file']).read_bytes())!=row['sha256']:raise ValueError('Installed DDS changed')
        apply_gui(integration.plan(gui,game,True))
        print('Already installed; verified owned files and repaired optional GUI integration.')
        return
    reader,number,files,current=db.snapshot(game)
    legacy=json.loads(args.adopt_legacy_state.read_text()) if args.adopt_legacy_state else None
    if legacy:
        if legacy.get('pack_selection')!={'omni_af':False,'tank':False}:
            raise ValueError('Legacy adoption requires stock selected on disk')
        db.assert_owned(current,{k:legacy['installed_'+k+'_sha256'] for k in current})
    elif running(game):
        raise ValueError('Exit regular AO normally before installing stock-HD database allocations')
    changes=integration.plan(gui,game,True)
    previous={path:path.read_bytes() if path.exists() else None for path in changes}
    sources=[];payloads=[];selected=[]
    for spec in pack['resources']:
        ident=spec['id'];key=(3030004,ident);original_pointer=reader.records[key]
        if legacy:
            stock=legacy['pack_catalog'].get('legacy_stock',legacy['pack_catalog']['stock'])[str(ident)]
            reader.records[key]=stock['virtual_offset']
        try:original,_=reader.get(*key)
        finally:reader.records[key]=original_pointer
        if db.digest(original)!=spec['stock_sha256']:
            raise ValueError('Original stock texture differs from supported build: '+str(ident))
        stock_image=decode_fctx(original,ident)
        stock_fctx,stock_dds=encode(stock_image,spec,original[:40])
        art=REPO/'packs/omni-af'/spec['artwork']
        if db.digest(art.read_bytes())!=spec['artwork_sha256']:raise ValueError('Custom artwork hash changed')
        with Image.open(art) as image:_,custom_dds=encode(image,spec,original[:40])
        for mode,data in [('stock',stock_dds),('custom',custom_dds)]:
            file=state/'textures'/f'{mode}-{ident}.dds';db.atomic(file,data)
            sources.append({'id':ident,'mode':mode,'file':str(file),'sha256':db.digest(data),'width':spec['width'],'height':spec['height']})
        payloads.append({'id':ident,'payload':stock_fctx})
        if legacy:
            active,_=reader.get(*key)
            expected=legacy['pack_catalog']['stock'][str(ident)]
            if db.digest(active)!=expected['sha256']:
                raise ValueError('Legacy disk stock pointer identity differs')
            if ImageSize(active)!=(spec['width'],spec['height']):raise ValueError('Legacy GPU baseline is not HD')
            selected.append({'type':3030004,'id':ident,'sha256':db.digest(active)})
    if legacy:desired=current
    else:desired,selected=db.append(reader,number,current,payloads)
    write_json(state/'runtime-textures.json',sources)
    write_json(state/'native-manifest.json',selected)
    # Checkpoints are private and must match if a failed attempt is retried.
    for key,data in current.items():
        backup=state/'backups'/(key+'.original')
        if backup.exists() and backup.read_bytes()!=data:raise ValueError('Existing checkpoint belongs to different database bytes')
        if not backup.exists():db.atomic(backup,data)
    write_json(state/'gui-before.json',{str(path):None if data is None else base64.b64encode(data).decode() for path,data in previous.items()})
    try:
        if not legacy:db.write(files,desired)
        db.verify_native(game,state/'native-manifest.json',state/'native-verification.log')
        apply_gui(changes)
        config={'game':str(game),'preferences':str(preferences),'hashes':pack['client_hashes']}
        write_json(state/'config.json',config)
        write_json(marker,{'schema':1,'pack':pack['id'],'version':pack['version'],'game':str(game),'gui':str(gui),
                           'adopted_database':bool(legacy),'part':number,
                           'original_hashes':{k:db.digest(v) for k,v in current.items()},
                           'installed_hashes':{k:db.digest(v) for k,v in desired.items()}})
    except BaseException:
        if not legacy:
            db.restore_owned(files,current,desired)
        apply_gui(previous)
        raise
    print('Installed: stock-HD verified by the native reader; optional armor controls added.')


def ImageSize(payload):
    import struct
    return struct.unpack_from('<HH',payload,28)


def uninstall(args):
    state=args.state.resolve();marker=state/'installed.json'
    installed=json.loads(marker.read_text());game=Path(installed['game']);gui=Path(installed['gui'])
    if running(game):
        raise ValueError('Exit regular AO normally before removing its loaded GUI controls and database selection')
    stop(state)
    reader,number,files,current=db.snapshot(game);db.assert_owned(current,installed['installed_hashes'])
    changes=integration.plan(gui,game,False)
    previous={path:path.read_bytes() if path.exists() else None for path in changes}
    original=current
    if not installed['adopted_database']:
        original={k:(state/'backups'/(k+'.original')).read_bytes() for k in current}
        db.assert_owned(original,installed['original_hashes'])
    try:
        if not installed['adopted_database']:db.write(files,original)
        apply_gui(changes)
        marker.unlink()
    except BaseException:
        if not installed['adopted_database']:db.restore_owned(files,current,original)
        apply_gui(previous)
        raise
    print('Uninstalled. Armor controls removed; private backups retained for review.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['install','uninstall','status'])
    parser.add_argument('--state',type=Path,required=True)
    parser.add_argument('--game',type=Path)
    parser.add_argument('--gui',type=Path)
    parser.add_argument('--preferences',type=Path)
    parser.add_argument('--adopt-legacy-state',type=Path)
    args=parser.parse_args()
    if args.action=='install':
        if not all((args.game,args.gui,args.preferences)):parser.error('install requires --game, --gui, --preferences')
        install(args)
    elif args.action=='uninstall':uninstall(args)
    else:
        marker=args.state/'installed.json'
        print(json.dumps({'installed':marker.is_file(),'companion':json.loads((args.state/'controller-status.json').read_text()) if (args.state/'controller-status.json').exists() else None}))


if __name__=='__main__':main()
