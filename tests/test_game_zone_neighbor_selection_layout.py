"""Complete zone-pass source, private/fault, GNU, padding and image gates."""

from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.experiments import game_zone_neighbor_selection_layout as layout
from tools.experiments import game_zone_neighbor_selection_integration as integration
from tools.experiments.game_route_projection_layout_normalizer import relocate
from tools.tests import test_game_zone_neighbor_selection_homes as homes_tests


previous, homes = homes_tests.previous, layout.homes


class AccessFault(Exception):
    pass


class LiteralOracle(homes_tests.HomeOracle):
    def __init__(self, *args, **kwargs):
        self.observing = self.provider = True
        self.accesses, self.fault, self.requested = 0, None, None
        super().__init__(*args, **kwargs)
        self.observing = self.provider = False

    def access(self, kind, address, size):
        if self.observing or self.provider:
            return
        self.requested = kind, address, size
        if self.accesses == self.fault:
            raise AccessFault()
        self.accesses += 1

    def get(self, address, size):
        self.access('R', address, size)
        return super().get(address, size)

    def put(self, address, value, size):
        self.access('W', address, size)
        return super().put(address, value, size)

    def record_call(self, target):
        self.observing = True
        try:
            return super().record_call(target)
        finally:
            self.observing = False

    def hook(self, target):
        self.provider = True
        try:
            return super().hook(target)
        finally:
            self.provider = False


def state(model):
    return (model.r, model.f, model.memory, model.stores, model.reads, model.visits,
            model.accesses, model.requested, model.condition, model.calls, model.events,
            model.private_calls, model.alias_writes)


def assemble(root, out, name, text):
    asm = out / (name + '.s')
    asm.write_text((root / 'conker/include/asm_processor_prelude.inc').read_text() + '\n.text\n' + text)
    obj = asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
                    '-I', str(root / 'conker/include'), '-o', str(obj), str(asm)],
                   check=True, capture_output=True)
    return obj


def original_function(text, name):
    opening, closing = 'glabel ' + name + '\n', 'endlabel ' + name
    if text.count(opening) != 1 or text.count(closing) != 1:
        raise ValueError('Unknown original zone-pass function extent')
    return ('.type ' + name + ',@function\n' + opening +
            text.split(opening, 1)[1].split(closing, 1)[0] + closing +
            '\n.size ' + name + ',.-' + name + '\n')


def link_map(out, name, obj, visitor, anchors):
    script = out / (name + '.ld')
    sections = sorted(((0x1508B3F8, '.text', obj.name),
                       (anchors['func_1508B2A8'], '.visitor', visitor.name)))
    script.write_text('SECTIONS { ' + ' '.join(
        '%s 0x%X : SUBALIGN(4) { %s(.text) }' % (section, address, leaf)
        for address, section, leaf in sections) + ' }\n')
    elf = script.with_suffix('.elf')
    result = subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', script.name,
                    '-e', layout.source.FUNCTION, '--no-warn-mismatch',
                    *['--defsym=%s=0x%X' % (key, value) for key, value in anchors.items()
                      if key != 'func_1508B2A8'], '-o', elf.name, obj.name, visitor.name],
                   cwd=out, capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.decode())
    functions = integration.load_elf_functions(str(elf), 'mips-linux-gnu-objdump')[0]
    return functions[layout.source.FUNCTION][:369], functions['func_1508B2A8'][:84]


