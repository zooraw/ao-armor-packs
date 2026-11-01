"""Owned, reversible stock-HD allocations; never write while AO is running."""
from pathlib import Path
import hashlib
import os
import struct
import subprocess
import sys
from rdb import Rdb


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.aap-staging')
    created=False
    try:
        with temporary.open('xb') as stream:
            created=True
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if created and temporary.exists():temporary.unlink()


def read_header(path):
    with Path(path).open('rb') as stream:return stream.read(4096)


def snapshot(game):
    root=Path(game)/'cd_image/data/db'
    reader=Rdb(root)
    parts=list(root.glob('ResourceDatabase.dat.[0-9][0-9][0-9]'))
    if not parts:raise ValueError('Unsupported unsegmented database')
    part=max(parts,key=lambda p:int(p.suffix[1:]));number=int(part.suffix[1:])
    base=read_header(root/'ResourceDatabase.dat')
    files={'index':root/'ResourceDatabase.idx','part':part,'header':root/'ResourceDatabase.dat'}
    data={'index':files['index'].read_bytes(),'part':part.read_bytes(),'header':base}
    if reader.allocated_end!=(reader.part_size-reader.block_offset)*number+len(data['part'])-1:
        raise ValueError('Database final-part EOF differs from verified layout')
    return reader,number,files,data


def append(reader,number,current,records):
    index=bytearray(current['index']);tail=bytearray()
    delta=(reader.part_size-reader.block_offset)*number
    selected=[]
    for row in records:
        payload=row['payload'];key=(3030004,row['id'])
        position=len(current['part'])+len(tail);virtual=delta+position
        if virtual//reader.part_size!=number or position+22+len(payload)>=reader.part_size:
            raise ValueError('Final database part has insufficient capacity')
        tail+=b'\xfa\xfa'+struct.pack('<IIiii',len(payload)+22,len(payload)+12,*key,len(payload))+payload
        struct.pack_into('<II',index,reader.slots[key],virtual>>32,virtual&0xffffffff)
        selected.append({'type':3030004,'id':row['id'],'sha256':digest(payload)})
    part=current['part']+tail;end=delta+len(part)-1;header=bytearray(current['header'])
    for low,high in [(0,128),(8,136)]:
        struct.pack_into('<I',header,low,end&0xffffffff);struct.pack_into('<I',header,high,end>>32)
    return {'index':bytes(index),'part':bytes(part),'header':bytes(header)},selected


def write(files,data):
    atomic(files['part'],data['part'])
    with files['header'].open('r+b') as stream:
        stream.write(data['header']);stream.flush();os.fsync(stream.fileno())
    atomic(files['index'],data['index'])


def restore_owned(files,before,attempted):
    """Rollback even a partially written layout, only while bytes remain ours."""
    actual={'index':files['index'].read_bytes(),'part':files['part'].read_bytes(),
            'header':read_header(files['header'])}
    for key,data in actual.items():
        if data not in (before[key],attempted[key]):
            raise ValueError('Concurrent database writer; refusing rollback')
    write(files,before)


def verify_native(game,manifest,log):
    powershell=Path(os.environ['WINDIR'])/'SysWOW64/WindowsPowerShell/v1.0/powershell.exe'
    result=subprocess.run([str(powershell),'-NoProfile','-File',str(Path(__file__).parent/'native_verify.ps1'),
                           '-GamePath',str(game),'-DatabasePath',str(Path(game)/'cd_image/data/db/ResourceDatabase'),
                           '-ManifestPath',str(manifest)],cwd=game,capture_output=True,text=True,
                          timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
    Path(log).write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise ValueError('Client-native verification failed; see the private native-verification.log')


def assert_owned(current,expected):
    for key,data in current.items():
        if digest(data)!=expected[key]:raise ValueError('Database changed outside this installation: '+key)
