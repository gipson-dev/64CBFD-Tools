"""Literal private/fault, native, relocation, owner and compiler-frame gates."""
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_table_fade_match as source
from tools.experiments import game_table_fade_frame as frame
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools import pad_generated_object as padder
from tools.tests import test_game_table_fade_callback as previous
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_factory_preset_wrapper import state as basic_state
from tools.tests.test_game_actor_mask_scan_match import AccessFault
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_record_constructor_match import elf_slot_offset

Oracle, fixture, reference, external = previous.TableFadeOracle, previous.fixture, previous.reference, previous.external


def state(model):
    return basic_state(model), model.lo, model.condition, model.callbacks, model.writes, model.visits


def controls():
    # Retain the earlier control meanings after the genuine tail operands split.
    result = {
        'wide-active': source.SELECTED.replace('record[0x24]', '*(u32 *)(record + 0x24)'),
        'wrong-rise': source.SELECTED.replace('<< 4', '<< 5'),
        'early-byte': source.SELECTED.replace('    if (record[0x24] == 0 && value == 0)', '    value = (u8)value;\n    if (record[0x24] == 0 && value == 0)'),
        'wrong-fade': source.SELECTED.replace('fades.values[index]', 'growth.values[index]'),
        'wrong-growth': source.SELECTED.replace('coefficient = growth.values[index]', 'coefficient = fades.values[index]'),
        'wrong-special': source.SELECTED.replace('index == 3', 'index == 4'),
        'live-growth': source.SELECTED.replace('coefficient = growth.values[index]', 'coefficient = D_8008CBD0.values[index]'),
        'live-scale': source.SELECTED.replace('record, scales.values[index]', 'record, D_8008CBC4.values[index]'),
    }
    return result


class TableFadeMatchCandidateTests(unittest.TestCase):
    def test_scope_and_strict_compiler_gate(self):
        self.assertEqual(len(source.PATHS), 52)
        self.assertEqual(len(set(source.PATHS.values())), 52)
        self.assertEqual(set(source.PATHS), set(source.BASELINE))
        self.assertEqual(source.build.body(source.SELECTED, source.FUNCTION), source.build.body(dict(frame.candidates())['tail-live-operands'], source.FUNCTION))
        for count, differences, frame_size, diagnostic in ((103, 15, 96, ''), (103, 14, 104, ''), (102, 15, 104, ''), (103, 15, 104, 'warning')):
            with patch.object(source, 'measure', return_value=(None, [], dict(words=count, differences=differences, frame=frame_size, diagnostics=diagnostic))):
                with self.assertRaisesRegex(ValueError, 'compiler shape'):
                    source.qualify(Path('.'), Path('.'))
        with self.assertRaisesRegex(ValueError, 'words or relocations'):
            source.normalize(b'', {})
        for body in dict(frame.candidates()).values():
            self.assertNotIn('volatile', body)


class TableFadeMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.raw_words, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>103I', cls.rom, source.ROM))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    test_08_all_original_801_archive_fingerprints = previous.TableFadeRecoveryTests.test_08_all_original_801_archive_fingerprints

    def test_01_guarded_shape_all_neighbors_pools_and_corruptions(self):
        self.assertEqual((len(self.raw_words), self.row['differences'], self.row['guards_added'], self.row['frame']), (103, 15, 27, 104))
        self.assertEqual(self.words, self.truth)
        raw, rel = source.raw_target(self.obj)
        normalized, moved = source.normalize(raw, rel)
        self.assertEqual(len(normalized), 412)
        self.assertEqual(moved[232], rel[236])
        self.assertEqual(moved[244], rel[240])
        self.assertNotIn(236, moved)
        self.assertNotIn(240, moved)
        for index in range(103):
            bad = bytearray(raw)
            bad[index * 4] ^= 1
            with self.assertRaisesRegex(ValueError, 'words or relocations'):
                source.normalize(bytes(bad), rel)
        for offset in rel:
            for action in ('missing', 'symbol', 'kind'):
                bad = dict(rel)
                if action == 'missing':
                    del bad[offset]
                else:
                    kind, name = bad[offset][0]
                    bad[offset] = [(kind + '_bad', name)] if action == 'kind' else [(kind, name + '_bad')]
                with self.assertRaisesRegex(ValueError, 'words or relocations'):
                    source.normalize(raw, bad)
        obj, diagnostic = source.build.compile_owner(self.root, self.out, (self.out / 'before-preset_owner').read_text(), 'before-owner')
        self.assertEqual(diagnostic, '')
        old, new = padder.parse_object(obj), padder.parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            relative = lambda o, f: [(p - f['value'], r) for p, r in o[2].items() if f['value'] <= p < f['value'] + f['size']]
            self.assertEqual(relative(old, f), relative(new, g), name)
        self.assertEqual(normalized_pools(obj), normalized_pools(self.obj))
        before = (self.out / 'before-guards').read_bytes()
        guards = source.guard_manifest(before, raw, rel)
        self.assertTrue(guards.startswith(before))
        rows = [r for r in csv.DictReader(io.StringIO(guards.decode())) if r['function'] == source.FUNCTION]
        self.assertEqual(len(rows), 27)
        self.assertEqual(sum(r['expected'] != r['replacement'] for r in rows), 15)
        self.assertTrue(all(r['omit'] == 'false' and not r['insert_after'] for r in rows))
        with self.assertRaisesRegex(ValueError, 'predecessor'):
            source.guard_manifest(guards, raw, rel)
        self.receipt('owner', raw_words=103, raw_differences=15, linked_words=103, linked_differences=0,
            expected_word_guards=27, numeric_replacements=15, identity_binding_guards=12,
            raw_word_flips_rejected=103, relocation_flips_rejected=48, unchanged_neighbors=29,
            pools_and_relative_relocations_fixed=True, no_frame_guards_or_profile_changes=True)

    def test_02_literal_private_guest_states_and_live_provider_semantics(self):
        cases, visits = 0, set()
        for index in range(11):
            limit = previous.TABLE[24 + index]
            values = sorted({v for v in (0, 1, 127, 128, 254, 255, limit - 1, limit, limit + 1) if 0 <= v <= 255})
            for value in values:
                for active in (0, 1, 255):
                    for step in (0, 1, 0xFFFFFFFF, 16, 0xFFFFFFE0, 0x80000000, 0x7FFFFFFF, 65536):
                        for mode in range(4):
                            memory = fixture(index, value, active, step)
                            expected, result, calls = reference(memory, mode=mode)
                            phase = (cases & 1) * 8
                            pair = [Oracle(w, memory, mode=mode, phase=phase).run() for w in (self.words, self.truth)]
                            self.assertEqual(state(pair[0]), state(pair[1]))
                            self.assertEqual((external(pair[0].memory), pair[0].r[2], pair[0].calls), (external(expected), result, calls))
                            visits |= pair[0].visits
                            cases += 1
        self.assertEqual(visits, set(range(source.ENTRY, source.ENTRY + 412, 4)) - {source.ENTRY + 304})
        self.receipt('abi', paired_cases=cases, full_literal_private_state_equal=True, both_stack_phases=True,
            full_word_completion_snapshot_tables_and_live_step_and_halfword=True, visited_words=102,
            retained_unreachable_incoming_home_store=304, valid_mode_domain=[0, 10])

    def test_03_every_fired_private_memory_fault(self):
        count, rejected_raw = 0, 0
        for memory in (fixture(0, 0, 0), fixture(3, 128, 1), fixture(6, 1, 0, 0xFFFFFFFF)):
            for phase in (0, 8):
                whole = Oracle(self.truth, memory, phase=phase, mode=3).run()
                for fault in range(whole.accesses):
                    pair = [Oracle(w, memory, fault=fault, phase=phase, mode=3) for w in (self.words, self.truth)]
                    for model in pair:
                        with self.assertRaises(AccessFault):
                            model.run()
                    self.assertEqual(state(pair[0]), state(pair[1]))
                    raw = Oracle(self.raw_words, memory, fault=fault, phase=phase, mode=3)
                    with self.assertRaises(AccessFault):
                        raw.run()
                    rejected_raw += state(raw) != state(pair[1])
                    count += 1
        self.assertGreater(rejected_raw, 0)
        self.receipt('prefixes', paired_fired_guest_faults=count, literal_states_equal=True,
            raw_scheduling_rejections=rejected_raw, no_affine_private_or_portable_C_fault_claim=True)

    def test_04_every_compiled_semantic_control_is_effective_and_rejected_by_guards(self):
        probes = [(0, 127, 1, 1, 0), (3, 1, 0, 1, 0), (6, 1, 0, 0xFFFFFFFF, 0), (0, 1, 1, 1, 2), (3, 255, 1, 16, 3), (0, 0, 0, 1, 0)]
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED)
            obj, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            self.assertEqual(row['diagnostics'], '')
            with self.assertRaisesRegex(ValueError, 'words or relocations'):
                source.normalize(*source.raw_target(obj))
            count = 0
            for index, value, active, step, mode in probes:
                memory = fixture(index, value, active, step)
                expected, result, calls = reference(memory, mode=mode)
                model = Oracle(words, memory, mode=mode).run()
                count += (external(model.memory), model.r[2], model.calls) != (external(expected), result, calls)
            self.assertGreater(count, 0, name)
        self.receipt('controls', effective_compiled_guest_negatives=8, every_mutant_rejected_by_normalization=True)

    def test_05_native32_complete_source_O2_O0_and_all_controls(self):
        with patch.object(previous.source, 'SELECTED', source.SELECTED), patch.object(previous, 'controls', controls):
            previous.TableFadeRecoveryTests.test_05_native32_all_intensity_modes_and_live_provider_boundaries(self)

    def test_06_real_helper_chain_and_full_private_aliases(self):
        image = (self.root / source.PATHS['elf']).read_bytes()
        connected = {}
        for entry, rom, count in ((source.MOVE, 0x19CD14, 34), (source.SCALE, 0x19CDFC, 14), (0x1516F8EC, 0x19CD9C, 12), (0x1516F91C, 0x19CDCC, 12)):
            words = list(struct.unpack_from('>%dI' % count, image, elf_slot_offset(image, entry, count * 4)))
            self.assertEqual(words, list(struct.unpack_from('>%dI' % count, self.rom, rom)))
            connected.update(zip(range(entry, entry + count * 4, 4), words))
        cases = 0
        for index in range(11):
            for value in (0, 1, 128, 255):
                for active in (0, 1):
                    for step in (1, 0xFFFFFFFF, 0x80000000):
                        memory = fixture(index, value, active, step)
                        pair = [Oracle(w, memory, phase=(cases & 1) * 8, connected=connected).run() for w in (self.words, self.truth)]
                        self.assertEqual(state(pair[0]), state(pair[1]))
                        cases += 1
        aliases = alias_faults = 0
        for phase in (0, 8):
            for offset in (-96, -80, -64, -48, -32, 0, 16):
                for mode in (0, 3):
                    record = previous.STACK + phase + offset
                    memory = fixture(3, 128, 1, record=record)
                    pair = [Oracle(w, memory, record=record, phase=phase, mode=mode) for w in (self.words, self.truth)]
                    errors = []
                    for model in pair:
                        try:
                            model.run()
                            errors.append(None)
                        except AssertionError as error:
                            if not error.args or not isinstance(error.args[0], tuple) or error.args[0][0] != 'unmapped read':
                                raise
                            errors.append(error.args)
                    self.assertEqual(errors[0], errors[1])
                    self.assertEqual(state(pair[0]), state(pair[1]))
                    alias_faults += errors[0] is not None
                    aliases += 1
        self.receipt('chain', actual_helper_words=[34, 14, 12, 12], all_calls_connected=True,
            full_private_real_chain_pairs=cases, full_private_synthetic_guest_aliases=aliases,
            alias_unmapped_read_prefixes=alias_faults, completed_aliases=aliases-alias_faults,
            aliases_not_portable_C_or_actual_game_mode_validity=True)

    def test_07_independent_original_and_normalized_rebases(self):
        raw, rel = source.normalize(*source.raw_target(self.obj))
        symbols = {name: int(name.split('_')[1], 16) for entries in rel.values() for _, name in entries}
        text, missing = emit_function(raw, dict(value=0, size=412), rel, source.FUNCTION, symbols)
        self.assertEqual(missing, [])
        original = (self.out / 'before-preset_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('glabel ', 1)[0]
        for label, body in dict(selected=text, original='glabel ' + source.FUNCTION + '\n' + original).items():
            path = self.out / (label + '-reloc.s')
            path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n' + body)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        for i, (entry, low) in enumerate(((source.ENTRY, None), (0x15177FFC, 0x7FFC), (0x15158004, 0x8004))):
            anchors = symbols if low is None else {name: (0x15100000 + j * 0x10000 + low if name.startswith('func_') else 0x80300000 + j * 0x10000 + low)
                for j, name in enumerate(sorted(symbols))}
            script = self.out / ('rebase-%d.ld' % i)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            outputs = []
            for label in ('selected', 'original'):
                elf = self.out / ('%s-rebase-%d.elf' % (label, i))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % pair for pair in anchors.items()], '-o', str(elf), str(self.out / (label + '-reloc.o'))], check=True, capture_output=True)
                outputs.append(sections(elf)['.text'][1][:412])
            self.assertEqual(outputs[0], outputs[1])
        self.receipt('rebases', independent_original_normalized_pairs=3, all_seven_symbols_independent=True,
            all_103_words_equal=True, GNU_signed_low_carries=True)

    def test_09_physical_guard_word_and_binding_gates(self):
        original = padder.parse_object(self.obj)
        start = original[1][source.FUNCTION]['value']
        manifest = self.out / 'qualified-guards.csv'
        rows = [r for r in csv.DictReader(io.StringIO(manifest.read_text())) if r['function'] == source.FUNCTION]
        for row in rows:
            bad = bytearray(original[0])
            bad[start + int(row['offset'], 0)] ^= 1
            with patch.object(padder, 'parse_object', return_value=(bytes(bad), original[1], original[2])):
                with self.assertRaisesRegex(ValueError, 'stale word patch'):
                    padder.emit_padded_assembly(self.obj, self.root / source.PATHS['preset_original'], filename=source.OWNER, word_patches_path=manifest)
        for offset in source.RELOCATIONS:
            rel = dict(original[2])
            kind, name = rel[start + offset][0]
            rel[start + offset] = [(kind, name + '_bad')]
            with patch.object(padder, 'parse_object', return_value=(original[0], original[1], rel)):
                with self.assertRaisesRegex(ValueError, 'stale relocations'):
                    padder.emit_padded_assembly(self.obj, self.root / source.PATHS['preset_original'], filename=source.OWNER, word_patches_path=manifest)
        self.receipt('physical-guards', stale_words_rejected=len(rows), stale_bindings_rejected=16)

    def test_10_fired_compiler_frame_trace_and_capture_corruptions(self):
        out = self.root / frame.BUILD
        out.mkdir(exist_ok=True)
        for name, expected in (('selected', (64, 68, 72, 96)), ('tail-live-operands', (72, 76, 80, 104))):
            record = frame.trace(self.root, out, name, dict(frame.candidates())[name])
            defs = {stage: [r['length'] for r in rows if r['name'] == 'def' and r['storage'] == 'M'] for stage, rows in record['records'].items()}
            self.assertEqual((defs['frontend'], defs['optimizer']), ([expected[0]], [expected[1]]))
            event = record['events'][-1]
            self.assertEqual((event['locals'], event['frame'], event['saved'], event['outgoing'], event['temporary']), (expected[2], expected[3], 8, 16, 0))
            self.assertEqual([e['frame'] for e in record['events']], [0, 8, 24, expected[3]])
            self.assertTrue(record['code_unchanged'] and record['standalone_equals_complete_owner'])
            self.assertFalse(record['literal_object_files_equal'])
            self.assertEqual(record['different_object_sections'], ['.mdebug'])
            log = (out / name / 'debugger.txt').read_text()
            for prefix in ('FRAME_TRACE ', 'FRAME_INPUT ', 'TRACE_EXIT '):
                bad = '\n'.join(line for line in log.splitlines() if not line.startswith(prefix))
                with self.assertRaises(ValueError):
                    frame.observer.validate_observations(out / name, bad)
            rb = Path.read_bytes
            for stage in ('frontend', 'optimizer'):
                path = out / name / (stage + '.ucode')
                with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\0' if p == path else rb(p)):
                    with self.assertRaises(ValueError):
                        frame.observer.validate_observations(out / name, log)
        self.receipt('frame', compiler_fingerprints_locked=True, CFE=[64, 72], UOPT=[68, 76], local_reservation=[72, 80],
            saved=8, outgoing=16, frames=[96, 104], observed_temporary_increment=0,
            text_functions_relocations_and_pools_fixed=True, literal_object_files_differ_in_mdebug=True,
            missing_gate_and_capture_corruptions_rejected=True)


if __name__ == '__main__':
    unittest.main()