class ZoneSelectionLayoutTests(unittest.TestCase):
    _previous = previous.GameZoneNeighborSelectionMatchTests
    _homes = homes_tests.ZoneNeighborSelectionHomeTests
    run_host = _homes.run_host
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
        cls.output = cls.root / (layout.BUILD + '/qualification')
        cls.output.mkdir(exist_ok=True)
        cls.values = layout.source.freeze(cls.root, cls.root / integration.BUILD)
        cls.record, cls.baseline = homes.source.compile_candidate(cls.root, cls.output, 'raw', layout.SELECTED)
        cls.raw, cls.bindings = layout.source.payload(cls.output / 'raw.o')
        cls.normalized, cls.moved = layout.normalize(cls.raw, cls.bindings)
        cls.words = relocate(cls.normalized, cls.moved, homes.source.SYMBOLS)
        _, cls.checkpoint = homes.source.compile_candidate(cls.root, cls.output, 'old-homes', homes.SELECTED)
        _, cls.old_layout = homes.source.compile_candidate(cls.root, cls.output, 'old-layout', homes.source.SELECTED)
        rom = cls.values['conker/conker.us.bin']
        cls.retail = list(struct.unpack_from('>369I', rom, 0xB88A8))
        cls.visitor = list(struct.unpack_from('>84I', rom, 0xB8758))
        cls.coverage, cls.visitor_coverage, cls.cases, cls.receipts = set(), set(), 0, {}
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)
        lines = ['.globl ' + layout.source.FUNCTION, '.type ' + layout.source.FUNCTION + ',@function',
                 layout.source.FUNCTION + ':']
        for i, word in enumerate(struct.unpack('>369I', cls.normalized)):
            label = '.Lzone_word_%d' % i
            lines += [label + ':', '.word 0x%08X' % word]
            lines += ['.reloc %s,%s,%s' % (label, kind, symbol)
                      for kind, symbol in cls.moved.get(i * 4, [])]
        lines.append('.size %s,.-%s' % (layout.source.FUNCTION, layout.source.FUNCTION))
        cls.normal_obj = assemble(cls.root, cls.output, 'normalized', '\n'.join(lines) + '\n')

    @classmethod
    def tearDownClass(cls):
        cls.receipts.update(public_four_way_cases=cls.cases, literal_private_pairs=cls.cases,
                            retail_words_visited=len(cls.coverage), visitor_words_visited=len(cls.visitor_coverage))
        (cls.output / 'qualification.json').write_text(json.dumps(cls.receipts, indent=2) + '\n')

    def check_case(self, memory, phase=0, roots=(0, 8), mode=0):
        wanted, calls, writes = previous.reference(memory, roots, mode)
        models = [LiteralOracle(words, memory, self.visitor, phase, roots, mode).run()
                  for words in (self.retail, self.words, self.baseline, self.checkpoint)]
        for model in models:
            self.assertEqual(model.calls, calls)
            self.assertEqual(previous.external_writes(model), writes)
            self.assertEqual(previous.external_memory(model.memory), previous.external_memory(wanted))
        self.assertEqual(state(models[0]), state(models[1]))
        type(self).coverage.update(models[0].visits & set(range(previous.ENTRY, previous.ENTRY + 369 * 4, 4)))
        type(self).visitor_coverage.update(models[0].visits & set(range(previous.VISITOR, previous.VISITOR + 84 * 4, 4)))
        type(self).cases += 1
        return models[0]

    def test_01_closed_origins_typed_public_accesses_and_stale_controls(self):
        self.assertEqual((self.record['body_words'], self.record['frame'], self.record['real_differences']), (367, 320, 340))
        self.assertEqual(self.record['diagnostics'], '')
        self.assertEqual(self.words, self.retail)
        order = layout.origins()
        kept = [item for item in order if isinstance(item, int)]
        self.assertEqual((len(kept), len(order) - len(kept), len(layout.REMOVED)), (364, 5, 3))
        memory_ops = {32, 33, 35, 36, 37, 40, 41, 43, 49, 57}
        raw = struct.unpack('>367I', self.raw)
        for at in layout.REMOVED:
            self.assertNotIn(raw[at // 4] >> 26, memory_ops)
        public = 0
        for i, item in enumerate(order):
            if isinstance(item, int) and raw[item // 4] >> 26 in memory_ops and raw[item // 4] >> 21 & 31 != 29:
                self.assertEqual(self.words[i] >> 26, raw[item // 4] >> 26)
                public += 1
        self.assertEqual(public, 58)
        for i in range(0, 1468, 4):
            bad = bytearray(self.raw)
            bad[i] ^= 1
            with self.assertRaises(ValueError):
                layout.normalize(bytes(bad), self.bindings)
        for i in self.bindings:
            bad = deepcopy(self.bindings)
            bad[i] = [('R_MIPS_26', layout.source.FUNCTION)]
            with self.assertRaises(ValueError):
                layout.normalize(self.raw, bad)
        wrong = order.copy()
        wrong[0], wrong[1] = wrong[1], wrong[0]
        with patch.object(layout, 'origins', return_value=wrong):
            with self.assertRaises(ValueError):
                layout.normalize(self.raw, self.bindings)
        with patch.object(layout, 'REGISTERS', {}):
            with self.assertRaises(ValueError):
                layout.normalize(self.raw, self.bindings)
        self.receipts.update(words=369, frame=320, retained_origins=364, derived_forms=5, omissions=3,
                            output_bindings=32, retained_public_memory_instructions=58,
                            raw_binding_stale_controls=397, recipe_negative_controls=2)

    def test_10_native32_source_and_effective_semantic_negatives(self):
        with patch.object(homes, 'SELECTED', layout.SELECTED):
            self._homes.test_10_native32_public_memory_and_calls(self)
        with patch.object(homes.source, 'SELECTED', layout.SELECTED):
            self._previous.test_root_reuse_and_clear_queue_negative_controls_fail(self)
        self.receipts['effective_semantic_negatives'] = 3

    def test_11_all_requested_instruction_access_cuts_fire(self):
        cases = [(previous.case_memory(count=0, zones=0), (-1,), 0),
                 (previous.wide_memory(1), (0,), 0),
                 (previous.wide_memory(1), (0,), 3)]
        for memory, _, _ in cases[1:]:
            previous.put(memory, previous.COUNT, 1, 1)
            previous.put(memory, previous.STATE + 0x1745, 1, 1)
        cuts = 0
        for memory, roots, mode in cases:
            for phase in (0, 8):
                complete = LiteralOracle(self.retail, memory, self.visitor, phase, roots, mode).run()
                for cut in range(complete.accesses):
                    pair = []
                    for words in (self.retail, self.words):
                        model = LiteralOracle(words, memory, self.visitor, phase, roots, mode)
                        model.fault = cut
                        with self.assertRaises(AccessFault):
                            model.run()
                        self.assertEqual(model.accesses, cut)
                        pair.append(model)
                    self.assertEqual(state(pair[0]), state(pair[1]))
                    cuts += 1
        self.receipts.update(fired_instruction_access_cut_pairs=cuts, every_requested_cut_fired=True,
                            observer_and_opaque_provider_accesses_excluded_from_fault_gates=True)

    def test_12_effective_alias_negatives_and_closed_store_order(self):
        with patch.object(homes_tests, 'HomeOracle', LiteralOracle):
            saved = self.baseline
            self.baseline = self.old_layout
            try:
                self._homes.test_11_real_query_pointers_and_effective_guest_home_aliases(self)
            finally:
                self.baseline = saved
        for phase in (0, 8):
            for cut in (16, 17, 18, 25):
                pair = []
                for words in (self.retail, self.words):
                    model = LiteralOracle(words, previous.case_memory(), self.visitor, phase)
                    model.fault = cut
                    with self.assertRaises(AccessFault):
                        model.run()
                    pair.append(model)
                self.assertEqual(state(pair[0]), state(pair[1]))
        self.receipts['earlier_store_order_boundary_closed'] = True

    def test_13_independent_original_assembly_and_GNU_maps(self):
        original = self.values['conker/asm/B3020.s'].decode()
        parent = assemble(self.root, self.output, 'original', original_function(original, layout.source.FUNCTION))
        visitor = assemble(self.root, self.output, 'original-visitor', original_function(original, 'func_1508B2A8'))
        self.assertEqual(layout.source.payload(parent), (self.normalized, self.moved))
        base = homes.source.SYMBOLS
        fields = dict(GLOBAL='D_800D23B0', COUNT='D_8008FD8C', START='D_8008FD90', ACTORS='D_800CC2D0',
                      NODES='D_800D2350', MINIMUM='D_8009DA5C', HEIGHT='func_15085DA8',
                      ROOT='func_15085DF8', ZERO='bzero', VISITOR='func_1508B2A8')
        runs = 0
        for n in range(3):
            anchors = dict(base)
            if n:
                for i, symbol in enumerate(('D_800D23B0', 'D_8008FD8C', 'D_8008FD90',
                                            'D_800CC2D0', 'D_800D2350', 'D_8009DA5C')):
                    anchors[symbol] = 0x71000000 + n * 0x1000000 + i * 0x100000 + (0x7FFC if n == 1 else 0x8000)
                for i, symbol in enumerate(('func_15085DA8', 'func_15085DF8', 'func_1508B2A8', 'bzero')):
                    anchors[symbol] = 0x16000000 + n * 0x100000 + i * 0x10000
            images = [link_map(self.output, '%s-map-%d' % (name, n), obj, visitor, anchors)
                      for name, obj in (('original', parent), ('normalized', self.normal_obj), ('raw', self.output / 'raw.o'))]
            self.assertEqual(images[0], images[1])
            with patch.multiple(previous, **{key: anchors[value] for key, value in fields.items()}), \
                    patch.dict(previous.visit_reference.__globals__,
                               GLOBAL=anchors['D_800D2350'], ENTRY=anchors['func_1508B2A8']):
                for memory, roots in ((previous.wide_memory(4), (0,)),
                                       (previous.case_memory(), (-1,)), (previous.case_memory(), (255,))):
                    expected, calls, writes = previous.reference(memory, roots)
                    models = [LiteralOracle(words, memory, child, roots=roots).run() for words, child in images]
                    self.assertEqual(state(models[0]), state(models[1]))
                    for model in models:
                        self.assertEqual(model.calls, calls)
                        self.assertEqual(previous.external_writes(model), writes)
                        self.assertEqual(previous.external_memory(model.memory), previous.external_memory(expected))
                        runs += 1
        self.receipts.update(independent_GNU_maps=3, completed_rebased_runs=runs,
                            independently_assembled_parent_and_visitor=True)

    def test_14_actual_Make_padding_image_negatives_and_live_scope(self):
        out = self.root / integration.BUILD
        self.assertTrue(json.loads((out / 'make-shadow.json').read_text())['padded_code_and_metadata_equal'])
        self.assertTrue(json.loads((out / 'first-link.json').read_text())['exact_prediction'])
        before = self.values['conker/retail_word_patches.us.csv']
        guards = integration.guard_bytes(before, out)
        self.assertTrue(guards.startswith(before))
        rows = list(csv.DictReader(io.StringIO(guards[len(before):].decode()),
                                   fieldnames=next(csv.reader(io.StringIO(before.decode())))))
        self.assertEqual((len(rows), sum(r['omit'] == 'true' for r in rows),
                          sum(bool(r['insert_after']) for r in rows)), (367, 3, 5))
        reader = csv.DictReader(io.StringIO(guards.decode()))
        fieldnames, full = reader.fieldnames, list(reader)
        at = next(i for i, row in enumerate(full) if row['filename'] == layout.source.OWNER
                  and row['function'] == layout.source.FUNCTION)
        for field, value in (('expected', '0x00000000'),
                             ('expected_relocations', 'R_MIPS_26:' + layout.source.FUNCTION)):
            bad = deepcopy(full)
            bad[at][field] = value
            stream = io.StringIO(newline='')
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(bad)
            path = self.output / ('negative-' + field + '.csv')
            path.write_text(stream.getvalue())
            with self.assertRaises(ValueError):
                layout.source.padded(self.root, out, path)
        old = self.values['conker/build/conker.us.elf']
        truth = self.values['conker/conker.us.bin'][layout.source.ROM:layout.source.ROM + 1476]
        expected = integration.predicted_image(old, truth)
        slot = layout.source.elf_slot_offset(old, layout.source.ENTRY, 1476)
        for at in (0, slot, slot + 1475, len(expected) - 1):
            bad = bytearray(expected)
            bad[at] ^= 1
            with self.assertRaises(ValueError):
                integration.check_image(old, bytes(bad), truth)
        if (self.root / layout.source.SOURCE).read_bytes() == self.values[layout.source.SOURCE]:
            layout.source.check_inputs(self.root, out)
        else:
            integration.audit(self.root, out)
        self.receipts.update(expected_word_rows=367, omissions=3, insertion_rows=5,
                            prior_guard_bytes_exact_prefix=True, actual_padder_stale_controls=2,
                            full_image_negative_controls=4)


if __name__ == '__main__':
    unittest.main()
