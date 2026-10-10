"""Direct RGB leaf matching, ordered aliases, real caller and linked-only audit."""
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_rgb_parameters_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as attachment
from tools.tests import test_game_actor_render_dispatch_recovery as dispatch
from tools.tests import test_game_owner_points_initializer_match as initializer
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools

STACK, OUTPUT = attachment.STACK, 0x24000
LINKS = ((screen.ENTRY, 0x800CC2D0), (0x15207FF0, 0x80107FFC),
    (0x15308004, 0x80118004))
SLOTS = (0, 25, -1, 0x7FFFFFFF, -0x80000000, 0x12345678)


def actor_address(slot, symbols=LINKS[0]):
    return (symbols[1] + (slot & 0xFFFFFFFF) * 0x32C) & 0xFFFFFFFF


def fixture(slot=0, flags=4, colors=(0, 1, 254, 255, 128, 127), symbols=LINKS[0]):
    actor = actor_address(slot, symbols)
    memory = {STACK + i: 0xA5 for i in range(-0x600, 0x100)}
    for start, length in ((actor - 16, 0x350), (OUTPUT, 32)):
        memory.update({(start + i) & 0xFFFFFFFF: (17 * i + 53) & 255 for i in range(length)})
    memory[actor + 0x66] = flags
    for i, value in enumerate(colors):
        memory[actor + 0x1DD + i] = value
    return memory


