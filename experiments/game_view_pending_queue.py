"""Reconstruct the pending projection queue in a private owner candidate."""
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_remaining_donor_candidates as build
from tools.experiments import game_view_orthographic_setup as previous

BUILD = 'conker/build/game-view-pending-queue'
FUNCTION, OWNER, ENTRY, ROM, WORDS = 'func_1510B3B0', 'generated_138520', 0x1510B3B0, 0x138860, 42
PATHS = {key: previous.PATHS[key] for key in ('elf', 'owner', 'guards', 'progress',
    'makefile', 'functions', 'variables', 'structs', 'layout', 'original')}
BASELINE = {key: previous.BASELINE[key] for key in PATHS}
BASELINE.update(elf='ebe9dc507cf591cb19aa4f01f20653b6c8df2bf7cba3325302738e147bd072ef',
    owner='4d528f1ca9f8678fd43bc2bdfb2d0ebbd155377d3a78de2d6e0f49d0b76d967c')
FOR_BODY = '''/* Apply pending view settings and mark each submitted row consumed. */
void func_1510B3B0(void) {
    f32 *pending;
    s32 index;

    for (index = 0, pending = D_800D9AC0[0]; index <= D_80082FA0;
         index++, pending += 3) {
        if (pending[0] != -1.0f) {
            func_1510B128(index, pending[1], pending[2], pending[0], 0.0f);
            pending[0] = -1.0f;
        }
    }
    D_800D9AF0 = 0;
}
'''
BODY = '''/* Apply pending view settings and mark each submitted row consumed. */
void func_1510B3B0(void) {
    f32 *pending;
    s32 index;

    index = 0;
    if (D_80082FA0 >= 0) {
        pending = D_800D9AC0[0];
        do {
            if (pending[0] != -1.0f) {
                func_1510B128(index, pending[1], pending[2], pending[0], 0.0f);
                pending[0] = -1.0f;
            }
            pending += 3;
        } while (++index <= D_80082FA0);
    }
    D_800D9AF0 = 0;
}
'''
GUARDS = ((0x54, 0x8E050004, 0x44070000), (0x58, 0x8E060008, 0x8E050004),
    (0x5C, 0x44070000, 0x8E060008))
GUARD_ROWS = ''.join('%s,%s,0x%X,0x%08X,0x%08X,-,-,Preserve closed pending-view argument load and float-move schedule,,,false\n' %
    ((OWNER, FUNCTION) + row) for row in GUARDS)


def guard_manifest(before):
    assert before.endswith(b'\n') and (',' + FUNCTION + ',').encode() not in before
    return before + GUARD_ROWS.encode()


def recover(before, body=BODY):
    lo, hi = build.function_span(before, FUNCTION)
    result = before[:lo] + body.rstrip() + before[hi:]
    return result.replace('extern u8 *D_800BE628;\n',
        'extern u8 *D_800BE628;\nextern s32 D_80082FA0;\n', 1)


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        if {key: hashlib.sha256(value).hexdigest() for key, value in data.items()} != BASELINE:
            raise ValueError('Changed pending queue baseline')
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Modified pending queue manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Modified immutable pending queue input: ' + key)


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    freeze(root, out)
    before = (out / 'before-owner').read_text()
    retail = struct.unpack_from('>42I', (root / 'conker/conker.us.bin').read_bytes(), ROM)
    records = []
    for label, body in variants():
        obj, diagnostics = build.compile_owner(root, out, recover(before, body), label)
        data, functions = build.link_owner(root, out, obj, OWNER)
        info = functions[FUNCTION]
        words = list(struct.unpack_from('>%dI' % (info['size'] // 4), data, info['value']))
        row = dict(label=label, bytes=info['size'], frame=-words[0] & 65535, diagnostics=diagnostics,
            differences=[(i, hex(a), hex(b)) for i, (a, b) in enumerate(zip(words, retail)) if a != b],
            word_length_difference=len(words)-42)
        records.append(row)
        print(label, row['bytes'], row['frame'], len(row['differences']), diagnostics, flush=True)
    (out / 'screens.json').write_text(json.dumps(records, indent=2) + '\n')


def variants():
    for placement in ('for', 'index-first', 'pointer-first', 'inside'):
        for local in (False, True):
            for pair in (False, True):
                body = FOR_BODY
                if placement == 'index-first':
                    body = body.replace('for (index = 0, pending = D_800D9AC0[0];',
                        'index = 0;\n    for (pending = D_800D9AC0[0];')
                elif placement == 'pointer-first':
                    body = body.replace('for (index = 0, pending = D_800D9AC0[0];',
                        'pending = D_800D9AC0[0];\n    for (index = 0;')
                elif placement == 'inside':
                    body = body.replace('for (index = 0, pending = D_800D9AC0[0]; index <= D_80082FA0;\n         index++, pending += 3) {',
                        'index = 0;\n    if (D_80082FA0 >= 0) {\n        pending = D_800D9AC0[0];\n        do {')
                    body = body.replace('    }\n    D_800D9AF0 =',
                        '            pending += 3;\n        } while (++index <= D_80082FA0);\n    }\n    D_800D9AF0 =')
                if local:
                    body = body.replace('    f32 *pending;', '    f32 scale;\n    f32 *pending;')
                    body = body.replace('if (pending[0] != -1.0f)', 'if ((scale = pending[0]) != -1.0f)').replace('pending[2], pending[0],', 'pending[2], scale,')
                if pair:
                    body = body.replace('    f32 *pending;', '    f32 (*pending)[3];').replace('= D_800D9AC0[0]', '= D_800D9AC0').replace('pending += 3', 'pending++')
                    body = body.replace('pending[0]', '(*pending)[0]').replace('pending[1]', '(*pending)[1]').replace('pending[2]', '(*pending)[2]')
                yield placement + ('-local' if local else '') + ('-row' if pair else ''), body
    for capture in ('x', 'y', 'xy', 'yx'):
        for scale in (False, True):
            body = BODY.replace('    f32 *pending;', '    f32 x, y;\n    f32 *pending;')
            assignments = ''.join('            %s = pending[%d];\n' % (axis, 1 if axis == 'x' else 2) for axis in capture)
            body = body.replace('            func_1510B128(', assignments + '            func_1510B128(')
            args = 'func_1510B128(index, pending[1], pending[2], pending[0],'
            new = 'func_1510B128(index, %s, %s, pending[0],' % ('x' if 'x' in capture else 'pending[1]', 'y' if 'y' in capture else 'pending[2]')
            body = body.replace(args, new)
            if scale:
                body = body.replace('    f32 x, y;', '    f32 x, y, scale;').replace(
                    'if (pending[0] != -1.0f)', 'if (-1.0f != (scale = pending[0]))').replace('pending[0], 0.0f)', 'scale, 0.0f)')
            yield 'capture-' + capture + ('-scale' if scale else ''), body


if __name__ == '__main__':
    main()
