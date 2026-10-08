"""Recover the complete timer, callback, live player state and final free flow."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151D8A24, 0x205ED4, 64
FUNCTION = 'func_151D8A24'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_205C90/func_151D8A24.s")'
DECLARATIONS = '''extern s32 D_800BE9E4;
extern void (*D_8008FCC0[])(u8 *);
void func_1516972C(u8 *);
'''
SYMBOLS = {'D_800BE9E4':0x800BE9E4,'D_8008FCC0':0x8008FCC0,
    'func_1501C17C':0x1501C17C,'func_1501C010':0x1501C010,'func_1516972C':0x1516972C}
SELECTED = '''void func_151D8A24(u8 *record) {
    u8 player;
    u8 expired = 0;

    if (record[0xE] & 1) {
        *(s16 *)(record + 0x10) = (s16)((u32)(s32)*(s16 *)(record + 0x10) - (u32)D_800BE9E4);
        if (*(s16 *)(record + 0x10) < 0) {
            expired = 1;
        }
    }
    if (*(s8 *)(record + 0x14) != -1) {
        D_8008FCC0[*(s8 *)(record + 0x14)](record);
    }
    if (record[0x12] != record[0x16]) {
        for (player = 0; player < 4; player++) {
            if (record[0x13] & (1U << player)) {
                func_1501C17C(player);
                func_1501C010(player, record[0x12]);
            }
        }
        record[0x16] = record[0x12];
    }
    if (expired) {
        func_1516972C(record);
    }
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'initialized-player', SELECTED.replace('u8 player;', 'u8 player = 0;')
    yield 'initialized-player-loop', SELECTED.replace('u8 player;', 'u8 player = 0;').replace('for (player = 0;', 'for (;')
    yield 'two-byte-initializers', SELECTED.replace('    u8 player;\n    u8 expired = 0;', '    u8 expired = 0, player = 0;')
    yield 'expiry-expression', SELECTED.replace('            expired = 1;', '            expired++;')
    yield 'register-player', SELECTED.replace('u8 player;', 'register u8 player;')
    yield 'register-expiry', SELECTED.replace('u8 expired = 0;', 'register u8 expired = 0;')
    yield 'volatile-expiry', SELECTED.replace('u8 expired = 0;', 'volatile u8 expired = 0;')
    yield 'block-player', SELECTED.replace('    u8 player;\n', '').replace('        for (player', '        u8 player;\n        for (player')
    yield 'block-register-player', SELECTED.replace('    u8 player;\n', '').replace('        for (player', '        register u8 player;\n        for (player')
    yield 'expiry-first', SELECTED.replace('    u8 player;\n    u8 expired = 0;', '    u8 expired = 0;\n    u8 player;')
    yield 'assignment-init', SELECTED.replace('    u8 expired = 0;', '    u8 expired;').replace('    if (record[0xE]', '    expired = 0;\n    if (record[0xE]', 1)
    yield 'int-expiry', SELECTED.replace('u8 expired', 's32 expired')
    yield 'int-player', SELECTED.replace('u8 player', 's32 player')
    yield 'signed-player', SELECTED.replace('u8 player', 's8 player')
    yield 'natural-subtract', SELECTED.replace('*(s16 *)(record + 0x10) = (s16)((u32)(s32)*(s16 *)(record + 0x10) - (u32)D_800BE9E4);', '*(s16 *)(record + 0x10) -= D_800BE9E4;')
    yield 'expiry-last', SELECTED.replace('    u8 expired = 0;\n', '').replace('    u8 player;', '    u8 player;\n    u8 expired;').replace('    if (record[0xE]', '    expired = 0;\n    if (record[0xE]', 1)
    yield 'old-style', SELECTED.replace('void func_151D8A24(u8 *record)', 'void func_151D8A24(record)\nu8 *record;')

    yield 'negative-bit-two', SELECTED.replace('record[0xE] & 1', 'record[0xE] & 2')
    yield 'negative-untruncated-expiry', SELECTED.replace('if (*(s16 *)(record + 0x10) < 0)', 'if ((s32)*(s16 *)(record + 0x10) - D_800BE9E4 < 0)')
    yield 'negative-unsigned-selector', SELECTED.replace('*(s8 *)(record + 0x14)', 'record[0x14]').replace('!= -1', '!= 255')
    yield 'negative-skip-zero', SELECTED.replace('!= -1', '!= 0')
    yield 'negative-cached-mask', SELECTED.replace('    u8 player;', '    u8 player;\n    u8 mask;').replace('        for (player', '        mask = record[0x13];\n        for (player').replace('record[0x13] &', 'mask &')
    yield 'negative-cached-level', SELECTED.replace('    u8 player;', '    u8 player;\n    u8 level;').replace('        for (player', '        level = record[0x12];\n        for (player').replace('func_1501C010(player, record[0x12])', 'func_1501C010(player, level)').replace('record[0x16] = record[0x12]', 'record[0x16] = level')
    yield 'negative-register-before-clear', SELECTED.replace('func_1501C17C(player);\n                func_1501C010(player, record[0x12]);', 'func_1501C010(player, record[0x12]);\n                func_1501C17C(player);')
    yield 'negative-early-free', SELECTED.replace('    if (expired) {\n        func_1516972C(record);\n    }\n', '').replace('    if (*(s8 *)', '    if (expired) {\n        func_1516972C(record);\n    }\n    if (*(s8 *)', 1)
    yield 'negative-pre-callback-level', SELECTED.replace('    u8 player;', '    u8 player;\n    u8 oldLevel;').replace('    if (*(s8 *)', '    oldLevel = record[0x12];\n    if (*(s8 *)', 1).replace('if (record[0x12] != record[0x16])', 'if (oldLevel != record[0x16])')


def owner_guards():
    return [dict(filename='generated_205C90',function=FUNCTION,offset='0x%X'%offset,
        expected='0x%08X'%before,replacement='0x%08X'%after,
        expected_relocations='-',replacement_relocations='-',
        note='Normalize complete private expiry-byte stack-slot allocation',
        insert_after='',insert_after_relocations='',omit='false')
        for offset,before,after in ((0x14,0xA3A00026,0xA3A00023),(0x4C,0xA3AA0026,0xA3AA0023),
                                   (0x8C,0x93AA0026,0x93AA0023),(0xD8,0x93AA0026,0x93AA0023))]


def normalize(words):
    result=list(words)
    assert len(result)==64 and result[0]==0x27BDFFD8
    for row in owner_guards():
        index=int(row['offset'],0)//4
        assert result[index]==int(row['expected'],0),('stale expiry-byte slot',index)
        result[index]=int(row['replacement'],0)
    return result


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    out.mkdir(exist_ok=True)
    source,obj,elf=(out/(name+suffix) for suffix in ('.c','.o','.elf'))
    source.write_text('#include <ultra64.h>\nvoid func_1501C17C(u8);\nvoid func_1501C010(u8,u8);\n'+DECLARATIONS+'\n'+body+'\n')
    result=subprocess.run(['ido/ido5.3_recomp/cc','-c','-32','-G','0','-Xfullwarn','-Xcpluscomm',
        '-signed','-nostdinc','-non_shared','-Wab,-r4300_mul','-mips2','-o32',
        '-I','conker/include','-I','conker/include/2.0L','-I','conker/include/2.0L/PR',
        '-I','conker/include/libc',
        '-D_LANGUAGE_C','-D_FINALROM','-DF3DEX_GBI_2','-D_MIPS_SZLONG=32',*PROFILES[profile],
        '-o',str(obj.relative_to(root)),str(source.relative_to(root))],cwd=root,capture_output=True,text=True)
    if result.returncode or result.stdout or result.stderr:
        raise ValueError(result.stdout+result.stderr)
    script=out/'record-state-update.ld'
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%ENTRY)
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',FUNCTION,
        *['--defsym=%s=0x%X'%item for item in SYMBOLS.items()],
        '-o',str(elf),str(obj)],check=True,capture_output=True)
    _,functions,relocations=parse_object(obj)
    meta,pools=functions[FUNCTION],sections(elf)
    words=list(struct.unpack_from('>%dI'%(meta['size']//4),pools['.text'][1],meta['value']))
    end=max(i for i,word in enumerate(words) if word==0x03E00008)+2
    assert not any(words[end:])
    words=words[:end]
    retail=struct.unpack_from('>%dI'%WORDS,(root/'conker/conker.us.bin').read_bytes(),ROM)
    frames=[(-word)&65535 for word in words if word&0xFFFF0000==0x27BD0000 and word&0x8000]
    return dict(name=name,profile=profile,body_words=end,frame=frames[0] if frames else 0,
        differences=sum(a!=b for a,b in itertools.zip_longest(words,retail,fillvalue=0)),diagnostics='',
        relocations=relocations,pool_bytes=sum(len(v[1]) for n,v in pools.items() if n in ('.rodata','.data'))),words


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--profiles',action='store_true')
    mode.add_argument('--candidate',choices=[name for name,_ in candidates()])
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-record-state-update'
    forms=[('profile-'+p,SELECTED,p) for p in PROFILES] if args.profiles else [
        (name,body,'o2g3') for name,body in candidates() if args.candidate is None or name==args.candidate]
    records=[]
    for name,body,profile in forms:
        record,_=compile_candidate(root,out,name,body,profile)
        records.append(record)
        print(name,record['body_words'],hex(record['frame']),record['differences'],flush=True)
    filename='profiles.json' if args.profiles else args.candidate+'-measurement.json' if args.candidate else 'measurements.json'
    (out/filename).write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