def reference(memory, slot=0, output=OUTPUT, symbols=LINKS[0]):
    result, events = memory.copy(), []
    actor = actor_address(slot, symbols)
    def get(address, size=1):
        value = attachment.read(result, address, size)
        events.append(('R', address, size, value))
        return value
    def put(address, value):
        attachment.put(result, address, value, 4)
        events.append(('W', address, 4, value & 0xFFFFFFFF))
    if get(actor + 0x66) & 12 == 4:
        red = get(actor + 0x1DD) + get(actor + 0x1E0)
        put(output, red // 2)
        green_second = get(actor + 0x1E1)
        green_first = get(actor + 0x1DE)
        red = get(output, 4)
        put(output + 4, (green_first + green_second) // 2)
        blue_second = get(actor + 0x1E2)
        blue_first = get(actor + 0x1DF)
        green = get(output + 4, 4)
        blue = (blue_first + blue_second) // 2
        put(output + 8, blue)
        put(output, 255 - red)
        put(output + 4, 255 - green)
        put(output + 8, 255 - blue)
    else:
        for offset in (8, 4, 0):
            put(output + offset, 255)
    return result, events


class RGBOracle(attachment.AttachmentOracle):
    def __init__(self, words, memory, slot=0, output=OUTPUT, symbols=LINKS[0], phase=0):
        super().__init__(words, memory, entry=symbols[0], arguments=(slot, output), phase=phase)


class ConnectedDispatch(dispatch.DispatchOracle):
    def hook(self, target):
        assert target != screen.ENTRY, 'RGB must execute its complete body, not a hook'
        return super().hook(target)


class GameActorRGBParametersMatchTests(unittest.TestCase):
    assemble = classmethod(attachment.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    run_host = attachment.GameActorAttachmentUpdateMatchTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-actor-rgb-parameters-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths = dict(dispatch.PATHS)
        if not (cls.out / 'baseline.json').exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out / 'baseline.json').write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads((cls.out / 'baseline.json').read_text())
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>57I', cls.rom, screen.ROM))
        assembly = (cls.root / 'conker/asm/58F80.s').read_text().split(
            'glabel ' + screen.FUNCTION, 1)[1].split('endlabel ' + screen.FUNCTION, 1)[0]
        cls.slot_asm = cls.out / 'slot.s'
        cls.slot_asm.write_text('glabel ' + screen.FUNCTION + assembly +
            'endlabel ' + screen.FUNCTION + '\n')
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl ' + screen.FUNCTION +
            '\n.type ' + screen.FUNCTION + ',@function\n' + screen.FUNCTION + ':\n' + assembly +
            '\n.size ' + screen.FUNCTION + ',.-' + screen.FUNCTION + '\n')
        cls.assemble('padded', emit_padded_assembly(cls.out / 'selected.o', cls.slot_asm,
            filename='generated_58F80'))
        cls.padded = cls.link('padded', LINKS[0])
        cls.elf = (cls.root / cls.paths['elf']).read_bytes()
        cls.current = cls.raw
        if screen.ORIGINAL not in (cls.root / screen.SOURCE).read_text():
            cls.current = list(struct.unpack_from('>57I', cls.elf,
                elf_slot_offset(cls.elf, screen.ENTRY, 228)))
        cls.caller = list(struct.unpack_from('>176I', cls.elf,
            elf_slot_offset(cls.elf, dispatch.screen.ENTRY, 704)))
        assert cls.caller == list(struct.unpack_from('>176I', cls.rom, dispatch.screen.ROM))
        cls.objects, cls.diagnostics = [], []
        before = (cls.out / 'before-source').read_text()
        for name, body in (('owner-before', before), ('owner-after', screen.install(before))):
            obj, diagnostics = compile_owner(cls.root, cls.out, body, name)
            subprocess.run(['python3', str(cls.root / 'tools/asm-processor/asm_processor.py'),
                '-O2', '-g3', str((cls.out / (name + '.c')).relative_to(cls.root / 'conker')),
                '--post-process', str(obj.relative_to(cls.root / 'conker')), '--assembler',
                'mips-linux-gnu-as -EB -march=vr4300', '--asm-prelude',
                'include/asm_processor_prelude.inc'], cwd=cls.root / 'conker', check=True, capture_output=True)
            cls.objects.append(obj)
            cls.diagnostics.append(diagnostics)
        cls.coverage = set()
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)
        cls.fixture = '''typedef unsigned char u8;typedef unsigned int u32;typedef int s32;
static u8 D_800CC2D0[26*0x32C];
''' + screen.SELECTED + '\n'

    @classmethod
    def link(cls, name, symbols):
        script = cls.out / ('link-%s-%X.ld' % (name, symbols[0]))
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % symbols[0])
        elf = script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script),
            '-e', screen.FUNCTION, '--defsym=D_800CC2D0=0x%X' % symbols[1],
            '-o', str(elf), str(cls.out / (name + '.o'))], check=True, capture_output=True)
        size = parse_object(cls.out / (name + '.o'))[1][screen.FUNCTION]['size'] // 4
        return list(struct.unpack_from('>%dI' % size, sections(elf)['.text'][1]))

    def receipt(self, name, **values):
        (self.out / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')

    def compare(self, memory, slot=0, output=OUTPUT, symbols=LINKS[0], bodies=None, phase=0):
        expected, events = reference(memory, slot, output, symbols)
        models = []
        for body in bodies or (self.retail, self.raw, self.current):
            model = RGBOracle(body, memory, slot, output, symbols, phase).run()
            self.assertEqual((model.memory, model.events), (expected, events))
            self.assertEqual(model.calls, [])
            models.append(model)
        self.coverage.update(models[0].visits)
        return models

    def test_01_all_flags_slot_widths_and_color_boundaries(self):
        cases = 0
        for slot, flags in itertools.product(SLOTS, range(256)):
            memory = fixture(slot, flags)
            self.compare(memory, slot, phase=8 if cases % 2 else 0)
            cases += 1
        values = (0, 1, 2, 127, 128, 254, 255)
        for channel, first, second in itertools.product(range(3), values, values):
            colors = [7, 91, 253, 12, 192, 4]
            colors[channel], colors[channel + 3] = first, second
            self.compare(fixture(colors=colors))
            cases += 1
        self.receipt('guest', cases=cases, executions=cases * 3, all_256_flag_bytes=True,
            full_32bit_slot_product=True, complete_memory_and_order_exact=True,
            alpha_untouched=True, saved_GPR_FPR_RA_SP_checked=True)

    def test_02_aliases_and_every_fired_fault_prefix(self):
        aliases = faults = 0
        for flags, offset, phase in itertools.product((0, 4, 12), range(-12, 0x334, 4), (0, 8)):
            memory = fixture(flags=flags)
            output = actor_address(0) + offset
            self.compare(memory, output=output, phase=phase)
            aliases += 1
        for flags, output in itertools.product((0, 4, 12),
                (OUTPUT, actor_address(0) + 0x64, actor_address(0) + 0x1D8,
                 actor_address(0) + 0x1DC, STACK - 0x20)):
            memory = fixture(flags=flags)
            expected, events = reference(memory, output=output)
            for ordinal in range(len(events)):
                prefix_memory = memory.copy()
                for event in events[:ordinal]:
                    if event[0] == 'W': attachment.put(prefix_memory, event[1], event[3], event[2])
                for body in (self.retail, self.raw, self.current):
                    model = RGBOracle(body, memory, output=output)
                    model.fault = ordinal
                    with self.assertRaises(attachment.AccessFault) as caught:
                        model.run()
                    self.assertEqual(caught.exception.args, (ordinal,))
                    self.assertEqual((model.memory, model.events), (prefix_memory, events[:ordinal]))
                faults += 1
        self.receipt('aliases-and-faults', alias_cases=aliases, fired_prefixes=faults,
            fault_executions=faults * 3, actual_actor_output_stack_aliases=True,
            every_requested_gate_fired=True, full_memory_and_access_order_exact=True)

    def test_03_independent_symbol_links_without_guards(self):
        cases = 0
        for symbols in LINKS:
            bodies = [self.link(name, symbols) for name in ('original', 'selected', 'padded')]
            self.assertEqual(bodies[0], bodies[1])
            self.assertEqual(bodies[0], bodies[2])
            for slot, flags, offset in itertools.product((0, 25, -1), (0, 4, 12), (None, 0x1DC)):
                output = OUTPUT if offset is None else actor_address(slot, symbols) + offset
                self.compare(fixture(slot, flags, symbols=symbols), slot, output, symbols, bodies)
                cases += 1
        self.receipt('links', independent_links=9, symbol_sets=3, cases=cases,
            signed_LO16_carries=True, raw_equals_original_equals_padded=True, guards=0)

    def test_04_owner_neighbors_pools_and_actual_padding(self):
        self.assertEqual(self.diagnostics, [[], []])
        first, second = [parse_object(obj) for obj in self.objects]
        relative = lambda data, f: {o - f['value']: uses for o, uses in data[2].items()
            if f['value'] <= o < f['value'] + f['size']}
        self.assertEqual(first[1].keys(), second[1].keys())
        for name, a in first[1].items():
            if name == screen.FUNCTION: continue
            b = second[1][name]
            self.assertEqual((a['size'], first[0][a['value']:a['value'] + a['size']], relative(first, a)),
                (b['size'], second[0][b['value']:b['value'] + b['size']], relative(second, b)), name)
        self.assertEqual(normalized_pools(self.objects[0]), normalized_pools(self.objects[1]))
        isolated = parse_object(self.out / 'selected.o')
        target = second[1][screen.FUNCTION]
        self.assertEqual(second[0][target['value']:target['value'] + 228], isolated[0][:228])
        self.assertEqual(relative(second, target), isolated[2])
        padded = []
        for i, obj in enumerate(self.objects):
            name = 'padded-owner-%d' % i
            self.assemble(name, emit_padded_assembly(obj, self.root / 'conker/asm/58F80.s',
                word_patches_path=self.out / 'before-guards', filename='generated_58F80',
                rodata_symbol='jtbl_80096DF8_game'))
            padded.append(parse_object(self.out / (name + '.o')))
        start = padded[1][1][screen.FUNCTION]['value']
        self.assertEqual(padded[1][1][screen.FUNCTION]['size'], 228)
        self.assertEqual(padded[0][0][:start], padded[1][0][:start])
        self.assertEqual(padded[0][0][start + 228:], padded[1][0][start + 228:])
        self.receipt('owner', neighbors=len(first[1]) - 1, diagnostics=0,
            caller_body_and_relocations_exact=True, isolated_equals_owner=True,
            pools_exact=True, only_target_padded_slot_changes=True, new_guards=0)

    def test_05_complete_actual_banked_dispatch_connection(self):
        cases = 0
        for slot, view, mode, phase, flags, enabled in itertools.product(
                (0, 25), (0, 3), range(7), (0, 8), (0, 4, 12), (0, 1)):
            memory = dispatch.fixture(slot, view, enabled=enabled)
            actor = actor_address(slot)
            memory[actor + 0x66] = flags
            colors = tuple((i * 37 + cases) & 255 for i in range(6))
            for i, value in enumerate(colors): memory[actor + 0x1DD + i] = value
            models = []
            for body in (self.retail, self.raw, self.current):
                connected = {screen.ENTRY + i * 4: word for i, word in enumerate(body)}
                model = ConnectedDispatch(self.caller, memory, slot, view, mode,
                    phase=phase, plan=dispatch.Plan(second=254), connected=connected).run()
                self.assertIn(screen.ENTRY, model.visits)
                render = [e for e in model.calls if e[1] == 'func_1502CCFC']
                self.assertEqual(len(render), 1)
                rgb = tuple(255 - (colors[i] + colors[i + 3]) // 2 for i in range(3)) if flags == 4 else (255,) * 3
                self.assertEqual(render[0][2][5], (*rgb, 144 if enabled else 255))
                models.append(model)
            for model in models[1:]:
                self.assertEqual((model.r[2], model.memory, model.events),
                    (models[0].r[2], models[0].memory, models[0].events))
            cases += 1
        self.receipt('caller', cases=cases, banked_caller_words=176, complete_RGB_words=57,
            actual_bodies_execute=True, other_callbacks_explicitly_bounded_opaque=True,
            renderer_RGB_and_alpha_checked=True, whole_game_acceptance=False)

    def test_06_actual_native32_complete_C(self):
        self.run_host('''
int slot, flags, channel, first, second, i, expected;
s32 parameters[4]; u8 *actor;
for(slot=0;slot<26;slot++) for(flags=0;flags<256;flags++) {
    actor=D_800CC2D0+slot*0x32C; actor[0x66]=flags;
    for(i=0;i<6;i++) actor[0x1DD+i]=(u8)(flags+37*i);
    parameters[3]=0x12345678; func_1502D54C(slot,parameters);
    for(i=0;i<3;i++) {
        expected=(flags&12)==4 ? 255-(actor[0x1DD+i]+actor[0x1E0+i])/2 : 255;
        if(parameters[i]!=expected) return 1;
    }
    if(parameters[3]!=0x12345678) return 2;
}
for(slot=0;slot<26;slot+=25) for(channel=0;channel<3;channel++)
for(first=0;first<256;first++) for(second=0;second<256;second++) {
    actor=D_800CC2D0+slot*0x32C; actor[0x66]=4;
    actor[0x1DD+channel]=first; actor[0x1E0+channel]=second;
    parameters[3]=0x12345678; func_1502D54C(slot,parameters);
    if(parameters[channel]!=255-(first+second)/2 || parameters[3]!=0x12345678) return 3;
}
''')
        self.receipt('native32', cases=26 * 256 + 2 * 3 * 65536,
            actual_complete_selected_C=True, every_byte_pair_each_channel=True,
            first_last_slots=True, alpha_sentinel_exact=True,
            disjoint_valid_native_inputs_only=True)

    def test_07_fresh_effective_complete_negative_controls(self):
        controls = (
            ('wrong-gate', screen.SELECTED.replace('== 4', '== 8'), fixture(), OUTPUT),
            ('wrong-average', screen.SELECTED.replace('/ 2', '/ 3'), fixture(), OUTPUT),
            ('missing-inversion', screen.SELECTED.replace('255 - parameters', '254 - parameters'), fixture(), OUTPUT),
            ('wrong-blue', screen.SELECTED.replace('actor[0x1E2]', 'actor[0x1E1]'), fixture(), OUTPUT),
            ('alpha-clobber', screen.SELECTED.replace('    if ((actor',
                '    parameters[3] = 255;\n    if ((actor'), fixture(), OUTPUT),
            ('white-order', screen.SELECTED.replace('parameters[0] = parameters[1] = parameters[2] = 255;',
                'parameters[2] = parameters[1] = parameters[0] = 255;'), fixture(flags=0), OUTPUT),
            ('load-order', screen.SELECTED.replace('actor[0x1E0] + actor[0x1DD]',
                'actor[0x1DD] + actor[0x1E0]'), fixture(), OUTPUT),
        )
        for name, body, memory, output in controls:
            _, words = screen.compile_candidate(self.root, self.out, name, body)
            wrong = RGBOracle(words, memory, output=output).run()
            expected, events = reference(memory, output=output)
            self.assertNotEqual((wrong.memory, wrong.events), (expected, events), name)
        self.receipt('negatives', fresh_effective_complete_compiled_controls=len(controls),
            public_semantics_and_physical_order_distinguished=True)

    def test_08_direct_shape_and_retail_coverage(self):
        self.assertEqual((self.meta['body_words'], self.meta['differences'], self.meta['pool_bytes'],
            self.meta['diagnostics']), (57, 0, 0, ''))
        self.assertEqual(self.raw, self.retail)
        self.assertEqual(self.padded, self.retail)
        self.assertEqual(self.current, self.retail)
        self.assertEqual(self.meta['relocations'], {
            32: [('R_MIPS_HI16', 'D_800CC2D0')], 36: [('R_MIPS_LO16', 'D_800CC2D0')]})
        missing = [i for i in range(57) if screen.ENTRY + i * 4 not in self.coverage]
        self.assertEqual(missing, [23, 24, 32, 33, 42, 43, 51])
        self.receipt('shape', words=57, frame=0, diagnostics=0, pool_bytes=0,
            guards=0, insertions=0, omissions=0, padding=0, visited_words=50,
            impossible_negative_byte_sum_corrections=[23, 24, 32, 33, 42, 43],
            ordinary_unreachable_constant_word=51)

    def test_09_whole_linked_installation(self):
        source = (self.root / screen.SOURCE).read_text()
        if screen.ORIGINAL in source:
            self.assertEqual({name: hashlib.sha256((self.root / path).read_bytes()).hexdigest()
                for name, path in self.paths.items()}, self.baseline)
            self.receipt('installation', installed=False, baseline_unchanged=True)
            return
        self.assertEqual(source, screen.install((self.out / 'before-source').read_text()))
        for name in ('guards', 'progress', 'rodata'):
            self.assertEqual((self.root / self.paths[name]).read_bytes(), (self.out / ('before-' + name)).read_bytes())
        before = (self.out / 'before-elf').read_bytes()
        expected = bytearray(before)
        struct.pack_into('>57I', expected, elf_slot_offset(before, screen.ENTRY, 228), *self.retail)
        with patch.multiple(initializer.base, FUNCTION=screen.FUNCTION, ENTRY=screen.ENTRY):
            struct.pack_into('>I', expected, initializer.target_symbol_size_offset(before), 228)
        actual = (self.root / self.paths['elf']).read_bytes()
        em, am = metadata(bytes(expected)), metadata(actual)
        self.assertEqual(em[:4], am[:4])
        for section in em[4:]:
            offset, length = section[4], section[5]
            expected[offset:offset + length] = actual[offset:offset + length]
        self.assertEqual(bytes(expected), actual)
        audit = audit_layout(self.root / self.paths['elf'], self.root / 'conker')
        self.assertTrue(audit['exact'], audit)
        self.receipt('installation', installed=True, only_target_228_bytes_and_extent_changed=True,
            guard_history_conversion_rodata_exact=True, protected_data=audit)


if __name__ == '__main__':
    unittest.main()
