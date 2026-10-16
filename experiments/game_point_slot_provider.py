"""Recover the packed point range's sixteen-pointer slot table."""
import argparse
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_packed_point_transform as previous
from tools.experiments import game_packet_rectangle as engine
from tools.tests import packed_point_transform_checkpoint as checkpoint
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.experiments.game_actor_classifier_candidates import sections

BUILD = 'conker/build/game-point-slot-provider'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_C1D70', 'func_1509499C', 0x1509499C, 0xC1E4C, 71
PATHS = previous.PATHS
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER)
build = previous.build
INITIAL = '''/* Build sixteen point slots from the packed inclusive range; clear unused slots. */
void func_1509499C(PackedPointSource948C0 *source, s16 **slots) {
    u8 range = source->slotRange;
    s16 *point = (s16 *)source->points;
    s32 index = 0;
    s16 first = range & 0xF;
    s16 end = (range >> 4) + 1;

    for (; index < first; index++) {
        slots[index] = NULL;
    }
    for (index = first; index < end; index++) {
        slots[index] = point;
        point += 8;
    }
    for (; index < 16; index++) {
        slots[index] = NULL;
    }
}'''
RAW_SHA256 = '0cb01a05cbec562a37a4ba900c6a3cb3668e3fcf016668627a71859d32c49f64'
SLOT_SHA256 = '00996153493e8ce73b27bc32ac67eb55774ec90af0896987c6fc80d5ed1ba330'
GUARDS = {
    0: (0x90860001, 0x90830001),
    12: (0x30C3000F, 0x3066000F),
    16: (0x00064103, 0x0003C103),
    20: (0x00037400, 0x00067400),
    24: (0x25080001, 0x27030001),
    32: (0x0008C400, 0x0003CC00),
    36: (0x01E01825, 0x01E03025),
    44: (0x00184403, 0x00191C03),
    56: (0x01203025, 0x01204025),
    60: (0x00005080, 0x00005880),
    64: (0x00AA2021, 0x00AB2021),
    76: (0x14C7FFFD, 0x1507FFFD),
    84: (0x10E3000A, 0x10E6000A),
    88: (0x00075880, 0x00076080),
    92: (0x00036080, 0x00066880),
    96: (0x01853021, 0x01A54021),
    100: (0x00AB2021, 0x00AC2021),
    120: (0x1486FFFB, 0x1488FFFB),
    128: (0x0068082A, 0x00C3082A),
    136: (0x00603825, 0x00C03825),
    140: (0x01034823, 0x00664823),
    144: (0x312D0003, 0x312E0003),
    148: (0x11A00009, 0x11C00009),
    152: (0x01A33021, 0x01C64021),
    156: (0x00037080, 0x00067880),
    160: (0x00AE2021, 0x00AF2021),
    176: (0x14C7FFFC, 0x1507FFFC),
    184: (0x10E8000D, 0x10E3000D),
    188: (0x00077880, 0x0007C080),
    192: (0x00AF2021, 0x00B82021),
    232: (0x14E8FFF6, 0x14E3FFF6),
    248: (0x0007C080, 0x0007C880),
    252: (0x00B82021, 0x00B92021),
}


def freeze(root, out):
    from tools.tests import point_slot_provider_checkpoint as current
    out.mkdir(parents=True, exist_ok=True)
    read = Path.read_bytes
    with patch.object(Path, 'read_bytes', lambda p:current.previous_input(read(p), p, root)), \
            patch.multiple(engine, PATHS=PATHS, BASELINE=BASELINE):
        engine.freeze(root, out)


def recovered_owner(before, body=None):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_1509499C() {\n    return 0;\n}':
        raise ValueError('Unknown point-slot provider predecessor')
    proto = 's32 func_1509499C();'
    if before.count(proto) != 1:
        raise ValueError('Unknown point-slot provider prototype')
    return (before[:lo] + (SELECTED if body is None else body) + before[hi:]).replace(
        proto, 'void func_1509499C(PackedPointSource948C0 *, s16 **);', 1)


