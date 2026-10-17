"""Complete return/button recovery, real assembler provenance and remaining FP gap."""
# Load this stdlib leaf outside the historical recursive experiment imports.
import ctypes
import copy
import hashlib
import itertools
import json
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_input_movement_return as recovery
from tools.tests import test_game_actor_input_movement_recovery as previous
from tools.tests import game_actor_input_movement_oracle as model
from tools.tests import game_actor_input_movement_native as native

source = recovery.source


class MovementReturnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / recovery.BUILD
        cls.body = recovery.selected_body()
        cls.obj, cls.words, cls.row = recovery.measure(cls.root, cls.out, recovery.SELECTED_NAME, cls.body)
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>959I', cls.rom, source.ROM))
        cls.connected = {0x150F34A0 + i * 4: w for i, w in enumerate(struct.unpack_from('>21I', cls.rom, 0x120950))}
        cls.harness = previous.MovementRecoveryTests('test_02_all_three_paths_and_numeric_boundaries')
        for name in ('root', 'out', 'rom', 'obj', 'words', 'truth', 'connected'):
            setattr(cls.harness, name, getattr(cls, name))
        cls.harness.coverage = set()
        cls.harness.providers = set()
        cls.work = cls.out / 'traces' / recovery.SELECTED_NAME

    def receipt(self, filename, **data):
        (self.out / (filename + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def test_01_complete_slot_original_return_tail_and_source_controls(self):
        self.assertEqual(tuple(self.row[k] for k in ('words', 'frame', 'differences')), (959, 128, 475))
        self.assertEqual(self.row['raw_sha'], recovery.SELECTED_SHA)
        self.assertEqual(self.row['first_unequal_word'], 137)
        self.assertEqual(self.words[:137], self.truth[:137])
        self.assertEqual(self.words[106:111], self.truth[106:111])
        self.assertEqual((self.row['raw_neighbors'], self.row['padded_neighbors']), (11, 11))
        self.assertEqual((self.row['new_guards'], self.row['matching_credit'], self.row['padded_differences']), (0, 0, 475))
        self.assertIn('u32 buttons;', self.body)
        self.assertIn('goto disabled_done;', self.body)
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
            self.assertEqual(row['raw_neighbors'], 11)
            if row['words'] > 959:
                self.assertTrue(row['padder_rejected'])
            else:
                self.assertEqual(row['padded_neighbors'], 11)
            rows.append(dict(name=name, words=row['words'], differences=row['differences'], raw_sha=row['raw_sha']))
        self.assertEqual(len(rows), 17)
        self.receipt('source-controls', completed_complete_forms=len(rows), rows=rows,
                     overflow_rejections=sum(r['words'] > 959 for r in rows), no_executable_trimming=True)

    def test_02_four_completed_captures_and_actual_assembler_boundary(self):
        forms = dict(recovery.all_forms())
        captures = (('selected-exit-cleanup', recovery.previous.selected_body(), 959, 721, 686),
                    ('local-disabled-exit', forms['local-disabled-exit'], 960, 605, 686),
                    ('separate-u32-buttons', forms['separate-u32-buttons'], 959, 486, 684),
                    (recovery.SELECTED_NAME, self.body, 959, 475, 684))
        rows = []
        for label, body, size, differences, instructions in captures:
            record, words, binary = recovery.finish_trace(self.root, self.out, label, body)
            self.assertEqual((len(words), sum(a != b for a, b in zip(words, self.truth))), (size, differences))
            self.assertEqual((record['correlated_events'], len(binary)), (74, instructions))
            self.assertEqual(record['compiler_as1_sha256'], recovery.BASELINE['movement_return_compiler_as1'])
            clear = next(i for i, r in enumerate(binary)
                         if (r['opcode'], r['register0'], r['register1'], r['word3']) == (70, 0, 16, 316))
            following_jump = next(r for r in binary[clear + 1:] if r['opcode'] == 4)
            raw = list(struct.iter_unpack('>4I', (self.out / 'traces' / label / 'as1-input-11.bin').read_bytes()))
            labels = [i for i in range(binary[clear]['record'] + 1, following_jump['record']) if raw[i][1] >> 16 & 63 == 0]
            self.assertEqual(bool(labels), label != 'selected-exit-cleanup')
            self.assertEqual(sum((r['opcode'], r['register0'], r['register1'], r['word3']) == (42, 31, 29, 44)
                                 for r in binary), 1)
            rows.append(dict(label=label, emitter_events=74, binary_instructions=len(binary),
                             kind0_labels_between_clear_and_jump=labels, one_RA_load_before_AS1=True))
        record = json.loads((self.work / 'return-summary.json').read_text())
        layout = recovery.check_layout(record, self.words, recovery.previous.frame.isolated(self.body))
        self.receipt('backend', completed_owned_captures=4, rows=rows, selected_layout=layout,
                     complete_normal_objects_relocations_pools_and_real_AS1_inputs_qualified=True)

    def test_03_observer_lifetime_transport_and_effective_AS1_controls(self):
        script = recovery.debugger_script(self.root, self.work)
        for forbidden in ('write_memory', '\ncall ', '\nattach ', 'target remote', '\nshell '):
            self.assertNotIn(forbidden, script)
        self.assertIn('gdb.events.exited.connect(movement_emit_removed)', script)
        function = script[script.index('def capture_as1():'):script.index('class EmitObserver')]
        env = dict(gdb=SimpleNamespace(current_progspace=lambda: SimpleNamespace(filename='as1'), GdbError=RuntimeError),
                   as1='as1', movement_emit_probes=[SimpleNamespace(is_valid=lambda: True)])
        exec(function, env)
        with self.assertRaisesRegex(RuntimeError, 'survived into AS1'):
            env['capture_as1']()
        log = (self.work / 'debugger.txt').read_text()
        count = 1
        with patch.object(recovery.backend.nodes, 'CHILD_EXIT', 'TRACE_EXIT inferior=4 code=0'):
            for name in recovery.backend.PROBES:
                for prefix in ('FINALIZER_EMIT_INSTALLED ', 'FINALIZER_EMIT_REMOVED '):
                    with self.assertRaises(ValueError):
                        recovery.backend.emitter_events(log.replace(prefix + name, ''))
                    count += 1
                filtered = '\n'.join(line for line in log.splitlines() if not (line.startswith(recovery.backend.PREFIX)
                    and json.loads(line.removeprefix(recovery.backend.PREFIX))['probe'] == name))
                with self.assertRaises(ValueError):
                    recovery.backend.emitter_events(filtered)
                count += 1
            marker = next(line for line in log.splitlines() if line.startswith('FINALIZER_AS1 '))
            event = json.loads(marker.removeprefix('FINALIZER_AS1 '))
            for key, value in (('inferior', 1), ('files', []), ('arguments', ['as1', '-O1'])):
                with self.assertRaises(ValueError):
                    recovery.backend.validate_as1(self.work, log.replace(marker, 'FINALIZER_AS1 ' + json.dumps(dict(event, **{key: value}))))
                count += 1
            path = self.work / 'as1-input-11.bin'
            data = path.read_bytes()
            read = Path.read_bytes
            with patch.object(Path, 'read_bytes', lambda p: data + b'\0' if p == path else read(p)):
                with self.assertRaises(ValueError):
                    recovery.backend.validate_as1(self.work, log)
            count += 1
            removed = 'FINALIZER_EMIT_REMOVED memory'
            late = log.replace(removed, '') + '\n' + removed
            with self.assertRaises(ValueError):
                recovery.backend.validate_as1(self.work, late)
            count += 1
        failed = json.loads((self.out / 'traces/selected/receipt.json').read_text())
        self.assertFalse(failed['code_unchanged'])
        self.assertNotEqual(failed['exit_code'], 0)
        with self.assertRaises((ValueError, FileNotFoundError)):
            recovery.finish_trace(self.root, self.out, 'selected', recovery.previous.selected_body())
        count += 1
        self.receipt('observer-controls', effective_controls=count, live_probe_AS1_guard_effective=True,
                     failed_owned_trace_not_accepted=True, actual_exit_markers_not_synthetic_records=True)

    def test_04_effective_wire_home_frame_and_emitted_store_controls(self):
        record = json.loads((self.work / 'return-summary.json').read_text())
        content = recovery.previous.frame.isolated(self.body)
        recovery.check_layout(record, self.words, content)
        count = 0
        for phase in ('frontend', 'optimizer'):
            bad = copy.deepcopy(record)
            next(r for r in bad['records'][phase] if r['name'] == 'def' and r['storage'] == 'M')['length'] += 4
            with self.assertRaises(ValueError):
                recovery.check_layout(bad, self.words, content)
            count += 1
        markers = dict(recovery.previous.frame.MARKERS)
        markers['distanceCall'] = 'nearestDistance = func_1505A6F8(D_800D154C, record);'
        markers['turn'] = 'func_150599C8(actor, 8, (u16)heading);'
        summary = recovery.previous.frame.summary(record, content, markers)
        for name in ('contact', 'speed', 'input', 'angle', 'distance', 'index', 'record', 'distanceCall'):
            marked = next(r for r in summary['phases']['frontend']['markers'][name]
                          if r['name'] == 'str' and r['storage'] == 'M')
            bad = copy.deepcopy(record)
            next(r for r in bad['records']['frontend'] if r['byte_offset'] == marked['byte_offset'])['offset'] -= 4
            with self.assertRaises(ValueError):
                recovery.check_layout(bad, self.words, content)
            count += 1
        for key, value in (('offset', -84), ('dtype', 'J'), ('length', 2)):
            bad = copy.deepcopy(record)
            next(r for r in bad['records']['frontend'] if r['name'] == 'str' and r['storage'] == 'M' and r['offset'] == -88)[key] = value
            with self.assertRaises(ValueError):
                recovery.check_layout(bad, self.words, content)
            count += 1
        angle = self.words.index(0x0D416973) + 1
        call = self.words.index(0x0D4169BE)
        slots = [0, 5, angle]
        for op, offset in ((43, 0x50), (43, 0x34), (57, 0x48)):
            slots.append(next(i for i in range(call - 5, call + 2) if self.words[i] >> 26 == op and self.words[i] & 65535 == offset))
        for index in slots:
            bad = list(self.words)
            bad[index] ^= 4
            with self.assertRaises(ValueError):
                recovery.check_layout(record, bad, content)
            count += 1
        for i in range(4):
            for key in ('host_pc', 'frame'):
                bad = copy.deepcopy(record)
                bad['events'][i][key] ^= 4
                with self.assertRaises(ValueError):
                    recovery.check_layout(bad, self.words, content)
                count += 1
        for key, value in (('locals', 88), ('saved', 24), ('temporary', 4)):
            bad = copy.deepcopy(record)
            bad['events'][-1][key] = value
            with self.assertRaises(ValueError):
                recovery.check_layout(bad, self.words, content)
            count += 1
        self.receipt('layout-controls', effective_controls=count, real_buttons_and_all_prior_live_homes_checked=True)

    def test_05_complete_public_width_filter_mutation_and_FP_corpus(self):
        for name in ('test_02_all_three_paths_and_numeric_boundaries', 'test_03_every_signed_stick_byte_and_cooldown',
                     'test_04_record_filters_nearest_ties_and_mutating_providers', 'test_10_modeled_float_edges_not_hardware_FCSR'):
            getattr(self.harness, name)()
        self.assertEqual(len(self.harness.coverage & set(range(source.ENTRY, source.ENTRY + source.SIZE, 4))), 947)
        self.receipt('public', complete_cases=2496, FP_edge_cases=20, reachable_retail_words=947,
                     original_duplicate_words_retained=12, actual_curve_connected=True, no_hardware_FCSR_claim=True)

    def test_06_initial_active_prefixes_and_complete_disabled_private_path(self):
        cuts = (38, 46, 37, 39, 40)
        equal = 0
        for phase, pattern, gate in itertools.product((0, 8), (0, 1), range(5)):
            memory, case = model.fixture(self.rom, phase=phase, pattern=pattern, gate=gate, held=101)
            for cut in range(cuts[gate] + 1):
                pair = [model.Oracle(w, memory, case, self.connected) for w in (self.truth, self.words)]
                for machine in pair:
                    machine.access_fault = cut
                    with self.assertRaises(model.point.faults.AccessBoundary):
                        machine.run()
                same = model.point.state(pair[0]) == model.point.state(pair[1])
                self.assertEqual(same, cut < cuts[gate])
                self.assertEqual(pair[0].lo, pair[1].lo)
                self.assertEqual(pair[0].condition, pair[1].condition)
                if same:
                    equal += 1
                else:
                    self.assertEqual(pair[0].memory, pair[1].memory)
                    self.assertEqual(pair[0].r, pair[1].r)
                    self.assertEqual([m.current_pc for m in pair], [0x150F3A80] * 2)
                    self.assertEqual([i for i, (a, b) in enumerate(zip(pair[0].f, pair[1].f)) if a != b], [4, 18])
        self.assertEqual(equal, 800)
        disabled, prefixes = 0, 0
        for phase, pattern, gate, held in itertools.product((0, 8), (0, 1), range(5), (0, 100, 101, 124)):
            memory, case = model.fixture(self.rom, phase=phase, pattern=pattern, gate=gate, held=held, disabled=1)
            for cut in range(96):
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
                self.assertEqual(model.point.state(pair[0]), model.point.state(pair[1]))
                self.assertEqual((pair[0].lo, pair[0].condition), (pair[1].lo, pair[1].condition))
                if not fired[0]:
                    disabled += 1
                    break
                prefixes += 1
            else:
                self.fail('Disabled fault-prefix corpus did not finish')
        self.assertEqual(disabled, 80)
        self.receipt('private', initial_active_states=20, equal_initial_active_prefixes=equal, first_cuts=list(cuts),
                     first_PC='0x150F3A80', different_FPRs=[4, 18], former_return_PC_gap_closed=True,
                     disabled_complete_states=disabled, disabled_equal_fault_prefixes=prefixes,
                     all_modeled_LO_condition_compared=True, full_opaque_provider_or_hardware_acceptance_not_claimed=True)

    def test_07_native32_unsigned_extremes_rebases_and_guest_aliases(self):
        self.harness.test_05_two_independent_text_rebases()
        specs = [*list(previous.core_specs())[::7], *list(previous.mutation_specs())[::5], *previous.targeted_specs()]
        original = model.fixture

        def fixture(rom, **spec):
            memory, case = original(rom, **spec)
            if 'headingOffset' in spec:
                model.put(memory, 0x800CC280, spec['headingOffset'])
            return memory, case

        for angle, offset in itertools.product((0, 1, 65535), (0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)):
            specs.append(dict(mode=0, angle=angle, magnitude=2., headingOffset=offset))
        with patch.object(model, 'fixture', fixture), patch.object(source, 'SELECTED', self.body):
            row = native.qualify(self.root, self.out, self.rom, specs)
            for spec in specs[-9:]:
                self.harness.compare(spec)
        self.assertEqual((row['cases_per_profile'], row['effective_controls']), (139, 8))
        count = 0
        for alias, gate, mode in itertools.product((0x800CC284, 0x800CC288, model.SLOT), (0, 1), (0, 1)):
            memory, case = model.fixture(self.rom, gate=gate, mode=mode, pattern=1, pressed=0x8000)
            model.put(memory, model.SLOT, alias)
            memory.update({0x800C0080 + i: 0xA5 for i in range(32)})
            expected = model.reference(memory, case)
            for words in (self.truth, self.words):
                actual = model.Oracle(words, memory, case, self.connected).run()
                self.assertEqual(model.public(actual.memory), model.public(expected[0]))
                self.assertEqual(actual.calls, expected[1])
                self.assertEqual(actual.observations, expected[2])
            count += 1
        self.receipt('native-rebases-aliases', native_cases_per_profile=139, profiles=['O2', 'O0'], UBSan=True,
                     effective_native_controls=8, unsigned_heading_guest_cases=9, rebases=2, rebase_cases=12,
                     guest_alias_cases=count, no_general_native_pointer_alias_claim=True)

    def test_08_installed_baseline_data_and_all_checkpoints_unchanged(self):
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
