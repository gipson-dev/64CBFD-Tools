"""Recover two complete factory packets and the trailing Init event packet."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_dual_factory_preset as previous
from tools.tests import dual_factory_preset_checkpoint as checkpoint
from tools.pad_generated_object import emit_padded_assembly

BUILD = 'conker/build/game-paired-record-event'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_1516F548', 0x1516F548, 0x19C9F8, 199
CALLEE, EVENT, CALLBACK = 0x1516D99C, 0x1000FA64, 0x1000EBC4
PATHS = dict(previous.PATHS, event_owner='conker/src/init_EB00.c',
    event_original='conker/asm/nonmatchings/init_EB00/func_1000FA64.s')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    event_owner='df10767e2955fc9d3e355712d3c5e8b3bf6fa9681ce79b528c50a689105dfb6e',
    event_original='b1a14303f2ddb5570dad0fcc48fa4ccef21247a1518077adcf5e5df2c6444e56')
build = previous.build
SELECTED = '''s32 func_1000EBC4(struct00 *arg0, s32 arg1, s32 arg2, s32 arg3);
u16 func_1000FA64(u16 arg0, s16 arg1, s16 arg2, s16 arg3, s32 arg4,
                 u16 arg5, s16 arg6, s32 arg7, void *arg8,
                 s32 arg9, s32 argA, s32 argB);

/* Submit two preset-13 records, then event 7 with the original full-word context.
 * Slots 12..14 are unused, but retain the caller's arg15/arg16 positions. */
void func_1516F548(s32 arg0, s32 arg1, s32 arg2, s32 arg3,
                   s32 arg4, s32 arg5, s32 arg6, s32 arg7,
                   s32 arg8, s32 arg9, s32 arg10, s32 arg11,
                   s32 arg12, s32 arg13, s32 arg14, s32 arg15, s32 arg16) {
    s32 x;
    s32 y;
    s32 z;
    s32 byte4;
    s32 byte6;
    s32 width;
    s32 height;
    s32 half3;
    s32 byte9;
    s32 half5;
    s32 shiftedWidth;
    s32 shiftedHeight;

    byte4 = (u8)arg4;
    shiftedWidth = (s32)((u32)arg7 << 12) / 4096;
    shiftedHeight = (s32)((u32)arg8 << 12) / 4096;
    height = (s16)shiftedHeight;
    width = (s16)shiftedWidth;
    byte6 = (u8)arg6;
    half3 = (u16)arg3;
    byte9 = (u8)arg9;
    half5 = (s16)arg5;
    x = (s16)arg0;
    y = (s16)arg1;
    z = (s16)arg2;
    func_1516D99C(
        (s16)arg0, (s16)arg1, (s16)arg2, 13, 0, 0x67, 0x17, 13,
        0, 0, 0x12, 0, 2, byte4, 0, byte6,
        0, 0, 0, arg10, 0, 0, 0, 0, 0, 0, 0,
        width, width, height, height, half3, byte9, 20, 255, 16, half5,
        200, 1, 0, 0, 1, 0, 0, 0, 0, 0, (u8)arg15, arg16);
    func_1516D99C(
        (s16)(&x)[0], (s16)(&y)[0], (s16)(&z)[0], 13, 0, 0x67, 0x17, 13,
        0, 0, 0x12, 0, 2, (&byte4)[0], 0, (&byte6)[0],
        0, 0, 0, arg11, 0, 0, 0, 0, 0, 0, 0,
        (&width)[0], (&width)[0], (&height)[0], (&height)[0],
        (&half3)[0], (&byte9)[0], 20, 255, 16, (&half5)[0],
        200, 1, 6, 0, 1, 0, 0, 0, 0, 0, (u8)(&arg15)[0], arg16);
    func_1000FA64(7, (s16)(&x)[0], (s16)(&y)[0], (s16)(&z)[0],
                 0x36B0, 1000, 100, (s32)func_1000EBC4, (void *)arg3, 0, 0, 0);
}
'''


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        hashes = {key: hashlib.sha256(value).hexdigest() for key, value in data.items()}
        if hashes != BASELINE:
            raise ValueError('Changed paired-event predecessor: ' + repr({k: v for k, v in hashes.items() if v != BASELINE[k]}))
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed paired-event baseline manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed paired-event fixture: ' + key)


def recovered_owner(before, selected=None):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1516F548() {\n    return 0;\n}':
        raise ValueError('Unknown paired-event placeholder')
    return before[:lo] + (SELECTED if selected is None else selected).rstrip() + before[hi:]


def measure(root, out, label, selected=None):
    selected = SELECTED if selected is None else selected
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recovered_owner((out / 'before-preset_owner').read_text(), selected), label)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>199I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    row = dict(label=label, candidate_sha256=hashlib.sha256(selected.encode()).hexdigest(),
        words=len(words), differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        frame=(0x10000 - (words[0] & 65535)) & 65535, diagnostics=diagnostics,
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def qualify(root, out):
    obj, words, row = measure(root, out, 'qualified')
    if (row['words'], row['differences'], row['frame'], row['diagnostics']) != (199, 0, 248, ''):
        raise ValueError('Paired event is not a direct match: ' + repr(row))
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER, word_patches_path=out / 'before-guards'))
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], check=True, capture_output=True)
    data, functions = build.link_owner(root, out, padded, OWNER)
    f = functions[FUNCTION]
    if f['size'] != 796 or list(struct.unpack_from('>199I', data, f['value'])) != words:
        raise ValueError('Paired-event production padding differs')
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, words, row


def candidates():
    def retype(body):
        prefix, target = body.split('void func_1516F548(', 1)
        signature, tail = target.split(') {', 1)
        for index, kind in ((0, 's16'), (1, 's16'), (2, 's16'), (4, 'u8'),
                            (5, 's16'), (6, 'u8'), (9, 'u8'), (15, 'u8')):
            signature = signature.replace('s32 arg%d,' % index, '%s arg%d,' % (kind, index))
        return prefix + 'void func_1516F548(' + signature + ') {' + tail
    typed = retype(SELECTED)
    inline = SELECTED.replace('    s32 shiftedWidth;\n    s32 shiftedHeight;\n', '').replace(
        '    shiftedWidth = (s32)((u32)arg7 << 12) / 4096;\n'
        '    shiftedHeight = (s32)((u32)arg8 << 12) / 4096;\n'
        '    height = (s16)shiftedHeight;\n    width = (s16)shiftedWidth;',
        '    width = (s16)((s32)((u32)arg7 << 12) / 4096);\n'
        '    height = (s16)((s32)((u32)arg8 << 12) / 4096);')
    forms = dict(initial=SELECTED, typed=typed, inline=inline)
    forms['typed_inline'] = retype(inline)
    for name, body in list(forms.items()):
        for local in ('byte4', 'byte6', 'width', 'height', 'half3', 'byte9', 'half5'):
            body = body.replace('(&%s)[0]' % local, local)
        forms[name + '_plain'] = body
    for name in ('initial', 'initial_plain', 'typed', 'typed_plain'):
        body = forms[name].replace('0, 0, 0x12, 0, 2, byte4, 0, byte6,',
            '0, 0, 0x12, 0, 2, (u8)arg4, 0, (u8)arg6,', 1).replace(
            'width, width, height, height, half3, byte9, 20, 255, 16, half5,',
            '(s16)shiftedWidth, (s16)shiftedWidth, (s16)shiftedHeight, (s16)shiftedHeight,\n'
            '        (u16)arg3, (u8)arg9, 20, 255, 16, (s16)arg5,', 1)
        forms[name + '_inputs'] = body
    for name in ('initial_plain', 'initial_plain_inputs', 'inline_plain'):
        body = forms[name]
        for local in ('x', 'y', 'z', 'byte4', 'byte6', 'width', 'height', 'half3', 'byte9', 'half5'):
            body = body.replace('    %s = ' % local, '    (&%s)[0] = ' % local)
        forms[name + '_stores'] = body
    for name in ('initial_plain', 'inline_plain', 'initial_plain_inputs'):
        body = forms[name]
        for local in ('x', 'y', 'z'):
            body = body.replace('(&%s)[0]' % local, local)
        forms[name + '_coords'] = body
        forms[name + '_coords_live'] = body.replace('(u8)(&arg15)[0]', '(u8)arg15')
    for name in ('initial_plain', 'inline_plain'):
        body = forms[name]
        for local in ('byte4', 'byte6', 'width', 'height', 'half3', 'byte9', 'half5', 'shiftedWidth', 'shiftedHeight'):
            body = body.replace('    s32 %s;' % local, '    register s32 %s;' % local)
        forms[name + '_register'] = body
    for name in ('initial', 'initial_plain', 'initial_inputs'):
        forms[name + '_short_temps'] = forms[name].replace('s32 shiftedWidth;', 's16 shiftedWidth;').replace(
            's32 shiftedHeight;', 's16 shiftedHeight;')
    for name in ('initial_plain_coords', 'inline_plain_coords', 'initial_inputs'):
        body = forms[name]
        locals_ = ('x', 'y', 'z', 'byte4', 'byte6', 'width', 'height', 'half3', 'byte9', 'half5')
        for local in locals_:
            body = body.replace('    s32 %s;\n' % local, '')
        body = body.replace('    byte4 = ', '    struct { s32 ' + ', '.join(locals_) + '; } saved;\n\n    byte4 = ')
        for local in locals_:
            body = re.sub(r'\b' + local + r'\b', 'saved.' + local, body)
        body = body.replace('s32 ' + ', '.join('saved.' + x for x in locals_), 's32 ' + ', '.join(locals_))
        forms[name + '_struct'] = body
    for name in ('initial_plain_coords', 'inline_plain_coords', 'initial_inputs'):
        body = forms[name]
        locals_ = ('x', 'y', 'z', 'byte4', 'byte6', 'width', 'height', 'half3', 'byte9', 'half5')
        for local in locals_:
            body = body.replace('    s32 %s;\n' % local, '')
            body = body.replace('(&%s)[0]' % local, local)
        body = body.replace('    byte4 = ', '    s32 saved[10];\n\n    byte4 = ')
        for i, local in enumerate(locals_):
            body = re.sub(r'\b' + local + r'\b', 'saved[%d]' % (9 - i), body)
        forms[name + '_array'] = body
    body = forms['inline_plain_coords_struct'].replace(
        's32 x, y, z, byte4, byte6, width, height, half3, byte9, half5;',
        's32 half5, byte9, half3, height, width, byte6, byte4, z, y, x;')
    forms['inline_reverse_struct'] = body
    return forms


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--measure', action='store_true')
    parser.add_argument('--screen', action='store_true')
    parser.add_argument('--name')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.screen:
        rows = []
        for name, body in candidates().items():
            if args.name and args.name not in name:
                continue
            row = measure(root, root / BUILD, name, body)[-1]
            rows.append(row)
            print(json.dumps({k: row[k] for k in ('label', 'words', 'differences', 'frame', 'diagnostics')}), flush=True)
        if not rows:
            parser.error('No candidate name matched')
        (root / BUILD / ('screen-' + (args.name or 'all') + '.json')).write_text(json.dumps(rows, indent=2) + '\n')
        raise SystemExit(0)
    result = measure(root, root / BUILD, 'initial') if args.measure else qualify(root, root / BUILD)
    print(json.dumps(result[-1], indent=2))
