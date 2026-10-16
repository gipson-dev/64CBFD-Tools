"""Screen real divider lifetimes and named history ranges without word guards."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_frame_timing_update as previous
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import frame_timing_checkpoint as checkpoint
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-frame-timing-fitting'
OWNER, FUNCTION, ENTRY, ROM, WORDS = previous.OWNER, previous.FUNCTION, previous.ENTRY, previous.ROM, previous.WORDS
PATHS = previous.PATHS
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER)
INITIAL = previous.SELECTED
build = previous.build


def freeze(root, out):
    with patch.object(previous, 'BASELINE', BASELINE):
        previous.freeze(root, out)


def recovered_owner(before, body, declarations=''):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != INITIAL.split('\n', 1)[1]:
        raise ValueError('Unknown frame-timing fitting predecessor')
    return before[:lo] + declarations + body.split('\n', 1)[1] + before[hi:]


def divisor_forms():
    # Keep the first byte gate separate from the word used by division.
    live = INITIAL.replace('    u8 divisor;', '    u32 divisor;').replace(
        '    divisor = D_800BEA0C;\n', '').replace(
        '    if (divisor != 0) {', '    if (D_800BEA0C != 0) {\n        divisor = D_800BEA0C;')
    yield 'branch-word-divisor', live, ''
    yield 'branch-byte-divisor', live.replace('    u32 divisor;', '    u8 divisor;'), ''
    copied = INITIAL.replace('    u8 divisor;', '    u8 gate;\n    u32 divisor;').replace(
        '    divisor = D_800BEA0C;', '    gate = D_800BEA0C;').replace(
        '    if (divisor != 0) {', '    if (gate != 0) {\n        divisor = gate;')
    yield 'cached-gate-word-divisor', copied, ''
    yield 'cached-gate-byte-divisor', copied.replace('    u32 divisor;', '    u8 divisor;'), ''
    for name, body, declarations in (('original', INITIAL, ''), ('branch', live, '')):
        updated = body.replace('                D_800BE610 = total - ((u32)D_800BE9E4 * total);',
            '                total -= (u32)D_800BE9E4 * total;\n                D_800BE610 = total;')
        yield name + '-updated-total', updated, declarations
        quotient = body.replace('    u32 total;', '    u32 total;\n    u32 quotient;').replace(
            '                D_800BE9E4 = total / divisor;',
            '                quotient = total / divisor;\n                D_800BE9E4 = quotient;').replace(
            '((u32)D_800BE9E4 * total)', '(quotient * total)')
        yield name + '-local-quotient', quotient, declarations


def history_forms():
    loop = '        for (i = 0; i < 10; i++) {\n            sum += D_800BE5E8[i];\n        }'
    named = INITIAL.replace(loop,
        '        sum += D_800BE5E8[0];\n        sum += D_800BE5EC;\n'
        '        for (i = 0; i < 8; i++) {\n            sum += D_800BE5F0[i];\n        }')
    declarations = 'extern f32 D_800BE5EC, D_800BE5F0[];\n'
    yield 'named-two-head-eight-tail', named, declarations
    yield 'named-head-original-tail', INITIAL.replace(loop,
        '        sum += D_800BE5E8[0];\n        sum += D_800BE5EC;\n'
        '        for (i = 2; i < 10; i++) {\n            sum += D_800BE5E8[i];\n        }'), declarations
    yield 'explicit-two-head-array-tail', INITIAL.replace(loop,
        '        sum += D_800BE5E8[0];\n        sum += D_800BE5E8[1];\n'
        '        for (i = 2; i < 10; i++) {\n            sum += D_800BE5E8[i];\n        }'), ''
    yield 'history-extent-256', INITIAL, ''


def combined_forms():
    history, declarations = next((body, decl) for name, body, decl in history_forms()
        if name == 'named-two-head-eight-tail')
    for name, body, _ in divisor_forms():
        if name not in ('branch-byte-divisor', 'cached-gate-word-divisor', 'original-updated-total'):
            continue
        old = INITIAL[INITIAL.index('    } else {\n        sum = 0.0f;'):]
        new = history[history.index('    } else {\n        sum = 0.0f;'):]
        if body.count(old) != 1:
            raise ValueError('Unknown timing history tail')
        yield name + '-named-history', body.replace(old, new), declarations
    for name, body in (('original', INITIAL), ('updated-total', dict((n,b) for n,b,_ in divisor_forms())['original-updated-total'])):
        for zero in ('chain-time-first', 'chain-inverse-first'):
            old = '        D_800BE9A4 = 0.0f;\n        D_800BE9A8 = 0.0f;'
            new = ('        D_800BE9A8 = D_800BE9A4 = 0.0f;' if zero == 'chain-time-first'
                else '        D_800BE9A4 = D_800BE9A8 = 0.0f;')
            if body.count(old) != 1:
                raise ValueError('Unknown timing zero reciprocal')
            yield name + '-' + zero, body.replace(old, new), ''


def division_capture_forms():
    body = INITIAL.replace('    u8 divisor;', '    u32 divisor;').replace('    divisor = D_800BEA0C;\n', '')
    body = body.replace('if (divisor != 0)', 'if (D_800BEA0C != 0)').replace(
        'if (divisor == 1)', 'if (D_800BEA0C == 1)').replace(
        '(f32)(u32)divisor', '(f32)(u32)D_800BEA0C')
    marker = '            total = D_800BE610 + (u32)D_800BE9E4;'
    for label, anchor in (('before-total', marker), ('before-ratio', '            D_800BE9A4 = (f32)'),
            ('before-integer', '            if (total >= divisor)')):
        candidate = body.replace(anchor, '            divisor = D_800BEA0C;\n' + anchor, 1)
        yield 'integer-divisor-' + label, candidate, ''
        cached = candidate.replace('    u32 total;', '    s32 ticks;\n    u32 total;').replace(
            '    D_800BEA08 = D_800BE9E4;', '    ticks = D_800BE9E4;\n    D_800BEA08 = ticks;')
        for old, new in (('D_800BE9E4 = 0;', 'D_800BE9E4 = ticks = 0;'),
                ('D_800BE9E4 = (s32)D_800BE9A4;', 'D_800BE9E4 = ticks = (s32)D_800BE9A4;'),
                ('D_800BE9E4 = total / divisor;', 'D_800BE9E4 = ticks = total / divisor;'),
                ('(u32)D_800BE9E4', '(u32)ticks'), ('(f32)D_800BE9E4', '(f32)ticks'),
                ('D_800BE9AC += D_800BE9E4;', 'D_800BE9AC += ticks;')):
            cached = cached.replace(old, new)
        yield 'integer-divisor-' + label + '-cached-ticks', cached, ''


def accumulator_forms():
    for label, body in (('original', INITIAL), ('updated', dict((n,b) for n,b,_ in divisor_forms())['original-updated-total'])):
        old = '            total = D_800BE610 + (u32)D_800BE9E4;'
        yield label + '-residual-first-accumulator', body.replace(old,
            '            total = D_800BE610;\n            total += (u32)D_800BE9E4;'), ''
        yield label + '-ticks-first-accumulator', body.replace(old,
            '            total = (u32)D_800BE9E4;\n            total += D_800BE610;'), ''


def measure(root, out, label, body, declarations='', edits=()):
    freeze(root, out)
    content = recovered_owner((out / 'before-dispatch_owner').read_text(), body, declarations)
    for old, new in edits:
        if content.count(old) != 1:
            raise ValueError('Unknown timing declaration edit')
        content = content.replace(old, new, 1)
    if label == 'history-extent-256':
        content = content.replace('D_800BE5E8[]', 'D_800BE5E8[256]')
    obj, diagnostics = build.compile_owner(root, out, content, label)
    text, functions, relocations = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    data, placed = build.link_owner(root, out, obj, OWNER)
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, placed[FUNCTION]['value']))
    truth = struct.unpack_from('>192I', (out / 'before-retail_rom').read_bytes(), ROM)
    slot = words + [0] * max(0, WORDS - len(words))
    row = dict(label=label, words=len(words), frame=(-words[0]) & 65535,
        differences=sum(a != b for a, b in zip(slot, truth)) + max(0, len(words) - WORDS),
        raw_sha256=hashlib.sha256(raw).hexdigest(), diagnostics=diagnostics,
        bindings={a - f['value']:v for a,v in relocations.items() if f['value'] <= a < f['value'] + f['size']},
        pools={n:d.hex() for n,(_,d) in sections(obj).items()
            if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d})
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


def trace_owner(root, variant='baseline', mode=6):
    from tools.experiments import game_text_measurer_uopt_trace as qualified
    if variant not in ('baseline', 'updated-total') or mode not in (5, 6):
        raise ValueError('Unknown frame-timing trace variant/mode')
    out = root / BUILD
    freeze(root, out)
    body = INITIAL if variant == 'baseline' else dict((n,b) for n,b,_ in divisor_forms())['original-updated-total']
    content = recovered_owner((out / 'before-dispatch_owner').read_text(), body)
    expected = (previous.RAW_SHA256 if variant == 'baseline' else
        '660ad91e67099a57e46c8458628ba0d84f3c6e30975dc7ea472f3a3da8351388')
    live = {key:hashlib.sha256((root / path).read_bytes()).hexdigest() for key,path in PATHS.items()}
    if live != BASELINE:
        raise ValueError('Changed frame-timing trace inputs')
    def compile_baseline(root, work, name, candidate):
        if candidate != content:
            raise ValueError('Changed frame-timing trace source')
        obj, diagnostics = build.compile_owner(root, work, candidate, name)
        text, functions, _ = parse_object(obj)
        f = functions[FUNCTION]
        digest = hashlib.sha256(text[f['value']:f['value'] + f['size']]).hexdigest()
        if digest != expected:
            raise ValueError('Changed frame-timing trace object')
        return dict(owner=OWNER, function=FUNCTION, raw_sha256=digest, diagnostics=diagnostics), None
    with patch.object(qualified.screen, 'compile_candidate', compile_baseline), patch.dict(
            qualified.screen.PROFILES, owner=('-O2', '-g3')):
        name = variant + '-mode-' + str(mode)
        result = qualified.trace_uopt(root, out / 'uopt', name, content, mode)
    work = out / 'uopt' / name
    log = (work / 'debugger.txt').read_text()
    if log.splitlines().count('Allocate diagnostic stream buffer') != 1 or 'Suppress diagnostic real-number printer' not in log:
        raise ValueError('Frame-timing diagnostic gate did not fire')
    if {key:hashlib.sha256((root / path).read_bytes()).hexdigest() for key,path in PATHS.items()} != live:
        raise ValueError('Frame-timing diagnostic changed live inputs')
    text = (work / 'uoptlist').read_text()
    first, last = 'IN LOCAL OPTIMIZATION OF ' + FUNCTION, 'IN REEMISSION OF ' + FUNCTION
    if text.count(first) != 1 or text.count(last) != 1:
        raise ValueError('Missing/duplicate frame-timing procedure')
    block = text[text.index(first):text.index(last) + len(last)]
    (work / 'procedure.txt').write_text(block)
    result.update(variant=variant, variables=qualified.variable_expressions(block), installable=False,
        constraints=qualified.allocation_constraints(block) if mode == 5 else [], live_inputs_unchanged=live)
    (work / 'trace.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true')
    parser.add_argument('--combined', action='store_true')
    parser.add_argument('--types', action='store_true')
    parser.add_argument('--division-captures', action='store_true')
    parser.add_argument('--accumulators', action='store_true')
    parser.add_argument('--trace', choices=('baseline', 'updated-total'))
    parser.add_argument('--mode', type=int, choices=(5, 6), default=6)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.trace:
        result = trace_owner(root, args.trace, args.mode)
        print(json.dumps({k:result[k] for k in ('variant', 'mode', 'code_unchanged', 'bytes', 'trace_sha256', 'variables')}, indent=2))
        return
    if args.types:
        for name, edits in (
            ('signed-residual', (('extern u32 D_800BE610;', 'extern s32 D_800BE610;'),)),
            ('residual-const-load', ())):
            body = INITIAL
            if name == 'residual-const-load':
                body = body.replace('D_800BE610 + (u32)D_800BE9E4', '*(const u32 *)&D_800BE610 + (u32)D_800BE9E4')
            row = measure(root, root / BUILD, name, body, edits=edits)[2]
            print(json.dumps({k:row[k] for k in ('label', 'words', 'frame', 'differences', 'raw_sha256', 'pools')}), flush=True)
        return
    for label, body, declarations in (accumulator_forms() if args.accumulators else division_capture_forms() if args.division_captures else
            combined_forms() if args.combined else history_forms() if args.history else divisor_forms()):
        row = measure(root, root / BUILD, label, body, declarations)[2]
        print(json.dumps({k:row[k] for k in ('label', 'words', 'frame', 'differences', 'raw_sha256', 'pools')}), flush=True)


if __name__ == '__main__':
    main()
