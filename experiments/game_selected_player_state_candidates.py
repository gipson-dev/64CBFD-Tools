"""Recover the ordered selected-player mapping/state predicate."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151D87E0, 0x205C90, 34
FUNCTION = 'func_151D87E0'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_205C90/func_151D87E0.s")'
DECLARATIONS = 'extern u8 D_80084060[];\nextern u8 D_800BE944[];\n'
SYMBOLS = {'D_80084060':0x80084060,'D_800BE944':0x800BE944}
SELECTED = '''s32 func_151D87E0(u8 mask) {
    u8 player;
    u8 index;
    for (player = 0; player < 4; player++) {
        if (mask & (1 << player)) {
            index = D_80084060[player];
            if (index >= 4) {
                return 0;
            }
            if (D_800BE944[index] != 0) {
                return 1;
            }
        }
    }
    return 0;
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'old-style-byte', SELECTED.replace('s32 func_151D87E0(u8 mask) {', 's32 func_151D87E0(mask)\nu8 mask;\n{')
    yield 'int-player', SELECTED.replace('u8 player;', 's32 player;')
    yield 'int-index', SELECTED.replace('u8 index;', 's32 index;')
    yield 'wide-mask-argument', SELECTED.replace('u8 mask', 'u32 mask')
    yield 'explicit-byte-step', SELECTED.replace('player++', 'player = (u8)(player + 1)')
    yield 'negative-invalid-continue', SELECTED.replace('if (index >= 4) {\n                return 0;', 'if (index >= 4) {\n                continue;')
    yield 'negative-threshold-five', SELECTED.replace('index >= 4', 'index >= 5')
    yield 'negative-narrow-index', SELECTED.replace('index = D_80084060[player];', 'index = D_80084060[player] & 3;')
    yield 'negative-reversed-bits', SELECTED.replace('1 << player', '1 << (3 - player)')
    yield 'negative-flag-one-only', SELECTED.replace('D_800BE944[index] != 0', 'D_800BE944[index] == 1')
    yield 'negative-shifted-flag', SELECTED.replace('D_800BE944[index]', 'D_800BE944[index + 1]')
    yield 'negative-return-two', SELECTED.replace('return 1;', 'return 2;')


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    out.mkdir(exist_ok=True)
    source,obj,elf=(out/(name+suffix) for suffix in ('.c','.o','.elf'))
    source.write_text('#include <ultra64.h>\n'+DECLARATIONS+'\n'+body+'\n')
    result=subprocess.run(['ido/ido5.3_recomp/cc','-c','-32','-G','0','-Xfullwarn','-Xcpluscomm',
        '-signed','-nostdinc','-non_shared','-Wab,-r4300_mul','-mips2','-o32',
        '-I','conker/include','-I','conker/include/2.0L','-I','conker/include/2.0L/PR',
        '-D_LANGUAGE_C','-D_FINALROM','-DF3DEX_GBI_2','-D_MIPS_SZLONG=32',*PROFILES[profile],
        '-o',str(obj.relative_to(root)),str(source.relative_to(root))],cwd=root,capture_output=True,text=True)
    if result.returncode or result.stdout or result.stderr:
        raise ValueError(result.stdout+result.stderr)
    script=out/'selected-player-state.ld'
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
    parser.add_argument('--profiles',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-selected-player-state'
    forms=[('profile-'+p,SELECTED,p) for p in PROFILES] if args.profiles else [
        (name,body,'o2g3') for name,body in candidates()]
    records=[]
    for name,body,profile in forms:
        record,_=compile_candidate(root,out,name,body,profile)
        records.append(record)
        print(name,record['body_words'],hex(record['frame']),record['differences'],flush=True)
    (out/('profiles.json' if args.profiles else 'measurements.json')).write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':
    main()
