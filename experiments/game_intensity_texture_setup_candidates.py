"""Recover the twelve-command intensity-texture display-list setup leaf."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x150412C0, 0x6E770, 79
FUNCTION, SOURCE = 'func_150412C0', 'conker/src/game/generated_6E770.c'
ORIGINAL = 's32 func_150412C0() {\n    return 0;\n}'
DECLARATION = 'extern u8 D_80084930[];\n'
SYMBOLS = dict(D_80084930=0x80084930)
PROFILES = dict(compiler.PROFILES, owner=('-O2', '-g3', '-Wo,-loopunroll,0'),
    compact=('-O2', '-g3', '-Wo,-loopunroll,0'))
SELECTED = '''Gfx *func_150412C0(Gfx *displayList) {
    gSPTexture(displayList++, 0xFFFF, 0xFFFF, 0, G_TX_RENDERTILE, G_ON);
    gDPPipeSync(displayList++);
    gDPSetCombineMode(displayList++, G_CC_DECALRGBA, G_CC_DECALRGBA);
    gDPSetOtherMode(displayList++, G_TF_BILERP | G_TC_FILT | 0xF, 0x55204C);
    gDPSetTextureImage(displayList++, G_IM_FMT_I, G_IM_SIZ_16b, 64, D_80084930);
    gDPLoadTextureBlock_4b(displayList++, D_80084930, G_IM_FMT_I, 64, 128,
        0, G_TX_WRAP, G_TX_WRAP, 0, 0, G_TX_NOLOD, G_TX_NOLOD);
    return displayList;
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'raw-mode', SELECTED.replace('G_TF_BILERP | G_TC_FILT | 0xF', '0x2C0F')
    yield 'arg-name', SELECTED.replace('displayList', 'arg0')


def compile_candidate(root, out, name, body=SELECTED, profile='owner'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS,
            FUNCTION=FUNCTION, RECORD='', DECLARATIONS=DECLARATION,
            SYMBOLS=SYMBOLS, PROFILES=PROFILES):
        meta, words = compiler.compile_candidate(root, out, name, body, profile)
    frames = [(-word) & 65535 for word in words
        if word & 0xFFFF0000 == 0x27BD0000 and word & 0x8000]
    assert len(frames) <= 1
    meta['frame'] = frames[0] if frames else 0
    return meta, words


def install(source):
    assert source.count(ORIGINAL) == 1 and SELECTED not in source
    assert DECLARATION.rstrip() not in source
    return source.replace(ORIGINAL, SELECTED).replace(
        'extern u8 D_800848D0[];\n', 'extern u8 D_800848D0[];\n'+DECLARATION, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-intensity-texture-setup'
    records = []
    for name, body in candidates():
        for profile in (('owner', 'o2g3', 'o1g3', 'o1') if args.profiles else ('owner',)):
            meta, _ = compile_candidate(root, out, name+'-'+profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
