"""Grouped live actor walk: semantic C, four derived guards and literal image gates."""
from pathlib import Path
from unittest.mock import patch
import argparse
import csv
import hashlib
import io
import json
import re
import shlex
import shutil
import struct
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import pad_c_object
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions

FUNCTION, ENTRY, ROM, SIZE = 'func_150228E4', 0x150228E4, 0x4FD94, 180
SOURCE, OBJECT = 'conker/src/game/generated_49D30.c', 'conker/build/src/game/generated_49D30.c.o'
OWNER, ASM = 'generated_49D30', 'conker/asm/49D30.s'
BUILD = 'conker/build/game-group-live-actor-match'
OLD_BODY = 's32 func_150228E4() {\n    return 0;\n}'
ANCHOR = 'extern u8 D_800C3518[][25];\n'
DECLARATIONS = 'extern struct127 D_800CC2D0[];\nvoid func_15060F28(struct127 *, s32);\n'
SELECTED = '/* Process live group actors; the helper may change the remaining entries. */\nvoid func_150228E4(s32 group) {\n    s32 index;\n    u8 *cursor;\n\n    index = 0;\n    if (D_800C3510[group] > 0) {\n        cursor = D_800C3518[group];\n        do {\n            if (D_800CC2D0[*cursor].interaction_state != 0) {\n                func_15060F28(&D_800CC2D0[*cursor], 0);\n            }\n            index++;\n            cursor++;\n        } while (index < D_800C3510[group]);\n    }\n}'
INPUTS = {
    "conker/Makefile": "54e393ef0f6c028cbfde10444ffff3581907a0647b0c3b16931ac93c8f3c85cf",
    "conker/asm/49D30.s": "745b8aaa3c4871d74f21c6cf2479a494cb5e01bcb2df1486c8dbc56004c3ae41",
    "conker/asm/data/2275E0.data.s": "9c912a5b5595b37b590fb8da13727bf91e1c495b0ff0f297231347417e7d700e",
    "conker/asm/nonmatchings/game_34F20/func_15007B3C.s": "fbe6f895bfe7849d87ef1a8b9a32bdffaaa0b6c64032c99c2e919cce9345e422",
    "conker/asm/nonmatchings/game_40490/func_15013000.s": "95975c7550133f3b9de582ad700587e462c46481e4ddeafe64a3de95ce63ba23",
    "conker/asm/nonmatchings/game_40490/func_150151D4.s": "321f4fdb5df7fbd1f14c000afbd27142a403fa5c306152aeccb94a73a29e3156",
    "conker/asm/nonmatchings/game_40490/func_15015354.s": "c8dc2fcab8ca0984d81c0232fd750f6d9bd2d4edb5d83b6f208cc119459dde0b",
    "conker/asm/nonmatchings/game_44C40/func_15017930.s": "63b82e0a5643cae83a97376e9e0940edb94694bccc2bb18422561598d3af69a8",
    "conker/asm/nonmatchings/game_83300/func_15060F28.s": "226c20ce9b9de365628c2ff1bae26fd7b4164dc435bfbf1028ea3b2ee0c8452f",
    "conker/build/conker.ld": "6479ca7cef48dc77d746c16afcc244de6bfb80c6789ba79a03d6f110e42a98d5",
    "conker/build/conker.us.elf": "db5035cc1f56562d05beae6098ce11e3e97ff4db9f6cacfffcb06c6926727dac",
    "conker/build/src/game/generated_49D30.c.o": "fda887c166c4ff7e8cd6a14251f6efa770a114532ce9b87b57002fd4768b33e0",
    "conker/build/src/game_34F20.c.o": "4893023e658b7838b524474c2f5d7740761db86863a6d78efcf099f040e0706f",
    "conker/build/src/game_40490.c.o": "e0b029857780217c9ecf1bed8b6f20cb011f0f0fa25093c1a3c392819a421594",
    "conker/conker.ld": "217efa560e11fa73c9edf1332d5494519fece1af469f2b99705f9d3b6d085db8",
    "conker/conker.us.bin": "f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382",
    "conker/include/2.0L/PR/gbi.h": "155141ca4e38735b9a5642521fb78ac735e4b32ee7509fb8df89966dc12c05b6",
    "conker/include/2.0L/PR/ultratypes.h": "1efbb2464233bd34b60e0f909e3409eb282a5a34aa04591637932bb1bf412ddd",
    "conker/include/2.0L/ultra64.h": "334dac734e99fcd8b227322092501397cfcdfb89af3529de6f81953b8feff65d",
    "conker/include/asm_processor_prelude.inc": "c23fba5e426068feb26591ba567642ccbd01219fab6604fec6eeed5362c4971d",
    "conker/include/functions.h": "2592982cdbbf797231326f9c623c055dd555b9ef7421883071a81f900edfcc81",
    "conker/include/libc/stdarg.h": "759498a7844671810843e0715215b1ddb3b402d2465e96aa19b65494d71ac2b4",
    "conker/include/libc/stddef.h": "e822ef44f9d0312debaef69d9934b62121b2927f8d4de349ad309e5ce8706721",
    "conker/include/libc/string.h": "ff969e54b7abd39d23a73c7b19b66afad925a626559bdaa2c47512341c440db5",
    "conker/include/macros.h": "dcb8c6e7f62fd6deaddc3544008092645782ded04b22ab431788c9648cb72769",
    "conker/include/structs.h": "081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69",
    "conker/include/variables.h": "1342a895b60d5802eec1fdb6fd1e738f88c9ef7b310b328f536e49a26c5d9df8",
    "conker/progress.csv": "16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be",
    "conker/retail_layout.us.txt": "a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5",
    "conker/retail_word_patches.us.csv": "01c02d32f3c22688893b69c5716a2c348ef2fe7ca00462a23cb9cc84cc472bbb",
    "conker/src/game/generated_10CD70.c": "0df14e155328a0b44b4effd24ce3126526f7e839fded181a4c85fc75e5d01457",
    "conker/src/game/generated_49D30.c": "350c4b08699ee583e4c5dd58b6fd403ab49dba62bf4aab53211d146850dc81de",
    "conker/src/game/generated_CDE80.c": "440ca60ba0044d20f8a8d8ad793bef664f258760e4fb3ca50e069a7ae615fa16",
    "conker/src/game_16EE20.c": "fc2cdab1d1d3952842fc82335c3599725171c5dad3fb4afd0e2ea31cc1c1b12a",
    "conker/src/game_34F20.c": "67bdf8b2ad041fbf891c8c83bf87e9b83398ac8d198dd5fec0ddd97ddc784d1b",
    "conker/src/game_40490.c": "fe5e93c04b9d072f9249d99876ae2074ecdc2e2e86931893e40fe983ddf0bded",
    "conker/src/game_83300.c": "5f6e538806ef7f966ee1a843a071df9d54c120105d25b7577a32e4f7981f2b54",
    "conker/symbol_addrs.us.txt": "d0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106",
    "conker/undefined_funcs.us.txt": "92cf330aeec0fa8b22a0549c75201869c455f3f065714f6a5d620e2fd752b64a",
    "conker/undefined_funcs_auto.txt": "3ada7d87571696b0cec57231830956a41eb844b374aa07fd58479db171b1d9d6",
    "conker/undefined_syms.us.txt": "d678bfadce508e3fb586a0e39cded5b4c6276e1f4fc3d59f9ab56cca6d6b244e",
    "conker/undefined_syms_auto.txt": "a74724688f404a019998d48cee2ddc4e21ffc753e2817171102d708538f518fd",
    "tools/check_game_data_layout.py": "98c6abbff94d29fc37df8021f530b50b42be0d2c5b5c65a598dd8070e7fde55c",
    "tools/experiments/alternative_source_draft_word_screen.py": "781792e48d99e2d57e8e99655275f0a9188b00d26b73d1d4a478c734ae8151a4",
    "tools/experiments/game_actor_state_tick_integration.py": "a2ffe4f27f70134c92ae1cd80911fd68229e2cb4c5768d5eb1ddf2d61e5725c1",
    "tools/experiments/game_record_callback_loop_match.py": "115fe3c10e6c5db56bc37d5aaf9c74b67aa204723cb09b9bce0ffeab55e6718e",
    "tools/experiments/game_remaining_donor_candidates.py": "15cec3a86a8b4e5954d5efbc900f5e9d047000672845896633fbe389874de0a1",
    "tools/match_progress.py": "46e1ebac2aa79aedb9a42ce5871a5d324fc6ca97978bc906aedf6664cb36abd3",
    "tools/pad_c_object.py": "d5e11a47650cbda9907672c381534ced6aac681d1f1333bac129038a685d9362",
    "tools/pad_generated_object.py": "ad513832cf991f3f04177faf8b22b1b434404d54168cd512e574e1921c349809",
    "tools/tests/game_frame_timing_oracle.py": "0473246cfb1219a8081c279b680aea19c5fef7829ca4a35878568a70ef643fa7",
    "tools/tests/game_owner_pool.py": "159b8c009af7b2d26ba5dce29f0c46ca0805cf14dbb27e5c682d107e551ca50e",
    "tools/tests/test_game_actor_burst_consumer_match.py": "c6a58dfbf711fbe5e49e9f6afb1a0e95e097319b7dcad4a1a74f13965e0736d5",
    "tools/tests/test_game_effect_owner_ray.py": "62376c5022f50db9a53b0ec8b9517a63bc9f298dff8c7a3047963ed216a0555f",
    "tools/tests/test_game_effect_position_payload.py": "b96faf372ff366565ec7967eb3148c04bbda539a76c1bd8498fc84f19ce5daf4",
    "tools/tests/test_game_projected_packet_draw.py": "e488215f4551d0ed97454e57edb43522c0df9d1ebe9b0303f42cbd236e0261d8",
    "tools/tests/test_game_record_callback_loop_match.py": "66a693e545aa7bd3f468b1f84937046a408ae496c12c082d9ff242d5158b016c",
    "tools/tests/test_game_row_destination_fill.py": "b79e64e36c55617f835d5fe7abadbba5d97272cd93d50055fb4167db8f8273fd"
}
RAW_SHA256 = '43a8219a93b386a4e1e08f07a7f9c68cc28b16eb559d13e1b5c4fa9d1b5acac7'
BINDINGS = {28: [('R_MIPS_HI16', 'D_800C3510')], 32: [('R_MIPS_LO16', 'D_800C3510')], 64: [('R_MIPS_HI16', 'D_800C3518')], 68: [('R_MIPS_LO16', 'D_800C3518')], 76: [('R_MIPS_HI16', 'D_800CC2D0')], 84: [('R_MIPS_LO16', 'D_800CC2D0')], 120: [('R_MIPS_26', 'func_15060F28')]}
BEFORE_OBJECT_SHA = 'fda887c166c4ff7e8cd6a14251f6efa770a114532ce9b87b57002fd4768b33e0'


