"""Recover four independent byte saturations with conditional live step reads."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_actor_effect_dispatch as previous
from tools.tests import actor_effect_dispatch_checkpoint as checkpoint
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly

BUILD = 'conker/build/game-four-byte-saturation'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_19A8B0', 'func_1516D400', 0x1516D400, 0x19A8B0, 58
COUNTERS, STEP, DRIVER, TABLE = 0x800DD2A0, 0x800BE9A0, 0x15167010, 0x8008B4A8
PATHS = dict(previous.PATHS, counter_callbacks='conker/asm/data/22FF90.rodata.s',
    counter_callback_prefix='conker/asm/data/22FF40.rodata.s',
    counter_driver_original='conker/asm/nonmatchings/game_1944C0/func_15167010.s')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    counter_callbacks='9150a226f309b306c5a590f6b5d18d9eaf6227c16cc1ae390454e91dd48902af',
    counter_callback_prefix='79390c57d68092ea4bcaa684d91ad9a6ab011bdb56f2e9bccff00266eb794158',
    counter_driver_original='eb7603f0cdfd6eba072d862b3f279a7cee0f20e0312f237ec9d38b2aa495b5f0')
build = previous.build
DECLARATIONS = 'extern u8 D_800BE9A0;\n'
INITIAL = '''/* Advance each unsaturated counter using its live increment byte. */
void func_1516D400(void) {
    s32 first;
    s32 second;
    s32 third;
    s32 fourth;

    if ((s32)D_800DD2A0 < 255) {
        first = D_800DD2A0 + D_800BE9A0;
        if (first >= 256) {
            first = 255;
        }
        D_800DD2A0 = first;
    }
    if ((s32)D_800DD2A1 < 255) {
        second = D_800DD2A1 + D_800BE9A0;
        if (second >= 256) {
            second = 255;
        }
        D_800DD2A1 = second;
    }
    if ((s32)D_800DD2A2 < 255) {
        third = D_800DD2A2 + D_800BE9A0;
        if (third >= 256) {
            third = 255;
        }
        D_800DD2A2 = third;
    }
    if ((s32)D_800DD2A3 < 255) {
        fourth = D_800DD2A3 + D_800BE9A0;
        if (fourth >= 256) {
            fourth = 255;
        }
        D_800DD2A3 = fourth;
    }
}
'''
SELECTED = INITIAL


def forms():
    for shared in (False, True):
        body = INITIAL
        for i, name in enumerate(('first', 'second', 'third', 'fourth')):
            current = 'current' if shared else 'current%d' % i
            symbol = 'D_800DD2A%d' % i
            body = body.replace('    if ((s32)%s < 255) {' % symbol,
                '    %s = %s;\n    if (%s < 255) {' % (current, symbol, current))
            body = body.replace('%s = %s + D_800BE9A0;' % (name, symbol),
                '%s = %s + D_800BE9A0;' % (name, current))
        decl = '    s32 current;\n' if shared else ''.join('    s32 current%d;\n' % i for i in range(4))
        body = body.replace('    s32 first;', decl+'    s32 first;', 1)
        yield ('shared' if shared else 'separate')+'-current', body
        yield ('shared' if shared else 'separate')+'-current-explicit-byte-store', body.replace(
            ' = first;', ' = (u8)first;').replace(' = second;', ' = (u8)second;').replace(' = third;', ' = (u8)third;').replace(' = fourth;', ' = (u8)fourth;')
        yield ('shared' if shared else 'separate')+'-current-byte-type', body.replace('s32 current', 'u8 current')
    ternary = INITIAL
    for name in ('first', 'second', 'third', 'fourth'):
        ternary = ternary.replace('        if (%s >= 256) {\n            %s = 255;\n        }' % (name, name),
            '        %s = %s < 256 ? %s : 255;' % (name, name, name))
    yield 'ternary', ternary
    yield 'shared-result', INITIAL.replace('    s32 second;\n    s32 third;\n    s32 fourth;\n', '').replace('second', 'first').replace('third', 'first').replace('fourth', 'first')


def storage_forms():
    yield 'unsigned-results-signed-test', INITIAL.replace('    s32 ', '    u32 ').replace(
        'if (first >=', 'if ((s32)first >=').replace('if (second >=', 'if ((s32)second >=').replace(
        'if (third >=', 'if ((s32)third >=').replace('if (fourth >=', 'if ((s32)fourth >=')
    yield 'word-fallthrough-diagnostic-only', INITIAL.replace('void func_', 's32 func_')
    for kind in ('addressed-result', 'one-branch-store', 'late-output-pointer', 'volatile-byte-snapshots-diagnostic'):
        body = INITIAL
        if kind == 'late-output-pointer':
            body = body.replace('    s32 first;', '    u8 *output;\n    s32 first;', 1)
        for i, name in enumerate(('first', 'second', 'third', 'fourth')):
            symbol = 'D_800DD2A%d' % i
            if kind == 'addressed-result':
                body = body.replace('%s = %s;' % (symbol, name), '%s = (&%s)[0];' % (symbol, name))
            elif kind == 'one-branch-store':
                old = '        if (%s >= 256) {\n            %s = 255;\n        }\n        %s = %s;' % (name, name, symbol, name)
                new = '        if (%s < 256) {\n            %s = %s;\n        } else {\n            %s = 255;\n        }' % (name, symbol, name, symbol)
                body = body.replace(old, new)
            elif kind == 'late-output-pointer':
                body = body.replace('%s = %s;' % (symbol, name), 'output = &%s;\n        *output = %s;' % (symbol, name))
            else:
                body = body.replace('    if ((s32)%s < 255) {' % symbol,
                    '    %s = *(volatile u8 *)&%s;\n    if (%s < 255) {' % (name, symbol, name)).replace(
                    '%s = %s + D_800BE9A0;' % (name, symbol), '%s += D_800BE9A0;' % name).replace(
                    '%s = %s;' % (symbol, name), '*(volatile u8 *)&%s = %s;' % (symbol, name))
        yield kind, body


def freeze(root, out):
    with patch.multiple(previous, PATHS=PATHS, BASELINE=BASELINE):
        previous.freeze(root, out)


def recovered_owner(before, selected=None):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1516D400() {\n    return 0;\n}':
        raise ValueError('Unknown four-counter predecessor')
    marker = 'extern u8 D_800DD2A0;\n'
    if before.count(marker) != 1:
        raise ValueError('Unknown four-counter declaration anchor')
    result = before[:lo] + (SELECTED if selected is None else selected).rstrip() + before[hi:]
    declarations = DECLARATIONS
    if any('D_800DD2A%d' % i in (SELECTED if selected is None else selected) for i in range(1, 4)):
        declarations = 'extern u8 D_800DD2A1, D_800DD2A2, D_800DD2A3;\n'+declarations
    return result.replace(marker, marker+declarations, 1)


scalar_owner = recovered_owner


def array_owner(before, selected=None):
    result = scalar_owner(before, selected)
    return result.replace('extern u8 D_800DD2A0;\n', 'extern u8 D_800DD2A0[4];\n').replace(
        '(&D_800DD2A0)[arg0]', '((u8 *)&D_800DD2A0)[arg0]')


def array_forms():
    loop = '''/* Advance the four counters, retaining each conditional step read. */
void func_1516D400(void) {
    s32 index;
    s32 value;
    for (index = 0; index < 4; index++) {
        value = D_800DD2A0[index];
        if (value < 255) {
            value += D_800BE9A0;
            if (value >= 256) {
                value = 255;
            }
            D_800DD2A0[index] = value;
        }
    }
}
'''
    yield 'array-loop', loop
    yield 'array-loop-repeat-read', loop.replace('        value = D_800DD2A0[index];\n        if (value < 255) {\n            value += D_800BE9A0;',
        '        if ((s32)D_800DD2A0[index] < 255) {\n            value = D_800DD2A0[index] + D_800BE9A0;')
    yield 'array-loop-unsigned-index', loop.replace('s32 index;', 'u32 index;')
    yield 'array-loop-register-value', loop.replace('s32 value;', 'register s32 value;')
    yield 'array-loop-reversed-add', loop.replace('value += D_800BE9A0;', 'value = D_800BE9A0 + value;')
    yield 'array-loop-preincrement', loop.replace('index++)', '++index)')
    yield 'array-loop-do-while', loop.replace('    for (index = 0; index < 4; index++) {', '    index = 0;\n    do {').replace('    }\n}\n', '    } while (++index < 4);\n}\n')
    yield 'array-pointer-loop', loop.replace('    s32 index;', '    u8 *counter;').replace(
        'for (index = 0; index < 4; index++)', 'for (counter = D_800DD2A0; counter < D_800DD2A0 + 4; counter++)').replace(
        'D_800DD2A0[index]', '*counter')
    explicit = INITIAL
    for i in range(4):
        explicit = explicit.replace('D_800DD2A%d' % i, 'D_800DD2A0[%d]' % i)
    yield 'array-unrolled', explicit
    yield 'array-loop-current', loop.replace('    s32 value;', '    s32 current;\n    s32 value;').replace(
        '        value = D_800DD2A0[index];\n        if (value < 255) {\n            value += D_800BE9A0;',
        '        current = D_800DD2A0[index];\n        if (current < 255) {\n            value = current + D_800BE9A0;')


def measure(root, out, label='selected', selected=None, flags=('-O2', '-g3'), isolate=False):
    freeze(root, out)
    run = subprocess.run
    def filtered_processor(command, *args, **kwargs):
        if len(command) > 1 and str(command[1]).endswith('/asm_processor.py'):
            command = [x for x in command if not str(x).startswith('-Wo,')]
        return run(command, *args, **kwargs)
    with patch.object(build.subprocess, 'run', filtered_processor):
        obj, diagnostics = build.compile_owner(root, out,
            recovered_owner((out / 'before-preset_owner').read_text(), selected), label, flags=flags)
    raw_text, funcs, rel = parse_object(obj)
    f = funcs[FUNCTION]
    link_obj = obj
    if f['size'] <= WORDS*4:
        primary, overrides = obj, None
        if isolate or tuple(flags) != ('-O2', '-g3'):
            primary, baseline_diagnostics = build.compile_owner(root, out,
                (out / 'before-preset_owner').read_text(), label+'-neighbor-baseline')
            if baseline_diagnostics:
                raise ValueError(baseline_diagnostics)
            overrides = {FUNCTION: obj}
        padded = out / (label+'-padded.s')
        padded.write_text(emit_padded_assembly(primary, root / PATHS['preset_original'], filename=OWNER,
            function_objects=overrides, word_patches_path=out / 'before-guards'))
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded.with_suffix('.o')), str(padded)], check=True, capture_output=True)
        link_obj = padded.with_suffix('.o')
    text, functions = build.link_owner(root, out, link_obj, OWNER)
    linked = functions[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (linked['size']//4), text, linked['value']))
    truth = list(struct.unpack_from('>58I', (out / 'before-retail_rom').read_bytes(), ROM))
    row = dict(label=label, flags=flags, words=len(words), differences=sum(a != b for a, b in zip(words, truth))+abs(len(words)-58),
        diagnostics=diagnostics, raw_sha256=hashlib.sha256(raw_text[f['value']:f['value']+f['size']]).hexdigest(),
        relocations={at-f['value']: v for at, v in rel.items() if f['value'] <= at < f['value']+f['size']},
        pools={n: d.hex() for n, (_, d) in sections(obj).items()
            if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d},
        different_words=[(i*4, '0x%08X'%a, '0x%08X'%b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label+'.json')).write_text(json.dumps(row, indent=2)+'\n')
    return obj, words, row


SELECTED = dict(array_forms())['array-loop-repeat-read']
recovered_owner = array_owner
RAW_SHA256 = 'cb81a04908e36763bd2765801292a0a1052cdac6d76d81c008ad47b70b082af7'
RELOCATIONS = {at: [('R_MIPS_HI16' if at in (0, 8, 52, 60, 68, 112, 120, 164, 172, 216) else 'R_MIPS_LO16',
    'D_800BE9A0' if at in (8, 12, 68, 72) else 'D_800DD2A0')]
    for at in (0, 4, 8, 12, 52, 56, 60, 64, 68, 72, 112, 116, 120, 124, 164, 168, 172, 176, 216, 220)}


def checked_object(obj):
    text, funcs, rel = parse_object(obj)
    f = funcs[FUNCTION]
    raw = text[f['value']:f['value']+f['size']]
    relative = {a-f['value']: v for a, v in rel.items() if f['value'] <= a < f['value']+f['size']}
    pools = {n: d for n, (_, d) in sections(obj).items()
        if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d}
    if len(raw) != 232 or hashlib.sha256(raw).hexdigest() != RAW_SHA256 or relative != RELOCATIONS or pools:
        raise ValueError('Unknown four-counter compiler words, bindings or pools')
    return raw, relative


def qualify(root, out):
    obj, words, row = measure(root, out, 'qualified')
    checked_object(obj)
    if (row['words'], row['differences'], row['diagnostics']) != (58, 0, ''):
        raise ValueError('Four-counter routine is not a direct 58-word match')
    if (','+FUNCTION+',').encode() in (out / 'before-guards').read_bytes():
        raise ValueError('Four-counter routine must not acquire instruction guards')
    return obj, out / 'qualified-padded.o', words, row


def slot_expected_image(before, rom):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown four-counter predecessor ELF')
    row = next(r for r in symbol_rows(before) if r[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError('Unknown four-counter predecessor extent')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, 232)
    result[at:at+232] = rom[ROM:ROM+232]
    struct.pack_into('>I', result, row[0]+8, 232)
    return bytes(result)


def expected_inputs(root, out):
    return dict(elf=slot_expected_image((out / 'before-elf').read_bytes(), (out / 'before-retail_rom').read_bytes()),
        preset_owner=recovered_owner((out / 'before-preset_owner').read_text()).encode())


def prelink_prediction(root, out):
    _, padded, _, _ = qualify(root, out)
    capture = out / 'link-inputs.json'
    if not capture.exists():
        if {k: hashlib.sha256((root / p).read_bytes()).hexdigest() for k, p in PATHS.items()} != BASELINE:
            raise ValueError('Four-counter link capture must precede installation')
        (out / 'before-linkscript').write_bytes((root / 'conker/build/conker.ld').read_bytes())
        (out / 'before-owner.o').write_bytes((root / 'conker/build/src/game' / (OWNER+'.c.o')).read_bytes())
        capture.write_text(json.dumps({n: hashlib.sha256((out / n).read_bytes()).hexdigest()
            for n in ('before-linkscript', 'before-owner.o')}, indent=2)+'\n')
    for name, digest in json.loads(capture.read_text()).items():
        if hashlib.sha256((out / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed four-counter pre-install link capture')
    link = (out / 'before-linkscript').read_text()
    needle = 'build/src/game/'+OWNER+'.c.o(.text);'
    if link.count(needle) != 1:
        raise ValueError('Expected exactly one four-counter text selector')
    for name, obj in (('baseline', out / 'before-owner.o'), ('prediction', padded)):
        script = out / (name+'.ld')
        script.write_text(link.replace(needle, str(obj.relative_to(root / 'conker'))+'(.text);', 1))
        result = subprocess.run(['mips-linux-gnu-ld', '-T', str(script.relative_to(root / 'conker')),
            '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
            '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
            '-o', str((out / ('prelink-'+name+'.elf')).relative_to(root / 'conker'))],
            cwd=root / 'conker', capture_output=True, text=True)
        if result.returncode:
            raise ValueError(result.stderr)
    before = (out / 'before-elf').read_bytes()
    if (out / 'prelink-baseline.elf').read_bytes() != before:
        raise ValueError('Linked inputs do not reproduce the four-counter predecessor')
    predicted = (out / 'prelink-prediction.elf').read_bytes()
    expected = expected_inputs(root, out)
    if predicted != expected['elf']:
        raise ValueError('Four-counter prelink differs from the complete slot/extent prediction')
    hashes = {k: hashlib.sha256(v).hexdigest() for k, v in expected.items()}
    initial = out / 'initial-prediction.json'
    if not initial.exists():
        if {k: hashlib.sha256((root / p).read_bytes()).hexdigest() for k, p in PATHS.items()} != BASELINE:
            raise ValueError('Four-counter prediction must precede installation')
        initial.write_text(json.dumps(hashes, indent=2)+'\n')
    if json.loads(initial.read_text()) != hashes:
        raise ValueError('Changed four-counter initial prediction')
    row = dict(after=hashes, changed_ELF_bytes=sum(a != b for a, b in zip(before, predicted)),
        metadata_exclusions=0, slot_bytes=232, target_guards=0)
    (out / 'prelink-prediction.json').write_text(json.dumps(row, indent=2)+'\n')
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--prelink', action='store_true')
    args = parser.parse_args()
    row = prelink_prediction(args.root, args.root / BUILD) if args.prelink else qualify(args.root, args.root / BUILD)[3]
    print(json.dumps(row, indent=2))


if __name__ == '__main__':
    main()
