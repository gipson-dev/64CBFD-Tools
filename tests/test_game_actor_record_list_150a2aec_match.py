"""Direct list lookup, original SDK shift, ordered callbacks and complete image."""
import json
import struct
import subprocess
import unittest
from dataclasses import replace

from tools.experiments import game_actor_record_list_150a2aec_match as source
from tools.tests import game_actor_record_list_150a2aec_oracle as guest
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode, WindowBoundary
from tools.experiments.game_remaining_donor_candidates import sections


def symbols():
    return {name: (guest.SHIFT if name == '__ull_rshift' else int(name.split('_')[1], 16))
            for rows in source.BINDINGS.values() for _, name in rows}


class ActorRecordListTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = source.ROOT
        cls.out = cls.root/source.BUILD
        cls.q = source.prepare(cls.root)
        cls.rom, cls.elf = guest.artifacts(cls.root)
        cls.truth = list(struct.unpack_from('>110I', cls.rom, source.ROM))
        cls.words = source.bound_blob(cls.q['normal'], cls.q['normal_refs'], symbols())
        cls.receipts = {}

    @classmethod
    def tearDownClass(cls):
        (cls.out/'suite-detail.json').write_text(json.dumps(cls.receipts, indent=2)+'\n')

    def test_01_direct_owner_binding_and_metadata_scope(self):
        q = self.q['report']
        self.assertEqual((q['words'], q['frame'], q['guards'], q['raw_neighbors'], q['padded_neighbors']), (110, 64, 0, 27, 27))
        self.assertEqual((q['functions'], q['strict_changed_bytes'], q['exclusions'], q['diagnostics']), (6052, 340, 0, 0))
        self.assertEqual(self.words, self.truth)
        self.assertEqual(self.q['raw'], self.q['normal'])
        self.assertEqual(self.q['refs'], self.q['normal_refs'])
        self.assertEqual(source.guard_rows(self.q['raw'], self.q['refs']), [])
        before = (self.out/'predecessor-guards.csv').read_bytes()
        self.assertEqual(source.guard_manifest(before, self.q['raw'], self.q['refs']), before)
        for offset in source.BINDINGS:
            refs = dict(self.q['refs'])
            refs[offset] = [('R_MIPS_26', 'wrong')]
            with self.assertRaises(ValueError):
                source.normalize(self.q['raw'], refs)
        for offset in (0, 4, 28, 180, 344, 436):
            bad = bytearray(self.q['raw'])
            bad[offset+3] ^= 1
            with self.assertRaises(ValueError):
                source.normalize(bytes(bad), self.q['refs'])
        self.receipts['scope'] = dict(direct_words=110, frame=64, guards=0, bindings=14,
                                     raw_and_padded_neighbors=27, raw_GPR_mask_added='FP/S7 only',
                                     padded_metadata_fixed=True, original_labels_retained=31,
                                     raw_word_corruptions=6, binding_corruptions=14, guard_history_unchanged=True)

    def test_02_original_shift_all_64_counts(self):
        words = list(struct.unpack_from('>11I', self.rom, 0x26800))
        at = source.elf_slot_offset(self.elf, guest.SHIFT, 44)
        self.assertEqual(self.elf[at:at+44], self.rom[0x26800:0x2682C])
        visited = set()
        cases = 0
        for value in (0, 1, 0x8000000000000000, 0xFFFFFFFFFFFFFFFF, 0x0123456789ABCDEF, 0xFEDCBA9876543210):
            for shift in range(64):
                case = guest.Case()
                args = (value >> 32, value&0xFFFFFFFF, 0, shift)
                m = guest.Oracle(words, guest.fixture(case), case, entry=guest.SHIFT, arguments=args)
                registers = m.r[:]
                m.run()
                result = value >> shift
                self.assertEqual((m.r[2], m.r[3]), (result >> 32, result&0xFFFFFFFF))
                self.assertEqual([guest.rd(m.memory, guest.STACK+i*4, 4) for i in range(4)], list(args))
                self.assertEqual(m.r[16:24], registers[16:24])
                self.assertEqual((m.r[29], m.r[30], m.r[31]), (registers[29], registers[30], registers[31]))
                visited.update(m.visits)
                cases += 1
        self.assertEqual(set(range(guest.SHIFT, guest.SHIFT+44, 4))-visited, set())
        bad = list(words)
        bad[6] &= ~(31 << 21)  # Shift by zero instead of the loaded count.
        m = guest.Oracle(bad, guest.fixture(), entry=guest.SHIFT, arguments=(0x12345678, 0x9ABCDEF0, 0, 33))
        self.assertEqual(m.code.get(guest.SHIFT+24), bad[6])
        m.run()
        self.assertNotEqual((m.r[2] << 32) | m.r[3], 0x123456789ABCDEF0 >> 33)
        self.receipts['SDK'] = dict(original_words=11, vectors=cases, shift_counts=64,
                                   high_low_O32_arguments=True, original_home_stores_and_LD64=True,
                                   effective_wrong_shift_control=True, bounded_low_word_root_model=True,
                                   full_hardware_64_bit_state_not_claimed=True)

    def test_03_independent_ordered_model_and_preserved_roles(self):
        visited = set()
        count = 0
        for case in guest.cases():
            initial = guest.fixture(case)
            expected = guest.reference(initial, case)
            machines = []
            for body in (self.truth, self.words):
                m = guest.Oracle(body, initial, case)
                registers, floats = m.r[:], m.f[:]
                m.run()
                self.assertEqual((guest.public(m.memory, case), m.calls, m.r[2]), expected, case)
                self.assertEqual(m.r[16:24], registers[16:24])
                self.assertEqual((m.r[29], m.r[30], m.r[31]), (registers[29], registers[30], registers[31]))
                self.assertEqual(m.f[20:], floats[20:])
                machines.append(m)
            self.assertEqual(guest.state(machines[0]), guest.state(machines[1]))
            visited.update(machines[0].visits)
            count += 1
        missing = sorted(set(range(source.ENTRY, source.ENTRY+440, 4))-visited)
        self.assertEqual(missing, [])
        self.receipts['model'] = dict(cases=count, words_reached=110, signed_count_and_unsigned_limit=True,
                                     all_three_mask_words_and_high_bits=True, low_12_bit_IDs=True,
                                     first_match_and_empty_scan=True, live_count_descriptor_and_ID_mutations=True,
                                     fixed_path_after_enabled_mutation=True, private_count_and_argument_home_aliases=True,
                                     complete_literal_state_equal=True, collision_service_bounded=True)

    def test_04_original_callers_and_real_argument_windows(self):
        jal = 0xC000000 | (source.ENTRY >> 2 & 0x3FFFFFF)
        sites = [p for p in range(0x2D4B0, 0x24D500, 4) if struct.unpack_from('>I', self.rom, p)[0] == jal]
        self.assertEqual(sites, [0xC7658, 0x16F608, 0x173F14])
        pointers = [p for p in range(0, len(self.rom)-3, 4) if source.ENTRY <= struct.unpack_from('>I', self.rom, p)[0] < source.ENTRY+440]
        self.assertEqual(pointers, [])
        checks = 0
        body_code = dict(zip(range(source.ENTRY, source.ENTRY+440, 4), self.words))
        for entry, offset, size, ids in ((0x151420F8, 0x16F5A8, 34, None), (0x15146970, 0x173E20, 74, (0x401D, 0x401E, 0x401F, 0x4020, 0x4021))):
            at = source.elf_slot_offset(self.elf, entry, size*4)
            self.assertEqual(self.elf[at:at+size*4], self.rom[offset:offset+size*4])
            if ids is None:
                at = source.elf_slot_offset(self.elf, 0x800A5200, 24)
                ids = struct.unpack_from('>6I', self.elf, at)
            for enabled, hit in ((0, -1), (0, 0), (8, -1), (8, len(ids)-1)):
                case = guest.Case(ids=ids, count=len(ids), enabled=enabled, hit=hit)
                initial = guest.fixture(case)
                constants = ((0x800A5200, ids),) if entry == 0x151420F8 else ((0x800A56D0, ids), (0x800A56E4, tuple(entry+x for x in (80, 88, 72, 156, 148, 64, 164, 56, 48))))
                for base, values in constants:
                    for i, value in enumerate(values):
                        for j in range(4):
                            initial.setdefault(base+i*4+j, 0)
                        guest.wr(initial, base+i*4, value, 4)
                expected = guest.reference(initial, case)[2]
                args = (guest.actor(case.index),) if entry == 0x151420F8 else (6, guest.actor(case.index))
                m = guest.Oracle(struct.unpack_from('>%dI' % size, self.rom, offset), initial, case, entry=entry, connected=body_code, arguments=args)
                m.run()
                call = next(a for target, a in m.calls if target == source.ENTRY)
                self.assertEqual(call[:2], (case.index, len(ids)))
                self.assertEqual(tuple(guest.rd(m.memory, call[2]+i*4, 4) for i in range(len(ids))), tuple(ids))
                wanted = int(expected != 0xFFFFFFFF) if entry == 0x151420F8 else (0xFFFFFFFF if expected == 0xFFFFFFFF else 6)
                self.assertEqual(m.r[2], wanted)
                self.assertEqual(m.r[29], guest.STACK)
                checks += 1
        window_entry = 0x1509A1A4
        window = struct.unpack_from('>10I', self.rom, 0xC7654)
        for enabled, hit in ((0, -1), (0, 0), (8, 2)):
            case = guest.Case(enabled=enabled, hit=hit)
            initial = guest.fixture(case)
            expected = guest.reference(initial, case)[2]
            m = guest.Oracle(window, initial, case, entry=window_entry, connected=body_code,
                             arguments=(case.index, case.count+2, guest.LIST))
            m.code = WindowCode(m.code, m)
            m.code.ends = (0x1509B484,)
            with self.assertRaises(WindowBoundary):
                m.run()
            self.assertEqual(m.r[2], 0 if expected == 0xFFFFFFFF else expected | 0x4000)
            self.assertEqual(m.calls[0], (source.ENTRY, (case.index, case.count, guest.LIST)))
            checks += 1
        self.receipts['callers'] = dict(direct_calls=3, entry_or_interior_pointers=0, complete_callers=2,
                                      complete_caller_words=108, original_script_window_words=10,
                                      connected_cases=checks, full_script_or_gameplay_not_qualified=True)

    def test_05_executed_access_cut_states(self):
        checks = 0
        for case in (guest.Case(), guest.Case(enabled=0, mutation=15), guest.Case(count=0), guest.Case(alias=2), guest.Case(enabled=0, private_count=1)):
            initial = guest.fixture(case)
            full = guest.Oracle(self.truth, initial, case)
            full.run()
            for cut in range(full.all_accesses):
                states = []
                for body in (self.truth, self.words):
                    m = guest.Oracle(body, initial, case)
                    m.cut = cut
                    with self.assertRaises(AccessBoundary):
                        m.run()
                    states.append(guest.state(m))
                self.assertEqual(states[0], states[1], (case, cut))
                checks += 1
        self.receipts['access_cuts'] = dict(executed_cuts=checks, original_SDK_accesses_included=True,
                                           full_literal_low_word_state=True)

    def test_06_native32_typed_lookup_and_effective_negatives(self):
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
                         byte_count=body.replace('i < count', 'i < (u8)count'),
                         wrong_mask_row=body.replace('[actorIndex][identity >> 6]', '[0][identity >> 6]'),
                         truncated_mask=body.replace('((u64 (*)[3])D_800D30F0)[actorIndex][identity >> 6]', '(u32)((u64 (*)[3])D_800D30F0)[actorIndex][identity >> 6]'),
                         wrong_ID_mask=body.replace('& 0xFFF', '& 0xFFE'),
                         equality_bound=body.replace('identity < (u32)D_800D3094', 'identity <= (u32)D_800D3094'),
                         wrong_collision_truth=body.replace('1) == 0', '1) > 0'),
                         wrong_scan_extent=body.replace('i < count', 'i + 1 < count'))
        for label, changed in negatives.items():
            self.assertNotEqual(changed, body, label)
            self.assertNotEqual(run('negative-'+label, changed), 0, label)
        self.receipts['native'] = dict(cases_per_executable=len(guest.native_cases()), optimizations=3,
                                      typed_s32_s32_pointer_lookup=True, SDK_actor812_descriptor52_pointer32=True,
                                      valid_mask_rows_and_records=True, live_provider_mutations=True,
                                      trapping_UBSan=True, effective_negatives=list(negatives),
                                      arbitrary_addresses_and_private_aliases_guest_only=True)

    def test_07_independent_links_and_complete_image_corruptions(self):
        original = symbols()
        moved = {n: 0x81238000+i*0x10000 for i, n in enumerate(original)}
        moved.update(__ull_rshift=0x17508010, func_150A1DA0=0x17518000)
        for i, (entry, bindings) in enumerate(((source.ENTRY, original), (0x17407F50, moved))):
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
                    elif word>>26 in (35, 37):
                        line = ('lw' if word>>26 == 35 else 'lhu')+' $%d, %%lo(%s)($%d)' % (rt, name, rs)
                    else:
                        line = 'addiu $%d, $%d, %%lo(%s)' % (rt, rs, name)
                    lines.append(line)
            p = self.out/('rebase-'+str(i))
            p.with_suffix('.s').write_text('\n'.join(lines)+'\n')
            p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-no-pad-sections', '-o', str(p.with_suffix('.o')), str(p.with_suffix('.s'))], check=True, capture_output=True)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(p.with_suffix('.ld')), *['--defsym=%s=0x%X' % (n, v) for n, v in bindings.items()], '-o', str(p.with_suffix('.elf')), str(p.with_suffix('.o'))], check=True, capture_output=True)
            self.assertEqual(list(struct.unpack('>110I', sections(p.with_suffix('.elf'))['.text'][1])), source.bound_blob(self.q['normal'], self.q['normal_refs'], bindings))
        before, after = self.q['predecessor_elf'].read_bytes(), self.q['qualified_elf'].read_bytes()
        truth = self.rom[source.ROM:source.ROM+440]
        self.assertEqual(source.strict_image(before, after, truth), 340)
        at = next(p for p, n, f, s in source.symbol_rows(before) if n == source.FUNCTION)
        for offset in (64, source.elf_slot_offset(before, source.ENTRY, 440), at+8, source.elf_slot_offset(before, guest.SHIFT, 44)):
            bad = bytearray(after)
            bad[offset] ^= 1
            with self.assertRaises(ValueError):
                source.strict_image(before, bytes(bad), truth)
        self.receipts['image'] = dict(changed_bytes=340, exclusions=0, independent_GNU_links=2,
                                     all_fourteen_bindings=True, signed_LO_carries=True, corruption_controls=4,
                                     named_definitions_fixed_except_size=True, protected_data_bytes=189088, protected_owners=720)


if __name__ == '__main__':
    unittest.main()
