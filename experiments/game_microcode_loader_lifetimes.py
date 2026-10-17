"""Fit the microcode loader's record indexing and DMA argument lifetimes."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_microcode_loader as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools import pad_generated_object

BUILD = 'conker/build/game-microcode-loader-lifetimes'
RAW_SHA256 = 'fcb10bf8144b781ba048515f26237c72c7d1aa29d1576c17d1e9819287c09e82'
RELOCATIONS = {at - (4 if at >= 0xFC else 0):rows for at, rows in source.RELOCATIONS.items()}
SCHEDULE = {0x70, 0x88, 0x8C, 0x90, 0x94}
PUBLICATION = {0xAC, 0xB8, 0xBC, 0xC0, 0xC4, 0xC8, 0xCC, 0xD0, 0xD4, 0xD8, 0xDC}
REGISTERS = {0x134, 0x138, 0x140, 0x14C, 0x150, 0x15C, 0x168}
GUARDS = SCHEDULE | PUBLICATION | REGISTERS


def flat_forms():
    for field_type in ('s32', 'u32'):
        declarations = source.DECLARATIONS[source.DECLARATIONS.index('extern struct104'):]
        declarations = '/* Each row is text start/end, then data start/end, relative to the ROM base. */\nextern ' + field_type + ' D_80084078[];\n' + declarations
        body = source.SELECTED.replace('MicrocodeRange49D30 *range;', field_type + ' *range;')
        for field, index in (('textStart', 0), ('textEnd', 1), ('dataStart', 2), ('dataEnd', 3)):
            body = body.replace('range->' + field, 'range[%d]' % index)
        body = body.replace('&D_80084078[variant]', '&D_80084078[variant * 4]').replace(
            '&D_80084078[(s32)(variant + pairedOffset)]', '&D_80084078[(variant + pairedOffset) * 4]')
        yield 'flat-' + field_type, body, declarations
        yield 'flat-' + field_type + '-signed-base', body.replace('(u32)D_800C1060', '(s32)D_800C1060').replace(
            '(u32)D_800BEBB0', '(s32)D_800BEBB0'), declarations


def publication_forms():
    _, body, declarations = next(flat_forms())
    expression = '(u64 *)((u32)D_800C1060 + (s32)(range[1] - range[0]))'
    nested = body.replace('        D_800BEB9C = ' + expression + ';\n', '').replace(
        'D_800BEB9C, range[3]', 'D_800BEB9C = ' + expression + ', range[3]')
    yield 'flat-nested', nested, declarations
    for label, target in (
            ('address', '*(u64 **)&D_800BEB9C'),
            ('array', '((u64 **)&D_800BEB9C)[0]'),
            ('volatile', '*(u64 *volatile *)&D_800BEB9C')):
        yield 'flat-publish-' + label, body.replace('        D_800BEB9C =', '        ' + target + ' ='), declarations
    for named in (False, True):
        candidate = nested if named else body
        candidate = candidate.replace('    s32 variant;', '    s32 dataStart;\n    s32 variant;')
        at = candidate.index('        func_10004514((s32)(range[2]')
        if not named: at = candidate.index('        D_800BEB9C =')
        candidate = candidate[:at] + '        dataStart = range[2];\n' + candidate[at:]
        lo = candidate.index('        func_10004514((s32)(range[2]')
        hi = candidate.index('\n', lo)
        candidate = candidate[:lo] + candidate[lo:hi].replace('range[2]', 'dataStart') + candidate[hi:]
        yield 'flat-start-%d' % named, candidate, declarations


def word_forms():
    _, body, declarations = next(flat_forms())
    expression = '(u64 *)((u32)D_800C1060 + (s32)(range[1] - range[0]))'
    for word_type in ('s32', 'u32'):
        value = '(' + word_type + ')D_800C1060 + (s32)(range[1] - range[0])'
        target = '*(' + word_type + ' *)&D_800BEB9C'
        separate = body.replace('D_800BEB9C = ' + expression, target + ' = ' + value)
        yield 'word-store-' + word_type, separate, declarations
        nested = body.replace('        D_800BEB9C = ' + expression + ';\n', '').replace(
            'D_800BEB9C, range[3]', '(void *)(' + target + ' = ' + value + '), range[3]')
        yield 'word-nested-' + word_type, nested, declarations


def pointer_forms():
    for label, body, declarations in (next(flat_forms()), next(publication_forms())):
        yield label + '-const-view', body.replace('s32 *range;', 'const s32 *range;'), declarations
        pointer_body = body.replace('s32 *range;', 'u8 **range;')
        for field in (0, 2):
            pointer_body = pointer_body.replace('range[%d] + (u32)D_2D4B0' % field,
                '(u32)range[%d] + (u32)D_2D4B0' % field)
        yield label + '-pointer-view', pointer_body, declarations.replace('extern s32 D_80084078[];', 'extern u8 *D_80084078[];')


def global_forms():
    for label, body, declarations in (next(flat_forms()), next(publication_forms())):
        yield label + '-array-global', body, declarations, 'array'
    for label, body, declarations in (next(flat_forms()), next(publication_forms())):
        value = '(s32)((u32)D_800C1060 + (s32)(range[1] - range[0]))'
        if label == 'flat-nested':
            body = body.replace('D_800BEB9C = (u64 *)((u32)D_800C1060 + (s32)(range[1] - range[0]))',
                '(void *)(D_800BEB9C = ' + value + ')')
        else:
            body = body.replace('D_800BEB9C = (u64 *)((u32)D_800C1060 + (s32)(range[1] - range[0]))',
                'D_800BEB9C = ' + value).replace('D_800BEB9C, range[3]', '(void *)D_800BEB9C, range[3]')
        yield label + '-word-global', body, declarations, 'word'


def advisory_forms():
    _, body, declarations = next(flat_forms())
    pointer = '(u64 *)((u32)D_800C1060 + (s32)(range[1] - range[0]))'
    pub = body.replace('    s32 variant;', '    u64 **pub;\n    s32 variant;').replace(
        '        D_800BEB9C = ' + pointer + ';', '        pub = &D_800BEB9C;\n        *pub = ' + pointer + ';').replace(
        'D_800BEB9C, range[3]', '*pub, range[3]')
    yield 'advisory-pub', pub, declarations
    named = body.replace('    s32 variant;', '    u64 *primaryData;\n    s32 variant;').replace(
        '        D_800BEB9C = ' + pointer + ';', '        primaryData = ' + pointer + ';\n        D_800BEB9C = primaryData;').replace(
        'D_800BEB9C, range[3]', 'primaryData, range[3]')
    yield 'advisory-data', named, declarations
    yield 'advisory-byte-pointer', body.replace(pointer, '(u64 *)((u8 *)D_800C1060 + (range[1] - range[0]))'), declarations


def measure(root, out, label, body, declarations, global_shape=None):
    recover = source.recovered_owner
    def owner(before, candidate=None):
        result = recover(before, candidate)
        if global_shape == 'array':
            result = result.replace('D_800BEB9C', 'D_800BEB9C[0]')
            result = result.replace('*D_800BEB9C[0],', '*D_800BEB9C[1],')
        if global_shape == 'word':
            result = result.replace('extern u64 *D_800BEAD0, *D_800BEB9C, *D_80038090, *D_80038094;',
                'extern u64 *D_800BEAD0, *D_80038090, *D_80038094;\nextern s32 D_800BEB9C;')
            result = result.replace('->list.t.ucode_data = D_800BEB9C;', '->list.t.ucode_data = (u64 *)D_800BEB9C;')
        return result
    with patch.object(source, 'recovered_owner', side_effect=owner):
        return source.measure(root, out, label, body, declarations)


def checked_object(obj):
    text, functions, relocations = parse_object(obj); f = functions[source.FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    bindings = {at - f['value']:r for at, r in relocations.items() if f['value'] <= at < f['value'] + f['size']}
    pools = {n:d for n, (_, d) in sections(obj).items()
        if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d}
    if len(raw) != 384 or hashlib.sha256(raw).hexdigest() != RAW_SHA256 or bindings != RELOCATIONS or pools:
        raise ValueError('Unknown flat microcode loader words/bindings/pools')
    return list(struct.unpack('>96I', raw)), bindings


def original(root, out, label='original-loader'):
    from tools.tests import test_game_view_list_setup as assembly
    context = type('OriginalContext', (), dict(root=root, out=out))
    return assembly.ViewListSetupTests.original.__func__(context, label,
        (out / 'before-view_list_caller_original').read_text(), source.FUNCTION)


def normalization(obj, original_obj):
    words, bindings = checked_object(obj)
    text, functions, relocations = parse_object(original_obj); f = functions[source.FUNCTION]
    if f['size'] != 388: raise ValueError('Unknown original microcode extent')
    original_raw = text[f['value']:f['value'] + f['size']]
    wanted = list(struct.unpack('>97I', original_raw))
    target_bindings = {at - f['value']:r for at, r in relocations.items() if f['value'] <= at < f['value'] + f['size']}
    if hashlib.sha256(original_raw).hexdigest() != '52e39770d43f037c6e57a21a8f99113d2ca5b60a62bd4619b665ef5be534c4a4' or (
            hashlib.sha256(json.dumps(target_bindings, sort_keys=True).encode()).hexdigest() !=
            'eb7e177955d8250d810098730137cacc2930906534cc3579392a5b6525b9a37b'):
        raise ValueError('Changed original microcode words/bindings')
    result = {}
    for index, word in enumerate(words):
        at = index * 4; target = at + (4 if at > 0xDC else 0)
        if at not in GUARDS:
            if word != wanted[target // 4] or bindings.get(at, []) != target_bindings.get(target, []):
                raise ValueError('Unexpected microcode change outside the three closed groups: %X' % at)
        else:
            result[at] = dict(expected=word, replacement=wanted[target // 4],
                expected_relocations=bindings.get(at, []), replacement_relocations=target_bindings.get(target, []))
            if at == 0xDC:
                result[at].update(insert_after=wanted[0xE0 // 4], insert_after_relocations=target_bindings.get(0xE0, []))
    if len(result) != 23 or wanted[:3] != words[:3] or wanted[-4:] != words[-4:]:
        raise ValueError('Changed microcode normalization extent/frame/saves')
    return result


def recovered_guards(before, obj, original_obj):
    fields = next(csv.reader(io.StringIO(before.decode())))
    if not before.endswith(b'\n'): raise ValueError('Unknown guard manifest terminator')
    existing = list(csv.DictReader(io.StringIO(before.decode())))
    if any(r['filename'] == source.OWNER and r['function'] == source.FUNCTION for r in existing):
        raise ValueError('Microcode loader already has guards')
    stream = io.StringIO(newline=''); writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    encode = lambda rows:';'.join(kind + ':' + name for kind, name in rows) or '-'
    for at, row in sorted(normalization(obj, original_obj).items()):
        reason = 'call-home schedule' if at in SCHEDULE else 'primary data publication address/schedule' if at in PUBLICATION else 'closed final DMA register cycle'
        writer.writerow(dict(filename=source.OWNER, function=source.FUNCTION, offset='0x%X' % at,
            expected='0x%08X' % row['expected'], replacement='0x%08X' % row['replacement'],
            expected_relocations=encode(row['expected_relocations']), replacement_relocations=encode(row['replacement_relocations']),
            note='Normalize microcode loader ' + reason,
            insert_after='0x%08X' % row['insert_after'] if 'insert_after' in row else '',
            insert_after_relocations=encode(row['insert_after_relocations']) if 'insert_after' in row else '', omit='false'))
    return before + stream.getvalue().encode()


def checked_guards(before, after, obj, original_obj):
    if after != recovered_guards(before, obj, original_obj):
        raise ValueError('Changed microcode normalization manifest')


def qualify(root, out):
    obj, raw, row = measure(root, out, 'qualified', *next(flat_forms())[1:]); checked_object(obj)
    old, diagnostics = source.previous.profiles.compile_owner(root, out,
        (out / 'before-view_list_caller_owner').read_text(), 'neighbor-before', True)
    neighbors = source.previous.same_functions(old, obj, (source.FUNCTION,))
    original_obj = original(root, out)
    guards = out / 'qualified-guards.csv'
    before_guards = (out / 'before-guards').read_bytes()
    guards.write_bytes(recovered_guards(before_guards, obj, original_obj))
    checked_guards(before_guards, guards.read_bytes(), obj, original_obj)
    script = out / 'qualified-padded.s'
    script.write_text(pad_generated_object.emit_padded_assembly(obj, out / 'before-view_list_caller_original',
        word_patches_path=guards, filename=source.OWNER))
    padded = script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(script)], capture_output=True, check=True)
    data, functions = source.build.link_owner(root, out, padded, source.OWNER); f = functions[source.FUNCTION]
    truth = (out / 'before-retail_rom').read_bytes()[source.ROM:source.ROM + 388]
    if diagnostics or row['diagnostics'] or f['size'] != 388 or data[f['value']:f['value'] + 388] != truth:
        raise ValueError('Guarded microcode loader is not byte-exact')
    row.update(byte_exact=True, direct=False, installed=False, new_guards=23, address_materialization_growth_words=1,
        inserted_delay_slot_words=1,
        unchanged_raw_neighbors=neighbors, raw_words=96, normalized_words=97)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, raw, row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--publication', action='store_true')
    parser.add_argument('--words', action='store_true'); parser.add_argument('--pointers', action='store_true')
    parser.add_argument('--globals', action='store_true'); parser.add_argument('--advisory', action='store_true')
    parser.add_argument('--qualify', action='store_true'); args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.qualify:
        print(json.dumps(qualify(root, root / BUILD)[3], indent=2), flush=True); raise SystemExit(0)
    for form in advisory_forms() if args.advisory else global_forms() if args.globals else pointer_forms() if args.pointers else word_forms() if args.words else publication_forms() if args.publication else flat_forms():
        row = measure(root, root / BUILD, *form)[2]
        print(json.dumps({k:row[k] for k in ('label', 'words', 'frame', 'differences', 'diagnostics',
            'raw_sha256', 'caller_words', 'caller_differences')}), flush=True)
