"""Bounded semantic evidence for a still-nonmatching barrier-crossing candidate."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_barrier_crossing_candidates as source
from tools.experiments import game_route_projection_integration as mixed
from tools.pad_generated_object import emit_padded_assembly
from tools.tests import game_barrier_crossing_oracle as guest
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_record_constructor_match import elf_slot_offset


class BarrierCrossingRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD / 'qualification'
        cls.values = source.freeze(cls.root, cls.out)
        cls.before = cls.values[source.SOURCE].decode()
        cls.initial = source.original_body(cls.before)
        cls.selected = source.selected_body(cls.before)
        cls.objects = {}
        cls.words = {}
        cls.measurements = {}
        for name, body in (('initial', cls.initial), ('selected', cls.selected)):
            obj, words, row = source.compile_candidate(cls.root, cls.out, name, body)
            cls.objects[name], cls.words[name], cls.measurements[name] = obj, words, row
        cls.retail = list(struct.unpack_from('>207I', cls.values['conker/conker.us.bin'], source.ROM))
        cls.corpus = tuple(guest.cases())
        cls.receipts = {}

    @classmethod
    def tearDownClass(cls):
        (cls.out / 'semantic-receipt.json').write_text(json.dumps(cls.receipts, indent=2) + '\n')

    def test_matching_boundary_and_production_remain_explicit(self):
        self.assertEqual((self.measurements['initial']['words'], self.measurements['initial']['frame'],
            self.measurements['initial']['differences']), (207, 128, 102))
        self.assertEqual((self.measurements['selected']['words'], self.measurements['selected']['frame'],
            self.measurements['selected']['differences']), (207, 144, 68))
        for row in self.measurements.values():
            self.assertEqual(row['diagnostics'], '')
            self.assertEqual(len(row['bindings']), 5)
        elf = self.values['conker/build/conker.us.elf']
        offset = elf_slot_offset(elf, source.ENTRY, source.WORDS * 4)
        self.assertEqual(list(struct.unpack_from('>207I', elf, offset)), self.words['initial'])
        for name, digest in source.INPUTS.items():
            self.assertEqual(hashlib.sha256((self.root / name).read_bytes()).hexdigest(), digest, name)
        self.assertEqual(hashlib.sha256((self.root / 'conker/progress.csv').read_bytes()).hexdigest(),
            '16798cbd1f7d69f7ecdd8b7e0071ba9ea975a50652bd8797673d1ec2b500c9be')
        self.receipts['production_unchanged'] = True
        self.receipts['candidate_is_byte_exact'] = False

    def test_reference_retail_and_both_raw_bodies(self):
        runs = 0
        covered = set()
        for n, case in enumerate(self.corpus):
            memory = guest.fixture(case)
            expected, after, calls, _, _ = guest.reference(memory, case)
            for phase in (0, 8):
                for label, words in (('retail', self.retail), *self.words.items()):
                    with self.subTest(case=n, phase=phase, body=label):
                        model = guest.CrossingModel(words, memory, case, phase).run()
                        self.assertTrue(guest.equivalent(model.f[0], expected), (case, label, hex(model.f[0]), hex(expected)))
                        self.assertEqual(guest.public(model.memory), guest.public(after))
                        self.assertEqual(model.calls, calls)
                        if label == 'retail':
                            covered.update(model.visits)
                        runs += 1
        self.assertEqual(len(covered), 198)
        self.receipts.update(fixtures=len(self.corpus), completed_guest_runs=runs,
            retail_words_visited=len(covered), retail_word_count=207,
            unvisited_retail_offsets=['0x%X' % offset for offset in range(0, 828, 4)
                if source.ENTRY + offset not in covered],
            comparison='finite bits and NaN class; saved ABI and public memory, not private-frame/FCSR parity')

    def test_last_crossing_is_not_the_minimum_or_last_accepted(self):
        for extra in (1, 2):
            case = guest.Case(count=4, extra=extra)
            result, _, _, crossings, minimum = guest.reference(guest.fixture(case), case)
            self.assertEqual(result, guest.bits(15.))
            self.assertEqual(minimum, .5)
            self.assertEqual([v[2] for v in crossings], [.5, .75])
            self.assertEqual(crossings[-1][3], extra == 2)
        self.receipts['last_rejected_crossing_counterexample'] = dict(retail_result=15, minimum_distance=10)

    def test_fired_private_cut_still_rejects_the_candidate(self):
        case = guest.Case()
        memory = guest.fixture(case)
        for cut in range(40):
            pair = []
            for words in (self.retail, self.words['selected']):
                model = guest.CrossingModel(words, memory, case)
                model.fault = cut
                with self.assertRaises(guest.core.AccessFault):
                    model.run()
                self.assertEqual(model.accesses, cut)
                pair.append(model)
            if pair[0].requested != pair[1].requested:
                base = guest.STACK - 144
                self.assertEqual(pair[0].requested, ('W', base + 0x50, 4))
                self.assertEqual(pair[1].requested, ('W', base + 0x58, 4))
                self.assertEqual(pair[0].memory, pair[1].memory)
                self.assertEqual(pair[0].r, pair[1].r)
                self.assertEqual(pair[0].f, pair[1].f)
                self.receipts['first_private_cut_difference'] = dict(access=cut,
                    fired_pairs=cut + 1, retail=pair[0].requested, candidate=pair[1].requested,
                    equal_prior_literal_state=True)
                return
        self.fail('The expected minimum-home mismatch did not fire')

    def test_actual_height_helper_before_count_and_pointer_capture(self):
        rom = self.values['conker/conker.us.bin']
        words = struct.unpack_from('>20I', rom, 0xB3258)
        code = {guest.HEIGHT + i * 4: word for i, word in enumerate(words)}
        levels = (-20., 0., 20., float('inf'))
        categories = (2, 128, 0, 255)
        runs = 0
        coverage = set()
        from dataclasses import replace
        for y in (-100., -20.001, -20., -19.999, -.001, 0., .001, 19.999, 20., 20.001, float('nan')):
            band = categories[sum(level <= y for level in levels)]
            case = replace(guest.Case(), point=(50., y, -10.), band=band, first_band=band)
            memory = guest.fixture(case)
            for i, level in enumerate(levels):
                guest.put(memory, 0x800D2360 + i * 4, guest.bits(level), 4)
                guest.put(memory, 0x800D237C + i, categories[i], 1)
            result, after, calls, _, _ = guest.reference(memory, case)
            for phase in (0, 8):
                for words in (self.retail, *self.words.values()):
                    model = guest.CrossingModel(words, memory, case, phase, code).run()
                    self.assertTrue(guest.equivalent(model.f[0], result))
                    self.assertEqual(guest.public(model.memory), guest.public(after))
                    self.assertEqual(model.calls, calls)
                    coverage.update(a for a in model.visits if a in code)
                    runs += 1
        self.assertEqual(len(coverage), 20)
        self.receipts.update(actual_height_helper_runs=runs, actual_height_helper_words_visited=len(coverage),
            height_helper_boundary='finite y and NaN; positive infinity would overrun the sentinel and is excluded')

    def test_both_copied_owners_and_actual_padding_preserve_neighbors(self):
        same = mixed.candidate.source.neighbor.same_functions
        objects = {}
        for label, normal in (('primary', False), ('normal', True)):
            old, diagnostics = source.compile_profile(self.root, self.out, self.before, 'before-' + label, normal)
            new, _, row = source.compile_candidate(self.root, self.out, 'after-' + label,
                self.selected, normal=normal, whole=True)
            self.assertEqual(diagnostics, '')
            self.assertEqual(row['diagnostics'], '')
            self.assertEqual(same(old, new, (source.FUNCTION,)), 72)
            self.assertEqual(normalized_pools(old), normalized_pools(new))
            self.assertEqual(source.payload(new), source.payload(self.objects['selected']))
            objects[label] = new
        guards = self.out / 'unchanged-guards.csv'
        guards.write_bytes(self.values['conker/retail_word_patches.us.csv'])
        assembly = self.out / 'selected-padded.s'
        assembly.write_text(emit_padded_assembly(objects['primary'], self.root / 'conker/asm/B3020.s',
            function_objects={'func_150891E8': objects['normal'], 'func_1508BC20': objects['normal']},
            word_patches_path=guards, filename=source.OWNER))
        padded = assembly.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32',
            '-I', str(self.root / 'conker/include'), '-o', str(padded), str(assembly)],
            check=True, capture_output=True)
        old = self.root / 'conker/build/src/game/generated_B3020.c.o'
        a, fa = source.link_owner(self.root, self.out, old, source.OWNER)
        b, fb = source.link_owner(self.root, self.out, padded, source.OWNER)
        self.assertEqual(same(old, padded, (source.FUNCTION,)), 72)
        self.assertEqual(normalized_pools(old), normalized_pools(padded))
        self.assertEqual(fa, fb)
        at = fb[source.FUNCTION]['value']
        self.assertEqual(a[:at], b[:at])
        self.assertEqual(a[at + 828:], b[at + 828:])
        self.assertEqual(list(struct.unpack_from('>207I', b, at)), self.words['selected'])
        self.assertNotEqual(self.words['selected'], self.retail)
        self.receipts.update(neighbors_each_profile=72, padded_neighbors_fixed=72,
            all73_owner_addresses_and_extents_fixed=True, new_guards=0,
            existing_normal_overrides=['func_150891E8', 'func_1508BC20'])

    def test_native32_both_semantic_bodies_and_effective_negative_controls(self):
        commands = 0
        def run(name, body, opt='-O2', corpus=None):
            nonlocal commands
            cfile, exe = self.out / (name + '.c'), self.out / name
            cfile.write_text(guest.native_harness(body, self.corpus if corpus is None else corpus))
            cmd = native_command(opt) + ['-fno-strict-aliasing', '-mstackrealign',
                '-Wno-maybe-uninitialized', '-o', str(exe), str(cfile)]
            result = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            commands += 1
            return subprocess.run([str(exe)], cwd=self.root, capture_output=True).returncode
        for label, body in (('initial', self.initial), ('selected', self.selected)):
            for opt in ('-O0', '-O2', '-O3'):
                self.assertEqual(run(label + '-native' + opt[1:], body, opt), 0)
        negatives = {
            'return-minimum': self.selected.replace('* fraction;', '* minimum;'),
            'clamp-neighbor': self.selected.replace('id != 255 && i < id', 'id != 255 && i < id && id < count'),
            'nonzero-type': self.selected.replace('first[14] == 1', 'first[14] != 0').replace('second[14] == 1', 'second[14] != 0'),
            'truncate-band': self.selected.replace('first[6] == band', 'first[6] == (u8)band'),
            'second-band': self.selected.replace('second[14] == 1', 'second[14] == 1 && second[6] == band'),
            'first-endpoint-inclusive': self.selected.replace('0.0f < a &&', '0.0f <= a &&').replace('a < 0.0f &&', 'a <= 0.0f &&'),
            'second-endpoint-exclusive': self.selected.replace('a <= b', 'a < b').replace('b <= a', 'b < a'),
            'unsigned-coordinates': self.selected.replace('*(s16 *)', '*(unsigned short *)'),
            'stop-on-FF': self.selected.replace('id = cursor[9];',
                'id = cursor[9];\n                    if (id == 255) { break; }'),
        }
        for name, body in negatives.items():
            self.assertNotEqual(body, self.selected)
            self.assertNotEqual(run('negative-' + name, body), 0, name)
        self.receipts.update(native32_positive_runs=6, native32_effective_negatives=len(negatives),
            native32_commands=commands, native32_fixtures=len(self.corpus))


if __name__ == '__main__':
    unittest.main()
