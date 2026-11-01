import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from types import SimpleNamespace
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from PIL import Image
import database
import integration
from prefs import read_selection
from rdb import Rdb
from textures import encode,decode_fctx


class InstallationTests(unittest.TestCase):
    def test_failed_atomic_create_preserves_another_writers_staging_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'target';staging=path.with_name('target.aap-staging')
            staging.write_bytes(b'another operation')
            with self.assertRaises(FileExistsError):database.atomic(path,b'ours')
            self.assertEqual(staging.read_bytes(),b'another operation')

    def test_partial_rollback_checks_ownership_separately_from_layout_validity(self):
        with tempfile.TemporaryDirectory() as folder:
            files={key:Path(folder)/key for key in ('index','part','header')}
            before={key:(key+' before').encode() for key in files}
            after={key:(key+' after').encode() for key in files}
            for key,path in files.items():path.write_bytes(after[key] if key=='part' else before[key])
            database.restore_owned(files,before,after)
            self.assertTrue(all(path.read_bytes()==before[key] for key,path in files.items()))
            files['index'].write_bytes(b'another writer')
            with self.assertRaises(ValueError):database.restore_owned(files,before,after)
            self.assertEqual(files['index'].read_bytes(),b'another writer')

    def test_optional_gui_install_repeat_and_remove_preserve_unrelated_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);gui=root/'Gui';game=root/'Game'
            for name in integration.LAYOUTS:
                base=gui/name;(base/'ActionMenu').mkdir(parents=True);(base/'OptionPanel').mkdir()
                (base/'ActionMenu/Menu_AOU.xml').write_text('<Menu>\n<MenuEntry label="Existing"/>\n</Menu>')
                (base/'LoginPrefs.xml').write_text('<Root>\n<Value name="existing" value="true"/>\n</Root>')
                (base/'OptionPanel/Root.xml').write_text('<root>\n<ScrollView label="Existing"/>\n</root>')
            self.assertFalse(any('aou_armor' in p.read_text() for p in gui.rglob('*.xml')))
            first=integration.plan(gui,game,True)
            for path,data in first.items():
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
                if path.suffix=='.xml':ET.fromstring(data)
            second=integration.plan(gui,game,True)
            self.assertEqual(first,second)
            for path,data in integration.plan(gui,game,False).items():
                if data is None:path.unlink(missing_ok=True)
                else:path.write_bytes(data)
            self.assertFalse(any('aou_armor' in p.read_text() for p in gui.rglob('*.xml')))
            for name in integration.LAYOUTS:
                self.assertIn('existing',(gui/name/'LoginPrefs.xml').read_text())
                self.assertIn('Existing',(gui/name/'ActionMenu/Menu_AOU.xml').read_text())

    def test_legacy_integration_migration_has_no_duplicate_controls(self):
        old='<root>\n<ScrollView label="Existing"/>\n'+integration.OPTIONS+'\n</root>'
        result=integration.inject(old,'options',integration.OPTIONS)
        self.assertEqual(result.count('scroll_client="aou_armor_scroll"'),1)
        self.assertEqual(result.count('label="Existing"'),1)

    def test_append_roundtrip_via_real_parser_preserves_other_bytes_and_native_eof(self):
        keys=[(3030004,i) for i in (18000,17988,204160,15805,15806,15807,15808,206969)]
        index=bytearray(512);struct.pack_into('<I',index,12,4096);struct.pack_into('<i',index,72,256)
        struct.pack_into('<I',index,184,65536);struct.pack_into('<h',index,264,len(keys))
        slots={}
        for i,key in enumerate(keys):
            at=284+i*16;slots[key]=at;struct.pack_into('>ii',index,at+8,*key)
        current={'index':bytes(index),'part':b'P'*8192,'header':b'\0'*4096}
        reader=SimpleNamespace(part_size=65536,block_offset=4096,slots=slots)
        rows=[{'id':key[1],'payload':('unique-'+str(key[1])).encode()} for key in keys]
        desired,selected=database.append(reader,1,current,rows)
        allowed={x for at in slots.values() for x in range(at,at+8)}
        self.assertTrue(all(a==b or i in allowed for i,(a,b) in enumerate(zip(index,desired['index']))))
        self.assertTrue(desired['part'].startswith(current['part']))
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'ResourceDatabase.idx').write_bytes(desired['index'])
            (root/'ResourceDatabase.dat').write_bytes(desired['header'])
            (root/'ResourceDatabase.dat.001').write_bytes(desired['part'])
            actual=Rdb(root)
            for row in rows:self.assertEqual(actual.get(3030004,row['id'])[0],row['payload'])
            self.assertEqual(actual.logical_end,actual.allocated_end)
            self.assertEqual(actual.logical_end,61440+len(desired['part'])-1)
        with self.assertRaises(ValueError):
            database.append(reader,1,current,[{'id':18000,'payload':b'x'*65536}])

    def test_texture_roundtrip_and_malformed_inputs(self):
        header=bytearray(40);struct.pack_into('<III',header,0,3030004,18000,2)
        header[16:20]=b'FCTX';header[36:40]=b'DXT1'
        spec={'width':8,'height':4,'levels':3}
        payload,dds=encode(Image.new('RGB',(16,8),(200,0,0)),spec,header)
        image=decode_fctx(payload,18000)
        self.assertEqual(image.size,(8,4));self.assertGreater(image.getpixel((0,0))[0],190)
        self.assertEqual(dds[:4],b'DDS ')
        for invalid in (payload[:-1],payload+b'x',payload[:36]+b'NOPE'+payload[40:]):
            with self.assertRaises(ValueError):decode_fctx(invalid,18000)
        with self.assertRaises(ValueError):encode(Image.new('RGB',(8,8)),spec,header)

    def test_preferences_read_only_named_booleans_and_reject_duplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'Prefs.xml'
            path.write_text('<Root><Value name="unrelated" value="private"/><Value name="aou_armor_tank" value="false"/></Root>')
            self.assertEqual(read_selection(path),{'omni_af':True,'tank':False})
            path.write_text('<Root><Value name="aou_armor_tank" value="false"/><Value name="aou_armor_tank" value="true"/></Root>')
            with self.assertRaises(ValueError):read_selection(path)


if __name__=='__main__':unittest.main()
