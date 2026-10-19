"""Exact context initialization, live alias order, helpers and retained switch data."""
from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_mode_context_init_candidates as source
from tools.experiments import game_mode_context_init_binding as binding
from tools.experiments import game_mode_context_init_integration as integration
from tools.experiments.game_route_projection_layout_normalizer import relocate
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_mode_context_init_oracle as guest
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.pad_generated_object import emit_padded_assembly, parse_object


def state(m):
    return (m.r, m.f, m.lo, m.condition, m.memory, m.events, m.reads, m.stores,
        m.requested, m.visits, m.calls, m.requests, m.accesses, m.nested_calls, m.rng_calls)


class ModeContextInitMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD / 'test'
        cls.values = source.freeze(cls.root, cls.out)
        cls.obj, _, cls.row = source.compile_candidate(cls.root, cls.out)
        cls.raw, cls.bindings = source.payload(cls.obj)
        cls.canonical, cls.moved = binding.normalize(cls.raw, cls.bindings)
        cls.anchors = {name: int(name[2:], 16) if name.startswith('D_') else int(name[5:], 16)
            for entries in cls.moved.values() for _, name in entries if name != binding.ANCHOR}
        cls.anchors[binding.ANCHOR] = source.TABLE
        cls.words = relocate(cls.canonical, cls.moved, cls.anchors)
        cls.rom = cls.values['conker/conker.us.bin']
        cls.retail = list(struct.unpack_from('>247I', cls.rom, source.ROM))
        guest.TABLE_BYTES = cls.rom[guest.RODATA_ROM:guest.RODATA_ROM + guest.RODATA_SIZE]
        guest.JUMP_BYTES = cls.rom[source.TABLE_ROM:source.TABLE_ROM + 32]
        cls.corpus, cls.receipts = tuple(guest.cases()), {}

    @classmethod
    def tearDownClass(cls):
        (cls.out / 'qualification.json').write_text(json.dumps(cls.receipts, indent=2) + '\n')

    def test_01_complete_source_words_table_and_stale_controls(self):
        self.assertEqual(self.words, self.retail)
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences']), (247, 40, 2))
        self.assertFalse(self.row['diagnostics'])
        self.assertEqual(self.canonical, self.raw)
        self.assertEqual(len(self.bindings), 32)
        pool = sections(self.out / 'selected.elf')['.rodata'][1][:32]
        self.assertEqual(pool, guest.JUMP_BYTES)
        controls = 0
        for at in range(0, 988, 4):
            bad = bytearray(self.raw)
            bad[at] ^= 1
            with self.assertRaises(ValueError): binding.normalize(bytes(bad), self.bindings)
            controls += 1
        for at in self.bindings:
            bad = deepcopy(self.bindings)
            bad[at] = [('R_MIPS_26', source.FUNCTION)]
            with self.assertRaises(ValueError): binding.normalize(self.raw, bad)
            controls += 1
        self.receipts.update(words=247, frame=40, all8_switch_targets_exact=True,
            raw_binding_stale_controls=controls, instruction_layout_guards=0, table_binding_rows=2)

    def test_02_full_public_reference_literal_states_and_live_selector_alias(self):
        pairs, coverage = 0, set()
        for n, case in enumerate(self.corpus):
            memory = guest.fixture(case)
            wanted, calls, stores = guest.reference(memory, case)
            for phase in (0, 8):
                models = [guest.InitModel(words, memory, case, phase).run() for words in (self.retail, self.words)]
                with self.subTest(case=n, phase=phase):
                    self.assertEqual(state(models[0]), state(models[1]))
                    self.assertEqual(models[0].r[2], 0)
                    self.assertEqual(guest.public(models[0].memory), guest.public(wanted))
                    self.assertEqual(models[0].calls, calls)
                    writes = [(a, value, size) for a, size, value in models[0].stores
                        if not guest.STACK - 0x800 <= a < guest.STACK + 0x100]
                    self.assertEqual(writes, stores)
                coverage.update(models[0].visits)
                pairs += 1
        self.assertEqual(len(coverage), 247)
        self.receipts.update(fixtures=len(self.corpus), completed_pairs=pairs,
            all247_retail_words_visited=True, all256_signed_selector_patterns=True,
            complete_live_mode_alias_cases=5, signed_out_of_range_tables_use_explicit_backing=True)

    def test_03_fired_private_cuts_and_effective_flag_order_negative(self):
        cases = (guest.Case(), guest.Case(found=False), guest.Case(key=0xBC),
            guest.Case(key=0xBE, weight_change=1), guest.Case(mode_alias=True))
        cuts = 0
        for case in cases:
            memory = guest.fixture(case)
            for phase in (0, 8):
                complete = guest.InitModel(self.retail, memory, case, phase).run()
                for cut in range(complete.accesses):
                    models = []
                    for words in (self.retail, self.words):
                        model = guest.InitModel(words, memory, case, phase)
                        model.fault = cut
                        with self.assertRaises(guest.core.AccessFault): model.run()
                        self.assertEqual(model.accesses, cut)
                        models.append(model)
                    self.assertEqual(state(models[0]), state(models[1]))
                    cuts += 1
        case = guest.Case()
        memory = guest.fixture(case)
        complete = guest.InitModel(self.retail, memory, case).run()
        cut = complete.requests.index(('W', guest.banks(case)[0] + 0x1703, 1)) + 1
        wrong = self.words.copy()
        wrong[0xF0 // 4] = (wrong[0xF0 // 4] & 0xFFFF0000) | 0x1702
        wrong[0xFC // 4] = (wrong[0xFC // 4] & 0xFFFF0000) | 0x1703
        self.assertEqual(guest.public(guest.InitModel(wrong, memory, case).run().memory), guest.public(complete.memory))
        states = []
        for words in (self.retail, wrong):
            model = guest.InitModel(words, memory, case)
            model.fault = cut
            with self.assertRaises(guest.core.AccessFault): model.run()
            states.append(guest.public(model.memory))
        self.assertNotEqual(*states)
        self.receipts.update(fired_private_cut_pairs=cuts, flag_order_negative_cut=cut,
            flag_order_negative_has_equal_final_public_state=True)

    def test_04_native32_complete_buffers_and_effective_negatives(self):
        def run(name, body, opt='-O2'):
            path, exe = self.out / (name + '.c'), self.out / name
            path.write_text(guest.native_harness(body, self.corpus))
            command = native_command(opt) + ['-fno-strict-aliasing', '-mstackrealign', '-o', str(exe), str(path)]
            result = subprocess.run(command, cwd=self.root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return subprocess.run([str(exe)], cwd=self.root, capture_output=True).returncode
        for opt in ('-O0', '-O2', '-O3'):
            self.assertEqual(run('native' + opt[1:], source.SELECTED, opt), 0)
        cached = source.SELECTED.replace('    s32 key;', '    s32 key;\n    s8 mode;').replace(
            '    func_1508BC20();', '    func_1508BC20();\n    mode = D_800E0BD0;').replace('[D_800E0BD0]', '[mode]')
        late = source.SELECTED.replace('    func_1508BC20();\n', '', 1)
        at = late.rfind('    return 0;')
        late = late[:at] + '    func_1508BC20();\n' + late[at:]
        negatives = {
            'clear-missing': source.SELECTED.replace('if (data == NULL) {', 'if (data == NULL) { D_800D23B0 = 0;'),
            'accept-BC': source.SELECTED.replace('        case 0xBE:', '        case 0xBC:\n        case 0xBE:'),
            'live-key': source.SELECTED.replace('switch (key)', 'switch (D_800D2E48)'),
            'cached-selector': cached,
            'unsigned-selector': source.SELECTED.replace('[D_800E0BD0]', '[(u8)D_800E0BD0]'),
            'unsigned-rate': source.SELECTED.replace('= D_800872F0[D_800E0BD0]', '= (u8)D_800872F0[D_800E0BD0]'),
            'short-loop': source.SELECTED.replace('offset < 0x40', 'offset < 0x3C'),
            'zero-seeds': source.SELECTED.replace('= D_800872F8[D_800E0BD0]', '= 0.0f'),
            'late-weights': late,
        }
        for name, body in negatives.items():
            self.assertNotEqual(body, source.SELECTED)
            self.assertNotEqual(run('negative-' + name, body), 0, name)
        self.receipts.update(native32_profiles=3, native32_fixtures=len(self.corpus), native32_effective_negatives=9,
            native_table_views_preserve_values_without_claiming_cross_view_aliases=True)

    def test_05_actual_lookup_wrapper_and_cyclic_weights(self):
        lookup = struct.unpack_from('>15I', self.rom, 0x1509B570 - 0x15000000 + 0x2D4B0)
        weights = struct.unpack_from('>189I', self.rom, 0xB90D0)
        code = {guest.LOOKUP + i * 4: w for i, w in enumerate(lookup)}
        code.update({guest.WEIGHTS + i * 4: w for i, w in enumerate(weights)})
        runs = 0
        for count in (0, 2):
            for case in (guest.Case(), guest.Case(found=False), guest.Case(key=0xBC)):
                memory = guest.fixture(case)
                meta = guest.banks(case)[0] - 32
                memory.update({meta + i: 0xA5 for i in range(32)})
                guest.put(memory, meta + 10, 32, 2)
                guest.put(memory, guest.COUNT, count, 1)
                wanted, calls, _ = guest.reference(memory, case, real_weights=count)
                for phase in (0, 8):
                    models = [guest.InitModel(words, memory, case, phase, code).run() for words in (self.retail, self.words)]
                    self.assertEqual(state(models[0]), state(models[1]))
                    self.assertEqual(guest.public(models[0].memory), guest.public(wanted))
                    self.assertEqual(models[0].calls, calls)
                    self.assertEqual(models[0].nested_calls, [(guest.FIND, case.key)])
                    self.assertEqual(models[0].rng_calls, count * 2 if case.found and case.key != 0xBC else 0)
                    runs += 2
        self.receipts.update(actual_lookup_weight_runs=runs, lookup_wrapper_words=15, cyclic_weight_words=189,
            connected_weight_counts=[0, 2], RNG_provider_value=.25, not_full_lookup_or_RNG_or_gameplay=True)

    def test_06_actual_caller_and_return_tail(self):
        rom = self.rom
        prefix = struct.unpack_from('>4I', rom, 0xCB534)
        tail = struct.unpack_from('>4I', rom, 0xCB87C)
        code = {0x1509E084 + i * 4: w for i, w in enumerate(prefix)}
        code.update({0x1509E3CC + i * 4: w for i, w in enumerate(tail)})
        class Caller(guest.InitModel):
            def record_call(self, target):
                if target == source.ENTRY:
                    self.caller_args.append(())
                    return
                super().record_call(target)
        runs = 0
        for case in (guest.Case(), guest.Case(found=False), guest.Case(key=0xBC), guest.Case(weight_change=1)):
            for phase in (0, 8):
                models = []
                for words in (self.retail, self.words):
                    model = Caller(words, guest.fixture(case), case, phase, code)
                    model.entry = 0x1509E084
                    sp = model.r[29]
                    guest.put(model.memory, sp + 0x20, model.before[16], 4)
                    guest.put(model.memory, sp + 0x24, 0xDEAD0000, 4)
                    model.before[29] = sp + 0x48
                    model.r[16] = 0x12345678
                    model.run()
                    self.assertEqual(model.r[2], 0)
                    self.assertEqual(model.caller_args, [()])
                    models.append(model)
                    runs += 1
                self.assertEqual(state(models[0]), state(models[1]))
        self.receipts.update(actual_caller_return_runs=runs, actual_case_prefix_and_shared_return_tail=True,
            not_full_command_dispatch=True)

    def test_07_independent_GNU_code_and_table_maps(self):
        asm = self.values['conker/asm/B3020.s'].decode()
        lo = asm.index('glabel ' + source.FUNCTION + '\n')
        hi = asm.index('endlabel ' + source.FUNCTION, lo)
        data = self.values['conker/asm/data/2424E0.rodata.s'].decode()
        data = data.split('dlabel jtbl_8009DA24\n', 1)[1].split('enddlabel jtbl_8009DA24', 1)[0]
        prelude = (self.root / 'conker/include/asm_processor_prelude.inc').read_text()
        retail = self.out / 'GNU-retail.s'
        retail.write_text(prelude + '\n.text\n' + asm[lo:hi] + '\n.section .rodata\n.globl ' + binding.ANCHOR +
            '\n' + binding.ANCHOR + ':\n' + data)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
            '-I', str(self.root / 'conker/include'), '-o', str(retail.with_suffix('.o')), str(retail)], check=True, capture_output=True)
        triples = 0
        for n, (entry, delta) in enumerate(((source.ENTRY, 0), (0x1621FFF4, 0x115CAC), (0x18FFF000, 0x235CB0))):
            anchors = {name: value + delta for name, value in self.anchors.items() if name != binding.ANCHOR}
            table = source.TABLE + delta
            anchors['jtbl_8009DA24'] = table
            images, pools = [], []
            for obj in (retail.with_suffix('.o'), self.obj):
                script = self.out / (obj.stem + '-GNU-%d.ld' % n)
                elf = script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x%X : SUBALIGN(4) { *(.rodata) } }\n' % (entry, table))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in anchors.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
                sections_ = sections(elf)
                images.append(list(struct.unpack('>247I', sections_['.text'][1][:988])))
                pools.append(sections_['.rodata'][1][:32])
            self.assertEqual(*images)
            self.assertEqual(*pools)
            moved = {name: getattr(guest, name) + delta for name in ('KEY', 'CONTEXT', 'MODE', 'LIMITS', 'VALUES', 'RATES',
                'LOOKUP', 'WEIGHTS', 'RODATA', 'COUNT', 'FIND', 'RANDOM', 'JUMP')}
            moved['JUMP_BYTES'] = pools[0]
            with patch.multiple(guest, **moved):
                for case in self.corpus[::37]:
                    memory = guest.fixture(case)
                    wanted, calls, _ = guest.reference(memory, case)
                    models = [guest.InitModel(words, memory, case, entry=entry).run() for words in images]
                    self.assertEqual(state(models[0]), state(models[1]))
                    self.assertEqual(guest.public(models[0].memory), guest.public(wanted))
                    self.assertEqual(models[0].calls, calls)
                    triples += 1
        self.receipts.update(independent_GNU_maps=3, rebased_pairs=triples,
            independent_source_and_retail_code_and_all8_table_entries_exact=True)

    def test_08_owner_guards_and_first_link_scope(self):
        out = self.root / integration.BUILD
        self.assertTrue(json.loads((out / 'qualification.json').read_text())['all73_addresses_fixed'])
        self.assertTrue(json.loads((out / 'make-shadow.json').read_text())['padded_code_and_metadata_equal'])
        before = self.values['conker/build/conker.us.elf']
        first = (out / 'first-linked.elf').read_bytes()
        truth = self.rom[source.ROM:source.ROM + 988]
        integration.check_image(before, first, truth)
        at = elf_slot_offset(before, source.ENTRY, 988)
        symbol = next(r[0] for r in symbol_rows(before) if r[1] == source.FUNCTION)
        for offset in (at, at - 4, symbol + 8, len(first) - 1):
            bad = bytearray(first)
            bad[offset] ^= 1
            with self.assertRaises(ValueError): integration.check_image(before, bytes(bad), truth)
        reader = lambda data: list(csv.DictReader(io.StringIO(data.decode())))
        old = reader(self.values['conker/retail_word_patches.us.csv'])
        new = reader((out / 'qualified-guards.csv').read_bytes())
        self.assertEqual(len(new) - len(old), 2)
        changed = [(a['function'], a['offset'], key) for a, b in zip(old, new) for key in a if a[key] != b[key]]
        self.assertEqual(changed, [('func_1508E6D0', '0x18', 'expected'), ('func_1508E780', '0x2C', 'expected')])
        self.assertEqual([r['function'] for r in new[-2:]], [source.FUNCTION] * 2)
        fields = list(new[0])
        for name, function, offset, field, value in (
                ('target-binding', source.FUNCTION, '0x38', 'expected_relocations', 'R_MIPS_HI16:D_800D23B0'),
                ('old-neighbor-addend', 'func_1508E6D0', '0x18', 'expected', '0x8C2E0008')):
            rows = deepcopy(new)
            row = next(r for r in rows if r['filename'] == source.OWNER and r['function'] == function and r['offset'] == offset)
            row[field] = value
            stream = io.StringIO(newline='')
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
            manifest = self.out / ('stale-' + name + '.csv')
            manifest.write_text(stream.getvalue())
            with self.assertRaises(ValueError):
                emit_padded_assembly(out / 'after-primary.o', self.root / 'conker/asm/B3020.s',
                    function_objects={n: out / 'after-normal.o' for n in integration.NORMAL_FUNCTIONS},
                    word_patches_path=manifest, filename=source.OWNER)
        self.receipts.update(strict_image_corruption_controls=4, changed_historical_guard_cells=changed,
            unchanged_padded_neighbors=72, new_table_binding_guards=2, actual_padder_stale_controls=2)

    def test_09_actual_padded_neighbor_switch_regressions(self):
        from tools.tests import test_game_route_limit_switch_match as limits
        from tools.tests import test_game_route_mode_code_match as modes
        out = self.root / integration.BUILD
        image = sections(out / 'qualified-padded.elf')['.text'][1]
        functions = parse_object(out / 'qualified-padded.o')[1]
        counts = {}
        for module, model_type, size in ((limits, limits.SwitchModel, 44), (modes, modes.ModeModel, 71)):
            info = functions[module.source.FUNCTION]
            words = list(struct.unpack_from('>%dI' % size, image, info['value']))
            retail = list(struct.unpack_from('>%dI' % size, self.rom, module.source.ROM))
            self.assertEqual(words, retail)
            table = self.rom[module.source.TABLE_ROM:module.source.TABLE_ROM + (252 if module is limits else 228)]
            probes = limits.cases()
            runs = 0
            for mode in ((0,) if module is limits else modes.MODES):
                for value in probes:
                    memory = limits.fixture(table) if module is limits else modes.fixture(table, mode)
                    models = [model_type(code, memory, (value,), entry=module.source.ENTRY).run() for code in (retail, words)]
                    self.assertEqual((models[0].r, models[0].memory, models[0].events),
                        (models[1].r, models[1].memory, models[1].events))
                    expected = limits.LIMITS.get(value, 100000) if module is limits else modes.expected(value, mode)
                    self.assertEqual(models[0].r[2], expected)
                    runs += 1
            counts[module.source.FUNCTION] = runs
        self.receipts.update(fresh_padded_neighbor_pairs=counts,
            neighbor_regression_uses_newly_padded_bytes_and_original_tables=True)

    def test_10_installed_image_and_scope(self):
        audit = integration.audit(self.root, self.root / integration.BUILD)
        image = (self.root / 'conker/build/conker.us.elf').read_bytes()
        at = elf_slot_offset(image, source.ENTRY, 988)
        self.assertEqual(image[at:at + 988], self.rom[source.ROM:source.ROM + 988])
        self.assertEqual((audit['functions'], audit['other_bodies_fixed']), (6057, 6056))
        self.assertTrue(audit['all_addresses_fixed'])
        self.assertTrue(audit['exact_first_link_reproduced'])
        self.receipts.update(installed_words=247, installed_other_bodies_fixed=6056,
            installed_all6057_addresses_fixed=True, installed_strict_first_link_identity=True,
            protected_game_data_bytes=189088, protected_game_data_owners=720)


if __name__ == '__main__':
    unittest.main()