def digest(data):
    return hashlib.sha256(data).hexdigest()

def recovered_owner(before):
    if before.count(OLD_BODY) != 1 or before.count(ANCHOR) != 1 or DECLARATIONS in before:
        raise ValueError('Grouped actor predecessor anchors changed')
    return before.replace(OLD_BODY, SELECTED).replace(ANCHOR, ANCHOR + DECLARATIONS)

def snapshot(output):
    values = {}
    for name, wanted in INPUTS.items():
        data = (output / ('before-' + name.replace('/', '_'))).read_bytes()
        if digest(data) != wanted:
            raise ValueError('Grouped actor historical input changed: ' + name)
        values[name] = data
    return values

def freeze(root, output):
    output.mkdir(parents=True, exist_ok=True)
    complete = all((output / ('before-' + name.replace('/', '_'))).exists() for name in INPUTS)
    if complete:
        values = snapshot(output)
        if (output / 'before-padded.o').read_bytes() != values[OBJECT]:
            raise ValueError('Grouped actor padded predecessor changed')
        return values
    values = {name: (root / name).read_bytes() for name in INPUTS}
    for name, wanted in INPUTS.items():
        if digest(values[name]) != wanted:
            raise ValueError('Grouped actor predecessor changed: ' + name)
        target = output / ('before-' + name.replace('/', '_'))
        if target.exists() and target.read_bytes() != values[name]:
            raise ValueError('Grouped actor partial snapshot differs: ' + name)
        target.write_bytes(values[name])
    (output / 'before-padded.o').write_bytes(values[OBJECT])
    return snapshot(output)

