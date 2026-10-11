"""Full alternate loader; checked closed S0/S1 transfer, no scheduling inserts."""
import csv
import io
import struct
from tools.experiments import game_node_alternate_loader_candidates as recovery
from tools.pad_generated_object import parse_object

ENTRY,ROM,WORDS=recovery.ENTRY,recovery.ROM,recovery.WORDS
FUNCTION,SOURCE,SELECTED=recovery.FUNCTION,recovery.SOURCE,recovery.SELECTED
RAW=tuple(int(v,16) for v in '''27BDFFC0 AFB10028 00808825 AFBF002C AFB00024 AFA50044 AFA60048 AFA7004C 240403F8 24050001 24060002 0C000000 24070002 8FB00058 24050040 14400003 AE020000 1000004C 24020001 0C000000 8E040000 8E0E0000 24020001 27A9003C A1C20215 8E0F0000 02202025 A1E20045 8FB80054 8FA70050 8FA6004C AFB80010 8E190000 AFA90018 8FA50048 272803F0 0C000000 AFA80014 8FAA003C 8E0B0000 24050001 24060002 A16A03F4 8E0D0000 8FAC0044 24070002 A1AC03F5 8E0E0000 A1C003F6 8FA4003C 00047980 0C000000 01E02025 8E180000 24050001 24060002 AF0203E8 8FA4003C 24070002 0004C980 0C000000 03202025 8E080000 AD0203EC 8E110000 8E2403E8 10800006 00000000 8E2903EC 24050001 00003025 15200010 3C073F80 54800005 8E2403EC 0C000000 00000000 8E110000 8E2403EC 14800004 00000000 0C000000 00000000 8E110000 0C000000 02202025 10000007 24020001 44802000 02202025 AFA00014 0C000000 E7A40010 00001025 8FBF002C 8FB00024 8FB10028 03E00008 27BD0040'''.split())
RELOCATIONS={44:[('R_MIPS_26','allocate_memory')],76:[('R_MIPS_26','bzero')],
    144:[('R_MIPS_26','func_1502FE10')],204:[('R_MIPS_26','allocate_memory')],
    240:[('R_MIPS_26','allocate_memory')],300:[('R_MIPS_26','func_10004074')],
    324:[('R_MIPS_26','func_10004074')],336:[('R_MIPS_26','func_10004074')],
    364:[('R_MIPS_26','func_1503F5B8')]}
TRANSFER={1:0xAFB00024,2:0x00808025,4:0xAFB10028,13:0x8FB10058,
    16:0xAE220000,20:0x8E240000,21:0x8E2E0000,25:0x8E2F0000,26:0x02002025,
    32:0x8E390000,39:0x8E2B0000,43:0x8E2D0000,47:0x8E2E0000,
    53:0x8E380000,62:0x8E280000,64:0x8E300000,65:0x8E0403E8,
    68:0x8E0903EC,74:0x8E0403EC,77:0x8E300000,78:0x8E0403EC,
    83:0x8E300000,85:0x02002025,89:0x02002025}


def recipe(words):
    if tuple(words)!=RAW:raise ValueError('stale complete alternate loader body')
    return [TRANSFER.get(i,w) for i,w in enumerate(words)]


def guard_rows(path):
    text,functions,relocations=parse_object(path);target=functions[FUNCTION];start=target['value']
    if target['size'] not in (396,400) or any(text[start+396:start+target['size']]):
        raise ValueError('unexpected alternate loader extent')
    relative={o-start:v for o,v in relocations.items() if start<=o<start+target['size']}
    if relative!=RELOCATIONS:raise ValueError('stale alternate loader relocations')
    words=struct.unpack_from('>99I',text,start);rows=[]
    for i,(old,new) in enumerate(zip(words,recipe(words))):
        if old==new:continue
        if i*4 in relative:raise ValueError('alternate transfer crossed a relocation')
        rows.append(dict(filename='generated_6C960',function=FUNCTION,offset='0x%X'%(i*4),
            expected='0x%08X'%old,replacement='0x%08X'%new,expected_relocations='-',replacement_relocations='-',
            note='Normalize checked alternate loader closed S0/S1 register transfer',
            insert_after='',insert_after_relocations='',omit='false'))
    assert len(rows)==24
    return rows


compile_candidate=recovery.compile_candidate
install=recovery.install


def append_guards(path,before,obj):
    if path.read_bytes()!=before or not before.endswith(b'\n'):raise ValueError('stale alternate loader guard manifest')
    reader=csv.DictReader(io.StringIO(before.decode('ascii')));rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):raise ValueError('alternate loader guards already published')
    output=io.StringIO(newline='')
    csv.DictWriter(output,fieldnames=reader.fieldnames,lineterminator='\n').writerows(guard_rows(obj))
    path.write_bytes(before+output.getvalue().encode('ascii'))
