"""Qualify complete semantic C and its explicit source-derived isolated layout."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch
import unittest

from tools.experiments import game_route_record_reload as source
from tools.experiments import game_route_record_reload_layout as layout
from tools.tests import test_game_route_record_capture as captured
from tools.tests import test_game_route_record_setup as previous
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.alternative_source_draft_word_screen import emit_function


class ReturnStopOracle(captured.CaptureOracle):
    def execute(self, word):
        if self.current_pc == source.ENTRY + 149 * 4:
            self.return_stop_fired = True
            raise previous.WindowStop
        return super().execute(word)


class RouteRecordReloadTests(captured.RouteRecordCaptureTests):
    @classmethod
    def setUpClass(cls):
        with patch.object(captured, 'source', source):
            super().setUpClass()
        cls.raw, cls.bindings = source.checked(cls.obj)
        cls.normalized, cls.moved = layout.normalize(cls.raw, cls.bindings)
        cls.anchors = {row[1]: row[2][1] for row in
                       source.installed.prior.symbol_rows(cls.values['conker/build/conker.us.elf'])}
        cls.normal = layout.relocate(cls.normalized, cls.moved, cls.anchors)

    def run(self, result=None):
        with patch.object(captured, 'source', source):
            return super().run(result)

    def test_07_actual_S7_capture_private_seed_lifetime_and_effective_old_control(self):
        # Preserve the prior 43-word-difference negative and its immutable source pin.
        with patch.object(captured, 'source', source.source):
            super().test_07_actual_S7_capture_private_seed_lifetime_and_effective_old_control()

    def test_09_all_words_bindings_file_free_recipe_and_independent_assembly(self):
        self.assertEqual(self.normal, self.truth)
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences']), (160, 96, 37))
        self.assertEqual(sorted(layout.origins()), list(range(160)))
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('File-free normalization')), \
                patch.object(Path, 'read_text', side_effect=AssertionError('File-free normalization')):
            self.assertEqual(layout.normalize(self.raw, self.bindings), (self.normalized, self.moved))
        original = assembly.ViewListSetupTests.original.__func__(self, 'original-route-setup',
            self.values['conker/asm/B3020.s'].decode(), source.FUNCTION)
        text, functions, rel = source.parse_object(original)
        f = functions[source.FUNCTION]
        self.assertEqual(text[f['value']:f['value'] + f['size']], self.normalized)
        self.assertEqual({at - f['value']: rows for at, rows in rel.items()
            if f['value'] <= at < f['value'] + f['size']}, self.moved)
        self.receipt('isolated-layout', words=160, raw_differences=37, normalized_differences=0,
            normalized_sha256=layout.NORMALIZED_SHA, bindings=26, file_free=True,
            all_source_slots_accounted=True, all_original_operations_retained=False,
            coalesced_copies=1, return_restores_derived_from_C_epilogue=1,
            selected_FF_rejoin_speculative_read_restored=True, inserted_or_omitted_slots=0)

    def test_10_normalized_full_states_prefixes_return_restore_and_join_controls(self):
        count = 0
        for index, p in enumerate(previous.corpus()):
            memory, args, allocation = previous.fixture(*p)
            machines = [captured.CaptureOracle(words, memory, args, self.helpers, allocation, (index & 1) * 8).run()
                        for words in (self.normal, self.truth)]
            a, b = machines
            self.assertEqual((a.memory, a.complete_trace, a.r, a.f, a.calls, a.current_pc, a.delay_of),
                             (b.memory, b.complete_trace, b.r, b.f, b.calls, b.current_pc, b.delay_of))
            count += 1
        fixtures = ((3, 0, 2, 1, 7, 0, 0, 0, 4), (4, 1, 0, 0, 7, 0, 0, 0, 128),
                    (3, 0, 2, 1, 7, 1, 0, 0, 4), (3, 0, 2, 1, 7, 2, 0, 0, 4))
        cuts = 0
        for p in fixtures:
            memory, args, allocation = previous.fixture(*p)
            full = captured.CaptureOracle(self.truth, memory, args, self.helpers, allocation).run()
            for cut in range(full.all_accesses):
                machines = []
                for words in (self.normal, self.truth):
                    m = captured.CaptureOracle(words, memory, args, self.helpers, allocation)
                    m.access_fault = cut
                    with self.assertRaises(previous.base.base.faults.AccessBoundary):
                        m.run()
                    machines.append(m)
                a, b = machines
                self.assertEqual((a.memory, a.complete_trace, a.r, a.f, a.calls, a.current_pc, a.delay_of),
                                 (b.memory, b.complete_trace, b.r, b.f, b.calls, b.current_pc, b.delay_of))
                cuts += 1
        memory, args, allocation = previous.fixture(gate=4)
        wrong = list(self.normal)
        wrong[74] = (23 << 21) | (23 << 11) | 37
        returns = []
        for words in (self.normal, wrong):
            m = ReturnStopOracle(words, memory, args, self.helpers, allocation)
            m.return_stop_fired = False
            with self.assertRaises(previous.WindowStop):
                m.run()
            self.assertTrue(m.return_stop_fired)
            returns.append(m.r[31])
        self.assertEqual(returns, [0xDEAD0000, source.ENTRY + 68 * 4])
        memory, args, allocation = previous.fixture(gate=2)
        wrong = list(self.normal)
        wrong[57] += 1
        join = [captured.CaptureOracle(words, memory, args, self.helpers, allocation).run()
                for words in (self.normal, wrong)]
        self.assertEqual([m.all_accesses for m in join], [37, 36])
        self.assertEqual(join[0].memory, join[1].memory)
        self.assertNotEqual(join[0].complete_trace, join[1].complete_trace)
        memory, args, allocation = previous.fixture(length=4)
        m = captured.CaptureOracle(self.normal, memory, args, self.helpers, allocation).run()
        self.assertEqual(m.post_reload_roles, [(2, 3)] * 3)
        raw_receipt = (self.out / 'caller.json').read_bytes()
        old_words = self.words
        try:
            self.words = self.normal
            previous.RouteRecordSetupTests.test_05_whole_Game_call_scan_and_three_argument_window(self)
            caller = json.loads((self.out / 'caller.json').read_text())
            caller['proof_model'] = 'normalized C'
            (self.out / 'normalized-caller.json').write_text(json.dumps(caller, indent=2) + '\n')
        finally:
            self.words = old_words
            (self.out / 'caller.json').write_bytes(raw_receipt)
        self.receipt('normalized-guest', paired_cases=count, fired_all_state_prefixes=cuts,
            both_complete_memory_and_GPR_FPR_PC_delay_states_equal=True,
            synthetic_not_hardware_traps=True, two_effective_return_and_join_controls=True,
            return_control_values=returns, later_S7_FP=[2, 3], normalized_caller_windows=41)

    def test_11_actual_private_mixed_profile_padding(self):
        prior = source.installed.prior
        before = self.values['conker/src/game/generated_B3020.c'].decode()
        body = source.recovered_owner(before, source.selected())
        normal, nd = prior.compile_profile(self.root, self.out, body, 'override-normal', True)
        old_normal, od = prior.compile_profile(self.root, self.out, before, 'baseline-normal', True)
        self.assertFalse(nd or od)
        self.assertEqual(source.installed.source.model.same_functions(old_normal, normal, (source.FUNCTION,)), 72)
        self.assertEqual(normalized_pools(old_normal), normalized_pools(normal))
        prior.candidate.checked(normal)
        prefix = self.values['conker/retail_word_patches.us.csv']
        guards = layout.private_guards(prefix, self.raw, self.bindings)
        self.assertTrue(guards.startswith(prefix))
        old_path, path = self.out / 'baseline-guards.csv', self.out / 'private-guards.csv'
        old_path.write_bytes(prefix)
        path.write_bytes(guards)
        old = prior.padded(self.root, self.out, self.out / 'owner-before.o', 'baseline-padded', old_path, old_normal)
        new = prior.padded(self.root, self.out, self.obj, 'qualified-padded', path, normal)
        a, fa = prior.link_owner(self.root, self.out, old, source.OWNER)
        b, fb = prior.link_owner(self.root, self.out, new, source.OWNER)
        at = fb[source.FUNCTION]['value']
        self.assertEqual(b[at:at + 640], self.values['conker/conker.us.bin'][source.ROM:source.ROM + 640])
        self.assertEqual((a[:at], a[at + 640:]), (b[:at], b[at + 640:]))
        self.assertEqual(set(fa), set(fb))
        for name in fa:
            self.assertEqual(fa[name]['value'], fb[name]['value'])
            if name != source.FUNCTION:
                self.assertEqual(fa[name], fb[name])
        self.assertEqual(normalized_pools(old), normalized_pools(new))
        self.receipt('padder', private_rows=160, prefix_bytes=len(prefix), primary_and_normal_neighbors=72,
            all_other_owner_bytes_addresses_extents_fixed=True, original_projection_override_preserved=True)

    def test_12_recipe_inputs_and_all_layout_choices_fail_closed(self):
        count = 0
        for i in range(160):
            bad = bytearray(self.raw)
            bad[i * 4] ^= 1
            with self.assertRaises(ValueError):
                layout.normalize(bytes(bad), self.bindings)
            count += 1
        for at in self.bindings:
            bad = dict(self.bindings)
            bad[at] = []
            with self.assertRaises(ValueError):
                layout.normalize(self.raw, bad)
            count += 1
        choices = 0
        for name in ('SAVED_ROLES', 'SPECIAL'):
            values = getattr(layout, name)
            for key, value in values.items():
                for field, register in list(value.items()) if isinstance(value, dict) else [(None, value)]:
                    bad = dict(values)
                    if field is None:
                        bad[key] = register ^ 1
                    else:
                        bad[key] = dict(value)
                        bad[key][field] = register ^ 1
                    with patch.object(layout, name, bad), self.assertRaises(ValueError):
                        layout.normalize(self.raw, self.bindings)
                    choices += 1
        for key in layout.COMMUTED:
            with patch.object(layout, 'COMMUTED', tuple(i for i in layout.COMMUTED if i != key)), self.assertRaises(ValueError):
                layout.normalize(self.raw, self.bindings)
            choices += 1
        for key in ('COPY_ORIGIN', 'RESTORE_ORIGIN', 'RETURN_BRANCH', 'RETURN_TARGET', 'REJOIN_BRANCH', 'REJOIN_ORIGIN'):
            with patch.object(layout, key, getattr(layout, key) + 1), self.assertRaises(ValueError):
                layout.normalize(self.raw, self.bindings)
            choices += 1
        with patch.object(layout, 'origins', return_value=list(range(160))), self.assertRaises(ValueError):
            layout.normalize(self.raw, self.bindings)
        self.receipt('layout-controls', raw_and_binding_controls=count, recipe_controls=choices + 1)

    def test_13_independent_GNU_rebases_and_code_rebased_guest(self):
        text, missing = emit_function(self.normalized, {'value': 0, 'size': 640}, self.moved,
                                      source.FUNCTION, self.anchors)
        self.assertFalse(missing)
        unit = self.out / 'normalized-rebase.s'
        obj = unit.with_suffix('.o')
        unit.write_text(text)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(unit)],
                       check=True, capture_output=True)
        referenced = {name for entries in self.moved.values() for _, name in entries}
        fixtures = list(previous.corpus())[::17]
        links, guests = 0, 0
        placements = ((source.ENTRY, None), (0x16218004, None), (0x18FFF000, None),
                      (0x16218004, 0x23457FFC), (0x18FFF000, 0x23458004))
        for placement, (entry, global_base) in enumerate(placements):
            anchors = {name: self.anchors[name] for name in referenced}
            if global_base is not None:
                for i, name in enumerate(sorted(n for n in anchors if n.startswith('D_'))):
                    anchors[name] = global_base + i * 0x100
            bodies = []
            for label, binary in (('retail', self.out / 'original-route-setup.o'), ('normalized', obj)):
                script = self.out / ('rebase-%d-%s.ld' % (placement, label))
                elf = script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                subprocess.run(['mips-linux-gnu-ld', '-T', str(script), '-e', source.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in sorted(anchors.items())],
                    '-o', str(elf), str(binary)], check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>160I', source.sections(elf)['.text'][1])))
                links += 1
            self.assertEqual(bodies[0], bodies[1])
            self.assertEqual(bodies[0], layout.relocate(self.normalized, self.moved, anchors))
            if global_base is not None:
                continue
            for index, p in enumerate(fixtures):
                memory, args, allocation = previous.fixture(*p)
                a, b = [captured.CaptureOracle(words, memory, args, self.helpers, allocation,
                            (index & 1) * 8, entry).run() for words in bodies]
                self.assertEqual((a.memory, a.complete_trace, a.r, a.f, a.calls, a.current_pc, a.delay_of),
                                 (b.memory, b.complete_trace, b.r, b.f, b.calls, b.current_pc, b.delay_of))
                guests += 1
        self.receipt('rebases', independent_GNU_links=links, code_placements=3, static_global_placements=2,
            paired_code_rebased_guest_cases=guests, all_words_and_bindings_equal=True,
            HI16_LO16_carry_boundaries=True, guest_execution_of_changed_globals_not_claimed=True)

    def test_14_completed_compiler_wire_provenance_and_effective_controls(self):
        audit = source.audit_wire(self.root)
        self.assertTrue(audit['code_unchanged'] and audit['reused_completed_capture'])
        work = self.root / source.BUILD / 'selected-wire'
        complete = json.loads((work / 'route-wire.json').read_text())['complete']
        self.assertEqual(source.wire_facts(complete, self.raw), audit['facts'])
        records = complete['optimizer_records']
        loads = [i for i, r in enumerate(records) if r['name'] == 'lod' and r['storage'] == 'M'
                 and r['offset'] in (-23, -24)]
        a, b = loads
        changes = ((a, 'offset', -24), (b, 'offset', -23), (a, 'dtype', 'J'),
                   (a, 'block', 769), (a + 2, 'offset', 3), (a + 3, 'offset', 3),
                   (a + 4, 'offset', 23), (b + 2, 'offset', 30), (b + 2, 'length', 1))
        for index, key, value in changes:
            changed = json.loads(json.dumps(complete))
            changed['optimizer_records'][index][key] = value
            with self.assertRaises(ValueError):
                source.wire_facts(changed, self.raw)
        changed = dict(complete, code_unchanged=False)
        with self.assertRaises(ValueError):
            source.wire_facts(changed, self.raw)
        bad = bytearray(self.raw)
        bad[0] ^= 1
        with self.assertRaises(ValueError):
            source.wire_facts(complete, bytes(bad))
        log = (work / 'debugger.txt').read_text()
        for inferior in (2, 3, 4, 5, 1):
            with self.assertRaises(ValueError):
                source.lifecycle(self.root.resolve(), log.replace(
                    'TRACE_EXIT inferior=%d code=0' % inferior,
                    'TRACE_EXIT inferior=%d code=23' % inferior, 1))
        original = Path.read_bytes
        for name in ('frontend.ucode', 'optimizer.ucode', 'ucode-table.json', 'ucode-types.json'):
            target = work / name
            def corrupt(path, *args, **kwargs):
                data = original(path, *args, **kwargs)
                return data + b'\0' if path == target else data
            with patch.object(Path, 'read_bytes', corrupt), patch.object(Path, 'write_text', return_value=0), \
                    self.assertRaises(ValueError):
                source.audit_wire(self.root)
        with patch.object(source.frontend, 'compiler_fingerprints', return_value={}), \
                patch.object(Path, 'write_text', return_value=0), self.assertRaises(ValueError):
            source.audit_wire(self.root)
        self.receipt('wire-controls', semantic_controls=len(changes) + 2, lifecycle_controls=5,
            payload_or_fingerprint_controls=5, four_exact_compiler_fingerprints=True,
            all_children_and_driver_exit_zero=True, final_inferior_null=True,
            normal_object_complete_code_functions_bindings_pools_equal=True,
            facts=audit['facts'], no_new_debugger_capture=True)
