"""Fit real FP value lifetimes without changing the recovered viewport contract."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_viewport_initialize as previous
from tools.experiments import game_view_list_setup as list_setup
from tools.pad_generated_object import parse_object
from tools import pad_c_object

BUILD = 'conker/build/game-viewport-initialize-lifetimes'
OWNER, FUNCTION, ENTRY, ROM, WORDS = previous.OWNER, previous.FUNCTION, previous.ENTRY, previous.ROM, previous.WORDS
PATHS, BASELINE, RELOCATIONS, build = previous.PATHS, previous.BASELINE, previous.RELOCATIONS, previous.build


def replace(body, old, new):
    if body.count(old) != 1:
        raise ValueError('Unknown viewport lifetime source anchor: ' + old)
    return body.replace(old, new, 1)


def aspect_forms():
    body = previous.SELECTED
    old = '''        referenceWidth = (f32)D_800BE638;
        referenceHeight = (f32)D_800BE650;
        VIEW_PROJECTIONS_476D0[index].axisScaleX = (VIEW_PROJECTIONS_476D0[index].width / referenceWidth) *
            ((referenceWidth / referenceHeight) / (VIEW_PROJECTIONS_476D0[index].width / VIEW_PROJECTIONS_476D0[index].height));'''
    choices = {
        'reference-aspect': '''        referenceWidth = (f32)D_800BE638;
        referenceAspect = referenceWidth / (f32)D_800BE650;
        VIEW_PROJECTIONS_476D0[index].axisScaleX = (VIEW_PROJECTIONS_476D0[index].width / referenceWidth) *
            (referenceAspect / (VIEW_PROJECTIONS_476D0[index].width / VIEW_PROJECTIONS_476D0[index].height));''',
        'selected-aspect': '''        referenceWidth = (f32)D_800BE638;
        selectedAspect = VIEW_PROJECTIONS_476D0[index].width / VIEW_PROJECTIONS_476D0[index].height;
        VIEW_PROJECTIONS_476D0[index].axisScaleX = (VIEW_PROJECTIONS_476D0[index].width / referenceWidth) *
            ((referenceWidth / (f32)D_800BE650) / selectedAspect);''',
        'width-fraction': '''        referenceWidth = (f32)D_800BE638;
        widthFraction = VIEW_PROJECTIONS_476D0[index].width / referenceWidth;
        VIEW_PROJECTIONS_476D0[index].axisScaleX = widthFraction *
            ((referenceWidth / (f32)D_800BE650) / (VIEW_PROJECTIONS_476D0[index].width / VIEW_PROJECTIONS_476D0[index].height));''',
    }
    for name, statements in choices.items():
        variable = {'reference-aspect':'referenceAspect', 'selected-aspect':'selectedAspect', 'width-fraction':'widthFraction'}[name]
        selected = replace(body, 'f32 referenceWidth, referenceHeight;', 'f32 referenceWidth, ' + variable + ';')
        yield name, replace(selected, old, statements)
    for label, selected in list(aspect_forms_base()):
        yield label, selected


def aspect_forms_base():
    body = previous.SELECTED
    marker = '        referenceHeight = (f32)D_800BE650;'
    for name, declaration in (('height-branch-local', '        f32 referenceHeight;\n'),
            ('both-dimensions-branch-local', '        f32 referenceWidth, referenceHeight;\n')):
        remove = '    f32 referenceWidth, referenceHeight;\n'
        selected = replace(body, remove, '' if name.startswith('both') else '    f32 referenceWidth;\n')
        selected = replace(selected, '    } else {\n        referenceWidth =', '    } else {\n' + declaration + '        referenceWidth =')
        yield name, selected


def half_forms():
    body = previous.SELECTED
    marker = '    VIEW_PROJECTIONS_476D0[index].extentX = '
    for variable in ('angle', 'sine', 'referenceWidth', 'referenceHeight'):
        selected = replace(body, marker, '    ' + variable + ' = 0.5f;\n' + marker)
        for axis in ('X', 'Y'):
            selected = replace(selected,
                'VIEW_PROJECTIONS_476D0[index].extent' + axis + ' = VIEW_PROJECTIONS_476D0[index].' + ('width' if axis == 'X' else 'height') + ' * 0.5f;',
                'VIEW_PROJECTIONS_476D0[index].extent' + axis + ' = VIEW_PROJECTIONS_476D0[index].' + ('width' if axis == 'X' else 'height') + ' * ' + variable + ';')
        yield 'half-in-' + variable, selected


def three_value_forms():
    body = previous.SELECTED
    body = replace(body, 'f32 referenceWidth, referenceHeight;', 'f32 referenceWidth, referenceAspect, selectedAspect;')
    old = '''        referenceWidth = (f32)D_800BE638;
        referenceHeight = (f32)D_800BE650;
        VIEW_PROJECTIONS_476D0[index].axisScaleX = (VIEW_PROJECTIONS_476D0[index].width / referenceWidth) *
            ((referenceWidth / referenceHeight) / (VIEW_PROJECTIONS_476D0[index].width / VIEW_PROJECTIONS_476D0[index].height));'''
    for order in ('reference-first', 'selected-first'):
        statements = ['        referenceAspect = referenceWidth / (f32)D_800BE650;',
            '        selectedAspect = VIEW_PROJECTIONS_476D0[index].width / VIEW_PROJECTIONS_476D0[index].height;']
        if order == 'selected-first': statements.reverse()
        new = '        referenceWidth = (f32)D_800BE638;\n' + '\n'.join(statements) + '''
        VIEW_PROJECTIONS_476D0[index].axisScaleX = (VIEW_PROJECTIONS_476D0[index].width / referenceWidth) *
            (referenceAspect / selectedAspect);'''
        selected = replace(body, old, new)
        yield 'three-values-' + order, selected
        yield 'three-values-' + order + '-sine-first', replace(selected,
            '    f32 angle;\n    f32 sine;', '    f32 sine;\n    f32 angle;')


def sequenced_trig_forms():
    for name, body in [('baseline', previous.SELECTED), *list(three_value_forms())[:2]]:
        for value in ('angle', 'referenceWidth', 'referenceHeight'):
            if value == 'referenceHeight' and name != 'baseline': continue
            selected = body
            for axis in ('X', 'Y'):
                needle = '    VIEW_PROJECTIONS_476D0[index].projectionScale' + axis + ' = '
                selected = replace(selected, needle, '    ' + value + ' = cosf(angle);\n' + needle)
                selected = replace(selected, '.extent' + axis + ' * cosf(angle)', '.extent' + axis + ' * ' + value)
            yield 'sequence-' + name + '-' + value, selected


def address_forms():
    body = dict(sequenced_trig_forms())['sequence-three-values-reference-first-sine-first-angle']
    old = '''    func_1501AF44(&VIEW_PROJECTIONS_476D0[index].left, &VIEW_PROJECTIONS_476D0[index].top,
        &VIEW_PROJECTIONS_476D0[index].right, &VIEW_PROJECTIONS_476D0[index].bottom);'''
    for name, pointer in (
            ('word-index-first', '(ViewProjection476D0 *)((u32)index * 0x180 + (u32)D_800BE628)'),
            ('signed-index-first', '(ViewProjection476D0 *)(index * 0x180 + D_800BE628)'),
            ('byte-base-first', '(ViewProjection476D0 *)((u8 *)D_800BE628 + index * 0x180)')):
        args = ['&(' + pointer + ')->' + field for field in ('left', 'top', 'right', 'bottom')]
        new = '    func_1501AF44(' + ',\n        '.join(args) + ');'
        yield name, replace(body, old, new)


SELECTED = re.sub(r'\bangle\b', 'trigValue', dict(address_forms())['word-index-first'])
RAW_SHA256 = 'a1348f447d175e2d072219ef8cecaad9ae4728f797816ecb5e5d7d09268732d4'
SERIALIZATION = (
    (('D_8008630C', 'D_800894F0'), (1, 0),
        ((0x8008630C, 0, 16, 0, 65521), (0x800894F0, 0, 16, 0, 65521))),
    (('D_8003CA48', 'D_800C3D48'), (1, 0),
        ((0x8003CA48, 0, 16, 0, 65521), (0x800C3D48, 0, 16, 0, 65521))),
)


def freeze(root, out):
    from tools.tests import viewport_initialize_checkpoint as checkpoint
    out.mkdir(parents=True, exist_ok=True)
    for key, relative in PATHS.items():
        current = (root / relative).read_bytes()
        if key in checkpoint.AFTER and hashlib.sha256(current).hexdigest() == checkpoint.AFTER[key]:
            current = checkpoint.fixture(root, 'before', key)
        if hashlib.sha256(current).hexdigest() != BASELINE[key]:
            raise ValueError('Unknown viewport initializer input: ' + key)
        target = out / ('before-' + key)
        if not target.exists(): target.write_bytes(current)
        if target.read_bytes() != current: raise ValueError('Changed viewport initializer fixture: ' + key)


def measure(root, label, body, out=None):
    with patch.object(previous, 'freeze', freeze):
        return previous.measure(root, root / BUILD if out is None else out, label, body)


def recovered_owner(before):
    return previous.recovered_owner(before, SELECTED)


def checked_object(obj):
    text, functions, relocations = parse_object(obj); f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    bindings = {at - f['value']:r for at, r in relocations.items() if f['value'] <= at < f['value'] + f['size']}
    pools = {n:d for n, (_, d) in previous.sections(obj).items()
        if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d}
    if len(raw) != 1492 or hashlib.sha256(raw).hexdigest() != RAW_SHA256 or bindings != RELOCATIONS or pools:
        raise ValueError('Unknown direct viewport initializer words/bindings/pools')
    return raw


def qualify(root, out):
    obj, words, row = measure(root, 'qualified-direct', SELECTED, out); checked_object(obj)
    before = (out / 'before-frustum_owner').read_text()
    old, diag = build.compile_owner(root, out, before, 'neighbor-before')
    a, b = parse_object(old), parse_object(obj)
    if diag or row['diagnostics'] or set(a[1]) != set(b[1]): raise ValueError('Changed viewport owner diagnostics/function set')
    rel = lambda p, f:{at - f['value']:r for at, r in p[2].items() if f['value'] <= at < f['value'] + f['size']}
    for name, f in a[1].items():
        if name == FUNCTION: continue
        g = b[1][name]
        if a[0][f['value']:f['value'] + f['size']] != b[0][g['value']:g['value'] + g['size']] or rel(a, f) != rel(b, g):
            raise ValueError('Changed viewport owner neighbor: ' + name)
    alternate, diag = list_setup.compile_owner(root, out, recovered_owner(before), 'qualified-nounroll', True)
    if diag: raise ValueError('Changed viewport no-unroll diagnostics')
    list_setup.checked_object(alternate)
    assembly = out / 'qualified-padded.s'
    assembly.write_text(pad_c_object.emit_padded_assembly(obj, root / PATHS['layout'], OWNER,
        word_patches_path=out / 'before-guards', function_objects={list_setup.FUNCTION:alternate}))
    padded = assembly.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(assembly)], capture_output=True, check=True)
    data, functions = build.link_owner(root, out, padded, OWNER); f = functions[FUNCTION]
    if f['size'] != 1492 or data[f['value']:f['value'] + 1492] != (out / 'before-retail_rom').read_bytes()[ROM:ROM + 1492]:
        raise ValueError('Direct viewport slot differs')
    row.update(byte_exact=True, new_guards=0, unchanged_neighbors=len(a[1]) - 1)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, words, row


def expected_inputs(root, out):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    before = (out / 'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']: raise ValueError('Changed viewport predecessor image')
    row = next(r for r in symbol_rows(before) if r[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 28): raise ValueError('Unknown viewport predecessor extent')
    data = bytearray(before); at = elf_slot_offset(before, ENTRY, 1492)
    data[at:at + 1492] = (out / 'before-retail_rom').read_bytes()[ROM:ROM + 1492]
    struct.pack_into('>I', data, row[0] + 8, 1492)
    from tools.tests import test_game_actor_burst_packet_match as serialization
    with patch.object(serialization, 'SERIALIZATION', SERIALIZATION):
        serialization.apply_burst_symbol_serialization(data)
    return dict(elf=bytes(data), frustum_owner=recovered_owner((out / 'before-frustum_owner').read_text()).encode())


def prelink_prediction(root, out):
    _, padded, _, _ = qualify(root, out)
    live = lambda:{k:hashlib.sha256((root / p).read_bytes()).hexdigest() for k, p in PATHS.items()}
    capture = out / 'link-inputs.json'
    if not capture.exists():
        if live() != BASELINE: raise ValueError('Viewport capture must precede installation')
        for name, path in (('before-linkscript', 'conker/build/conker.ld'), ('before-owner.o', 'conker/build/src/' + OWNER + '.c.o')):
            (out / name).write_bytes((root / path).read_bytes())
        capture.write_text(json.dumps({n:hashlib.sha256((out / n).read_bytes()).hexdigest()
            for n in ('before-linkscript', 'before-owner.o')}, indent=2) + '\n')
    for name, digest in json.loads(capture.read_text()).items():
        if hashlib.sha256((out / name).read_bytes()).hexdigest() != digest: raise ValueError('Changed viewport link capture')
    link = (out / 'before-linkscript').read_text(); needle = 'build/src/' + OWNER + '.c.o(.text);'
    if link.count(needle) != 1: raise ValueError('Unknown viewport link selector')
    for label, obj in (('baseline', out / 'before-owner.o'), ('prediction', padded)):
        script = out / (label + '.ld'); script.write_text(link.replace(needle, str(obj.relative_to(root / 'conker')) + '(.text);', 1))
        subprocess.run(['mips-linux-gnu-ld', '-T', str(script.relative_to(root / 'conker')),
            '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
            '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
            '-o', str((out / ('prelink-' + label + '.elf')).relative_to(root / 'conker'))], cwd=root / 'conker', capture_output=True, check=True)
    if (out / 'prelink-baseline.elf').read_bytes() != (out / 'before-elf').read_bytes(): raise ValueError('Viewport predecessor not reproduced')
    expected = expected_inputs(root, out); actual = (out / 'prelink-prediction.elf').read_bytes()
    if actual != expected['elf']: raise ValueError('Viewport link differs outside its slot/extent prediction')
    hashes = {k:hashlib.sha256(v).hexdigest() for k, v in expected.items()}; initial = out / 'initial-prediction.json'
    if not initial.exists():
        if live() != BASELINE: raise ValueError('Viewport prediction must precede installation')
        initial.write_text(json.dumps(hashes, indent=2) + '\n')
    if json.loads(initial.read_text()) != hashes: raise ValueError('Changed first viewport prediction')
    row = dict(after=hashes, changed_ELF_bytes=sum(a != b for a, b in zip((out / 'before-elf').read_bytes(), actual)),
        body_bytes=1492, new_guards=0, exact_symbol_groups=2, metadata_exclusions=0)
    (out / 'prelink-prediction.json').write_text(json.dumps(row, indent=2) + '\n'); return row


def installation_patch(root, out):
    expected = expected_inputs(root, out)
    if json.loads((out / 'initial-prediction.json').read_text()) != {k:hashlib.sha256(v).hexdigest() for k, v in expected.items()}:
        raise ValueError('Changed viewport installation prediction')
    path = root / PATHS['frustum_owner']; before, after = path.read_bytes(), expected['frustum_owner']
    if hashlib.sha256(before).hexdigest() != BASELINE['frustum_owner']: raise ValueError('Changed viewport source before installation')
    diff = list(difflib.unified_diff(before.decode().splitlines(), after.decode().splitlines(), n=3, lineterm=''))
    return '*** Begin Patch\n*** Update File: ' + str(path) + '\n' + '\n'.join(
        '@@' if line.startswith('@@') else line for line in diff[2:]) + '\n*** End Patch\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--half', action='store_true')
    parser.add_argument('--three-values', action='store_true')
    parser.add_argument('--sequence-trig', action='store_true')
    parser.add_argument('--addresses', action='store_true')
    parser.add_argument('--filter', default='')
    parser.add_argument('--selected', action='store_true')
    parser.add_argument('--prelink', action='store_true')
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args(); root = Path(__file__).resolve().parents[2]
    if args.prelink:
        print(json.dumps(prelink_prediction(root, root / BUILD), indent=2), flush=True); raise SystemExit(0)
    if args.prepare:
        print(installation_patch(root, root / BUILD), end=''); raise SystemExit(0)
    for label, body in ([('selected', SELECTED)] if args.selected else address_forms() if args.addresses else sequenced_trig_forms() if args.sequence_trig else three_value_forms() if args.three_values else half_forms() if args.half else aspect_forms()):
        if args.filter not in label: continue
        row = measure(root, label, body)[2]
        print(json.dumps({k:row[k] for k in ('label', 'words', 'frame', 'differences', 'diagnostics', 'raw_sha256', 'pools')}), flush=True)
