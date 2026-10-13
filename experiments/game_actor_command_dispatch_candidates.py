"""Recover the complete actor command writer/finalizer dispatcher."""
import argparse
import csv
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler
from tools.experiments.game_actor_type_dispatch_candidates import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object

ENTRY,ROM,WORDS=0x15033FE0,0x61490,119
FUNCTION,SOURCE='func_15033FE0','conker/src/game/generated_61490.c'
TABLE,TABLE_ROM=0x80097C80,0x23C740
SYMBOLS=dict(D_800CC2D0=0x800CC2D0,func_150341BC=0x150341BC,func_150D8590=0x150D8590,
    func_150344A0=0x150344A0,func_150B58F0=0x150B58F0,func_150F1B48=0x150F1B48,
    func_15034420=0x15034420,func_150BE438=0x150BE438,func_15034340=0x15034340,
    func_150343B0=0x150343B0,func_1503DA3C=0x1503DA3C,func_15034860=0x15034860)
OWNER_DECLARATIONS='''u8 *func_150341BC(u8 *, s32);
u8 *func_150D8590(u16 *, s32);
u8 *func_150344A0(u8 *, s32);
u8 *func_150B58F0(u8 *, s32);
s32 func_150F1B48(u8 *, s32);
u8 *func_15034420(u8 *, s32);
u8 *func_150BE438(u8 *, s32);
u8 *func_15034340(u8 *, s32);
u8 *func_150343B0(u8 *, s32);
s32 func_1503DA3C(s32, u32);
s32 func_15034860(u8 *, u8 *, s32, s32);
'''
DECLARATIONS='extern u8 D_800CC2D0[];\n'+OWNER_DECLARATIONS
ORIGINAL='s32 func_15033FE0() {\n    return 0;\n}'
SELECTED='''void func_15033FE0(u8 *output, s32 slot) {
    u8 *actor = D_800CC2D0 + (u32)slot * 0x32C;
    u8 *cursor = output;
    s32 first;
    s32 second;

    if (*(u32 *)(actor + 0x1D4) == 0) {
        *(s16 *)output = 0x1000;
        return;
    }
    if (*(s32 *)actor == 1) {
        cursor = func_150341BC(output, slot);
    } else {
        switch (actor[4]) {
            case 0x2B:
                cursor = func_150D8590((u16 *)output, slot);
                break;
            case 0x28:
            case 0x77:
                cursor = func_150344A0(output, slot);
                break;
            case 0x4B:
                cursor = func_150B58F0(output, slot);
                break;
            case 0x7B:
                cursor = (u8 *)func_150F1B48(output, slot);
                break;
            case 0x8A:
                cursor = func_15034420(output, slot);
                break;
            case 0x21:
                cursor = func_150BE438(output, slot);
                break;
            case 0x98:
                cursor = func_15034340(output, slot);
                break;
            case 0x5A:
            case 0x74:
            case 0x7A:
            case 0x8D:
                cursor = func_150343B0(output, slot);
                break;
        }
    }
    first = func_1503DA3C(actor[4], 0);
    second = func_1503DA3C(actor[4], 1);
    cursor = (u8 *)func_15034860(cursor, actor, first, second);
    *(s16 *)cursor = 0x1000;
}'''


BASE=SELECTED


def recovered_owner(source,body=None):
    body=SELECTED if body is None else body
    if source.count(ORIGINAL)==1:
        source=source.replace(ORIGINAL,body)
    elif source.count(body)!=1:
        raise ValueError('Expected known dispatcher placeholder or complete body')
    if OWNER_DECLARATIONS not in source:
        source=source.replace('extern u8 D_800CC2D0[];','extern u8 D_800CC2D0[];\n'+OWNER_DECLARATIONS.rstrip(),1)
    return source


def neighbor_table_guard(obj):
    text,functions,relocations=parse_object(obj)
    name='func_1503453C'
    meta=functions[name]
    offsets=[o for o,r in relocations.items() if meta['value']<=o<meta['value']+meta['size']
             and r==[('R_MIPS_LO16','.rodata')]]
    assert len(offsets)==1
    offset=offsets[0]
    word=struct.unpack_from('>I',text,offset)[0]
    assert word&65535==148
    return dict(filename='generated_61490',function=name,offset='0x%X'%(offset-meta['value']),
        expected='0x%08X'%word,replacement='0x%08X'%((word&~65535)|160),
        expected_relocations='R_MIPS_LO16:.rodata',replacement_relocations='R_MIPS_LO16:.rodata',
        note='Translate existing actor type table over original float and alignment gap',
        insert_after='',insert_after_relocations='',omit='false')


def guard_bytes(before,obj):
    reader=csv.DictReader(io.StringIO(before.decode()))
    row=neighbor_table_guard(obj)
    if any(r['function']==row['function'] and int(r['offset'],0)==int(row['offset'],0) for r in reader):
        raise ValueError('Neighbor table translation already installed')
    tail=io.StringIO()
    writer=csv.DictWriter(tail,fieldnames=reader.fieldnames,lineterminator='\n')
    writer.writerow(row)
    return before+tail.getvalue().encode()