def payload(obj):
    text, functions, bindings = parse_object(obj)
    info = functions[FUNCTION]
    start, size = info['value'], info['size']
    if size != SIZE:
        if size != 192 or start + size != len(text) or any(text[start + SIZE:start + size]):
            raise ValueError('Grouped actor extent/alignment changed')
        if any(start + SIZE <= at < start + size for at in bindings):
            raise ValueError('Grouped actor alignment has a relocation')
    return text[start:start + SIZE], {at - start: rows for at, rows in bindings.items() if start <= at < start + SIZE}

def normalized_payload(raw, bindings):
    if len(raw) != SIZE or digest(raw) != RAW_SHA256 or bindings != BINDINGS:
        raise ValueError('Grouped actor raw words or bindings changed')
    result, rebound = bytearray(raw), dict(bindings)
    for a, b in ((0x30, 0x38), (0x50, 0x54)):
        result[a:a + 4], result[b:b + 4] = raw[b:b + 4], raw[a:a + 4]
        for dest, src in ((a, b), (b, a)):
            if src in bindings:
                rebound[dest] = bindings[src]
            else:
                rebound.pop(dest, None)
    return bytes(result), rebound

def predicted_image(before, truth):
    if digest(before) != INPUTS['conker/build/conker.us.elf'] or len(truth) != SIZE:
        raise ValueError('Grouped actor strict image predecessor changed')
    result = bytearray(before)
    at = elf_slot_offset(before, ENTRY, SIZE)
    result[at:at + SIZE] = truth
    rows = [offset for offset, name, fields, _ in symbol_rows(before)
        if name == FUNCTION and fields[1:3] == (ENTRY, 12) and fields[3] & 15 == 2]
    if len(rows) != 1:
        raise ValueError('Grouped actor symbol-size predecessor changed')
    struct.pack_into('>I', result, rows[0] + 8, SIZE)
    return bytes(result)

