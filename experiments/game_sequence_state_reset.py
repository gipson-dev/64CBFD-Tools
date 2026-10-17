"""Recover the per-slot/shared sequence reset without changing production inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_record_maximum_scan as previous
from tools.tests import record_maximum_checkpoint as checkpoint
from tools.experiments.game_view_list_setup import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-sequence-state-reset'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_49D30', 'func_1501D044', 0x1501D044, 0x4A4F4, 100
PATHS = dict(previous.PATHS)
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER)
build = previous.build
DECLARATIONS = '''extern s32 D_800C35B8[], D_800C35B0[];
extern u8 D_800C35C0[], D_800C35EA[];
extern u8 D_800C3654[], D_800C3656[], D_800C3658[], D_800C365A[];
extern u8 D_800C365C[], D_800C365E[], D_800C3660[];
extern u8 D_800C35F8, D_800C3638, D_800C3662, D_800C3C8C, D_800C3C8D;
extern u8 D_800C35C2, D_800C3A58, D_800C3C8B, D_800C3680, D_800C3672, D_800C3C9D, D_8008FD84;
extern s8 D_800C3C8A;
extern s16 D_800C3C8E, D_800C3C9E;
extern s32 D_800C367C;
extern void *D_800C3D50;
extern f32 D_800C3648, D_800C364C, D_800C3650, D_800C35A4, D_800C3674, D_800C3678;
extern f32 D_800969C0;
void func_150233BC(void);

'''
INITIAL = '''/* Reset the selected slot and shared sequence state before clearing actor records. */
void func_1501D044(s32 slot) {
    D_800C35B8[slot] = -100;
    D_800C35B0[slot] = 0;
    D_800C35C0[slot] = 0;
    D_800C3C8E = 0;
    D_800C363A[slot] = 0;
    D_800C35EA[slot] = 0;
    D_800C3D50 = NULL;
    D_800C35F8 = 255;
    D_800C3648 = 0.0f;
    D_800C364C = 0.0f;
    D_800C3650 = 0.0f;
    D_800C3654[slot] = 0;
    D_800C3656[slot] = 0;
    D_800C3658[slot] = 1;
    D_800C365A[slot] = 0;
    D_800C365C[slot] = 0;
    D_800C365E[slot] = 0;
    D_800C3660[slot] = 0;
    D_800C3638 = 0;
    D_800C3662 = 0;
    D_800C3C8C = 0;
    D_800C3C8D = 0;
    D_800C35C2 = 0;
    D_800C3A58 = 0;
    D_800C35A4 = 0.0f;
    D_800C3C8A = -1;
    D_800C3C8B = 0;
    D_800C3674 = D_800969C0;
    D_800C3678 = D_800969C0;
    D_800C367C = 0;
    D_800C3680 = 0;
    D_800C3672 = 0;
    D_800C3C9D = 100;
    D_800C3C9E = -1;
    func_150233BC();
    D_8008FD84 = 0;
    D_800C3670 = 0;
}'''
def forms():
    yield 'initial', INITIAL
    body = INITIAL.replace('    D_800C35B8[slot]', '    f32 limit = D_800969C0;\n\n    D_800C35B8[slot]', 1)
    body = body.replace('D_800C3674 = D_800969C0', 'D_800C3674 = limit').replace('D_800C3678 = D_800969C0', 'D_800C3678 = limit')
    yield 'cached-limit', body
    yield 'cached-literals', body.replace('    f32 limit', '    s32 unset = -1;\n    f32 zero = 0.0f;\n    f32 limit').replace(
        ' = 0.0f;', ' = zero;').replace('f32 zero = zero;', 'f32 zero = 0.0f;').replace('D_800C3C8A = -1', 'D_800C3C8A = unset').replace('D_800C3C9E = -1', 'D_800C3C9E = unset')


def float_forms():
    body = dict(forms())['cached-limit']
    yield 'const-limit', body.replace('f32 limit =', 'const f32 limit =')
    yield 'register-limit', body.replace('f32 limit =', 'register f32 limit =')
    yield 'chained-limit-stores', body.replace('    D_800C3674 = limit;\n    D_800C3678 = limit;', '    D_800C3678 = D_800C3674 = limit;')
    zero = body.replace('    f32 limit = D_800969C0;', '    register f32 zero = 0.0f;\n    register f32 limit = D_800969C0;')
    for target in ('D_800C3648', 'D_800C364C', 'D_800C3650', 'D_800C35A4'):
        zero = zero.replace(target + ' = 0.0f', target + ' = zero')
    yield 'register-floats', zero


SELECTED = dict(forms())['cached-limit'].replace(
    '    f32 limit =', '    /* Capture the shared limit before resetting indexed state. */\n    f32 limit =').replace(
    '    D_8008FD84 = 0;', '    /* These flags are cleared only after the actor-table helper returns. */\n    D_8008FD84 = 0;')


def freeze(root, out):
    from tools.tests import sequence_state_reset_checkpoint as installed
    out.mkdir(parents=True, exist_ok=True)
    for key, relative in PATHS.items():
        data = installed.previous_input((root / relative).read_bytes(), relative, root)
        if hashlib.sha256(data).hexdigest() != BASELINE[key]: raise ValueError('Unknown sequence reset input: ' + key)
        target = out / ('before-' + key)
        if not target.exists(): target.write_bytes(data)
        if target.read_bytes() != data: raise ValueError('Changed sequence reset fixture: ' + key)


def recovered_owner(before, body=None):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1501D044() {\n    return 0;\n}': raise ValueError('Unknown sequence reset predecessor')
    marker = 'extern u8 *D_800C3778[][30];\n'
    if before.count(marker) != 1 or 'extern f32 D_800969C0;' in before: raise ValueError('Unknown sequence reset declarations')
    return (before[:lo] + (SELECTED if body is None else body) + before[hi:]).replace(marker, marker + '\n' + DECLARATIONS, 1)


def recovered_caller(before):
    marker = '/* Generated placeholder declarations. */\n'
    if before.count(marker) != 1 or 'void func_1501D044(s32 slot);' in before: raise ValueError('Unknown sequence reset caller declaration')
    return before.replace(marker, marker + 'void func_1501D044(s32 slot);\n', 1)


def measure(root, out, label, body):
    freeze(root, out)
    obj, diagnostics = compile_owner(root, out, recovered_owner((out / 'before-view_list_caller_owner').read_text(), body), label, True)
    text, functions, relocations = parse_object(obj); f = functions[FUNCTION]; raw = text[f['value']:f['value'] + f['size']]
    data, placed = build.link_owner(root, out, obj, OWNER)
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, placed[FUNCTION]['value']))
    truth = list(struct.unpack_from('>100I', (out / 'before-retail_rom').read_bytes(), ROM))
    row = dict(label=label, words=len(words), diagnostics=diagnostics,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS), raw_sha256=hashlib.sha256(raw).hexdigest(),
        bindings={at - f['value']:r for at, r in relocations.items() if f['value'] <= at < f['value'] + f['size']},
        pools={n:d.hex() for n, (_, d) in sections(obj).items() if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d},
        different_words=[(i * 4, '0x%08X' % a, '0x%08X' % b) for i, (a, b) in enumerate(zip(words, truth)) if a != b])
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--forms', action='store_true')
    parser.add_argument('--floats', action='store_true'); args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    for label, body in float_forms() if args.floats else forms() if args.forms else [('selected', SELECTED)]:
        row = measure(root, root / BUILD, label, body)[2]
        print(json.dumps({k:row[k] for k in ('label', 'words', 'differences', 'diagnostics', 'raw_sha256', 'pools')}), flush=True)
