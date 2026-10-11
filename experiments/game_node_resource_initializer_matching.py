"""Checked post-loader read schedule, temporary allocation and delay-slot mask."""
import csv
import io
import struct
from tools.experiments import game_node_resource_initializer_candidates as recovery
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = recovery.ENTRY, recovery.ROM, recovery.WORDS
FUNCTION, SOURCE, SELECTED = recovery.FUNCTION, recovery.SOURCE, recovery.SELECTED
RAW = tuple(int(v,16) for v in '''27BDFFC0 AFB00028 00808025 AFBF002C AFA50044 8E0E0024 55C00054 00001025 82050017 2401FFFF 26060024 14A1000E 26070014 92040001 260F0030 AFAF0010 AFA00018 AFA00014 26050024 26060014 0C000000 27A7003C 50400010 920C0004 10000042 24020001 92040001 27B8003C 26190030 26080048 AFA80018 AFB90014 0C000000 AFB80010 50400004 920C0004 10000036 24020001 920C0004 8E090024 8FAA003C 8FAB0044 318D0010 012A2023 15A00027 91620066 304E000C 24010008 55C10024 8FB9003C 8E0F0030 24050001 24060002 11E0001E 24070002 0C000000 AFA40034 14400003 AE020028 1000001F 24020001 8FA40034 24050001 24060002 0C000000 24070002 14400006 AE02002C 0C000000 8E040028 AE000028 10000013 24020001 8FA4003C 8E050028 0C000000 8FA60034 8FA4003C 8E05002C 0C000000 8FA60034 24180001 10000005 A2180008 8FB9003C AE190028 8FA8003C AE08002C 24090001 A2090009 00001025 8FBF002C 8FB00028 27BD0040 03E00008 00000000'''.split())
RELOCATIONS = {80:[('R_MIPS_26','func_1502FE10')],128:[('R_MIPS_26','func_1503F62C')],
    220:[('R_MIPS_26','allocate_memory')],256:[('R_MIPS_26','allocate_memory')],
    272:[('R_MIPS_26','func_10004074')],300:[('R_MIPS_26','bcopy')],316:[('R_MIPS_26','bcopy')]}
SCHEDULE = {23:0x8FA90044,35:0x8FA90044,38:0x8FA90044,39:0x920D0004,40:0x8E0B0024,
    41:0x8FAC003C,42:0x91220066,43:0x31AE0010,44:0x016C2023,45:0x15C00026,
    46:0x304A000C,48:0x55410024}


def recipe(words):
    if tuple(words)!=RAW: raise ValueError('stale complete node resource initializer')
    return [SCHEDULE.get(i,w) for i,w in enumerate(words)]


def guard_rows(path):
    text,functions,relocations=parse_object(path);target=functions[FUNCTION];start=target['value']
    if target['size'] not in (384,388) or any(text[start+384:start+target['size']]):
        raise ValueError('unexpected node resource initializer extent')
    relative={o-start:uses for o,uses in relocations.items() if start<=o<start+target['size']}
    if relative!=RELOCATIONS: raise ValueError('stale node resource initializer relocations')
    words=struct.unpack_from('>96I',text,start);rows=[]
    for index,(old,new) in enumerate(zip(words,recipe(words))):
        if old==new:continue
        if index*4 in relative:raise ValueError('initializer schedule crossed relocation')
        rows.append(dict(filename='generated_5D2C0',function=FUNCTION,offset='0x%X'%(index*4),
            expected='0x%08X'%old,replacement='0x%08X'%new,expected_relocations='-',replacement_relocations='-',
            note='Normalize checked node resource post-loader read schedule and delay-slot flag mask',
            insert_after='',insert_after_relocations='',omit='false'))
    assert len(rows)==12
    return rows


compile_candidate=recovery.compile_candidate
install=recovery.install


def append_guards(path,before,obj):
    if path.read_bytes()!=before or not before.endswith(b'\n'):
        raise ValueError('stale node resource guard manifest')
    reader=csv.DictReader(io.StringIO(before.decode('ascii')));rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):raise ValueError('initializer guards already published')
    output=io.StringIO(newline='')
    csv.DictWriter(output,fieldnames=reader.fieldnames,lineterminator='\n').writerows(guard_rows(obj))
    path.write_bytes(before+output.getvalue().encode('ascii'))
