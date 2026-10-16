"""Recover the graphics-task submission body without changing production inputs."""
import argparse
import csv
import difflib
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_viewport_initialize_lifetimes as previous
from tools.experiments import game_view_list_setup as profiles
from tools.tests import viewport_initialize_checkpoint as checkpoint
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_classifier_candidates import sections
from tools import pad_c_object, pad_generated_object

BUILD = 'conker/build/game-graphics-task-submit'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_49D30', 'func_1501C880', 0x1501C880, 0x49D30, 239
PATHS = dict(previous.PATHS,
    task_sched='conker/include/2.0L/PR/sched.h', task_header='conker/include/2.0L/PR/sptask.h',
    task_donor='../Another Source/CBFD-Recompiled/conker/conker/src/game/game_49D30.c',
    task_original_caller='conker/asm/nonmatchings/game_45B80/func_1501878C.s')
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER,
    task_sched='40a7e05e5e774a3cbc015d44bb8225f469937de178bfe84cd1de9ef3c5ff7572',
    task_header='12b0a593a7013076fb60cf7224f0bdf25da554076e8b6f2ffe3999769e737dc5',
    task_donor='de86733aea5f3ec2399ae312d9d38dc1ad324be04d6568b4c75b82dec007356d',
    task_original_caller='dd67261a3a124a4ed359fb91fc3552f801e1888562f3659c63c0e8794ae90d5f')
build = previous.build
DECLARATIONS = '''#include <PR/sched.h>

extern u8 D_800BE9C0, D_800BE617, D_800BEBA0;
extern s16 D_800BEAA8;
extern s32 D_80082FA0;
extern Gfx *D_800BE9C8[], *D_800BE9D0, *D_800BE9D8[];
extern OSScTask *D_800BEAD4, D_800BEAD8[];
extern u64 D_100290D0[], D_100291A0[], D_800C1060[], D_800BEBB0[], D_800CBE10[], D_8003A5E8[];
extern u64 *D_800BEAD0, *D_800BEB9C, *D_80038090, *D_80038094;
extern void *D_8002AAE8[];
extern OSMesgQueue D_8003B1E8, D_800BEA10;
extern OSScMsg D_800BEA68[];
void func_1501A39C(void);
s32 func_1501CC3C(void);
'''
INITIAL = '''/* Submit the current graphics task, repairing an out-of-range command cursor. */
void func_1501C880(s32 unused, s32 swapBuffers) {
    s32 capacity;
    Gfx *start;
    s32 used;

    D_800BEAD4 = &D_800BEAD8[D_800BE9C0];
    D_800BEAD4->next = 0;
    capacity = (s32)((u32)D_800BE9C8[1] - (u32)D_800BE9C8[0]) >> 3;
    start = D_800BE9C8[D_800BE9C0];
    used = (s32)((u32)D_800BE9D0 - (u32)start) >> 3;
    if (used < 0 || capacity < used) {
        func_1501A39C();
        D_800BE9D0 = D_800BE9D8[D_800BE9C0];
        gDPFullSync(D_800BE9D0++);
        gSPEndDisplayList(D_800BE9D0++);
        start = D_800BE9C8[D_800BE9C0];
        used = (s32)((u32)D_800BE9D0 - (u32)start) >> 3;
    }
    if (used < 0 || capacity - 400 < used) {
        D_800BE9D0 = (Gfx *)((u32)start + ((u32)capacity - 400U) * 8U);
        gDPFullSync(D_800BE9D0++);
        gSPEndDisplayList(D_800BE9D0++);
        start = D_800BE9C8[D_800BE9C0];
    }
    D_800BEAD4->list.t.data_ptr = (u64 *)start;
    D_800BEAD4->list.t.data_size = (u32)((s32)((u32)D_800BE9D0 - (u32)D_800BE9C8[D_800BE9C0]) >> 3) << 3;
    func_1501CC3C();
    D_800BEAD4->list.t.type = M_GFXTASK;
    D_800BEAD4->list.t.flags = OS_TASK_LOADABLE;
    D_800BEAD4->list.t.ucode_boot = D_100290D0;
    D_800BEAD4->list.t.ucode_boot_size = (u32)D_100291A0 - (u32)D_100290D0;
    if (D_800BEBA0 != 0) {
        D_800BEAD4->list.t.ucode = D_800C1060;
        D_800BEAD4->list.t.ucode_data = D_800BEB9C;
    } else {
        D_800BEAD4->list.t.ucode = D_800BEBB0;
        D_800BEAD4->list.t.ucode_data = D_800BEAD0;
    }
    D_800BEAD4->list.t.ucode_data_size = SP_UCODE_DATA_SIZE;
    D_800BEAD4->list.t.dram_stack = D_800CBE10;
    D_800BEAD4->list.t.dram_stack_size = 0x400;
    D_800BEAD4->list.t.output_buff = D_80038090;
    D_800BEAD4->list.t.output_buff_size = D_80038094;
    D_800BEAD4->list.t.yield_data_ptr = D_8003A5E8;
    D_800BEAD4->list.t.yield_data_size = OS_YIELD_DATA_SIZE;
    D_800BEAD4->flags = OS_SC_NEEDS_RDP | OS_SC_NEEDS_RSP | OS_SC_LAST_TASK;
    if (swapBuffers != 0) {
        D_800BEAD4->flags |= OS_SC_SWAPBUFFER;
    }
    if (D_800BE617 != 0) {
        D_800BEAD4->flags |= ((u32)D_80082FA0 + 1U) << 16;
        D_800BE617 = 0;
    }
    D_800BEAD4->msgQ = &D_800BEA10;
    D_800BEAD4->msg = &D_800BEA68[D_800BE9C0];
    D_800BEAD4->framebuffer = D_8002AAE8[D_800BE9C0];
    osWritebackDCacheAll();
    osSendMesg(&D_8003B1E8, D_800BEAD4, OS_MESG_BLOCK);
    if (swapBuffers != 0) {
        D_800BE9C0 ^= 1;
    }
    D_800BEAA8++;
}'''


