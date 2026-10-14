"""Complete guarded emitter, real factory/copies and closed production boundaries."""
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_effect_packet_candidates as source
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import test_game_actor_burst_packet_match as producer
from tools.tests import test_game_actor_burst_consumer_recovery as arithmetic
from tools.tests.test_game_actor_burst_consumer_match import TrackedCode, AccessBoundary
from tools.tests import test_game_actor_burst_consumer_match as consumer
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.game_animation_timeline_oracle import bits, signed
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_record_constructor_match as image
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools import pad_c_object
from tools.check_game_data_layout import audit_layout

STACK, ACTOR, CREATED = producer.STACK, 0x21000, 0x25000
FLOAT, RNG, EFFECT, ALLOCATOR, MEMCPY = 0x150ADA68, 0x150ADA20, 0x151A26EC, 0x15130374, 0x10022EC0
GLOBALS = ('D_800BE9A8', 'D_800A8DC8', 'D_800A8DCC', 'D_800A8DD0')
COEFFICIENTS = (bits(0.5), 0x3A83126F, 0x4413C000, 0x3A83126F)
ARGS = tuple(map(bits, (1.5, -2.5, 3.5, 2., -4., 8.))) + (ACTOR,)
BASELINE_ELF = '205c023e2ffa29a90d7204bb8eb260989590a4ea30f268e916cd252f88d21708'


def expected_effect_image(before, words):
    expected = bytearray(before)
    offset = image.elf_slot_offset(before, source.ENTRY, 432)
    expected[offset:offset + 432] = struct.pack('>108I', *words)
    with patch.object(image.screen, 'ENTRY', source.ENTRY):
        size = image.elf_symbol_size_offset(before, source.FUNCTION)
    if struct.unpack_from('>I', before, size)[0] != 12:
        raise ValueError('Expected original 12-byte emitter symbol')
    struct.pack_into('>I', expected, size, 432)
    return bytes(expected)


def csv_rows(rows):
    stream = io.StringIO(newline='')
    csv.DictWriter(stream, fieldnames=tuple(rows[0]), lineterminator='\n').writerows(rows)
    return stream.getvalue()


