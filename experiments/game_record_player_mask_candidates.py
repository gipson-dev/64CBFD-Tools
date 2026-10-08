"""Recover the four-player live-mask dispatcher and callback lifetime."""

import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x151D8B24, 0x205FD4, 25
FUNCTION = 'func_151D8B24'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_205C90/func_151D8B24.s")'
DECLARATIONS = 'void func_1501C17C(u8 player);\n'
SYMBOLS = {'func_1501C17C':0x1501C17C}
SELECTED = '''void func_151D8B24(u8 *owner) {
    u8 player;
    for (player = 0; player < 4; player++) {
        if (owner[0x13] & (1 << player)) {
            func_1501C17C(player);
        }
    }
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'int-counter', SELECTED.replace('u8 player;', 's32 player;')
    yield 'unsigned-int-counter', SELECTED.replace('u8 player;', 'u32 player;')
    yield 'explicit-byte-increment', SELECTED.replace('player++', 'player = (u8)(player + 1)')
    yield 'volatile-owner', SELECTED.replace('u8 *owner', 'u8 *volatile owner')
    yield 'explicit-nonzero', SELECTED.replace('owner[0x13] & (1 << player)', '(owner[0x13] & (1 << player)) != 0')
    yield 'negative-cached-mask', SELECTED.replace('    u8 player;', '    u8 player;\n    u8 mask = owner[0x13];').replace(
        'if (owner[0x13]', 'if (mask')
    yield 'negative-wrong-offset', SELECTED.replace('owner[0x13]', 'owner[0x12]')
    yield 'negative-reverse-bits', SELECTED.replace('1 << player', '1 << (3 - player)')
    yield 'negative-three-players', SELECTED.replace('player < 4', 'player < 3')
    yield 'negative-inverted-gate', SELECTED.replace('owner[0x13] & (1 << player)', '(owner[0x13] & (1 << player)) == 0')
    yield 'negative-first-hit-only', SELECTED.replace('func_1501C17C(player);', 'func_1501C17C(player);\n            break;')
    yield 'negative-shifted-argument', SELECTED.replace('func_1501C17C(player);', 'func_1501C17C((u8)(player + 1));')


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
    script=out/'record-player-mask.ld'
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
    out=root/'conker/build/game-record-player-mask'
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
