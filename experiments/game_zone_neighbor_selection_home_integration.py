"""Qualify source-only private homes through both owner profiles and padding."""

import json
import shutil
import struct
import subprocess
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_zone_neighbor_selection_homes as homes
from tools.experiments import game_route_actor_event_candidates as snapshots
from tools.experiments.game_route_projection_integration import compile_profile
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.experiments.game_graphics_task_submit import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.pad_generated_object import parse_object, emit_padded_assembly


BUILD = homes.BUILD + '/integration'
SOURCE, OWNER = 'conker/src/game/generated_B3020.c', 'generated_B3020'
FUNCTION, ENTRY, ROM, SIZE = 'func_1508B3F8', 0x1508B3F8, 0xB88A8, 1476
INPUTS = {
    SOURCE: 'a5187038998c59d0630b480e8cc03e87e43aed40a6a27c9eeb8207e46bfd44ea',
    'conker/build/conker.us.elf': '0462d68d9fe12d04c2d747b1f8877305f84bce1ac7793e24024268e6e06e07c7',
    'conker/retail_word_patches.us.csv': 'e870831d0fe6d5562f156698a9c24d0af1f864fe95b8a1790bcdcf664be60dc4',
    'conker/progress.csv': '16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be',
    'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
    'conker/asm/B3020.s': '26ef139d5592329ed22f9287267c13fefadf7f17290bc5ef1085cbe20e80b187',
    'conker/Makefile': 'cf6de057267055cf5ad789e72426b7433c0bfe37d04ae56c241332cf2f2febf4',
    'conker/symbol_addrs.us.txt': 'd0906b571bc87c2dc3e436b2245b69df9165bddd175c6b0d2498a0d21e8e2106',
    'conker/retail_layout.us.txt': 'a26cc89426fb1e9bc4bf80c0c94fabbc4c6a56c853024925fc2ba5b26027e1c5',
    'conker/include/structs.h': '081b0f0bd0f86173c34674f1d1434a9a09a6f59e6e05d5fa375613afbed7be69',
    'conker/include/2.0L/PR/sched.h': '40a7e05e5e774a3cbc015d44bb8225f469937de178bfe84cd1de9ef3c5ff7572',
    'ido/ido5.3_recomp/cc': 'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a',
    'ido/ido5.3_recomp/cfe': 'f6122d3fafc6d9140013068cc762f8048b1bd349e94e8d0839d5bdef26842db9',
    'ido/ido5.3_recomp/uopt': '23c108b975e88034af4ccbd89bd054a1ff3ee4ea9de28f25d91d75a7800f527d',
    'ido/ido5.3_recomp/ugen': 'fa9d94d28fc012ccaf231861a807387278f566ae70fd951c6c41443c135ea23d',
    'conker/asm/nonmatchings/generated_B3020/func_1508802C.s': 'b39962df8e9c69c8b1dcbcdc966f800629b4f766272de49077016e09d6a9781c',
    'conker/asm/nonmatchings/generated_B3020/func_150880F8.s': '458a28abcd34caa2d5b2a2d81eef68e3f5b3dbe04b504552ee2507053e10185a',
    'conker/asm/nonmatchings/generated_B3020/func_150885EC.s': 'fa53c1e57e0adc20d2eb72d62f8d9ef10904448671a84efe382736d58a025151',
    'conker/asm/nonmatchings/generated_B3020/func_1508868C.s': '4dd68e203f15f82856252b42d1ed7fafbf970848ead3a177b07987aed75a0329',
}
COMMENT = '/* Resolve queued zones into per-player neighbor labels. */\n'


def freeze(root, out):
    with patch.object(snapshots, 'INPUTS', INPUTS):
        return snapshots.freeze(root, out)


def recovered_owner(before):
    if before.count(homes.source.SELECTED) != 1:
        raise ValueError('Unknown zone-selection source predecessor')
    return before.replace(homes.source.SELECTED, COMMENT + homes.SELECTED)


