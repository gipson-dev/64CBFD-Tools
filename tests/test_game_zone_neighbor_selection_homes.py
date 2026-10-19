"""Qualify real query/scalar homes without claiming a complete private match."""

import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_zone_neighbor_selection_homes as homes
from tools.experiments import game_zone_neighbor_selection_home_integration as integration
from tools.tests import test_game_zone_neighbor_selection_match as previous
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


class HomeOracle(previous.ZoneOracle):
    def __init__(self, *args, alias=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.alias, self.private_calls, self.alias_writes = alias, [], []

    def record_call(self, target):
        if target in (previous.ZERO, previous.VISITOR):
            self.private_calls.append((target, self.r[4] if target == previous.ZERO else self.r[5]))
        super().record_call(target)

    def hook(self, target):
        super().hook(target)
        if target == previous.ROOT and self.lookup == 1 and self.alias:
            home, value = self.alias
            address = self.r[29] + home
            self.alias_writes.append((address, value))
            self.put(address, value, 4)


class StoreFault(Exception):
    pass


class StoreCutOracle(previous.ZoneOracle):
    cut = None

    def put(self, address, value, size):
        if self.cut is not None:
            self.requested = (address, size)
            if self.cut == 0:
                raise StoreFault()
            self.cut -= 1
        return super().put(address, value, size)


class ZoneNeighborSelectionHomeTests(unittest.TestCase):
    _previous = previous.GameZoneNeighborSelectionMatchTests
    check_case = _previous.check_case
    test_02_connected_smoke_and_root_failure = _previous.test_bounded_connected_smoke_and_root_failure
    test_03_signed_queue_and_player_bounds = _previous.test_signed_queue_and_player_bounds
    test_04_height_radial_and_unordered_gates = _previous.test_height_radial_unordered_and_selection_boundaries
    test_05_live_lookup_mutations = _previous.test_lookup_mutations_of_future_work_and_publication
    test_06_all_candidate_counts_and_full_word_coverage = _previous.test_every_candidate_count_remainder_and_four_way_scan
    test_07_replaced_globals_keep_captured_cursors = _previous.test_mutated_global_bases_keep_original_selection_and_zone_cursors
    test_08_strict_comparisons_and_first_tie = _previous.test_strict_equal_candidate_distance_and_first_tie_winner
    test_09_minimum_unordered_and_signed_bounds = _previous.test_minimum_unordered_and_signed_floating_bounds

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.output = cls.root / (homes.BUILD + '/qualification')
        cls.output.mkdir(exist_ok=True)
        cls.values = integration.freeze(cls.root, cls.root / integration.BUILD)
        cls.record, cls.words = homes.source.compile_candidate(cls.root, cls.output, 'named-homes', homes.SELECTED)
        _, cls.baseline = homes.source.compile_candidate(cls.root, cls.output, 'previous', homes.source.SELECTED)
        _, cls.checkpoint = homes.source.compile_candidate(cls.root, cls.output, 'indexed', homes.source.BASELINE)
        rom = cls.values['conker/conker.us.bin']
        cls.retail = list(struct.unpack_from('>369I', rom, 0xB88A8))
        cls.visitor = list(struct.unpack_from('>84I', rom, 0xB8758))
        cls.coverage, cls.visitor_coverage, cls.cases, cls.receipts = set(), set(), 0, {}
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)

    @classmethod
    def tearDownClass(cls):
        cls.receipts.update(public_four_way_cases=cls.cases,
                            retail_words_visited=len(cls.coverage),
                            visitor_words_visited=len(cls.visitor_coverage))
        (cls.output / 'qualification.json').write_text(json.dumps(cls.receipts, indent=2) + '\n')

    def test_01_closed_declarations_real_homes_and_exact_opcode_history(self):
        before, after = homes.source.SELECTED, homes.SELECTED
        self.assertEqual(before.split('\n\n', 1)[1], after.split('\n\n', 1)[1])
        self.assertEqual(sorted(homes.names(before)), sorted(homes.names(after)))
        self.assertEqual(len(list(homes.candidates())), 32)
        for invalid in (homes.names(before)[:-1], ['query'] * len(homes.names(before))):
            with self.assertRaises(ValueError):
                homes.declarations(before, invalid)
        with self.assertRaises(ValueError):
            homes.declarations('void missing(void) {}\n\n', [])
        self.assertEqual((self.record['body_words'], self.record['frame'],
                          self.record['real_differences'], self.record['diagnostics']), (369, 320, 277, ''))
        changes = []
        for i, (a, b) in enumerate(zip(self.baseline, self.words)):
            if a != b:
                self.assertEqual(a >> 16, b >> 16)
                self.assertEqual(a >> 21 & 31, 29)
                changes.append((i, a & 65535, b & 65535))
        self.assertTrue(changes)
        locations = homes.locations(self.words)
        self.assertEqual(locations['query_x_stores'], [0xAC])
        self.assertEqual(locations['query_count_stores'], [0xD8, 0xD8])
        self.assertEqual(locations['zero_word_homes'], [0x13C] * 3)
        self.assertEqual(locations['opening_pointer_homes'], [0x124, 0x94, 0x13C])
        self.receipts.update(words=369, frame=320, raw_differences=277,
                            stack_immediate_only_changes=changes, no_new_storage=True,
                            query_home=0xAC, selections_home=0x124, zone_home=0x94,
                            counter_home=0x13C, matching_credit=0)

    def run_host(self, body):
        fixture = self.fixture
        self.assertEqual(fixture.count(homes.source.SELECTED), 1)
        fixture = fixture.replace(homes.source.SELECTED, homes.SELECTED)
        source = self.path / 'native-homes.c'
        source.write_text(fixture + 'int run(void) {\n' + body + '\nreturn 0;\n}\n' + START)
        profiles = []
        for name in ('O0', 'O2', 'O3'):
            binary = self.path / ('native-' + name)
            command = native_command('-' + name) + ['-mstackrealign', '-fno-strict-aliasing',
                       '-Wno-unused-function', str(source), '-o', str(binary)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            profiles.append(name)
        control = self.path / 'ubsan-control.c'
        control.write_text('typedef int s32; int run(void) {'
                           'volatile s32 limit=2147483647; return limit+1;}\n' + START)
        executable = control.with_suffix('')
        result = subprocess.run(native_command('-O2') + [str(control), '-o', str(executable)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([str(executable)], capture_output=True, timeout=10)
        self.assertEqual(result.returncode, -4)
        self.receipts.update(native_fixtures=1424, native_profiles=profiles, UBSan=True,
                             fired_sanitizer_overflow_control=result.returncode)

    def test_10_native32_public_memory_and_calls(self):
        original = self.root
        shadow = self.path / 'native-source-root'
        owner = shadow / integration.SOURCE
        owner.parent.mkdir(parents=True)
        owner.write_bytes(self.values[integration.SOURCE])
        try:
            self.root = shadow
            self._previous.test_native_1424_complete_public_memory_footprints(self)
        finally:
            self.root = original

    def test_11_real_query_pointers_and_effective_guest_home_aliases(self):
        scenarios = (('query-threshold', 0xB4, previous.bits(1000.0)),
                     ('counter', 0x13C, 3),
                     ('zone-cursor', 0x94, previous.STATE + 0x1748 + 5 * 12),
                     ('selections', 0x124, previous.ALT_STATE + 0x55C))
        runs, negative = 0, []
        for (name, home, value), phase in itertools.product(scenarios, (0, 8)):
            memory = previous.wide_memory(8)
            memory.update({previous.ALT_STATE + i: memory[previous.STATE + i]
                           for i in range(0x1900)})
            previous.put(memory, previous.STATE + 0x1748 + 6 * 12, previous.bits(float('nan')))
            models = [HomeOracle(words, memory, self.visitor, phase, (0,), alias=(home, value)).run()
                      for words in (self.retail, self.words)]
            a, b = models
            self.assertEqual(a.alias_writes, b.alias_writes)
            self.assertEqual(len(a.alias_writes), 1)
            self.assertEqual((a.calls, previous.external_writes(a), previous.external_memory(a.memory)),
                             (b.calls, previous.external_writes(b), previous.external_memory(b.memory)))
            self.assertEqual(a.private_calls, b.private_calls)
            self.assertTrue(a.private_calls)
            expected = previous.STACK + phase - 320 + 0xAC
            self.assertTrue(all(address == expected + (0x36 if target == previous.ZERO else 0)
                                for target, address in a.private_calls))
            bad = HomeOracle(self.baseline, memory, self.visitor, phase, (0,), alias=(home, value)).run()
            self.assertNotEqual((bad.calls, previous.external_memory(bad.memory)),
                                (a.calls, previous.external_memory(a.memory)), name)
            runs += 2
            negative.append((name, phase))
        self.receipts.update(completed_guest_alias_runs=runs, effective_old_home_alias_negatives=negative,
                             guest_aliases_excluded_from_portable_C=True)

    def test_12_fired_store_prefix_keeps_remaining_private_boundary_explicit(self):
        witnesses = []
        for phase in (0, 8):
            outputs = []
            for words in (self.retail, self.words):
                model = StoreCutOracle(words, previous.case_memory(), self.visitor, phase)
                model.cut = 17
                with self.assertRaises(StoreFault):
                    model.run()
                outputs.append(model.requested)
            self.assertNotEqual(*outputs)
            witnesses.append((phase, outputs))
        self.receipts.update(fired_private_store_boundary_witnesses=witnesses,
                             complete_literal_private_match=False)

    def test_13_actual_owner_and_guard_history(self):
        root = self.root
        out = root / integration.BUILD
        record = json.loads((out / 'qualification.json').read_text())
        self.assertEqual(record['raw_differences'], 277)
        self.assertTrue(record['all73_addresses_and_extents_fixed'])
        self.assertEqual(record['preserved_padded_neighbors'], 72)
        self.assertEqual((out / 'unchanged-guards.csv').read_bytes(),
                         self.values['conker/retail_word_patches.us.csv'])
        integration.check_inputs(root, out)
        self.receipts.update(installed=False, production_inputs_audited=len(self.values))

    def test_14_effective_complete_body_semantic_negatives(self):
        with patch.object(homes.source, 'SELECTED', homes.SELECTED):
            self._previous.test_root_reuse_and_clear_queue_negative_controls_fail(self)
        self.receipts['effective_semantic_negatives'] = 3


if __name__ == '__main__':
    unittest.main()
