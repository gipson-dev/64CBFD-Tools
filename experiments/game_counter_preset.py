"""Recover the signed-slot counter gate and pre-call clear with the full preset."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_actor_type_preset as previous
from tools.tests import actor_type_preset_checkpoint as checkpoint
from tools.pad_generated_object import emit_padded_assembly

BUILD = 'conker/build/game-counter-preset'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_1516EED4', 0x1516EED4, 0x19C384, 84
CALLEE, TABLE = 0x1516D99C, 0x800DD2A0
PATHS = dict(previous.PATHS)
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER)
build = previous.build
SELECTED = '''/* Consume a qualifying slot counter before creating its effect preset. */
void func_1516EED4(s32 arg0, s32 arg1, s32 arg2, s32 arg3) {
    u8 *counter = &D_800DD2A0 + arg0;

    if (arg0 < 4 && (s32)*counter >= arg1) {
        *counter = 0;
        func_1516D99C(
            0, 0, 0, 4, 0, 0xFF, 0xFF, 0xFF,
            0, 0, 0, 0, 2, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0x200, 0x200, 0, 0, 0x1E,
            0, 0, arg0, 0x14, 0, 0, 0x81, 8,
            0, 1, 0, 0, 0, 0xC, 0, (u8)arg2, arg3);
    }
}
'''
INITIAL = SELECTED


def candidates():
    separate = INITIAL.replace('u8 *counter = &D_800DD2A0 + arg0;',
        'u8 *counter;\n\n    counter = &D_800DD2A0 + arg0;')
    unsigned = separate.replace('0, 0, 0, 4, 0, 0xFF, 0xFF, 0xFF,',
        '0, 0, 0, 4U, 0U, 0xFFU, 0xFFU, 0xFFU,')
    for line in ('0, 0, 0, 0, 2, 0, 0, 0,', '0, 0, 0, 0, 0, 0, 0, 0,',
            '0, 0, 0, 0x200, 0x200, 0, 0, 0x1E,',
            '0, 0, arg0, 0x14, 0, 0, 0x81, 8,', '0, 1, 0, 0, 0, 0xC, 0, (u8)arg2, arg3);'):
        tokens = line.split(', ')
        # Match the archived narrow-parameter literal types, not a new profile.
        indices = {'0, 0, 0, 0x200, 0x200, 0, 0, 0x1E,': (0, 1, 2, 7),
            '0, 0, arg0, 0x14, 0, 0, 0x81, 8,': (0, 1, 3, 5, 6, 7),
            '0, 1, 0, 0, 0, 0xC, 0, (u8)arg2, arg3);': (0, 1, 2, 3, 5, 6)}.get(line, range(8))
        for i in indices:
            tokens[i] = tokens[i].rstrip(',') + 'U' + (',' if tokens[i].endswith(',') else '')
        unsigned = unsigned.replace(line, ', '.join(tokens))
    narrow = unsigned.replace('0, 0, arg0, 0x14U,', '0, 0, (u8)arg0, 0x14U,')
    captured = INITIAL.replace('        *counter = 0;',
        '        u8 flag = arg2;\n        s32 tag = arg3;\n        s32 slot = arg0;\n\n        *counter = 0;').replace('0, 0, arg0, 0x14,',
            '0, 0, slot, 0x14,').replace('(u8)arg2, arg3);', 'flag, tag);')
    inline = INITIAL.replace('    u8 *counter = &D_800DD2A0 + arg0;\n\n', '').replace('*counter', '(&D_800DD2A0)[arg0]')
    assigned = inline.replace('    if (arg0 < 4', '    s32 slot;\n\n    if ((slot = arg0) < 4').replace('(s32)(&D_800DD2A0)[arg0]', '(s32)(&D_800DD2A0)[slot]')
    return dict(initial=INITIAL, separate=separate, archived_literals=unsigned,
        archived_index=unsigned.replace('&D_800DD2A0 + arg0', '&(&D_800DD2A0)[arg0]'),
        archived_narrow=narrow,
        word_address=INITIAL.replace('&D_800DD2A0 + arg0', '(u8 *)((u32)&D_800DD2A0 + (u32)arg0)'),
        copied_slot=INITIAL.replace('    u8 *counter = &D_800DD2A0 + arg0;',
            '    s32 slot = arg0;\n    u8 *counter = &D_800DD2A0 + slot;').replace('if (arg0 < 4', 'if (slot < 4'),
        unsigned_pointer=INITIAL.replace('&D_800DD2A0 + arg0', '&D_800DD2A0 + (u32)arg0'),
        inverted=INITIAL.replace('arg0 < 4 && (s32)*counter >= arg1', 'arg0 < 4 && arg1 <= (s32)*counter'),
        register_input=INITIAL.replace('(s32 arg0,', '(register s32 arg0,'),
        unsigned_input=INITIAL.replace('(s32 arg0,', '(u32 arg0,').replace('arg0 < 4', '(s32)arg0 < 4'),
        copied_everywhere=INITIAL.replace('    u8 *counter', '    s32 slot = arg0;\n    u8 *counter').replace('+ arg0', '+ slot').replace('if (arg0 <', 'if (slot <').replace('0, 0, arg0,', '0, 0, slot,'),
        commuted=INITIAL.replace('&D_800DD2A0 + arg0', 'arg0 + &D_800DD2A0'),
        comma_gate=INITIAL.replace('    u8 *counter = &D_800DD2A0 + arg0;', '    u8 *counter;').replace('if (arg0 < 4 &&', 'if ((counter = &D_800DD2A0 + arg0, arg0 < 4) &&'),
        captured_inputs=captured,
        argument_clear=INITIAL.replace('        *counter = 0;\n', '').replace('            0, 0, 0, 4,', '            (*counter = 0), 0, 0, 4,'),
        nested_pointer=INITIAL.replace('    u8 *counter = &D_800DD2A0 + arg0;', '    u8 *counter;').replace('    if (arg0 < 4 && (s32)*counter >= arg1) {',
            '    if (arg0 < 4) {\n        counter = &D_800DD2A0 + arg0;\n        if ((s32)*counter < arg1) return;'),
        pointer_difference_gate=INITIAL.replace('arg0 < 4', 'counter - &D_800DD2A0 < 4'),
        word_difference_gate=INITIAL.replace('arg0 < 4', '(s32)((u32)counter - (u32)&D_800DD2A0) < 4'),
        nonzero_gate=INITIAL.replace('arg0 < 4', '!(arg0 >= 4)'),
        conditional_gate=INITIAL.replace('arg0 < 4 && (s32)*counter >= arg1', 'arg0 < 4 ? (s32)*counter >= arg1 : 0'),
        inline_counter=inline,
        assigned_gate=assigned,
        assigned_gate_store=assigned.replace('        (&D_800DD2A0)[arg0] =', '        (&D_800DD2A0)[slot] ='),
        inline_le_gate=inline.replace('arg0 < 4', 'arg0 <= 3'),
        register_pointer=INITIAL.replace('u8 *counter', 'register u8 *counter'),
        early_return=INITIAL.replace('    if (arg0 < 4 && (s32)*counter >= arg1) {',
            '    if (arg0 >= 4) return;\n    if ((s32)*counter < arg1) return;\n    {'))


SELECTED = candidates()['inline_counter']
LINKED_SHA256 = '368f27dd4d9fa72f9effe32c97fad90f86ff257964b5e7ef7a58cbb221092952'


def diagnostic_fit(words):
    """Describe the closed compiler delta; never install or emit guard rows."""
    if len(words) != 85 or hashlib.sha256(struct.pack('>85I', *words)).hexdigest() != LINKED_SHA256:
        raise ValueError('Unknown linked counter-preset diagnostic input')
    registers = {8: 25, 9: 8, 10: 9, 11: 10, 12: 11, 13: 12, 14: 13, 15: 14, 24: 15, 25: 24}
    result = []
    for index, word in enumerate(words):
        if index == 10:
            continue
        op = word >> 26
        fields = (21, 16, 11) if op == 0 else () if op in (2, 3) else (21, 16)
        for shift in fields:
            register = word >> shift & 31
            # The original opening index stays in T6; later T6 joins the cycle.
            replacement = registers.get(register, register) if index >= 6 and not (index < 11 and register == 14) else register
            word = word & ~(31 << shift) | replacement << shift
        if index == 9:
            word = word & 0xFFFF0000 | ((word & 65535) - 1)
        result.append(word)
    return result


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        hashes = {key: hashlib.sha256(value).hexdigest() for key, value in data.items()}
        if hashes != BASELINE:
            raise ValueError('Changed counter-preset predecessor: ' + repr({k: v for k, v in hashes.items() if v != BASELINE[k]}))
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed counter-preset baseline manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed counter-preset fixture: ' + key)


def recovered_owner(before, selected=SELECTED):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1516EED4() {\n    return 0;\n}':
        raise ValueError('Unknown counter-preset placeholder')
    return (before[:lo] + selected.rstrip() + before[hi:]).replace('extern s32 D_800BE9E4;',
        'extern s32 D_800BE9E4;\nextern u8 D_800DD2A0;', 1)


def measure(root, out, label, selected=SELECTED):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recovered_owner((out / 'before-preset_owner').read_text(), selected), label)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>%dI' % WORDS, (root / 'conker/conker.us.bin').read_bytes(), ROM))
    row = dict(label=label, words=len(words), differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        diagnostics=diagnostics, different_words=[(index * 4, '0x%08X' % actual, '0x%08X' % expected)
            for index, (actual, expected) in enumerate(zip(words, truth)) if actual != expected])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def qualify(root, out):
    obj, words, row = measure(root, out, 'qualified')
    if (row['words'], row['differences'], row['diagnostics']) != (WORDS, 0, ''):
        raise ValueError('Counter preset is not a direct match: ' + repr(row))
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER,
        word_patches_path=out / 'before-guards'))
    padded = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(path)], check=True, capture_output=True)
    data, functions = build.link_owner(root, out, padded, OWNER)
    f = functions[FUNCTION]
    if f['size'] != WORDS * 4 or list(struct.unpack_from('>%dI' % WORDS, data, f['value'])) != words:
        raise ValueError('Counter-preset production padder differs')
    row.update(guards_added=0, frame=208, direct_C=True)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, words, row


def recover(root, out):
    obj, words, row = measure(root, out, 'recovered')
    if (row['words'], row['differences'], row['diagnostics']) != (85, 76, ''):
        raise ValueError('Changed counter-preset recovery: ' + repr(row))
    row.update(installable=False, guards_added=0, retail_words=WORDS,
        reason='Extra opening index load and coupled private register allocation differ')
    (out / 'recovery.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen', action='store_true')
    parser.add_argument('--qualify', action='store_true')
    args = parser.parse_args()
    if args.screen:
        for name, body in candidates().items():
            row = measure(Path.cwd(), Path.cwd() / BUILD, name, body)[-1]
            print(json.dumps({k: row[k] for k in ('label', 'words', 'differences', 'diagnostics')}), flush=True)
        return
    action = qualify if args.qualify else recover
    print(json.dumps(action(Path.cwd(), Path.cwd() / BUILD)[-1], indent=2))


if __name__ == '__main__':
    main()
