"""Recover the complete record allocator and player-registration flow."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151D8868, 0x205D18, 111
FUNCTION = 'func_151D8868'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_205C90/func_151D8868.s")'
DECLARATIONS = "#include <string.h>\nextern u8 D_800E0B94;\nextern u8 D_800BEAC0, D_800BEAC1, D_800BEAC2, D_800BEAC3;\nextern s32 D_80082FA0;\ns32 func_151D87E0(u8 mask);\ns32 func_15181CC8(s32 player);\ns32 func_1517EF00(s32 player);\nvoid *func_15167A68(s32 kind, s32 context, s32 bytes, s32 flag, u8 slot, u8 pool);\nvoid func_1501C010(u8 player, u8 level);\n"
SYMBOLS = {"D_800E0B94":2148404116,"D_800BEAC0":2148264640,"D_800BEAC1":2148264641,"D_800BEAC2":2148264642,"D_800BEAC3":2148264643,"D_80082FA0":2148020128,"func_151D87E0":354256864,"func_15181CC8":353901768,"func_1517EF00":353890048,"func_15167A68":353794664,"func_1501C010":352436240,"memcpy":268578496}
SELECTED = '''u8 *func_151D8868(u8 *owner, s32 payloadBytes, u8 slot, s32 context) {
    u8 validationPlayer;
    u8 player;
    u8 *record;

    if (D_800E0B94 != 0) {
        return NULL;
    }
    if (func_151D87E0(owner[5]) == 0) {
        return NULL;
    }
    if (D_800BEAC0 || D_800BEAC1 || D_800BEAC2 || D_800BEAC3) {
        return NULL;
    }
    for (validationPlayer = 0; validationPlayer <= D_80082FA0; validationPlayer++) {
        if (owner[5] & (1U << validationPlayer)) {
            if (func_15181CC8(validationPlayer) == 0 || func_1517EF00(validationPlayer) != 0) {
                return NULL;
            }
        }
    }
    record = func_15167A68(0x3F, context, payloadBytes + 0x18, 1, slot, 1);
    if (record == NULL) {
        return NULL;
    }
    memcpy(record + 0xE, owner, 8);
    for (player = 0; player < 4; player++) {
        if (record[0x13] & (1U << player)) {
            func_1501C010(player, owner[4]);
        }
    }
    record[0x16] = owner[4];
    return record;
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'defined-byte-shifts', SELECTED.replace('1U << validationPlayer', '1U << (validationPlayer & 31)')
    shared = SELECTED.replace('    u8 validationPlayer;\n', '').replace('validationPlayer', 'player')
    yield 'shared-counter', shared
    distinct = SELECTED
    yield 'distinct-counters', distinct
    yield 'distinct-unsigned-shifts', distinct.replace('1 <<', '1U <<')
    yield 'distinct-wide-slot', distinct.replace('u8 slot', 's32 slot')
    yield 'distinct-explicit-gates', distinct.replace('D_800BEAC0 || D_800BEAC1 || D_800BEAC2 || D_800BEAC3',
        'D_800BEAC0 != 0 || D_800BEAC1 != 0 || D_800BEAC2 != 0 || D_800BEAC3 != 0')
    yield 'distinct-separate-gates', distinct.replace(
        '    if (D_800BEAC0 || D_800BEAC1 || D_800BEAC2 || D_800BEAC3) {\n        return NULL;\n    }',
        '\n'.join('    if (D_800BEAC%d) {\n        return NULL;\n    }' % i for i in range(4)))
    yield 'distinct-volatile-limit', distinct.replace('validationPlayer <= D_80082FA0',
        'validationPlayer <= *(volatile s32 *)&D_80082FA0')
    yield 'distinct-explicit-limit', distinct.replace('validationPlayer <= D_80082FA0',
        'D_80082FA0 >= validationPlayer')
    yield 'distinct-gate-or', distinct.replace(
        'D_800BEAC0 || D_800BEAC1 || D_800BEAC2 || D_800BEAC3',
        'D_800BEAC0 || D_800BEAC1 || D_800BEAC2 || (D_800BEAC3 != 0)')
    yield 'distinct-while', distinct.replace(
        'for (validationPlayer = 0; validationPlayer <= D_80082FA0; validationPlayer++) {',
        'validationPlayer = 0;\n    while (validationPlayer <= D_80082FA0) {').replace(
        '    record = func_15167A68', '    record = func_15167A68').replace(
        '        }\n    }\n    record =', '        }\n        validationPlayer++;\n    }\n    record =')
    gate = '    if (D_800BEAC0 || D_800BEAC1 || D_800BEAC2 || D_800BEAC3) {\n        return NULL;\n    }'
    before, after = distinct.split(gate)
    yield 'distinct-enclosed-positive', before + '    if (D_800BEAC0 == 0 && D_800BEAC1 == 0 && D_800BEAC2 == 0 && D_800BEAC3 == 0) {' + after[:-1] + '    }\n    return NULL;\n}'
    yield 'distinct-final-positive', before + '    if (D_800BEAC0 || D_800BEAC1 || D_800BEAC2) {\n        return NULL;\n    }\n    if (D_800BEAC3 == 0) {' + after[:-1] + '    }\n    return NULL;\n}'
    yield 'distinct-do-loop', distinct.replace(
        'for (validationPlayer = 0; validationPlayer <= D_80082FA0; validationPlayer++) {',
        'validationPlayer = 0;\n    if (D_80082FA0 >= 0) {\n        do {').replace(
        '        }\n    }\n    record =', '        }\n        validationPlayer++;\n        } while (validationPlayer <= D_80082FA0);\n    }\n    record =')
    pointer = distinct.replace('    u8 *record;', '    u8 *record;\n    s32 *limit;').replace(
        '    for (validationPlayer', '    limit = &D_80082FA0;\n    for (validationPlayer', 1).replace(
        'validationPlayer <= D_80082FA0', 'validationPlayer <= *limit')
    yield 'distinct-limit-pointer', pointer
    yield 'distinct-limit-pointer-first', pointer.replace('    limit = &D_80082FA0;\n', '').replace(
        '    if (D_800E0B94', '    limit = &D_80082FA0;\n    if (D_800E0B94', 1)
    yield 'distinct-positive-limit', distinct.replace(
        'for (validationPlayer = 0; validationPlayer <= D_80082FA0; validationPlayer++) {',
        'for (validationPlayer = 0; !(D_80082FA0 < validationPlayer); validationPlayer++) {')
    yield 'int-player', SELECTED.replace('u8 player;', 's32 player;')
    yield 'wide-slot', SELECTED.replace('u8 slot', 's32 slot')
    yield 'signed-shifts', SELECTED.replace('1U <<', '1 <<')
    yield 'explicit-byte-step', SELECTED.replace('player++', 'player = (u8)(player + 1)')
    yield 'separate-failures', SELECTED.replace(
        'if (func_15181CC8(validationPlayer) == 0 || func_1517EF00(validationPlayer) != 0) {\n                return NULL;\n            }',
        'if (func_15181CC8(validationPlayer) == 0) {\n                return NULL;\n            }\n            if (func_1517EF00(validationPlayer) != 0) {\n                return NULL;\n            }')

    yield 'negative-exclusive-limit', SELECTED.replace('validationPlayer <=', 'validationPlayer <')
    yield 'negative-owner-registration-mask', SELECTED.replace('record[0x13] &', 'owner[5] &')
    yield 'negative-cached-limit', SELECTED.replace('    u8 *record;', '    u8 *record;\n    s32 limit;').replace(
        '    for (validationPlayer', '    limit = D_80082FA0;\n    for (validationPlayer', 1).replace(
        'validationPlayer <= D_80082FA0', 'validationPlayer <= limit')
    yield 'negative-cached-owner-mask', SELECTED.replace('    u8 *record;', '    u8 *record;\n    u8 mask;').replace(
        '    for (validationPlayer', '    mask = owner[5];\n    for (validationPlayer', 1).replace(
        'if (owner[5] &', 'if (mask &')
    yield 'negative-cached-record-mask', SELECTED.replace('    u8 *record;', '    u8 *record;\n    u8 mask;').replace(
        '    for (player =', '    mask = record[0x13];\n    for (player =').replace(
        'if (record[0x13] &', 'if (mask &')
    yield 'negative-copy-seven', SELECTED.replace('owner, 8)', 'owner, 7)')
    yield 'negative-allocation-size', SELECTED.replace('payloadBytes + 0x18', 'payloadBytes + 0x1C')
    yield 'negative-shifted-result', SELECTED.replace('    return record;', '    return record + 1;')


def owner_guards():
    return [dict(filename='generated_205C90', function=FUNCTION, offset='0x%X' % offset,
        expected='0x%08X' % before, replacement='0x%08X' % after,
        expected_relocations='-', replacement_relocations='-',
        note='Normalize final zero-gate branch and equivalent conditional limit-load schedule',
        insert_after='', insert_after_relocations='', omit='false')
        for offset, before, after in ((0x94, 0x51000004, 0x11000003), (0x98, 0x8E490000, 0))]


def normalize(words):
    result = list(words)
    assert len(result) == WORDS and result[39] == 0x10000040 and result[41] == 0x8E490000
    for row in owner_guards():
        index = int(row['offset'], 0) // 4
        assert result[index] == int(row['expected'], 0), ('stale conditional schedule', index)
        result[index] = int(row['replacement'], 0)
    return result


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    out.mkdir(exist_ok=True)
    source,obj,elf=(out/(name+suffix) for suffix in ('.c','.o','.elf'))
    source.write_text('#include <ultra64.h>\n'+DECLARATIONS+'\n'+body+'\n')
    result=subprocess.run(['ido/ido5.3_recomp/cc','-c','-32','-G','0','-Xfullwarn','-Xcpluscomm',
        '-signed','-nostdinc','-non_shared','-Wab,-r4300_mul','-mips2','-o32',
        '-I','conker/include','-I','conker/include/2.0L','-I','conker/include/2.0L/PR',
        '-I','conker/include/libc',
        '-D_LANGUAGE_C','-D_FINALROM','-DF3DEX_GBI_2','-D_MIPS_SZLONG=32',*PROFILES[profile],
        '-o',str(obj.relative_to(root)),str(source.relative_to(root))],cwd=root,capture_output=True,text=True)
    if result.returncode or result.stdout or result.stderr:
        raise ValueError(result.stdout+result.stderr)
    script=out/'record-player-registration.ld'
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
    out=root/'conker/build/game-record-player-registration'
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
