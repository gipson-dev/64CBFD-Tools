"""Direct table-debris C, exact literal alias, and complete pre-install image prediction."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_table_debris_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import test_game_table_debris as previous
from tools.tests import game_table_debris_oracle as guest
from tools.tests import game_table_debris_native as native
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools


def controls():
    return {
        'narrow-lookup': source.SELECTED.replace('func_1518C900(entry->kind)', 'func_1518C900((u8)entry->kind)'),
        'signed-lookup': source.SELECTED.replace('func_1518C900(entry->kind)', 'func_1518C900((s16)entry->kind)'),
        'cached-kind': source.SELECTED.replace('    s32 asset;', '    s32 kind;\n    s32 asset;').replace(
            '        asset = func_1518C900(entry->kind);\n        packet.kind = entry->kind;',
            '        kind = entry->kind;\n        asset = func_1518C900(kind);\n        packet.kind = kind;'),
        'wrong-position-type': source.SELECTED.replace('entry->offset[0] + originX', '*(s32 *)&entry->offset[0] + originX'),
        'missing-absolute': source.SELECTED.replace('fabsf(entry->offset[1])', 'entry->offset[1]'),
        'wrong-horizontal': source.SELECTED.replace('entry->offset[2] * 0.09f', 'entry->offset[2] * 0.23f'),
        'wrong-rotation': source.SELECTED.replace('packet.rotation[0] * 0.1f', 'packet.rotation[1] * 0.1f'),
        'wrong-second-range': source.SELECTED.replace('* 10.0f - 5.0f', '* 9.0f - 5.0f'),
        'reset-fixed-packet': source.SELECTED.replace('        asset = func_1518C900(entry->kind);',
            '        packet.lifetime = 60;\n        asset = func_1518C900(entry->kind);'),
        'reset-reserved-byte': source.SELECTED.replace('        packet.asset = asset;',
            '        packet.reserved44[0] = 0;\n        packet.asset = asset;'),
        'wide-actor-store': source.SELECTED.replace('actor[0x6E] = 1;', '*(s32 *)(actor + 0x6C) = 1;'),
    }


class TableDebrisMatchTests(unittest.TestCase):
    receipt = previous.TableDebrisTests.receipt
    compare = previous.TableDebrisTests.compare
    test_02_complete_sequences_all_packet_bytes_and_provider_lifetimes = previous.TableDebrisTests.test_02_complete_sequences_all_packet_bytes_and_provider_lifetimes
    test_06_original_three_input_caller_and_missing_current_window = previous.TableDebrisTests.test_06_original_three_input_caller_and_missing_current_window
    test_07_actual_consumer_allocator_and_full_packet_copies = previous.TableDebrisTests.test_07_actual_consumer_allocator_and_full_packet_copies

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.truth = list(struct.unpack_from('>158I', cls.rom, source.ROM))

    def test_01_direct_shape_neighbors_literal_pool_and_actual_padder(self):
        self.assertEqual(self.words, self.truth)
        self.assertEqual((self.row['words'], self.row['frame'], self.row['packet_home'], self.row['target_word_guards']), (158, 232, 132, 0))
        raw, rel = source.checked_object(self.obj)
        old_obj, diagnostics = source.build.compile_owner(self.root, self.out,
            (self.out / 'before-edge_wrapper_owner').read_text(), 'neighbor-baseline')
        self.assertEqual(diagnostics, '')
        old, new = parse_object(old_obj), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            relative = lambda o, f: {at - f['value']: rows for at, rows in o[2].items() if f['value'] <= at < f['value'] + f['size']}
            self.assertEqual(relative(old, f), relative(new, g), name)
        self.assertEqual(normalized_pools(old_obj), {'.rodata': None, '.data': None})
        self.assertEqual(sections(self.obj)['.rodata'][1], source.POOL)
        self.assertEqual(self.rom[0x24BA64:0x24BA70], source.POOL[:12])
        self.assertEqual({i: struct.unpack_from('>I', raw, i)[0] for i in (164, 216, 268)},
            {164: 0xE7A6007C, 216: 0xE7AA0078, 268: 0xE7B20074})
        self.assertNotIn((',' + source.FUNCTION + ',').encode(), (self.out / 'before-guards').read_bytes())
        # The unaliased compiler stream reads its own immutable literal pool.
        data, functions = source.build.link_owner(self.root, self.out, self.obj, source.OWNER)
        f = functions[source.FUNCTION]
        raw_words = list(struct.unpack_from('>158I', data, f['value']))
        address, pool = sections(self.obj.with_suffix('.elf'))['.rodata']
        for mode in (0, 1, 2, 3, 4, 5):
            memory, args = guest.fixture(self.rom, 1)
            memory.update({address + i: byte for i, byte in enumerate(pool)})
            models = self.compare(memory, args, mode, streams=(self.truth, raw_words))
            self.assertEqual(models[0].observed, models[1].observed)
        self.receipt('shape', **self.row, neighbors_unchanged=8, existing_guard_bytes_fixed=True,
            six_raw_literal_address_differences_resolved_only_by_anchor=True,
            own_raw_literal_pool_semantics_cases=6, no_instructions_inserted_omitted_or_replaced=True)

    def test_03_effective_compiled_semantic_negatives(self):
        evidence = []
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED, name)
            obj, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            address, pool = sections(obj.with_suffix('.elf'))['.rodata']
            failed = False
            for mode in (0, 1, 2, 3, 5):
                memory, args = guest.fixture(self.rom, 1)
                memory.update({address + i: byte for i, byte in enumerate(pool)})
                try:
                    self.compare(memory, args, mode, 2, streams=(self.truth, words))
                except AssertionError:
                    failed = True
                    break
            self.assertTrue(failed, name)
            evidence.append(dict(name=name, raw_sha256=row['raw_sha256'], effective=True))
        self.receipt('negatives', compiled=evidence, each_stream_uses_its_actual_literal_pool=True)

    def test_04_native32_framed_initialized_and_provider_seeded_bytes(self):
        with patch.object(previous, 'source', source), patch.object(previous, 'controls', controls):
            return previous.TableDebrisTests.test_04_native32_framed_initialized_and_provider_seeded_bytes(self)

    def test_05_all_live_frozen_input_and_manifest_corruptions(self):
        source.freeze(self.root, self.out)
        expected = source.expected_inputs(self.root, self.out)
        prediction = {k: hashlib.sha256(data).hexdigest() for k, data in expected.items()}
        initial = self.out / 'initial-prediction.json'
        if not initial.exists():
            self.assertEqual({k: hashlib.sha256((self.root / p).read_bytes()).hexdigest() for k, p in source.PATHS.items()}, source.BASELINE)
            initial.write_text(json.dumps(prediction, indent=2) + '\n')
        self.assertEqual(json.loads(initial.read_text()), prediction)
        live = {k: hashlib.sha256((self.root / p).read_bytes()).hexdigest() for k, p in source.PATHS.items()}
        self.assertIn(live, (source.BASELINE, dict(source.BASELINE, **prediction)))
        rb, rt = Path.read_bytes, Path.read_text
        for key in source.PATHS:
            target = self.out / ('before-' + key)
            with patch.object(Path, 'read_bytes', lambda p: rb(p) + b'\n' if p == target else rb(p)):
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    source.freeze(self.root, self.out)
        target = self.out / 'baseline.json'
        with patch.object(Path, 'read_text', lambda p, *a, **kw: '{}' if p == target else rt(p, *a, **kw)):
            with self.assertRaisesRegex(ValueError, 'manifest'):
                source.freeze(self.root, self.out)
        self.receipt('scope', inputs=len(source.PATHS), all_frozen_capture_corruptions=True,
            complete_preinstall_prediction=prediction, target_guards_unchanged=True)

    def test_08_fired_complete_literal_fault_prefixes(self):
        cases = 0
        for phase in (0, 8):
            memory, args = guest.fixture(self.rom, 1)
            complete = guest.TableDebrisOracle(self.words, memory, args, phase).run()
            for fault in range(complete.accesses):
                models = []
                for words in (self.words, self.truth):
                    model = guest.TableDebrisOracle(words, memory, args, phase, fault=fault)
                    with self.assertRaises(guest.edge.AccessFault):
                        model.run()
                    models.append(model)
                self.assertEqual(guest.prior.literal(models[0]), guest.prior.literal(models[1]))
                cases += 1
        self.receipt('faults', fired_prefix_pairs=cases, literal_all_state_equal=True,
            no_native_FP_environment_or_fault_order_claim=True)

    def test_09_all_raw_words_bindings_pool_and_alias_controls(self):
        text, functions, rel = parse_object(self.obj)
        f = functions[source.FUNCTION]
        for index in range(158):
            bad = bytearray(text)
            bad[f['value'] + index * 4] ^= 1
            with patch.object(source, 'parse_object', return_value=(bytes(bad), functions, rel)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        for at in source.RELOCATIONS:
            bad = {k: list(v) for k, v in rel.items()}
            bad[f['value'] + at] = [(source.RELOCATIONS[at][0][0], 'wrong_symbol')]
            with patch.object(source, 'parse_object', return_value=(text, functions, bad)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        pools = sections(self.obj)
        for index in range(16):
            bad = bytearray(source.POOL)
            bad[index] ^= 1
            with patch.object(source, 'sections', return_value=dict(pools, **{'.rodata': (0, bytes(bad))})):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        bad = self.out / 'wrong-anchor.s'
        bad.write_text(emit_padded_assembly(self.obj, self.root / source.PATHS['edge_wrapper_original'], filename=source.OWNER,
            word_patches_path=self.out / 'before-guards', rodata_symbol='D_800A6FA8'))
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(bad.with_suffix('.o')), str(bad)], check=True, capture_output=True)
        data, functions = source.build.link_owner(self.root, self.out, bad.with_suffix('.o'), source.OWNER)
        words = list(struct.unpack_from('>158I', data, functions[source.FUNCTION]['value']))
        memory, args = guest.fixture(self.rom, 1)
        guest.put(memory, 0x800A6FB0, guest.bits(-0.2))
        with self.assertRaises(AssertionError):
            self.compare(memory, args, streams=(self.truth, words))
        self.receipt('corruptions', raw_word_flips=158, binding_flips=18, literal_bytes=16, wrong_alias_effective=True)

    def test_10_independent_original_rebases_and_literal_carries(self):
        original = (self.out / 'before-edge_wrapper_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('endlabel ' + source.FUNCTION, 1)[0]
        path = self.out / 'original-rebase.s'
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n.type ' +
            source.FUNCTION + ', @function\nglabel ' + source.FUNCTION + '\n' + original + '\n.size ' + source.FUNCTION + ', . - ' + source.FUNCTION + '\n')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        text, functions, rel = parse_object(path.with_suffix('.o'))
        f = functions[source.FUNCTION]
        original_raw = text[f['value']:f['value'] + f['size']]
        original_rel = {at - f['value']: rows for at, rows in rel.items() if f['value'] <= at < f['value'] + f['size']}
        raw, bindings = source.checked_object(self.obj)
        cases = 0
        for entry, delta, call_delta in ((0x15201000, 0x1000, 0x2000), (0x15302000, 0x2100, 0x4000), (0x15403000, 0x4100, 0x6000)):
            calls = {'func_1518C900': source.LOOKUP + call_delta, 'func_150ADA68': source.RANDOM + call_delta, 'func_15168BE4': source.SUBMIT + call_delta}
            original_links = {'D_%08X' % at: at + delta for at in (source.TABLE, *range(0x800A6F98, 0x800A6FB0, 4))}
            original_links.update(calls)
            candidate_links = dict(original_links)
            aliased = {at: [(kind, source.POOL_ANCHOR if symbol == '.rodata' else symbol)
                for kind, symbol in rows] for at, rows in bindings.items()}
            streams = []
            for index, (data, rows, links) in enumerate(((raw, aliased, candidate_links), (original_raw, original_rel, original_links))):
                assembly, missing = emit_function(data, dict(value=0, size=len(data)), rows, source.FUNCTION, links)
                self.assertFalse(missing)
                file = self.out / ('rebase-%X-%d.s' % (entry, index))
                file.write_text(assembly)
                file.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(file.with_suffix('.o')), str(file)], check=True, capture_output=True)
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(file.with_suffix('.ld')), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in links.items()], '-o', str(file.with_suffix('.elf')), str(file.with_suffix('.o'))], check=True, capture_output=True)
                streams.append(list(struct.unpack_from('>158I', sections(file.with_suffix('.elf'))['.text'][1])))
            self.assertEqual(streams[0], streams[1])
            mapping = {new: old for new, old in zip(calls.values(), (source.LOOKUP, source.RANDOM, source.SUBMIT))}
            for pattern, flags, mode, phase in itertools.product(range(3), (0, 0xABCDEF81), (0, 4), (0, 8)):
                initial, args = guest.fixture(self.rom, pattern, flags)
                memory = {a + delta if source.TABLE <= a < 0x800A6FB0 else a: byte for a, byte in initial.items()}
                expected = guest.reference(initial, args, mode, phase=phase)
                for words in streams:
                    model = guest.TableDebrisOracle(words, memory, args, phase, mode, entry=entry, bindings=mapping).run()
                    public = {a - delta if source.TABLE + delta <= a < 0x800A6FB0 + delta else a: byte for a, byte in guest.public(model.memory).items()}
                    self.assertEqual((model.calls, model.full_packets, public), expected)
                cases += 1
        self.receipt('rebases', independent_original_sets=3, paired_cases=cases, all_96_bytes=True,
            literal_pool_addends_and_signed_low_carry=True, all_table_constant_and_call_bindings_changed=True)

    def test_11_actual_fired_compiler_frame_provenance(self):
        from tools.experiments import game_actor_callback_frame_trace as observer
        self.assertEqual(observer.fingerprints(self.root), observer.COMPILERS)
        evidence = {}
        for name, frame, reservation, digest in (('scalar', 248, 144, '7c11a8d372b5d02912bf3e11053e88e2223aba5746f8f446e0cb33e2788f1436'),
                ('array', 248, 144, '0065ae5fc134e4aeb1e371148aa32c1329db165c8c8c0834a1774e3d98c2eed3'),
                ('accepted', 232, 128, source.RAW_SHA256)):
            work = self.out / ('frame-' + name)
            log = (work / 'debugger.txt').read_text()
            result = observer.validate_observations(work, log)
            receipt = json.loads((work / 'receipt.json').read_text())
            self.assertEqual(receipt['exit_code'], 0)
            self.assertEqual(receipt['raw_target_sha256'], digest)
            self.assertTrue(receipt['code_unchanged'] and receipt['standalone_equals_complete_owner'])
            self.assertEqual(receipt['different_object_sections'], ['.mdebug'])
            self.assertEqual(parse_object(work / 'normal.o'), parse_object(work / 'traced.o'))
            final = result['events'][-1]
            self.assertEqual((final['frame'], final['locals'], final['saved'], final['outgoing'], final['temporary']), (frame, reservation, 88, 16, 0))
            self.assertTrue(all(line.endswith(' code=0') for line in receipt['completed_exits']))
            with self.assertRaises(ValueError):
                observer.validate_observations(work, log.replace('frame-watch-installed', 'not-installed'))
            evidence[name] = dict(frame=frame, locals=reservation, saved=88, outgoing=16, no_spill_increment=True)
        self.receipt('frames', fired_owned_compiler_observations=evidence, all_three_emit_normal_code=True,
            mdebug_metadata_not_claimed_equal=True, no_compiler_change_or_install=True)

    def test_12_complete_preinstall_relinks_and_exact_symbol_serialization(self):
        row = source.prelink_prediction(self.root, self.out)
        expected = source.expected_inputs(self.root, self.out)
        self.assertEqual((self.out / 'prelink-prediction.elf').read_bytes(), expected['elf'])
        before = (self.out / 'before-elf').read_bytes()
        initial = source.slot_expected_image(before, self.rom)
        self.assertEqual((row['slot_changes'], row['additional_serialization_bytes']), (507, 121))
        self.assertEqual(sum(a != b for a, b in zip(before, expected['elf'])), 628)
        names = {n for original, _ in source.SERIALIZATION_GROUPS for n in original}
        controls = 0
        for at, name, fields, name_at in source.symbol_rows(initial):
            if name in names:
                for position in (at, at + 4, name_at):
                    bad = bytearray(initial)
                    bad[position] ^= 1
                    with self.assertRaises(ValueError):
                        source.serialize_symbols(bytes(bad))
                    controls += 1
        self.assertEqual(controls, 51)
        self.receipt('prediction', **row, total_changed_bytes=628, exact_record_name_cycles=6,
            effective_record_name_corruptions=controls, complete_preinstall_image=True, no_exclusions=True)


if __name__ == '__main__':
    unittest.main()
