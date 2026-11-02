"""Install PRK armor sidecars/integration without changing its SQLite database."""
import argparse
import base64
import json
from pathlib import Path
from database import atomic,digest
from install import running,stop,apply_gui,write_json
from prk_materials import profile,verify_sources,switch
from prefs import read_selection
import integration


def install(args):
    client=args.client.resolve();gui=args.profile.resolve()/'Gui';state=args.state.resolve()
    if running(client):raise ValueError('Exit the selected PRK game normally before installing its GUI integration')
    state.mkdir(parents=True,exist_ok=True);marker=state/'installed.json'
    spec=profile();rows=verify_sources(client)
    if not args.preferences.is_file():raise ValueError('Select the PRK account Prefs.xml')
    if marker.exists():
        installed=json.loads(marker.read_text())
        if installed['client']!=str(client) or installed['profile']!=str(args.profile.resolve()):
            raise ValueError('Private state belongs to another PRK client/profile')
        for name,expected in installed['gui_hashes'].items():
            path=Path(name)
            if not path.is_file() or digest(path.read_bytes())!=expected:
                raise ValueError('PRK GUI changed; uninstall armor integration before replacing the GUI')
        print('PRK armor already installed; source/resource and integration hashes verified.')
        return
    changes=integration.plan(gui,client,True,layouts=spec['gui_layouts'])
    for row in rows:
        destination=Path(row['target'])
        if destination.exists():raise ValueError('Another material file already owns '+destination.name)
        # Never silently mask an existing pack's work on these resource IDs.
        for folder in [client/'randy-vk/materials',client/'randy-vk/live',*list((client/'randy-vk/packs').glob('*'))]:
            if not folder.is_dir():continue
            for pattern in [f"1010004_{row['id']}_*.png",f"{row['id']}_*.png"]:
                if any(folder.glob(pattern)):raise ValueError('Conflicting PRK material maps for '+str(row['id']))
    before={path:path.read_bytes() if path.exists() else None for path in changes}
    for path,data in before.items():
        if path.name in ['AOU_Armor_Menu.xml','armor-packs.html'] and data is not None:
            raise ValueError('Existing optional armor integration must be removed first')
    # PRK help names the correct launcher, independently of retail AO's guide.
    for path,data in list(changes.items()):
        if path.name=='armor-packs.html':
            changes[path]=data.replace(b'AO Armor Packs',b'PRK Armor Packs').replace(b'normal game launcher',b'Project Rubi-Ka launcher')
    choices=read_selection(args.preferences)
    try:
        switch(rows,choices);apply_gui(changes)
        write_json(state/'config.json',{'client':str(client),'profile':str(args.profile.resolve()),
                   'preferences':str(args.preferences.resolve()),'hashes':spec['client_hashes'],'files':rows})
        write_json(marker,{'schema':1,'backend':'prk-ao-vk','client':str(client),'profile':str(args.profile.resolve()),
                   'files':rows,'gui_hashes':{str(p):digest(v) for p,v in changes.items()},
                   'gui_originals':{str(p):None if v is None else base64.b64encode(v).decode() for p,v in before.items()},
                   'database':'read-only: eight stock records verified; no database writes'})
    except BaseException:
        switch(rows,{'omni_af':False,'tank':False});apply_gui(before);raise
    print('PRK armor installed: eight opaque stock/artwork records verified; SQLite unchanged; live sidecars prepared.')


def uninstall(args):
    state=args.state.resolve();marker=state/'installed.json';installed=json.loads(marker.read_text())
    if running(Path(installed['client'])):raise ValueError('Exit PRK normally before removing its GUI controls')
    stop(state)
    for name,expected in installed['gui_hashes'].items():
        path=Path(name)
        if not path.is_file() or digest(path.read_bytes())!=expected:
            raise ValueError('PRK GUI changed externally; refusing to restore stale files')
    switch(installed['files'],{'omni_af':False,'tank':False})
    previous={Path(name):None if value is None else base64.b64decode(value) for name,value in installed['gui_originals'].items()}
    apply_gui(previous);marker.unlink()
    print('PRK armor removed; exact pre-armor GUI bytes restored; SQLite unchanged.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['install','uninstall'])
    parser.add_argument('--state',type=Path,required=True)
    parser.add_argument('--client',type=Path)
    parser.add_argument('--profile',type=Path)
    parser.add_argument('--preferences',type=Path)
    args=parser.parse_args()
    if args.action=='install':
        if not all([args.client,args.profile,args.preferences]):parser.error('install requires client, profile and preferences')
        install(args)
    else:uninstall(args)


if __name__=='__main__':main()