def check_image(before, actual, truth):
    if actual != predicted_image(before, truth):
        raise ValueError('Grouped actor image differs from literal prediction')

def expected_inputs(values, output, installed):
    expected = dict(values)
    if installed:
        expected.update({SOURCE: recovered_owner(values[SOURCE].decode()).encode(),
            OBJECT: (output / 'typed-padded.o').read_bytes(),
            'conker/retail_word_patches.us.csv': (output / 'typed-proposed-guards.csv').read_bytes(),
            'conker/build/conker.us.elf': predicted_image(values['conker/build/conker.us.elf'], values['conker/conker.us.bin'][ROM:ROM + SIZE])})
    return expected

def check_input_map(values, actual, output, installed):
    expected = expected_inputs(values, output, installed)
    if actual.keys() != expected.keys():
        raise ValueError('Grouped actor input map membership changed')
    for name, data in expected.items():
        if actual[name] != data:
            raise ValueError('Grouped actor input changed: ' + name)

ARTIFACTS = ('typed-before.o', 'typed-after.o', 'typed-isolated.o', 'typed-original.o',
    'typed-padded.o', 'typed-proposed-owner.c', 'typed-proposed-guards.csv', 'first-linked.elf')

def verify_prepared(output):
    pins = json.loads((output / 'artifact-fingerprint.json').read_text())
    if set(pins) != set(ARTIFACTS):
        raise ValueError('Grouped actor prepared artifacts changed')
    for name, wanted in pins.items():
        if digest((output / name).read_bytes()) != wanted:
            raise ValueError('Grouped actor frozen artifact changed: ' + name)
    return pins

