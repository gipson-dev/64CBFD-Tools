"""Qualify the reset's closed F0/F2 allocation and seven-word opening schedule."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_sequence_state_reset as source
from tools.experiments.game_graphics_task_submit import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools import pad_c_object

RAW_SHA256 = '8335ddc383022ef73f53ab03c77cdb4081fe2b92f1472f9cb5ec6f31ee5f801d'
RAW_BINDINGS_SHA256 = '0fbcfad7c48bc67bfa7bca3c0ccee0c808273d65fe094616d7389895f3f58775'
ORIGINAL_SHA256 = '9e64f2b01a82d0f5481cc419d694b72f5a72e6794b4f6a2be3121c5448b8b1b8'
ORIGINAL_BINDINGS_SHA256 = '5d04ff2864190211219f1d88c2e1932d900da59746f18dcdc567872ab2fd9e6c'
ROUTING = {4:16, 8:4, 12:20, 16:8, 20:12, 24:28, 28:24}
FLOAT_STORES = {0x7C, 0x84, 0x8C, 0x11C, 0x134, 0x13C}


def object_parts(obj):
    text, functions, relocations = parse_object(obj); f = functions[source.FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    return raw, {at - f['value']:r for at, r in relocations.items() if f['value'] <= at < f['value'] + f['size']}


def bindings_hash(bindings): return hashlib.sha256(json.dumps(bindings, sort_keys=True).encode()).hexdigest()


def checked_object(obj):
    raw, bindings = object_parts(obj)
    pools = {n:d for n, (_, d) in sections(obj).items()
        if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d}
    if len(raw) != 400 or hashlib.sha256(raw).hexdigest() != RAW_SHA256 or bindings_hash(bindings) != RAW_BINDINGS_SHA256 or pools:
        raise ValueError('Unknown sequence reset words/bindings/pools')
    return list(struct.unpack('>100I', raw)), bindings


def original(root, out, label='original-reset', name=source.FUNCTION):
    from tools.tests import test_game_view_list_setup as assembly
    context = type('OriginalContext', (), dict(root=root, out=out))
    return assembly.ViewListSetupTests.original.__func__(context, label,
        (out / 'before-view_list_caller_original').read_text(), name)


def swap_float_register(word):
    op, rs = word >> 26, word >> 21 & 31
    shift = 16 if op in (49, 57) else 11 if op == 17 and rs == 4 else None
    if shift is None: return word
    register = word >> shift & 31
    if register not in (0, 2): raise ValueError('Unexpected reset FPR role')
    return word ^ (2 << shift)


def normalization(obj, original_obj):
    words, bindings = checked_object(obj); raw, target_bindings = object_parts(original_obj)
    if len(raw) != 400 or hashlib.sha256(raw).hexdigest() != ORIGINAL_SHA256 or bindings_hash(target_bindings) != ORIGINAL_BINDINGS_SHA256:
        raise ValueError('Changed original sequence reset words/bindings')
    wanted = list(struct.unpack('>100I', raw)); result = {}
    for at in range(0, 400, 4):
        routed = ROUTING.get(at, at)
        if swap_float_register(words[routed // 4]) != wanted[at // 4] or bindings.get(routed, []) != target_bindings.get(at, []):
            raise ValueError('Reset differs outside the opening schedule and closed F0/F2 allocation: %X' % at)
        if words[at // 4] != wanted[at // 4] or bindings.get(at, []) != target_bindings.get(at, []):
            result[at] = dict(expected=words[at // 4], replacement=wanted[at // 4],
                expected_relocations=bindings.get(at, []), replacement_relocations=target_bindings.get(at, []))
    if set(result) != set(ROUTING) | FLOAT_STORES: raise ValueError('Changed sequence reset guard extent')
    return result


def recovered_guards(before, obj, original_obj):
    fields = next(csv.reader(io.StringIO(before.decode())))
    if not before.endswith(b'\n'): raise ValueError('Unknown guard manifest terminator')
    if any(r['filename'] == source.OWNER and r['function'] == source.FUNCTION for r in csv.DictReader(io.StringIO(before.decode()))):
        raise ValueError('Sequence reset already has guards')
    stream = io.StringIO(newline=''); writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    encode = lambda rows:';'.join(kind + ':' + name for kind, name in rows) or '-'
    for at, row in sorted(normalization(obj, original_obj).items()):
        writer.writerow(dict(filename=source.OWNER, function=source.FUNCTION, offset='0x%X' % at,
            expected='0x%08X' % row['expected'], replacement='0x%08X' % row['replacement'],
            expected_relocations=encode(row['expected_relocations']), replacement_relocations=encode(row['replacement_relocations']),
            note='Normalize sequence reset ' + ('opening independent schedule and F0/F2 roles' if at in ROUTING else 'closed F0/F2 allocation'),
            insert_after='', insert_after_relocations='', omit='false'))
    return before + stream.getvalue().encode()


def checked_guards(before, after, obj, original_obj):
    if after != recovered_guards(before, obj, original_obj): raise ValueError('Changed sequence reset guards')


def qualify(root, out):
    obj, raw, row = source.measure(root, out, 'qualified', source.SELECTED); checked_object(obj)
    old, diagnostics = source.compile_owner(root, out, (out / 'before-view_list_caller_owner').read_text(), 'neighbor-before', True)
    neighbors = same_functions(old, obj, (source.FUNCTION,)); original_obj = original(root, out)
    guards = out / 'qualified-guards.csv'; before = (out / 'before-guards').read_bytes()
    guards.write_bytes(recovered_guards(before, obj, original_obj)); checked_guards(before, guards.read_bytes(), obj, original_obj)
    script = out / 'qualified-padded.s'; script.write_text(emit_padded_assembly(obj,
        out / 'before-view_list_caller_original', word_patches_path=guards, filename=source.OWNER))
    padded = script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(script)], capture_output=True, check=True)
    data, functions = source.build.link_owner(root, out, padded, source.OWNER); f = functions[source.FUNCTION]
    truth = (out / 'before-retail_rom').read_bytes()[source.ROM:source.ROM + 400]
    if diagnostics or row['diagnostics'] or f['size'] != 400 or data[f['value']:f['value'] + 400] != truth:
        raise ValueError('Guarded sequence reset is not byte-exact')
    callers = []
    for label, content in (('caller-before', (out / 'before-view_init_caller_owner').read_text()),
            ('caller-after', source.recovered_caller((out / 'before-view_init_caller_owner').read_text()))):
        caller, _ = source.compile_owner(root, out, content, label); callers.append(caller)
    caller_functions = same_functions(*callers, ())
    caller_script = out / 'caller-after-padded.s'; caller_script.write_text(pad_c_object.emit_padded_assembly(
        callers[-1], out / 'before-layout', 'game_34F20', word_patches_path=guards))
    caller_padded = caller_script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(caller_padded), str(caller_script)], capture_output=True, check=True)
    row.update(byte_exact=True, direct=False, installed=False, new_guards=13, unchanged_raw_neighbors=neighbors,
        unchanged_caller_functions=caller_functions, normalized_words=100, frame=24, inserted_words=0, omitted_words=0)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, raw, row


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    print(json.dumps({k:v for k,v in qualify(root, root / source.BUILD)[3].items() if k not in ('bindings', 'different_words')}, indent=2), flush=True)