def forms():
    for span in (False, True):
        body = INITIAL
        if span:
            body = body.replace('(s32)((u32)D_800BE9C8[1] - (u32)D_800BE9C8[0]) >> 3',
                'D_800BE9C8[1] - D_800BE9C8[0]').replace('(s32)((u32)D_800BE9D0 - (u32)start) >> 3',
                'D_800BE9D0 - start').replace('(u32)((s32)((u32)D_800BE9D0 - (u32)D_800BE9C8[D_800BE9C0]) >> 3) << 3',
                '(D_800BE9D0 - D_800BE9C8[D_800BE9C0]) * 8')
        for tail, expr in (('unsigned', '(Gfx *)((u32)start + ((u32)capacity - 400U) * 8U)'),
                ('signed', '(Gfx *)((u32)start + (capacity - 400) * 8)'),
                ('pointer', 'start + (capacity - 400)')):
            yield 'span-%d-tail-%s' % (span, tail), body.replace(
                '(Gfx *)((u32)start + ((u32)capacity - 400U) * 8U)', expr)


def signed_forms():
    for spans in (False, True):
        body = INITIAL.replace('(Gfx *)((u32)start + ((u32)capacity - 400U) * 8U)',
            '(Gfx *)((s32)start + (capacity - 400) * 8)')
        if spans:
            body = body.replace('(s32)((u32)D_800BE9C8[1] - (u32)D_800BE9C8[0])',
                '((s32)D_800BE9C8[1] - (s32)D_800BE9C8[0])').replace(
                '(s32)((u32)D_800BE9D0 - (u32)start)', '((s32)D_800BE9D0 - (s32)start)').replace(
                '(s32)((u32)D_800BE9D0 - (u32)D_800BE9C8[D_800BE9C0])',
                '((s32)D_800BE9D0 - (s32)D_800BE9C8[D_800BE9C0])')
        for task in ('inline', 'local', 'chain'):
            candidate = body
            if task == 'local':
                candidate = candidate.replace('    s32 capacity;', '    OSScTask *task;\n    s32 capacity;').replace(
                    '    D_800BEAD4 = &D_800BEAD8[D_800BE9C0];\n    D_800BEAD4->next = 0;',
                    '    task = &D_800BEAD8[D_800BE9C0];\n    D_800BEAD4 = task;\n    task->next = 0;')
            elif task == 'chain':
                candidate = candidate.replace('    D_800BEAD4 = &D_800BEAD8[D_800BE9C0];\n    D_800BEAD4->next = 0;',
                    '    (D_800BEAD4 = &D_800BEAD8[D_800BE9C0])->next = 0;')
            yield 'signed-%d-%s' % (spans, task), candidate


