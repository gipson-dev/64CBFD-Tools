"""Checked initialization schedule; no body insertion, deletion or relocation rewrite."""
import csv
import io
import struct
from tools.experiments import game_animation_node_constructor_candidates as recovery
from tools.experiments.game_actor_segment_selector_matching import fields
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = recovery.ENTRY, recovery.ROM, recovery.WORDS
FUNCTION, SOURCE, SELECTED = recovery.FUNCTION, recovery.SOURCE, recovery.SELECTED
RAW = tuple(int(v,16) for v in '''27BDFFD0 AFB10018 00A08825 AFBF001C AFB00014 AFA40030 AFA60038 AFA7003C 8FAE0030 8FAF003C 91C3003B 31F80008 14600003 00000000 10000084 00001025 17000013 3C100000 8E100000 8FA8004C 52000010 2404005C 92190000 8E020054 14790009 00000000 920A0006 150A0006 00000000 920B0001 162B0003 00000000 10000072 00001025 1440FFF3 00408025 2404005C 24050001 00003025 0C000000 24070002 8FA5003C 8FA8004C 14400003 00408025 10000065 00001025 3C030000 8C630000 00004825 3C010000 10600004 240E00FF AC620058 3C030000 8C630000 AC430054 AC400058 8FAC0030 AC220000 3C013F80 918D003B 44812000 A0510001 AC400024 AC400028 AC40002C AC400030 A04E0003 AC400044 A0450004 A0480006 A04D0000 E4440040 8FAF0038 24010004 24060002 A04F0002 8FA40044 8FA30054 AC400038 AC40003C A0400008 A0400009 A4400018 A440001A 8FB80050 24070002 A0580007 94790000 30B80004 24050001 A459000A 946A0002 A44A000C 946B0004 AC400048 A44B000E 8FAC0058 A0440016 A04C0017 8FAD0040 A04D0015 8FAE005C A0400013 AC40004C AC400050 A0400005 A4400022 A44E001E 8FAF0060 10810002 A44F0020 13000008 24040080 0C000000 AFA90024 8FA90024 14400004 AE020034 10000002 24090001 AC400034 8FA20048 3419FFFF 02002025 54400004 A602001C 10000002 A619001C A602001C 15200005 8FA50030 0C000000 AFA90024 8FA90024 01224825 11200006 02002025 02002025 0C000000 24050001 10000004 00001025 0C000000 8FA50030 02001025 8FBF001C 8FB00014 8FB10018 03E00008 27BD0030'''.split())
RELOCATIONS = {68:[('R_MIPS_HI16','D_800C3EE0')],72:[('R_MIPS_LO16','D_800C3EE0')],
    156:[('R_MIPS_26','allocate_memory')],188:[('R_MIPS_HI16','D_800C3EE0')],
    192:[('R_MIPS_LO16','D_800C3EE0')],200:[('R_MIPS_HI16','D_800C3EE0')],
    216:[('R_MIPS_HI16','D_800C3EE0')],220:[('R_MIPS_LO16','D_800C3EE0')],
    236:[('R_MIPS_LO16','D_800C3EE0')],460:[('R_MIPS_26','allocate_memory')],
    532:[('R_MIPS_26','func_1502FFD8')],560:[('R_MIPS_26','func_15030158')],
    576:[('R_MIPS_26','func_15031A50')]}
SCHEDULE = {62:63,63:62,64:72,65:74,66:64,67:65,68:66,69:67,70:68,71:69,72:70,73:71,
    74:73,75:77,76:79,77:78,78:86,79:80,80:81,81:82,82:83,83:84,84:85,85:88,86:89,
    87:90,88:75,89:92,90:93,92:76,93:94,94:95,95:87,96:97,97:98,98:96,99:100,
    100:101,101:99,104:109,105:110,106:104,107:105,108:106,109:107,110:108}


def recipe(words):
    if tuple(words) != RAW:
        raise ValueError('stale complete animation node constructor')
    renamed = list(words)
    for index in (52,68): renamed[index] = fields(words[index],rt=15)
    for index in (74,77): renamed[index] = fields(words[index],rt=14)
    assert set(SCHEDULE) == set(SCHEDULE.values())
    return [renamed[SCHEDULE.get(index,index)] for index in range(WORDS)]


def guard_rows(path):
    text,functions,relocations = parse_object(path)
    target=functions[FUNCTION];start=target['value']
    if target['size'] not in (608,612) or any(text[start+608:start+target['size']]):
        raise ValueError('unexpected animation node constructor extent')
    words=struct.unpack_from('>152I',text,start)
    relative={o-start:uses for o,uses in relocations.items() if start<=o<start+target['size']}
    if relative!=RELOCATIONS: raise ValueError('stale animation node constructor relocations')
    rows=[]
    for index,(old,new) in enumerate(zip(words,recipe(words))):
        if old==new: continue
        if index*4 in relative: raise ValueError('constructor schedule crossed a relocation')
        rows.append(dict(filename='generated_5D2C0',function=FUNCTION,offset='0x%X'%(index*4),
            expected='0x%08X'%old,replacement='0x%08X'%new,expected_relocations='-',replacement_relocations='-',
            note='Normalize checked animation node initialization schedule and closed temporary register swap',
            insert_after='',insert_after_relocations='',omit='false'))
    assert len(rows)==47
    return rows


compile_candidate = recovery.compile_candidate
install = recovery.install


def append_guards(path,before,obj):
    if path.read_bytes()!=before or not before.endswith(b'\n'):
        raise ValueError('stale node constructor guard manifest')
    reader=csv.DictReader(io.StringIO(before.decode('ascii')));rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):
        raise ValueError('node constructor guards already published')
    output=io.StringIO(newline='')
    csv.DictWriter(output,fieldnames=reader.fieldnames,lineterminator='\n').writerows(guard_rows(obj))
    path.write_bytes(before+output.getvalue().encode('ascii'))
