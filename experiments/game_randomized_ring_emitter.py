"""Recover the radial factory emitter that is the typed debris caller's prerequisite."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_six_piece_debris as previous
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.pad_generated_object import emit_padded_assembly
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_record_color_fade_match import registers
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD = 'conker/build/game-randomized-ring-emitter'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19E040', 'func_151718F0', 0x151718F0, 0x19EDA0, 193
SINE, COSINE, RANDOM, FACTORY = 0x15048A40, 0x150489B0, 0x150ADA20, 0x1516D4E8
COLORS = 0x8008CC20
PATHS, BASELINE, build, freeze = previous.PATHS, previous.BASELINE, previous.build, previous.freeze

DECLARATIONS = '''typedef struct RingColors19E040 {
    u8 values[3];
} RingColors19E040;
extern RingColors19E040 D_8008CC20;
f32 func_15048A40(u8 angle);
f32 func_150489B0(u8 angle);
s32 func_150ADA20(void);
void func_1516D4E8(
    s16 arg0, s16 arg1, s16 arg2, u8 arg3, u8 arg4, u8 arg5,
    u8 arg6, u8 arg7, u8 arg8, u8 arg9, u8 arg10, u8 arg11,
    u8 arg12, u8 arg13, u8 arg14, u8 arg15, u8 arg16, u8 arg17,
    u8 arg18, u8 arg19, u8 arg20, u8 arg21, u8 arg22, s16 arg23,
    s16 arg24, u8 arg25, s16 arg26, s32 arg27, s32 arg28, u8 arg29,
    s32 arg30);

'''

SELECTED = '''/* Emit randomized radial particles using the staged palette-zero color.
 * Nonzero palette selectors would read beyond the original three-byte object. */
void func_151718F0(f32 x, f32 y, f32 z, f32 radius, s32 lifetime,
                  f32 spread, s32 palette, s32 count, u8 flags, s32 context) {
    RingColors19E040 colors;
    u8 *color;
    f32 sine;
    f32 cosine;
    f32 positionZ;
    f32 delay;
    f32 baseLifetime;
    s32 phase;
    s32 index;
    s32 angle;
    s32 zHigh;
    s32 zLow;
    s32 extent;
    s32 fixedX;
    s32 fixedZ;
    s32 tail;
    s32 step;
    s16 height;

    colors = D_8008CC20;
    if (count != 0) {
        phase = 0;
        index = 0;
        if (count > 0) {
            step = 0xFFFF / count;
            height = (s16)(s32)y;
            baseLifetime = (f32)lifetime;
            color = colors.values + palette * 3;
            do {
                angle = (phase >> 8) & 255;
                sine = func_15048A40(angle);
                cosine = func_150489B0(angle);
                positionZ = radius * cosine + z;
                fixedZ = (s32)(200.0f * cosine);
                zHigh = (fixedZ >> 8) & 255;
                zLow = fixedZ & 255;
                delay = (f32)((u32)func_150ADA20() & 0xFFFFU) * 0.0000152587890625f + 100.0f;
                extent = (s32)((f32)((u32)func_150ADA20() & 0xFFFFU) * spread + baseLifetime);
                tail = func_150ADA20();
                fixedX = (s32)(200.0f * sine);
                func_1516D4E8((s16)(s32)(radius * sine + x), height, (s16)(s32)positionZ,
                    0xD, 0, color[0], color[1], color[2], 0, 0, 0, 0, 2,
                    (fixedX >> 8) & 255, fixedX & 255, zHigh, zLow, 0, 0, 5, 0, 0, 0,
                    (s16)extent, (s16)extent, (tail & 15) + 10, (s32)delay,
                    0, 0, flags, context);
                index += 1;
                phase += step;
            } while (index != count);
        }
    }
}
'''


def recovered_owner(before, selected=None):
    selected = SELECTED if selected is None else selected
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_151718F0() {\n    return 0;\n}':
        raise ValueError('Unknown ring placeholder')
    result = before[:lo] + selected.rstrip() + before[hi:]
    return result.replace('extern s32 D_800BE9F0;', DECLARATIONS + 'extern s32 D_800BE9F0;', 1)


def measure(root, out, label='selected', selected=None, flags=('-O2', '-g3')):
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out,
        recovered_owner((out / 'before-edge_wrapper_owner').read_text(), selected), label, flags=flags)
    data, functions = build.link_owner(root, out, obj, OWNER)
    f = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value']))
    truth = list(struct.unpack_from('>%dI' % WORDS, (root / 'conker/conker.us.bin').read_bytes(), ROM))
    pools, raw = sections(obj), parse_object(obj)
    row = dict(label=label, flags=flags, words=len(words), frame=(-words[0]) & 65535,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        diagnostics=diagnostics, pool_bytes=sum(len(pools.get(n, (0, b''))[1]) for n in ('.rodata', '.data')),
        raw_sha256=hashlib.sha256(raw[0][f['value']:f['value'] + f['size']]).hexdigest(),
        relocations={at - f['value']: rows for at, rows in raw[2].items() if f['value'] <= at < f['value'] + f['size']},
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def screens(root, out):
    start, end = INITIAL.index('    RingColors19E040 colors;'), INITIAL.index('\n\n    colors =')
    declarations = INITIAL[start:end].splitlines()
    plain = declarations[1:]
    for index in range(len(plain) + 1):
        body = INITIAL[:start] + '\n'.join(plain[:index] + declarations[:1] + plain[index:]) + INITIAL[end:]
        _, _, row = measure(root, out, 'colors-%02d' % index, body)
        print(json.dumps({k: row[k] for k in ('label', 'words', 'frame', 'differences', 'raw_sha256')}), flush=True)


def initialization_screens(root, out):
    import itertools
    initial = INITIAL.replace('    RingColors19E040 colors;\n', '').replace(
        '    s16 height;', '    s16 height;\n    u32 draw;\n    RingColors19E040 colors;').replace(
        '                delay = (f32)((u32)func_150ADA20() & 0xFFFFU)',
        '                draw = (u32)func_150ADA20() & 0xFFFFU;\n                delay = (f32)draw')
    lines = ('            height = (s16)(s32)y;', '            baseLifetime = (f32)lifetime;',
        '            color = colors.values + palette * 3;')
    for i, order in enumerate(itertools.permutations(lines)):
        body = initial.replace('\n'.join(lines), '\n'.join(order))
        _, _, row = measure(root, out, 'initialization-%d' % i, body)
        print(json.dumps({k: row[k] for k in ('label', 'words', 'frame', 'differences', 'raw_sha256')}), flush=True)


INITIAL = SELECTED
SELECTED = INITIAL.replace('    RingColors19E040 colors;\n', '').replace(
    '    s16 height;', '    s16 height;\n    u32 draw;\n    RingColors19E040 colors;').replace(
    '                delay = (f32)((u32)func_150ADA20() & 0xFFFFU)',
    '                draw = (u32)func_150ADA20() & 0xFFFFU;\n                delay = (f32)draw').replace(
    ' * Nonzero palette selectors would read beyond the original three-byte object. */',
    ' * Nonzero palette selectors would read beyond the original three-byte object.\n'
    ' * Guards normalize only eight closed initialization temporary-register words. */')
RAW_SHA256 = '4673c5ad1944b94409da4d02d2ad7740d3aaefedf974492d956da6895dc2ba99'
RELOCATIONS = {84: [('R_MIPS_HI16', 'D_8008CC20')], 88: [('R_MIPS_LO16', 'D_8008CC20')],
    244: [('R_MIPS_26', 'func_15048A40')], 256: [('R_MIPS_26', 'func_150489B0')],
    304: [('R_MIPS_26', 'func_150ADA20')], 364: [('R_MIPS_26', 'func_150ADA20')],
    424: [('R_MIPS_26', 'func_150ADA20')], 672: [('R_MIPS_26', 'func_1516D4E8')]}
RENAMES = {12: 24, 24: 12, 13: 14, 14: 13, 15: 25, 25: 15}
CHANGED = {44, 47, 48, 50, 51, 52, 54, 55}


def raw_target(obj):
    text, functions, rel = parse_object(obj)
    f = functions[FUNCTION]
    return text[f['value']:f['value'] + f['size']], {at - f['value']: rows for at, rows in rel.items()
        if f['value'] <= at < f['value'] + f['size']}


def prove_register_cycle(raw, normalized):
    if len(raw) != WORDS or len(normalized) != WORDS:
        raise ValueError('Unknown ring proof extent')
    if any(a != b for i, (a, b) in enumerate(zip(raw, normalized)) if i not in CHANGED):
        raise ValueError('Ring transformation escaped the initialization cycle')

    def evaluate(words):
        regs = [0, *(('entry', i) for i in range(1, 32))]
        fprs, reads = {}, []
        for word in words[44:56]:
            op, rs, rt, rd, shift = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31, word >> 6 & 31
            if op == 35:
                value = ('load32', regs[rs], (word & 65535) - (65536 if word & 32768 else 0))
                reads.append(value)
                regs[rt] = value
            elif op == 9:
                regs[rt] = ('add32', regs[rs], (word & 65535) - (65536 if word & 32768 else 0))
            elif op == 15:
                regs[rt] = word << 16 & 0xFFFFFFFF
            elif op == 17 and rs == 4:
                fprs[rd] = regs[rt]
            elif op == 0:
                fn = word & 63
                if fn in (0, 3):
                    regs[rd] = ('sll32' if fn == 0 else 'sra32', regs[rt], shift)
                elif fn == 18:
                    regs[rd] = ('entry-lo',)
                elif fn in (33, 35):
                    regs[rd] = ('add32' if fn == 33 else 'sub32', regs[rs], regs[rt])
                elif fn == 37 and regs[rt] == 0:
                    regs[rd] = regs[rs]
                else:
                    raise ValueError('Unsupported ring initialization operation')
            else:
                raise ValueError('Unsupported ring initialization opcode')
            regs[0] = 0
        return {i: value for i, value in enumerate(regs) if i not in RENAMES}, fprs, reads

    if evaluate(raw) != evaluate(normalized):
        raise ValueError('Ring live-role graph differs')
    expected = [0x93BE0163, 0x468027A0, 0x00118203, 0x320900FF, 0x01208025,
        raw[61], 0x312400FF]
    if raw[56:63] != expected or raw[61] >> 26 != 3:
        raise ValueError('Unknown ring first-call continuation')
    return dict(live_GPR_FPR_roles_and_ordered_reads_equal=True,
        palette_pointer_and_height_equal_for_arbitrary_words=True,
        changed_scratch_dead_before_first_provider=True,
        ordinary_memory_and_O32_caller_saved_clobber_contract=True,
        no_frame_home_schedule_opcode_branch_constant_or_binding_changes=True)


def normalize(raw, rel):
    if hashlib.sha256(raw).hexdigest() != RAW_SHA256 or rel != RELOCATIONS:
        raise ValueError('Unknown ring compiler words or bindings')
    words = list(struct.unpack('>193I', raw))
    output = [registers(word, RENAMES) if 44 <= i < 56 else word for i, word in enumerate(words)]
    prove_register_cycle(words, output)
    return struct.pack('>193I', *output)


def link_target(out, name, raw, rel, entry=ENTRY, bindings=None):
    bindings = bindings or dict(D_8008CC20=COLORS, func_15048A40=SINE, func_150489B0=COSINE,
        func_150ADA20=RANDOM, func_1516D4E8=FACTORY)
    assembly, missing = emit_function(raw, dict(value=0, size=len(raw)), rel, FUNCTION, bindings)
    if missing:
        raise ValueError('Unbound ring symbols: ' + repr(missing))
    path = out / (name + '.s')
    path.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)],
        check=True, capture_output=True)
    path.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
    subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(path.with_suffix('.ld')), '-e', FUNCTION,
        *['--defsym=%s=0x%X' % item for item in bindings.items()], '-o', str(path.with_suffix('.elf')),
        str(path.with_suffix('.o'))], check=True, capture_output=True)
    return list(struct.unpack_from('>%dI' % (len(raw) // 4), sections(path.with_suffix('.elf'))['.text'][1]))


def guard_manifest(before, raw, rel):
    if hashlib.sha256(before).hexdigest() != BASELINE['guards'] or (',' + FUNCTION + ',').encode() in before:
        raise ValueError('Unknown ring guard predecessor')
    replacement = struct.unpack('>193I', normalize(raw, rel))
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=next(csv.reader(io.StringIO(before.decode()))), lineterminator='\n')
    for i, expected in enumerate(struct.unpack('>193I', raw)):
        bindings = ';'.join(kind + ':' + name for kind, name in rel.get(i * 4, [])) or '-'
        writer.writerow(dict(filename=OWNER, function=FUNCTION, offset='0x%X' % (i * 4),
            expected='0x%08X' % expected, replacement='0x%08X' % replacement[i],
            expected_relocations=bindings, replacement_relocations=bindings,
            note='Retain ring compiler fingerprint' if expected == replacement[i] else
                'Normalize checked ring initialization temporary registers',
            insert_after='', insert_after_relocations='', omit='false'))
    return before + output.getvalue().encode()


def qualify(root, out):
    obj, raw_words, row = measure(root, out, 'qualified')
    if (row['words'], row['frame'], row['differences'], row['diagnostics'], row['pool_bytes']) != (193, 320, 8, '', 0):
        raise ValueError('Unknown ring compiler shape')
    raw, rel = raw_target(obj)
    normalized = normalize(raw, rel)
    words = link_target(out, 'normalized', normalized, rel)
    proof = prove_register_cycle(raw_words, words)
    truth = list(struct.unpack_from('>193I', (root / 'conker/conker.us.bin').read_bytes(), ROM))
    if words != truth:
        raise ValueError('Ring normalization is not retail exact')
    manifest = out / 'qualified-guards.csv'
    manifest.write_bytes(guard_manifest((out / 'before-guards').read_bytes(), raw, rel))
    path = out / 'qualified-padded.s'
    path.write_text(emit_padded_assembly(obj, root / PATHS['edge_wrapper_original'], filename=OWNER, word_patches_path=manifest))
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
    data, functions = build.link_owner(root, out, path.with_suffix('.o'), OWNER)
    f = functions[FUNCTION]
    if f['size'] != 772 or list(struct.unpack_from('>193I', data, f['value'])) != words:
        raise ValueError('Ring actual padding differs')
    row.update(guarded_words=193, guarded_differences=0, identity_guards=185, transforming_guards=8,
        no_insertion_omission_schedule_or_home_changes=True, proof=proof)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, path.with_suffix('.o'), raw_words, words, row


def expected_image(before, rom):
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown ring predecessor ELF')
    row = next(row for row in symbol_rows(before) if row[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError('Unknown ring predecessor extent')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, 772)
    result[at:at + 772] = rom[ROM:ROM + 772]
    struct.pack_into('>I', result, row[0] + 8, 772)
    return bytes(result)


def expected_inputs(root, out):
    raw, rel = raw_target(out / 'qualified.o')
    return dict(elf=expected_image((out / 'before-elf').read_bytes(), (root / 'conker/conker.us.bin').read_bytes()),
        edge_wrapper_owner=recovered_owner((out / 'before-edge_wrapper_owner').read_text()).encode(),
        guards=guard_manifest((out / 'before-guards').read_bytes(), raw, rel))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen', action='store_true')
    parser.add_argument('--initialization-screen', action='store_true')
    parser.add_argument('--qualify', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.qualify:
        print(json.dumps(qualify(root, root / BUILD)[-1], indent=2))
    elif args.initialization_screen:
        initialization_screens(root, root / BUILD)
    elif args.screen:
        screens(root, root / BUILD)
    else:
        print(json.dumps({k: v for k, v in measure(root, root / BUILD)[-1].items() if k != 'different_words'}, indent=2))
