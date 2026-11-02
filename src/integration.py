"""Armor controls exist only when this separate pack installs them."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

LAYOUTS=('AOU_CYT','AOU_Slim_CNI','AOU_Slim_CNT')
BEGIN='<!-- AO_ARMOR_PACKS_BEGIN -->'
END='<!-- AO_ARMOR_PACKS_END -->'
MENU='''<Menu label="Armor Packs" name="aou_armor_menu" sub_script="AOU_Armor_Menu.xml" tooltip="Armor Packs" tooltip_body="Switch installed armor artwork immediately"/>'''
DEFAULTS='''<Value name="aou_armor_omni_af" value="true"/>
<Value name="aou_armor_tank" value="true"/>'''
OPTIONS='''<ScrollView label="Armor Packs" v_scrollbar_mode="auto" scroll_client="aou_armor_scroll" max_size="Point(16000,-1)">
  <ScrollViewChild name="aou_armor_scroll">
    <View view_layout="vertical" h_alignment="LEFT" max_size="Point(16000,-1)">
      <TextView value="Checked: custom. Unchecked: original. Changes are immediate with the companion running."/>
      <OptionCheckBox label="Omni-Armed Forces helmet/body" opt_type="variant" opt_variable="aou_armor_omni_af"/>
      <OptionCheckBox label="Omni-Armed Forces Tank Armor" opt_type="variant" opt_variable="aou_armor_tank"/>
    </View>
  </ScrollViewChild>
</ScrollView>'''
HELP='''<html><body><font color=CCInfoHeader>AO Armor Packs</font><br>
Use AOU - Armor Packs or F10 - Armor Packs.<br>
[x] / checked = custom artwork. [ ] / unchecked = original artwork.<br>
Helmet/body and Tank Armor switch independently.<br><br>
The local companion must be running. Use the AO Armor Packs desktop shortcut
to start it and the normal game launcher. The companion can attach to a game
already running. No game restart is needed for an armor choice.<br>
If the artwork does not change, run the shortcut and check the companion status.<br>
Install/uninstall with the separate AO Armor Packs repository. Uninstall restores
the database and removes these controls. The AOU GUI alone does not install armor.
</body></html>'''


def clean(text,kind):
    text=re.sub(r'\n?'+re.escape(BEGIN)+r'.*?'+re.escape(END)+r'\n?', '',text,flags=re.S)
    # Migrate the earlier local prototype without removing unrelated controls.
    if kind=='menu':text=re.sub(r'^[ \t]*<Menu\b[^\n]*sub_script="AOU_Armor_Menu.xml"[^\n]*\n?', '',text,flags=re.M)
    elif kind=='options':text=re.sub(r'[ \t]*<ScrollView\b[^>]*scroll_client="aou_armor_scroll".*?</ScrollView>\s*','',text,flags=re.S)
    elif kind=='prefs':text=re.sub(r'^[ \t]*<Value name="aou_armor_(?:omni_af|tank)"[^\n]*\n?','',text,flags=re.M)
    ET.fromstring(text)
    return text


def inject(text,kind,block=None):
    text=clean(text,kind)
    if block is not None:
        at=text.lower().rfind('</menu>' if kind=='menu' else '</root>')
        if at<0:raise ValueError('Unrecognized AOU XML root')
        text=text[:at]+'\n'+BEGIN+'\n'+block+'\n'+END+'\n'+text[at:]
    ET.fromstring(text)
    return text


def plan(gui_root,game,enabled,layouts=LAYOUTS):
    """Prepare/validate every edit before the installer writes any GUI files."""
    changes={}
    for name in layouts:
        base=Path(gui_root)/name
        if not base.exists():continue
        for file,kind,block in [('ActionMenu/Menu_AOU.xml','menu',MENU),('LoginPrefs.xml','prefs',DEFAULTS),('OptionPanel/Root.xml','options',OPTIONS)]:
            path=base/file
            changes[path]=inject(path.read_text(encoding='utf-8'),kind,block if enabled else None).encode('utf-8')
        submenu=base/'ActionMenu/AOU_Armor_Menu.xml'
        changes[submenu]=(Path(__file__).parent/'armor-menu.xml').read_bytes() if enabled else None
    if not changes:raise ValueError('No supported AOU layout found in the selected Gui directory')
    helpfile=Path(game)/'Scripts/AOU_mod/HelpFiles/armor-packs.html'
    changes[helpfile]=HELP.encode('utf-8') if enabled else None
    # Remove the prototype's redundant AppData copy on uninstall as well.
    optional=Path(gui_root).parent/'scripts/AOU_mod/HelpFiles/armor-packs.html'
    if enabled or optional.exists():changes[optional]=HELP.encode('utf-8') if enabled else None
    return changes
