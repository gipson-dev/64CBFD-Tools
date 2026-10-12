"""Recover the extended-character metrics switch and original readonly pool."""
import argparse
import itertools
import json
import struct
import subprocess
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = 0x150415E0, 0x6EA90, 115
TABLE, TABLE_ROM = 0x80098AB0, 0x23D570
ANCHOR = 'jtbl_80098AB0_game'
FUNCTION, SOURCE = 'func_150415E0', 'conker/src/game/generated_6E770.c'
ORIGINAL = 's32 func_150415E0() {\n    return 0;\n}'
DECLARATIONS = '''extern f32 D_80098AFC;
extern f32 D_80098B00;
extern f32 D_80098B04;
extern f32 D_80098B08;
extern f32 D_80098B0C;
'''
SYMBOLS = dict(D_80098AFC=0x80098AFC,D_80098B00=0x80098B00,
    D_80098B04=0x80098B04,D_80098B08=0x80098B08,D_80098B0C=0x80098B0C)
PROFILES = dict(compiler.PROFILES, owner=('-O2','-g3','-Wo,-loopunroll,0'))
BASE = '''void func_150415E0(s32 code, s32 *width, s32 *height, f32 *scale,
    s32 *mode, f32 *factor) {
    if (code >= 0xA8 && code < 0x100) {
        *factor = 1.0f;
        switch (code) {
            case 0xA8:
            case 0xA9:
                *width = 32;
                *height = 18;
                *scale = D_80098AFC;
                *mode = 1;
                return;
            case 0xAA:
            case 0xAB:
            case 0xAC:
            case 0xAD:
                *width = 32;
                *height = 27;
                *scale = 2.0f;
                *mode = 1;
                *factor = D_80098B00;
                return;
            case 0xAE:
                *width = 16;
                *height = 17;
                *scale = D_80098B04;
                *mode = 1;
                return;
            case 0xAF:
            case 0xB0:
                *width = 46;
                *height = 16;
                *scale = 2.0f;
                *mode = 1;
                return;
            case 0xB6:
            case 0xB7:
            case 0xB8:
            case 0xB9:
                *width = 16;
                *height = 12;
                *scale = 2.0f;
                *mode = 0;
                return;
            case 0xBA:
                *mode = 0;
                *scale = D_80098B08;
                *width = 55;
                *height = 12;
                return;
            case 0xB1:
                *width = 38;
                *height = 24;
                *scale = 2.0f;
                *mode = 1;
                *factor = D_80098B0C;
                return;
            default:
                *width = 12;
                *height = 16;
                *scale = 2.0f;
                *mode = 0;
                return;
        }
    }
    *scale = 0.0f;
    *width = 0;
    *height = 0;
}'''
SELECTED = BASE
PROFILE_LINE = '$(BUILD_DIR)/$(SRC_DIR)/game/generated_6E770.c.o: OPT_FLAGS := -O2 -g3 -Wo,-loopunroll,0'
BINDING_LINE = '$(BUILD_DIR)/$(SRC_DIR)/game/generated_6E770.c.o: RETAIL_RODATA_SYMBOL := '+ANCHOR


def candidates():
    yield 'selected', SELECTED
    yield 'inverted-gate', BASE.replace('    if (code >= 0xA8 && code < 0x100) {',
        '    if (code < 0xA8 || code >= 0x100) {\n        *scale = 0.0f;\n        *width = 0;\n        *height = 0;\n        return;\n    }\n    {').replace(
        '    *scale = 0.0f;\n    *width = 0;\n    *height = 0;\n}', '}')
    yield 'break-cases', BASE.replace('                return;', '                break;').replace(
        '        }\n    }\n    *scale = 0.0f;', '        }\n        return;\n    }\n    *scale = 0.0f;')
    yield 'normalized-switch', BASE.replace('switch (code)', 'switch (code - 0xA8)').replace(
        'case 0xA8:', 'case 0:').replace('case 0xA9:', 'case 1:').replace('case 0xAA:', 'case 2:').replace(
        'case 0xAB:', 'case 3:').replace('case 0xAC:', 'case 4:').replace('case 0xAD:', 'case 5:').replace(
        'case 0xAE:', 'case 6:').replace('case 0xAF:', 'case 7:').replace('case 0xB0:', 'case 8:').replace(
        'case 0xB1:', 'case 9:').replace('case 0xB6:', 'case 14:').replace('case 0xB7:', 'case 15:').replace(
        'case 0xB8:', 'case 16:').replace('case 0xB9:', 'case 17:').replace('case 0xBA:', 'case 18:')


