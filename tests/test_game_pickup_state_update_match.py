"""Bounded guest qualification for the complete player-item/pickup updater."""

from pathlib import Path
import json
import struct
import subprocess
import unittest

from tools.experiments import game_pickup_state_update_candidates as source
from tools.tests import game_pickup_state_update_oracle as guest


ROOT = Path(__file__).resolve().parents[2]


def observation(model):
    writes = [e for e in model.events if e[0] == 'W' and not guest.private(e[1])]
    return guest.public(model.memory), model.calls, writes, model.fired


class PickupStateUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = ROOT / source.BUILD / 'test'
        cls.values = source.freeze(ROOT, cls.output)
        cls.retail = list(struct.unpack_from('>681I', cls.values['conker/conker.us.bin'], source.ROM))
        cls.obj, cls.words, cls.report = source.compile_candidate(ROOT, cls.output)
        _, cls.normal, cls.normal_report = source.compile_candidate(ROOT, cls.output, 'normal', normal=True)
        cls.corpus, cls.pairs, cls.coverage = list(guest.cases()), 0, set()
        cls.read_differences, cls.native_runs, cls.negatives = [], [], []

    @classmethod
    def tearDownClass(cls):
        row = dict(primary=cls.report, normal=cls.normal_report, cases=len(cls.corpus),
            fixture_profile_phases=cls.pairs, retail_words_visited=len(cls.coverage),
            unvisited_retail_offsets=[hex(i * 4) for i in range(681)
                if source.ENTRY + i * 4 not in cls.coverage], native_runs=cls.native_runs,
            compiled_negatives=cls.negatives, public_read_sequence_differences=len(cls.read_differences),
            installed=False, matching_credit=0)
        (cls.output / 'test-receipt.json').write_text(json.dumps(row, indent=2) + '\n')
        (cls.output / 'public-read-differences.json').write_text(json.dumps(cls.read_differences, indent=2) + '\n')
        print('pickup-update qualification:', row)

    def test_empty_pass_rotates_and_wraps_signed_player_selector(self):
        case = guest.Case(selector=0)
        for phase in (0, 8):
            wanted = guest.UpdateOracle(self.retail, guest.fixture(case), case, phase).run()
            actual = guest.UpdateOracle(self.words, guest.fixture(case), case, phase).run()
            self.assertEqual(observation(wanted)[2], [('W', guest.SELECTOR, 1, 1), ('W', guest.SELECTOR, 1, 0)])
            self.assertEqual(observation(actual), observation(wanted))

    def test_complete_retail_and_both_compiled_profiles_against_independent_reference(self):
        for name, case in self.corpus:
            memory = guest.fixture(case)
            expected = guest.reference(memory, case)
            for phase in (0, 8):
                wanted = guest.UpdateOracle(self.retail, memory, case, phase).run()
                with self.subTest(case=name, phase=phase, profile='retail'):
                    self.assertEqual(observation(wanted), expected)
                    self.assertEqual(len(wanted.fired), len(case.actions), 'A requested helper mutation never fired')
                type(self).coverage.update(wanted.visits)
                for profile, words in (('primary', self.words), ('normal', self.normal)):
                    actual = guest.UpdateOracle(words, memory, case, phase).run()
                    with self.subTest(case=name, phase=phase, profile=profile):
                        self.assertEqual(observation(actual), expected)
                    old_reads = [e for e in wanted.events if e[0] == 'R' and not guest.private(e[1])]
                    new_reads = [e for e in actual.events if e[0] == 'R' and not guest.private(e[1])]
                    if old_reads != new_reads:
                        i = next((i for i, (a, b) in enumerate(zip(old_reads, new_reads)) if a != b),
                            min(len(old_reads), len(new_reads)))
                        type(self).read_differences.append(dict(case=name, phase=phase, profile=profile,
                            retail_count=len(old_reads), candidate_count=len(new_reads), first=i,
                            retail=old_reads[max(0, i - 1):i + 2], candidate=new_reads[max(0, i - 1):i + 2]))
                    type(self).pairs += 1

    def test_current_placeholder_is_an_effective_negative(self):
        before = self.values[source.SOURCE].decode()
        lo, hi = source.function_span(before, source.FUNCTION)
        _, words, _ = source.compile_candidate(ROOT, self.output, 'placeholder', before[lo:hi])
        case = guest.Case(selector=0)
        model = guest.UpdateOracle(words, guest.fixture(case), case).run()
        self.assertNotEqual(observation(model), guest.reference(guest.fixture(case), case))

    def test_production_inputs_unchanged(self):
        for name, value in self.values.items():
            self.assertEqual((ROOT / name).read_bytes(), value, name)

    def test_selected_profile_shape_and_initial_source_control(self):
        self.assertEqual((self.report['words'], self.report['frame'], self.report['differences']), (680, 280, 665))
        self.assertEqual(self.report['raw_SHA256'], '899a737e40358f6a0842007c5404d9040bed2c583f92ec155377121f6f3be5f7')
        self.assertEqual(self.words, self.normal)
        self.assertEqual(self.report['diagnostics'], '')
        _, initial, row = source.compile_candidate(ROOT, self.output, 'initial-control', source.INITIAL)
        self.assertEqual((row['words'], row['frame'], row['differences']), (682, 288, 666))
        self.assertNotEqual(initial, self.words)

    def test_complete_owner_profiles_preserve_other_72_bodies_and_pools(self):
        from tools.experiments.game_actor_state_tick_integration import same_functions
        from tools.tests.game_owner_pool import normalized_pools
        before = self.values[source.SOURCE].decode()
        lo, hi = source.function_span(before, source.FUNCTION)
        for normal in (False, True):
            a, _, _ = source.compile_candidate(ROOT, self.output, 'owner-before-' + str(normal),
                before[lo:hi], normal, whole=True)
            b, _, row = source.compile_candidate(ROOT, self.output, 'owner-after-' + str(normal),
                source.SELECTED, normal, whole=True)
            self.assertEqual(same_functions(a, b, (source.FUNCTION,)), 72)
            self.assertEqual(normalized_pools(a), normalized_pools(b))
            self.assertEqual(row['raw_SHA256'], self.report['raw_SHA256'])

    def native(self, unit, label, optimization):
        path = self.output / (label + '.c')
        path.write_text(unit)
        binary = self.output / (label + optimization)
        command = ['gcc', '-m32', optimization, '-std=c99', '-fno-strict-aliasing',
            '-msse2', '-mfpmath=sse', '-mstackrealign', '-ffreestanding', '-nostdlib',
            '-static', '-fno-pie', '-no-pie', '-fno-stack-protector', '-ffp-contract=off',
            '-fsanitize=undefined', '-fsanitize-undefined-trap-on-error',
            '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter', '-Wno-unused-function',
            str(path), '-o', str(binary)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return subprocess.run([str(binary)], capture_output=True, timeout=30)

    def test_complete_native32_C_at_three_optimizations_with_UBSan(self):
        unit = guest.native_harness(source.SELECTED, self.corpus)
        for optimization in ('-O0', '-O2', '-O3'):
            result = self.native(unit, 'native', optimization)
            self.assertEqual(result.returncode, 0, (optimization, result.stdout, result.stderr))
            type(self).native_runs.append(dict(optimization=optimization, fixtures=len(self.corpus),
                returncode=result.returncode, trap_UBSan=True))

    def test_compiled_semantic_negatives_are_effective(self):
        changes = (
            ('current-mask', 'previous = data[0x75] & 0x7F;', 'previous = data[0x75];'),
            ('nausea-boundary', 'data[0x19B] >= 5', 'data[0x19B] > 5'),
            ('unmapped-44-preservation', 'index != 0x2C', 'index != 0x2F'),
            ('charge-byte-wrap', 'data[0x19A] += 3;', 'data[0x19A] += 2;'),
            ('cached-scale', 'func_150ADA68() * scale * x', 'func_150ADA68() * D_8009DA90 * x'),
            ('minus-one-not-byte255', 'if (node != -1)', 'if (node != 255)'),
        )
        rows = []
        for name, old, new in changes:
            self.assertEqual(source.SELECTED.count(old), 1)
            body = source.SELECTED.replace(old, new)
            result = self.native(guest.native_harness(body, self.corpus), 'negative-' + name, '-O2')
            self.assertNotEqual(result.returncode, 0, name)
            rows.append(dict(name=name, returncode=result.returncode))
        (self.output / 'semantic-negatives.json').write_text(json.dumps(rows, indent=2) + '\n')
        type(self).negatives = rows


if __name__ == '__main__':
    unittest.main()
