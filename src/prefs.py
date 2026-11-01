"""Read only the two armor preferences; never collect account details."""
import xml.etree.ElementTree as ET

PREFERENCES = {'omni_af': 'aou_armor_omni_af', 'tank': 'aou_armor_tank'}


def read_selection(path):
    values = {}
    for element in ET.parse(path).getroot().iter('Value'):
        name = element.get('name')
        if name not in PREFERENCES.values():
            continue
        if name in values or element.get('value') not in ('true', 'false'):
            raise ValueError('Malformed or duplicate armor preference')
        values[name] = element.get('value') == 'true'
    return {key: values.get(name, True) for key, name in PREFERENCES.items()}
