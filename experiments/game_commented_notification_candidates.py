"""Qualify the commented live-object notification draft under the active ABI."""
import hashlib
import itertools
import json
from pathlib import Path
import struct

from tools.experiments import game_remaining_donor_candidates as build

BUILD = 'conker/build/game-commented-object-notification'
FUNCTION, OWNER, WORDS = 'func_15063168', 'game_83300', 59
BASELINE_ELF = 'bbc201571e311a6946d21093d697b0fd7c18134e861f0e162922d4952416792f'
GUARD_ROWS = (
    'game_83300,func_15063168,0x30,0x00008025,0x25CE0000,-,R_MIPS_LO16:D_800CC2D0,Normalize independent object notification base-address and index initialization schedule,,,false\n'
    'game_83300,func_15063168,0x38,0x25CE0000,0x00008025,R_MIPS_LO16:D_800CC2D0,-,Normalize independent object notification base-address and index initialization schedule,,,false\n')
BODY = '''/* Notify other live object slots whose attached reaction byte is still clear. */
void func_15063168(struct127 *object) {
    s32 index;
    s32 selfIndex;
    struct126 *attached;

    if (D_8008FD8C > 0) {
        selfIndex = ((char *)object - (char *)D_800CC2D0) / 0x32C;

        index = 0;
        do {
            if (index == selfIndex) {
                goto next;
            }
            if (!((1 << index) & D_800CC268)) {
                goto next;
            }
            attached = D_800CC2D0[index].unk31C;
            if (attached == 0) {
                goto next;
            }
            if (*(u8 *)((char *)attached + 0x1AC) != 0) {
                goto next;
            }
            func_15194FF4(object, &D_800CC2D0[index], 1);
        next:
            index++;
        } while (index < D_8008FD8C);
    }
}'''


def recover(before, body=BODY):
    pragma = '#pragma GLOBAL_ASM("asm/nonmatchings/game_83300/func_15063168.s")'
    if before.count(pragma) != 1:
        raise ValueError('Expected one notification assembly owner')
    result = before.replace(pragma, body)
    result = result.replace('s32 func_15063168();\n', '')
    result = result.replace('/* Non-matching C placeholders for asm/nonmatchings/game_83300/func_15063168.s. */\n', '')
    result = result.replace('#include "variables.h"\n', '#include "variables.h"\n\ns32 func_15194FF4(struct127 *, struct127 *, s32);\n', 1)
    return result


def freeze(root, out):
    paths = {'elf': 'conker/build/conker.us.elf', 'owner': 'conker/src/game_83300.c',
        'makefile': 'conker/Makefile', 'guards': 'conker/retail_word_patches.us.csv', 'progress': 'conker/progress.csv'}
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in paths.items()}
        if hashlib.sha256(data['elf']).hexdigest() != BASELINE_ELF:
            raise ValueError('Refusing to capture a changed image baseline')
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps({key: hashlib.sha256(value).hexdigest() for key, value in data.items()}, indent=2) + '\n')
    for key, digest in json.loads(manifest.read_text()).items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed immutable input: ' + key)


def candidates():
    yield 'donor', BODY
    yield 'index-before-gate', BODY.replace('    if (D_8008FD8C > 0)', '    index = 0;\n    if (D_8008FD8C > 0)').replace('\n        index = 0;', '')
    yield 'index-before-self', BODY.replace('        selfIndex = ', '        index = 0;\n        selfIndex = ').replace('\n\n        index = 0;', '')
    declarations = '    s32 index;\n    s32 selfIndex;\n    struct126 *attached;'
    for order in itertools.permutations(('s32 index;', 's32 selfIndex;', 'struct126 *attached;')):
        if tuple(order) != ('s32 index;', 's32 selfIndex;', 'struct126 *attached;'):
            yield 'order-' + '-'.join(line.split()[-1].strip('*;') for line in order), BODY.replace(declarations, '\n'.join('    ' + line for line in order))


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    out.mkdir(exist_ok=True)
    freeze(root, out)
    before = (out / 'before-owner').read_text()
    rom = (root / 'conker/conker.us.bin').read_bytes()
    truth = list(struct.unpack_from('>%dI' % WORDS, rom, 0x90618))
    results = []
    for label, body in candidates():
        obj, diagnostics = build.compile_owner(root, out, recover(before, body), label)
        text, functions = build.link_owner(root, out, obj, OWNER)
        info = functions[FUNCTION]
        actual = list(struct.unpack('>%dI' % (info['size'] // 4), text[info['value']:info['value'] + info['size']]))
        if len(actual) > WORDS and not any(actual[WORDS:]):
            actual = actual[:WORDS]
        differences = [(i, a, b) for i, (a, b) in enumerate(zip(actual, truth)) if a != b]
        record = dict(label=label, words=len(actual), differences=differences,
            length_delta=len(actual) - WORDS, diagnostics=diagnostics)
        print(json.dumps({key: value for key, value in record.items() if key != 'diagnostics'}), flush=True)
        results.append(record)
    (out / 'candidates.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
