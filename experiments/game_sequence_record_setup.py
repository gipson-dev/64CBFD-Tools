"""Recover the complete gated sequence-record setup before any installation credit."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_sequence_state_reset as previous
from tools.tests import sequence_state_reset_checkpoint as checkpoint
from tools.experiments.game_view_list_setup import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-sequence-record-setup'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_49D30', 'func_1501D348', 0x1501D348, 0x4A7F8, 473
PATHS = dict(previous.PATHS)
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER)
build = previous.build
DECLARATIONS = '''typedef struct {
    u16 activeCount;
    u16 fallbackCount;
    u16 preferredCount;
    u16 auxiliaryCount;
} SequenceHeader49D30;
typedef struct {
    u8 *data;
    u32 bytes;
} SequenceDescriptor49D30;
typedef struct {
    u8 pad00[4];
    u32 *items;
    u8 pad08[0x30];
    u8 *scratch;
    u8 pad3C[4];
} SequenceRuntime49D30;
extern u8 D_800C35C4, D_800C35C5, D_800C35E8[], D_800C3C90, D_800C3C98;
extern s8 D_800C35A8;
extern s32 D_800BE9F0, D_800C3C94;
extern u8 **D_800C35E0[];
extern SequenceRuntime49D30 *D_800C3A50[];
extern u8 *D_800C3958[], *D_800C3868[][30];
extern s16 D_800C3C9A;
extern u8 D_800DBFF4;
extern void (*D_800840FC[])(s32, s32, s32, s32);
s32 allocate_memory(s32, s32, s32, s32);
void func_1501C730(s32, s32, s32, s32, s32);
s32 func_15022BA4();
s32 func_15020388();
s32 func_150238D0();
void func_15022234(s32);
void func_15022248(s32);
s32 func_1501E81C();
s32 func_150242F8();
s32 func_1501EC38();
s32 func_15022848();
void func_15022754(s32);
s32 func_15022528();
s32 func_15020EC4();
s32 func_1501DAAC();

'''
INITIAL = '''/* Allocate and publish a slot's record groups, then run its setup providers. */
void func_1501D348(s32 scene, s32 sequence, s32 slot, s32 hook, s32 parameter) {
    u8 *status;
    u8 state;
    SequenceDescriptor49D30 *bundle;
    SequenceDescriptor49D30 *descriptor;
    SequenceHeader49D30 *header;
    u16 **enabled;
    u16 **fallback;
    u16 **preferred;
    u8 ***auxiliary;
    SequenceRuntime49D30 **runtime;
    u8 **pointers;
    RecordMaximum49D30 **preferredPointers;
    s32 i;
    s32 cursor;
    s32 capacity;
    s32 bytes;
    void *allocated;
    u16 total;
    u16 entries;

    status = &D_800C35EA[slot];
    state = *status;
    if (state == 1 || D_800C35C4 != 0) return;
    D_800C3C90 = hook;
    D_800C3C94 = parameter;
    if (scene != D_800BE9F0) {
        D_800C35C4 = (u32)sequence + 1U;
        func_1501C730(1, scene, 0, 0, 0);
        if (*status != 0) D_800C35C5 = 0;
        else D_800C35C5 = 1;
        return;
    }
    D_800C35E8[slot] = sequence;
    if (state != 2) {
        D_800C35A8 = D_800BE9F0;
        D_800C3C98 = sequence;
    }
    func_1501D044(slot);
    if (func_1501D1D4(scene, sequence, slot) == 0) return;
    bundle = (SequenceDescriptor49D30 *)D_800C3668[slot];
    header = (SequenceHeader49D30 *)bundle[0].data;
    enabled = &D_800C35C8[slot];
    *enabled = (void *)allocate_memory(header->activeCount * 2, 1, 0, 0);
    cursor = 1;
    i = 0;
    if (header->activeCount > 0) {
        descriptor = bundle + 1;
        do {
            (*enabled)[i] = descriptor->bytes >> 3;
            i++;
            descriptor++;
        } while (i < header->activeCount);
        i = 0;
    }
    capacity = header->fallbackCount;
    if (capacity < header->activeCount) capacity = header->activeCount;
    bytes = capacity * 2;
    fallback = &D_800C35D0[slot];
    *fallback = (void *)allocate_memory(bytes, 1, 0, 0);
    bzero(*fallback, bytes);
    capacity = header->preferredCount;
    if (capacity < header->activeCount) capacity = header->activeCount;
    bytes = capacity * 2;
    preferred = &D_800C35D8[slot];
    *preferred = (void *)allocate_memory(bytes, 1, 0, 0);
    bzero(*preferred, bytes);
    auxiliary = &D_800C35E0[slot];
    *auxiliary = (void *)allocate_memory(header->auxiliaryCount * 4, 1, 0, 0);
    runtime = &D_800C3A50[slot];
    *runtime = (void *)allocate_memory(header->activeCount * 0x40, 1, 0, 0);
    if (header->activeCount > 0) {
        do {
            entries = (*enabled)[i];
            if (entries != 0) {
                allocated = (void *)allocate_memory(entries * 4, 1, 0, 0);
                (*runtime)[i].items = allocated;
                allocated = (void *)allocate_memory(0x194, 1, 0, 0);
                (*runtime)[i].scratch = allocated;
            }
            i++;
        } while (i < header->activeCount);
        i = 0;
    }
    D_800C3958[slot] = (void *)allocate_memory(header->activeCount * 0x44, 1, 0, 0);
    if (header->activeCount > 0) {
        pointers = &D_800C3960[slot][0];
        do {
            *pointers = (void *)allocate_memory(0x10, 1, 0, 0);
            i++;
            pointers++;
        } while (i < header->activeCount);
        i = 0;
    }
    if (header->activeCount > 0) {
        do {
            (*preferred)[i] = 0;
            (*fallback)[i] = 0;
            (*enabled)[i] = 0;
            i++;
        } while (i < header->activeCount);
        i = 0;
    }
    D_800C363A[slot] = header->activeCount;
    if (header->activeCount > 0) {
        pointers = &D_800C3868[slot][0];
        descriptor = bundle + 1;
        do {
            (*enabled)[i] = descriptor->bytes >> 3;
            *pointers++ = descriptor->data;
            i++;
            cursor++;
            descriptor++;
        } while (i < header->activeCount);
        i = 0;
    }
    D_800C35F0[slot] = bundle[cursor].data;
    /* Retail skips another activeCount descriptors before the fallback group. */
    cursor += header->activeCount;
    if (header->fallbackCount > 0) {
        pointers = &D_800C3778[slot][0];
        descriptor = bundle + cursor;
        do {
            (*fallback)[i] = descriptor->bytes >> 3;
            *pointers++ = descriptor->data;
            i++;
            cursor++;
            descriptor++;
        } while (i < header->fallbackCount);
        i = 0;
    }
    if (header->preferredCount > 0) {
        preferredPointers = &D_800C3688[slot][0];
        descriptor = bundle + cursor;
        do {
            (*preferred)[i] = descriptor->bytes >> 3;
            *preferredPointers++ = (RecordMaximum49D30 *)descriptor->data;
            i++;
            cursor++;
            descriptor++;
        } while (i < header->preferredCount);
        i = 0;
    }
    if (header->auxiliaryCount > 0) {
        descriptor = bundle + cursor;
        do {
            (*auxiliary)[i] = descriptor->data;
            i++;
            descriptor++;
        } while (i < header->auxiliaryCount);
        i = 0;
    }
    if (hook != 0) D_800840FC[hook](scene, sequence, slot, parameter);
    total = func_1501CFF8(slot);
    D_800C3C9A = (s16)total;
    D_800C3D50 = (void *)allocate_memory(total * 12, 1, 0, 0);
    D_800C35B0[slot] = 0;
    func_1501CDC0(slot);
    func_1501CE54(slot);
    func_15022BA4(slot);
    if (D_800C363A[slot] > 0) {
        do { func_15020388(i, slot); i++; } while (i < D_800C363A[slot]);
    }
    func_150238D0();
    *status = 1;
    D_800C3638 = 1;
    func_15022234(slot);
    func_15022248(slot);
    if (D_800C363A[slot] == 0) func_1501E81C(0, slot);
    func_150242F8(1, slot);
    func_1501EC38(slot);
    func_15022848(slot);
    func_15022754(slot);
    func_15022528(slot);
    func_15020EC4(slot);
    D_800DBFF4 = 4;
    func_1501DAAC(slot);
}'''
SELECTED = INITIAL


def offset_forms():
    body=SELECTED.replace('    s32 i;','    s32 i;\n    s32 offset;')
    for name in ('enabled','fallback','preferred'):
        body=body.replace('(*%s)[i]'%name,'*(u16 *)((u8 *)*%s + offset)'%name)
    body=body.replace('(*auxiliary)[i]','*(u8 **)((u8 *)*auxiliary + offset)')
    # Keep one byte-offset cursor separate from the element-count loop index.
    parts=body.split('        do {\n');result=parts[0]
    for part in parts[1:]:
        loop,rest=part.split('        } while (',1)
        if '+ offset)' in loop:
            result+='        offset = 0;\n'
            step=4 if '*(u8 **)' in loop else 2
            loop=loop.replace('            i++;','            i++;\n            offset += %d;'%step)
        result+='        do {\n'+loop+'        } while ('+rest
    yield 'shared-byte-offset',result


def runtime_forms():
    body=SELECTED.replace('SequenceRuntime49D30 **runtime;','u8 **runtime;').replace(
        'runtime = &D_800C3A50[slot];','runtime = (u8 **)&D_800C3A50[slot];').replace(
        '(*runtime)[i].items','*(u32 **)(*runtime + i * 0x40 + 4)').replace(
        '(*runtime)[i].scratch','*(u8 **)(*runtime + i * 0x40 + 0x38)')
    yield 'byte-runtime-view',body
    scoped=SELECTED.replace('    RecordMaximum49D30 **preferredPointers;\n','').replace(
        '    if (header->preferredCount > 0) {','    if (header->preferredCount > 0) {\n        RecordMaximum49D30 **preferredPointers;')
    yield 'scoped-preferred-cursor',scoped


def total_forms():
    body=SELECTED.replace('    u16 total;\n','').replace(
        '    total = func_1501CFF8(slot);\n    D_800C3C9A = (s16)total;',
        '    D_800C3C9A = func_1501CFF8(slot);').replace('total * 12','(u16)D_800C3C9A * 12')
    yield 'global-total',body
    yield 'explicit-total-address',body.replace('    s32 bytes;', '    s32 bytes;\n    s16 *totalOutput;').replace(
        '    D_800C3C9A = func_1501CFF8(slot);',
        '    totalOutput = &D_800C3C9A;\n    *totalOutput = func_1501CFF8(slot);').replace('(u16)D_800C3C9A * 12','(u16)*totalOutput * 12')


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    for key, relative in PATHS.items():
        data = (root / relative).read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE[key]: raise ValueError('Unknown record setup input: ' + key)
        target = out / ('before-' + key)
        if not target.exists(): target.write_bytes(data)
        if target.read_bytes() != data: raise ValueError('Changed record setup fixture: ' + key)


def recovered_owner(before, body=None):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1501D348() {\n    return 0;\n}': raise ValueError('Unknown record setup predecessor')
    marker = 'void func_150233BC(void);\n'
    if before.count(marker) != 1 or 'SequenceHeader49D30' in before: raise ValueError('Unknown record setup declarations')
    return (before[:lo] + (SELECTED if body is None else body) + before[hi:]).replace(marker, marker + '\n' + DECLARATIONS, 1)


def measure(root, out, label, body):
    freeze(root, out)
    obj, diagnostics = compile_owner(root, out, recovered_owner((out / 'before-view_list_caller_owner').read_text(), body), label, True)
    text, functions, relocations = parse_object(obj); f = functions[FUNCTION]; raw = text[f['value']:f['value'] + f['size']]
    data, placed = build.link_owner(root, out, obj, OWNER)
    words = list(struct.unpack_from('>%dI' % (f['size'] // 4), data, placed[FUNCTION]['value']))
    truth = list(struct.unpack_from('>473I', (out / 'before-retail_rom').read_bytes(), ROM))
    row = dict(label=label, words=len(words), frame=-((words[0] & 65535) - 65536), diagnostics=diagnostics,
        differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words) - WORDS), raw_sha256=hashlib.sha256(raw).hexdigest(),
        bindings={at - f['value']:r for at, r in relocations.items() if f['value'] <= at < f['value'] + f['size']},
        pools={n:d.hex() for n, (_, d) in sections(obj).items() if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d})
    (out / (label + '.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, words, row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--offsets',action='store_true')
    parser.add_argument('--runtime',action='store_true');parser.add_argument('--totals',action='store_true');args=parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    for label,body in total_forms() if args.totals else runtime_forms() if args.runtime else offset_forms() if args.offsets else [('selected',SELECTED)]:
        row = measure(root, root / BUILD, label, body)[2]
        print(json.dumps({k:v for k,v in row.items() if k != 'bindings'}, indent=2), flush=True)
