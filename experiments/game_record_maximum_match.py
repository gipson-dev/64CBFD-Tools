"""Qualify only the 105-word temporary-register and setup-schedule normalization."""
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_record_maximum_scan as source
from tools.experiments.game_graphics_task_submit import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object, emit_padded_assembly

RAW_SHA256 = 'f5207f069387e6276e47b620614f3a25075067a0af2230ec741e0c613aa93b6f'
ORIGINAL_SHA256 = '1ca9ff9805fb6c8f36cbb37565483d4e6017fc09904ded36abcae1d08a0cd843'
ORIGINAL_BINDINGS_SHA256 = '2a2438675d38a42fae7f7ee529d2aa7cec53eb7f660a5e5819f770afe1a50694'
ROUTING = {0x11C:0x124, 0x120:0x128, 0x124:0x11C, 0x128:0x120}
RELOCATIONS = {
    0:[('R_MIPS_HI16', 'D_800C3640')], 4:[('R_MIPS_LO16', 'D_800C3640')],
    16:[('R_MIPS_HI16', 'D_800C363A')], 28:[('R_MIPS_LO16', 'D_800C363A')],
    32:[('R_MIPS_HI16', 'D_800C35D8')], 48:[('R_MIPS_LO16', 'D_800C35D8')],
    56:[('R_MIPS_HI16', 'D_800C3688')], 68:[('R_MIPS_LO16', 'D_800C3688')],
    116:[('R_MIPS_HI16', 'D_800C3688')], 120:[('R_MIPS_LO16', 'D_800C3688')],
    136:[('R_MIPS_HI16', 'D_800C35C8')], 144:[('R_MIPS_LO16', 'D_800C35C8')],
    268:[('R_MIPS_HI16', 'D_800C35C8')], 284:[('R_MIPS_LO16', 'D_800C35C8')],
    276:[('R_MIPS_HI16', 'D_800C3778')], 296:[('R_MIPS_LO16', 'D_800C3778')],
    280:[('R_MIPS_HI16', 'D_800C35D0')], 292:[('R_MIPS_LO16', 'D_800C35D0')],
}


def object_parts(obj):
    text, functions, relocations = parse_object(obj); f = functions[source.FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    return raw, {at - f['value']:r for at, r in relocations.items()
        if f['value'] <= at < f['value'] + f['size']}


def checked_object(obj):
    raw, bindings = object_parts(obj)
    pools = {n:d for n, (_, d) in sections(obj).items()
        if n.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and d}
    if len(raw) != 420 or hashlib.sha256(raw).hexdigest() != RAW_SHA256 or bindings != RELOCATIONS or pools:
        raise ValueError('Unknown record maximum words/bindings/pools')
    return list(struct.unpack('>105I', raw)), bindings


def original(root, out, label='original-maximum'):
    from tools.tests import test_game_view_list_setup as assembly
    context = type('OriginalContext', (), dict(root=root, out=out))
    return assembly.ViewListSetupTests.original.__func__(context, label,
        (out / 'before-view_list_caller_original').read_text(), source.FUNCTION)


def register_only(actual, wanted):
    op = actual >> 26
    if op != wanted >> 26: return False
    fields = (21, 16, 11) if op == 0 else (21, 16)
    mask = 0x03FFF800 if op == 0 else 0x03FF0000
    if (actual ^ wanted) & ~mask: return False
    # No argument, output, stack, return or saved-register role can be repaired.
    temporaries = {1, *range(8, 16), 24, 25}
    return all((actual >> shift & 31) == (wanted >> shift & 31) or
        {(actual >> shift & 31), (wanted >> shift & 31)} <= temporaries for shift in fields)


def normalization(obj, original_obj):
    words, bindings = checked_object(obj); raw, original_bindings = object_parts(original_obj)
    if len(raw) != 420 or hashlib.sha256(raw).hexdigest() != ORIGINAL_SHA256 or (
            hashlib.sha256(json.dumps(original_bindings, sort_keys=True).encode()).hexdigest() != ORIGINAL_BINDINGS_SHA256):
        raise ValueError('Changed original record maximum words/bindings')
    wanted = list(struct.unpack('>105I', raw)); result = {}
    for at in range(0, 420, 4):
        routed = ROUTING.get(at, at)
        if not register_only(words[routed // 4], wanted[at // 4]) or bindings.get(routed, []) != original_bindings.get(at, []):
            raise ValueError('Non-register change outside the four-word setup routing: %X' % at)
        if words[at // 4] != wanted[at // 4] or bindings.get(at, []) != original_bindings.get(at, []):
            result[at] = dict(expected=words[at // 4], replacement=wanted[at // 4],
                expected_relocations=bindings.get(at, []), replacement_relocations=original_bindings.get(at, []))
    if len(result) != 48: raise ValueError('Changed record maximum guard extent')
    return result


def recovered_guards(before, obj, original_obj):
    fields = next(csv.reader(io.StringIO(before.decode())))
    if not before.endswith(b'\n'): raise ValueError('Unknown guard manifest terminator')
    if any(r['filename'] == source.OWNER and r['function'] == source.FUNCTION
            for r in csv.DictReader(io.StringIO(before.decode()))):
        raise ValueError('Record maximum already has guards')
    stream = io.StringIO(newline=''); writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    encode = lambda rows:';'.join(kind + ':' + name for kind, name in rows) or '-'
    for at, row in sorted(normalization(obj, original_obj).items()):
        writer.writerow(dict(filename=source.OWNER, function=source.FUNCTION, offset='0x%X' % at,
            expected='0x%08X' % row['expected'], replacement='0x%08X' % row['replacement'],
            expected_relocations=encode(row['expected_relocations']), replacement_relocations=encode(row['replacement_relocations']),
            note='Normalize record maximum ' + ('independent setup schedule and temporaries' if at in ROUTING else 'temporary register allocation'),
            insert_after='', insert_after_relocations='', omit='false'))
    return before + stream.getvalue().encode()


def checked_guards(before, after, obj, original_obj):
    if after != recovered_guards(before, obj, original_obj): raise ValueError('Changed record maximum guards')


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
    truth = (out / 'before-retail_rom').read_bytes()[source.ROM:source.ROM + 420]
    if diagnostics or row['diagnostics'] or f['size'] != 420 or data[f['value']:f['value'] + 420] != truth:
        raise ValueError('Guarded record maximum is not byte-exact')
    row.update(byte_exact=True, direct=False, installed=False, new_guards=48,
        unchanged_raw_neighbors=neighbors, normalized_words=105, inserted_words=0, omitted_words=0, frame=0)
    (out / 'qualification.json').write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, raw, row


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root, root / source.BUILD)[3], indent=2), flush=True)
