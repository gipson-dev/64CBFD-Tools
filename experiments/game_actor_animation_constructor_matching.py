"""Closed constructor register cycles and independent integer expression scheduling."""
import csv
import io
import struct
from tools.experiments import game_actor_animation_constructor_candidates as recovery
from tools.experiments.game_actor_segment_selector_matching import fields
from tools.pad_generated_object import parse_object

ENTRY,ROM,WORDS=recovery.ENTRY,recovery.ROM,recovery.WORDS
FUNCTION,SOURCE,SELECTED=recovery.FUNCTION,recovery.SOURCE,recovery.SELECTED
RAW=tuple(int(word,16) for word in '''27BDFF98 F7B40040 AFB60060 AFB40058 AFB20050 4486A000 00809025 00A0A025 00E0B025 AFBF0064 AFB5005C AFB30054 AFB1004C AFB00048 2694FFFF 3C0F0000 25EF0000 001470C0 01CFA821 92B80004 00001825 8EA60000 1B000036 00008825 00C08025 24130002 92020003 260E0008 14400011 00000000 92190002 92050001 92060000 AFB90010 92080004 02402025 00003825 AFA80014 92090005 AFA90018 920A0006 E7B40020 0C000000 AFAA001C 1000001A 00401825 16620003 26830001 10000002 92020006 2402FFFF 920B0004 92050000 92060001 92070007 AFAB0010 920C0005 AFA3001C AFB60018 AFAC0014 920D0002 AFA20028 AFAE0024 AFAD0020 920F000E 02402025 AFAF002C 9218000F 0C000000 AFB80030 00401825 92B90004 26310001 26100010 0239082A 5420FFCF 92020003 00601025 8FBF0064 D7B40040 8FB00048 8FB1004C 8FB20050 8FB30054 8FB40058 8FB5005C 8FB60060 03E00008 27BD0068'''.split())
RELOCATIONS={60:[('R_MIPS_HI16','D_80086CC4')],64:[('R_MIPS_LO16','D_80086CC4')],
    168:[('R_MIPS_26','func_15083AC8')],272:[('R_MIPS_26','func_15030AF4')]}


def recipe(words):
    if tuple(words)!=RAW:raise ValueError('stale complete actor animation constructor')
    output=list(words)
    output[21]=fields(words[21],rt=2)
    output[24]=fields(words[24],rs=2)
    for index in (34,37,38,39,40,43,51,55,56,59,60,63):
        output[index]=fields(words[index],rt=(words[index]>>16&31)+1)
    # Animation ID and payload address are independent, non-faulting expressions.
    # Move their emitted computations between the loop head and type-test delay.
    output[27]=words[47]
    output[47]=fields(words[27],rt=8)
    output[62]=fields(words[62],rt=8)
    return output


def guard_rows(path):
    text,functions,relocations=parse_object(path);target=functions[FUNCTION];start=target['value']
    if target['size'] not in (356,360) or any(text[start+356:start+target['size']]):
        raise ValueError('unexpected actor animation constructor extent')
    words=struct.unpack_from('>89I',text,start)
    relative={offset-start:uses for offset,uses in relocations.items() if start<=offset<start+target['size']}
    if relative!=RELOCATIONS:raise ValueError('stale actor animation constructor relocations')
    rows=[]
    for index,(word,fitted) in enumerate(zip(words,recipe(words))):
        if word==fitted:continue
        uses=relative.get(index*4,[]);names=';'.join(kind+':'+symbol for kind,symbol in uses) or '-'
        rows.append(dict(filename='generated_AEB40',function=FUNCTION,offset='0x%X'%(index*4),
            expected='0x%08X'%word,replacement='0x%08X'%fitted,
            expected_relocations=names,replacement_relocations=names,
            note='Normalize closed actor animation constructor register cycles and independent expression schedule',
            insert_after='',insert_after_relocations='',omit='false'))
    assert len(rows)==17
    return rows


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    return recovery.compile_candidate(root,out,name,body,profile)


def install(before):return recovery.install(before)


def append_guards(path,before,obj):
    if path.read_bytes()!=before or not before.endswith(b'\n'):
        raise ValueError('stale constructor guard manifest')
    reader=csv.DictReader(io.StringIO(before.decode('ascii')));existing=list(reader)
    if any(row['function']==FUNCTION for row in existing):
        raise ValueError('constructor guards already published')
    rows=guard_rows(obj);output=io.StringIO(newline='')
    writer=csv.DictWriter(output,fieldnames=reader.fieldnames,lineterminator='\n');writer.writerows(rows)
    # Keep the mixed-newline historical prefix byte-for-byte; only rows are generated.
    path.write_bytes(before+output.getvalue().encode('ascii'))