def word_forms():
    for label, selected in [('initial', INITIAL), *signed_forms()]:
        if label not in ('initial', 'signed-1-local', 'signed-0-local'): continue
        body = selected.replace('    Gfx *start;', '    s32 start;').replace(
            'start = D_800BE9C8[D_800BE9C0]', 'start = ((s32 *)D_800BE9C8)[D_800BE9C0]').replace(
            '(s32)((u32)D_800BE9C8[1] - (u32)D_800BE9C8[0])',
            '(((s32 *)D_800BE9C8)[1] - ((s32 *)D_800BE9C8)[0])').replace(
            '((s32)D_800BE9C8[1] - (s32)D_800BE9C8[0])',
            '(((s32 *)D_800BE9C8)[1] - ((s32 *)D_800BE9C8)[0])')
        for tail in ('word', 'pointer'):
            candidate = body
            expression = '(Gfx *)((u32)start + ((u32)capacity - 400U) * 8U)' if label == 'initial' else '(Gfx *)((s32)start + (capacity - 400) * 8)'
            candidate = candidate.replace(expression, '(Gfx *)(start + (capacity - 400) * 8)' if tail == 'word' else
                '(Gfx *)start + (capacity - 400)')
            yield 'word-' + label + '-' + tail, candidate


def access_forms():
    for next_word in (False, True):
        for cursor_word in (False, True):
            body = INITIAL
            if next_word: body = body.replace('    D_800BEAD4->next = 0;', '    *(s32 *)D_800BEAD4 = 0;')
            if cursor_word:
                body = body.replace('        D_800BE9D0 = (Gfx *)((u32)start + ((u32)capacity - 400U) * 8U);',
                    '        *(s32 *)&D_800BE9D0 = (s32)start + (capacity - 400) * 8;')
            yield 'access-%d-%d' % (next_word, cursor_word), body


def tail_forms():
    old = '(Gfx *)((u32)start + ((u32)capacity - 400U) * 8U)'
    for label, expr in (
            ('unsigned-shift', '(Gfx *)((u32)start + ((u32)(capacity - 400) << 3))'),
            ('signed-shift', '(Gfx *)((s32)start + ((capacity - 400) << 3))'),
            ('size-multiply', '(Gfx *)((u32)start + (capacity - 400) * sizeof(Gfx))'),
            ('index-first-shift', '(Gfx *)(((u32)(capacity - 400) << 3) + (u32)start)')):
        yield label, INITIAL.replace(old, expr)
    named = INITIAL.replace('    s32 used;', '    s32 used;\n    s32 available;').replace(
        '    if (used < 0 || capacity - 400 < used) {',
        '    available = capacity - 400;\n    if (used < 0 || available < used) {').replace(old,
        '(Gfx *)((u32)start + ((u32)available << 3))')
    yield 'named-available', named
    goto = INITIAL.replace('    if (used < 0 || capacity - 400 < used) {',
        '    if (used < 0) goto limit;\n    if (used <= capacity - 400) goto ready;\nlimit: {').replace(
        '    D_800BEAD4->list.t.data_ptr =', 'ready:\n    D_800BEAD4->list.t.data_ptr =')
    yield 'split-limit-control', goto


def opening_forms():
    selected = dict(tail_forms())['named-available']
    statement = '    capacity = (s32)((u32)D_800BE9C8[1] - (u32)D_800BE9C8[0]) >> 3;\n'
    for label, marker in (('capacity-before-task', '    D_800BEAD4 ='),
            ('capacity-before-clear', '    D_800BEAD4->next =')):
        body = selected.replace(statement, '')
        body = body.replace(marker, statement + marker, 1)
        yield label, body
    body = selected.replace('    s32 capacity;', '    s32 capacity;\n    s32 bytes;').replace(statement,
        '    bytes = (s32)((u32)D_800BE9C8[1] - (u32)D_800BE9C8[0]);\n    capacity = bytes >> 3;\n')
    yield 'named-byte-span', body


