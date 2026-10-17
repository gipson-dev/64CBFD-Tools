"""Recover the complete six-query sequence flag/color scan before installation."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_sequence_record_setup_installation as previous
from tools.tests import sequence_record_setup_checkpoint as checkpoint
from tools.experiments.game_view_list_setup import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-sequence-event-scan'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_49D30', 'func_1501DAAC', 0x1501DAAC, 0x4AF5C, 219
PATHS = dict(previous.PATHS)
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER)
PATHS['color_provider_original'] = 'conker/asm/1AC2F0.s'
BASELINE['color_provider_original'] = '986998c8d258929b7f39cfec89be4ae5a892fff9355a75c8fa33f5221f5a2258'
build = previous.source.build
DECLARATIONS = '''typedef struct {
    u8 pad00[5];
    s8 colorIndex;
    s16 mode;
} SequenceEvent49D30;
extern u8 D_800C3C99, D_800C3C9C, D_800C35A9, D_800C35AA;
extern u8 D_80084110[][3];
s32 func_15023BB0(u8 *, s32, s32, SequenceEvent49D30 **,
    s32, s32, s32, s32, s32, s32, s32);
void func_1517EE40(s32, s32, s32, s32, s32, s32);

'''
INITIAL = '''/* Collect live sequence flags and submit each improving color selection. */
void func_1501DAAC(s32 slot) {
    SequenceEvent49D30 *event;
    u8 *count;
    s32 best;
    RecordMaximum49D30 **record;
    u8 *commands;
    s32 value;
    s32 index;
    u8 *color;

    D_800C3C99 = 0;
    D_800C35A9 = 0;
    D_800C3C9C = 0;
    D_800C35AA = 0;
    count = &D_800C363A[slot];
    D_800C3C8E = 0;
    best = -1;
    index = 0;
    if (*count > 0) {
        record = D_800C3688[slot];
        do {
            commands = (u8 *)*record + 0x18;
            if (*record != NULL) {
                event = NULL;
                func_15023BB0(commands, 5, index, &event, 1, 0x1E, 0, 0, 0, 0, slot);
                if (event != NULL) D_800C3C99 = 1;
                event = NULL;
                func_15023BB0(commands, 5, index, &event, 1, 0x0E, 0, 0, 0, 0, slot);
                if (event != NULL) D_800C3C9C = 1;
                event = NULL;
                func_15023BB0(commands, 5, index, &event, 1, 0x68, 0, 0, 0, 0, slot);
                if (event != NULL) D_800C35AA = 1;
                event = NULL;
                func_15023BB0(commands, 5, index, &event, 1, 0x44, 0, 0, 0, 0, slot);
                if (event != NULL) D_800C35A9 = 1;
                event = NULL;
                value = func_15023BB0(commands, 5, index, &event, 1, 0x77, 0, 0, 0, 0, slot);
                if (event != NULL) D_800C3C8E = value;
                event = NULL;
                value = func_15023BB0(commands, 5, index, &event, 1, 1, 1, 0, 0, 0, slot);
                if (event != NULL && (best == -1 || value < best)) {
                    best = value;
                    if (event->mode == 1) {
                        color = D_80084110[event->colorIndex];
                        func_1517EE40(color[0], color[1], color[2], 0, 1, 0);
                    } else {
                        color = D_80084110[event->colorIndex];
                        func_1517EE40(color[0], color[1], color[2], 0, 0, 0);
                    }
                }
            }
            index++;
            record++;
        } while (index < *count);
    }
    D_800C35B0[slot] = (u16)D_800C3C8E;
}'''


def forms():
    yield 'initial', INITIAL
    no_color = INITIAL.replace('    u8 *color;\n', '').replace(
        '                        color = D_80084110[event->colorIndex];\n', '').replace(
        'color[0], color[1], color[2]',
        'D_80084110[event->colorIndex][0], D_80084110[event->colorIndex][1], D_80084110[event->colorIndex][2]')
    yield 'inline-color', no_color
    declarations = no_color[no_color.index('    SequenceEvent49D30 *event;'):no_color.index('\n\n    D_800C3C99')]
    retail_homes = '''    s32 best;
    s32 value;
    SequenceEvent49D30 *event;
    RecordMaximum49D30 **record;
    u8 *commands;
    u8 *count;
    s32 index;'''
    yield 'retail-homes', no_color.replace(declarations,retail_homes)
    yield 'retail-homes-scoped', no_color.replace(declarations,retail_homes.replace('    s32 value;\n','')).replace(
        '            if (*record != NULL) {\n', '            if (*record != NULL) {\n                s32 value;\n', 1)
    for label, body in (('initial', INITIAL), ('inline-color', no_color)):
        for position in ('tail', 'after-count', 'after-best', 'after-record', 'after-value'):
            changed = body.replace('    SequenceEvent49D30 *event;\n', '')
            marker = dict(tail='    s32 index;\n', **{'after-count':'    u8 *count;\n',
                'after-best':'    s32 best;\n', 'after-record':'    RecordMaximum49D30 **record;\n',
                'after-value':'    s32 value;\n'})[position]
            yield label+'-event-'+position, changed.replace(marker, marker+'    SequenceEvent49D30 *event;\n', 1)


SELECTED = dict(forms())['retail-homes']


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    for key, relative in PATHS.items():
        data = (root / relative).read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            from tools.tests import sequence_event_scan_checkpoint as installed
            data = installed.previous_input(data,relative,root)
        if hashlib.sha256(data).hexdigest() != BASELINE[key]: raise ValueError('Unknown event scan input: ' + key)
        target = out / ('before-' + key)
        if not target.exists(): target.write_bytes(data)
        if target.read_bytes() != data: raise ValueError('Changed event scan fixture: ' + key)


def recovered_owner(before, body=None):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1501DAAC() {\n    return 0;\n}': raise ValueError('Unknown event scan predecessor')
    marker = 's32 func_1501DAAC();\n'
    if before.count(marker) != 1 or 'SequenceEvent49D30' in before: raise ValueError('Unknown event scan declarations')
    result = before[:lo] + (SELECTED if body is None else body) + before[hi:]
    return result.replace(marker, 'void func_1501DAAC(s32 slot);\n' + DECLARATIONS, 1)


def measure(root, out, label, body):
    freeze(root, out)
    obj, diagnostics = compile_owner(root, out, recovered_owner((out / 'before-view_list_caller_owner').read_text(), body), label, True)
    text, functions, relocations = parse_object(obj); f = functions[FUNCTION]
    data, placed = build.link_owner(root, out, obj, OWNER)
    raw = text[f['value']:f['value'] + f['size']]
    words = list(struct.unpack_from('>%dI' % (f['size']//4), data, placed[FUNCTION]['value']))
    truth = list(struct.unpack_from('>219I', (out / 'before-retail_rom').read_bytes(), ROM))
    row = dict(label=label, words=len(words), differences=sum(a != b for a, b in zip(words, truth)) + abs(len(words)-WORDS),
        frame=(-((words[0] & 65535)-65536)), diagnostics=diagnostics, raw_sha256=hashlib.sha256(raw).hexdigest(),
        bindings={at-f['value']:r for at,r in relocations.items() if f['value'] <= at < f['value']+f['size']},
        pools={n:d.hex() for n,(_,d) in sections(obj).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d})
    (out / (label + '.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj, words, row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--forms',action='store_true'); args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    for label,body in forms() if args.forms else [('selected',SELECTED)]:
        row = measure(root,root/BUILD,label,body)[2]
        print(json.dumps({k:row[k] for k in ('label','words','differences','frame','diagnostics','raw_sha256')},indent=2),flush=True)
