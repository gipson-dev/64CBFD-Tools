"""Check the complete release body and close the auxiliary-pointer register transfer."""
import csv
import io
import struct
from tools.experiments import game_node_release_candidates as recovery
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = recovery.ENTRY, recovery.ROM, recovery.WORDS
FUNCTION, SOURCE, SELECTED = recovery.FUNCTION, recovery.SOURCE, recovery.SELECTED
RAW = tuple(int(v,16) for v in '''27BDFFE0 AFB00018 00808025 AFBF001C AFA50024 8FAE0024 55C00004 920F0009 0C000000 02002025 920F0009 51E0001A 8E040034 92180008 8FB90024 5300000F 8E040048 13200007 24050004 0C000000 8E040028 0C000000 8E04002C 10000007 8E040048 0C000000 8E040028 8E04002C 0C000000 24050004 8E040048 10800003 00000000 0C000000 00000000 0C000000 92040001 8E040034 8FA80024 5080000A 8E040044 11000005 00000000 0C000000 00000000 10000004 8E040044 0C000000 24050004 8E040044 50800004 8E04004C 0C000000 00000000 8E04004C 8FA90024 5080000A 8E040050 11200005 00000000 0C000000 00000000 10000004 8E040050 0C000000 24050004 8E040050 8FAA0024 10800009 00000000 11400005 00000000 0C000000 00000000 10000003 00000000 0C000000 24050004 3C020000 24420000 8C4B0000 560B0004 8E020058 8E0C0054 AC4C0000 8E020058 50400004 8E020054 8E0D0054 AC4D0054 8E020054 10400003 00000000 8E0E0058 AC4E0058 0C000000 02002025 8FBF001C 8FB00018 27BD0020 03E00008 00000000'''.split())
RELOCATIONS = {32:[('R_MIPS_26','func_15031C14')],76:[('R_MIPS_26','func_10004074')],
    84:[('R_MIPS_26','func_10004074')],100:[('R_MIPS_26','func_100043B4')],
    112:[('R_MIPS_26','func_100043B4')],132:[('R_MIPS_26','func_1503F7B8')],
    140:[('R_MIPS_26','func_1518CA04')],172:[('R_MIPS_26','func_10004074')],
    188:[('R_MIPS_26','func_100043B4')],208:[('R_MIPS_26','func_10004074')],
    240:[('R_MIPS_26','func_10004074')],256:[('R_MIPS_26','func_100043B4')],
    288:[('R_MIPS_26','func_10004074')],304:[('R_MIPS_26','func_100043B4')],
    312:[('R_MIPS_HI16','D_800C3EE0')],316:[('R_MIPS_LO16','D_800C3EE0')],
    380:[('R_MIPS_26','func_10004074')]}
TRANSFER = {40:0x8E020044,46:0x8E020044,49:0x8E020044,50:0x50400004,53:0x00402025}


def recipe(words):
    if tuple(words)!=RAW:raise ValueError('stale complete node release body')
    return [TRANSFER.get(i,w) for i,w in enumerate(words)]


def guard_rows(path):
    text,functions,relocations=parse_object(path);target=functions[FUNCTION];start=target['value']
    if target['size'] not in (408,412) or any(text[start+408:start+target['size']]):
        raise ValueError('unexpected node release extent')
    relative={o-start:uses for o,uses in relocations.items() if start<=o<start+target['size']}
    if relative!=RELOCATIONS:raise ValueError('stale node release relocations')
    words=struct.unpack_from('>102I',text,start);rows=[]
    for i,(old,new) in enumerate(zip(words,recipe(words))):
        if old==new:continue
        if i*4 in relative:raise ValueError('release transfer crossed a relocation')
        rows.append(dict(filename='generated_5D2C0',function=FUNCTION,offset='0x%X'%(i*4),
            expected='0x%08X'%old,replacement='0x%08X'%new,expected_relocations='-',replacement_relocations='-',
            note='Normalize checked node release auxiliary-pointer register transfer',
            insert_after='',insert_after_relocations='',omit='false'))
    assert len(rows)==5
    return rows


compile_candidate=recovery.compile_candidate
install=recovery.install


def append_guards(path,before,obj):
    if path.read_bytes()!=before or not before.endswith(b'\n'):raise ValueError('stale node release guard manifest')
    reader=csv.DictReader(io.StringIO(before.decode('ascii')));rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):raise ValueError('release guards already published')
    output=io.StringIO(newline='')
    csv.DictWriter(output,fieldnames=reader.fieldnames,lineterminator='\n').writerows(guard_rows(obj))
    path.write_bytes(before+output.getvalue().encode('ascii'))