SELECTED = dict(opening_forms())['capacity-before-task']
RAW_SHA256 = 'c59f51258bcc79b0ba9e4c28f4b1559e366f4cf01f2bf8d7fc6144d34a251ad2'
RELOCATIONS = {
    0x8: [['R_MIPS_HI16','D_800BE9C0']],
    0xC: [['R_MIPS_HI16','D_800BEAD4']],
    0x10: [['R_MIPS_HI16','D_800BE9D0']],
    0x14: [['R_MIPS_HI16','D_800BE9C8']],
    0x18: [['R_MIPS_LO16','D_800BE9C8']],
    0x1C: [['R_MIPS_LO16','D_800BE9D0']],
    0x20: [['R_MIPS_LO16','D_800BEAD4']],
    0x24: [['R_MIPS_LO16','D_800BE9C0']],
    0x38: [['R_MIPS_HI16','D_800BEAD8']],
    0x50: [['R_MIPS_LO16','D_800BEAD8']],
    0x9C: [['R_MIPS_26','func_1501A39C']],
    0xA8: [['R_MIPS_HI16','D_800BE9D8']],
    0xAC: [['R_MIPS_HI16','D_800BE9D0']],
    0xB8: [['R_MIPS_LO16','D_800BE9D8']],
    0xBC: [['R_MIPS_LO16','D_800BE9D0']],
    0xC0: [['R_MIPS_HI16','D_800BEAD4']],
    0xC4: [['R_MIPS_HI16','D_800BE9C8']],
    0xC8: [['R_MIPS_LO16','D_800BE9C8']],
    0xCC: [['R_MIPS_LO16','D_800BEAD4']],
    0x144: [['R_MIPS_HI16','D_800BE9D0']],
    0x148: [['R_MIPS_LO16','D_800BE9D0']],
    0x1B8: [['R_MIPS_26','func_1501CC3C']],
    0x1C0: [['R_MIPS_HI16','D_800BEAD4']],
    0x1C4: [['R_MIPS_LO16','D_800BEAD4']],
    0x1DC: [['R_MIPS_HI16','D_100290D0']],
    0x1E0: [['R_MIPS_LO16','D_100290D0']],
    0x1EC: [['R_MIPS_HI16','D_100291A0']],
    0x1F0: [['R_MIPS_LO16','D_100291A0']],
    0x200: [['R_MIPS_HI16','D_800BEBA0']],
    0x208: [['R_MIPS_LO16','D_800BEBA0']],
    0x20C: [['R_MIPS_HI16','D_800BE617']],
    0x210: [['R_MIPS_HI16','D_800BEBB0']],
    0x218: [['R_MIPS_LO16','D_800BE617']],
    0x220: [['R_MIPS_HI16','D_800C1060']],
    0x224: [['R_MIPS_LO16','D_800C1060']],
    0x22C: [['R_MIPS_HI16','D_800BEB9C']],
    0x230: [['R_MIPS_LO16','D_800BEB9C']],
    0x244: [['R_MIPS_LO16','D_800BEBB0']],
    0x248: [['R_MIPS_HI16','D_800BEAD0']],
    0x254: [['R_MIPS_LO16','D_800BEAD0']],
    0x264: [['R_MIPS_HI16','D_800CBE10']],
    0x270: [['R_MIPS_LO16','D_800CBE10']],
    0x280: [['R_MIPS_HI16','D_80038090']],
    0x284: [['R_MIPS_HI16','D_80038094']],
    0x290: [['R_MIPS_LO16','D_80038090']],
    0x294: [['R_MIPS_HI16','D_8003A5E8']],
    0x298: [['R_MIPS_LO16','D_8003A5E8']],
    0x2A4: [['R_MIPS_LO16','D_80038094']],
    0x2D0: [['R_MIPS_HI16','D_80082FA0']],
    0x2F0: [['R_MIPS_HI16','D_800BEA10']],
    0x300: [['R_MIPS_LO16','D_80082FA0']],
    0x320: [['R_MIPS_LO16','D_800BEA10']],
    0x324: [['R_MIPS_HI16','D_800BEA68']],
    0x334: [['R_MIPS_LO16','D_800BEA68']],
    0x348: [['R_MIPS_HI16','D_8002AAE8']],
    0x358: [['R_MIPS_LO16','D_8002AAE8']],
    0x35C: [['R_MIPS_26','osWritebackDCacheAll']],
    0x364: [['R_MIPS_HI16','D_800BEAD4']],
    0x368: [['R_MIPS_LO16','D_800BEAD4']],
    0x36C: [['R_MIPS_HI16','D_8003B1E8']],
    0x370: [['R_MIPS_LO16','D_8003B1E8']],
    0x378: [['R_MIPS_26','osSendMesg']],
    0x384: [['R_MIPS_HI16','D_800BEAA8']],
    0x388: [['R_MIPS_LO16','D_800BEAA8']],
}
RELOCATIONS = {at:[tuple(row) for row in rows] for at, rows in RELOCATIONS.items()}
SERIALIZATION = (
    (('D_800BEAD8', 'D_800BE9F8'), (1, 0),
        ((0x800BEAD8, 0, 16, 0, 65521), (0x800BE9F8, 0, 16, 0, 65521))),
    (('D_800BEAD4', 'D_800BE9F4'), (1, 0),
        ((0x800BEAD4, 0, 16, 0, 65521), (0x800BE9F4, 0, 16, 0, 65521))),
    (('D_800CBE10', 'D_800A0758', '.L15028860_game_data'), (1, 2, 0),
        ((0x800CBE10, 0, 16, 0, 65521), (0x800A0758, 0, 16, 0, 65521), (0x15028860, 0, 16, 0, 5))),
)