def installed_guards(before):
    owned = {offset: [('R_MIPS_LO16', 'D_800BE9A8')] for offset, _, _ in source.GUARDS if offset == 0x34}
    words = [0] * 108
    words[0] = 0x27BDFF68
    for offset, expected, _ in source.GUARDS:
        words[offset // 4] = expected
    return before + csv_rows(source.guard_rows(words, owned)).encode('ascii')


def fixture(args=ARGS, symbols=None, phase=0, seed=0):
    symbols = symbols or source.SYMBOLS
    m = {STACK + i: (i * 17 + seed * 31 + 0xA5) & 255 for i in range(-0x600, 0x180)}
    for base, size in ((args[6] - 32, 0x240), (CREATED - 32, 0x300)):
        m.update({base + i: (i * 13 + seed * 11 + 0xA5) & 255 for i in range(size)})
    for name, value in zip(GLOBALS, COEFFICIENTS):
        m.update({symbols[name] + i: 0xA5 for i in range(4)})
        put(m, symbols[name], value)
    put(m, args[6] + 0x40, bits(1.25))
    put(m, args[6] + 0xC, 255, 1)
    put(m, args[6] + 1, 128, 1)
    for index, value in enumerate(args[2:]):
        put(m, STACK + phase + 8 + index * 4, value)
    return m


def mutations(role, index, mode, actor, incoming, symbols):
    if role == FLOAT and index == 0 and mode in (1, 3):
        changes = ((actor + 0x40, bits(4.), 4), (symbols[GLOBALS[0]], bits(2.), 4),
            (symbols[GLOBALS[1]], bits(0.0078125), 4))
        if mode == 3:
            changes += tuple((incoming + 0xC + i * 4, bits(v), 4) for i, v in enumerate((5., 6., -7.)))
        return changes
    if role == RNG and index == 1 and mode == 2:
        return ((symbols[GLOBALS[2]], bits(800.), 4), (symbols[GLOBALS[3]], bits(0.001953125), 4),
            (actor + 0xC, 129, 1), (actor + 1, 254, 1), (actor + 0x40, bits(8.), 4))
    return ()


def reference(memory, args=ARGS, floats=None, integers=(0, 0xFFFFFFFF), mode=0, phase=0, symbols=None):
    s, m = symbols or source.SYMBOLS, dict(memory)
    floats = floats or tuple(map(bits, (0.25, 0.5, 0.75)))
    actor, incoming = args[6], STACK + phase
    calls = []
    retained = read(m, actor + 0x40)
    for i, value in enumerate(args[2:]):
        put(m, incoming + 8 + i * 4, value)
    def callback(role, index):
        calls.append((role, ()))
        for address, value, size in mutations(role, index, mode, actor, incoming, s):
            put(m, address, value, size)
    callback(FLOAT, 0)
    world = read(m, s[GLOBALS[0]])
    speed = arithmetic.mul(arithmetic.add(arithmetic.mul(floats[0], bits(166.)), bits(160.)), read(m, s[GLOBALS[1]]))
    directions = [read(m, incoming + 0xC + i * 4) for i in range(3)]
    velocity = tuple(arithmetic.mul(arithmetic.mul(v ^ 0x80000000, world), speed) for v in directions)
    callback(FLOAT, 1)
    callback(FLOAT, 2)
    callback(RNG, 0)
    callback(RNG, 1)
    strength = arithmetic.mul(arithmetic.add(arithmetic.mul(floats[1], read(m, s[GLOBALS[2]])), bits(-600.)),
        read(m, s[GLOBALS[3]]))
    lifetime = arithmetic.mul(arithmetic.add(arithmetic.mul(floats[2], bits(500.)), bits(400.)), retained)
    payload = (*args[:3], 0, 0, 0, *velocity, bits(1.), strength, lifetime,
        integers[0] % 21 + 15, integers[1] % 101 + 100, 15, 20, 0, 0xFFFFFFFF,
        0x56, 0x27, 0, read(m, actor + 0xC, 1), read(m, actor + 1, 1))
    calls.append((EFFECT, (0x8C, 0x74, 0x80, *payload)))
    return calls


class EffectOracle(producer.BurstOracle):
    def __init__(self, words, memory, args=ARGS, floats=None, integers=(0, 0xFFFFFFFF),
            mode=0, phase=0, symbols=None, fault=None, connected=None, outcome=0):
        super().__init__(words, memory, actor=args[6], phase=phase, mode=mode,
            symbols=symbols or source.SYMBOLS, entry=source.ENTRY, connected=connected,
            arguments=(0x12345678, 0x87654321, *args[2:]))
        self.f[12], self.f[14] = args[:2]
        self.floats = floats or tuple(map(bits, (0.25, 0.5, 0.75)))
        self.integers = tuple(integers) + (0xFFFFFFFF, 0x80000000)
        self.float_count = self.integer_count = 0
        self.current_pc, self.delay_of, self.root_fault = None, None, fault
        self.code = TrackedCode(self.code, self)
        self.outcome, self.allocations, self.copies = outcome, [], []

    def execute(self, word):
        if word >> 26 == 32:
            rs, rt, immediate = word >> 21 & 31, word >> 16 & 31, word & 65535
            address = (self.r[rs] + (immediate if immediate < 32768 else immediate - 65536)) & 0xFFFFFFFF
            self.own_instruction = True
            try:
                value = self.get(address, 1)
                self.r[rt] = value if value < 128 else value | 0xFFFFFF00
                self.r[0] = 0
            finally:
                self.own_instruction = False
        else:
            super().execute(word)
            if word >> 26 == 0 and word & 63 == 26:
                left, right = signed(self.r[word >> 21 & 31]), signed(self.r[word >> 16 & 31])
                assert right and (left, right) != (-2147483648, -1)
                self.hi = (left - signed(self.lo) * right) & 0xFFFFFFFF

    def access(self):
        if self.own_instruction and source.ENTRY <= self.current_pc < source.ENTRY + 432:
            if self.accesses == self.root_fault:
                raise AccessBoundary
            self.accesses += 1

    def record_call(self, target):
        if target == EFFECT:
            args = self.arguments(17)
            frame = STACK + self.phase - 0x98
            payload = tuple(self.get(pointer + i * 4, 4) for pointer in args[:3] for i in range(3))
            values = (*(pointer - frame for pointer in args[:3]), *payload, *args[3:])
        elif target == ALLOCATOR:
            args = self.arguments(5)
            self.allocations.append((args, bytes(self.get(args[0] + i, 1) for i in range(0x78))))
            values = args
        elif target == MEMCPY:
            args = self.arguments(3)
            self.copies.append((args[0], bytes(self.get(args[1] + i, 1) for i in range(args[2]))))
            values = args
        else:
            assert target in (FLOAT, RNG), hex(target)
            values = ()
        self.calls.append((target, values))
        self.events.append(('CALL', target, values))

    def hook(self, target):
        index = self.float_count if target == FLOAT else self.integer_count
        for address, value, size in mutations(target, index, self.mode, self.actor, STACK + self.phase, self.symbols):
            self.put(address, value, size)
        value, result = None, 0x11223344
        if target == FLOAT:
            value = self.floats[self.float_count]
            self.float_count += 1
        elif target == RNG:
            result = self.integers[self.integer_count]
            self.integer_count += 1
        elif target == ALLOCATOR:
            result = CREATED if self.outcome else 0
        else:
            assert target == EFFECT
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = result
        if value is not None:
            self.f[0] = value


class GameActorEffectPacketMatchTests(unittest.TestCase):
    write_rows = staticmethod(consumer.GameActorBurstConsumerMatchTests.write_rows)

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-effect-packet-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(owner=source.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            makefile='conker/Makefile', assembly='conker/asm/1D43B0.s',
            layout='conker/retail_layout.us.txt', factory='conker/asm/1CC440.s',
            table='conker/asm/data/22E4E0.rodata.s')
        manifest = cls.out / 'baseline.json'
        if not manifest.exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['elf'] == BASELINE_ELF
        for name, digest in cls.baseline.items():
            assert hashlib.sha256((cls.out / ('before-' + name)).read_bytes()).hexdigest() == digest
        cls.meta, cls.raw = source.compile_candidate(cls.root, cls.out, 'selected')
        cls.object = cls.out / 'selected.o'
        text, functions, cls.relocations = parse_object(cls.object)
        cls.object_words = list(struct.unpack_from('>108I', text))
        cls.rows = source.guard_rows(cls.object_words, cls.relocations)
        cls.guards = cls.out / 'guards.csv'
        cls.write_rows(cls.guards, cls.rows)
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>108I', cls.rom, source.ROM))
        block = (cls.out / 'before-assembly').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1]
        cls.asm = cls.out / 'target.s'
        cls.asm.write_text('.include "' + str(cls.root / 'conker/include/asm_processor_prelude.inc') +
            '"\nglabel ' + source.FUNCTION + '\n' + block.split('endlabel ' + source.FUNCTION, 1)[0] +
            'endlabel ' + source.FUNCTION + '\n')
        cls.layout = cls.out / 'layout.csv'
        cls.layout.write_text('section,filename,function,address,end\n'
            'game,generated_1D43B0,func_151A7610,0x151A7610,0x151A77C0\n')
        cls.original = cls.assemble('original', cls.asm.read_text())
        cls.padded = [cls.assemble('padded%d' % index, assembly) for index, assembly in enumerate((
            emit_padded_assembly(cls.object, cls.asm, filename='generated_1D43B0', word_patches_path=cls.guards),
            pad_c_object.emit_padded_assembly(cls.object, cls.layout, 'generated_1D43B0', word_patches_path=cls.guards)))]
        cls.words = cls.link(cls.padded[0], 'qualified')

    @classmethod
    def assemble(cls, name, assembly):
        path = cls.out / (name + '.s')
        path.write_text(assembly)
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(path)],
            check=True, capture_output=True)
        return obj

    @classmethod
    def link(cls, obj, name, entry=source.ENTRY, symbols=None):
        script = cls.out / (name + '.ld')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
            *['--defsym=%s=0x%X' % item for item in (symbols or source.SYMBOLS).items()],
            '-o', str(elf), str(obj)], check=True, capture_output=True)
        return list(struct.unpack_from('>108I', sections(elf)['.text'][1]))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def test_01_both_real_padders_extent_relocations_and_independent_carry_links(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (108, 0x98, 8, 0, ''))
        self.assertEqual(self.words, self.retail)
        self.assertEqual(len(self.rows), 8)
        self.assertEqual(parse_object(self.object)[1][source.FUNCTION]['size'], 432)
        for index, entry in enumerate((source.ENTRY, 0x15207FF0, 0x15218008, 0x15328000)):
            symbols = {n: v + index * 0x10000 for n, v in source.SYMBOLS.items()}
            if index:
                symbols.update(zip(GLOBALS, (0x90007FFC + index * 0x10000,
                    0x91008004 + index * 0x10000, 0x92007FF8 + index * 0x10000,
                    0x93008008 + index * 0x10000)))
            original = self.link(self.original, 'original-%d' % index, entry, symbols)
            for pad, obj in enumerate(self.padded):
                self.assertEqual(self.link(obj, 'padded%d-%d' % (pad, index), entry, symbols), original)
                self.assertEqual(parse_object(obj)[1][source.FUNCTION]['size'], 432)
                self.assertEqual(parse_object(obj)[2], self.relocations)
        self.receipt('shape', raw108_frame152=True, eight_closed_F2_F12_guards=True,
            actual_padders=2, independent_links=4, all_data_carries_and_JALs_original=True)

    def test_02_every_guard_word_and_relocation_control_fires(self):
        checks = 0
        for index, row in enumerate(self.rows):
            for field, bad in (('expected', '0x00000000'), ('expected_relocations', 'R_MIPS_26:wrong_symbol')):
                rows = [dict(value) for value in self.rows]
                rows[index][field] = bad
                corrupt = self.out / 'corrupt-guards.csv'
                self.write_rows(corrupt, rows)
                for emit in (
                        lambda: emit_padded_assembly(self.object, self.asm, word_patches_path=corrupt,
                            filename='generated_1D43B0'),
                        lambda: pad_c_object.emit_padded_assembly(self.object, self.layout,
                            'generated_1D43B0', word_patches_path=corrupt)):
                    with self.assertRaisesRegex(ValueError, 'stale word patch|stale relocations'):
                        emit()
                    checks += 1
        self.receipt('guards', fired_stale_word_and_relocation_controls=checks,
            one_LO16_symbol_preserved_without_transplant=True, no_insertions_or_omissions=True)

    def test_03_complete_semantic_reference_and_guarded_states(self):
        cases, seen = 0, set()
        samples = (tuple(map(bits, v)) for v in ((0., 0., 0.), (0.25, 0.5, 0.75),
            (1., 1., 1.), (-0.5, 0.125, 1.25)))
        for floats, integers, mode, phase in itertools.product(tuple(samples),
                ((0, 0), (1, 2), (0xFFFFFFFF, 0x80000000), (0x80000000, 0xFFFFFFFF)),
                range(4), (0, 8)):
            memory = fixture(phase=phase)
            expected = reference(memory, floats=floats, integers=integers, mode=mode, phase=phase)
            models = [EffectOracle(body, memory, floats=floats, integers=integers, mode=mode, phase=phase).run()
                for body in (self.retail, self.words)]
            raw = EffectOracle(self.raw, memory, floats=floats, integers=integers, mode=mode, phase=phase).run()
            for model in (*models, raw):
                self.assertEqual(model.calls, expected)
                self.assertEqual((model.float_count, model.integer_count, model.r[29]), (3, 2, STACK + phase))
                self.assertEqual(model.f[20:], model.saved_f)
            self.assertEqual(producer.complete_state(models[0]), producer.complete_state(models[1]))
            seen.update(models[0].visits)
            cases += 1
        self.assertEqual(seen, set(range(source.ENTRY, source.ENTRY + 432, 4)))
        self.receipt('guest', cases=cases, all108_words_reached=True,
            raw_semantic_reference_and_guarded_complete_states=True,
            retained_actor_field_and_live_coefficients_bytes_directions=True,
            not_hardware_FCSR_or_all_input_gameplay_acceptance=True)

    def test_04_fired_access_prefixes_private_aliases_and_raw_cycle_witness(self):
        cuts, aliases = 0, 0
        for mode, phase in itertools.product(range(4), (0, 8)):
            memory = fixture(phase=phase)
            complete = EffectOracle(self.retail, memory, mode=mode, phase=phase).run()
            for cut in range(complete.accesses):
                models = [EffectOracle(body, memory, mode=mode, phase=phase, fault=cut)
                    for body in (self.retail, self.words)]
                for model in models:
                    with self.assertRaises(AccessBoundary):
                        model.run()
                self.assertEqual(producer.complete_state(models[0]), producer.complete_state(models[1]))
                self.assertEqual((models[0].current_pc, models[0].delay_of),
                    (models[1].current_pc, models[1].delay_of))
                cuts += 1
            for actor in (ACTOR, STACK + phase - 0x98 + 0x8C - 0x40,
                    STACK + phase - 0x98 + 0x74 - 0x40, STACK + phase - 0x98 + 0x80 - 0xC):
                args = (*ARGS[:6], actor)
                m = fixture(args, phase=phase)
                models = [EffectOracle(body, m, args, mode=mode, phase=phase, fault=5)
                    for body in (self.retail, self.words)]
                for model in models:
                    with self.assertRaises(AccessBoundary):
                        model.run()
                self.assertEqual(producer.complete_state(models[0]), producer.complete_state(models[1]))
                aliases += 1
        memory = fixture()
        cut = 12
        models = [EffectOracle(body, memory, fault=cut) for body in (self.retail, self.raw)]
        for model in models:
            with self.assertRaises(AccessBoundary):
                model.run()
        self.assertNotEqual(models[0].f, models[1].f)
        self.receipt('prefixes', fired_root_pairs=cuts, fired_alias_pairs=aliases,
            actual_PC_modeled_BD_and_all_prefix_states=True,
            raw_register_cycle_FPR_witness_fired=True, callback_accesses_excluded=True,
            private_aliases_guest_only_and_not_hardware_EPC_claim=True)

    def test_05_complete_owner_neighbors_pools_and_both_padders(self):
        before = (self.out / 'before-owner').read_text()
        after = source.recovered_owner(before)
        old_obj, old_warnings = compile_owner(self.root, self.out, before, 'owner-before')
        new_obj, new_warnings = compile_owner(self.root, self.out, after, 'owner-after')
        self.assertEqual(new_warnings, old_warnings)
        old_text, old_funcs, old_reloc = parse_object(old_obj)
        new_text, new_funcs, new_reloc = parse_object(new_obj)
        self.assertEqual(set(new_funcs), set(old_funcs))
        for name, old in old_funcs.items():
            new = new_funcs[name]
            if name == source.FUNCTION:
                self.assertEqual(new['size'], 432)
                self.assertEqual(new_text[new['value']:new['value'] + 432], struct.pack('>108I', *self.object_words))
                continue
            self.assertEqual(new['size'], old['size'], name)
            self.assertEqual(new_text[new['value']:new['value'] + new['size']],
                old_text[old['value']:old['value'] + old['size']], name)
            relative = lambda table, f: {at - f['value']: v for at, v in table.items()
                if f['value'] <= at < f['value'] + f['size']}
            self.assertEqual(relative(new_reloc, new), relative(old_reloc, old), name)
        self.assertEqual(normalized_pools(old_obj), normalized_pools(new_obj))
        owner_guards = self.out / 'owner-guards.csv'
        owner_guards.write_bytes(installed_guards((self.out / 'before-guards').read_bytes()))
        for index, assembly in enumerate((
                emit_padded_assembly(new_obj, self.out / 'before-assembly', filename='generated_1D43B0',
                    word_patches_path=owner_guards),
                pad_c_object.emit_padded_assembly(new_obj, self.out / 'before-layout', 'generated_1D43B0',
                    word_patches_path=owner_guards))):
            text, funcs, _ = parse_object(self.assemble('owner-pad%d' % index, assembly))
            target = funcs[source.FUNCTION]
            self.assertEqual(text[target['value']:target['value'] + 432], parse_object(self.padded[index])[0][:432])
        self.receipt('owner', neighbors=len(old_funcs) - 1, all_raw_words_relative_relocations_pools_and_warnings_fixed=True,
            both_complete_padders_and_prior_consumer_guards_preserved=True)

    def test_06_real157_word_factory_actual_memcpy_and_table1(self):
        helper = struct.unpack_from('>157I', self.rom, 0x1CFB9C)
        memcpy = struct.unpack_from('>11I', self.rom, 0x22EC0)
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x22E5C0)[0], source.ENTRY)
        data = (self.out / 'before-elf').read_bytes()
        self.assertEqual(data[image.elf_slot_offset(data, EFFECT, 628):][:628], struct.pack('>157I', *helper))
        cases = 0
        connected = dict(zip(range(EFFECT, EFFECT + 628, 4), helper))
        connected.update(zip(range(MEMCPY, MEMCPY + 44, 4), memcpy))
        for mode, phase, outcome in itertools.product(range(4), (0, 8), (0, 1)):
            memory = fixture(phase=phase)
            models = [EffectOracle(body, memory, mode=mode, phase=phase, connected=connected, outcome=outcome).run()
                for body in (self.retail, self.words)]
            for model in models:
                self.assertEqual((model.float_count, model.integer_count, len(model.allocations), len(model.copies)),
                    (3, 4, 1, 2 if outcome else 0))
                self.assertEqual(model.allocations[0][0][1:], (1, 16, 129 if mode == 2 else 255,
                    254 if mode == 2 else 128))
                if outcome:
                    self.assertEqual([p for p, _ in model.copies], [CREATED + 0xA8, CREATED + 0xB0])
                    self.assertEqual(model.copies[0][1][:4], struct.pack('>I', bits(1.)))
                self.assertEqual(model.r[2], 0)
            self.assertEqual(producer.complete_state(models[0]), producer.complete_state(models[1]))
            cases += 1
        self.receipt('connected', cases=cases, actual_factory157_and_memcpy11=True,
            success_and_failure_payload_copy_paths=True, authentic_table_index1=True,
            allocator_and_RNG_still_bounded_hooks=True, enclosing_dispatcher_not_claimed=True)

    def test_07_effective_complete_source_semantic_controls(self):
        controls = dict(
            count=source.SELECTED.replace('% 21 + 15', '% 21 + 16'),
            signed=source.SELECTED.replace('u32 integer0;', 's32 integer0;').replace(
                'integer0 = (u32)', 'integer0 = (s32)'),
            seed=source.SELECTED.replace('166.0f', '167.0f'),
            retained=source.SELECTED.replace('* retained,', '* *(f32 *)(actor + 0x40),'),
            coefficient=source.SELECTED.replace('first * D_800A8DCC', 'first * D_800A8DD0'),
            byte=source.SELECTED.replace('actor[0xC]', 'actor[0xD]'))
        memory = fixture()
        expected = reference(memory, integers=(0xFFFFFFFF, 0x80000000), mode=1)
        for name, body in controls.items():
            self.assertNotEqual(body, source.SELECTED, name)
            _, words = source.compile_candidate(self.root, self.out, 'negative-' + name, body)
            actual = EffectOracle(words, memory, integers=(0xFFFFFFFF, 0x80000000), mode=1).run()
            self.assertNotEqual(actual.calls, expected, name)
        self.receipt('controls', six_effective_guest_semantic_controls=True,
            signed_remainder_also_fires_native_control=True, bounded_signed_DIV_HI_completed=True)

    def test_08_closed_image_source_guard_prefix_and_protected_data(self):
        before_owner = (self.out / 'before-owner').read_text()
        after = source.recovered_owner(before_owner)
        current_owner = (self.root / source.SOURCE).read_text()
        self.assertIn(current_owner, (before_owner, after))
        before = (self.out / 'before-elf').read_bytes()
        installed = current_owner == after
        expected = expected_effect_image(before, self.retail) if installed else before
        current = (self.root / self.paths['elf']).read_bytes()
        self.assertTrue(current == expected, 'Undeclared whole ELF change')
        for name in set(self.paths) - {'owner', 'elf'}:
            before = (self.out / ('before-' + name)).read_bytes()
            expected = installed_guards(before) if name == 'guards' and installed else before
            self.assertEqual((self.root / self.paths[name]).read_bytes(), expected, name)
        data = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']), (True, 189088, 720, 0))
        old = (self.out / 'before-elf').read_bytes()
        self.receipt('image', installed=installed, changed_bytes=sum(a != b for a, b in zip(old, current)),
            protected_data=data, all_undeclared_ELF_and_source_guard_history_fixed=True)

    def test_09_effective_image_source_and_raw_guard_controls(self):
        rb, rt = Path.read_bytes, Path.read_text
        elf = self.root / self.paths['elf']
        data = rb(elf)
        for address, size in ((source.ENTRY, 432), (0x151A743C, 468), (0x151A6F00, 1260), (0x80089B00, 4)):
            bad = bytearray(data)
            bad[image.elf_slot_offset(data, address, size)] ^= 1
            with patch.object(Path, 'read_bytes', lambda p, v=bytes(bad): v if p == elf else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_08_closed_image_source_guard_prefix_and_protected_data()
        with patch.object(image.screen, 'ENTRY', source.ENTRY):
            size = image.elf_symbol_size_offset(data, source.FUNCTION)
        bad = bytearray(data)
        bad[size] ^= 1
        with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == elf else rb(p)):
            with self.assertRaises(AssertionError):
                self.test_08_closed_image_source_guard_prefix_and_protected_data()
        before = (self.out / 'before-elf').read_bytes()
        with patch.object(image.screen, 'ENTRY', source.ENTRY):
            at = image.elf_symbol_size_offset(before, source.FUNCTION)
        bad = bytearray(before)
        bad[at + 3] ^= 1
        with self.assertRaisesRegex(ValueError, 'original 12-byte'):
            expected_effect_image(bytes(bad), self.retail)
        guards = self.root / self.paths['guards']
        data = rb(guards)
        with patch.object(Path, 'read_bytes', lambda p: data + b'\n' if p == guards else rb(p)):
            with self.assertRaises(AssertionError):
                self.test_08_closed_image_source_guard_prefix_and_protected_data()
        owner = self.root / source.SOURCE
        data = rt(owner)
        with patch.object(Path, 'read_text', lambda p, *a, **k: data + '\n' if p == owner else rt(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_08_closed_image_source_guard_prefix_and_protected_data()
        self.receipt('image-controls', seven_current_corruptions_and_one_bad_baseline_size_rejected=True,
            no_metadata_exclusions_or_reset_baselines=True)

    def test_10_native32_complete_packet_both_profiles_and_signed_control(self):
        parameters, expected = [], []
        samples = (tuple(map(bits, v)) for v in ((0., 0., 0.), (0.25, 0.5, 0.75),
            (1., 1., 1.), (-0.5, 0.125, 1.25)))
        for floats, integers, mode, directions in itertools.product(tuple(samples),
                ((0, 0), (1, 2), (0xFFFFFFFF, 0x80000000), (0x80000000, 0xFFFFFFFF)),
                range(3), ((2., -4., 8.), (0., -0., 1.))):
            args = (*ARGS[:3], *map(bits, directions), ACTOR)
            memory = fixture(args)
            calls = reference(memory, args, floats, integers, mode)
            parameters.append([*args[:6], *floats, *integers, mode])
            expected.append(list(calls[-1][1][3:]))
        def array(name, values):
            return 'static const u32 %s[%d][%d]={\n%s\n};\n' % (name, len(values), len(values[0]),
                ',\n'.join('{' + ','.join('0x%Xu' % v for v in row) + '}' for row in values))
        native = '''typedef unsigned char u8; typedef int s32; typedef unsigned int u32; typedef float f32;
''' + source.RECORD + '''
static u8 actor[0x240] __attribute__((aligned(16)));
static u32 mode,fi,ri,used,order[6],observed[23],floatWords[3],integerWords[2];
f32 D_800BE9A8,D_800A8DC8,D_800A8DCC,D_800A8DD0;
static f32 value(u32 word){union{f32 f;u32 u;}v;v.u=word;return v.f;}
static u32 raw(f32 number){union{f32 f;u32 u;}v;v.f=number;return v.u;}
f32 func_150ADA68(void){u32 n=fi++;order[used++]=0x150ADA68;
 if(n==0 && mode==1){*(f32 *)(actor+0x40)=4.0f;D_800BE9A8=2.0f;D_800A8DC8=0.0078125f;}
 return value(floatWords[n]);}
s32 func_150ADA20(void){u32 n=ri++;order[used++]=0x150ADA20;
 if(n==1 && mode==2){D_800A8DCC=800.0f;D_800A8DD0=0.001953125f;actor[0xC]=129;actor[1]=254;
 *(f32 *)(actor+0x40)=8.0f;}return (s32)integerWords[n];}
void func_151A26EC(BurstVector1D43B0*a,BurstVector1D43B0*b,BurstVector1D43B0*c,
 f32 d,f32 e,f32 f,s32 g,s32 h,s32 i,s32 j,s32 k,s32 l,s32 m,s32 n,s32 o,u8 p,s32 q){
 order[used++]=0x151A26EC;
 observed[0]=raw(a->x);observed[1]=raw(a->y);observed[2]=raw(a->z);
 observed[3]=raw(b->x);observed[4]=raw(b->y);observed[5]=raw(b->z);
 observed[6]=raw(c->x);observed[7]=raw(c->y);observed[8]=raw(c->z);
 observed[9]=raw(d);observed[10]=raw(e);observed[11]=raw(f);
 observed[12]=g;observed[13]=h;observed[14]=i;observed[15]=j;observed[16]=k;observed[17]=l;
 observed[18]=m;observed[19]=n;observed[20]=o;observed[21]=p;observed[22]=q;}
''' + source.SELECTED + '\n' + array('parameters', parameters) + array('expected', expected) + '''
static const u32 wantedOrder[]={0x150ADA68,0x150ADA68,0x150ADA68,0x150ADA20,0x150ADA20,0x151A26EC};
static int run(void){u32 n,i;for(n=0;n<sizeof(parameters)/sizeof(parameters[0]);n++){
 for(i=0;i<sizeof(actor);i++)actor[i]=0xA5;
 *(f32 *)(actor+0x40)=1.25f;actor[0xC]=255;actor[1]=128;
 D_800BE9A8=0.5f;D_800A8DC8=value(0x3A83126F);D_800A8DCC=value(0x4413C000);D_800A8DD0=value(0x3A83126F);
 for(i=0;i<3;i++)floatWords[i]=parameters[n][6+i];
 integerWords[0]=parameters[n][9];integerWords[1]=parameters[n][10];mode=parameters[n][11];fi=ri=used=0;
 func_151A7610(value(parameters[n][0]),value(parameters[n][1]),value(parameters[n][2]),
  value(parameters[n][3]),value(parameters[n][4]),value(parameters[n][5]),actor);
 if(fi!=3 || ri!=2 || used!=6)return 1;
 for(i=0;i<6;i++)if(order[i]!=wantedOrder[i])return 2;
 for(i=0;i<23;i++)if(observed[i]!=expected[n][i])return 4;
}return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status));__builtin_unreachable();}
'''
        signed = source.SELECTED.replace('u32 integer0;', 's32 integer0;').replace('integer0 = (u32)', 'integer0 = (s32)')
        self.assertNotEqual(signed, source.SELECTED)
        for name, profile, body, code in (('selected-O2', '-O2', source.SELECTED, 0),
                ('selected-O0', '-O0', source.SELECTED, 0), ('signed-control', '-O2', signed, 4)):
            path = self.out / ('native-' + name + '.c')
            path.write_text(native.replace(source.SELECTED, body))
            binary = path.with_suffix('')
            compiled = subprocess.run(['cc', '-m32', profile, '-std=c99', '-fno-strict-aliasing', '-msse2',
                '-mfpmath=sse', '-mstackrealign', '-ffp-contract=off', '-ffreestanding', '-nostdlib', '-static',
                '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-unused-parameter', str(path), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            result = subprocess.run([str(binary)], capture_output=True)
            self.assertEqual(result.returncode, code, name)
        self.receipt('native', cases_per_profile=len(parameters), profiles=['O2', 'O0'],
            all23_packet_values_and_six_callback_order_checks=True,
            signed_remainder_control_fired=True, signed_zero_directions=True,
            not_native_private_alias_or_hardware_FP_acceptance=True)


if __name__ == '__main__':
    unittest.main()