def audit(root, output):
    values = snapshot(output)
    actual = {name: (root / name).read_bytes() for name in INPUTS}
    installed = actual[SOURCE] != values[SOURCE]
    check_input_map(values, actual, output, installed)
    before = output / 'before-conker_build_conker.us.elf'
    current = root / 'conker/build/conker.us.elf'
    a, _, aa = load_elf_functions(str(before), 'mips-linux-gnu-objdump')
    b, _, ba = load_elf_functions(str(current), 'mips-linux-gnu-objdump')
    if aa != ba or a.keys() != b.keys() or [name for name in a if a[name] != b[name]] != ([FUNCTION] if installed else []):
        raise ValueError('Grouped actor changed another body/address')
    data = audit_layout(current, root / 'conker')
    if (data['exact'], data['owner_count'], data['bytes'], data['different_bytes']) != (True, 720, 189088, 0):
        raise ValueError('Grouped actor protected Game data changed')
    return dict(installed=installed, functions=len(b), other_bodies_fixed=len(b) - int(installed),
        addresses_fixed=True, game_data=data, metadata_exclusions=0)

def qualify(root, output):
    r, o = Path(root), Path(output)
    name, owner, size = 'func_150228E4', 'generated_49D30', 180
    source_path = r / 'conker/src/game/generated_49D30.c'
    values = freeze(r, o)
    before = values[SOURCE].decode()
    selected = SELECTED
    old = 's32 func_150228E4() {\n    return 0;\n}'
    declarations = 'extern struct127 D_800CC2D0[];\nvoid func_15060F28(struct127 *, s32);\n'
    anchor = 'extern u8 D_800C3518[][25];\n'
    assert before.count(old) == before.count(anchor) == 1 and declarations not in before
    after = recovered_owner(before)
    assert selected == SELECTED
    head = '#include <ultra64.h>\n#include "structs.h"\nextern u8 D_800C3510[];\n' + anchor + declarations
    run = subprocess.run
    def command(args, *pos, **kw):
        if any(str(x).endswith('/asm-processor/asm_processor.py') for x in args):
            args = [x for x in args if not str(x).startswith('-Wo,')]
        return run(args, *pos, **kw)

    objects = []
    for label, text in (('before', before), ('after', after), ('isolated', head + selected)):
        with patch.object(subprocess, 'run', command):
            obj, diagnostics = compile_owner(r, o, text, 'typed-' + label, flags=('-O2', '-g3', '-Wo,-loopunroll,0'))
        objects.append((obj, diagnostics))
    assert objects[0][1] == objects[1][1] and not objects[2][1]

    def payload(obj):
        text, funcs, binds = parse_object(obj)
        f = funcs[name]
        start = f['value']
        if f['size'] != size:
            assert f['size'] == 192 and start + f['size'] == len(text)
            assert not any(text[start + size:start + f['size']])
            assert not any(start + size <= at < start + f['size'] for at in binds)
        return text[start:start + size], {at - start: values for at, values in binds.items() if start <= at < start + size}

    raw, bindings = payload(objects[1][0])
    assert payload(objects[2][0]) == (raw, bindings)
    normalized, rebound = normalized_payload(raw, bindings)
    assembly = (r / 'conker/asm/49D30.s').read_text()
    span = re.search(r'^glabel ' + name + r'\n.*?^endlabel ' + name + r'\s*$', assembly, re.M | re.S)[0]
    span = span.replace('glabel ' + name, '.globl ' + name + '\n.type ' + name + ', @function\n' + name + ':').replace('endlabel ' + name, '.size ' + name + ', . - ' + name)
    asm = o / 'typed-original.s'
    asm.write_text('.set noreorder\n.set noat\n.set mips3\n.text\n' + span)
    original = asm.with_suffix('.o')
    run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-mabi=32', '-o', str(original), str(asm)], check=True, capture_output=True)
    assert payload(original) == (bytes(normalized), rebound)
    neighbors = same_functions(objects[0][0], objects[1][0], (name,))
    assert normalized_pools(objects[0][0]) == normalized_pools(objects[1][0])

    old_guards = values['conker/retail_word_patches.us.csv']
    fields = next(csv.reader(io.StringIO(old_guards.decode())))
    assert not any(row['function'] == name for row in csv.DictReader(io.StringIO(old_guards.decode())))
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    fmt = lambda values: ';'.join(kind + ':' + symbol for kind, symbol in values) or '-'
    for at in (0x30, 0x38, 0x50, 0x54):
        writer.writerow(dict(filename=owner, function=name, offset=hex(at),
            expected='0x%08X' % struct.unpack_from('>I', raw, at)[0],
            replacement='0x%08X' % struct.unpack_from('>I', normalized, at)[0],
            expected_relocations=fmt(bindings.get(at, [])), replacement_relocations=fmt(rebound.get(at, [])),
            note='Normalize two independent group-actor setup instruction swaps', insert_after='', insert_after_relocations='', omit='false'))
    assert old_guards.endswith(b'\n')
    guards = o / 'typed-proposed-guards.csv'
    guards.write_bytes(old_guards + stream.getvalue().encode())
    pad = o / 'typed-padded.s'
    pad.write_text(pad_c_object.emit_padded_assembly(objects[1][0], r / 'conker/retail_layout.us.txt', owner, word_patches_path=guards))
    padded = pad.with_suffix('.o')
    run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-mabi=32', '-I', str(r / 'conker/include'), '-o', str(padded), str(pad)], check=True, capture_output=True)
    linked, funcs = link_owner(r, o, padded, owner)
    at = funcs[name]['value']
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    assert linked[at:at + size] == truth
    (o / 'typed-proposed-owner.c').write_text(after)
    (o / 'typed-selected.c').write_text(head + selected)
    sha = lambda data: hashlib.sha256(data).hexdigest()
    report = dict(function=name, words=45, frame=48, raw_differences=4, guard_rows=4, derived_independent_swaps=[[0x30, 0x38], [0x50, 0x54]],
        raw_SHA256=sha(raw), raw_bindings=bindings, normalized_bindings=rebound, preserved_raw_neighbors=neighbors,
        pools_equal=True, owner_isolated_payload_equal=True, ordinary_padder_reproduces_retail=True,
        original_GNU_payload_equal=True, source_SHA256=sha(after.encode()), before_source_SHA256=sha(before.encode()),
        padded_SHA256=sha(padded.read_bytes()), existing_Guards_SHA256=sha(old_guards), proposed_Guards_SHA256=sha(guards.read_bytes()),
        provider_ABI='void func_15060F28(struct127 *, s32)', actor_size=0x32C, actor_field='interaction_state',
        matching_credit=0, preinstall_qualification=True, production_install_required=True)
    (o / 'typed-qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    assert neighbors == 56
    return report

def boundaries(root, output):
    r, o = Path(root), Path(output)
    proof = json.loads((o / 'typed-qualification.json').read_text())
    values = snapshot(o)
    sha = lambda data: hashlib.sha256(data).hexdigest()
    assert sha(values[SOURCE]) == proof['before_source_SHA256']
    assert sha((o / 'typed-proposed-owner.c').read_bytes()) == proof['source_SHA256']
    assert sha(values['conker/retail_word_patches.us.csv']) == proof['existing_Guards_SHA256']
    assert sha((o / 'typed-proposed-guards.csv').read_bytes()) == proof['proposed_Guards_SHA256']
    assert sha((o / 'typed-padded.o').read_bytes()) == proof['padded_SHA256']
    symbols = dict(D_800C3510=0x800C3510, D_800C3518=0x800C3518, D_800CC2D0=0x800CC2D0, func_15060F28=0x15060F28)
    objects = []
    for label in ('original', 'padded', 'after'):
        text, funcs, bindings = parse_object(o / ('typed-' + label + '.o'))
        assembly, unresolved = emit_function(text, funcs['func_150228E4'], bindings, 'func_150228E4', symbols)
        assert not unresolved
        path = o / ('gnu-' + label + '.s')
        path.write_text('.set noreorder\n.set noat\n.set mips3\n' + assembly)
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-mabi=32', '-o', str(obj), str(path)], check=True, capture_output=True)
        objects.append(obj)
    rebase_rows = []
    for index in range(9):
        mapped = {name: value + index * 0x10000 for name, value in symbols.items()}
        if index >= 3:
            lows = (0x7ffc, 0x8004, 0xfff0)
            for j, name in enumerate(tuple(symbols)[:3]):
                mapped[name] = 0x81200000 + j * 0x10000 + lows[(index + j) % 3]
        entry = 0x150228E4 + index * 0x20000
        link = o / ('gnu-rebase-%d.ld' % index)
        link.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
        spans = []
        for label, obj in zip(('original', 'padded'), objects):
            elf = o / ('gnu-rebase-%d-%s.elf' % (index, label))
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(link), '-e', 'func_150228E4',
                *['--defsym=%s=0x%X' % item for item in mapped.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            data = sections(elf)['.text'][1]
            assert not any(data[180:])
            spans.append(data[:180])
        assert spans[0] == spans[1]
        rebase_rows.append(dict(entry=entry, symbols=mapped, SHA256=sha(spans[0])))

    conker = r / 'conker'
    shadow = o / 'make-shadow'
    (shadow / 'src/game').mkdir(parents=True, exist_ok=True)
    target = (shadow / 'src/game/generated_49D30.c.o').relative_to(conker).as_posix()
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR=' + shadow.relative_to(conker).as_posix(), target], cwd=conker, capture_output=True, text=True, check=True)
    (o / 'make-shadow-plan.txt').write_text(plan.stdout + plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        assert args[0] in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'), args
        args = [(o / 'typed-proposed-owner.c').relative_to(conker).as_posix() if value == 'src/game/generated_49D30.c' else value for value in args]
        args = [(o / 'typed-proposed-guards.csv').relative_to(conker).as_posix() if value == 'retail_word_patches.us.csv' else value for value in args]
        redirect = None
        if '>' in args:
            assert args.count('>') == 1 and args[-2] == '>'
            redirect = (conker / args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        p = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        assert p.returncode == 0 and not p.stderr and (redirect is not None or not p.stdout), (args, p.returncode, p.stdout, p.stderr)
        if redirect is not None:
            redirect.write_text(p.stdout)
        commands.append(args)
    compilers = [args for args in commands if args[0] == '../ido/ido5.3_recomp/cc']
    assert len(commands) == 3 and len(compilers) == 1
    assert all(flag in compilers[0] for flag in ('-O2', '-g3', '-Wo,-loopunroll,0'))
    actual = conker / target
    assert same_functions(o / 'typed-after.o', Path(str(actual) + '.compact')) == 57
    assert normalized_pools(o / 'typed-after.o') == normalized_pools(Path(str(actual) + '.compact'))
    assert link_owner(r, o, actual, 'generated_49D30') == link_owner(r, o, o / 'typed-padded.o', 'generated_49D30')

    before_object = o / 'before-padded.o'
    a, fa = link_owner(r, o, before_object, 'generated_49D30')
    b, fb = link_owner(r, o, o / 'typed-padded.o', 'generated_49D30')
    expected = {name: dict(info) for name, info in fa.items()}
    assert expected['func_150228E4']['size'] == 12
    expected['func_150228E4']['size'] = 180
    assert expected == fb
    at = fb['func_150228E4']['value']
    assert a[:at] == b[:at] and a[at + 180:] == b[at + 180:]
    assert same_functions(before_object, o / 'typed-padded.o', ('func_150228E4',)) == 56
    assert normalized_pools(before_object) == normalized_pools(o / 'typed-padded.o')

    before = values['conker/build/conker.us.elf']
    assert sha(before) == 'db5035cc1f56562d05beae6098ce11e3e97ff4db9f6cacfffcb06c6926727dac'
    link_input = o / 'link-input/generated_49D30.c.o'
    link_input.parent.mkdir(exist_ok=True)
    shutil.copyfile(o / 'typed-padded.o', link_input)
    old = 'build/src/game/generated_49D30.c.o'
    script = (conker / 'build/conker.ld').read_text()
    assert script.count(old) == 1
    link = o / 'first-link.ld'
    link.write_text(script.replace(old, link_input.relative_to(conker).as_posix()))
    elf = o / 'first-linked.elf'
    subprocess.run(['mips-linux-gnu-ld', '-T', link.relative_to(conker).as_posix(), '-T', 'undefined_syms.us.txt',
        '-T', 'undefined_funcs.us.txt', '-T', 'undefined_syms_auto.txt', '-T', 'undefined_funcs_auto.txt',
        '--no-check-sections', '--no-warn-mismatch', '-o', elf.relative_to(conker).as_posix()], cwd=conker, check=True, capture_output=True)
    after = elf.read_bytes()
    rom = (conker / 'conker.us.bin').read_bytes()
    expected = bytearray(before)
    at = elf_slot_offset(before, 0x150228E4, 180)
    expected[at:at + 180] = rom[0x4FD94:0x4FE48]
    rows = [offset for offset, name, fields, _ in symbol_rows(before) if name == 'func_150228E4' and fields[1:3] == (0x150228E4, 12) and fields[3] & 15 == 2]
    assert len(rows) == 1
    struct.pack_into('>I', expected, rows[0] + 8, 180)
    assert after == bytes(expected), 'Unexpected strict full-image change'
    data = audit_layout(elf, conker)
    assert (data['exact'], data['owner_count'], data['bytes'], data['different_bytes']) == (True, 720, 189088, 0)

    assembly = (conker / 'asm/49D30.s').read_text()
    caller = re.search(r'^glabel func_1501EA18\n.*?^endlabel func_1501EA18\s*$', assembly, re.M | re.S)[0]
    caller = caller.replace('glabel func_1501EA18', '.globl func_1501EA18\n.type func_1501EA18, @function\nfunc_1501EA18:').replace('endlabel func_1501EA18', '.size func_1501EA18, . - func_1501EA18')
    path = o / 'actual-caller.s'
    path.write_text('.set noreorder\n.set noat\n.set mips3\n.text\n' + caller)
    obj = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-mabi=32', '-o', str(obj), str(path)], check=True, capture_output=True)
    linked, funcs = link_owner(r, o, obj, 'generated_49D30')
    f = funcs['func_1501EA18']
    assert f['size'] == 544 and linked[f['value']:f['value'] + 544] == rom[0x4BEC8:0x4C0E8]
    report = dict(independent_GNU_rebases=rebase_rows, original_caller_words=136, actual_Make_commands=len(commands),
        normal_no_unroll_profile=True, raw_and_padded_Make_equal=True, raw_and_padded_neighbors=56,
        strict_image_SHA256=sha(after), strict_image_changed_bytes=sum(x != y for x, y in zip(before, after)),
        metadata_exclusions=0, game_data=data, preinstall_qualification=True, matching_credit=0,
        caller_execution_aliases_guard_corruptions_canonical_tools_install_pending=True)
    (o / 'boundary-qualification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report

def prepare(root, output):
    if (output / 'artifact-fingerprint.json').exists():
        raise ValueError('Inspect frozen qualification; preparation is not a test setup action')
    a, b = qualify(root, output), boundaries(root, output)
    (output / 'artifact-fingerprint.json').write_text(json.dumps({name: digest((output / name).read_bytes()) for name in ARTIFACTS}, indent=2) + '\n')
    verify_prepared(output)
    return dict(owner=a, boundaries=b)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / BUILD
    print(json.dumps(prepare(root, output) if args.prepare else audit(root, output)), flush=True)