def payload(obj):
    text, functions, bindings = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value'] + f['size']]
    words = struct.unpack('>%dI' % (len(raw) // 4), raw)
    end = max(i for i, w in enumerate(words) if w == 0x03E00008) + 2
    if any(words[end:]):
        raise ValueError('Nonzero zone-selection alignment tail')
    return raw[:end * 4], {at - f['value']: entries for at, entries in bindings.items()
                          if f['value'] <= at < f['value'] + end * 4}


def padded(root, out, guards):
    asm = out / 'home-padded.s'
    asm.write_text(emit_padded_assembly(out / 'after-primary.o', root / 'conker/asm/B3020.s',
        function_objects={name: out / 'after-normal.o' for name in
                          ('func_150891E8', 'func_1508BC20', 'func_15089BC0')},
        word_patches_path=guards, filename=OWNER))
    obj = asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
                    '-I', str(root / 'conker/include'), '-o', str(obj), str(asm)],
                   check=True, capture_output=True)
    return obj


def qualify(root, out):
    values = freeze(root, out)
    before = values[SOURCE].decode()
    unit = recovered_owner(before)
    for label, normal in (('primary', False), ('normal', True)):
        a, da = compile_profile(root, out, before, 'before-' + label, normal)
        b, db = compile_profile(root, out, unit, 'after-' + label, normal)
        if da or db or same_functions(a, b, (FUNCTION,)) != 72:
            raise ValueError('Private-home permutation changed another raw owner function')
        if normalized_pools(a) != normalized_pools(b):
            raise ValueError('Private-home permutation changed raw pools')
        raw_a, binds_a = payload(a)
        raw_b, binds_b = payload(b)
        if len(raw_a) != len(raw_b) or binds_a != binds_b:
            raise ValueError('Private-home permutation changed length or relocation bindings')
        for x, y in zip(struct.unpack('>%dI' % (len(raw_a) // 4), raw_a),
                        struct.unpack('>%dI' % (len(raw_b) // 4), raw_b)):
            if x != y and (x >> 16 != y >> 16 or x >> 21 & 31 != 29):
                raise ValueError('Private-home permutation changed a non-stack instruction field')
    guards = out / 'unchanged-guards.csv'
    guards.write_bytes(values['conker/retail_word_patches.us.csv'])
    obj = padded(root, out, guards)
    baseline = out / 'before-padded.o'
    if not baseline.exists():
        shutil.copyfile(root / 'conker/build/src/game/generated_B3020.c.o', baseline)
    a, fa = link_owner(root, out, baseline, OWNER)
    b, fb = link_owner(root, out, obj, OWNER)
    if fa != fb or same_functions(baseline, obj, (FUNCTION,)) != 72:
        raise ValueError('Private-home permutation changed padded addresses/extents/neighbors')
    at = fb[FUNCTION]['value']
    if a[:at] != b[:at] or a[at + SIZE:] != b[at + SIZE:]:
        raise ValueError('Private-home permutation changed another padded byte')
    if normalized_pools(baseline) != normalized_pools(obj):
        raise ValueError('Private-home permutation changed padded pools')
    old = values['conker/build/conker.us.elf']
    slot = elf_slot_offset(old, ENTRY, SIZE)
    if a[at:at + SIZE] != old[slot:slot + SIZE]:
        raise ValueError('Private-home predecessor does not reproduce installed bytes')
    truth = values['conker/conker.us.bin'][ROM:ROM + SIZE]
    changed = b[at:at + SIZE]
    if len(changed) != SIZE or changed == truth:
        raise ValueError('Expected a complete nonmatching 369-word improvement')
    (out / 'qualified-target.bin').write_bytes(changed)
    (out / 'proposed-owner.c').write_text(unit)
    result = dict(words=369, frame=320,
                  raw_differences=sum(x != y for x, y in zip(
                      struct.unpack('>369I', changed), struct.unpack('>369I', truth))),
                  query_home=0xAC, selections_home=0x124, zone_home=0x94, counter_home=0x13C,
                  preserved_raw_neighbors_per_profile=72, preserved_padded_neighbors=72,
                  all73_addresses_and_extents_fixed=True, guards_unchanged=True,
                  Makefile_unchanged=True, matching_credit=0)
    (out / 'qualification.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def check_inputs(root, out):
    values = freeze(root, out)
    for name, before in values.items():
        if (root / name).read_bytes() != before:
            raise ValueError('Unexpected private-home input change: ' + name)
    return values


def main():
    root = Path(__file__).resolve().parents[2]
    out = root / BUILD
    print(json.dumps(qualify(root, out), indent=2))


if __name__ == '__main__':
    main()
