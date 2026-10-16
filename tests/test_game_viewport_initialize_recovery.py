"""Full semantic recovery; raw FPR/private matching remains an explicit open gate."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_viewport_initialize as source
from tools.tests import game_viewport_initialize_oracle as model
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as tracking
from tools.pad_generated_object import parse_object
from tools.tests.test_game_record_constructor_match import elf_slot_offset


class ViewportInitializeRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]; cls.out = cls.root / source.BUILD
        cls.obj, cls.raw, cls.row = source.measure(cls.root, cls.out, 'qualified-recovery', source.SELECTED)
        source.checked_candidate(cls.obj)
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>373I', cls.rom, source.ROM))
        cls.helpers = {0x1501AE94 + i * 4:w for i, w in enumerate(struct.unpack_from('>44I', cls.rom, 0x48344))}
        cls.helpers.update({0x1501AF44 + i * 4:w for i, w in enumerate(struct.unpack_from('>87I', cls.rom, 0x483F4))})

    def receipt(self, name, **row):
        (self.out / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')

    def test_01_complete373_frame_homes_and_exact_first94_words(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences']), (373, 72, 49))
        self.assertEqual(self.row['diagnostics'], ''); self.assertFalse(self.row['pools'])
        self.assertEqual(self.raw[:94], self.truth[:94]); self.assertNotEqual(self.raw, self.truth)
        before = (self.out / 'before-elf').read_bytes()
        at = elf_slot_offset(before, 0x1501AE94, 524)
        self.assertEqual(before[at:at + 524], self.rom[0x48344:0x48550])
        changed = [i for i, (a, b) in enumerate(zip(self.raw, self.truth)) if a != b]
        self.assertEqual(len(changed), 49)
        for i in changed:
            a, b = self.raw[i], self.truth[i]
            if i == 349: self.assertEqual((a, b), (0x01B01821, 0x020D1821))
            else:
                self.assertIn(a >> 26, (17, 49, 57))
                mask = (~((31 << 16) | (31 << 11) | (31 << 6)) if a >> 26 == 17 else ~(31 << 16)) & 0xFFFFFFFF
                self.assertEqual(a & mask, b & mask)
        self.receipt('emission', words=373, frame=72, exact_opening_words=94, real_word_differences=49,
            FPR_field_only_words=48, commutative_address_word=1, no_guards_or_installation=True)

    def test_02_independent_reference_complete_guest_and_conversion_prefixes(self):
        cases = invalid = 0; seen = set()
        fixtures = itertools.chain(model.corpus(), (model.fixture(layout=1, pattern=p) for p in (1, 2, 3)),
            (model.fixture(depth=p) for p in (0xFFFF, 0x10000)))
        for memory, args in fixtures:
            expected, calls, complete = model.reference(memory, args)
            for phase in (0, 8):
                machines = []
                for words in (self.truth, self.raw):
                    m = model.InitializeOracle(words, memory, args, self.helpers, phase)
                    if complete: m.run()
                    else:
                        with self.assertRaises(model.ConversionBoundary): m.run()
                    self.assertTrue(model.public(m.memory) == model.public(expected), (args, phase))
                    self.assertEqual(m.calls, calls); seen.update(m.visits); machines.append(m)
                self.assertEqual(machines[0].memory, machines[1].memory)
                self.assertEqual(machines[0].events, machines[1].events)
                cases += 1; invalid += not complete
        wanted = set(range(source.ENTRY, source.ENTRY + 1492, 4))
        self.assertEqual(seen & wanted, wanted)
        self.receipt('guest', paired_cases=cases, conversion_prefix_cases=invalid, all373_words_visited=True,
            real_bounds_and_clamp_words=131, other_helper_contracts_not_full_chain=True,
            full_memory_ordered_access_and_packets=True, raw_private_FPR_match_not_claimed=True)

    def test_03_callback_live_base_page_fov_and_cached_angle_contracts(self):
        cases = 0
        for index in (0, 1, 3):
            for layout in (0, 1, 3):
                for transfer in (0, 1):
                    for mode in range(6):
                        for phase in (0, 8):
                            memory, args = model.fixture(index, layout, transfer=transfer)
                            expected, calls, complete = model.reference(memory, args, 2, mode)
                            self.assertTrue(complete); machines = []
                            for words in (self.truth, self.raw):
                                m = model.InitializeOracle(words, memory, args, self.helpers, phase, 2, mode).run()
                                self.assertTrue(model.public(m.memory) == model.public(expected), (index, layout, transfer, mode))
                                self.assertEqual(len(m.fired), int(mode in (1, 2, 3, 4) or mode == 5 and bool(transfer)))
                                self.assertEqual(m.calls, calls); machines.append(m)
                            self.assertEqual(machines[0].memory, machines[1].memory)
                            self.assertEqual(machines[0].events, machines[1].events); cases += 1
        self.receipt('callbacks', paired_cases=cases, bounded_provider_mutations=True,
            live_base_page_FOV_and_cached_pending_angle=True, real_projection_FOV_trig_chain_still_open=True)

    def test_04_actual_original_and_ten_unchanged_owner_neighbors(self):
        original = assembly.ViewListSetupTests.original.__func__(type(self), 'original-viewport',
            (self.out / 'before-viewport_original').read_text(), source.FUNCTION)
        data, functions = source.build.link_owner(self.root, self.out, original, source.OWNER)
        f = functions[source.FUNCTION]
        self.assertEqual(f['size'], 1492)
        self.assertEqual(data[f['value']:f['value'] + 1492], self.rom[source.ROM:source.ROM + 1492])
        before, diag = source.build.compile_owner(self.root, self.out, (self.out / 'before-frustum_owner').read_text(), 'neighbor-before')
        self.assertEqual(diag, ''); a, b = parse_object(before), parse_object(self.obj)
        self.assertEqual(set(a[1]), set(b[1]))
        rel = lambda p, f:{at - f['value']:r for at, r in p[2].items() if f['value'] <= at < f['value'] + f['size']}
        count = 0
        for name, f in a[1].items():
            if name == source.FUNCTION: continue
            g = b[1][name]
            self.assertEqual(a[0][f['value']:f['value'] + f['size']], b[0][g['value']:g['value'] + g['size']], name)
            self.assertEqual(rel(a, f), rel(b, g), name); count += 1
        self.assertEqual(count, 10)
        self.receipt('neighbors', original_GNU_words=373, unchanged_normal_neighbors=10,
            production_image_source_and_guards_untouched=True)

    def test_05_first_literal_private_FPR_boundary_is_not_hidden(self):
        join = source.ENTRY + 0x17C
        class Join(Exception): pass
        class Code(tracking.TrackedCode):
            def __getitem__(self, pc):
                if pc == join: raise Join
                return super().__getitem__(pc)
        memory, args = model.fixture(); machines = []
        for words in (self.truth, self.raw):
            m = model.InitializeOracle(words, memory, args, self.helpers); m.code = Code(m.code, m)
            with self.assertRaises(Join): m.run()
            machines.append(m)
        a, b = machines
        self.assertEqual(a.memory, b.memory); self.assertEqual(a.r, b.r)
        self.assertEqual(a.events, b.events); self.assertNotEqual(a.f, b.f)
        self.assertEqual(a.f[16], model.bits(0.5)); self.assertEqual(b.f[14], model.bits(0.5))
        self.receipt('private-boundary', first_different_instruction='0x1501AA38', cut_before='0x1501AA3C',
            retail_constant_FPR=16, raw_constant_FPR=14, memory_GPR_and_access_prefix_equal=True,
            literal_FPR_prefix_not_equal=True, not_installable_as_byte_exact=True)

    def test_06_all_words_bindings_pools_and_immutable_live_baseline(self):
        text, functions, relocations = parse_object(self.obj); f = functions[source.FUNCTION]
        for i in range(373):
            bad = bytearray(text); bad[f['value'] + i * 4] ^= 1
            with patch.object(source, 'parse_object', return_value=(bytes(bad), functions, relocations)):
                with self.assertRaises(ValueError): source.checked_candidate(self.obj)
        for at in (*source.RELOCATIONS, 0):
            bad = dict(relocations); bad[f['value'] + at] = [('R_MIPS_26', 'wrong')]
            with patch.object(source, 'parse_object', return_value=(text, functions, bad)):
                with self.assertRaises(ValueError): source.checked_candidate(self.obj)
        with patch.object(source, 'sections', return_value={'.rodata':(0, b'bad')}):
            with self.assertRaises(ValueError): source.checked_candidate(self.obj)
        with self.assertRaises(ValueError): source.recovered_owner(source.recovered_owner((self.out / 'before-frustum_owner').read_text()))
        self.assertEqual(len(source.PATHS), 130)
        for key, path in source.PATHS.items():
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), source.BASELINE[key], key)
        self.receipt('fail-closed', word_corruptions=373, bindings=len(source.RELOCATIONS), extra_binding=1, private_pool=1,
            all130_live_inputs_unchanged=True, zero_production_matching_credit=True)

    def test_07_effective_compiled_semantic_controls(self):
        body = source.SELECTED
        cached = body.replace('VIEW_PROJECTIONS_476D0', 'cachedViews').replace('    s16 *origin;',
            '    ViewProjection476D0 *cachedViews = VIEW_PROJECTIONS_476D0;\n    s16 *origin;', 1)
        negative_origin = model.fixture(1, 2)
        model.put(negative_origin[0], model.ORIGINS + 44, 0x8000, 2)
        specs = (
            ('full-word-flag', body.replace('s16 transferFov', 's32 transferFov'), model.fixture(transfer=0x10000), 0),
            ('narrow-depth-first', body.replace(' = depth >> 1;', ' = (s16)depth >> 1;'), model.fixture(depth=0xFFFF), 0),
            ('page-xor', body.replace('viewport[!D_800BE9C0]', 'viewport[D_800BE9C0 ^ 1]'), model.fixture(page=255), 0),
            ('wrong-origin-stride', body.replace('layout * 20 + index * 4', 'layout * 20 + index * 8'), model.fixture(1, 2), 0),
            ('unsigned-origin', body.replace('(f32)origin[0]', '(f32)(u16)origin[0]'), negative_origin, 0),
            ('cached-base', cached, model.fixture(), 1))
        mismatches = {}
        for name, candidate, (memory, args), mode in specs:
            self.assertNotEqual(candidate, body)
            words = source.measure(self.root, self.out, 'negative-' + name, candidate)[1]
            expected, calls, complete = model.reference(memory, args, mode=mode)
            self.assertTrue(complete)
            if len(words) > 373:
                with self.assertRaisesRegex(ValueError, 'overlaps'):
                    model.InitializeOracle(words, memory, args, self.helpers, mode=mode)
            m = model.InitializeOracle(words, memory, args, self.helpers, mode=mode, entry=0x15200000).run()
            different = model.public(m.memory) != model.public(expected) or m.calls != calls
            self.assertTrue(different, name); mismatches[name] = True
        self.receipt('semantic-controls', effective_compiled_controls=mismatches,
            negative_root_relocated_away_from_helpers=True, overlap_guard_exercised=True,
            no_compile_failure_unmapped_access_or_sanitizer_signal_counted=True)


if __name__ == '__main__': unittest.main()
