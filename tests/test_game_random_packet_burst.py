"""Direct burst match, real ABI, packet lifetimes, rebases and complete install proof."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_random_packet_burst as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests import game_random_packet_burst_oracle as guest
from tools.tests import game_random_packet_burst_native as native
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.match_progress import load_elf_functions


def controls():
    b = source.SELECTED
    return {
        'narrow-lookup': b.replace('func_1518C900(kind)', 'func_1518C900((u8)kind)'),
        'unsigned-high': b.replace('(func_150ADA20() >> 16)', '((u32)func_150ADA20() >> 16)'),
        'wrong-vertical-low': b.replace('verticalDraw = (u32)func_150ADA20() & 65535', 'verticalDraw = (u32)func_150ADA20() >> 16'),
        'wrong-position-scale': b.replace('spread * 0.0000152587890625f', 'spread * 0.000030517578125f'),
        'wrong-scale-range': b.replace('maximumScale - minimumScale', 'maximumScale + minimumScale'),
        'wrong-duration': b.replace('* 6.666667f + 20.0f', '* 6.666667f + 21.0f'),
        'fixed-field-reset': b.replace('        do {', '        do {\n            packet.lifetime = lifetime;'),
        'reserved-reset': b.replace('            packet.asset =', '            packet.reserved44[0] = 0;\n            packet.asset =', 1),
        'short-count': b.replace('index != count', 'index != count - 1').replace('if (count > 0)', 'if (count > 1)'),
    }


class BurstTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>256I', cls.rom, source.ROM))
        cls.owner = (cls.out / 'before-edge_wrapper_owner').read_text()

    def receipt(self, name, **row):
        (self.out / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')

    def compare(self, memory, args, mode=0, rotation=0, phase=0, fcsr=0, streams=None):
        expected = guest.reference(memory, args, mode, rotation, phase)
        models = [guest.BurstOracle(w, memory, args, mode=mode, rotation=rotation, phase=phase, fcsr=fcsr).run()
            for w in (streams or (self.truth, self.words))]
        for model in models:
            self.assertEqual((model.calls, model.full_packets), expected)
            self.assertEqual(model.random_count, max(0, guest.signed(args[0])) * 12)
        self.assertEqual(guest.prior.prior.literal(models[0]), guest.prior.prior.literal(models[1]))
        return models

    def test_01_exact_shape_neighbors_pool_and_no_guards(self):
        self.assertEqual(self.words, self.truth)
        old_obj, diag = source.build.compile_owner(self.root, self.out, self.owner, 'neighbor-baseline')
        self.assertFalse(diag)
        old, new = parse_object(old_obj), parse_object(self.obj)
        self.assertEqual(set(old[1]), set(new[1]))
        for name, f in old[1].items():
            if name == source.FUNCTION:
                continue
            g = new[1][name]
            self.assertEqual(f['size'], g['size'], name)
            self.assertEqual(old[0][f['value']:f['value'] + f['size']], new[0][g['value']:g['value'] + g['size']], name)
            relative = lambda o, f: {a - f['value']: v for a, v in o[2].items() if f['value'] <= a < f['value'] + f['size']}
            self.assertEqual(relative(old, f), relative(new, g), name)
        self.assertEqual(sections(self.obj)['.rodata'][1], source.POOL)
        self.assertEqual(sections(old_obj)['.rodata'][1], source.previous.POOL)
        self.assertEqual(self.rom[0x24BA64:0x24BA80], source.POOL[:28])
        self.assertNotIn((',' + source.FUNCTION + ',').encode(), (self.out / 'before-guards').read_bytes())
        data, functions = source.build.link_owner(self.root, self.out, self.obj, source.OWNER)
        address, pool = sections(self.obj.with_suffix('.elf'))['.rodata']
        raw_words = list(struct.unpack_from('>256I', data, functions[source.FUNCTION]['value']))
        for mode in range(6):
            m, a = guest.fixture(self.rom, 3)
            m.update({address+i: b for i, b in enumerate(pool)})
            model = guest.BurstOracle(raw_words, m, a, mode=mode).run()
            self.assertEqual((model.calls, model.full_packets), guest.reference(m, a, mode))
        bad = self.out / 'wrong-alias.s'
        bad.write_text(emit_padded_assembly(self.obj, self.root / source.PATHS['edge_wrapper_original'], filename=source.OWNER,
            word_patches_path=self.out / 'before-guards', rodata_symbol='D_800A6FA8'))
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(bad.with_suffix('.o')), str(bad)], check=True, capture_output=True)
        data, functions = source.build.link_owner(self.root, self.out, bad.with_suffix('.o'), source.OWNER)
        wrong = list(struct.unpack_from('>256I', data, functions[source.FUNCTION]['value']))
        m, a = guest.fixture(self.rom, 1)
        guest.put(m, 0x800A6FC0, guest.bits(1.0))
        model = guest.BurstOracle(wrong, m, a).run()
        self.assertNotEqual(model.full_packets, guest.reference(m, a)[1])
        self.receipt('shape', words=256, frame=224, packet=124, neighbors=8, target_guards=0,
            literal_pool_bytes=32, retail_literal_bytes=28, padding_not_emitted=4,
            own_raw_literal_pool_cases=6, wrong_alias_effective=True)

    def test_02_whole_sequences_widths_count_and_live_packet_lifetimes(self):
        visits, cases = set(), 0
        for count, kind, mode, rotation, phase in itertools.product((-3, 0, 1, 4),
                (0, 0xCB, 0x800001CB, 0xFFFFFFFF), range(6), (0, 5), (0, 8)):
            m, a = guest.fixture(self.rom, count, kind)
            models = self.compare(m, a, mode, rotation, phase)
            if count <= 0:
                reads = {e[1] for e in models[0].events if e[0] == 'R'}
                self.assertTrue(reads.isdisjoint({guest.STACK+phase+n for n in (8, 12, 16, 51, 52)}))
            visits.update(models[0].visits)
            cases += 1
        # Masked low halves cannot enter the compiler's unsigned-negative repair arms.
        missed = sorted(source.ENTRY + 4*i for i in range(256) if source.ENTRY + 4*i not in visits)
        self.receipt('sequences', paired_cases=cases, all_96_packet_bytes=True, visits=len(visits),
            not_visited=[hex(a) for a in missed], unsigned_correction_and_conversion_paths_not_claimed=True)

    def test_03_duration_word_conversion_and_fcsr_restore(self):
        cases, outcomes = 0, []
        for minimum in (0.0, 20.0, 100.0, 107374184.0, 214748368.0, -10.0, float('inf'), float('nan')):
            for fcsr in (0, 4, 0x800000):
                m, a = guest.fixture(self.rom, 1, minimum=minimum, maximum=minimum)
                models = self.compare(m, a, fcsr=fcsr)
                outcomes.append(models[0].full_packets[0][0x59])
                cases += 1
        self.assertIn(255, outcomes)
        self.receipt('conversion', guest_cases=cases, final_bytes=outcomes,
            FCSR_truncation_control_restore=True, not_full_hardware_FP_flags=True,
            native_special_float_to_integer_cases_excluded=True)

    def test_04_effective_compiled_semantic_negatives(self):
        evidence = []
        for name, body in controls().items():
            self.assertNotEqual(body, source.SELECTED)
            obj, words, row = source.measure(self.root, self.out, 'negative-' + name, body)
            address, pool = sections(obj.with_suffix('.elf'))['.rodata'] if row['words'] > 256 else (0, b'')
            rejected = False
            for mode in (0, 2, 3, 4):
                m, a = guest.fixture(self.rom, 3)
                m.update({address+i: b for i, b in enumerate(pool)})
                expected_calls, expected_packets = guest.reference(m, a, mode)
                try:
                    model = guest.BurstOracle(words, m, a, mode=mode).run()
                    observed = model.calls, [guest.prior.initialized(p) for p in model.full_packets]
                    wanted = expected_calls, [guest.prior.initialized(p) for p in expected_packets]
                    rejected = observed != wanted
                    if mode in (2, 3, 4):
                        rejected |= model.full_packets[1:] != expected_packets[1:]
                except (AssertionError, KeyError):
                    rejected = True
                if rejected:
                    break
            self.assertTrue(rejected, name)
            evidence.append(dict(name=name, raw_sha256=row['raw_sha256'], effective=True))
        self.receipt('negatives', compiled=evidence)

    def test_05_native32_separate_units_O2_O0_UBSan_and_negatives(self):
        harness = self.out / 'native-harness.c'
        harness.write_text(native.fixtures(self.rom, self.owner))
        exits = {}
        for name, body, profile, valid in [('O2', source.SELECTED, '-O2', True), ('O0', source.SELECTED, '-O0', True)] + [
                ('negative-' + n, b, '-O2', False) for n, b in controls().items()]:
            path = self.out / ('native-' + name + '.c')
            path.write_text(native.declarations(self.owner) + body)
            command = ['cc', '-m32', profile, '-std=c11', '-fno-strict-aliasing', '-msse2', '-mfpmath=sse', '-mstackrealign',
                '-ffp-contract=off', '-ffreestanding', '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector',
                '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation']
            command += ['-fsanitize=undefined', '-fsanitize-undefined-trap-on-error'] if valid else ['-Wno-unused-but-set-variable']
            built = subprocess.run([*command, str(path), str(harness), '-o', str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr[:2000])
            result = subprocess.run([str(path.with_suffix(''))], timeout=60)
            self.assertIn(result.returncode, (0,) if valid else tuple(range(20, 26)), name)
            exits[name] = result.returncode
        self.receipt('native', cases_per_O2_O0=512, selected_UBSan=True, separate_units=True, exits=exits,
            all_90_initialized_bytes_and_provider_seeded_holes=True, initial_indeterminate_bytes_excluded=True)

    def test_06_every_raw_word_binding_pool_and_alias_corruption(self):
        text, funcs, rel = parse_object(self.obj)
        f = funcs[source.FUNCTION]
        for i in range(256):
            bad = bytearray(text)
            bad[f['value']+i*4] ^= 1
            with patch.object(source, 'parse_object', return_value=(bytes(bad), funcs, rel)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        for at in source.RELOCATIONS:
            bad = dict(rel)
            bad[f['value']+at] = [(rel[f['value']+at][0][0], 'wrong_binding')]
            with patch.object(source, 'parse_object', return_value=(text, funcs, bad)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        pools = sections(self.obj)
        for i in range(len(source.POOL)):
            bad = bytearray(source.POOL)
            bad[i] ^= 1
            with patch.object(source, 'sections', return_value=dict(pools, **{'.rodata': (0, bytes(bad))})):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        self.receipt('corruptions', raw_words=256, bindings=len(source.RELOCATIONS), pool_bytes=32)

    def test_07_fired_literal_fault_prefixes(self):
        cases = 0
        for phase in (0, 8):
            m, a = guest.fixture(self.rom, 1)
            complete = guest.BurstOracle(self.words, m, a, phase=phase).run()
            for fault in range(complete.accesses):
                models = []
                for words in (self.words, self.truth):
                    model = guest.BurstOracle(words, m, a, phase=phase, fault=fault)
                    with self.assertRaises(guest.prior.edge.AccessFault):
                        model.run()
                    models.append(model)
                self.assertEqual(guest.prior.prior.literal(models[0]), guest.prior.prior.literal(models[1]))
                cases += 1
        self.receipt('faults', fired_literal_prefix_pairs=cases, not_portable_C_fault_or_FP_proof=True)

    def test_08_preinstall_full_prediction_and_frozen_inputs(self):
        row = source.prelink_prediction(self.root, self.out)
        self.assertEqual((row['slot_changes'], row['additional_serialization_bytes']), (793, 0))
        expected = source.expected_inputs(self.root, self.out)
        hashes = {k: hashlib.sha256(v).hexdigest() for k, v in expected.items()}
        self.assertEqual(json.loads((self.out / 'initial-prediction.json').read_text()), hashes)
        live = {k: hashlib.sha256((self.root / p).read_bytes()).hexdigest() for k, p in source.PATHS.items()}
        self.assertIn(live, (source.BASELINE, dict(source.BASELINE, **hashes)))
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
        self.receipt('scope', frozen_inputs=len(source.PATHS), predictions=hashes, metadata_exclusions=0)

    def test_09_independently_assembled_original_rebases(self):
        original = (self.out / 'before-edge_wrapper_original').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1].split('endlabel ' + source.FUNCTION, 1)[0]
        path = self.out / 'original-rebase.s'
        path.write_text('.include "' + str(self.root / 'conker/include/asm_processor_prelude.inc') + '"\n.type ' +
            source.FUNCTION + ', @function\nglabel ' + source.FUNCTION + '\n' + original + '\n.size ' + source.FUNCTION + ', . - ' + source.FUNCTION + '\n')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')), str(path)], check=True, capture_output=True)
        text, funcs, rel = parse_object(path.with_suffix('.o'))
        f = funcs[source.FUNCTION]
        original_raw = text[f['value']:f['value'] + f['size']]
        original_rel = {at-f['value']: rows for at, rows in rel.items() if f['value'] <= at < f['value'] + f['size']}
        raw, bindings = source.checked_object(self.obj)
        cases = 0
        for entry, delta, call_delta in ((0x15201000, 0x1000, 0x2000), (0x15302000, 0x2100, 0x4000), (0x15403000, 0x4100, 0x6000)):
            calls = dict(func_150ADA20=source.RANDOM+call_delta, func_1518C900=source.LOOKUP+call_delta, func_15168BE4=source.SUBMIT+call_delta)
            links = dict(calls, **{'D_%08X' % a: a+delta for a in range(0x800A6FA4, 0x800A6FC0, 4)})
            aliased = {at: [(k, source.POOL_ANCHOR if n == '.rodata' else n) for k, n in rows] for at, rows in bindings.items()}
            streams = []
            for i, (data, rows) in enumerate(((raw, aliased), (original_raw, original_rel))):
                asm, missing = emit_function(data, dict(value=0, size=len(data)), rows, source.FUNCTION, links)
                self.assertFalse(missing)
                file = self.out / ('rebase-%X-%d.s' % (entry, i))
                file.write_text(asm)
                file.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(file.with_suffix('.o')), str(file)], check=True, capture_output=True)
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(file.with_suffix('.ld')), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in links.items()], '-o', str(file.with_suffix('.elf')), str(file.with_suffix('.o'))], check=True, capture_output=True)
                streams.append(list(struct.unpack_from('>256I', sections(file.with_suffix('.elf'))['.text'][1])))
            self.assertEqual(streams[0], streams[1])
            for phase, mode, rotation in itertools.product((0, 8), (0, 2, 3, 4), (0, 5)):
                initial, args = guest.fixture(self.rom, 3)
                memory = {a+delta if 0x800A6FA4 <= a < 0x800A6FC0 else a: b for a, b in initial.items()}
                models = [guest.BurstOracle(words, memory, args, phase=phase, mode=mode, rotation=rotation, entry=entry,
                    bindings={links[n]: old for n, old in zip(calls, (source.RANDOM, source.LOOKUP, source.SUBMIT))}).run() for words in streams]
                self.assertEqual((models[0].calls, models[0].full_packets), guest.reference(initial, args, mode, rotation, phase))
                self.assertEqual(guest.prior.prior.literal(models[0]), guest.prior.prior.literal(models[1]))
                cases += 1
        self.receipt('rebases', independently_assembled_sets=3, paired_cases=cases, all_calls_constants_and_signed_low_carries=True)

    def test_10_three_original_caller_windows_and_current_stub_limit(self):
        class StopCaller(guest.BurstOracle):
            def record_call(self, target):
                if target == source.ENTRY:
                    self.forwarded = self.arguments(14)
                    raise guest.prior.edge.CallBoundary
                return super().record_call(target)
        actor, cases = 0x20000, 0
        image = (self.out / 'before-elf').read_bytes()
        symbols = load_elf_functions(str(self.root / source.PATHS['elf']), 'mips-linux-gnu-objdump')[0]
        self.assertEqual(symbols['func_15169C70'][:3], [0x00001025, 0x03E00008, 0])
        self.assertFalse(any(symbols['func_15169C70'][3:]))
        constants = self.rom[0x24B77C:0x24B788]
        for entry, rom, end, count, kind, variant, lifetime, spread, coef in (
                (0x15169E5C, 0x19730C, 0x15169ED4, 4, 11, 2, 255, 60.0, 0xBECCCCCD),
                (0x15169FE0, 0x197490, 0x1516A058, 3, 11, 2, 60, 40.0, guest.bits(-0.5)),
                (0x1516A07C, 0x19752C, 0x1516A0F0, 2, 203, 5, 60, 60.0, 0xBF333333)):
            data = self.rom[rom:rom+end-entry]
            self.assertEqual(image[elf_slot_offset(image, entry, len(data)):][:len(data)], bytes(len(data)))
            for phase in (0, 8):
                memory, _ = guest.fixture(self.rom)
                memory.update({actor+i: 0xA5 for i in range(256)})
                memory.update({0x800A6CBC+i: b for i, b in enumerate(constants)})
                for at, val in ((0x90, 1.25), (0x94, -2.5), (0x98, 3.75), (0xAC, -8.0), (0xDC, 0.25)):
                    guest.put(memory, actor+at, guest.bits(val))
                guest.put(memory, actor+1, 0xFE, 1)
                guest.put(memory, actor+12, 0x81, 1)
                model = StopCaller(list(struct.unpack('>%dI' % (len(data)//4), data)), memory, (0,)*14, phase=phase, entry=entry)
                model.r[16], model.r[15], model.r[9], model.r[13] = actor, 2, 2, 5
                with self.assertRaises(guest.prior.edge.CallBoundary):
                    model.run()
                expected = (count, kind, guest.bits(1.25), guest.bits(-2.5), guest.bits(3.75), guest.bits(6.0 if count == 2 else -2.0),
                    guest.bits(0.5), 0x3F333333 if count == 3 else guest.bits(1.0), guest.bits(spread), variant, lifetime, coef, 0x81, 0xFE)
                self.assertEqual(model.forwarded, expected)
                cases += 1
        self.receipt('caller', original_captures=cases, caller='func_15169C70', args=14,
            current_caller_is_placeholder=True, current_windows_zero_filled=True, no_gameplay_acceptance=True)

    def test_11_actual_consumer_allocator_and_full_packet_copy(self):
        lower = guest.prior.prior
        image, connected = (self.out / 'before-elf').read_bytes(), {}
        for address, rom, size in ((source.SUBMIT, 0x196094, 104), (lower.ALLOCATOR, 0x194F18, 112)):
            data = image[elf_slot_offset(image, address, size):][:size]
            self.assertEqual(data, self.rom[rom:rom+size])
            connected.update(zip(range(address, address+size, 4), struct.unpack('>%dI' % (size//4), data)))
        cases = 0
        for phase, mode, fail in itertools.product((0, 8), (0, 6), (False, True)):
            memory, args = guest.fixture(self.rom, 4)
            memory.update({0x30000+i: 0xA5 for i in range(4*0x100)})
            for words in (self.truth, self.words):
                model = guest.BurstOracle(words, memory, args, phase=phase, mode=mode, connected=connected, fail=fail).run()
                calls, packets = guest.reference(memory, args, mode, phase=phase)
                copies = [(0x30090+i*0x100, p) for i, p in enumerate(packets)
                    if struct.unpack_from('>I', p, 0x40)[0] and not (fail and (i+1)%3 == 0)]
                self.assertEqual((model.calls, model.full_packets, model.copies), (calls, packets, copies))
                cases += 1
        self.receipt('connected', runs=cases, actual_consumer_allocator_words=54, full_96_byte_copies=True,
            zero_asset_and_every_third_allocation_failure=True, RNG_lookup_heap_registration_bcopy_bounded=True)


if __name__ == '__main__':
    unittest.main()