def forms():
    yield 'for-range', INITIAL
    for kind in ('s16', 'u16', 'u32', 'const u8', 'register u8'):
        yield 'packed-type-'+kind.replace(' ', '-'), INITIAL.replace('u8 range =', kind+' range =')
    yield 'for-zero', INITIAL.replace('for (; index < first;', 'for (index = 0; index < first;')
    yield 'uninitialized-index', INITIAL.replace('s32 index = 0;', 's32 index;').replace(
        'for (; index < first;', 'for (index = 0; index < first;')
    yield 'pointer-after-bounds', INITIAL.replace('    s16 *point = (s16 *)source->points;\n', '').replace(
        '    s16 end = (range >> 4) + 1;', '    s16 end = (range >> 4) + 1;\n    s16 *point = (s16 *)source->points;')
    yield 'post-increment-clear', INITIAL.replace('for (; index < first; index++) {\n        slots[index] = NULL;',
        'for (; index < first;) {\n        slots[index++] = NULL;').replace(
        'for (; index < 16; index++) {\n        slots[index] = NULL;',
        'for (; index < 16;) {\n        slots[index++] = NULL;')
    yield 'wide-range', INITIAL.replace('u8 range =', 's32 range =')
    yield 'field-bounds', INITIAL.replace('    u8 range = source->slotRange;\n', '').replace(
        'range & 0xF', 'source->slotRange & 0xF').replace('(range >> 4)', '(source->slotRange >> 4)')
    head, loops = INITIAL.split('\n    for (; index < first;', 1)
    declarations = dict(point='    s16 *point = (s16 *)source->points;',
        index='    s32 index = 0;', first='    s16 first = source->slotRange & 0xF;',
        end='    s16 end = (source->slotRange >> 4) + 1;')
    opening = INITIAL.split('    u8 range =', 1)[0]
    for order in itertools.permutations(declarations):
        field = opening+'\n'.join(declarations[k] for k in order)+'\n\n    for (; index < first;'+loops
        yield 'fields-'+'-'.join(order), field
        yield 'loop-init-'+'-'.join(order), field.replace('s32 index = 0;', 's32 index;').replace(
            'for (; index < first;', 'for (index = 0; index < first;')
    plain = dict(point='    s16 *point;', index='    s32 index;', first='    s16 first;', end='    s16 end;')
    assignments = '''    point = (s16 *)source->points;
    index = 0;
    first = source->slotRange & 0xF;
    end = (source->slotRange >> 4) + 1;'''
    for order in itertools.permutations(plain):
        yield 'assign-'+'-'.join(order), opening+'\n'.join(plain[k] for k in order)+'\n\n'+assignments+'\n\n    for (; index < first;'+loops
    prefix = '    for (; index < first; index++) {\n        slots[index] = NULL;\n    }'
    for label, base in (('cached', INITIAL), ('fields', dict(forms_head())['fields'])):
        for comparison in ('<', '!='):
            guarded = '    if (first > 0) {\n        do {\n            slots[index] = NULL;\n            index++;\n        } while (index '+comparison+' first);\n    }'
            yield 'guard-'+label+('-lt' if comparison == '<' else '-ne'), base.replace(prefix, guarded)
    for kind in ('s16', 's32', 'u8'):
        end_range = INITIAL.replace('    u8 range = source->slotRange;', '    '+kind+' end = source->slotRange;').replace(
            '    s16 first = range & 0xF;', '    s16 first = end & 0xF;').replace(
            '    s16 end = (range >> 4) + 1;', '    end = (s16)((end >> 4) + 1);')
        yield 'range-end-'+kind, end_range
    for label, base in (('cached', INITIAL), ('fields', dict(forms_head())['fields'])):
        array = base.replace('s16 *point = (s16 *)source->points;', 's16 (*point)[8] = source->points;').replace(
            'slots[index] = point;', 'slots[index] = *point;').replace('point += 8;', 'point++;')
        yield 'array-point-'+label, array
    best = opening+'\n'.join(declarations[k] for k in ('point','first','index','end'))+'\n\n    for (; index < first;'+loops
    for label, base in (('cached', INITIAL), ('fields', dict(forms_head())['fields']), ('best', best)):
        for kind in ('s32', 's16', 'u16', 'u32'):
            yield 'index-'+label+'-'+kind, base.replace('s32 index = 0;', kind+' index = 0;')
        yield 'register-index-'+label, base.replace('s32 index = 0;', 'register s32 index = 0;')
    for label, base in (('cached', INITIAL), ('fields', dict(forms_head())['fields'])):
        separate = base.replace('    s32 index = 0;', '    s32 prefixIndex = 0;\n    s32 index;').replace(
            prefix, prefix.replace('index', 'prefixIndex'))
        yield 'separate-prefix-'+label, separate
        yield 'separate-prefix-late-'+label, separate.replace('    s32 index;\n', '').replace(
            '\n\n    for (; prefixIndex', '\n    s32 index;\n\n    for (; prefixIndex', 1)


