"""Qualify view side-plane recovery and disjoint phase-local home coalescing."""
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_remaining_donor_candidates as build

BUILD = 'conker/build/game-view-frustum-planes'
FUNCTION, OWNER, ENTRY, ROM, WORDS, RAW_WORDS = 'func_1501B22C', 'game_476D0', 0x1501B22C, 0x486DC, 61, 59
GUARDS = ((0x54, 0xE7AC0020, 0xE7AC0024), (0x58, 0xC7AC0020, 0xC7AC0024),
    (0x60, 0xE7A00030, 0xE7A00034), (0x64, 0xC7A20030, 0xC7A20034))
GUARD_ROWS = ''.join('game_476D0,func_1501B22C,0x%X,0x%08X,0x%08X,-,-,Coalesce disjoint horizontal and vertical frustum angle and cosine stack homes,,,false\n' % row for row in GUARDS)
PATHS = {
    'elf': 'conker/build/conker.us.elf', 'owner': 'conker/src/game_476D0.c',
    'progress': 'conker/progress.csv', 'makefile': 'conker/Makefile',
    'guards': 'conker/retail_word_patches.us.csv',
    'functions': 'conker/include/functions.h', 'structs': 'conker/include/structs.h',
    'variables': 'conker/include/variables.h',
    'original': 'conker/asm/nonmatchings/game_476D0/func_1501B22C.s',
}
BASELINE = {
    'elf': 'c9ff4e7ec28882546f87fb159a96b0c0e1c2b8fac6de4eb58725d91eef78a3bd',
    'owner': '05a16ebd87fee7a6894d5a4fc1231a6322ae7ccd4aac7ffa9eb7a55616e486b1',
    'progress': '005fd7682d37802a2b7591cfb023648b6a083c8df6b957bdfedd737222cad68e',
    'makefile': '838070597f76ea2f7182c158dfb6710946cfcabcb5435e994f93cdb99340e313',
    'guards': '25d0c541e1bd0ea1d537439e8ba4234ad629ee9c5405025cc0408d99f28e5b9a',
    'functions': '2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81',
    'structs': '081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69',
    'variables': '1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8',
    'original': '7bb5a42cff83525d209676e0ad4c89684bf121f9b9968a06c70c83e3353925cb',
}
BODY = '''/* Build the selected view's four half-FOV side-plane normals. */
void func_1501B22C(s32 index) {
    struct259 *view = (struct259 *)(index * 0x180 + (char *)D_800BE628);
    f32 value, verticalCosine, horizontalCosine, negativeVerticalCosine;
    f32 halfVertical, verticalAngle, horizontalValue;

    value = view->unk74 * 0.5f;
    horizontalValue = -value;
    halfVertical = view->unk78 * 0.5f;
    horizontalValue *= D_80096900;
    horizontalCosine = cosf(horizontalValue);
    horizontalValue = sinf(horizontalValue);
    view->unk9C = horizontalValue;
    view->unk90 = horizontalValue;
    horizontalCosine = -horizontalCosine;
    view->unk88 = -horizontalCosine;
    view->unk94 = horizontalCosine;
    view->unk98 = 0.0f;
    view->unk8C = 0.0f;
    verticalAngle = halfVertical * D_80096904;
    verticalCosine = cosf(verticalAngle);
    value = sinf(verticalAngle);
    negativeVerticalCosine = -verticalCosine;
    value = -value;
    view->unkA0 = 0.0f;
    view->unkB0 = -negativeVerticalCosine;
    view->unkA8 = value;
    view->unkB4 = value;
    view->unkAC = 0.0f;
    view->unkA4 = negativeVerticalCosine;
}'''


def recover(before, body=BODY):
    lo, hi = build.function_span(before, FUNCTION)
    trailing = before[hi:]
    if not trailing.startswith('\n// JUSTREG: I think?') or any(line and not line.startswith('//') for line in trailing.splitlines()):
        raise ValueError('Expected only the original disabled terminal draft')
    result = before[:lo] + body + '\n'
    declaration = 's32 func_1501B22C();\n'
    if result.count(declaration) != 1:
        raise ValueError('Expected one obsolete view placeholder declaration')
    result = result.replace(declaration, '')
    result = result.replace('/* Non-matching C placeholders for asm/nonmatchings/game_476D0/func_1501B22C.s. */\n', '')
    return result.replace('#include "variables.h"\n', '#include "variables.h"\n\nvoid func_1501B22C(s32 index);\n', 1)


def freeze(root, out):
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        if {key: hashlib.sha256(value).hexdigest() for key, value in data.items()} != BASELINE:
            raise ValueError('Refusing to capture changed view-plane inputs')
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Modified view-plane baseline manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Modified immutable view-plane input: ' + key)


def variants():
    yield 'selected', BODY
    yield 'typed-index', BODY.replace('(struct259 *)(index * 0x180 + (char *)D_800BE628)', '(struct259 *)D_800BE628 + index')
    yield 'byte-index', BODY.replace('index * 0x180 + (char *)D_800BE628', '(char *)D_800BE628 + index * 0x180')
    yield 'integer-offset', BODY.replace('index * 0x180 + (char *)D_800BE628', 'index * 0x180 + D_800BE628')
    yield 'union-angle', BODY.replace('halfVertical, verticalAngle, horizontalValue;', 'halfVertical;\n    union { f32 horizontal; f32 vertical; } angle;').replace('horizontalValue', 'angle.horizontal').replace('verticalAngle', 'angle.vertical')
    yield 'volatile-cosine', BODY.replace('verticalCosine, horizontalCosine, ', '').replace(
        '    f32 halfVertical,', '    volatile f32 cosine;\n    f32 halfVertical,').replace('verticalCosine', 'cosine').replace('horizontalCosine', 'cosine')


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    out.mkdir(exist_ok=True)
    freeze(root, out)
    before = (out / 'before-owner').read_text()
    truth = list(struct.unpack_from('>61I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    rows = []
    for label, body in variants():
        obj, diagnostics = build.compile_owner(root, out, recover(before, body), label)
        data, functions = build.link_owner(root, out, obj, OWNER)
        info = functions[FUNCTION]
        words = list(struct.unpack_from('>%dI' % (info['size'] // 4), data, info['value']))
        row = dict(label=label, words=len(words), frame=(-words[0]) & 0xFFFF,
            differences=[(i, a, b) for i, (a, b) in enumerate(zip(words, truth)) if a != b],
            warnings=diagnostics.count('cfe: Warning'), flags=['-O2', '-g3'])
        rows.append(row)
        print(json.dumps({**row, 'differences': row['differences'] if len(row['differences']) <= 12 else len(row['differences'])}), flush=True)
    (out / 'candidates.json').write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
