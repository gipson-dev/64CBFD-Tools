"""Qualify the complete two-save C candidate and its isolated closed layout."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_route_vector_layout as layout
from tools.tests import test_game_route_vector_builder as vector
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.game_owner_pool import normalized_pools

source = layout.source


class FullTraceOracle(vector.VectorOracle):
    def __init__(self, *args, **kwargs):
        self.complete_trace = []
        super().__init__(*args, **kwargs)

    def get(self, at, n):
        value = super().get(at, n)
        self.complete_trace.append(('R', at, n, value))
        return value

    def put(self, at, value, n):
        super().put(at, value, n)
        self.complete_trace.append(('W', at, n, value & ((1 << (8 * n)) - 1)))


class RouteVectorSavedRoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        cls.obj, cls.words, cls.row = source.qualify(cls.root, cls.out)
        cls.values = source.freeze(cls.root, cls.out)
        cls.raw, cls.bindings = source.checked(cls.obj)
        cls.normalized, cls.moved = layout.normalize(cls.raw, cls.bindings)
        cls.normal = layout.relocate(cls.normalized, cls.moved, {'D_800D2350': vector.GLOBAL})
        cls.truth = list(struct.unpack_from('>83I', cls.values['conker/conker.us.bin'], source.model.ROM))

    def receipt(self, name, **data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def test_01_all_words_bindings_origins_and_file_free_layout(self):
        self.assertEqual(self.normal, self.truth)
        self.assertEqual((self.row['words'], self.row['frame'], self.row['differences'], self.row['saved']),
                         (83, 16, 56, [(17, 12), (16, 8)]))
        self.assertEqual(sorted(layout.origins()), list(range(83)))
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('File-free layout')), \
                patch.object(Path, 'read_text', side_effect=AssertionError('File-free layout')):
            self.assertEqual(layout.normalize(self.raw, self.bindings), (self.normalized, self.moved))
        context = type('Context', (), dict(root=self.root, out=self.out))
        original = assembly.ViewListSetupTests.original.__func__(context, 'original-vector',
            self.values['conker/asm/B3020.s'].decode(), source.model.FUNCTION)
        text, functions, rel = source.model.parse_object(original)
        f = functions[source.model.FUNCTION]
        self.assertEqual(text[f['value']:f['value'] + f['size']], self.normalized)
        self.assertEqual({at - f['value']: value for at, value in rel.items()
                          if f['value'] <= at < f['value'] + f['size']}, self.moved)

    def test_02_full_memory_access_order_private_homes_and_ABI(self):
        cases = list(itertools.product((0, 5, 15), range(243), (0,), (0x3F000000, 0xBF000000), (0,)))
        cases.extend((mask, pattern, 0, speed, alias) for mask, pattern, speed, alias in itertools.product(
            (0, 5), (2, 242), (0x3F000000, 0x3F800000), range(1, 11)))
        cases.extend((0, 242, coordinate, speed, 0) for coordinate, speed in itertools.product(range(7), vector.SPEEDS))
        for case, args in enumerate(cases):
            memory, parameters = vector.fixture(*args)
            expected, trace = vector.reference(memory, parameters)
            results = []
            for words in (self.words, self.normal):
                m = FullTraceOracle(words, memory, parameters, (case & 1) * 8).run()
                self.assertEqual((vector.public(m.memory), m.trace), (vector.public(expected), trace), args)
                self.assertEqual(m.calls, [])
                self.assertEqual(m.f[20:], m.saved_f)
                for register in (*range(16, 24), 28, 29, 30, 31):
                    self.assertEqual(m.r[register], m.before[register])
                results.append(m)
            self.assertEqual((results[0].memory, results[0].complete_trace),
                             (results[1].memory, results[1].complete_trace), args)
        self.receipt('guest', cases=len(cases), full_memory_and_access_order_equal=True,
                     both_stack_phases=True, guest_aliases=10, ordinary_saved_ABI_equal=True)

    def test_03_fired_memory_prefixes_and_invariant_roles(self):
        count = 0
        for alias, mask in itertools.product(range(11), (0, 15)):
            memory, args = vector.fixture(mask, alias=alias)
            full = FullTraceOracle(self.truth, memory, args).run()
            for cut in range(full.all_accesses):
                results = []
                for words in (self.words, self.normal):
                    m = FullTraceOracle(words, memory, args)
                    m.access_fault = cut
                    with self.assertRaises(vector.base.faults.AccessBoundary):
                        m.run()
                    results.append(m)
                self.assertEqual((results[0].memory, results[0].complete_trace),
                                 (results[1].memory, results[1].complete_trace))
                count += 1
        memory, args = vector.fixture()
        for words in (self.words, self.normal):
            m = FullTraceOracle(words, memory, args)
            m.access_fault = 4
            with self.assertRaises(vector.base.faults.AccessBoundary):
                m.run()
            self.assertEqual((m.r[16], m.r[17]), (vector.GLOBAL, 4))
        self.receipt('faults', fired_prefixes=count, fixtures=22, all_private_public_bytes_and_accesses_equal=True,
                     saved_roles=['S0=&D_800D2350', 'S1=4'], hardware_traps_or_scratch_register_identity_not_claimed=True)

    def test_04_native32_and_effective_semantic_controls(self):
        cases = [(mask, pattern, 0, speed, alias) for mask, pattern, speed, alias in itertools.product(
            (0, 5, 15), (0, 2, 18, 242), (0x3F000000, 0xBF000000), range(6))]
        text = vector.NATIVE.replace('ROWS', ',\n'.join(vector.native_case(p) for p in cases))
        body = source.selected()
        exits = {}
        controls = {
            'unsigned-coordinate': body.replace('*(s16 *)', '*(u16 *)'),
            'narrow-delta': body.replace('(f32)(nextX - currentX)', '(f32)(s16)(nextX - currentX)'),
            'cached-speed': body.replace('deltaZ * *(f32 *)record', 'deltaZ * speed'),
        }
        for label, candidate, flags in [('O0', body, ['-O0']), ('O2-UBSAN', body, ['-O2'])] + [
                (name, candidate, ['-O2']) for name, candidate in controls.items()]:
            path = self.out / ('native-' + label + '.c')
            path.write_text(text + candidate)
            command = [*vector.native_command(flags[0]), '-fno-strict-aliasing', '-mstackrealign',
                       str(path), '-o', str(path.with_suffix(''))]
            run = subprocess.run(command, cwd=self.root, capture_output=True, text=True)
            self.assertEqual((run.returncode, run.stdout, run.stderr), (0, '', ''), label)
            result = subprocess.run([str(path.with_suffix(''))], capture_output=True, text=True)
            self.assertEqual((result.returncode, result.stdout, result.stderr),
                             (0 if label in ('O0', 'O2-UBSAN') else 23, '', ''), label)
            exits[label] = result.returncode
        self.receipt('native32', cases_per_positive_profile=len(cases) + 65536, exits=exits,
                     all_signed_coordinates=True, host_endian_aligned_and_pointer32=True,
                     incompatible_halfword_pointer_aliases_and_NaN_payload_proof_not_claimed=True)

    def test_05_actual_private_mixed_profile_padder(self):
        prior = source.installed.prior
        before = self.values['conker/src/game/generated_B3020.c'].decode()
        candidate = source.model.recovered_owner(before, source.selected())
        normal, nd = prior.compile_profile(self.root, self.out, candidate, 'override-normal', True)
        old_normal, od = prior.compile_profile(self.root, self.out, before, 'baseline-normal', True)
        self.assertFalse(nd or od)
        self.assertEqual(source.model.same_functions(old_normal, normal, (source.model.FUNCTION,)), 72)
        self.assertEqual(normalized_pools(old_normal), normalized_pools(normal))
        prior.candidate.checked(normal)
        original_guards = self.values['conker/retail_word_patches.us.csv']
        guards = layout.private_guards(original_guards, self.raw, self.bindings)
        self.assertTrue(guards.startswith(original_guards))
        old_path, path = self.out / 'baseline-guards.csv', self.out / 'private-guards.csv'
        old_path.write_bytes(original_guards)
        path.write_bytes(guards)
        old = prior.padded(self.root, self.out, self.out / 'owner-before.o', 'baseline-padded', old_path, old_normal)
        new = prior.padded(self.root, self.out, self.obj, 'qualified-padded', path, normal)
        a, fa = source.model.link_owner(self.root, self.out, old, source.model.OWNER)
        b, fb = source.model.link_owner(self.root, self.out, new, source.model.OWNER)
        at = fb[source.model.FUNCTION]['value']
        self.assertEqual(b[at:at + 332], self.values['conker/conker.us.bin'][source.model.ROM:source.model.ROM + 332])
        self.assertEqual((a[:at], a[at + 332:]), (b[:at], b[at + 332:]))
        self.assertEqual(set(fa), set(fb))
        for name in fa:
            self.assertEqual(fa[name]['value'], fb[name]['value'])
            if name != source.model.FUNCTION:
                self.assertEqual(fa[name], fb[name])
        self.assertEqual(normalized_pools(old), normalized_pools(new))
        self.receipt('padder', private_rows=83, all_other_owner_bytes_addresses_extents_fixed=True,
                     primary_and_normal_neighbors=72, projection_override_preserved=True,
                     production_guard_prefix_bytes=len(original_guards), installed=False)

    def test_06_raw_words_bindings_and_recipe_fail_closed(self):
        count = 0
        for i in range(83):
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
        recipe = 0
        for name, values in (('GP_CYCLE', layout.GP_CYCLE), ('SPECIAL', layout.SPECIAL), ('FP_ROLES', layout.FP_ROLES)):
            for key, value in values.items():
                alternatives = value.items() if isinstance(value, dict) else [(None, value)]
                for field, register in list(alternatives):
                    bad = dict(values)
                    if field is None:
                        bad[key] = register ^ 1
                    else:
                        bad[key] = dict(value)
                        bad[key][field] = register ^ 1
                    with patch.object(layout, name, bad), self.assertRaises(ValueError):
                        layout.normalize(self.raw, self.bindings)
                    recipe += 1
        for name in ('GP_COMMUTED', 'FP_COMMUTED'):
            values = getattr(layout, name)
            for at in values:
                with patch.object(layout, name, tuple(i for i in values if i != at)), self.assertRaises(ValueError):
                    layout.normalize(self.raw, self.bindings)
                recipe += 1
        with patch.object(layout, 'origins', return_value=list(range(83))), self.assertRaises(ValueError):
            layout.normalize(self.raw, self.bindings)
        self.receipt('controls', raw_and_binding_controls=count, recipe_controls=recipe + 1)

    def test_07_inputs_and_production_remain_frozen(self):
        raw = Path.read_bytes
        for index, name in enumerate(source.INPUTS):
            for target in (self.root / name, self.out / ('before-%02d' % index)):
                def corrupt(path, *args, **kwargs):
                    data = raw(path, *args, **kwargs)
                    return data + b'\0' if path == target else data
                with patch.object(Path, 'read_bytes', corrupt), self.assertRaises(ValueError):
                    source.freeze(self.root, self.out)
        source.freeze(self.root, self.out)
        self.assertEqual(source.model.INPUTS['conker/src/game/generated_B3020.c'],
                         'ce0cf9b5504e5b41b267c09d69c3bdc9ed2f24533ed7de0dd68935bd678f467f')
        self.receipt('inputs', live_and_snapshot_controls=len(source.INPUTS) * 2,
                     production_unchanged=True, matching_credit=0)


    def test_08_independent_GNU_rebases_and_guest_aliases(self):
        original = self.out / 'original-vector.o'
        text, functions, relocations = source.model.parse_object(self.obj)
        raw_script = self.out / 'rebase-raw.s'
        raw_obj = raw_script.with_suffix('.o')
        count = 0
        for placement, (entry, global_address) in enumerate(((source.model.ENTRY, vector.GLOBAL),
                (0x16218004, 0x23457FFC), (0x18FFF000, 0x23458004))):
            # Re-emit the C object with only the independently chosen anchor.
            emitted, missing = vector.emit_function(text, functions[source.model.FUNCTION], relocations,
                source.model.FUNCTION, {'D_800D2350': global_address})
            self.assertFalse(missing)
            raw_script.write_text(emitted)
            subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(raw_obj), str(raw_script)],
                           check=True, capture_output=True)
            bodies = []
            for label, obj in (('retail', original), ('raw', raw_obj)):
                script = self.out / ('rebase-%d-%s.ld' % (placement, label))
                elf = script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
                subprocess.run(['mips-linux-gnu-ld', '-T', str(script), '-e', source.model.FUNCTION,
                    '--defsym=D_800D2350=0x%X' % global_address, '-o', str(elf), str(obj)],
                    check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>83I', vector.sections(elf)['.text'][1])))
            normalized = layout.relocate(self.normalized, self.moved, {'D_800D2350': global_address})
            self.assertEqual(bodies[0], normalized)
            for alias, mask, phase in itertools.product(range(11), (0, 5, 15), (0, 8)):
                memory, args = vector.fixture(mask, alias=alias, global_address=global_address)
                expected, trace = vector.reference(memory, args, global_address)
                results = []
                for words in (bodies[1], normalized):
                    m = FullTraceOracle(words, memory, args, phase, entry).run()
                    self.assertEqual((vector.public(m.memory), m.trace), (vector.public(expected), trace))
                    results.append(m)
                self.assertEqual((results[0].memory, results[0].complete_trace),
                                 (results[1].memory, results[1].complete_trace))
                count += 1
        self.receipt('rebases', independent_GNU_links=6, code_and_global_placements=3,
                     paired_guest_cases=count, all_normalized_words_and_bindings_equal=True,
                     HI16_LO16_carry_boundaries=True)


if __name__ == '__main__':
    unittest.main()