def compile_candidate(root,out,name,body=None):
    body=SELECTED if body is None else body
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS):
        record,_=compiler.compile_candidate(root,out,name,body)
    ld=out/(name+'.ld')
    ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x%X : SUBALIGN(4) { *(.rodata) } }\n'%(ENTRY,TABLE))
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',FUNCTION,
        *['--defsym=%s=0x%X'%x for x in SYMBOLS.items()],'-o',str(out/(name+'.elf')),str(out/(name+'.o'))],check=True,capture_output=True)
    pool=sections(out/(name+'.elf'))
    words=list(struct.unpack_from('>%dI'%record['body_words'],pool['.text'][1]))
    retail=struct.unpack_from('>%dI'%WORDS,(root/'conker/conker.us.bin').read_bytes(),ROM)
    record['differences']=sum(a!=b for a,b in itertools.zip_longest(words,retail,fillvalue=0))
    data=pool.get('.rodata',(TABLE,b''))[1]
    record['pool_bytes']=len(data)
    return record,words,data


def source_screens(SELECTED):
    yield 'selected',SELECTED
    yield 'cursor-first',SELECTED.replace('    u8 *actor = D_800CC2D0 + (u32)slot * 0x32C;\n    u8 *cursor = output;',
        '    u8 *cursor = output;\n    u8 *actor = D_800CC2D0 + (u32)slot * 0x32C;')
    yield 'inline-second',SELECTED.replace('    s32 second;\n','').replace('    second = func_1503DA3C(actor[4], 1);\n','').replace(
        'cursor, actor, first, second','cursor, actor, first, func_1503DA3C(actor[4], 1)')
    yield 'signed-type-local',SELECTED.replace('    s32 first;','    s32 type;\n    s32 first;').replace(
        '        switch (actor[4]) {','        type = actor[4];\n        switch (type) {')
    yield 'signed-slot-arithmetic',SELECTED.replace('(u32)slot *','slot *')
    typed=SELECTED.replace('    s32 first;','    s32 type;\n    s32 first;').replace(
        '        switch (actor[4]) {','        type = actor[4];\n        switch (type) {')
    for name,before in (('first-home-second','    u8 *cursor = output;'),
            ('first-home-first','    u8 *actor ='),('first-home-third','    s32 type;')):
        body=typed.replace('    s32 first;\n','')
        yield name,body.replace(before,'    s32 first;\n'+before,1)
    cursor_parameter=typed.replace('u8 *output, s32 slot','u8 *cursor, s32 slot').replace(
        '    u8 *cursor = output;\n','').replace('output','cursor')
    yield 'cursor-parameter',cursor_parameter
    yield 'cursor-parameter-inline-second',cursor_parameter.replace('    s32 second;\n','').replace(
        '    second = func_1503DA3C(actor[4], 1);\n','').replace(
        'cursor, actor, first, second','cursor, actor, first, func_1503DA3C(actor[4], 1)')
    inline_actor=typed.replace('    u8 *actor = D_800CC2D0 + (u32)slot * 0x32C;\n','').replace(
        'actor','(D_800CC2D0 + (u32)slot * 0x32C)')
    yield 'inline-actor',inline_actor
    yield 'inline-actor-cursor-parameter',inline_actor.replace('u8 *output, s32 slot','u8 *cursor, s32 slot').replace(
        '    u8 *cursor = output;\n','').replace('output','cursor')


def candidates():
    yield from source_screens(BASE)


SELECTED=dict(candidates())['first-home-second']


def trace_frame(root,out,name,body):
    from tools.experiments import game_actor_callback_frame_trace as observer
    def adapter(root,work,name,source):
        metadata,words,_=compile_candidate(root,work,name,source)
        return metadata,words
    with patch.object(observer,'screen',SimpleNamespace(compile_candidate=adapter)):
        return observer.trace(root,out,name,body)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screens',action='store_true')
    parser.add_argument('--trace',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-actor-command-dispatch'
    out.mkdir(exist_ok=True)
    if args.trace:
        body=dict(candidates())['signed-type-local']
        record=trace_frame(root,root/'conker/build/game-actor-command-dispatch-frame','signed-type',body)
        matched=trace_frame(root,root/'conker/build/game-actor-command-dispatch-frame','matched',SELECTED)
        for name,entry in (('old',record),('matched',matched)):
            print(json.dumps(dict(name=name,baseline=entry['baseline'],events=entry['events'],
                input_sizes=[r['bytes'] for r in entry['inputs']],code_unchanged=entry['code_unchanged'],
                optimizer_M_defs=[r['length'] for r in entry['records']['optimizer'] if r['name']=='def' and r['storage']=='M']),indent=2))
        return
    rows=[]
    for name,body in candidates() if args.screens else [('selected',SELECTED)]:
        row,_,pool=compile_candidate(root,out,name,body)
        rows.append(row)
        print(name,row['body_words'],hex(row['frame']),row['differences'],len(pool),flush=True)
    (out/'measurements.json').write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':
    main()
