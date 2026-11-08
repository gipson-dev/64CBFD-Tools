"""Triangle ABI, ordered signed geometry, original callers and complete image."""
import json
import struct
import subprocess
import unittest
from dataclasses import replace
from pathlib import Path

from tools.experiments import game_triangle_facing_1510e670_match as source
from tools.tests import game_triangle_facing_1510e670_oracle as guest
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode, WindowBoundary
from tools.experiments.game_remaining_donor_candidates import sections


class TriangleFacingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = source.ROOT
        cls.out = cls.root/source.BUILD
        cls.q = source.prepare(cls.root)
        cls.rom = (cls.root/'conker/conker.us.bin').read_bytes()
        cls.elf = (cls.root/source.ELF).read_bytes()
        cls.truth = list(struct.unpack_from('>77I', cls.rom, source.ROM))
        cls.normal = source.bound_blob(cls.q['normal'], cls.q['normal_refs'], dict(D_800D3300=guest.TABLE, func_150AD8B0=guest.CROSS))
        cls.raw = source.bound_blob(cls.q['raw'], cls.q['refs'], dict(D_800D3300=guest.TABLE, func_150AD8B0=guest.CROSS))
        cls.receipts = {}

    @classmethod
    def tearDownClass(cls):
        (cls.out/'suite-detail.json').write_text(json.dumps(cls.receipts, indent=2)+'\n')

    def test_01_closed_normalization_and_owner_scope(self):
        report = self.q['report']
        self.assertEqual((report['words'], report['frame'], report['guards'], report['raw_neighbors'], report['padded_neighbors']), (77, 88, 3, 13, 13))
        self.assertEqual((report['functions'], report['strict_changed_bytes'], report['exclusions'], report['diagnostics']), (6052, 210, 0, 0))
        self.assertEqual(self.normal, self.truth)
        self.assertEqual([i for i, (a, b) in enumerate(zip(self.raw, self.truth)) if a != b], [62, 63, 65])
        self.assertEqual(self.q['refs'], source.BINDINGS)
        for i in (62, 63, 65):
            bad = bytearray(self.q['raw'])
            bad[i*4+3] ^= 1
            with self.assertRaises(ValueError):
                source.normalize(bytes(bad), self.q['refs'])
        for refs in ({}, dict(self.q['refs'], **{'240': [('R_MIPS_26', 'wrong')]})):
            with self.assertRaises(ValueError):
                source.normalize(self.q['raw'], refs)
        before = (self.out/'predecessor-guards.csv').read_bytes()
        after = source.guard_manifest(before, self.q['raw'], self.q['refs'])
        self.assertTrue(after.startswith(before))
        with self.assertRaises(ValueError):
            source.guard_manifest(before+b'\n', self.q['raw'], self.q['refs'])
        self.receipts['scope'] = dict(words=77, frame=88, guards=3, raw_and_padded_neighbors=13, new_warnings=0,
                                     original_relocations=3, negative_raw_and_binding_controls=5, inherited_guard_prefix_preserved=True)

    def test_02_ordered_geometry_original_cross_and_private_aliases(self):
        count = 0
        visited = set()
        for case in guest.cases():
            initial = guest.fixture(case)
            expected = guest.reference(initial, case)
            machines = []
            for label, words in (('retail', self.truth), ('normal', self.normal), ('raw', self.raw)):
                machine = guest.Oracle(words, initial, case)
                registers, floats = machine.r[:], machine.f[:]
                machine.run()
                self.assertEqual((guest.public(machine.memory, case), machine.semantic_calls, machine.r[2]), expected, (label, case))
                self.assertEqual(machine.r[16:24], registers[16:24])
                self.assertEqual((machine.r[29], machine.r[31]), (registers[29], registers[31]))
                self.assertEqual(machine.f[20:], floats[20:])
                machines.append(machine)
            self.assertEqual(guest.state(machines[0]), guest.state(machines[1]))
            self.assertEqual(machines[0].memory, machines[2].memory)
            visited.update(machines[0].visits)
            count += 1
        self.assertEqual(set(range(source.ENTRY, source.ENTRY+308, 4))-visited, set())
        at = source.elf_slot_offset(self.elf, guest.CROSS, 76)
        self.assertEqual(self.elf[at:at+76], self.rom[0xDAD60:0xDAD60+76])
        self.assertTrue(visited & set(range(guest.CROSS, guest.CROSS+76, 4)))
        self.receipts['model'] = dict(cases=count, instruction_coverage=77, original_cross_words=19,
                                     full_word_guest_indices=True, ordered_signed_halfword_reads=True,
                                     unsigned_byte_offsets=True, degeneracy_and_winding=True, private_vertex_edge_aliases=True,
                                     forced_nan_and_infinities=True, complete_normalized_state_equal=True,
                                     raw_memory_and_preserved_roles_equal=True, hardware_FCSR_or_nan_payload_not_emulated=True)

    def test_03_original_three_caller_windows_and_literal_owner(self):
        code = dict(zip(range(source.ENTRY, source.ENTRY+308, 4), self.normal))
        start, end = 0x1510E950, 0x1510F648
        at = source.elf_slot_offset(self.elf, start, end-start)
        self.assertEqual(self.elf[at:at+end-start], self.rom[0x13BE00:0x13BE00+end-start])
        word = 0x0C000000 | (source.ENTRY >> 2 & 0x3FFFFFF)
        calls = [0x15000000+p-0x2D4B0 for p in range(0x2D4B0, 0x24D500, 4) if int.from_bytes(self.rom[p:p+4], 'big') == word]
        self.assertEqual(calls, [0x1510EEB0, 0x1510EFAC, 0x1510F300])
        windows = ((0x1510EEB0, 9, (0x1510EED4,)), (0x1510EFAC, 10, (0x1510EFD4,)),
                   (0x1510F300, 5, (0x1510F314, 0x1510F3C4)))
        checks = 0
        for entry, size, ends in windows:
            body = list(struct.unpack_from('>%dI' % size, self.rom, entry-0x15000000+0x2D4B0))
            for points, absent in ((guest.Case().points, False), (tuple(reversed(guest.Case().points)), False), (guest.Case().points, True)):
                case = guest.Case(index=2, points=points, absent=absent)
                initial = guest.fixture(case)
                for address in (0x800A2D88, 0x800A2D8C, 0x800A2D90):
                    guest.wr(initial, address, 0x3E800000, 4)
                expected = guest.reference(initial, case)
                machine = guest.Oracle(body, initial, case, entry=entry, connected=code, arguments=(2,))
                machine.r[16], machine.r[19] = 2, 0x13579BDF
                machine.f[20] = 0x3F400000
                machine.code = WindowCode(machine.code, machine)
                machine.code.ends = ends
                with self.assertRaises(WindowBoundary):
                    machine.run()
                self.assertEqual(machine.calls[0], (source.ENTRY, (2,)))
                self.assertEqual(machine.r[2], expected[2])
                self.assertEqual(machine.semantic_calls, expected[1])
                self.assertEqual(machine.r[29], guest.STACK)
                if entry == 0x1510EEB0 and expected[2]:
                    self.assertEqual([guest.rd(machine.memory, guest.STACK+p, 4) for p in (0xCC, 0xD4, 0xD0)], [1, 2, 0x13579BDF])
                if entry == 0x1510EFAC:
                    self.assertEqual(machine.r[18], 0)
                    if expected[2]:
                        self.assertEqual((guest.rd(machine.memory, guest.STACK+0x12C, 4), machine.r[30], machine.f[26], guest.rd(machine.memory, guest.STACK+0x140, 4)), (0x13579BDF, 1, 0x3F400000, 2))
                checks += 1
        self.receipts['callers'] = dict(all_direct_JALs=3, original_caller_words=830, connected_windows=3,
                                       cases=checks, typed_s32_index_and_return=True, full_caller_gameplay_not_qualified=True)

    def test_04_access_cut_normalized_state(self):
        checks = 0
        for case in (guest.Case(), guest.Case(absent=True), guest.Case(alias=1), guest.Case(forced=0x7FC12345)):
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
        self.receipts['access_cuts'] = dict(executed_instruction_access_cuts=checks, literal_normalized_state=True,
                                           raw_FPR_fault_identity_not_claimed=True)

    def test_05_native32_leaf_and_effective_negatives(self):
        def run(label, body=None, opt='-O2'):
            path = self.out/(label+'.c')
            path.write_text(guest.native_harness(body))
            exe = path.with_suffix('.elf')
            result = subprocess.run([*native_command(opt), '-mstackrealign', '-fno-strict-aliasing', str(path.relative_to(self.root)), '-o', str(exe.relative_to(self.root))], cwd=self.root, capture_output=True, text=True)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))
            return subprocess.run([str(exe)], timeout=20).returncode
        for opt in ('-O0', '-O2', '-O3'):
            self.assertEqual(run('native'+opt, opt=opt), 0)
        body = source.SELECTED
        negatives = dict(stub=body[:body.index('{')+1]+'\nreturn 0;\n}',
                         wrong_null_result=body.replace('    return 0;\n}', '    return 1;\n}'),
                         unsigned_coordinate=body.replace('second[0] - first[0]', '(u16)second[0] - (u16)first[0]'),
                         wrong_offset=body.replace('offsets[1]', 'offsets[0]'),
                         reverse_cross=body.replace('func_150AD8B0(edgeA, edgeB, normal)', 'func_150AD8B0(edgeB, edgeA, normal)'),
                         wrong_component=body.replace('normal[1] < 0.0f', 'normal[2] < 0.0f'),
                         reject_zero=body.replace('normal[1] < 0.0f', 'normal[1] <= 0.0f'),
                         reject_nan=body.replace('normal[1] < 0.0f', '!(normal[1] >= 0.0f)'))
        for label, changed in negatives.items():
            self.assertNotEqual(changed, body)
            self.assertEqual(run('negative-'+label, changed), 1, label)
        count = sum(not c.alias and 0 <= c.index < 16 for c in guest.cases())
        self.receipts['native'] = dict(cases_per_executable=count, optimizations=3, semantic_negatives=list(negatives),
                                      SDK_s16_u32_float32_pointer32=True, typed_s32_callback=True, finite_signed_coordinates=True,
                                      trapping_UBSan_and_RN_no_FTZ_DAZ=True, valid_disjoint_backing=True,
                                      private_aliases_and_sparse_indices_guest_only=True)

    def test_06_independent_relocations_and_literal_image_corruptions(self):
        for i, (entry, symbols) in enumerate(((source.ENTRY, dict(D_800D3300=guest.TABLE, func_150AD8B0=guest.CROSS)),
                                               (0x17407F50, dict(D_800D3300=0x81238000, func_150AD8B0=0x17508010)))):
            lines = ['.set noreorder', '.set noat', '.text', '.globl '+source.FUNCTION, source.FUNCTION+':']
            for j, (word,) in enumerate(struct.iter_unpack('>I', self.q['normal'])):
                refs = self.q['normal_refs'].get(j*4, [])
                if not refs:
                    lines.append('.word 0x%08X' % word)
                else:
                    kind, name = refs[0]
                    rt, rs = word>>16&31, word>>21&31
                    lines.append('jal '+name if kind == 'R_MIPS_26' else 'lui $%d, %%hi(%s)' % (rt, name) if kind == 'R_MIPS_HI16' else 'addiu $%d, $%d, %%lo(%s)' % (rt, rs, name))
            p = self.out/('rebase-'+str(i))
            p.with_suffix('.s').write_text('\n'.join(lines)+'\n')
            p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(p.with_suffix('.o')), str(p.with_suffix('.s'))], check=True, capture_output=True)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(p.with_suffix('.ld')), *['--defsym=%s=0x%X' % (n, a) for n, a in symbols.items()], '-o', str(p.with_suffix('.elf')), str(p.with_suffix('.o'))], check=True, capture_output=True)
            self.assertEqual(list(struct.unpack_from('>77I', sections(p.with_suffix('.elf'))['.text'][1])), source.bound_blob(self.q['normal'], self.q['normal_refs'], symbols))
        before, after = self.q['predecessor_elf'].read_bytes(), self.q['qualified_elf'].read_bytes()
        truth = self.rom[source.ROM:source.ROM+308]
        self.assertEqual(source.strict_image(before, after, truth), 210)
        symbol = next(p for p, n, f, s in source.symbol_rows(before) if n == source.FUNCTION)
        for offset in (64, source.elf_slot_offset(before, source.ENTRY, 308), symbol+8, source.elf_slot_offset(before, guest.CROSS, 76)):
            bad = bytearray(after)
            bad[offset] ^= 1
            with self.assertRaises(ValueError):
                source.strict_image(before, bytes(bad), truth)
        self.receipts['image'] = dict(changed_bytes=210, exclusions=0, independent_GNU_links=2,
                                     all_three_relocations=True, signed_LO_carry=True, corruptions_rejected=4,
                                     protected_data_bytes=189088, protected_owners=720, all_6052_addresses_fixed=True)


if __name__ == '__main__':
    unittest.main()