def freeze(root, out):
    from tools.tests import graphics_task_submit_checkpoint as final
    out.mkdir(parents=True, exist_ok=True)
    for key, relative in PATHS.items():
        data = (root / relative).read_bytes()
        if key in final.AFTER and hashlib.sha256(data).hexdigest() == final.AFTER[key]:
            data = final.fixture(root, 'before', key)
        if hashlib.sha256(data).hexdigest() != BASELINE[key]: raise ValueError('Unknown graphics submission input: ' + key)
        path = out / ('before-' + key)
        if not path.exists(): path.write_bytes(data)
        if path.read_bytes() != data: raise ValueError('Changed graphics submission fixture: ' + key)


def recovered_owner(before, body=None):
    body = SELECTED if body is None else body
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1501C880() {\n    return 0;\n}':
        raise ValueError('Unknown graphics submission predecessor')
    if before.count('#include "structs.h"\n') != 1 or '#include <PR/sched.h>' in before:
        raise ValueError('Unknown graphics submission declaration anchor')
    return (before[:lo] + body + before[hi:]).replace('#include "structs.h"\n',
        '#include "structs.h"\n' + DECLARATIONS + '\n', 1)


def recovered_caller(before):
    old, new = 's32 func_1501C880(s32, s32);', 'void func_1501C880(s32 unused, s32 swapBuffers);'
    if before.count(old) != 1: raise ValueError('Unknown graphics submission caller interface')
    condition = 'if (D_800BEAC1 != D_800BEAC0) {'
    if before.count(condition) != 1: raise ValueError('Unknown graphics submission caller comparison')
    return before.replace(old, new, 1).replace(condition, 'if (D_800BEAC0 != D_800BEAC1) {', 1)


