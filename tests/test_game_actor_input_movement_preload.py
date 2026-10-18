"""Complete movement preload/source screens and bounded private-path qualification."""
# Load this stdlib leaf before the historical recursive experiment imports.
import ctypes
import copy
import hashlib
import itertools
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_input_movement_preload as recovery
from tools.tests import test_game_actor_input_movement_return as prior

source = recovery.source
model = prior.model
backend = recovery.previous.backend


class MovementPreloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / recovery.BUILD
        cls.body = recovery.selected_body()
        cls.obj, cls.words, cls.row = recovery.measure(cls.root, cls.out, recovery.SELECTED_NAME, cls.body)
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>959I', cls.rom, source.ROM))
        cls.connected = {0x150F34A0 + i * 4: w for i, w in enumerate(struct.unpack_from('>21I', cls.rom, 0x120950))}
        cls.harness = prior.previous.MovementRecoveryTests('test_02_all_three_paths_and_numeric_boundaries')
        for name in ('root', 'out', 'rom', 'obj', 'words', 'truth', 'connected'):
            setattr(cls.harness, name, getattr(cls, name))
        cls.harness.coverage = set()
        cls.harness.providers = set()
        cls.work = cls.out / 'traces' / recovery.SELECTED_NAME

    def receipt(self, filename, **data):
        (self.out / (filename + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def test_01_complete_sources_real_links_and_337_word_opening(self):
        self.assertEqual(tuple(self.row[k] for k in ('words', 'frame', 'differences')), (959, 128, 420))
        self.assertEqual(self.row['raw_sha'], recovery.SELECTED_SHA)
        self.assertEqual(self.row['first_unequal_word'], 337)
        self.assertEqual(self.words[:337], self.truth[:337])
        self.assertEqual(self.row['first_unequal_PC'], 0x150F3A38)
        self.assertNotIn('f32 stickX;', self.body)
        self.assertIn('amount = (f32)D_800CC284->x;', self.body)
        before = (self.out / 'before-record_gate_owner').read_text()
        rows = []
        for name, body in recovery.all_forms():
            self.assertEqual((self.out / (name + '.c')).read_text(), source.recovered_owner(before, body), name)
            raw, _ = source.parts(self.out / (name + '.o'))
            row = json.loads((self.out / (name + '-audit.json')).read_text())
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row['raw_sha'])
            words = list(struct.unpack_from('>%dI' % (len(raw) // 4),
                         source.projection.sections(self.out / (name + '-linked.elf'))['.text'][1]))
            self.assertEqual((len(words), (-words[0]) & 65535, sum(x != y for x, y in zip(words, self.truth))),
                             tuple(row[k] for k in ('words', 'frame', 'differences')))
            self.assertEqual((row['raw_neighbors'], row['padded_neighbors']), (11, 11))
            self.assertEqual((row['new_guards'], row['matching_credit'], row['installed']), (0, 0, False))
            self.assertEqual(row['padded_differences'], row['differences'])
            first = next((i for i, (a, b) in enumerate(zip(words, self.truth)) if a != b), None)
            rows.append(dict(name=name, words=row['words'], frame=row['frame'], differences=row['differences'],
                             raw_sha=row['raw_sha'], first_unequal_word=first))
        self.assertEqual(len(rows), 22)
        self.receipt('source-controls', complete_forms=len(rows), rows=rows, no_executable_trimming=True)

    def test_02_actual_assembler_capture_and_existing_live_homes(self):
        record, words, binary = recovery.finish_trace(self.root, self.out)
        self.assertEqual(words, self.words)
        self.assertEqual((record['correlated_events'], len(binary)), (74, 684))
        content = recovery.previous.previous.frame.isolated(self.body)
        layout = recovery.check_layout(record, words, content)
        frame = recovery.previous.previous.frame
        summary = frame.summary(record, content, {'stickSample': 'amount = (f32)D_800CC284->x;'})
        stores = [r for r in summary['phases']['frontend']['markers']['stickSample']
                  if r['name'] == 'str' and r['storage'] == 'M']
        self.assertEqual([(r['offset'], r['dtype'], r['length']) for r in stores], [(-8, 'R', 4)])
        for key, value in (('offset', -12), ('dtype', 'J'), ('length', 2)):
            bad = copy.deepcopy(record)
            next(r for r in bad['records']['frontend'] if r['byte_offset'] == stores[0]['byte_offset'])[key] = value
            with self.assertRaisesRegex(ValueError, 'stick sample'):
                recovery.check_layout(bad, words, content)
        self.assertEqual(record['compiler_as1_sha256'], recovery.BASELINE['movement_return_compiler_as1'])
        self.receipt('backend', normal_and_traced_objects_identical=True, whole_owner_and_isolated_identical=True,
                     emitter_events=74, actual_AS1_instructions=684, existing_layout=layout,
                     stick_sample_existing_amount_home=-8, effective_sample_home_controls=3,
                     compiler_as1_sha=record['compiler_as1_sha256'])

    def test_03_effective_capture_and_assembler_rejections(self):
        log = (self.work / 'debugger.txt').read_text()
        count = 0
        with patch.object(backend.nodes, 'CHILD_EXIT', 'TRACE_EXIT inferior=4 code=0'):
            for name in backend.PROBES:
                for prefix in ('FINALIZER_EMIT_INSTALLED ', 'FINALIZER_EMIT_REMOVED '):
                    with self.assertRaises(ValueError):
                        backend.emitter_events(log.replace(prefix + name, ''))
                    count += 1
                filtered = '\n'.join(line for line in log.splitlines() if not (line.startswith(backend.PREFIX)
                    and json.loads(line.removeprefix(backend.PREFIX))['probe'] == name))
                with self.assertRaises(ValueError):
                    backend.emitter_events(filtered)
                count += 1
            marker = next(line for line in log.splitlines() if line.startswith('FINALIZER_AS1 '))
            event = json.loads(marker.removeprefix('FINALIZER_AS1 '))
            for key, value in (('inferior', 1), ('files', []), ('arguments', ['as1', '-O1'])):
                with self.assertRaises(ValueError):
                    backend.validate_as1(self.work, log.replace(marker, 'FINALIZER_AS1 ' + json.dumps(dict(event, **{key: value}))))
                count += 1
            path = self.work / 'as1-input-11.bin'
            data = path.read_bytes()
            read = Path.read_bytes
            with patch.object(Path, 'read_bytes', lambda p: data + b'\0' if p == path else read(p)):
                with self.assertRaises(ValueError):
                    backend.validate_as1(self.work, log)
            count += 1
            removed = 'FINALIZER_EMIT_REMOVED memory'
            with self.assertRaises(ValueError):
                backend.validate_as1(self.work, log.replace(removed, '') + '\n' + removed)
            count += 1
        summary_path = self.work / 'allocation-summary.json'
        original = json.loads(summary_path.read_text())
        read_text = Path.read_text
        for key, value in (('exit_code', 1), ('code_unchanged', False), ('source_sha', '0' * 64),
                           ('whole_owner_target_identical', False), ('compiler_sha256', {})):
            bad = copy.deepcopy(original)
            bad[key] = value
            with patch.object(Path, 'read_text', lambda p, *a, **k: json.dumps(bad) if p == summary_path else read_text(p, *a, **k)):
                with self.assertRaises(ValueError):
                    recovery.finish_trace(self.root, self.out)
            count += 1
        self.receipt('capture-controls', effective_controls=count, actual_exit_markers_not_synthetic=True)

    test_04_existing_live_home_and_frame_controls = prior.MovementReturnTests.test_04_effective_wire_home_frame_and_emitted_store_controls
    test_05_complete_public_corpus = prior.MovementReturnTests.test_05_complete_public_width_filter_mutation_and_FP_corpus

    def pair_at(self, memory, case, cut):
        pair = [model.Oracle(w, memory, case, self.connected) for w in (self.truth, self.words)]
        fired = []
        for machine in pair:
            machine.access_fault = cut
            try:
                machine.run()
                fired.append(False)
            except model.point.faults.AccessBoundary:
                fired.append(True)
        self.assertEqual(fired[0], fired[1])
        self.assertEqual((pair[0].lo, pair[0].condition), (pair[1].lo, pair[1].condition))
        return pair, fired[0]

    def complete_prefixes(self, specs):
        finished, prefixes = 0, 0
        for spec in specs:
            memory, case = model.fixture(self.rom, **spec)
            for cut in range(96):
                pair, fired = self.pair_at(memory, case, cut)
                self.assertEqual(model.point.state(pair[0]), model.point.state(pair[1]), (spec, cut))
                if not fired:
                    finished += 1
                    break
                prefixes += 1
            else:
                self.fail('Complete private path did not finish in bound')
        return finished, prefixes

    def test_06_extended_active_prefixes_complete_disabled_and_mode_zero_paths(self):
        cuts = (42, 50, 41, 43, 44)
        equal = 0
        for phase, pattern, gate in itertools.product((0, 8), (0, 1), range(5)):
            memory, case = model.fixture(self.rom, phase=phase, pattern=pattern, gate=gate, held=101)
            for cut in range(cuts[gate] + 1):
                pair, fired = self.pair_at(memory, case, cut)
                self.assertTrue(fired)
                same = model.point.state(pair[0]) == model.point.state(pair[1])
                self.assertEqual(same, cut < cuts[gate])
                if same:
                    equal += 1
                else:
                    self.assertEqual(pair[0].memory, pair[1].memory)
                    self.assertEqual([m.current_pc for m in pair], [0x150F3AB8] * 2)
                    self.assertEqual([i for i, (a, b) in enumerate(zip(pair[0].r, pair[1].r)) if a != b], [10, 11, 15, 24])
                    self.assertIn(2, [i for i, (a, b) in enumerate(zip(pair[0].f, pair[1].f)) if a != b])
        self.assertEqual(equal, 880)
        disabled = (dict(phase=p, pattern=b, gate=g, held=h, disabled=1)
                    for p, b, g, h in itertools.product((0, 8), (0, 1), range(5), (0, 100, 101, 124)))
        disabled_states, disabled_prefixes = self.complete_prefixes(disabled)
        mode_zero = (dict(phase=p, pattern=b, gate=g, mode=0, nearby=n, depth=d, pressed=a,
                          position=-101. if a else 100.)
                     for p, b, g, n, d, a in itertools.product((0, 8), (0, 1), range(5),
                                                              (0, 101), (0., 100.00001), (0, 0xC000)))
        zero_states, zero_prefixes = self.complete_prefixes(mode_zero)
        self.assertEqual((disabled_states, disabled_prefixes, zero_states), (80, 2700, 160))
        self.receipt('private', active_states=20, equal_active_prefixes=equal, first_cuts=list(cuts),
                     first_PC='0x150F3AB8', different_GPRs=[10, 11, 15, 24],
                     disabled_complete_states=disabled_states, disabled_fault_prefixes=disabled_prefixes,
                     mode_zero_complete_states=zero_states, mode_zero_fault_prefixes=zero_prefixes,
                     all_LO_condition_compared=True, full_opaque_provider_or_hardware_acceptance_not_claimed=True)

    test_07_native_rebases_unsigned_extremes_and_aliases = prior.MovementReturnTests.test_07_native32_unsigned_extremes_rebases_and_guest_aliases

    def test_08_all_protected_entries_production_and_checkpoint_members(self):
        recovery.freeze(self.root, self.out)
        for key, path in recovery.PATHS.items():
            self.assertEqual((self.root / path).read_bytes(), (self.out / ('before-' + key)).read_bytes())
        self.harness.test_07_production_baseline_and_callback_preserved()
        source.checkpoint.freeze_after(self.root)
        self.receipt('protected', entries=len(recovery.PATHS), paths=len(set(recovery.PATHS.values())),
                     ELF_sha=hashlib.sha256((self.root / 'conker/build/conker.us.elf').read_bytes()).hexdigest(),
                     immutable_first_image_members=10, installed=False, new_guards=0, matching_credit=0)


if __name__ == '__main__':
    unittest.main()
