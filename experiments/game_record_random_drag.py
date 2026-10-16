"""Recover the full-word fade and repeated-X threshold in record callback 6."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_directional_burst_match as previous
from tools.tests import directional_burst_checkpoint as checkpoint
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_record_color_fade_match import registers
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD = 'conker/build/game-record-random-drag'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_151707E0', 0x151707E0, 0x19DC90, 117
STEP, RANDOM, LIFETIME_RANDOM, MOVE, SCALE_X, SCALE_Z = (
    0x800BE9E4, 0x151EF610, 0x150ADA20, 0x1516F864, 0x1516F8EC, 0x1516F91C)
PATHS, BASELINE = previous.PATHS, dict(previous.BASELINE, **checkpoint.AFTER)
build = previous.build
SELECTED = '''/* Fade the record and apply randomized drag using the repeated X threshold. */
s32 func_151707E0(u8 *record) {
    s32 first;
    s32 second;
    s8 high;
    u8 low;
    s32 value = record[0x1F];

    if (record[0x24] != 0) {
        if (value == 0) {
            record[0x24] = (u32)func_150ADA20() % 25U + 200;
        }
        if (value != 254) {
            value = (s32)((u32)value + ((u32)D_800BE9E4 << 6));
            if (value >= 255) {
                value = 254;
            }
            record[0x1F] = value;
        }
    } else {
        if (value != 0) {
            value = (s32)((u32)value - ((u32)D_800BE9E4 << 4));
            if (value < 0) {
                value = 0;
            }
            record[0x1F] = value;
        }
    }
    if (record[0x24] == 0 && value == 0) {
        return 1;
    }
    func_1516F864(record);
    if (record[0x2F] != 0) {
        func_1516F8EC(record, func_151EF610() % 32 + 230);
        func_1516F91C(record, func_151EF610() % 32 + 230);
    } else {
        high = *(s8 *)(record + 0x26);
        low = record[0x27];
        first = (s32)((u32)high << 8) + low;
        second = (s32)((u32)high << 8) + low;
        if ((s32)((u32)first * (u32)first + (u32)second * (u32)second) >= 2001) {
            func_1516F8EC(record, func_151EF610() % 32 + 220);
            func_1516F91C(record, func_151EF610() % 32 + 220);
        }
    }
    *(s16 *)(record + 0x18) = 0;
    return 0;
}
'''


def freeze(root, out):
    out.mkdir(exist_ok=True)
    manifest = out / 'baseline.json'
    if not manifest.exists():
        data = {key: (root / path).read_bytes() for key, path in PATHS.items()}
        hashes = {key: hashlib.sha256(value).hexdigest() for key, value in data.items()}
        if hashes != BASELINE:
            raise ValueError('Changed random-drag predecessor: ' + repr({k: v for k, v in hashes.items() if v != BASELINE[k]}))
        for key, value in data.items():
            (out / ('before-' + key)).write_bytes(value)
        manifest.write_text(json.dumps(BASELINE, indent=2) + '\n')
    if json.loads(manifest.read_text()) != BASELINE:
        raise ValueError('Changed random-drag manifest')
    for key, digest in BASELINE.items():
        if hashlib.sha256((out / ('before-' + key)).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed random-drag fixture: ' + key)


def recovered_owner(before, selected=None):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_151707E0() {\n    return 0;\n}':
        raise ValueError('Unknown random-drag placeholder')
    return before[:lo] + (SELECTED if selected is None else selected).rstrip() + before[hi:]


def measure(root, out, label='selected', body=None):
    body = SELECTED if body is None else body
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out, recovered_owner((out / 'before-preset_owner').read_text(), body), label)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>117I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    pools = sections(obj)
    row = dict(label=label, words=len(words), diagnostics=diagnostics,
        frame=(0x10000 - (words[0] & 65535)) & 65535,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        pool_bytes=sum(len(pools.get(name, (0, b''))[1]) for name in ('.rodata', '.data')),
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def screens(root, out):
    variants = {'unsigned-squares': INITIAL,
        'mixed-squares': INITIAL.replace('(u32)first * (u32)first', 'first * first'),
        'signed-squares': INITIAL.replace('(u32)first * (u32)first + (u32)second * (u32)second',
            '(u32)(first * first) + (u32)(second * second)'),
        'distinct-packed': INITIAL.replace('second = (s32)((u32)high << 8) + low;',
            'second = high * 256 + low;')}
    types = ('s32 first;\n    s32 second;\n    s8 high;\n    u8 low;\n    s32 value = record[0x1F];',
        's32 first;\n    s32 second;\n    s32 value = record[0x1F];\n    s8 high;\n    u8 low;',
        's8 high;\n    u8 low;\n    s32 first;\n    s32 second;\n    s32 value = record[0x1F];')
    for name, body in variants.items():
        for number, declarations in enumerate(types):
            candidate = body.replace(types[0], declarations)
            _, _, row = measure(root, out, name + '-' + str(number), candidate)
            print(json.dumps({k: v for k, v in row.items() if k != 'different_words'}), flush=True)


def expression_screens(root, out):
    distinct = INITIAL.replace('second = (s32)((u32)high << 8) + low;', 'second = high * 256 + low;')
    for remove in (('first',), ('second',), ('first', 'second')):
        body = distinct
        expressions = {'first': '(s32)((u32)high << 8) + low', 'second': 'high * 256 + low'}
        for name in remove:
            body = body.replace('    s32 ' + name + ';\n', '').replace(
                '        ' + name + ' = ' + expressions[name] + ';\n', '')
            body = body.replace('(u32)' + name, '(u32)(' + expressions[name] + ')')
        _, _, row = measure(root, out, 'inline-' + '-'.join(remove), body)
        print(json.dumps({k: v for k, v in row.items() if k != 'different_words'}), flush=True)


def inline_body():
    body = INITIAL.replace('    s32 first;\n    s32 second;\n', '').replace(
        '        first = (s32)((u32)high << 8) + low;\n        second = (s32)((u32)high << 8) + low;\n', '')
    return body.replace('(u32)first', '(u32)((s32)((u32)high << 8) + low)').replace(
        '(u32)second', '(u32)(high * 256 + low)')


def width_screens(root, out):
    body = inline_body()
    for high, low in (('s8', 'u8'), ('s32', 'u8'), ('s8', 'u32'), ('s32', 'u32')):
        candidate = body.replace('    s8 high;', '    ' + high + ' high;').replace(
            '    u8 low;', '    ' + low + ' low;')
        for reverse in (False, True):
            current = candidate
            if reverse:
                a, b = '(s32)((u32)high << 8) + low', 'high * 256 + low'
                current = current.replace(a, 'PACK_FIRST').replace(b, a).replace('PACK_FIRST', b)
            _, _, row = measure(root, out, 'width-' + high + '-' + low + '-' + str(int(reverse)), current)
            print(json.dumps({k: v for k, v in row.items() if k != 'different_words'}), flush=True)


INITIAL = SELECTED
SELECTED = inline_body().replace(
    '/* Fade the record and apply randomized drag using the repeated X threshold. */',
    '/* Fade the record and apply randomized drag using the repeated X threshold.\n'
    ' * Guards normalize only the threshold temporaries and its dead duplicate load. */').replace(
    ' * (u32)((s32)((u32)high << 8) + low)',
    ' *\n            (u32)((s32)((u32)high << 8) + low)').replace(
    ' + (u32)(high * 256 + low) *', ' +\n            (u32)(high * 256 + low) *')


def raw_target(obj):
    text, functions, rel = parse_object(obj)
    f = functions[FUNCTION]
    return text[f['value']:f['value'] + f['size']], {at - f['value']: rows for at, rows in rel.items()
        if f['value'] <= at < f['value'] + f['size']}


RAW_SHA256 = '30113f5570a2cecb768221f05ac20b958067c946dad9d0923ef3f7f7950af76d'
RELOCATIONS = {40: [('R_MIPS_26', 'func_150ADA20')],
    80: [('R_MIPS_HI16', 'D_800BE9E4')], 84: [('R_MIPS_LO16', 'D_800BE9E4')],
    128: [('R_MIPS_HI16', 'D_800BE9E4')], 132: [('R_MIPS_LO16', 'D_800BE9E4')],
    188: [('R_MIPS_26', 'func_1516F864')], 208: [('R_MIPS_26', 'func_151EF610')],
    240: [('R_MIPS_26', 'func_1516F8EC')], 248: [('R_MIPS_26', 'func_151EF610')],
    280: [('R_MIPS_26', 'func_1516F91C')], 360: [('R_MIPS_26', 'func_151EF610')],
    392: [('R_MIPS_26', 'func_1516F8EC')], 400: [('R_MIPS_26', 'func_151EF610')],
    432: [('R_MIPS_26', 'func_1516F91C')]}
RENAMES = {2: 4, 6: 5, 4: 2, 5: 3, 12: 3, 13: 12, 14: 13, 15: 14}


def prove_register_plan(raw, normalized):
    """Check the only live changed region; scratch GPR return bits are not ABI outputs."""
    if len(raw) != 117 or len(normalized) != 117:
        raise ValueError('Unknown random-drag proof extent')
    allowed = {51, *range(74, 88)}
    if any(a != b for i, (a, b) in enumerate(zip(raw, normalized)) if i not in allowed):
        raise ValueError('Random-drag transformation escaped the threshold region')
    for words in (raw, normalized):
        if words[74] != words[51] or words[50] != 0x51400018 or words[72] != 0x10000026:
            raise ValueError('Unknown random-drag dead-load CFG')
        for i, word in enumerate(words):
            if word >> 26 in (1, 4, 5, 6, 7, 20, 21, 22, 23):
                if i + 1 + ((word & 65535) + 32768) % 65536 - 32768 == 74:
                    raise ValueError('Random-drag duplicate load became reachable')

    def values(words):
        regs = [0, *(('entry', i) for i in range(1, 32))]
        hi, lo = ('entry-hi',), ('entry-lo',)
        for at in (51, *range(75, 88)):
            word = words[at]
            op, rs, rt, rd = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31
            if op in (32, 36):
                regs[rt] = ('read-s8' if op == 32 else 'read-u8', regs[rs], word & 65535)
            elif op == 0:
                fn = word & 63
                if fn == 0:
                    regs[rd] = 0 if word == 0 else ('shl32', regs[rt], word >> 6 & 31)
                elif fn == 33:
                    regs[rd] = ('add32', regs[rs], regs[rt])
                elif fn == 25:
                    hi, lo = ('multiply-high', regs[rs], regs[rt]), ('multiply-low', regs[rs], regs[rt])
                elif fn == 18:
                    regs[rd] = lo
                else:
                    raise ValueError('Unsupported random-drag proof operation')
            elif op == 10:
                regs[rt] = ('signed-less-than', regs[rs], word & 65535)
            else:
                raise ValueError('Unsupported random-drag proof opcode')
            regs[0] = 0
        return regs[1], tuple(regs[16:]), hi, lo

    if values(raw) != values(normalized):
        raise ValueError('Random-drag threshold dependency proof failed')
    # Either branch clears V0 before return, or a zero-argument RNG clobbers
    # caller-saved state before it is used again. No provider reads hidden GPRs.
    if normalized[88:92] != [0x54200016, 0xA6000018, 0x0D47BD84, 0]:
        raise ValueError('Unknown random-drag threshold continuation')
    return dict(ordered_threshold_graph_equal=True, duplicate_load_index_74_unreachable=True,
        same_branches_calls_memory_order_frame_and_saved_ABI=True,
        raw_scratch_GPR_return_bits_not_claimed=True)


def normalize(raw, relocations):
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256 or relocations != RELOCATIONS:
        raise ValueError('Unknown random-drag words or relocations')
    words = list(struct.unpack('>117I', raw))
    output = [registers(word, {2: 4} if i == 51 else RENAMES if 74 <= i <= 87 else {})
        for i, word in enumerate(words)]
    return struct.pack('>117I', *output)


def guard_manifest(before, raw, rel):
    if hashlib.sha256(before).hexdigest() != BASELINE['guards'] or (',' + FUNCTION + ',').encode() in before:
        raise ValueError('Unknown random-drag guard predecessor')
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=next(csv.reader(io.StringIO(before.decode()))), lineterminator='\n')
    replacement = struct.unpack('>117I', normalize(raw, rel))
    for i, expected in enumerate(struct.unpack('>117I', raw)):
        bindings = ';'.join(kind + ':' + name for kind, name in rel.get(i * 4, [])) or '-'
        writer.writerow(dict(filename=OWNER, function=FUNCTION, offset='0x%X' % (i * 4),
            expected='0x%08X' % expected, replacement='0x%08X' % replacement[i],
            expected_relocations=bindings, replacement_relocations=bindings,
            note='Retain random-drag compiler fingerprint' if expected == replacement[i] else
                'Normalize checked random-drag threshold temporary registers',
            insert_after='', insert_after_relocations='', omit='false'))
    return before + output.getvalue().encode()


def link_target(out, name, raw, rel, entry=ENTRY, bindings=None):
    bindings = bindings or dict(D_800BE9E4=STEP, func_150ADA20=LIFETIME_RANDOM, func_151EF610=RANDOM,
        func_1516F864=MOVE, func_1516F8EC=SCALE_X, func_1516F91C=SCALE_Z)
    assembly, missing = emit_function(raw, dict(value=0, size=len(raw)), rel, FUNCTION, bindings)
    if missing:
        raise ValueError('Unbound random-drag symbols: ' + repr(missing))
    path = out / (name + '.s')
    path.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)],
        check=True, capture_output=True)
    path.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
    subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(path.with_suffix('.ld')), '-e', FUNCTION,
        *['--defsym=%s=0x%X' % item for item in bindings.items()], '-o', str(path.with_suffix('.elf')),
        str(path.with_suffix('.o'))], check=True, capture_output=True)
    return list(struct.unpack_from('>%dI' % (len(raw) // 4), sections(path.with_suffix('.elf'))['.text'][1]))


def qualify(root, out):
    obj, raw_words, row = measure(root, out, 'qualified')
    if (row['words'], row['frame'], row['differences'], row['diagnostics'], row['pool_bytes']) != (117, 40, 13, '', 0):
        raise ValueError('Unknown random-drag compiler shape')
    raw, rel = raw_target(obj)
    normalized = normalize(raw, rel)
    words = link_target(out, 'normalized', normalized, rel, ENTRY, dict(
        D_800BE9E4=STEP, func_150ADA20=LIFETIME_RANDOM, func_151EF610=RANDOM,
        func_1516F864=MOVE, func_1516F8EC=SCALE_X, func_1516F91C=SCALE_Z))
    proof = prove_register_plan(raw_words, words)
    truth = list(struct.unpack_from('>117I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    if words != truth:
        raise ValueError('Random-drag normalization is not retail exact')
    guards = guard_manifest((out / 'before-guards').read_bytes(), raw, rel)
    manifest = out / 'qualified-guards.csv'
    manifest.write_bytes(guards)
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['preset_original'], filename=OWNER, word_patches_path=manifest))
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)],
        check=True, capture_output=True)
    data, functions = build.link_owner(root, out, path.with_suffix('.o'), OWNER)
    f = functions[FUNCTION]
    if f['size'] != 468 or list(struct.unpack_from('>117I', data, f['value'])) != words:
        raise ValueError('Random-drag actual padding differs')
    row.update(guarded_words=117, guarded_differences=0, identity_guards=104,
        transforming_guards=13, no_insertion_omission_schedule_or_home_changes=True, proof=proof)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, path.with_suffix('.o'), raw_words, words, row


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown random-drag predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError('Unknown random-drag predecessor extent')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, 468)
    result[at:at + 468] = rom[ROM:ROM + 468]
    struct.pack_into('>I', result, row[0] + 8, 468)
    return bytes(result)


def expected_inputs(root, out):
    raw, rel = raw_target(out / 'qualified.o')
    return dict(elf=expected_image((out / 'before-elf').read_bytes(), (root / 'conker/conker.us.bin').read_bytes()),
        preset_owner=recovered_owner((out / 'before-preset_owner').read_text()).encode(),
        guards=guard_manifest((out / 'before-guards').read_bytes(), raw, rel))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen', action='store_true')
    parser.add_argument('--expression-screen', action='store_true')
    parser.add_argument('--width-screen', action='store_true')
    parser.add_argument('--qualify', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.qualify:
        print(json.dumps(qualify(root, root / BUILD)[-1], indent=2))
    elif args.width_screen:
        width_screens(root, root / BUILD)
    elif args.expression_screen:
        expression_screens(root, root / BUILD)
    elif args.screen:
        screens(root, root / BUILD)
    else:
        print(json.dumps({k: v for k, v in measure(root, root / BUILD)[-1].items() if k != 'different_words'}, indent=2))
