"""Bounded semantic recovery; the 148-word candidate is not installation-qualified."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path

from tools.experiments import game_object_color_mode_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_owner_metadata_adapter_match import AdapterOracle, COS
from tools.tests import test_game_owner_metadata_adapter_match as adapter
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests.test_game_owner_actor_update_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_record_constructor_match import elf_slot_offset

OBJECT, OUTPUT, FLOAT = 0x22000, 0x24000, 0x25000
TABLE = 0x80096F1C
ARGUMENTS = (OBJECT, OUTPUT, OUTPUT + 4, OUTPUT + 8, OUTPUT + 12)


def public(memory):
    return {a: b for a, b in memory.items() if OBJECT <= a < FLOAT + 4}


def fixture(mode=1, packed=0x40802010, phase=37, blend=71, value=10.25):
    memory = {STACK + i: 0xA5 for i in range(-0x600, 0x140)}
    for base, size in ((OBJECT, 0x180), (OUTPUT, 80), (FLOAT, 4)):
        memory.update({base + i: (i * 17 + 0x35) & 255 for i in range(size)})
    put(memory, OBJECT + 0xA0, packed)
    memory[OBJECT + 0xA4] = mode
    memory[OBJECT + 0xA5], memory[OBJECT + 0xA6], memory[OBJECT + 0xA7] = phase, 52, blend
    put(memory, FLOAT, bits(value))
    return memory


def reference(memory, arguments=ARGUMENTS, cosine=0.5):
    result, events, calls = memory.copy(), [], []
    object_address, red, green, blue, opacity = arguments
    def get(address, size=4):
        value = read(result, address, size)
        events.append(('R', address, size, value))
        return value
    def store(address, value):
        put(result, address, value)
        events.append(('W', address, 4, value & 0xFFFFFFFF))
    mode = get(object_address + 0xA4, 1)
    if mode == 1:
        for output, offset in ((red, 0xA5), (green, 0xA6), (blue, 0xA7)):
            store(output, get(object_address + offset, 1))
        value = get(object_address + 0xA0)
        if value >= 256:
            amount = floating(get(value))
            amount = 0.0 if amount < 0 else 255.0 if amount > 255 else amount
            value = int(floating(bits(amount * floating(0x40233333))))
        store(opacity, value)
    elif mode in (2, 3):
        for output in (red, green, blue): store(output, 0)
        value = get(object_address + 0xA5, 1)
        store(opacity, value)
        if get(object_address + 0xA4, 1) == 3: store(opacity, 255 - value)
    elif mode in (4, 5, 6, 7):
        value = get(object_address + 0xA0)
        high = value >> 24 & 255
        store(red, value >> 16 & 255)
        store(green, get(object_address + 0xA0) >> 8 & 255)
        store(blue, get(object_address + 0xA0) & 255)
        phase = get(object_address + 0xA5, 1)
        if mode in (4, 5):
            calls.append((COS, bits(phase * floating(0x3CC90FDB))))
            amount = floating(bits(cosine + 1.0))
            amount = floating(bits(amount * 0.5))
            amount = floating(bits(64.0 * amount))
            value = int(floating(bits(float(high) + amount)))
            store(opacity, value)
            blend = get(object_address + 0xA7, 1)
            store(opacity, value + (signed((255 - value) * (255 - blend) & 0xFFFFFFFF) >> 8))
        else:
            store(opacity, 255 - ((phase * high) >> 8))
    return public(result), events, calls


class ModeOracle(AdapterOracle):
    def __init__(self, words, memory, arguments=ARGUMENTS, phase=0, cosine=0.5, entry=screen.ENTRY):
        TriangleOracle.__init__(self, words, memory, arguments=arguments, phase=phase, entry=entry)
        self.cosine = bits(cosine)
    def record_call(self, target):
        assert target == COS
        self.calls.append((target, self.f[12]))
    def hook(self, target):
        assert target == COS
        for register in (1, 2, 3, *range(4, 16), 24, 25): self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.f[0] = self.cosine


class GameObjectColorModeRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-object-color-mode-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = (screen.SOURCE, 'conker/build/conker.us.elf', 'conker/retail_word_patches.us.csv',
            'conker/progress.csv', 'conker/asm/data/23B8A0.rodata.s')
        baseline = cls.out / 'baseline.json'
        if not baseline.exists():
            hashes = {}
            for i, name in enumerate(cls.paths):
                data = (cls.root / name).read_bytes()
                (cls.out / ('before-%d' % i)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            baseline.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads(baseline.read_text())
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.pools = sections(cls.out / 'selected.elf')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>150I', cls.rom, screen.ROM))
        cls.table = struct.unpack_from('>7I', cls.rom, 0x23B9DC)

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def run_body(self, memory, words=None, pools=None, arguments=ARGUMENTS, phase=0, cosine=0.5, oracle=ModeOracle):
        memory = memory.copy()
        if words is None:
            words = self.retail
            for i, word in enumerate(self.table): put(memory, TABLE + i * 4, word)
        else:
            for name, (address, data) in (pools or self.pools).items():
                if name == '.rodata': memory.update({address + i: value for i, value in enumerate(data)})
        for symbol, value in ((0x80096F38, 0x40233333), (0x80096F3C, 0x3CC90FDB)):
            put(memory, symbol, value)
        return oracle(words, memory, arguments, phase, cosine).run()

    def compare(self, memory, arguments=ARGUMENTS, phase=0, cosine=0.5):
        expected = reference(memory, arguments, cosine)
        models = (self.run_body(memory, arguments=arguments, phase=phase, cosine=cosine),
            self.run_body(memory, self.words, arguments=arguments, phase=phase, cosine=cosine))
        for model in models:
            events = [event for event in model.events if OBJECT <= event[1] < FLOAT + 4]
            self.assertEqual((public(model.memory), events, model.calls), expected)
        return models

    def test_01_complete_modes_values_aliases_and_ordered_public_accesses(self):
        cases, coverage = 0, [set(), set()]
        for mode, phase, cosine in itertools.product(range(256), (0, 8), (-1.0, 1.0)):
            memory = fixture(mode, packed=FLOAT if mode == 1 else 0xFF802010)
            for hits, model in zip(coverage, self.compare(memory, phase=phase, cosine=cosine)):
                hits.update(model.visits)
            cases += 1
        for direct in range(256):
            self.compare(fixture(packed=direct))
            cases += 1
        for value in (-100.0, -0.0, 0.0, 0.25, 10.25, 100.0, 254.9, 255.0, 300.0):
            self.compare(fixture(packed=FLOAT, value=value))
            cases += 1
        aliases = []
        for index in range(1, 5):
            for target in (OUTPUT, OBJECT + 0xA0, OBJECT + 0xA4, OBJECT + 0xA8):
                args = list(ARGUMENTS)
                args[index] = target
                aliases.append(tuple(args))
        aliases.append((OBJECT, OUTPUT, OUTPUT, OUTPUT, OUTPUT))
        for mode, args, cosine in itertools.product(range(8), aliases, (-1.0, 0.5, 1.0)):
            self.compare(fixture(mode, packed=83 if mode == 1 else 0xFF802010), args, cosine=cosine)
            cases += 1
        self.receipt('guest', cases=cases, executions=cases * 2, all_256_modes=True,
            public_memory_and_ordered_accesses_equal=True, retail_words_reached=len(coverage[0]),
            raw_words_reached=len(coverage[1]), bounded_cosine_not_actual_trig_or_FCSR=True)

    def test_02_effective_compiled_semantic_negatives(self):
        forms = dict(screen.candidates())
        controls = (
            ('negative-cache-mode', fixture(3), (*ARGUMENTS[:4], OBJECT + 0xA4)),
            ('negative-cache-word', fixture(6), (OBJECT, OBJECT + 0xA0, *ARGUMENTS[2:])),
            ('negative-byte-opacity', fixture(1, packed=FLOAT, value=300.0), ARGUMENTS),
            ('negative-unsigned-product', fixture(5, packed=0xFF802010), ARGUMENTS))
        records = []
        for name, memory, args in controls:
            meta, words = screen.compile_candidate(self.root, self.out, name, forms[name])
            model = self.run_body(memory, words, sections(self.out / (name + '.elf')), args, cosine=1.0)
            self.assertNotEqual(public(model.memory), reference(memory, args, 1.0)[0], name)
            records.append(meta)
        self.receipt('negatives', complete_compiled_controls=4, effective=4, measurements=records)

    def test_03_physical_homes_and_explicit_installation_rejection(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['diagnostics']), (148, 40, ''))
        text, functions, relocations = parse_object(self.out / 'selected.o')
        self.assertEqual(functions[screen.FUNCTION]['size'], 592)
        raw = struct.unpack_from('>148I', text)
        self.assertEqual(raw[0], 0x27BDFFD8)
        self.assertIn(0xAFA40028, raw)
        self.assertIn(0x8FA40028, raw)
        stores = [word & 65535 for word in raw if word >> 26 == 43 and word >> 21 & 31 == 29]
        self.assertEqual(stores, [0x14, 0x1C, 0x28])
        for mode in (4, 5):
            original, candidate = self.compare(fixture(mode))
            self.assertEqual({a: original.memory[a] for a in fixture(mode)},
                {a: candidate.memory[a] for a in fixture(mode)})
            stack = lambda model: [event for event in model.events if event[0] == 'W' and STACK - 40 <= event[1] <= STACK + 16]
            self.assertEqual(stack(original), stack(candidate))
        table = struct.unpack_from('>7I', self.pools['.rodata'][1])
        expected = tuple(address - screen.ENTRY for address in self.table)
        actual = tuple(address - screen.ENTRY for address in table)
        self.assertEqual(expected, (48, 208, 208, 264, 264, 496, 496))
        self.assertNotEqual(actual, expected)
        self.assertEqual(actual[:5], expected[:5])
        self.assertEqual(actual[5:], (492, 492))
        self.assertEqual(relocations[0x1C], [('R_MIPS_HI16', '.rodata')])
        self.assertEqual(relocations[0x24], [('R_MIPS_LO16', '.rodata')])
        self.receipt('shape', raw_words=148, retail_words=150, frame=40,
            raw_differences=self.meta['differences'], private_store_homes=stores,
            retail_table_offsets=expected, candidate_table_offsets=actual,
            installation_rejected=True, reason='mode6/7 case offset differs; unqualified pool anchor/addend',
            inserted_or_omitted_words=0, guards_added=0)

    def test_04_actual_copied_owner_neighbors_and_pool_boundary(self):
        before = (self.out / 'before-0').read_text()
        original = 's32 func_1502EC34() {\n    return 0;\n}'
        self.assertEqual(before.count(original), 1)
        after = before.replace(original, screen.SELECTED).replace('#include <ultra64.h>',
            '#include <ultra64.h>\n' + screen.DECLARATIONS, 1)
        objects, diagnostics = [], []
        for name, body in (('owner-before', before), ('owner-after', after)):
            obj, warnings = compile_owner(self.root, self.out, body, name)
            subprocess.run(['python3', str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / (name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(obj.relative_to(self.root / 'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker',
                check=True, capture_output=True)
            objects.append(obj)
            diagnostics.append(warnings)
        self.assertEqual(diagnostics[0], diagnostics[1])
        old, of, orels = parse_object(objects[0])
        new, nf, nrels = parse_object(objects[1])
        self.assertEqual(of.keys(), nf.keys())
        relative = lambda rs, f: {o - f['value']: r for o, r in rs.items() if f['value'] <= o < f['value'] + f['size']}
        for name, f in nf.items():
            if name == screen.FUNCTION: continue
            prior = of[name]
            self.assertEqual((f['size'], new[f['value']:f['value'] + f['size']], relative(nrels, f)),
                (prior['size'], old[prior['value']:prior['value'] + prior['size']], relative(orels, prior)), name)
        raw = parse_object(self.out / 'selected.o')[0]
        f = nf[screen.FUNCTION]
        # Pool addends differ in a real owner; do not replace them with isolated offsets.
        self.assertEqual(f['size'], len(raw))
        pool_before, pool_after = sections(objects[0])['.rodata'][1], sections(objects[1])['.rodata'][1]
        self.assertEqual(pool_after[:len(pool_before)], pool_before)
        self.assertEqual(len(pool_after) - len(pool_before), 32)
        output = emit_padded_assembly(objects[1], self.root / 'conker/asm/58F80.s',
            word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_58F80',
            rodata_symbol='jtbl_80096DF8_game')
        self.assertIn('jtbl_80096DF8_game', output)
        self.assertNotEqual(new[f['value']:f['value'] + f['size']], raw)
        padded = []
        for index, obj in enumerate(objects):
            path = self.out / ('padded-%d.s' % index)
            path.write_text(emit_padded_assembly(obj, self.root / 'conker/asm/58F80.s',
                word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_58F80',
                rodata_symbol='jtbl_80096DF8_game'))
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(path.with_suffix('.o')),
                str(path)], check=True, capture_output=True)
            padded.append(parse_object(path.with_suffix('.o')))
        target = padded[1][1][screen.FUNCTION]
        start = target['value']
        self.assertEqual(padded[0][0][:start], padded[1][0][:start])
        self.assertEqual(padded[0][0][start + 600:], padded[1][0][start + 600:])
        owner_addend = struct.unpack_from('>I', new, f['value'] + 0x24)[0] & 65535
        expected_addend = TABLE - 0x80096DF8
        self.assertNotEqual(owner_addend, expected_addend)
        self.receipt('owner', neighbors=len(nf) - 1, existing_warnings=len(diagnostics[0]), new_warnings=0,
            all_neighbor_bytes_and_relative_relocations_equal=True, existing_pool_prefix_equal=True,
            new_pool_bytes=32, actual_padder_does_not_validate_case_target_contents=True,
            all_other_padded_owner_bytes_equal=True, compiled_owner_table_addend=owner_addend,
            required_retail_anchor_addend=expected_addend, installation_not_qualified=True)

    def test_05_production_baseline_and_protected_data_unchanged(self):
        self.assertEqual({name: hashlib.sha256((self.root / name).read_bytes()).hexdigest() for name in self.paths},
            self.baseline)
        self.assertIn('s32 func_1502EC34() {\n    return 0;\n}', (self.root / screen.SOURCE).read_text())
        audit = audit_layout(self.root / 'conker/build/conker.us.elf', self.root / 'conker')
        self.receipt('production', hashes=self.baseline, source_not_installed=True,
            no_guard_rows_added=True, protected_data_audit=audit)

    def test_06_every_public_access_fault_prefix_and_lazy_no_output_modes(self):
        cases = 0
        for mode in range(1, 8):
            memory = fixture(mode, packed=FLOAT if mode == 1 else 0xFF802010)
            _, events, _ = reference(memory)
            for cut in range(len(events)):
                class FaultOracle(ModeOracle):
                    def __init__(self, *args):
                        super().__init__(*args)
                        self.public_accesses = 0
                        self.failed = False
                    def access(self, address):
                        if OBJECT <= address < FLOAT + 4:
                            if self.public_accesses == cut:
                                self.failed = True
                                raise RuntimeError('public access fault')
                            self.public_accesses += 1
                    def get(self, address, size):
                        self.access(address)
                        return super().get(address, size)
                    def put(self, address, value, size):
                        if self.recording: self.access(address)
                        return super().put(address, value, size)
                    def run(self):
                        try:
                            super().run()
                        except RuntimeError:
                            return self
                        raise AssertionError('fault gate did not fire')
                expected_memory = memory.copy()
                for kind, address, size, value in events[:cut]:
                    if kind == 'W': put(expected_memory, address, value, size)
                for words in (None, self.words):
                    model = self.run_body(memory, words, oracle=FaultOracle)
                    self.assertTrue(model.failed)
                    self.assertEqual(public(model.memory), public(expected_memory))
                    self.assertEqual([event for event in model.events if OBJECT <= event[1] < FLOAT + 4], events[:cut])
                cases += 1
        for mode in (0, 8, 127, 255):
            args = (OBJECT, 1, 3, 5, 7)
            self.compare(fixture(mode), args)
        self.receipt('faults', public_access_prefixes=cases, executions=cases * 2,
            lazy_invalid_output_pointer_cases=4, fault_gate_verified=True)

    def test_07_actual_compiled_helper_connected_to_banked_adapter(self):
        elf = (self.root / 'conker/build/conker.us.elf').read_bytes()
        adapter_words = struct.unpack_from('>89I', elf, elf_slot_offset(elf, adapter.screen.ENTRY, 356))
        default_words = struct.unpack_from('>34I', elf, elf_slot_offset(elf, adapter.DEFAULT, 136))
        self.assertEqual(adapter_words, struct.unpack_from('>89I', self.rom, adapter.screen.ROM))
        self.assertEqual(default_words, struct.unpack_from('>34I', self.rom, 0x1E1E3C))
        cases = 0
        for mode, packed, phase, cosine in itertools.product(range(8), (83, 0xFF802010, FLOAT),
                (0, 8), (-1.0, 0.5, 1.0)):
            memory = adapter.fixture(mode)
            memory.update(fixture(mode, packed=FLOAT if mode == 1 and packed >= 256 else packed))
            outcomes = []
            for helper_words, pools in ((self.retail, None), (self.words, self.pools)):
                data = memory.copy()
                if pools is None:
                    for i, word in enumerate(self.table): put(data, TABLE + i * 4, word)
                else:
                    address, pool = pools['.rodata']
                    data.update({address + i: value for i, value in enumerate(pool)})
                put(data, 0x80096F38, 0x40233333)
                put(data, 0x80096F3C, 0x3CC90FDB)
                connected = dict(zip(range(screen.ENTRY, screen.ENTRY + len(helper_words) * 4, 4), helper_words))
                connected.update(zip(range(adapter.DEFAULT, adapter.DEFAULT + 136, 4), default_words))
                model = AdapterOracle(adapter_words, data, phase=phase, connected=connected, cosine=bits(cosine)).run()
                outcomes.append(({a: model.memory[a] for a in memory}, model.calls, model.r[2]))
                self.assertTrue(any(screen.ENTRY <= address < screen.ENTRY + len(helper_words) * 4 for address in model.visits))
            # Register and instruction scheduling can reorder independent private loads.
            self.assertEqual(outcomes[0][0], outcomes[1][0])
            self.assertEqual(outcomes[0][1:], outcomes[1][1:])
            cases += 1
        self.receipt('connected', cases=cases, executions=cases * 2, banked_linked_adapter_words=89,
            banked_linked_default_words=34, actual_compiled_helper_words=148,
            complete_input_memory_and_nested_calls_equal=True, production_helper_still_stub=True)


if __name__ == '__main__':
    unittest.main()