def compile_candidate(root,out,name,body=SELECTED,profile='owner',table=TABLE):
    with patch.multiple(compiler,ENTRY=ENTRY,ROM=ROM,WORDS=WORDS,FUNCTION=FUNCTION,
            RECORD='',DECLARATIONS=DECLARATIONS,SYMBOLS=SYMBOLS,PROFILES=PROFILES):
        meta,_ = compiler.compile_candidate(root,out,name,body,profile)
    script = out/(name+'-pool.ld'); elf = script.with_suffix('.elf')
    script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } '
        '.rodata 0x%X : SUBALIGN(4) { *(.rodata) } }\n'%(ENTRY,table))
    subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',FUNCTION,
        *['--defsym=%s=0x%X'%v for v in SYMBOLS.items()],'-o',str(elf),str(out/(name+'.o'))],
        check=True,capture_output=True)
    text,functions,relocations = parse_object(out/(name+'.o'))
    info = functions[FUNCTION]; pools = sections(elf)
    words = list(struct.unpack_from('>%dI'%(info['size']//4),pools['.text'][1],info['value']))
    end = max(i for i,w in enumerate(words) if w == 0x03E00008)+2
    assert not any(words[end:]); words = words[:end]
    retail = struct.unpack_from('>115I',(root/'conker/conker.us.bin').read_bytes(),ROM)
    frames = [(-w)&65535 for w in words if w&0xFFFF0000 == 0x27BD0000 and w&0x8000]
    meta.update(body_words=end,frame=frames[0] if frames else 0,
        differences=sum(a!=b for a,b in itertools.zip_longest(words,retail,fillvalue=0)),
        relocations=relocations,pool_bytes=len(pools.get('.rodata',(0,b''))[1]))
    return meta,words,pools.get('.rodata',(0,b''))[1]


def install(source):
    assert source.count(ORIGINAL) == 1 and SELECTED not in source
    assert DECLARATIONS.rstrip() not in source
    return source.replace(ORIGINAL,SELECTED).replace('#include <ultra64.h>\n',
        '#include <ultra64.h>\n'+DECLARATIONS,1)


def bind_pool(makefile):
    assert makefile.count(PROFILE_LINE) == 1 and BINDING_LINE not in makefile
    return makefile.replace(PROFILE_LINE,PROFILE_LINE+'\n'+BINDING_LINE,1)


def bind_pool_bytes(data):
    anchor=PROFILE_LINE.encode('ascii')
    assert data.count(anchor)==1 and BINDING_LINE.encode('ascii') not in data
    end=data.index(anchor)+len(anchor)
    newline=b'\r\n' if data[end:end+2]==b'\r\n' else b'\n'
    assert data[end:end+len(newline)]==newline
    return data[:end]+newline+BINDING_LINE.encode('ascii')+data[end:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter',default='selected')
    parser.add_argument('--profiles',action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]; out = root/'conker/build/game-extended-character-metrics'
    records = []
    for name,body in candidates():
        if args.filter and args.filter not in name:
            continue
        for profile in (('owner','o2g3','o1g3','o1') if args.profiles else ('owner',)):
            meta,_,_ = compile_candidate(root,out,name+'-'+profile,body,profile)
            records.append(meta)
            print(meta['name'],meta['body_words'],hex(meta['frame']),meta['differences'],meta['pool_bytes'],flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__ == '__main__':
    main()
