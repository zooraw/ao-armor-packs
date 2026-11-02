"""PRK ao-vk sidecars: native renderer owns upload/reload; SQLite stays read-only."""
from io import BytesIO
from pathlib import Path
import json
import sqlite3
from PIL import Image,ImageChops
from database import atomic,digest

REPO=Path(__file__).resolve().parent.parent
GROUPS={'omni_af':{18000,17988,204160,15805,15806,15807,15808},'tank':{206969}}


def profile():
    return json.loads((REPO/'packs/omni-af/prk-profile.json').read_text())


def opaque_cat(image):
    """The PRK CAT fast path keeps resource identity only without green key."""
    red,green,blue=image.convert('RGB').split()
    mask=ImageChops.multiply(red.point(lambda v:255 if v<8 else 0),green.point(lambda v:255 if v>=252 else 0))
    return ImageChops.multiply(mask,blue.point(lambda v:255 if v<8 else 0)).getbbox() is None


def verify_sources(client):
    spec=profile();client=Path(client)
    for name,expected in spec['client_hashes'].items():
        if digest((client/name).read_bytes())!=expected:raise ValueError('Unsupported PRK build: '+name)
    pack=json.loads((REPO/'packs/omni-af/pack.json').read_text())
    db=sqlite3.connect((client/'cd_image/rdb.db').as_uri()+'?mode=ro',uri=True)
    rows=[]
    try:
        db.execute('BEGIN')
        for row in pack['resources']:
            ident=row['id'];resource=db.execute('SELECT data FROM rdb_1010004 WHERE id=?',(ident,)).fetchone()
            if not resource or digest(resource[0])!=spec['resource_hashes'][str(ident)]:
                raise ValueError('PRK stock resource differs: '+str(ident))
            image=Image.open(BytesIO(resource[0]));image.load()
            if not opaque_cat(image):raise ValueError('Keyed CAT garment needs a different backend: '+str(ident))
            source=REPO/'packs/omni-af'/row['artwork'];data=source.read_bytes()
            if digest(data)!=row['artwork_sha256']:raise ValueError('Custom artwork changed: '+str(ident))
            with Image.open(BytesIO(data)) as art:
                art.load()
                if art.width*image.height!=art.height*image.width:raise ValueError('PRK UV aspect differs: '+str(ident))
                if not opaque_cat(art):raise ValueError('Custom artwork contains the PRK green key')
            rows.append({'id':ident,'type':1010004,'source':str(source),'sha256':digest(data),
                         'group':'tank' if ident==206969 else 'omni_af',
                         'target':str(client/'randy-vk/materials'/f'1010004_{ident}_d.png')})
    finally:db.close()
    return rows


def switch(rows,selection):
    if set(selection)!=set(GROUPS) or any(type(v) is not bool for v in selection.values()):
        raise ValueError('Explicit boolean choices required for both PRK armor groups')
    changes=[]
    for row in rows:
        source=Path(row['source']).read_bytes() if selection[row['group']] else None
        if source is not None and digest(source)!=row['sha256']:raise ValueError('PRK custom source changed')
        target=Path(row['target']);before=target.read_bytes() if target.exists() else None
        if before is not None and digest(before)!=row['sha256']:
            raise ValueError('PRK material sidecar belongs to another writer: '+target.name)
        desired=source if selection[row['group']] else None
        changes.append((target,before,desired))
    done=[]
    try:
        for target,before,desired in changes:
            if before==desired:continue
            if desired is None:target.unlink()
            else:atomic(target,desired)
            done.append((target,before,desired))
    except BaseException:
        for target,before,desired in reversed(done):
            now=target.read_bytes() if target.exists() else None
            if now!=desired:raise ValueError('Another writer changed sidecar during rollback')
            if before is None:target.unlink(missing_ok=True)
            else:atomic(target,before)
        raise
    return [{'id':r['id'],'mode':'custom' if selection[r['group']] else 'stock'} for r in rows]
