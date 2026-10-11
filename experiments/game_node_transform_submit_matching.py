"""Complete transform submit; private terminator placement and closed base transfer."""
import csv
import io
import struct
from tools.experiments import game_node_transform_submit_candidates as recovery
from tools.pad_generated_object import parse_object

ENTRY,ROM,WORDS=recovery.ENTRY,recovery.ROM,recovery.WORDS
FUNCTION,SOURCE,SELECTED=recovery.FUNCTION,recovery.SOURCE,recovery.SELECTED
RAW=tuple(int(v,16) for v in '''27BDFFB8 AFB00028 00808025 AFBF002C 3C0E0000 91CE0000 AFA00044 24040320 000E7880 020FC021 8F1903E0 24050001 24060002 13200024 00000000 0C000000 24070002 AFA20044 02002025 00002825 0C000000 00403025 3C090000 91290000 24081000 A7A8003E 00095080 020A1821 8C6B03E8 8C6503E0 27AD003E AFAB0038 920C03F4 8E0703F0 AFA0001C AFA00018 AFAD0014 27A40038 02003025 0C000000 AFAC0010 3C0E0000 91CE0000 920503F4 000E7880 020FC021 0C000000 8F0403E8 24190001 A21903F6 3C050000 8CA50000 02002025 00003025 0C000000 00003825 8FA80044 51000004 8FBF002C 0C000000 01002025 8FBF002C 8FB00028 27BD0048 03E00008 00000000'''.split())
RELOCATIONS={16:[('R_MIPS_HI16','D_800BE9C0')],20:[('R_MIPS_LO16','D_800BE9C0')],
    60:[('R_MIPS_26','allocate_memory')],80:[('R_MIPS_26','func_1502D824')],
    88:[('R_MIPS_HI16','D_800BE9C0')],92:[('R_MIPS_LO16','D_800BE9C0')],
    156:[('R_MIPS_26','func_150A81D0')],164:[('R_MIPS_HI16','D_800BE9C0')],
    168:[('R_MIPS_LO16','D_800BE9C0')],184:[('R_MIPS_26','func_150A9984')],
    200:[('R_MIPS_HI16','D_800BE9A4')],204:[('R_MIPS_LO16','D_800BE9A4')],
    216:[('R_MIPS_26','func_1507BDB0')],236:[('R_MIPS_26','func_10004074')]}
TRANSFER={25:0xA7A80040,27:0x020A1021,28:0x8C4B03E8,29:0x8C4503E0,30:0x27AD0040}


def recipe(words):
    if tuple(words)!=RAW:raise ValueError('stale complete transform submit body')
    return [TRANSFER.get(i,w) for i,w in enumerate(words)]


def guard_rows(path):
    text,functions,relocations=parse_object(path);target=functions[FUNCTION];start=target['value']
    if target['size'] not in (264,268) or any(text[start+264:start+target['size']]):
        raise ValueError('unexpected transform submit extent')
    relative={o-start:v for o,v in relocations.items() if start<=o<start+target['size']}
    if relative!=RELOCATIONS:raise ValueError('stale transform submit relocations')
    words=struct.unpack_from('>66I',text,start);rows=[]
    for i,(old,new) in enumerate(zip(words,recipe(words))):
        if old==new:continue
        if i*4 in relative:raise ValueError('terminator placement crossed a relocation')
        rows.append(dict(filename='generated_6C960',function=FUNCTION,offset='0x%X'%(i*4),
            expected='0x%08X'%old,replacement='0x%08X'%new,expected_relocations='-',replacement_relocations='-',
            note='Normalize checked node transform terminator placement and closed base transfer',
            insert_after='',insert_after_relocations='',omit='false'))
    assert len(rows)==5
    return rows


compile_candidate=recovery.compile_candidate
install=recovery.install


def append_guards(path,before,obj):
    if path.read_bytes()!=before or not before.endswith(b'\n'):raise ValueError('stale transform submit guard manifest')
    reader=csv.DictReader(io.StringIO(before.decode('ascii')));rows=list(reader)
    if any(row['function']==FUNCTION for row in rows):raise ValueError('transform submit guards already published')
    output=io.StringIO(newline='')
    csv.DictWriter(output,fieldnames=reader.fieldnames,lineterminator='\n').writerows(guard_rows(obj))
    path.write_bytes(before+output.getvalue().encode('ascii'))