def recovered_guards(before, old, new):
    a, b = parse_object(old), parse_object(new); name = 'func_1501878C'
    f, g = a[1][name], b[1][name]
    if f['size'] != 1644 or g['size'] != 1644: raise ValueError('Changed frame-driver extent')
    for p, q, wanted in ((a, f, '891ed2b97a7d62cd4862c65ce530b933b33f3ebd8858baafd7df5dc0e5f3b178'),
            (b, g, 'a829527cf77c7e22c8d5f7a9f0c7c35854ffedffdc01a8d797677849cdc743e3')):
        raw_bytes = p[0][q['value']:q['value'] + q['size']]
        bindings = {i - q['value']:v for i, v in p[2].items() if q['value'] <= i < q['value'] + q['size']}
        if hashlib.sha256(raw_bytes).hexdigest() != wanted or hashlib.sha256(json.dumps(bindings, sort_keys=True).encode()).hexdigest() != (
                '0f89518b245f4d2dd5bca3a9c47c5fe918573330dc5730146bbb1cf8962899fb'):
            raise ValueError('Unknown frame-driver words or bindings')
    raw = lambda p, q:list(struct.unpack('>411I', p[0][q['value']:q['value'] + q['size']]))
    x, y = raw(a, f), raw(b, g)
    changes = {i * 4:(v, w) for i, (v, w) in enumerate(zip(x, y)) if v != w}
    if set(changes) != {0x558, 0x55C, 0x568, 0x588, 0x58C, 0x590, 0x598, 0x59C, 0x5B0}:
        raise ValueError('Unknown frame-driver void-call allocation changes')
    lines = before.splitlines(keepends=True); rows = list(csv.DictReader(io.StringIO(before.decode())))
    if len(lines) != len(rows) + 1: raise ValueError('Unknown multiline guard format')
    removed = set(); result = [lines[0]]
    for line, row in zip(lines[1:], rows):
        at = int(row['offset'], 16)
        if row['filename'] == 'game_45B80' and row['function'] == name and at in changes:
            prior, current = changes[at]
            binding = lambda p, q:';'.join(kind + ':' + symbol for kind, symbol in p[2].get(q['value'] + at, [])) or '-'
            if (int(row['expected'], 16), int(row['replacement'], 16)) != (prior, current) or at in removed or (
                    row['expected_relocations'] != binding(a, f) or row['replacement_relocations'] != binding(b, g) or
                    row['insert_after'] or row['insert_after_relocations'] or row['omit'] != 'false'):
                raise ValueError('Unknown obsolete frame-driver guard')
            removed.add(at)
        else: result.append(line)
    if removed != set(changes): raise ValueError('Missing obsolete frame-driver guard')
    return b''.join(result)


def measure(root, out, label, body):
    freeze(root, out)
    obj, diagnostics = profiles.compile_owner(root, out,
        recovered_owner((out / 'before-view_list_caller_owner').read_text(), body), label, True)
    text, functions, relocations = parse_object(obj); f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    data, placed = build.link_owner(root, out, obj, OWNER)
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, placed[FUNCTION]['value']))
    truth = list(struct.unpack_from('>239I', (out / 'before-retail_rom').read_bytes(), ROM))
    row = dict(label=label, words=len(words), frame=(-words[0]) & 65535, diagnostics=diagnostics,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS),
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        bindings={at - f['value']:r for at, r in relocations.items() if f['value'] <= at < f['value'] + f['size']},
        pools={n:d.hex() for n, (_, d) in sections(obj).items()
            if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d},
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
    if len(raw) != 956 or hashlib.sha256(raw).hexdigest() != RAW_SHA256 or bindings != RELOCATIONS or pools:
        raise ValueError('Unknown graphics submission words/bindings/pools')
    return raw


def same_functions(old, new, excluded=()):
    a, b = parse_object(old), parse_object(new)
    if set(a[1]) != set(b[1]): raise ValueError('Changed graphics owner function set')
    rel = lambda p, f:{at - f['value']:r for at, r in p[2].items() if f['value'] <= at < f['value'] + f['size']}
    for name, f in a[1].items():
        if name in excluded: continue
        g = b[1][name]
        if a[0][f['value']:f['value'] + f['size']] != b[0][g['value']:g['value'] + g['size']] or rel(a, f) != rel(b, g):
            raise ValueError('Changed graphics neighbor/caller: ' + name)
    return len(a[1]) - len(excluded)


