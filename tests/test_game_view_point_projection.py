"""Direct projection words, full connected tail ABI, aliases and bounded faults."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_view_point_projection as source
from tools.tests import game_view_point_projection_oracle as model
from tools.tests import test_game_view_list_setup as assembly
from tools.tests import test_game_actor_burst_consumer_match as tracking
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests import game_view_point_projection_native as native
from tools.tests.test_game_projected_packet_draw import native_command


class ViewPointProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.padded, cls.raw, cls.row = source.qualify(cls.root, cls.out)
        cls.rom = (cls.out / 'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>87I', cls.rom, source.ROM))
        cls.helper = list(struct.unpack_from('>58I', cls.rom, 0xD4E10))
        data, functions = source.build.link_owner(cls.root, cls.out, cls.padded, source.OWNER)
        cls.emitted = list(struct.unpack_from('>87I', data, functions[source.FUNCTION]['value']))

    def receipt(self, name, **row):
        (self.out / (name + '.json')).write_text(json.dumps(row, indent=2) + '\n')

    def test_01_direct87_frame_homes_ten_neighbors_and_all58_helper_words(self):
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences']), (87, 56, 0))
        self.assertEqual(self.row['unchanged_neighbors'], 10)
        self.assertEqual(self.row['diagnostics'], '')
        self.assertFalse(self.row['pools'])
        self.assertEqual(self.raw, self.truth)
        self.assertEqual(self.emitted, self.truth)
        self.assertEqual(len(source.RELOCATIONS), 7)
        before = (self.out / 'before-elf').read_bytes()
        at = elf_slot_offset(before, model.MATRIX, 232)
        self.assertEqual(before[at:at + 232], self.rom[0xD4E10:0xD4EF8])
        for key, name, rom, count in (('point_matrix', 'func_150A7960', 0xD4E10, 40),
                ('point_tail', 'func_150A7A00', 0xD4EB0, 5), ('point_continuation', 'func_150A7A14', 0xD4EC4, 13)):
            obj = assembly.ViewListSetupTests.original.__func__(type(self), 'original-' + name,
                (self.out / ('before-' + key)).read_text(), name)
            data, functions = source.build.link_owner(self.root, self.out, obj, 'generated_D4E10')
            f = functions[name]
            self.assertEqual(f['size'], count * 4)
            self.assertEqual(data[f['value']:f['value'] + f['size']], self.rom[rom:rom + count * 4])
        self.receipt('emission', direct_words=87, frame=56, new_guards=0, no_profile_change=True,
            unchanged_neighbors=10, actual_helper_GNU_and_ELF_exact_words=[40, 5, 13])

    def test_02_connected_guest_reference_private_state_aliases_and_nonfinite(self):
        cases = 0
        seen = set()
        for memory, args in model.corpus():
            expected, transformed = model.reference(memory, args)
            for phase in (0, 8):
                machines = []
                for words in (self.truth, self.raw, self.emitted):
                    m = model.PointProjectionOracle(words, memory, args, self.helper, phase).run()
                    self.assertEqual(model.public(m.memory), model.public(expected), (args, phase))
                    self.assertEqual(len(m.calls), 1)
                    sp = m.before[29] - 56
                    self.assertEqual(m.calls[0], (model.TAIL,
                        ((model.MATRICES + model.half(args[0]) * 64) & 0xFFFFFFFF,
                        *args[1:4], sp + 52, sp + 48, sp + 44, sp + 40)))
                    self.assertEqual(m.observations, [args[1:3]])
                    self.assertEqual(tuple(model.read(m.memory, sp + p) for p in (52, 48, 44)), transformed[:3])
                    seen.update(m.visits)
                    machines.append(m)
                for m in machines[1:]: self.assertEqual(model.state(m), model.state(machines[0]))
                cases += 1
        self.assertEqual(seen & set(range(source.ENTRY, source.ENTRY + 348, 4)), set(range(source.ENTRY, source.ENTRY + 348, 4)))
        self.assertEqual(seen & set(range(model.MATRIX, model.MATRIX + 232, 4)), set(range(model.MATRIX, model.MATRIX + 232, 4)))
        self.receipt('guest', three_way_cases=cases, all87_root_and58_helper_words_visited=True,
            actual_eight_word_tail_ABI_and_F12_F14=True, full_public_private_register_access_state=True,
            zero_nonfinite_reciprocal_and_output_base_page_aliases=True, hardware_FCSR_not_emulated=True)

    def test_03_fail_closed87_words_seven_bindings_extra_pool_and_stale_source(self):
        text, functions, relocations = parse_object(self.obj)
        f = functions[source.FUNCTION]
        for i in range(87):
            bad = bytearray(text); bad[f['value'] + i * 4] ^= 1
            with patch.object(source, 'parse_object', return_value=(bytes(bad), functions, relocations)):
                with self.assertRaises(ValueError): source.checked_object(self.obj)
        for at in (*source.RELOCATIONS, 0):
            bad = dict(relocations); bad[f['value'] + at] = [('R_MIPS_26', 'wrong')]
            with patch.object(source, 'parse_object', return_value=(text, functions, bad)):
                with self.assertRaises(ValueError): source.checked_object(self.obj)
        with patch.object(source, 'sections', return_value={'.rodata':(0, b'bad')}):
            with self.assertRaises(ValueError): source.checked_object(self.obj)
        with self.assertRaises(ValueError): source.recovered_owner(source.recovered_owner((self.out / 'before-frustum_owner').read_text()))
        self.receipt('fail-closed', raw_words=87, bindings=7, extra_binding=1, private_pool=1, stale_source=True)

    def test_04_independent_original_and_direct_C_rebases(self):
        original = assembly.ViewListSetupTests.original.__func__(type(self), 'original-projection',
            (self.out / 'before-point_original').read_text(), source.FUNCTION)
        text, functions, relocations = parse_object(self.padded)
        names = sorted({name for rows in source.RELOCATIONS.values() for _, name in rows})
        for index in range(3):
            entry = 0x15207FF0 + index * 0x100000
            symbols = {name:(entry + 0x10000 if name.startswith('func_') else
                0x80100000 + n * 0x10000 + (0x7FFC, 0x8004, 0x7FD0)[index]) for n, name in enumerate(names)}
            emitted, unresolved = emit_function(text, functions[source.FUNCTION], relocations, source.FUNCTION, symbols)
            self.assertFalse(unresolved)
            asm = self.out / ('direct-rebase-%d.s' % index); asm.write_text(emitted)
            obj = asm.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], capture_output=True, check=True)
            images = []
            for label, path in (('original', original), ('direct', obj)):
                script = self.out / ('rebase-%s-%d.ld' % (label, index))
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                elf = script.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(path)], capture_output=True, check=True)
                images.append(sections(elf)['.text'][1][:348])
            self.assertEqual(images[0], images[1])
        self.receipt('rebases', original_GNU_links=3, independent_C_links=3, all87_words_compared=True, HI_LO_carries=True)

    def test_07_all_connected_memory_fault_prefixes(self):
        cases = 0
        for memory, args in [model.fixture(), model.fixture(1, 1), model.fixture(-1, 255),
                model.fixture(alias=7), model.fixture(alias=8), model.fixture(alias=9)]:
            for phase in (0, 8):
                full = model.PointProjectionOracle(self.truth, memory, args, self.helper, phase).run()
                for fault in range(full.all_accesses):
                    machines = []
                    for words in (self.truth, self.raw, self.emitted):
                        m = model.PointProjectionOracle(words, memory, args, self.helper, phase)
                        m.access_fault = fault
                        with self.assertRaises(tracking.AccessBoundary): m.run()
                        self.assertEqual(m.all_accesses, fault)
                        machines.append(m)
                    for m in machines[1:]: self.assertEqual(model.state(m), model.state(machines[0]))
                    cases += 1
        self.receipt('faults', fired_three_way_prefixes=cases, root_and_real_tail_matrix_continuation_accesses=True,
            hardware_exceptions_not_emulated=True)

    def test_05_native32_typed_caller_separate_adapter_O2_O0_UBSan_controls(self):
        before = (self.out / 'before-frustum_owner').read_text()
        harness = self.out / 'native.c'; harness.write_text(native.program(before))
        helper = self.out / 'native-adapter.c'; helper.write_text(native.HELPER)
        exits = {}
        for name, opt, body in [('o2', '-O2', source.SELECTED), ('o0', '-O0', source.SELECTED)] + [
                (name, '-O2', body) for name, body in native.controls().items()]:
            if name not in ('o2', 'o0'): self.assertNotEqual(body, source.SELECTED)
            unit = self.out / ('native-' + name + '.c'); unit.write_text(native.header(before) + body + '\n')
            exe = unit.with_suffix('.elf')
            built = subprocess.run([*native_command(opt), '-mstackrealign', '-fno-strict-aliasing',
                str(unit.relative_to(self.root)), str(helper.relative_to(self.root)), str(harness.relative_to(self.root)),
                '-o', str(exe.relative_to(self.root))], cwd=self.root, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            ran = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30)
            exits[name] = ran.returncode
            self.assertEqual(ran.returncode, 0 if name in ('o2', 'o0') else 21, (name, ran.stderr))
        self.receipt('native', cases_each=sum(1 for _ in native.cases()), exits=exits,
            typed_seven_word_caller_and_eight_word_semantic_adapter_in_separate_units=True,
            real_SDK_Vp_offsets_and_all784_public_words_canaries=True, UBSan=True, no_fwrapv=True,
            NaN_class_only_for_changed_native_float_outputs=True,
            guest_only_base_page_and_halfword_output_aliases=True)

    def test_06_three_complete_original_callers_real_cuts_and_consumed_outputs(self):
        specs = (('point_caller_a', 'generated_197C20', 'func_1516CC58', 0x19A108, 285, 0x1516CD74, 8),
            ('point_caller_b', 'generated_157840', 'func_1512AD54', 0x158204, 235, 0x1512ADD4, 19),
            ('point_caller_c', 'generated_1A11B0', 'func_151742EC', 0x1A179C, 193, 0x1517447C, 28))
        cases = 0
        for key, owner, name, rom, count, entry, length in specs:
            obj = assembly.ViewListSetupTests.original.__func__(type(self), 'original-' + name,
                (self.out / ('before-' + key)).read_text(), name)
            data, functions = source.build.link_owner(self.root, self.out, obj, owner)
            f = functions[name]; full = data[f['value']:f['value'] + f['size']]
            self.assertEqual(len(full), count * 4)
            self.assertEqual(full, self.rom[rom:rom + count * 4])
            va = int(name[5:], 16)
            cut = list(struct.unpack_from('>%dI' % length, full, entry - va))
            join = entry + length * 4
            class Join(Exception): pass
            class Code(tracking.TrackedCode):
                def __getitem__(self, pc):
                    if pc == join: raise Join
                    return super().__getitem__(pc)
            for raw_view in (-1, 0, 1, 3, 255, 0x10001):
                view = raw_view & 255 if key == 'point_caller_b' else model.half(raw_view) if key == 'point_caller_c' else raw_view
                for pattern in (0, 1):
                    for phase in (0, 8):
                        memory, args = model.fixture(view, pattern=pattern)
                        actor = 0x25000
                        memory.update({actor + i:0xA5 for i in range(0x300)})
                        sp = model.STACK + phase
                        outputs = (sp + 0x54, sp + 0x50, sp + 0x4C) if key == 'point_caller_a' else (
                            (0x800DC1F0, 0x800DC1F4, 0x800DC1F8) if key == 'point_caller_b' else
                            (sp + 0xB4, sp + 0xB0, sp + 0xAC))
                        for address in outputs:
                            for i in range(4): memory.setdefault(address + i, 0xA5)
                        for i, value in enumerate(args[1:4]):
                            model.put(memory, actor + (0x2BC if key == 'point_caller_b' else 12 if key == 'point_caller_a' else 0) + i * 4, value)
                        memory[actor + 0x23D] = raw_view & 255
                        call_args = (view & 0xFFFFFFFF, *args[1:4], *outputs)
                        expected, _ = model.reference(memory, call_args)
                        machines = []
                        for words in (self.truth, self.raw, self.emitted):
                            code = {source.ENTRY + i * 4:w for i, w in enumerate(words)}; code[join] = 0
                            m = model.PointProjectionOracle(cut, memory, call_args, self.helper, phase, entry, code)
                            m.r[16] = m.before[16] = actor
                            if key == 'point_caller_a':
                                m.r[2] = actor; m.r[13] = outputs[0]; m.r[14] = outputs[1]
                            elif key == 'point_caller_b':
                                m.r[24] = outputs[0]; m.r[25] = 0x800E0000; m.f[12] = args[2]
                            else:
                                m.r[2] = raw_view & 0xFFFFFFFF
                                m.r[18] = 0; m.r[24] = memory[model.PAGE]
                            m.code = Code(m.code, m)
                            with self.assertRaises(Join): m.run()
                            self.assertEqual(m.calls[0], (source.ENTRY, call_args))
                            for address in outputs: self.assertEqual(model.read(m.memory, address), model.read(expected, address))
                            if key == 'point_caller_b': self.assertEqual(m.f[8], model.read(expected, outputs[2]))
                            if key == 'point_caller_c':
                                self.assertEqual(m.f[16], model.read(expected, outputs[2]))
                                self.assertEqual(m.f[4], model.read(expected, outputs[0]))
                            self.assertEqual(m.r[29], sp)
                            machines.append(m)
                        for m in machines[1:]: self.assertEqual(model.state(m), model.state(machines[0]))
                        cases += 1
        self.receipt('callers', full_original_words=[285, 235, 193], actual_three_way_cut_cases=cases,
            actual_word_XYZ_stack_outputs_and_delay_argument=True, consumed_output_loads_in_two_callers=True,
            full_caller_or_gameplay_not_claimed=True)

    def test_08_cached_base_and_page_are_effective_functional_negatives(self):
        body = source.SELECTED
        base = body.replace('VIEW_PROJECTIONS_476D0', 'cachedViews').replace('    f32 transformedX;',
            '    ViewProjection476D0 *cachedViews = VIEW_PROJECTIONS_476D0;\n    f32 transformedX;', 1)
        page = body.replace('D_800BE9C0', 'cachedPage').replace('    f32 transformedX;',
            '    u8 cachedPage = D_800BE9C0;\n    f32 transformedX;', 1)
        mismatches = {}
        for name, candidate, aliases in (('cached-base', base, (7, 8)), ('cached-page', page, (9,))):
            words = source.measure(self.root, self.out, 'negative-' + name, candidate)[1]
            differences = 0
            for alias in aliases:
                memory, args = model.fixture(alias=alias)
                wanted, _ = model.reference(memory, args)
                m = model.PointProjectionOracle(words, memory, args, self.helper).run()
                differences += model.public(m.memory) != model.public(wanted)
            self.assertEqual(differences, len(aliases))
            mismatches[name] = differences
        self.receipt('live-load-controls', effective_output_mismatches=mismatches,
            no_unmapped_access_or_compile_failure_counted=True)


if __name__ == '__main__': unittest.main()