def forms_head():
    yield 'fields', INITIAL.replace('    u8 range = source->slotRange;\n', '').replace(
        'range & 0xF', 'source->slotRange & 0xF').replace('(range >> 4)', '(source->slotRange >> 4)')


SELECTED = dict(forms())['fields-point-first-index-end']


def measure(root, out, label='selected', body=None):
    if label == 'baseline':
        raise ValueError('Reserved immutable fixture label')
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root, out, recovered_owner((out/'before-packet_owner').read_text(), body), label)
    raw, functions, rel = parse_object(obj)
    f = functions[FUNCTION]
    data, placed = build.link_owner(root, out, obj, OWNER)
    linked = placed[FUNCTION]
    words = list(struct.unpack_from('>%dI' % (f['size']//4), data, linked['value']))
    truth = struct.unpack_from('>71I', (out/'before-retail_rom').read_bytes(), ROM)
    row = dict(label=label, words=len(words), frame=(-words[0])&65535 if words[0]>>16 == 0x27BD else 0,
        differences=sum(a != b for a,b in zip(words, truth))+abs(len(words)-WORDS), diagnostics=diagnostics,
        raw_sha256=hashlib.sha256(raw[f['value']:f['value']+f['size']]).hexdigest(),
        relocations={a-f['value']:v for a,v in rel.items() if f['value'] <= a < f['value']+f['size']},
        pools={n:d.hex() for n,(_,d) in sections(obj).items()
            if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d},
        different_words=[(i*4,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a != b])
    (out/(label+'.json')).write_text(json.dumps(row, indent=2)+'\n')
    return obj, words, row


def closed_instruction_roles(raw, truth):
    if len(raw) != WORDS or len(truth) != WORDS:
        raise ValueError('Changed point-slot instruction extent')
    for a, b in zip(raw, truth):
        op, fn = a >> 26, a & 63
        if op == 0 and fn in (0, 2, 3):
            mask = (31 << 16) | (31 << 11)
        elif op == 0 and fn in (33, 35, 37, 42):
            mask = (31 << 21) | (31 << 16) | (31 << 11)
        elif op in (4, 5, 9, 10, 12, 35, 36, 43):
            mask = (31 << 21) | (31 << 16)
        elif op == 6:
            mask = 31 << 21
        elif a == b == 0x03E00008:
            mask = 0
        else:
            raise ValueError('Unknown point-slot instruction role')
        if a & ~mask != b & ~mask:
            raise ValueError('Point-slot normalization changes an operation or immediate')


def proposed_guards(before):
    reader = csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename'] == OWNER and r['function'] == FUNCTION for r in reader):
        raise ValueError('Unexpected prior point-slot guards')
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=reader.fieldnames,
        lineterminator='\r\n' if before.endswith(b'\r\n') else '\n')
    for offset, (expected, replacement) in GUARDS.items():
        writer.writerow(dict(filename=OWNER, function=FUNCTION, offset=hex(offset),
            expected='0x%08X'%expected, replacement='0x%08X'%replacement,
            expected_relocations='-', replacement_relocations='-', omit='false',
            note='Normalize closed packed-point slot-builder compiler scratch roles'))
    if not before.endswith(b'\n'):
        raise ValueError('Unexpected point-slot predecessor CSV ending')
    return before + output.getvalue().encode()


def checked_object(obj):
    text, functions, rel = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value']+f['size']]
    bindings = {a-f['value']:v for a,v in rel.items() if f['value'] <= a < f['value']+f['size']}
    pools = {n:d for n,(_,d) in sections(obj).items()
        if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
    if len(raw) != 284 or hashlib.sha256(raw).hexdigest() != RAW_SHA256 or bindings or pools:
        raise ValueError('Unknown point-slot object/bindings/pools')
    return raw


def qualify(root, out):
    obj, raw, row = measure(root, out, 'qualified')
    checked_object(obj)
    truth = list(struct.unpack_from('>71I', (out/'before-retail_rom').read_bytes(), ROM))
    if (row['words'], row['frame'], row['differences'], row['diagnostics']) != (71, 0, 33, ''):
        raise ValueError('Unknown point-slot compiler shape')
    closed_instruction_roles(raw, truth)
    if {i*4:(a,b) for i,(a,b) in enumerate(zip(raw,truth)) if a != b} != GUARDS:
        raise ValueError('Changed point-slot scratch role sites')
    guards = out/'proposed-guards.csv'
    guards.write_bytes(proposed_guards((out/'before-guards').read_bytes()))
    padded = out/'qualified-padded.s'
    padded.write_text(emit_padded_assembly(obj, root/PATHS['packet_original'], filename=OWNER, word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded.with_suffix('.o')),str(padded)],
        check=True, capture_output=True)
    data, functions = build.link_owner(root, out, padded.with_suffix('.o'), OWNER)
    f = functions[FUNCTION]
    slot = data[f['value']:f['value']+284]
    if f['size'] != 284 or slot != struct.pack('>71I', *truth):
        raise ValueError('Point-slot provider is not byte exact')
    target = out/'predicted-slot.bin'
    if not target.exists():
        target.write_bytes(slot)
    if target.read_bytes() != slot:
        raise ValueError('Changed first point-slot prediction')
    row = dict(row, new_guards=33, slot_bytes=284, body_bytes=284, byte_exact=True)
    (out/'qualification.json').write_text(json.dumps(row, indent=2)+'\n')
    return obj, padded.with_suffix('.o'), raw, truth, row


def slot_expected_image(before, slot):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown point-slot predecessor image')
    if len(slot) != 284 or hashlib.sha256(slot).hexdigest() != SLOT_SHA256:
        raise ValueError('Unknown point-slot candidate slot')
    row = next(r for r in symbol_rows(before) if r[1] == FUNCTION)
    if row[2][1:3] != (ENTRY, 12):
        raise ValueError('Unknown point-slot predecessor extent')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, 284)
    result[at:at+284] = slot
    struct.pack_into('>I', result, row[0]+8, 284)
    return bytes(result)


def expected_inputs(root, out):
    return dict(elf=slot_expected_image((out/'before-elf').read_bytes(), (out/'predicted-slot.bin').read_bytes()),
        packet_owner=recovered_owner((out/'before-packet_owner').read_text()).encode(),
        guards=proposed_guards((out/'before-guards').read_bytes()))


def prelink_prediction(root, out):
    from tools.experiments import game_projected_packet_draw as core
    with patch.multiple(core, PATHS=PATHS, BASELINE=BASELINE, qualify=qualify, expected_inputs=expected_inputs):
        row = core.prelink_prediction(root, out)
    row.pop('draw_guards')
    row.pop('projected_guards')
    row.update(slot_bytes=284, body_bytes=284, new_guards=33, matched_functions=1,
        metadata_serialization_bytes=0)
    (out/'prelink-prediction.json').write_text(json.dumps(row, indent=2)+'\n')
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--screens', action='store_true')
    parser.add_argument('--filter', default='')
    parser.add_argument('--qualify', action='store_true')
    parser.add_argument('--prelink', action='store_true')
    args = parser.parse_args()
    if args.qualify or args.prelink:
        print(json.dumps(prelink_prediction(args.root, args.root/BUILD) if args.prelink else
            qualify(args.root, args.root/BUILD)[-1], indent=2))
        return
    for label, body in forms() if args.screens else (('selected', SELECTED),):
        if args.filter and args.filter not in label:
            continue
        row = measure(args.root, args.root/BUILD, label, body)[2]
        print(json.dumps({k:row[k] for k in ('label','words','frame','differences','diagnostics','raw_sha256')}), flush=True)


if __name__ == '__main__':
    main()