def qualify(root, out):
    obj, words, row = measure(root, out, 'qualified', SELECTED); checked_object(obj)
    old, diag = profiles.compile_owner(root, out, (out / 'before-view_list_caller_owner').read_text(), 'neighbor-before', True)
    neighbors = same_functions(old, obj, (FUNCTION,))
    caller = (out / 'before-dispatch_owner').read_text()
    caller_before, before_diag = build.compile_owner(root, out, caller, 'caller-before')
    caller_after, after_diag = build.compile_owner(root, out, recovered_caller(caller), 'caller-after')
    callers = same_functions(caller_before, caller_after, ('func_1501878C',))
    if row['diagnostics'] or diag or before_diag.count('cfe: Warning 712:') != 4 or (
            before_diag.replace('caller-before.c', 'caller-after.c') != after_diag):
        raise ValueError('Changed graphics submission diagnostics')
    guards = out / 'qualified-guards.csv'
    guards.write_bytes(recovered_guards((out / 'before-guards').read_bytes(), caller_before, caller_after))
    caller_objects = []
    for label, raw, manifest in (('caller-padded-before', caller_before, out / 'before-guards'),
            ('caller-padded-after', caller_after, guards)):
        script = out / (label + '.s')
        script.write_text(pad_c_object.emit_padded_assembly(raw, root / PATHS['layout'], 'game_45B80', word_patches_path=manifest))
        padded_caller = script.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded_caller), str(script)], capture_output=True, check=True)
        caller_objects.append(padded_caller)
    normalized_callers = same_functions(*caller_objects)
    assembly = out / 'qualified-padded.s'
    assembly.write_text(pad_generated_object.emit_padded_assembly(obj, out / 'before-view_list_caller_original',
        word_patches_path=guards, filename=OWNER))
    padded = assembly.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(assembly)], capture_output=True, check=True)
    data, functions = build.link_owner(root, out, padded, OWNER); f = functions[FUNCTION]
    if f['size'] != 956 or data[f['value']:f['value'] + 956] != (out / 'before-retail_rom').read_bytes()[ROM:ROM + 956]:
        raise ValueError('Graphics submission padded slot differs')
    row.update(byte_exact=True, new_guards=0, removed_caller_guards=9, unchanged_caller_warnings=4, unchanged_no_unroll_neighbors=neighbors,
        unchanged_raw_caller_neighbors=callers, unchanged_caller_functions=normalized_callers)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, words, row


