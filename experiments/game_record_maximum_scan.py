"""Recover the frame-free priority record maximum without changing production inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_microcode_loader_installation as previous
from tools.tests import microcode_loader_checkpoint as checkpoint
from tools.experiments.game_view_list_setup import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-record-maximum-scan'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_49D30', 'func_1501CE54', 0x1501CE54, 0x4A304, 105
PATHS = dict(previous.PATHS)
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER)
build = previous.source.build
DECLARATIONS = '''typedef struct {
    u8 pad00[0xA];
    s16 maximum;
    u8 pad0C[6];
    s16 overrideValue;
} RecordMaximum49D30;
extern s32 D_800C3640[];
extern RecordMaximum49D30 *D_800C3688[][30];
extern u16 *D_800C35D0[];
extern u8 *D_800C3778[][30];

'''
INITIAL = '''/* Prefer an explicit override or primary maximum before scanning fallback tails. */
void func_1501CE54(s32 slot) {
    s32 *maximum;
    s32 count;
    u16 *primary;
    s32 found;
    s32 i;
    s32 offset;
    u16 *enabled;
    s32 value;
    u16 entries;

    maximum = &D_800C3640[slot];
    *maximum = 0;
    count = D_800C363A[slot];
    if (count != 0) {
        primary = D_800C35D8[slot];
        if (primary[0] >= 4) {
            value = D_800C3688[slot][0]->overrideValue;
            if (value != -9999) {
                *maximum = value;
                return;
            }
        }
        found = 0;
        i = 0;
        offset = 0;
        if (count > 0) {
            enabled = D_800C35C8[slot];
            do {
                if (*enabled++ != 0 && *(u16 *)((u8 *)primary + offset) != 0) {
                    value = D_800C3688[slot][i]->maximum;
                    if (*maximum < value) {
                        *maximum = value;
                        found = 1;
                    }
                }
                i++;
                offset += 2;
            } while (i < count);
        }
        if (!found) {
            i = 0;
            offset = 0;
            if (count > 0) {
                enabled = D_800C35C8[slot];
                do {
                    if (*enabled++ != 0) {
                        entries = *(u16 *)((u8 *)D_800C35D0[slot] + offset);
                        if (entries != 0) {
                            value = *(s16 *)(D_800C3778[slot][i] + entries * 8 - 2);
                            if (*maximum < value) {
                                *maximum = value;
                            }
                        }
                    }
                    i++;
                    offset += 2;
                } while (i < count);
            }
        }
    }
}'''
def forms():
    body = INITIAL.replace('    s32 value;', '    s32 overrideValue;\n    s32 primaryValue;\n    s32 fallbackValue;\n    u16 active;')
    lo = body.index('        if (primary[0]'); hi = body.index('        found = 0;')
    body = body[:lo] + body[lo:hi].replace('value', 'overrideValue') + body[hi:]
    lo = body.index('        found = 0;'); hi = body.index('        if (!found)')
    body = body[:lo] + body[lo:hi].replace('value', 'primaryValue') + body[hi:]
    lo = body.index('        if (!found)')
    body = body[:lo] + body[lo:].replace('value', 'fallbackValue')
    body = body.replace('        offset = 0;\n        if (count > 0) {\n            enabled = D_800C35C8[slot];',
        '        if (count > 0) {\n            enabled = D_800C35C8[slot];\n            offset = 0;').replace(
        '            offset = 0;\n            if (count > 0) {\n                enabled = D_800C35C8[slot];',
        '            if (count > 0) {\n                enabled = D_800C35C8[slot];\n                offset = 0;')
    body = body.replace('if (*enabled++ != 0', 'active = *enabled++;\n                if (active != 0', 1)
    body = body.replace('if (*enabled++ != 0', 'active = *enabled++;\n                    if (active != 0', 1)
    yield 'named-values', body
    yield 'byte-count', body.replace('    s32 count;', '    u8 count;').replace('count > 0', '(s32)count > 0').replace('i < count', 'i < (s32)count')
    split = body.replace('    s32 i;', '    s32 i;\n    s32 fallbackIndex;').replace(
        '    s32 offset;', '    s32 offset;\n    s32 fallbackOffset;').replace('    u16 *enabled;', '    u16 *enabled;\n    u16 *fallbackEnabled;')
    lo = split.index('        if (!found)')
    split = split[:lo] + split[lo:].replace('i = 0', 'fallbackIndex = 0').replace('[slot][i]', '[slot][fallbackIndex]').replace(
        'i++;', 'fallbackIndex++;').replace('i < count', 'fallbackIndex < count').replace('offset', 'fallbackOffset').replace('enabled', 'fallbackEnabled')
    yield 'split-cursors', split
    yield 'split-byte-count', split.replace('    s32 count;', '    u8 count;').replace('count > 0', '(s32)count > 0').replace(
        'i < count', 'i < (s32)count').replace('fallbackIndex < count', 'fallbackIndex < (s32)count')


def loop_forms():
    body = dict(forms())['named-values']
    for style in ('while', 'for'):
        candidate = body.replace('do {', 'while (i < count) {' if style == 'while' else 'for (; i < count; i++, offset += 2) {')
        candidate = candidate.replace('} while (i < count);', '}')
        if style == 'for':
            candidate = candidate.replace('                i++;\n                offset += 2;\n', '').replace(
                '                    i++;\n                    offset += 2;\n', '')
        yield style + '-loops', candidate
        narrow = candidate.replace('s32 overrideValue;', 's16 overrideValue;').replace('s32 primaryValue;', 's16 primaryValue;').replace(
            's32 fallbackValue;', 's16 fallbackValue;')
        yield style + '-narrow-values', narrow
        yield style + '-word-active', narrow.replace('u16 active;', 's32 active;')


def test_forms():
    body = dict(forms())['named-values']
    yield 'condition-increment', body.replace('                i++;\n', '').replace(
        '                    i++;\n', '').replace('while (i < count)', 'while (++i < count)')
    predicate = body.replace('    u16 entries;', '    u16 entries;\n    s32 keepGoing;').replace(
        'offset += 2;', 'offset += 2;\n                keepGoing = i < count;').replace('while (i < count)', 'while (keepGoing)')
    yield 'named-predicate', predicate
    yield 'bool-predicate', predicate.replace('s32 keepGoing;', 'u8 keepGoing;')
    yield 'explicit-break', body.replace('offset += 2;', 'offset += 2;\n                if (i >= count) break;').replace('while (i < count)', 'while (1)')
    yield 'cast-comparison', body.replace('while (i < count)', 'while ((s32)(i < count) != 0)')
    yield 'signed-index-cast', body.replace('    s32 i;', '    u32 i;').replace('while (i < count)', 'while ((s32)i < count)')


def offset_forms():
    body = dict(test_forms())['cast-comparison'].replace('    s32 *maximum;', '    s32 slotOffset;\n    s32 *maximum;')
    body = body.replace('    maximum = &D_800C3640[slot];',
        '    slotOffset = slot * 4;\n    maximum = (s32 *)((u8 *)D_800C3640 + slotOffset);')
    for table in ('D_800C35D8', 'D_800C35C8', 'D_800C35D0'):
        body = body.replace(table + '[slot]', '*(u16 **)((u8 *)' + table + ' + slotOffset)')
    yield 'named-slot-offset', body
    for condition in ('(i < count)', '(i < count) == 1', '!(i >= count)', '(i < count) ? 1 : 0'):
        yield 'offset-condition-%d' % len(condition), body.replace('(s32)(i < count) != 0', condition)


def width_forms():
    body = dict(forms())['named-values']
    for width in ('s16', 'u16', 'u8'):
        candidate = body.replace('    s32 i;', '    ' + width + ' i;')
        yield 'index-' + width, candidate
        yield 'index-' + width + '-byte-bound', candidate.replace('    s32 count;', '    u8 count;').replace('count > 0', '(s32)count > 0')


def flat_forms():
    declarations = DECLARATIONS.replace('D_800C3688[][30]', 'D_800C3688[]').replace('D_800C3778[][30]', 'D_800C3778[]')
    for label, body in [('initial', INITIAL), ('named', dict(forms())['named-values']), ('cast', dict(test_forms())['cast-comparison'])]:
        for table in ('D_800C3688', 'D_800C3778'):
            body = body.replace(table + '[slot][0]', table + '[slot * 30]').replace(table + '[slot][i]', table + '[slot * 30 + i]')
        yield 'flat-' + label, body, declarations


def cursor_forms():
    for label, selected in (('initial', INITIAL), ('named', dict(forms())['named-values'])):
        body = selected.replace('if (*enabled++ != 0', 'if (*enabled != 0').replace('    u16 active;\n', '')
        body = body.replace('                active = *enabled++;\n                if (active != 0', '                if (*enabled != 0').replace(
            '                    active = *enabled++;\n                    if (active != 0', '                    if (*enabled != 0')
        body = body.replace('                i++;', '                enabled++;\n                i++;').replace(
            '                    i++;', '                    enabled++;\n                    i++;')
        yield 'tail-cursor-' + label, body
        yield 'tail-cursor-' + label + '-byte-bound', body.replace('    s32 count;', '    u8 count;').replace('count > 0', '(s32)count > 0').replace('i < count', 'i < (s32)count')
        yield 'tail-cursor-' + label + '-cast-test', body.replace('while (i < count)', 'while ((s32)(i < count) != 0)')


def status_forms():
    body = dict(forms())['named-values'].replace('    s32 found;\n', '').replace('    s32 overrideValue;\n', '').replace(
        '    s32 fallbackValue;', '    s32 value;').replace('overrideValue', 'value').replace('fallbackValue', 'value').replace('found', 'value')
    # Keep the member name distinct from the lifetime-sharing local.
    body = body.replace('->value', '->overrideValue')
    for active in (False, True):
        candidate = body
        if active:
            candidate = candidate.replace('    u16 active;\n', '').replace(
                '                active = *enabled++;\n                if (active != 0', '                if (*enabled++ != 0').replace(
                '                    active = *enabled++;\n                    if (active != 0', '                    if (*enabled++ != 0')
        yield 'status-%d' % active, candidate
        yield 'status-%d-byte-bound' % active, candidate.replace('    s32 count;', '    u8 count;').replace('count > 0', '(s32)count > 0').replace('i < count', 'i < (s32)count')
        yield 'status-%d-cast-test' % active, candidate.replace('while (i < count)', 'while ((s32)(i < count) != 0)')


def scoped_forms():
    body = dict(test_forms())['cast-comparison']
    for name, marker in (('overrideValue', '        if (primary[0] >= 4) {'),
            ('primaryValue', '                if (active != 0 && *(u16 *)((u8 *)primary + offset) != 0) {'),
            ('fallbackValue', '                        if (entries != 0) {')):
        body = body.replace('    s32 ' + name + ';\n', '')
        body = body.replace(marker, marker + '\n    s32 ' + name + ';')
    yield 'scoped-values', body
    body = body.replace('    u16 active;\n', '')
    body = '\n'.join(line + '\n' + ' ' * (len(line) - len(line.lstrip()) + 4) + 'u16 active;'
        if line.strip() == 'do {' else line for line in body.split('\n'))
    yield 'scoped-active', body


SELECTED = dict(status_forms())['status-0-cast-test'].replace(
    '        value = 0;',
    '        /* In the preferred pass, value records whether the output was updated. */\n        value = 0;')


def freeze(root, out):
    from tools.tests import record_maximum_checkpoint as installed
    out.mkdir(parents=True, exist_ok=True)
    for key, relative in PATHS.items():
        data = installed.previous_input((root / relative).read_bytes(), relative, root)
        if hashlib.sha256(data).hexdigest() != BASELINE[key]: raise ValueError('Unknown record maximum input: ' + key)
        target = out / ('before-' + key)
        if not target.exists(): target.write_bytes(data)
        if target.read_bytes() != data: raise ValueError('Changed record maximum fixture: ' + key)


def recovered_owner(before, body=None, declarations=None):
    body = SELECTED if body is None else body
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1501CE54() {\n    return 0;\n}': raise ValueError('Unknown record maximum predecessor')
    marker = 'extern u8 *D_800C3960[][30];\n'
    if before.count(marker) != 1 or 'RecordMaximum49D30' in before: raise ValueError('Unknown record maximum declarations')
    return (before[:lo] + body + before[hi:]).replace(marker, marker + '\n' + (DECLARATIONS if declarations is None else declarations), 1)


def measure(root, out, label, body, no_unroll=True, declarations=None):
    freeze(root, out)
    obj, diagnostics = compile_owner(root, out, recovered_owner((out / 'before-view_list_caller_owner').read_text(), body, declarations), label, no_unroll)
    text, functions, relocations = parse_object(obj); f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    data, placed = build.link_owner(root, out, obj, OWNER)
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, placed[FUNCTION]['value']))
    truth = list(struct.unpack_from('>105I', (out / 'before-retail_rom').read_bytes(), ROM))
    row = dict(label=label, words=len(words), diagnostics=diagnostics,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        bindings={at - f['value']:r for at, r in relocations.items() if f['value'] <= at < f['value'] + f['size']},
        pools={n:d.hex() for n, (_, d) in sections(obj).items()
            if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d},
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--forms', action='store_true')
    parser.add_argument('--loops', action='store_true'); parser.add_argument('--tests', action='store_true')
    parser.add_argument('--offsets', action='store_true'); parser.add_argument('--default-profile', action='store_true')
    parser.add_argument('--widths', action='store_true'); parser.add_argument('--flat', action='store_true')
    parser.add_argument('--cursors', action='store_true'); parser.add_argument('--status', action='store_true')
    parser.add_argument('--scopes', action='store_true'); args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    for form in scoped_forms() if args.scopes else status_forms() if args.status else cursor_forms() if args.cursors else flat_forms() if args.flat else width_forms() if args.widths else offset_forms() if args.offsets else test_forms() if args.tests else loop_forms() if args.loops else forms() if args.forms else [('initial', SELECTED)]:
        label, body, *declarations = form
        row = measure(root, root / BUILD, label + ('-default' if args.default_profile else ''), body, not args.default_profile,
            declarations[0] if declarations else None)[2]
        print(json.dumps({k:row[k] for k in ('label', 'words', 'differences', 'diagnostics', 'raw_sha256', 'pools')}), flush=True)
