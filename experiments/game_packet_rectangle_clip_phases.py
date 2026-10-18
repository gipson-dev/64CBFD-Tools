"""Screen clipping and flip lifetimes against the current rectangle owner.

This screens and qualifies one source-only improvement. Historical whole-image fixtures
remain immutable; the direct compiler helpers use the explicitly pinned live
successor instead of teaching old fixtures to accept an unknown image.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from tools.experiments import game_packet_rectangle_step_lifetime as previous
from tools.experiments.game_graphics_task_submit import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_packet_rectangle_flip_capture import RELOCATIONS
from tools.pad_generated_object import parse_object
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools

BUILD = 'conker/build/game-packet-rectangle-clip-phases'
OWNER, FUNCTION, ENTRY, ROM, WORDS = (
    previous.OWNER, previous.FUNCTION, previous.ENTRY, previous.ROM, previous.WORDS)
INITIAL = previous.INITIAL
RAW_SHA256 = 'f95ee415f2eba533fa4076e5f6c42331367bf3444eb855a78b7816f598dc48c3'
INPUTS = {
    'conker/src/game/generated_C1D70.c': 'ee0b950eea15592bcbf9f9ecb7d4c449156d072959cbf3a807409bdf692b22ab',
    'conker/build/conker.us.elf': 'db5587cb50d49f0ffc3de024bfc87c234d42e499667cc26d624839f4e3bff286',
    'conker/retail_word_patches.us.csv': '3f60679be81037a4035cd35f7b87a85db8764d0ccad1d68b3695bbce6a497e9b',
    'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    'conker/asm/C1D70.s': 'dcf4dee9900592f8f40476367e93b455b7e5a3d1705e2c0bb658657b7780b139',
    'conker/include/2.0L/PR/gbi.h': '155141ca4e38735b9a5642521fb78ac735e4b32ee7509fb8df89966dc12c05b6',
    'conker/include/2.0L/PR/mbi.h': '8a0b32eb3cc7844a38b1b3ed1b160036b203efac0dc3c0275c53354423e40960',
    'conker/Makefile': 'a6e92d90cdeb8c65e7d1ff57f6603ea4f0e5bee6c09d5a028a51a1e0e369bfd6',
    'conker/symbol_addrs.us.txt': 'd0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106',
    'tools/experiments/game_packet_rectangle_step_lifetime.py': '0e8895fe37e238052acefe55c74b56a0b5b4f9ff5e3f731039604c542559874d',
    'tools/experiments/game_packet_rectangle_macro_lifetime.py': 'e85687458f6b10836ae2bb6b9e03aa06533c0371aad6881e80f554a5e396dd27',
    'tools/experiments/game_remaining_donor_candidates.py': '15cec3a86a8b4e5954d5efbc900f5e9d047000672845896633fbe389874de0a1',
    'tools/asm-processor/asm_processor.py': 'b3d9afebcf8bcbf5bcb75a8baa6808dbd5036771aa41d3b1143175aa0c965911',
    'ido/ido5.3_recomp/cc': 'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a',
    'ido/ido5.3_recomp/cfe': 'f6122d3fafc6d9140013068cc762f8048b1bd349e94e8d0839d5bdef26842db9',
    'ido/ido5.3_recomp/uopt': '23c108b975e88034af4ccbd89bd054a1ff3ee4ea9de28f25d91d75a7800f527d',
    'ido/ido5.3_recomp/ugen': 'fa9d94d28fc012ccaf231861a807387278f566ae70fd951c6c41443c135ea23d',
}


def freeze(root, out, installed=False):
    values = {}
    for index, (relative, digest) in enumerate(INPUTS.items()):
        path = out / ('before-%02d' % index) if installed else root / relative
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('Changed rectangle input: ' + relative)
        values[relative] = raw
    out.mkdir(parents=True, exist_ok=True)
    for index, (relative, raw) in enumerate(values.items()):
        target = out / ('before-%02d' % index)
        if target.exists() and target.read_bytes() != raw:
            raise ValueError('Changed rectangle fixture: ' + relative)
        if not target.exists():
            target.write_bytes(raw)
    if installed:
        expected = expected_inputs(values, (out / 'selected-slot.bin').read_bytes())
        for relative, raw in values.items():
            if (root / relative).read_bytes() != expected.get(relative, raw):
                raise ValueError('Changed installed rectangle input: ' + relative)
    return values


def replace_once(body, old, new):
    if body.count(old) != 1:
        raise ValueError('Changed rectangle source anchor: ' + old)
    return body.replace(old, new, 1)


def recovered_owner(before, body):
    lo, hi = previous.build.function_span(before, FUNCTION)
    if before[lo:hi] != INITIAL.split('\n', 1)[1].rstrip():
        raise ValueError('Unknown rectangle source body')
    return before[:lo] + body.split('\n', 1)[1].rstrip() + before[hi:]


def forms():
    yield 'predecessor', INITIAL
    steps = {
        'S': '            stepS = (u16)(0u - (u32)originalStepS);\n',
        'T': '            stepT = (u16)(0u - (u32)stepT);\n',
    }
    origins = {
        'S': '            textureS = (packet->descriptor->unk4 + 255) << 5;\n',
        'T': '            textureT = (s32)((u32)((packet->descriptor->unk6 + 255) << 5) - (u32)fractionalT);\n',
    }
    for roles in (('S',), ('T',), ('S', 'T')):
        body = INITIAL
        for role in roles:
            body = replace_once(body, steps[role] + origins[role], origins[role] + steps[role])
        yield 'flip-origin-first-' + ''.join(roles), body
    for placement in ('before-step', 'after-step'):
        for roles in (('S',), ('T',), ('S', 'T')):
            body = INITIAL
            for role in roles:
                name = 'dimension' + role
                offset = '4' if role == 'S' else '6'
                body = replace_once(body, '    s32 animationDelta;',
                    '    s32 ' + name + ';\n    s32 animationDelta;')
                snapshot = '            ' + name + ' = packet->descriptor->unk' + offset + ';\n'
                origin = origins[role].replace('packet->descriptor->unk' + offset, name)
                block = (snapshot + steps[role] if placement == 'before-step' else
                    steps[role] + snapshot) + origin
                body = replace_once(body, steps[role] + origins[role], block)
            yield 'dimension-' + placement + '-' + ''.join(roles), body
    for kind in ('s16', 'u16'):
        for roles in (('S',), ('T',), ('S', 'T')):
            arguments = ', stepS, stepT);'
            replacement = ', ' + ', '.join('(' + kind + ')step' + r if r in roles else
                'step' + r for r in ('S', 'T')) + ');'
            yield 'macro-step-' + kind + '-' + ''.join(roles), replace_once(INITIAL, arguments, replacement)
    # Every macro use of X already narrows to s16; the Y sign predicate does not.
    narrow_x = replace_once(INITIAL, '(s32)((u32)integerX << 2)', '(s16)((u32)integerX << 2)')
    yield 'macro-narrow-X', narrow_x
    for role in ('S', 'T'):
        body = replace_once(narrow_x, ', stepS, stepT);',
            ', ' + ', '.join('(s16)step' + r if r == role else 'step' + r
                for r in ('S', 'T')) + ');')
        yield 'macro-narrow-X-step-' + role, body


SELECTED = dict(forms())['flip-origin-first-ST']
SELECTED_RAW_SHA256 = 'e2e13c5089c8786bc9aeb729e6b90a26440af550d12cffaa93155b14c3514edb'
SELECTED_SLOT_SHA256 = 'ff3d235b00bf542ffc18643e6c90e1d6475223eb188d9827aed631d5b8cb8e79'


def expected_inputs(values, slot):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    before = values['conker/build/conker.us.elf']
    if hashlib.sha256(before).hexdigest() != INPUTS['conker/build/conker.us.elf']:
        raise ValueError('Changed rectangle predecessor image')
    if len(slot) != 1384 or hashlib.sha256(slot).hexdigest() != SELECTED_SLOT_SHA256:
        raise ValueError('Changed rectangle first emitted slot')
    at = elf_slot_offset(before, ENTRY, WORDS * 4)
    after = before[:at] + slot + before[at + len(slot):]
    return {'conker/build/conker.us.elf': after,
        'conker/src/game/generated_C1D70.c': recovered_owner(
            values['conker/src/game/generated_C1D70.c'].decode(), SELECTED).encode()}


def measure(root, out, label, body=SELECTED, installed=False):
    values = freeze(root, out, installed)
    obj, diagnostics = previous.build.compile_owner(root, out,
        recovered_owner(values['conker/src/game/generated_C1D70.c'].decode(), body), label)
    data, functions = previous.build.link_owner(root, out, obj, OWNER)
    retail = list(struct.unpack_from('>346I', values['conker/conker.us.bin'], ROM))
    words, bindings, row = facts(obj, data, functions, retail)
    row.update(diagnostics=diagnostics, bindings=bindings)
    return obj, words, row


def checked_object(obj):
    text, functions, relocations = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    bindings = {at - f['value']: entries for at, entries in relocations.items()
        if f['value'] <= at < f['value'] + f['size']}
    pools = {name: data for name, (_, data) in sections(obj).items()
        if name.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')) and data}
    if len(raw) != 1384 or hashlib.sha256(raw).hexdigest() != SELECTED_RAW_SHA256 or bindings != RELOCATIONS or pools:
        raise ValueError('Changed rectangle object words, bindings or pools')
    return raw, bindings


def qualify(root, out, installed=False):
    values = freeze(root, out, installed)
    obj, words, row = measure(root, out, 'qualified', installed=installed)
    if (row['words'], row['frame'], row['differences'], row['diagnostics'], row['sha256'],
            row['linked_sha256']) != (346, 136, 6, '', SELECTED_RAW_SHA256, SELECTED_SLOT_SHA256):
        raise ValueError('Unknown selected rectangle emission')
    checked_object(obj)
    script = out / 'qualified-padded.s'
    script.write_text(emit_padded_assembly(obj, root / 'conker/asm/C1D70.s',
        filename=OWNER, word_patches_path=root / 'conker/retail_word_patches.us.csv'))
    padded = script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(padded), str(script)],
        check=True, capture_output=True)
    data, functions = previous.build.link_owner(root, out, padded, OWNER)
    f = functions[FUNCTION]
    slot = data[f['value']:f['value'] + f['size']]
    if slot != struct.pack('>346I', *words):
        raise ValueError('Rectangle padder changed the selected body')
    selected_slot = out / 'selected-slot.bin'
    if selected_slot.exists() and selected_slot.read_bytes() != slot:
        raise ValueError('Changed rectangle first emitted slot')
    if not selected_slot.exists():
        selected_slot.write_bytes(slot)
    predicted = expected_inputs(values, slot)
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    expected = predicted['conker/build/conker.us.elf']
    at = elf_slot_offset(expected, ENTRY, len(slot))
    if expected[at:at + len(slot)] != slot:
        raise ValueError('Prediction did not use actual emitted C')
    for key, raw in predicted.items():
        path = out / ('after-elf' if key.endswith('.elf') else 'after-owner')
        if path.exists() and path.read_bytes() != raw:
            raise ValueError('Changed immutable rectangle successor')
        if not path.exists():
            path.write_bytes(raw)
    row.update(pools=normalized_pools(obj), new_guards=0)
    return obj, padded, words, row


def audit(root, out):
    from tools.check_game_data_layout import audit_layout
    from tools.match_progress import load_elf_functions
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    values = freeze(root, out, installed=True)
    before = out / 'before-01'
    actual = root / 'conker/build/conker.us.elf'
    old, _, old_addresses = load_elf_functions(str(before), 'mips-linux-gnu-objdump')
    new, _, addresses = load_elf_functions(str(actual), 'mips-linux-gnu-objdump')
    if set(old) != set(new) or old_addresses != addresses:
        raise ValueError('Changed rectangle ELF function set')
    changed = []
    for name, old_row in old.items():
        new_row = new[name]
        if old_row != new_row:
            changed.append(name)
    if changed != [FUNCTION]:
        raise ValueError('Changed non-target rectangle ELF functions')
    a = sorted((n, f[1:]) for _, n, f, _ in symbol_rows(values['conker/build/conker.us.elf']))
    b = sorted((n, f[1:]) for _, n, f, _ in symbol_rows(actual.read_bytes()))
    if a != b:
        raise ValueError('Changed rectangle symbol metadata')
    same_functions(out / 'qualified-padded.o',
        root / 'conker/build/src/game/generated_C1D70.c.o')
    layout = audit_layout(actual, root / 'conker')
    if (layout['exact'], layout['bytes'], layout['owner_count'], layout['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Changed rectangle Game data layout')
    row = dict(functions=len(old), changed=changed,
        changed_ELF_bytes=sum(a != b for a, b in zip(before.read_bytes(), actual.read_bytes())),
        metadata_exclusions=0, data_layout=layout)
    (out / 'installed-audit.json').write_text(json.dumps(row, indent=2) + '\n')
    return row


def facts(obj, data, functions, retail):
    text, raw_functions, relocations = parse_object(obj)
    f = functions[FUNCTION]
    raw = data[f['value']:f['value'] + f['size']]
    words = list(struct.unpack('>%dI' % (len(raw) // 4), raw))
    different = [i for i in range(max(len(words), len(retail)))
        if i >= len(words) or i >= len(retail) or words[i] != retail[i]]
    target = raw_functions[FUNCTION]
    unlinked = text[target['value']:target['value'] + target['size']]
    bindings = {at - target['value']: entries for at, entries in relocations.items()
        if target['value'] <= at < target['value'] + target['size']}
    return words, bindings, dict(words=len(words), frame=(-words[0]) & 0xffff,
        differences=len(different), different=different,
        prefix=different[0] if different else len(words),
        suffix=len(words) - different[-1] - 1 if different and len(words) == WORDS else 0,
        sha256=hashlib.sha256(unlinked).hexdigest(),
        linked_sha256=hashlib.sha256(raw).hexdigest())


def screen(root, out, emit=None):
    values = freeze(root, out)
    before = values['conker/src/game/generated_C1D70.c'].decode()
    retail = list(struct.unpack('>%dI' % WORDS,
        values['conker/conker.us.bin'][ROM:ROM + WORDS * 4]))
    rows = []
    for label, body in forms():
        obj, diagnostics = previous.build.compile_owner(root, out,
            recovered_owner(before, body), label)
        data, functions = previous.build.link_owner(root, out, obj, OWNER)
        words, bindings, row = facts(obj, data, functions, retail)
        if diagnostics:
            raise ValueError('Rectangle compiler diagnostics: ' + diagnostics)
        if not rows:
            if (row['words'], row['frame'], row['differences'], row['sha256']) != (
                    WORDS, 0x88, 18, RAW_SHA256):
                raise ValueError('Unknown current rectangle emission')
            baseline_obj, baseline_bindings = obj, bindings
            baseline_words, baseline_different = words, set(row['different'])
            pools = normalized_pools(obj)
        neighbors = same_functions(baseline_obj, obj, (FUNCTION,))
        if normalized_pools(obj) != pools:
            raise ValueError('Changed rectangle owner pools')
        different = set(row['different'])
        row.update(label=label, source_sha256=hashlib.sha256(body.encode()).hexdigest(),
            neighbors=neighbors, pools_unchanged=True, diagnostics=diagnostics,
            bindings_unchanged=bindings == baseline_bindings,
            old_exact_losses=sorted(different - baseline_different),
            new_exact_words=sorted(baseline_different - different),
            identical_to_predecessor=words == baseline_words)
        rows.append(row)
        if emit:
            emit(row)
    (out / 'screen.json').write_text(json.dumps(rows, indent=2) + '\n')
    freeze(root, out)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    screen(args.root, args.root / BUILD,
        lambda row: print(json.dumps(row), flush=True))


if __name__ == '__main__':
    main()
