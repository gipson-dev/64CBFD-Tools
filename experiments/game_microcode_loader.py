"""Recover paired microcode loads, signed cache bytes and ordered DMA packets."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_graphics_task_submit as previous
from tools.tests import graphics_task_submit_checkpoint as checkpoint
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_classifier_candidates import sections
from tools import pad_generated_object

BUILD = 'conker/build/game-microcode-loader'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_49D30', 'func_1501CC3C', 0x1501CC3C, 0x4A0EC, 97
PATHS = dict(previous.PATHS, dma_owner='conker/src/init_4470.c')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    dma_owner='748a12c58998a503d3933844a433455078c4675155cc5da9155e9860e34e4bcb')
build = previous.build
DECLARATIONS = '''typedef struct {
    u32 textStart, textEnd, dataStart, dataEnd;
} MicrocodeRange49D30;
extern MicrocodeRange49D30 D_80084078[];
extern struct104 *D_800B0DF0;
extern s32 D_800BEB98;
extern s8 D_80084070, D_80084074;
extern u8 D_2D4B0[];
s32 func_10004514(s32 devAddr, void *dramAddr, u32 size, s32 block);

'''
INITIAL = '''/* Load both selected microcode pairs when their signed cache bytes differ. */
void func_1501CC3C(void) {
    u8 variant;
    s32 pairedOffset;
    MicrocodeRange49D30 *range;
    u32 offset;

    pairedOffset = 4;
    variant = D_800B0DF0->pad2B[0];
    if ((s32)variant >= 2) {
        variant -= 2;
        pairedOffset = 0;
    }
    if (D_800BEB98 == 1) {
        variant += 2;
    }
    range = &D_80084078[variant];
    if (variant != D_80084070 || pairedOffset != D_80084074) {
        offset = range->textStart;
        func_10004514((s32)(offset + (u32)D_2D4B0), D_800C1060, range->textEnd - offset, 1);
        D_800BEB9C = (u64 *)((u32)D_800C1060 + (range->textEnd - range->textStart));
        offset = range->dataStart;
        func_10004514((s32)(offset + (u32)D_2D4B0), D_800BEB9C, range->dataEnd - offset, 1);
        D_80084070 = variant;
        range = &D_80084078[variant + pairedOffset];
        D_80084074 = pairedOffset;
        offset = range->textStart;
        func_10004514((s32)(offset + (u32)D_2D4B0), D_800BEBB0, range->textEnd - offset, 1);
        D_800BEAD0 = (u64 *)((u32)D_800BEBB0 + (range->textEnd - range->textStart));
        offset = range->dataStart;
        func_10004514((s32)(offset + (u32)D_2D4B0), D_800BEAD0, range->dataEnd - offset, 1);
    }
}'''


def forms():
    for variant_type in ('s32', 'u32'):
        for offset_type in ('u32', 's32'):
            yield variant_type + '-' + offset_type, INITIAL.replace('    u8 variant;', '    ' + variant_type + ' variant;').replace(
                '    u32 offset;', '    ' + offset_type + ' offset;')


def inline_forms():
    body = dict(forms())['s32-u32'].replace('    u32 offset;\n', '')
    for field in ('text', 'data'):
        body = body.replace('        offset = range->' + field + 'Start;\n', '')
        for destination in (('D_800C1060', 'D_800BEBB0') if field == 'text' else ('D_800BEB9C', 'D_800BEAD0')):
            body = body.replace('func_10004514((s32)(offset + (u32)D_2D4B0), ' + destination + ', range->' + field + 'End - offset, 1);',
                'func_10004514((s32)(range->' + field + 'Start + (u32)D_2D4B0), ' + destination + ', range->' + field + 'End - range->' + field + 'Start, 1);')
    yield 'inline', body
    yield 'inline-pointers', body.replace('(u64 *)((u32)D_800C1060 + (range->textEnd - range->textStart))',
        '(u64 *)((u8 *)D_800C1060 + (range->textEnd - range->textStart))').replace(
        '(u64 *)((u32)D_800BEBB0 + (range->textEnd - range->textStart))',
        '(u64 *)((u8 *)D_800BEBB0 + (range->textEnd - range->textStart))')
    named = body.replace('    MicrocodeRange49D30 *range;', '    MicrocodeRange49D30 *range;\n    u32 textBytes;')
    for code, data in (('D_800C1060', 'D_800BEB9C'), ('D_800BEBB0', 'D_800BEAD0')):
        named = named.replace('        ' + data + ' = ', '        textBytes = range->textEnd - range->textStart;\n        ' + data + ' = ').replace(
            '(u32)' + code + ' + (range->textEnd - range->textStart)', '(u32)' + code + ' + textBytes')
    yield 'inline-named-size', named
    yield 'inline-offset-first', body.replace('(u32)D_800C1060 + (range->textEnd - range->textStart)',
        '(range->textEnd - range->textStart) + (u32)D_800C1060').replace(
        '(u32)D_800BEBB0 + (range->textEnd - range->textStart)', '(range->textEnd - range->textStart) + (u32)D_800BEBB0')


def grouped_forms():
    body = dict(inline_forms())['inline']
    body = body.replace('    pairedOffset = 4;\n', '').replace(
        '        pairedOffset = 0;\n    }', '        pairedOffset = 0;\n    } else {\n        pairedOffset = 4;\n    }')
    body = body.replace('variant + pairedOffset', '(s32)(variant + pairedOffset)')
    yield 'explicit-else', body
    for cast in ('s32', 'u32'):
        grouped = body.replace('(range->textEnd - range->textStart)', '(' + cast + ')(range->textEnd - range->textStart)')
        yield 'grouped-' + cast, grouped
    yield 'signed-fields', body.replace('range->textEnd', '(s32)range->textEnd').replace('range->textStart', '(s32)range->textStart')


def lifetime_forms():
    body = dict(grouped_forms())['grouped-s32']
    for paired in (False, True):
        candidate = body
        if paired:
            candidate = candidate.replace('        range = &D_80084078[(s32)(variant + pairedOffset)];',
                '        variant += pairedOffset;\n        range = &D_80084078[variant];')
        expression = '(u64 *)((u32)D_800C1060 + (s32)(range->textEnd - range->textStart))'
        nested = candidate.replace('        D_800BEB9C = ' + expression + ';\n', '').replace(
            'D_800BEB9C, range->dataEnd', 'D_800BEB9C = ' + expression + ', range->dataEnd')
        yield 'nested-%d' % paired, nested
        yield 'paired-%d' % paired, candidate


def local_forms():
    body = dict(grouped_forms())['grouped-s32']
    body = body.replace('    MicrocodeRange49D30 *range;', '    MicrocodeRange49D30 *range;\n    u64 *data;')
    for code, destination in (('D_800C1060', 'D_800BEB9C'), ('D_800BEBB0', 'D_800BEAD0')):
        statement = '        ' + destination + ' = '
        body = body.replace(statement, '        data = ').replace(
            '        func_10004514((s32)(range->dataStart + (u32)D_2D4B0), ' + destination + ',',
            statement + 'data;\n        func_10004514((s32)(range->dataStart + (u32)D_2D4B0), data,')
    for address in (False, True):
        for starts in (False, True):
            candidate = body
            if address:
                candidate = candidate.replace('&D_80084078[variant]', '(MicrocodeRange49D30 *)((s32)D_80084078 + variant * 16)').replace(
                    '&D_80084078[(s32)(variant + pairedOffset)]', '(MicrocodeRange49D30 *)((s32)D_80084078 + (variant + pairedOffset) * 16)')
            if starts:
                candidate = candidate.replace('    u64 *data;', '    u64 *data;\n    u32 primaryDataStart;\n    u32 pairedDataStart;')
                for name, destination in (('primaryDataStart', 'D_800BEB9C'), ('pairedDataStart', 'D_800BEAD0')):
                    pos = candidate.index('        data = ', candidate.index('D_800BEBB0, range->textEnd') if destination == 'D_800BEAD0' else 0)
                    candidate = candidate[:pos] + '        ' + name + ' = range->dataStart;\n' + candidate[pos:]
                    pos = candidate.index('        ' + destination + ' = data;')
                    end = candidate.index('\n', candidate.index('        func_10004514', pos))
                    candidate = candidate[:pos] + candidate[pos:end].replace('range->dataStart', name) + candidate[end:]
            yield 'local-%d-%d' % (address, starts), candidate


def register_forms():
    for label, body in local_forms():
        body = body.replace('    u64 *data;', '    register u64 *data;').replace(
            '    u32 primaryDataStart;', '    register u32 primaryDataStart;').replace(
            '    u32 pairedDataStart;', '    register u32 pairedDataStart;')
        yield 'register-' + label, body
        if label.endswith('-1'):
            body = body.replace('    register u64 *data;', '    register u64 *data;\n    register u64 **primaryDataSlot;').replace(
                '        D_800BEB9C = data;', '        primaryDataSlot = &D_800BEB9C;\n        *primaryDataSlot = data;')
            yield 'slot-' + label, body


def scoped_forms():
    for name in ('local-0-0', 'local-1-0', 'local-0-1', 'local-1-1'):
        body = dict(local_forms())[name]
        declarations = [line for line in body.splitlines() if 'u64 *data;' in line or 'DataStart;' in line]
        for line in declarations: body = body.replace(line + '\n', '')
        marker = '    if (variant != D_80084070 || pairedOffset != D_80084074) {\n'
        body = body.replace(marker, marker + '\n'.join('    ' + line for line in declarations) + '\n')
        yield 'scoped-' + name, body
        yield 'byte-' + name, body.replace('u64 *data;', 'u8 *data;').replace('data = (u64 *)', 'data = (u8 *)').replace(
            '= data;', '= (u64 *)data;')


def ordering_forms():
    body = dict(local_forms())['local-1-0']
    old = '    s32 variant;\n    s32 pairedOffset;\n    MicrocodeRange49D30 *range;\n    u64 *data;'
    for label, declarations in (
            ('data-first', 'u64 *data;s32 variant;s32 pairedOffset;MicrocodeRange49D30 *range'),
            ('range-first', 'MicrocodeRange49D30 *range;u64 *data;s32 variant;s32 pairedOffset'),
            ('data-middle', 's32 variant;s32 pairedOffset;u64 *data;MicrocodeRange49D30 *range'),
            ('range-middle', 's32 variant;MicrocodeRange49D30 *range;s32 pairedOffset;u64 *data')):
        candidate = body.replace(old, '\n'.join('    ' + line + ';' for line in declarations.split(';')))
        yield label, candidate
    yield 'word-data', body.replace('u64 *data;', 's32 data;').replace('data = (u64 *)', 'data = (s32)').replace('= data;', '= (u64 *)data;').replace(', data,', ', (void *)data,')


def table_forms():
    body = dict(grouped_forms())['grouped-s32']
    body = body.replace('&D_80084078[variant]', '(MicrocodeRange49D30 *)((s32)D_80084078 + variant * 16)').replace(
        '&D_80084078[(s32)(variant + pairedOffset)]', '(MicrocodeRange49D30 *)((s32)D_80084078 + (variant + pairedOffset) * 16)')
    yield 'signed-table', body, DECLARATIONS.replace('u32 textStart', 's32 textStart')
    yield 'pointer-table', body.replace('range->textStart + (u32)D_2D4B0', '(u32)range->textStart + (u32)D_2D4B0').replace(
        'range->dataStart + (u32)D_2D4B0', '(u32)range->dataStart + (u32)D_2D4B0'), DECLARATIONS.replace(
        'u32 textStart, textEnd, dataStart, dataEnd;', 'u8 *textStart, *textEnd, *dataStart, *dataEnd;')


SELECTED = dict(grouped_forms())['grouped-s32']
RAW_SHA256 = 'e4b491e01ea802d65e7e042abe7a8a42a84923d6b00f833fbf35a15ecd149e0f'
RELOCATIONS = {}
for hi, lo, symbol in (
        (0x0C, 0x10, 'D_800B0DF0'), (0x18, 0x40, 'D_800BEB98'),
        (0x20, 0x58, 'D_80084070'), (0x24, 0x6C, 'D_80084074'),
        (0x30, 0x48, 'D_80084078'), (0x50, 0x68, 'D_2D4B0'),
        (0x80, 0x84, 'D_800C1060'), (0xA8, 0xAC, 'D_800C1060'),
        (0xB8, 0xC8, 'D_800BEB9C'), (0xE8, 0xF0, 'D_80084070'),
        (0xFC, 0x10C, 'D_80084074'), (0xEC, 0x104, 'D_80084078'),
        (0x118, 0x11C, 'D_800BEBB0'), (0x138, 0x13C, 'D_800BEBB0'),
        (0x148, 0x158, 'D_800BEAD0')):
    RELOCATIONS[hi] = [('R_MIPS_HI16', symbol)]
    RELOCATIONS[lo] = [('R_MIPS_LO16', symbol)]
for at in (0x9C, 0xD8, 0x12C, 0x168):
    RELOCATIONS[at] = [('R_MIPS_26', 'func_10004514')]


def freeze(root, out):
    from tools.tests import microcode_loader_checkpoint as current
    out.mkdir(parents=True, exist_ok=True)
    for key, relative in PATHS.items():
        data = current.previous_input((root / relative).read_bytes(), relative, root)
        if hashlib.sha256(data).hexdigest() != BASELINE[key]: raise ValueError('Unknown microcode loader input: ' + key)
        target = out / ('before-' + key)
        if not target.exists(): target.write_bytes(data)
        if target.read_bytes() != data: raise ValueError('Changed microcode loader fixture: ' + key)


def recovered_owner(before, body=None):
    body = SELECTED if body is None else body
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1501CC3C() {\n    return 0;\n}': raise ValueError('Unknown microcode loader predecessor')
    result = before[:lo] + body + before[hi:]
    old = 's32 func_1501CC3C(void);'
    if result.count(old) != 1 or 'MicrocodeRange49D30' in before: raise ValueError('Unknown microcode loader declarations')
    return result.replace(old, DECLARATIONS + 'void func_1501CC3C(void);', 1)


def measure(root, out, label, body, declarations=None):
    freeze(root, out)
    owner = recovered_owner((out / 'before-view_list_caller_owner').read_text(), body)
    if declarations is not None: owner = owner.replace(DECLARATIONS, declarations)
    obj, diagnostics = previous.profiles.compile_owner(root, out,
        owner, label, True)
    text, functions, relocations = parse_object(obj); f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    data, placed = build.link_owner(root, out, obj, OWNER)
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, placed[FUNCTION]['value']))
    truth = list(struct.unpack_from('>97I', (out / 'before-retail_rom').read_bytes(), ROM))
    caller = functions['func_1501C880']; start = placed['func_1501C880']['value']
    caller_bytes = data[start:start + caller['size']]
    row = dict(label=label, words=len(words), frame=(-words[0]) & 65535, diagnostics=diagnostics,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        bindings={at - f['value']:r for at, r in relocations.items() if f['value'] <= at < f['value'] + f['size']},
        pools={n:d.hex() for n, (_, d) in sections(obj).items()
            if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d},
        caller_words=caller['size'] // 4,
        caller_differences=sum(a != b for a,b in zip(struct.unpack('>%dI' % (len(caller_bytes)//4), caller_bytes),
            struct.unpack_from('>239I', (out / 'before-retail_rom').read_bytes(), previous.ROM))),
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b)
            for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def checked_object(obj):
    text, functions, relocations = parse_object(obj); f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    bindings = {at - f['value']:r for at, r in relocations.items() if f['value'] <= at < f['value'] + f['size']}
    pools = {n:d for n, (_, d) in sections(obj).items()
        if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d}
    if len(raw) != 388 or hashlib.sha256(raw).hexdigest() != RAW_SHA256 or bindings != RELOCATIONS or pools:
        raise ValueError('Unknown microcode research candidate words/bindings/pools')
    return raw


def qualify(root, out):
    """Qualify a non-installed research candidate, not a production match."""
    obj, words, row = measure(root, out, 'qualified', SELECTED); checked_object(obj)
    old, diagnostics = previous.profiles.compile_owner(root, out,
        (out / 'before-view_list_caller_owner').read_text(), 'neighbor-before', True)
    neighbors = previous.same_functions(old, obj, (FUNCTION,))
    script = out / 'qualified-padded.s'
    script.write_text(pad_generated_object.emit_padded_assembly(obj, out / 'before-view_list_caller_original',
        word_patches_path=out / 'before-guards', filename=OWNER))
    padded = script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(script)], capture_output=True, check=True)
    data, functions = build.link_owner(root, out, padded, OWNER); f = functions[FUNCTION]
    emitted = list(struct.unpack_from('>97I', data, f['value']))
    if diagnostics or row['diagnostics'] or row['pools'] or row['words'] != 97 or row['frame'] != 48 or (
            row['differences'] != 44 or row['caller_words'] != 239 or row['caller_differences'] or
            f['size'] != 388 or emitted != words):
        raise ValueError('Changed microcode research checkpoint')
    row.update(byte_exact=False, installed=False, new_guards=0, unchanged_raw_neighbors=neighbors,
        immutable_inputs=len(PATHS), normal_padder_preserves_candidate=True)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, words, row


if __name__ == '__main__':
    screens = dict(initial=lambda:[('initial', INITIAL)], forms=forms, inline=inline_forms, grouped=grouped_forms,
        lifetimes=lifetime_forms, locals=local_forms, registers=register_forms, scopes=scoped_forms,
        ordering=ordering_forms, tables=table_forms)
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--screen', choices=screens)
    actions.add_argument('--qualify', action='store_true'); args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.qualify:
        print(json.dumps(qualify(root, root / BUILD)[3], indent=2), flush=True); raise SystemExit(0)
    for form in screens[args.screen]() if args.screen else [('selected', SELECTED)]:
        label, body, *declarations = form
        row = measure(root, root / BUILD, label, body, *declarations)[2]
        print(json.dumps({k:row[k] for k in ('label', 'words', 'frame', 'differences', 'diagnostics', 'raw_sha256',
            'pools', 'caller_words', 'caller_differences')}), flush=True)
