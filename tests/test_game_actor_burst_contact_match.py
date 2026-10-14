"""Direct contact callback, mixed O32 ABI, actual owner and closed image gates."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_burst_contact_candidates as source
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import test_game_actor_burst_packet_match as producer
from tools.tests import test_game_actor_burst_consumer_recovery as arithmetic
from tools.tests.test_game_actor_burst_consumer_match import TrackedCode, AccessBoundary
from tools.tests.test_game_record_callback_update_match import external
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_record_constructor_match as image
from tools.tests.test_game_one_shot_timer_match import canonical_symbols
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools import pad_c_object
from tools.check_game_data_layout import audit_layout

STACK, ACTOR = producer.STACK, 0x21000
RELEASE, RNG, EFFECT = (source.SYMBOLS[n] for n in
    ('func_1516972C', 'func_150ADA20', 'func_1514AB5C'))
FIELDS = tuple((at, 4) for at in (0x10, 0x14, 0x18, 0x3C, 0x44, 0x48,
    0x4C, 0x50, 0x54, 0x58, 0x60, 0x170, 0x174)) + (
    (0x64, 2), (0x178, 1), (0x179, 1), (0x17A, 2), (0x17C, 2))
BASELINE_ELF = 'b2c092d4e31f04377ebc5c05314803c8aed6e75233b93b58e30447187139c499'


def expected_contact_image(before, words):
    expected = bytearray(before)
    offset = image.elf_slot_offset(before, source.ENTRY, 468)
    expected[offset:offset + 468] = struct.pack('>117I', *words)
    with patch.object(image.screen, 'ENTRY', source.ENTRY):
        size = image.elf_symbol_size_offset(before, source.FUNCTION)
    if struct.unpack_from('>I', before, size)[0] != 12:
        raise ValueError('Expected original 12-byte contact symbol')
    struct.pack_into('>I', expected, size, 468)
    return bytes(expected)


def arguments(actor=ACTOR):
    return (actor, bits(-2.5), 0x8765ABCD, 0xFEDCBA98, bits(3.5), 0xFFFF1234)


def fixture(relation=0, duration=33, animation=1, active=1, variant=255,
        actor=ACTOR, phase=0, seed=0):
    m = {STACK + i: (i * 17 + seed * 31 + 0xA5) & 255 for i in range(-0x600, 0x400)}
    m.update({actor + i: (i * 13 + seed * 11 + 0xA5) & 255 for i in range(-32, 0x240)})
    values = (1.5, 0.25, 2.0, -8.0, -2.0, 4.0, -6.0, 8.0, -10.0, 12.0)
    for (at, _), value in zip(FIELDS, values):
        put(m, actor + at, bits(value))
    put(m, actor + 0x60, 0xA55AFFFF)
    put(m, actor + 0x170, (bits(-4.), bits(4.), bits(5.), 0x7FC12345)[relation])
    put(m, actor + 0x174, 0x33445566 if animation else 0)
    put(m, actor + 0x64, duration & 65535, 2)
    put(m, actor + 0x178, active, 1)
    put(m, actor + 0x179, variant, 1)
    put(m, actor + 0x17A, 0x8001, 2)
    put(m, actor + 0x17C, 0xFFFF, 2)
    put(m, STACK + phase + 0x10, arguments(actor)[4])
    return m


def mutations(target, mode, actor, incoming):
    if target == RELEASE and mode == 1:
        return ((actor + 0x170, bits(-8.), 4), (actor + 0x48, bits(2.), 4),
            (actor + 0x174, 0x778899AA, 4), (actor + 0x64, 100, 2))
    if target == RNG and mode in (2, 3):
        changes = ((actor + 0x18, bits(4.), 4), (actor + 0x179, 0, 1),
            (actor + 0x17A, 0xFFFE, 2), (actor + 0x17C, 0x7FFF, 2))
        if mode == 3:
            changes += ((incoming + 4, bits(6.), 4), (incoming + 0x10, bits(-3.), 4),
                (incoming + 0xC, 0x87654321, 4))
        return changes
    return ()


def reference(memory, args=None, random=0, mode=0, phase=0):
    args, m, calls = args or arguments(), dict(memory), []
    actor, incoming = args[0], STACK + phase
    for index, value in enumerate(args[:4]):
        put(m, incoming + index * 4, value)
    put(m, incoming + 0x10, args[4])
    def callback(target, values):
        calls.append((target, values))
        for address, value, size in mutations(target, mode, actor, incoming):
            put(m, address, value, size)
    get = lambda at, size=4: read(m, actor + at, size)
    put(m, actor + 0x3C, arithmetic.add(get(0x10), args[4]))
    if get(0x174):
        callback(RELEASE, (get(0x174),))
        put(m, actor + 0x174, 0)
    if floating(get(0x170)) < floating(get(0x48)):
        for mask in (7, 8, 0x40, 0x20):
            put(m, actor + 0x60, get(0x60) & ~mask)
        for at in (0x44, 0x48, 0x4C):
            put(m, actor + at, 0)
        if arithmetic.signed_half(get(0x64, 2)) > 32:
            put(m, actor + 0x64, 32, 2)
        if get(0x178, 1):
            variant = int(bool(get(0x179, 1)))
            callback(RNG, ())
            value = get(0x18)
            half = arithmetic.mul(value, bits(0.5))
            callback(EFFECT, (read(m, incoming + 4), read(m, incoming + 0x10),
                read(m, incoming + 0xC), arithmetic.mul(value, bits(35.)),
                random % 3 + 2, value, half, value, half,
                arithmetic.signed_half(get(0x17A, 2)) & 0xFFFFFFFF,
                arithmetic.signed_half(get(0x17C, 2)) & 0xFFFFFFFF, variant))
    else:
        factor = get(0x14)
        for at in (0x44, 0x48, 0x4C, 0x50, 0x54, 0x58):
            value = get(at) ^ (0x80000000 if at == 0x48 else 0)
            put(m, actor + at, arithmetic.mul(value, factor))
    return external(m), calls


class ContactOracle(producer.BurstOracle):
    def __init__(self, words, memory, args=None, random=0, mode=0, phase=0,
            entry=source.ENTRY, connected=None, fault=None):
        args = args or arguments()
        super().__init__(words, memory, actor=args[0], phase=phase, mode=mode,
            symbols=source.SYMBOLS, entry=entry, connected=connected, arguments=args)
        self.random, self.current_pc, self.delay_of, self.root_fault = random, None, None, fault
        self.code = TrackedCode(self.code, self)

    def access(self):
        if self.own_instruction and source.ENTRY <= self.current_pc < source.ENTRY + 468:
            if self.accesses == self.root_fault:
                raise AccessBoundary
            self.accesses += 1

    def record_call(self, target):
        if target == source.ENTRY:
            self.callbacks.append(self.arguments(6))
            return
        if target == EFFECT:
            values = (self.f[12], self.f[14], self.r[6], self.r[7], *self.arguments(12)[4:])
        else:
            assert target in (RELEASE, RNG), hex(target)
            values = self.arguments(1 if target == RELEASE else 0)
        self.calls.append((target, values))
        self.events.append(('CALL', target, values))

    def hook(self, target):
        for address, value, size in mutations(target, self.mode, self.actor, STACK + self.phase):
            self.put(address, value, size)
        for reg in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[reg] = 0xA5000000 + reg
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = self.random if target == RNG else 0x11223344


class GameActorBurstContactMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-burst-contact-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(owner=source.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            makefile='conker/Makefile', assembly='conker/asm/1D43B0.s',
            layout='conker/retail_layout.us.txt', caller='conker/asm/15F680.s',
            table='conker/asm/data/22E370.rodata.s')
        manifest = cls.out / 'baseline.json'
        if not manifest.exists():
            digests = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                digests[name] = hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(digests, indent=2) + '\n')
        cls.baseline = json.loads(manifest.read_text())
        assert cls.baseline['elf'] == BASELINE_ELF
        for name, digest in cls.baseline.items():
            assert hashlib.sha256((cls.out / ('before-' + name)).read_bytes()).hexdigest() == digest
        cls.meta, cls.words = source.compile_candidate(cls.root, cls.out, 'selected')
        cls.object = cls.out / 'selected.o'
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>117I', cls.rom, source.ROM))
        block = (cls.out / 'before-assembly').read_text().split('glabel ' + source.FUNCTION + '\n', 1)[1]
        cls.asm = cls.out / 'target.s'
        cls.asm.write_text('.include "' + str(cls.root / 'conker/include/asm_processor_prelude.inc') +
            '"\nglabel ' + source.FUNCTION + '\n' + block.split('endlabel ' + source.FUNCTION, 1)[0] +
            'endlabel ' + source.FUNCTION + '\n')
        cls.layout = cls.out / 'layout.csv'
        cls.layout.write_text('section,filename,function,address,end\n'
            'game,generated_1D43B0,func_151A743C,0x151A743C,0x151A7610\n')
        cls.original = cls.assemble('original', cls.asm.read_text())
        cls.padded = [cls.assemble('padded%d' % index, assembly) for index, assembly in enumerate((
            emit_padded_assembly(cls.object, cls.asm, filename='generated_1D43B0'),
            pad_c_object.emit_padded_assembly(cls.object, cls.layout, 'generated_1D43B0')))]

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
        return list(struct.unpack_from('>117I', sections(elf)['.text'][1]))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def compare(self, memory, args=None, random=0, mode=0, phase=0, bodies=None):
        expected = reference(memory, args, random, mode, phase)
        models = [ContactOracle(body, memory, args, random, mode, phase).run()
            for body in (bodies or (self.retail, self.words))]
        for model in models:
            self.assertEqual((external(model.memory), model.calls), expected)
            self.assertEqual((model.r[2], model.r[29], model.f[20:]), (1, STACK + phase, model.saved_f))
        self.assertEqual(producer.complete_state(models[0]), producer.complete_state(models[1]))
        return models

    def test_01_direct_shape_both_padders_and_independent_rebased_links(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences'],
            self.meta['pool_bytes'], self.meta['diagnostics']), (117, 0x48, 0, 0, ''))
        self.assertEqual(self.words, self.retail)
        self.assertEqual(self.meta['relocations'], {0x40: [('R_MIPS_26', 'func_1516972C')],
            0xF0: [('R_MIPS_26', 'func_150ADA20')], 0x164: [('R_MIPS_26', 'func_1514AB5C')]})
        for index, entry in enumerate((source.ENTRY, 0x15207FF0, 0x15218008, 0x15328000)):
            symbols = {n: v + index * 0x10000 for n, v in source.SYMBOLS.items()}
            original = self.link(self.original, 'original-%d' % index, entry, symbols)
            for pad, obj in enumerate(self.padded):
                self.assertEqual(self.link(obj, 'padded%d-%d' % (pad, index), entry, symbols), original)
                self.assertEqual(parse_object(obj)[1][source.FUNCTION]['size'], 468)
        self.receipt('shape', direct117_words=True, frame=72, guards=0,
            actual_padders=2, independent_links=4, exact_external_JAL_relocations=True)

    def test_02_threshold_duration_flags_rng_and_mutated_call_domains(self):
        seen, cases = set(), 0
        for relation, duration, animation, active, variant, random, mode, phase in itertools.product(
                range(4), (-32768, -1, 31, 32, 33, 32767), (0, 1), (0, 1), (0, 255),
                (0, 1, 2, 0xFFFFFFFF, 0x80000000), range(4), (0, 8)):
            m = fixture(relation, duration, animation, active, variant, phase=phase)
            for model in self.compare(m, random=random, mode=mode, phase=phase):
                seen.update(model.visits)
            cases += 1
        target = set(range(source.ENTRY, source.ENTRY + 468, 4))
        self.assertEqual(target - seen, {0x151A75B0})
        self.receipt('guest', cases=cases, reached_words=len(target & seen),
            unreachable_duplicate_load_preserved=True, quiet_NaN_threshold_comparison_only=True,
            independent_external_reference_and_complete_modeled_states=True,
            mixed_F12_F14_GPR_and_eight_stack_arguments=True, before_rng_variant_after_rng_value=True,
            incoming_float_context_home_mutations=True, not_hardware_FCSR_or_gameplay=True)

    def test_03_all_fired_root_access_prefix_states_and_private_aliases(self):
        cuts, aliases = 0, 0
        for relation, mode, phase in itertools.product((0, 2), range(4), (0, 8)):
            m = fixture(relation, phase=phase)
            complete = ContactOracle(self.retail, m, mode=mode, phase=phase).run()
            for cut in range(complete.accesses):
                models = [ContactOracle(body, m, mode=mode, phase=phase, fault=cut)
                    for body in (self.retail, self.words)]
                for model in models:
                    with self.assertRaises(AccessBoundary):
                        model.run()
                self.assertEqual(producer.complete_state(models[0]), producer.complete_state(models[1]))
                self.assertEqual((models[0].current_pc, models[0].delay_of),
                    (models[1].current_pc, models[1].delay_of))
                cuts += 1
            for actor in (ACTOR, STACK + phase - 0x48 - 0x174,
                    STACK + phase - 0x48 - 0x170, STACK + phase - 0x48 - 0x44):
                memory = fixture(relation, actor=actor, phase=phase)
                models = [ContactOracle(body, memory, arguments(actor), mode=mode, phase=phase, fault=6)
                    for body in (self.retail, self.words)]
                for model in models:
                    with self.assertRaises(AccessBoundary):
                        model.run()
                self.assertEqual(producer.complete_state(models[0]), producer.complete_state(models[1]))
                aliases += 1
        self.receipt('prefixes', fired_root_pairs=cuts, fired_alias_pairs=aliases,
            full_modeled_memory_GPR_FPR_HI_LO_calls_PC_and_BD=True,
            callback_accesses_excluded=True, private_aliases_guest_only=True,
            not_a_hardware_EPC_BD_or_all_input_native_claim=True)

    def test_04_complete_owner_neighbors_relocations_pools_and_guard_history(self):
        before = (self.out / 'before-owner').read_text()
        after = source.recovered_owner(before)
        old_obj, old_warnings = compile_owner(self.root, self.out, before, 'owner-before')
        new_obj, new_warnings = compile_owner(self.root, self.out, after, 'owner-after')
        self.assertEqual(new_warnings, old_warnings)
        old_text, old_functions, old_relocations = parse_object(old_obj)
        new_text, new_functions, new_relocations = parse_object(new_obj)
        self.assertEqual(set(old_functions), set(new_functions))
        for name, old in old_functions.items():
            new = new_functions[name]
            if name == source.FUNCTION:
                self.assertEqual(new['size'], 468)
                self.assertEqual(new_text[new['value']:new['value'] + 468],
                    parse_object(self.object)[0][:468])
                continue
            self.assertEqual(new['size'], old['size'], name)
            self.assertEqual(new_text[new['value']:new['value'] + new['size']],
                old_text[old['value']:old['value'] + old['size']], name)
            relative = lambda reloc, f: {at - f['value']: v for at, v in reloc.items()
                if f['value'] <= at < f['value'] + f['size']}
            self.assertEqual(relative(new_relocations, new), relative(old_relocations, old), name)
        self.assertEqual(normalized_pools(old_obj), normalized_pools(new_obj))
        padded = []
        for index, obj in enumerate((old_obj, new_obj)):
            for pad, assembly in enumerate((
                    emit_padded_assembly(obj, self.out / 'before-assembly', filename='generated_1D43B0',
                        word_patches_path=self.out / 'before-guards'),
                    pad_c_object.emit_padded_assembly(obj, self.out / 'before-layout', 'generated_1D43B0',
                        word_patches_path=self.out / 'before-guards'))):
                padded.append(parse_object(self.assemble('owner%d-pad%d' % (index, pad), assembly)))
        for new, old in ((padded[2], padded[0]), (padded[3], padded[1])):
            for name, old_function in old[1].items():
                if name == source.FUNCTION:
                    continue
                current = new[1][name]
                self.assertEqual(current, old_function)
                at, size = current['value'], current['size']
                self.assertEqual(new[0][at:at + size], old[0][at:at + size], name)
        self.receipt('owner', unchanged_neighbors=len(old_functions) - 1,
            warnings_pools_all_relative_relocations_fixed=True,
            both_complete_owner_padders_and_existing_ten_consumer_guards=True)

    def test_05_effective_semantic_and_operand_shape_controls(self):
        controls = dict(
            count=source.SELECTED.replace('% 3 + 2', '% 3 + 3'),
            threshold=source.SELECTED.replace('extra->field00 <', 'extra->field00 >'),
            clamp=source.SELECTED.replace('> 32', '> 31').replace('= 32;', '= 31;'),
            variant=source.SELECTED.replace('variant = 1;', 'variant = extra->field09;'),
            clear=source.SELECTED.replace('extra->animation = NULL;', 'extra->animation = (u8 *)1;'),
            half=source.SELECTED.replace('* 0.5f', '* 0.75f'))
        memory = fixture()
        expected = reference(memory)
        for name, body in controls.items():
            self.assertNotEqual(body, source.SELECTED)
            _, words = source.compile_candidate(self.root, self.out, 'negative-' + name, body)
            model = ContactOracle(words, memory).run()
            self.assertNotEqual((external(model.memory), model.calls), expected, name)
        meta, _ = source.compile_candidate(self.root, self.out, 'uncommuted', source.NEAR_MATCH)
        self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), (117, 72, 1))
        merged = source.SELECTED.replace('''        *(u32 *)(actor + 0x60) &= ~7;
        *(u32 *)(actor + 0x60) &= ~8;
        *(u32 *)(actor + 0x60) &= ~0x40;
        *(u32 *)(actor + 0x60) &= ~0x20;''', '        *(u32 *)(actor + 0x60) &= ~0x6F;')
        self.assertNotEqual(merged, source.SELECTED)
        _, words = source.compile_candidate(self.root, self.out, 'merged-flags', merged)
        models = [ContactOracle(body, memory).run() for body in (self.retail, words)]
        self.assertNotEqual([e for e in models[0].events if e[0] == 'W' and e[1] == ACTOR + 0x60],
            [e for e in models[1].events if e[0] == 'W' and e[1] == ACTOR + 0x60])
        self.receipt('controls', six_effective_full_source_semantic_controls=True,
            merged_flag_store_trace_control=True, uncommuted_single_word_control=True)

    def test_06_actual_dispatch_table4_six_argument_callback_window(self):
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x22E404)[0], source.ENTRY)
        start, end = 0x15132FE0, 0x15133014
        caller = list(struct.unpack_from('>13I', self.rom, 0x160490))
        # Start at a real dispatcher continuation; earlier speed computation is outside this window.
        cases = 0
        for phase, mode in itertools.product((0, 8), range(4)):
            memory = fixture(phase=phase)
            put(memory, 0x80089944, source.ENTRY)
            for at, value in ((0x374, bits(-2.5)), (0x378, 0x8765ABCD), (0x37C, 0xFEDCBA98)):
                put(memory, STACK + phase + at, value)
            put(memory, ACTOR + 0x110, bits(3.5))
            models = []
            for body in (self.retail, self.words):
                model = ContactOracle(caller + [0x03E00008, 0], memory, mode=mode,
                    phase=phase, entry=start, connected=dict(zip(range(source.ENTRY, source.ENTRY + 468, 4), body)))
                model.r[16], model.r[2] = ACTOR, 4
                model.r[4] = ACTOR
                # The enclosing dispatcher's RA belongs to its omitted frame; stop before its continuation.
                class Continuation(TrackedCode):
                    def __getitem__(self, pc):
                        if pc == end:
                            raise AccessBoundary
                        return super().__getitem__(pc)
                model.code = Continuation(model.code, model)
                with self.assertRaises(AccessBoundary):
                    model.run()
                self.assertEqual(model.callbacks, [(ACTOR, bits(-2.5), 0x8765ABCD,
                    0xFEDCBA98, bits(3.5), ACTOR + 0x114)])
                models.append(model)
            self.assertEqual(producer.complete_state(models[0]), producer.complete_state(models[1]))
            cases += 1
        self.receipt('dispatcher', real_ROM_window_cases=cases, actual_table_index4=True,
            fifth_float_and_unused_sixth_pointer=True, continuation_gate_fired=True,
            enclosing_speed_path_and_complete_effect_helper_not_claimed=True)

    def test_09_native32_both_profiles_and_effective_unsigned_remainder_control(self):
        initial, final, parameters, traces = [], [], [], []
        for relation, duration, animation, active, variant, random, mode in itertools.product(
                range(4), (-32768, 32, 33, 32767), (0, 1), (0, 1), (0, 255),
                (0, 1, 2, 0xFFFFFFFF, 0x80000000), range(3)):
            memory = fixture(relation, duration, animation, active, variant)
            expected, calls = reference(memory, random=random, mode=mode)
            initial.append([read(memory, ACTOR + at, size) for at, size in FIELDS])
            final.append([read(expected, ACTOR + at, size) for at, size in FIELDS])
            flat = [v for target, args in calls for v in (target, len(args), *args)]
            traces.append([len(flat), *flat, *([0] * (24 - len(flat)))])
            parameters.append([mode, random])
        def array(name, rows):
            return 'static const u32 %s[%d][%d]={\n%s\n};\n' % (name, len(rows), len(rows[0]),
                ',\n'.join('{' + ','.join('0x%Xu' % v for v in row) + '}' for row in rows))
        native = '''typedef unsigned char u8; typedef short s16; typedef int s32;
typedef unsigned int u32; typedef float f32;
#define NULL ((void *)0)
''' + source.RECORD + '''
static u8 actor[0x240] __attribute__((aligned(16)));
static u32 mode,randomWord,trace[24],used;
static u32 raw(f32 value){union{f32 f;u32 u;}v;v.f=value;return v.u;}
static void set(u32 at,u32 value,u32 size){u32 i;for(i=0;i<size;i++)actor[at+i]=(u8)(value>>(i*8));}
static u32 get(u32 at,u32 size){u32 i,v=0;for(i=0;i<size;i++)v|=(u32)actor[at+i]<<(i*8);return v;}
void func_1516972C(u32 pointer){
 trace[used++]=0x1516972C;trace[used++]=1;trace[used++]=pointer;
 if(mode==1){set(0x170,0xC1000000,4);set(0x48,0x40000000,4);
 set(0x174,0x778899AA,4);set(0x64,100,2);}}
s32 func_150ADA20(void){
 trace[used++]=0x150ADA20;trace[used++]=0;
 if(mode==2){set(0x18,0x40800000,4);set(0x179,0,1);set(0x17A,0xFFFE,2);set(0x17C,0x7FFF,2);}
 return (s32)randomWord;}
void func_1514AB5C(f32 a,f32 b,s32 c,f32 d,s32 e,f32 f,f32 g,f32 h,f32 i,s16 j,s16 k,u8 l){
 trace[used++]=0x1514AB5C;trace[used++]=12;
 trace[used++]=raw(a);trace[used++]=raw(b);trace[used++]=(u32)c;trace[used++]=raw(d);
 trace[used++]=(u32)e;trace[used++]=raw(f);trace[used++]=raw(g);trace[used++]=raw(h);
 trace[used++]=raw(i);trace[used++]=(u32)j;trace[used++]=(u32)k;trace[used++]=l;}
''' + source.SELECTED + '\n' + array('initial', initial) + array('expected', final) + (
            array('parameters', parameters) + array('traces', traces) +
            array('fields', [[at, size] for at, size in FIELDS])) + '''
static int run(void){u32 n,i;for(n=0;n<sizeof(initial)/sizeof(initial[0]);n++){
 for(i=0;i<sizeof(actor);i++)actor[i]=0xA5;
 for(i=0;i<sizeof(fields)/sizeof(fields[0]);i++)set(fields[i][0],initial[n][i],fields[i][1]);
 mode=parameters[n][0];randomWord=parameters[n][1];used=0;
 if(func_151A743C(actor,-2.5f,(s32)0x8765ABCD,(s32)0xFEDCBA98,3.5f)!=1)return 1;
 for(i=0;i<sizeof(fields)/sizeof(fields[0]);i++)if(get(fields[i][0],fields[i][1])!=expected[n][i])return 2;
 if(used!=traces[n][0])return 3;
 for(i=0;i<used;i++)if(trace[i]!=traces[n][i+1])return 4;
}return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status));__builtin_unreachable();}
'''
        signed = source.SELECTED.replace('(u32)func_150ADA20() % 3', 'func_150ADA20() % 3')
        self.assertNotEqual(signed, source.SELECTED)
        for name, profile, body, success in (('selected-O2', '-O2', source.SELECTED, True),
                ('selected-O0', '-O0', source.SELECTED, True), ('signed-control', '-O2', signed, False)):
            path = self.out / ('native-' + name + '.c')
            path.write_text(native.replace(source.SELECTED, body))
            binary = path.with_suffix('')
            compiled = subprocess.run(['cc', '-m32', profile, '-std=c99', '-fno-strict-aliasing', '-msse2',
                '-mfpmath=sse', '-mstackrealign', '-ffp-contract=off', '-ffreestanding', '-nostdlib', '-static',
                '-fno-pie', '-no-pie', '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                '-Wno-unused-parameter', str(path), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            result = subprocess.run([str(binary)], capture_output=True)
            if success:
                self.assertEqual(result.returncode, 0, name)
            else:
                self.assertEqual(result.returncode, 4, name)
        self.receipt('native', cases_per_profile=len(initial), profiles=['O2', 'O0'],
            initialized_raw_actor_fields_and_all_callback_argument_bits=True,
            signed_remainder_control_fired_at_trace_check=True,
            not_private_home_alias_or_hardware_FP_acceptance=True)

    def test_07_closed_image_source_and_protected_history(self):
        before_owner = (self.out / 'before-owner').read_text()
        installed_owner = source.recovered_owner(before_owner)
        from tools.experiments import game_actor_effect_packet_candidates as effect
        effect_owner = effect.recovered_owner(installed_owner)
        current_owner = (self.root / source.SOURCE).read_text()
        self.assertIn(current_owner, (before_owner, installed_owner, effect_owner))
        before = (self.out / 'before-elf').read_bytes()
        installed = current_owner in (installed_owner, effect_owner)
        expected = expected_contact_image(before, self.retail) if installed else before
        if current_owner == effect_owner:
            from tools.tests.test_game_actor_effect_packet_match import expected_effect_image
            expected = expected_effect_image(expected, struct.unpack_from('>108I', self.rom, effect.ROM))
        current = (self.root / self.paths['elf']).read_bytes()
        self.assertTrue(current == expected, 'Undeclared whole ELF change')
        self.assertEqual(canonical_symbols(current), canonical_symbols(expected))
        for name in set(self.paths) - {'owner', 'elf'}:
            expected_input = (self.out / ('before-' + name)).read_bytes()
            if name == 'guards' and current_owner == effect_owner:
                from tools.tests.test_game_actor_effect_packet_match import installed_guards
                expected_input = installed_guards(expected_input)
            self.assertEqual((self.root / self.paths[name]).read_bytes(), expected_input, name)
        data = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertEqual((data['exact'], data['bytes'], data['owner_count'], data['different_bytes']),
            (True, 189088, 720, 0))
        self.receipt('image', installed=installed,
            changed_bytes=sum(a != b for a, b in zip(before, current)), protected_data=data,
            all_undeclared_ELF_source_guard_layout_caller_and_table_bytes_fixed=True)

    def test_08_effective_closed_image_and_raw_guard_corruptions(self):
        rb, rt = Path.read_bytes, Path.read_text
        elf = self.root / self.paths['elf']
        data = rb(elf)
        for entry, size in ((source.ENTRY, 468), (producer.PROVIDER, 1260), (0x80089944, 4)):
            bad = bytearray(data)
            bad[image.elf_slot_offset(data, entry, size)] ^= 1
            with patch.object(Path, 'read_bytes', lambda p, v=bytes(bad): v if p == elf else rb(p)):
                with self.assertRaises(AssertionError):
                    self.test_07_closed_image_source_and_protected_history()
        size = None
        with patch.object(image.screen, 'ENTRY', source.ENTRY):
            size = image.elf_symbol_size_offset(data, source.FUNCTION)
        bad = bytearray(data)
        bad[size] ^= 1
        with patch.object(Path, 'read_bytes', lambda p: bytes(bad) if p == elf else rb(p)):
            with self.assertRaises(AssertionError):
                self.test_07_closed_image_source_and_protected_history()
        guards = self.root / self.paths['guards']
        data = rb(guards)
        with patch.object(Path, 'read_bytes', lambda p: data + b'\n' if p == guards else rb(p)):
            with self.assertRaises(AssertionError):
                self.test_07_closed_image_source_and_protected_history()
        owner = self.root / source.SOURCE
        data = rt(owner)
        with patch.object(Path, 'read_text', lambda p, *a, **k: data + '\n' if p == owner else rt(p, *a, **k)):
            with self.assertRaises(AssertionError):
                self.test_07_closed_image_source_and_protected_history()
        self.receipt('image-controls', target_neighbor_table_symbol_source_and_raw_guard_rejections=6,
            no_broad_metadata_exclusions=True)


if __name__ == '__main__':
    unittest.main()