def expected_inputs(root, out):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    before = (out / 'before-elf').read_bytes()
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']: raise ValueError('Changed graphics submission predecessor image')
    row = next(r for r in symbol_rows(before) if r[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12): raise ValueError('Unknown graphics submission predecessor extent')
    data = bytearray(before); at = elf_slot_offset(before, ENTRY, 956)
    data[at:at + 956] = (out / 'before-retail_rom').read_bytes()[ROM:ROM + 956]
    struct.pack_into('>I', data, row[0] + 8, 956)
    from tools.tests import test_game_actor_burst_packet_match as serialization
    with patch.object(serialization, 'SERIALIZATION', SERIALIZATION):
        serialization.apply_burst_symbol_serialization(data)
    return dict(elf=bytes(data), view_list_caller_owner=recovered_owner((out / 'before-view_list_caller_owner').read_text()).encode(),
        dispatch_owner=recovered_caller((out / 'before-dispatch_owner').read_text()).encode(),
        guards=recovered_guards((out / 'before-guards').read_bytes(), out / 'caller-before.o', out / 'caller-after.o'))


def prelink_prediction(root, out):
    _, padded, _, _ = qualify(root, out)
    live = lambda:{k:hashlib.sha256((root / p).read_bytes()).hexdigest() for k, p in PATHS.items()}
    capture = out / 'link-inputs.json'
    if not capture.exists():
        if live() != BASELINE: raise ValueError('Graphics submission capture must precede installation')
        for name, path in (('before-linkscript', 'conker/build/conker.ld'),
                ('before-task-owner.o', 'conker/build/src/game/generated_49D30.c.o'),
                ('before-caller-owner.o', 'conker/build/src/game_45B80.c.o')):
            (out / name).write_bytes((root / path).read_bytes())
        capture.write_text(json.dumps({n:hashlib.sha256((out / n).read_bytes()).hexdigest()
            for n in ('before-linkscript', 'before-task-owner.o', 'before-caller-owner.o')}, indent=2) + '\n')
    for name, digest in json.loads(capture.read_text()).items():
        if hashlib.sha256((out / name).read_bytes()).hexdigest() != digest: raise ValueError('Changed graphics submission link capture')
    for label, task, caller in (('baseline', out / 'before-task-owner.o', out / 'before-caller-owner.o'),
            ('prediction', padded, out / 'caller-padded-after.o')):
        link = (out / 'before-linkscript').read_text()
        for needle, obj in (('build/src/game/generated_49D30.c.o(.text);', task), ('build/src/game_45B80.c.o(.text);', caller)):
            if link.count(needle) != 1: raise ValueError('Unknown graphics submission link selector')
            link = link.replace(needle, str(obj.relative_to(root / 'conker')) + '(.text);', 1)
        script = out / (label + '.ld'); script.write_text(link)
        subprocess.run(['mips-linux-gnu-ld', '-T', str(script.relative_to(root / 'conker')),
            '-T', 'undefined_syms.us.txt', '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt',
            '-T', 'undefined_funcs_auto.txt', '--no-check-sections', '--no-warn-mismatch',
            '-o', str((out / ('prelink-' + label + '.elf')).relative_to(root / 'conker'))], cwd=root / 'conker', capture_output=True, check=True)
    if (out / 'prelink-baseline.elf').read_bytes() != (out / 'before-elf').read_bytes(): raise ValueError('Graphics submission predecessor not reproduced')
    expected = expected_inputs(root, out); actual = (out / 'prelink-prediction.elf').read_bytes()
    if actual != expected['elf']: raise ValueError('Graphics submission link differs outside the first slot/extent prediction')
    hashes = {k:hashlib.sha256(v).hexdigest() for k, v in expected.items()}; initial = out / 'initial-prediction.json'
    if not initial.exists():
        if live() != BASELINE: raise ValueError('Graphics submission prediction must precede installation')
        initial.write_text(json.dumps(hashes, indent=2) + '\n')
    if json.loads(initial.read_text()) != hashes: raise ValueError('Changed first graphics submission prediction')
    row = dict(after=hashes, changed_ELF_bytes=sum(a != b for a, b in zip((out / 'before-elf').read_bytes(), actual)),
        body_bytes=956, new_guards=0, removed_caller_guards=9, exact_symbol_groups=3, metadata_exclusions=0)
    (out / 'prelink-prediction.json').write_text(json.dumps(row, indent=2) + '\n'); return row


def installation_patch(root, out):
    expected = expected_inputs(root, out)
    if json.loads((out / 'initial-prediction.json').read_text()) != {k:hashlib.sha256(v).hexdigest() for k, v in expected.items()}:
        raise ValueError('Changed graphics submission installation prediction')
    patches = []
    for key, after in expected.items():
        if key == 'elf': continue
        path = root / PATHS[key]; before = path.read_bytes()
        if hashlib.sha256(before).hexdigest() != BASELINE[key]: raise ValueError('Changed graphics submission source/guards before installation')
        diff = list(difflib.unified_diff(before.decode().splitlines(), after.decode().splitlines(), n=3, lineterm=''))
        patches.append('*** Update File: ' + str(path) + '\n' + '\n'.join(
            '@@' if line.startswith('@@') else line for line in diff[2:]))
    return '*** Begin Patch\n' + '\n'.join(patches) + '\n*** End Patch\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--forms', action='store_true')
    parser.add_argument('--signed', action='store_true')
    parser.add_argument('--word', action='store_true')
    parser.add_argument('--access', action='store_true')
    parser.add_argument('--tail', action='store_true')
    parser.add_argument('--opening', action='store_true')
    parser.add_argument('--prelink', action='store_true'); parser.add_argument('--prepare', action='store_true'); args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if args.prelink:
        print(json.dumps(prelink_prediction(root, root / BUILD), indent=2), flush=True); raise SystemExit(0)
    if args.prepare:
        print(installation_patch(root, root / BUILD), end=''); raise SystemExit(0)
    for label, body in opening_forms() if args.opening else tail_forms() if args.tail else access_forms() if args.access else word_forms() if args.word else signed_forms() if args.signed else forms() if args.forms else [('initial', SELECTED)]:
        row = measure(root, root / BUILD, label, body)[2]
        print(json.dumps({k:row[k] for k in ('label', 'words', 'frame', 'differences', 'diagnostics', 'raw_sha256', 'pools')}), flush=True)
