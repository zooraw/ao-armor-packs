from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from PIL import Image
from database import digest
from prk_materials import opaque_cat,switch


class PrkTests(unittest.TestCase):
    def test_opaque_fast_path_rejects_rgb565_green_key(self):
        self.assertTrue(opaque_cat(Image.new('RGB',(4,4),(24,24,24))))
        self.assertTrue(opaque_cat(Image.new('RGB',(4,4),(96,0,0))))
        for color in [(0,255,0),(7,252,7)]:
            self.assertFalse(opaque_cat(Image.new('RGB',(4,4),color)))

    def test_groups_toggle_independently_and_conflicting_files_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);rows=[]
            for ident,group in [(18000,'omni_af'),(206969,'tank')]:
                source=root/f'source-{ident}.png';source.write_bytes(str(ident).encode())
                rows.append({'id':ident,'source':str(source),'sha256':digest(source.read_bytes()),
                             'group':group,'target':str(root/'materials'/f'{ident}.png')})
            switch(rows,{'omni_af':True,'tank':True})
            switch(rows,{'omni_af':False,'tank':True})
            self.assertFalse(Path(rows[0]['target']).exists());self.assertTrue(Path(rows[1]['target']).exists())
            switch(rows,{'omni_af':True,'tank':False})
            self.assertTrue(Path(rows[0]['target']).exists());self.assertFalse(Path(rows[1]['target']).exists())
            switch(rows,{'omni_af':False,'tank':False})
            self.assertTrue(all(not Path(r['target']).exists() for r in rows))
            Path(rows[0]['target']).write_bytes(b'another writer')
            with self.assertRaises(ValueError):switch(rows,{'omni_af':True,'tank':True})
            self.assertEqual(Path(rows[0]['target']).read_bytes(),b'another writer')
            self.assertFalse(Path(rows[1]['target']).exists())

    def test_disable_uses_ownership_even_when_source_was_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'owned.png';target.write_bytes(b'owned')
            row={'id':18000,'source':str(root/'missing.png'),'sha256':digest(b'owned'),'group':'omni_af','target':str(target)}
            switch([row],{'omni_af':False,'tank':False})
            self.assertFalse(target.exists())


if __name__=='__main__':unittest.main()
