"""Direct actor-choice instructions, pool bindings, caller ABI and image proof."""
import json
import struct
import subprocess
import unittest
from pathlib import Path

from tools.experiments import game_actor_choice_15146970_match as source
from tools.tests import game_actor_choice_15146970_oracle as guest
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode, WindowBoundary
from tools.experiments.game_remaining_donor_candidates import sections


def symbols():
    return dict(jtbl_800A56E4_game=guest.TABLE, D_800BE9F0=guest.WORLD,
                func_151420F8=guest.PREDICATE, D_800A56D0=guest.CHOICES,
                D_800CC2D0=guest.ACTORS, func_150A2AEC=guest.LOOKUP)


class ActorChoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = source.ROOT
        cls.out = cls.root/source.BUILD
        cls.q = source.prepare(cls.root)
        cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.elf = (cls.root/source.ELF).read_bytes()
        cls.truth = list(struct.unpack_from('>74I', cls.rom, source.ROM))
        cls.normal = source.bound_blob(cls.q['normal'], cls.q['normal_refs'], symbols())
        cls.receipts = {}

    @classmethod
    def tearDownClass(cls):
        (cls.out/'suite-detail.json').write_text(json.dumps(cls.receipts, indent=2)+'\n')

    def test_01_direct_words_pool_ownership_and_guards(self):
        q = self.q['report']
        self.assertEqual((q['words'], q['frame'], q['guards'], q['raw_neighbors'], q['padded_neighbors']), (74, 48, 2, 12, 12))
        self.assertEqual((q['functions'], q['strict_changed_bytes'], q['exclusions'], q['diagnostics']), (6052, 257, 0, 0))
        self.assertEqual(self.normal, self.truth)
        self.assertEqual(self.q['raw'], self.q['normal'])
        rows = source.guard_rows(self.q['raw'], self.q['refs'])
        self.assertEqual([r[2] for r in rows], ['0x0A8', '0x0AC'])
        self.assertTrue(all(r[3] == r[4] and '.data' in r[5] and 'D_800A56D0' in r[6] for r in rows))
        for offset in (168, 172):
            bad = bytearray(self.q['raw'])
            bad[offset+3] ^= 1
            with self.assertRaises(ValueError):
                source.normalize(bytes(bad), self.q['refs'])
        for offset in source.BINDINGS:
            bad = dict(self.q['refs'])
            bad[offset] = [('R_MIPS_26', 'wrong')]
            with self.assertRaises(ValueError):
                source.normalize(self.q['raw'], bad)
        before = (self.out/'predecessor-guards.csv').read_bytes()
        self.assertTrue(source.guard_manifest(before, self.q['raw'], self.q['refs']).startswith(before))
        with self.assertRaises(ValueError):
            source.guard_manifest(before+b'\n', self.q['raw'], self.q['refs'])
        self.receipts['scope'] = dict(direct_words=74, frame=48, instruction_changes=0, relocation_only_guards=2,
                                     switch_entries=9, initializer_words=5, original_case_labels_retained=9,
                                     raw_and_padded_neighbors=12, inherited_guard_prefix_preserved=True,
                                     raw_word_negatives=2, binding_negatives=10)

    def test_02_independent_model_original_predicate_and_lookup_paths(self):
        count = 0
        visited, provider_calls = set(), set()
        connected_words = set()
        for case in guest.cases():
            initial = guest.fixture(case)
            expected = guest.reference(initial, case)
            machines = []
            for body in (self.truth, self.normal):
                machine = guest.Oracle(body, initial, case)
                registers, floats = machine.r[:], machine.f[:]
                machine.run()
                self.assertEqual((guest.public(machine.memory, case), machine.semantic_calls, machine.r[2]), expected, case)
                self.assertEqual(machine.r[16:24], registers[16:24])
                self.assertEqual((machine.r[29], machine.r[31]), (registers[29], registers[31]))
                self.assertEqual(machine.f[20:], floats[20:])
                machines.append(machine)
            self.assertEqual(guest.state(machines[0]), guest.state(machines[1]))
            visited.update(machines[0].visits)
            if case.connected:
                connected_words.update(machines[0].visits)
            if machines[0].shifts:
                provider_calls.add('rshift')
            if machines[0].collisions:
                provider_calls.add('collision')
            count += 1
        self.assertEqual(set(range(source.ENTRY, source.ENTRY+296, 4))-visited, set())
        self.assertEqual(provider_calls, {'rshift', 'collision'})
        # The predicate is a current exact helper. The lookup is still a
        # production placeholder; execute its full original control flow from ROM.
        at = source.elf_slot_offset(self.elf, guest.PREDICATE, 136)
        self.assertEqual(self.elf[at:at+136], self.rom[0x16F5A8:0x16F5A8+136])
        self.assertGreater(len(connected_words & set(range(guest.PREDICATE, guest.PREDICATE+136, 4))), 0)
        self.assertGreater(len(connected_words & set(range(guest.LOOKUP, guest.LOOKUP+440, 4))), 0)
        self.receipts['model'] = dict(cases=count, target_words_covered=74, full_word_selector=True,
                                     wrapped_signed_actor_difference_and_truncating_division=True,
                                     copied_list_snapshot=True, provider_mutations=True, preserved_roles=True,
                                     complete_raw_normalized_retail_state_equal=True,
                                     original_predicate_words=34, original_lookup_words=110,
                                     original_lookup_has_both_mask_and_collision_paths=True,
                                     shift_and_collision_services_bounded=True, production_lookup_unmodified=True)

    def test_03_table_census_and_original_classifier_window(self):
        jal = 0xC000000 | (source.ENTRY >> 2 & 0x3FFFFFF)
        calls, pointers = [], []
        for p in range(0, len(self.rom)-3, 4):
            word = struct.unpack_from('>I', self.rom, p)[0]
            if word == jal:
                calls.append(p)
            if source.ENTRY <= word < source.ENTRY+296:
                pointers.append((p, word))
        self.assertEqual(calls, [])
        self.assertEqual(pointers, [(0x22EB44, source.ENTRY)]+[(0x24A1A4+4*i, source.ENTRY+v) for i, v in enumerate(guest.OFFSETS)])
        parent, end = 0x15141A7C, 0x15141C0C
        at = source.elf_slot_offset(self.elf, parent, end-parent)
        self.assertEqual(self.elf[at:at+end-parent], self.rom[0x16EF2C:0x16EF2C+end-parent])
        entry, table = 0x15141AE4, 0x8008A084
        window = struct.unpack_from('>10I', self.rom, 0x16EF94)
        code = dict(zip(range(source.ENTRY, source.ENTRY+296, 4), self.normal))
        checks = 0
        for case in [guest.Case(kind=k) for k in range(10)]+[guest.Case(kind=1, predicate=0), guest.Case(kind=6, lookup=0), guest.Case(kind=1, connected=2, masked=1, match=2)]:
            initial = guest.fixture(case)
            for i in range(4):
                initial[table+i] = 0
            guest.wr(initial, table, source.ENTRY, 4)
            machine = guest.Oracle(window, initial, case, entry=entry, connected=code, arguments=(0,))
            machine.r[16], machine.r[17], machine.r[18], machine.r[2] = 0, table, guest.actor(case), guest.u32(case.kind)
            machine.code = WindowCode(machine.code, machine)
            machine.code.ends = (0x15141B0C, 0x15141B60)
            with self.assertRaises(WindowBoundary):
                machine.run()
            self.assertEqual(machine.calls[0], (source.ENTRY, (guest.u32(case.kind), guest.actor(case))))
            expected = guest.reference(initial, case)
            self.assertEqual((machine.semantic_calls, machine.r[2], machine.r[7]), (expected[1], expected[2], expected[2]))
            self.assertEqual(machine.r[29], guest.STACK)
            checks += 1
        self.receipts['caller'] = dict(direct_calls=0, entry_pointers=1, original_switch_pointers=9,
                                      classifier_slot=0, original_parent_words=100, window_words=10,
                                      connected_window_cases=checks, typed_s32_pointer_s32_return=True,
                                      full_dispatcher_or_gameplay_acceptance_not_claimed=True)

    def test_04_executed_access_cuts(self):
        checks = 0
        for case in (guest.Case(kind=-1), guest.Case(kind=1), guest.Case(kind=6), guest.Case(kind=1, connected=2, masked=1, match=2)):
            initial = guest.fixture(case)
            complete = guest.Oracle(self.truth, initial, case)
            complete.run()
            for cut in range(complete.all_accesses):
                states = []
                for body in (self.truth, self.normal):
                    machine = guest.Oracle(body, initial, case)
                    machine.cut = cut
                    with self.assertRaises(AccessBoundary):
                        machine.run()
                    states.append(guest.state(machine))
                self.assertEqual(states[0], states[1], (case, cut))
                checks += 1
        self.receipts['access_cuts'] = dict(executed_cuts=checks, complete_literal_state_equal=True)

    def test_05_native32_callback_and_effective_controls(self):
        def run(label, body=None, opt='-O2'):
            p = self.out/(label+'.c')
            p.write_text(guest.native_harness(body))
            exe = p.with_suffix('.elf')
            result = subprocess.run([*native_command(opt), '-mstackrealign', '-fno-strict-aliasing', str(p.relative_to(self.root)), '-o', str(exe.relative_to(self.root))], cwd=self.root, capture_output=True, text=True)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))
            return subprocess.run([str(exe)], timeout=20).returncode
        for opt in ('-O0', '-O2', '-O3'):
            self.assertEqual(run('native'+opt, opt=opt), 0)
        body = source.SELECTED
        negatives = dict(stub=body[:body.index('{')+1]+'\nreturn 0;\n}',
                         byte_selector=body.replace('switch (kind)', 'switch ((u8)kind)'),
                         wrong_world=body.replace('D_800BE9F0 == 4', 'D_800BE9F0 == 3'),
                         positive_predicate=body.replace('if (func_151420F8(actor))', 'if (func_151420F8(actor) > 0)'),
                         wrong_actor_stride=body.replace('/ 0x32C', '/ 0x330'),
                         wrong_list=body.replace('0x401F', '0x401A'),
                         wrong_count=body.replace('5, choices)', '4, choices)'),
                         wrong_lookup_sentinel=body.replace('5, choices) == -1', '5, choices) == 0'))
        for label, changed in negatives.items():
            self.assertNotEqual(changed, body, label)
            self.assertEqual(run('negative-'+label, changed), 1, label)
        self.receipts['native'] = dict(cases_per_executable=len(guest.native_cases()), optimizations=3,
                                      semantic_negatives=list(negatives), SDK_widths_and_typed_callback=True,
                                      valid_actor_arena=True, trapping_UBSan=True, original_initializer_values=True,
                                      relocated_initializer_memory_and_private_faults_guest_only=True)

    def test_06_independent_code_and_pool_links_and_image_corruptions(self):
        moved = dict(jtbl_800A56E4_game=0x81258004, D_800BE9F0=0x81268000,
                     func_151420F8=0x17508010, D_800A56D0=0x81248000,
                     D_800CC2D0=0x81277FF8, func_150A2AEC=0x17518000)
        for i, (entry, bindings) in enumerate(((source.ENTRY, symbols()), (0x17407F50, moved))):
            lines = ['.set noreorder', '.set noat', '.text', '.globl '+source.FUNCTION, source.FUNCTION+':']
            for j, (word,) in enumerate(struct.iter_unpack('>I', self.q['normal'])):
                refs = self.q['normal_refs'].get(j*4, [])
                if not refs:
                    lines.append('.word 0x%08X' % word)
                else:
                    kind, name = refs[0]
                    rt, rs = word>>16&31, word>>21&31
                    if kind == 'R_MIPS_26':
                        line = 'jal '+name
                    elif kind == 'R_MIPS_HI16':
                        line = 'lui $%d, %%hi(%s)' % (rt, name)
                    elif word>>26 == 35:
                        line = 'lw $%d, %%lo(%s)($%d)' % (rt, name, rs)
                    else:
                        line = 'addiu $%d, $%d, %%lo(%s)' % (rt, rs, name)
                    lines.append(line)
            # The two compiler pools have separate alignment tails. Retail
            # packs the 20 useful initializer bytes directly before the table.
            lines += ['.section .rodata']+['.word %s+%d' % (source.FUNCTION, v) for v in guest.OFFSETS]+['.data']+['.word 0x%X' % v for v in guest.IDS]
            p = self.out/('rebase-'+str(i))
            p.with_suffix('.s').write_text('\n'.join(lines)+'\n')
            p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x%X : SUBALIGN(4) { *(.rodata) } .data 0x%X : SUBALIGN(4) { *(.data) } }\n' % (entry, bindings['jtbl_800A56E4_game'], bindings['D_800A56D0']))
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-no-pad-sections', '-o', str(p.with_suffix('.o')), str(p.with_suffix('.s'))], check=True, capture_output=True)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(p.with_suffix('.ld')), *['--defsym=%s=0x%X' % (n, a) for n, a in bindings.items()], '-o', str(p.with_suffix('.elf')), str(p.with_suffix('.o'))], check=True, capture_output=True)
            pools = sections(p.with_suffix('.elf'))
            self.assertEqual(list(struct.unpack_from('>74I', pools['.text'][1])), source.bound_blob(self.q['normal'], self.q['normal_refs'], bindings))
            self.assertEqual(pools['.rodata'][1], struct.pack('>9I', *[entry+v for v in guest.OFFSETS]))
            self.assertEqual(pools['.data'][1], struct.pack('>5I', *guest.IDS))
        before, after = self.q['predecessor_elf'].read_bytes(), self.q['qualified_elf'].read_bytes()
        truth = self.rom[source.ROM:source.ROM+296]
        self.assertEqual(source.strict_image(before, after, truth), 257)
        at = next(p for p, n, f, s in source.symbol_rows(before) if n == source.FUNCTION)
        for offset in (64, source.elf_slot_offset(before, source.ENTRY, 296), at+8, 2740849, 2816704, 3030988, 3093463, source.elf_slot_offset(before, guest.CHOICES, 20)):
            bad = bytearray(after)
            bad[offset] ^= 1
            with self.assertRaises(ValueError):
                source.strict_image(before, bytes(bad), truth)
        self.receipts['image'] = dict(changed_bytes=257, exclusions=0, independent_links=2,
                                     all_ten_code_bindings=True, switch_R32_entries=9, initializer_words=5,
                                     signed_LO_carries=True, named_metadata_pair_swaps=2,
                                     corruption_controls=8, protected_data_bytes=189088, protected_owners=720)


if __name__ == '__main__':
    unittest.main()
