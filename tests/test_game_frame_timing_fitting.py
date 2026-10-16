"""Reject a score-only fit and loss of the history's signed-zero addition."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_frame_timing_fitting as source
from tools.experiments import game_text_measurer_uopt_trace as trace
from tools.tests import game_frame_timing_oracle as model
from tools.tests import game_frame_timing_native as native
from tools.tests import test_game_actor_burst_consumer_match as tracking
from tools.tests.test_game_projected_packet_draw import native_command
from tools.pad_generated_object import parse_object

UPDATED = dict((n,b) for n,b,_ in source.divisor_forms())['original-updated-total']


def zero_cases():
    patterns = ((0x80000000,) * 10, (0,) * 10,
        (0x80000000,) + (0,) * 9, (0,) + (0x80000000,) * 9,
        (0x80000001,) * 10, (1, 0x80000001) * 5)
    for pattern, index, mode in itertools.product(patterns, (10, 255), (0, 2)):
        memory = model.fixture(0, 0, 0, 0, index, 10)
        for i, value in enumerate(pattern):
            model.put(memory, model.HISTORY + i * 4, value)
        yield memory, mode, ('zero', pattern, index)


class FrameTimingFittingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / source.BUILD
        source.freeze(cls.root, cls.out)
        cls.before = {key:hashlib.sha256((cls.root/path).read_bytes()).hexdigest() for key,path in source.PATHS.items()}
        assert cls.before == source.BASELINE
        cls.objects, cls.words, cls.rows = {}, {}, {}
        named, declarations = next((b,d) for n,b,d in source.history_forms() if n == 'named-two-head-eight-tail')
        for name, body, decl in (('predecessor', source.INITIAL, ''), ('updated-total', UPDATED, ''),
                ('named-history', named, declarations)):
            cls.objects[name], cls.words[name], cls.rows[name] = source.measure(cls.root, cls.out, name, body, decl)
        cls.truth = list(struct.unpack_from('>192I', (cls.out/'before-retail_rom').read_bytes(), source.ROM))

    def receipt(self, name, **row):
        (self.out/(name+'.json')).write_text(json.dumps(row, indent=2)+'\n')

    def test_01_complete_owner_shape_binding_and_neighbor_boundary(self):
        self.assertEqual((self.rows['predecessor']['words'], self.rows['predecessor']['differences']), (191, 141))
        self.assertEqual((self.rows['updated-total']['words'], self.rows['updated-total']['differences']), (191, 139))
        self.assertEqual(self.rows['predecessor']['raw_sha256'], source.previous.RAW_SHA256)
        self.assertEqual(self.rows['updated-total']['raw_sha256'], '660ad91e67099a57e46c8458628ba0d84f3c6e30975dc7ea472f3a3da8351388')
        for name in ('predecessor', 'updated-total'):
            self.assertEqual(self.rows[name]['bindings'][0x64], [('R_MIPS_HI16','D_800BE610')])
            self.assertEqual(self.rows[name]['bindings'][0x6C], [('R_MIPS_LO16','D_800BE610')])
            self.assertEqual(self.words[name][0x64//4], 0x3C09800C)
            self.assertEqual(self.words[name][0x6C//4], 0x2529E610)
            self.assertEqual(self.words[name][0x14//4], 0x90C6EA0C)
            self.assertEqual(self.words[name][0x20//4], 0x00C02025)
        self.assertEqual(self.truth[0x5C//4], 0x3C04800C)
        self.assertEqual(self.truth[0x60//4], 0x8C84E610)
        old = parse_object(self.objects['predecessor'])
        before = (self.out/'before-dispatch_owner').read_text()
        for name in ('updated-total', 'named-history'):
            new = parse_object(self.objects[name])
            self.assertEqual(set(old[1]), set(new[1]))
            for function, f in old[1].items():
                if function == source.FUNCTION:
                    continue
                g = new[1][function]
                self.assertEqual(old[0][f['value']:f['value']+f['size']], new[0][g['value']:g['value']+g['size']], function)
                bindings = lambda p,s:{a-s['value']:r for a,r in p[2].items() if s['value']<=a<s['value']+s['size']}
                self.assertEqual(bindings(old,f), bindings(new,g), function)
            self.assertEqual(self.rows[name]['frame'], 24)
            self.assertFalse(self.rows[name]['pools'])
            after = (self.out/(name+'.c')).read_text()
            sites = source.previous.previous.previous.warning_sites
            self.assertEqual(sites(before, self.rows['predecessor']['diagnostics']), sites(after, self.rows[name]['diagnostics']))
        self.receipt('shape-boundary', owner_neighbors=15, predecessor_differences=141,
            candidate_differences=139, code_installed=False, no_new_guards=True)

    def test_02_public_agreement_does_not_establish_private_matching(self):
        count = 0
        orders = [0, 0]
        for memory, mode, args in itertools.chain(model.corpus(), zero_cases()):
            expected, calls, observations = model.reference(memory, mode)
            for phase in (0, 8):
                machines = [model.TimingOracle(words, memory, mode, phase).run()
                    for words in (self.truth, self.words['predecessor'], self.words['updated-total'])]
                for m in machines:
                    self.assertEqual((model.public(m.memory), m.calls, m.observations),
                        (model.public(expected), calls, observations), (args, phase))
                events = lambda m:[e for e in m.events if e[0] in ('R','W') and model.BASE<=e[1]<model.BASE+model.LENGTH]
                for i, m in enumerate(machines[1:]):
                    orders[i] += events(machines[0]) != events(m)
                count += 1
        self.assertEqual(count, 6908)
        self.assertGreater(orders[0], 0)
        self.assertGreater(orders[1], 0)
        self.receipt('public-candidate', cases=count, extra_signed_zero_cases=48,
            predecessor_different_access_orders=orders[0], candidate_different_access_orders=orders[1],
            original_predecessor_candidate_public_agree=True, complete_private_fault_equivalence=False)

    def test_03_named_history_is_an_effective_guest_negative_zero_control(self):
        memory, mode, _ = next(zero_cases())
        expected, calls, observations = model.reference(memory, mode)
        self.assertEqual(model.read(expected, model.MEAN), 0)
        m = model.TimingOracle(self.words['named-history'], memory, mode).run()
        self.assertEqual(model.read(m.memory, model.MEAN), 0x80000000)
        self.assertEqual(m.calls, calls)
        self.assertNotEqual(m.observations, observations)
        self.assertNotEqual(model.public(m.memory), model.public(expected))
        # Retail must actually execute the opening +0 addition; this is not a model-only failure.
        r = model.TimingOracle(self.truth, memory, mode).run()
        self.assertEqual(model.public(r.memory), model.public(expected))
        self.assertEqual(self.truth[0x260//4], 0x460A6000)
        self.assertIn(source.ENTRY+0x260, r.visits)
        self.receipt('named-history-rejection', retail_mean='0x00000000', candidate_mean='0x80000000',
            actual_guest_completed=True, callback_fired=True, first_zero_addition_required=True)

    def test_04_actual_opening_access_faults_still_disagree_in_registers(self):
        count = 0
        for ticks, divisor, phase, cut in itertools.product((1,0xFFFFFFFF), (0,1,3), (0,8), (1,2)):
            memory = model.fixture(ticks, divisor)
            machines = []
            for words in (self.truth, self.words['predecessor'], self.words['updated-total']):
                m = model.TimingOracle(words, memory, phase=phase)
                m.root_fault = cut
                with self.assertRaises(tracking.AccessBoundary):
                    m.run()
                self.assertEqual(m.root_accesses, cut)
                self.assertEqual(m.current_pc, source.ENTRY+(0x14 if cut==1 else 0x18))
                self.assertFalse(m.calls)
                self.assertEqual(m.r[29], m.before[29]-24)
                machines.append(m)
            for m in machines[1:]:
                self.assertEqual(m.memory, machines[0].memory)
                self.assertEqual(m.f, machines[0].f)
                self.assertEqual((m.r[29],m.r[31]), (machines[0].r[29],machines[0].r[31]))
                self.assertNotEqual(m.r, machines[0].r)
            count += 1
        self.receipt('opening-fault-boundary', cuts=count, actual_dispatched_offsets=[20,24],
            same_memory_FPR_SP_RA=True, different_GPRs=True, lower_score_not_private_state_proof=True)

    def test_05_actual_candidate_native32_O2_O0_and_effective_controls(self):
        harness = self.out/'native-fitting.c'
        harness.write_text(native.program())
        controls = {
            'ordinary-remainder': UPDATED.replace('total -= (u32)D_800BE9E4 * total;', 'total -= (u32)D_800BE9E4 * divisor;'),
            'wrong-total-sign': UPDATED.replace('total -= (u32)D_800BE9E4 * total;', 'total += (u32)D_800BE9E4 * total;'),
            'uncached-index': UPDATED.replace('D_800BE619 = historyIndex + 1;', 'D_800BE619++;'),
        }
        exits = {}
        for name, opt, body in [('o2','-O2',UPDATED), ('o0','-O0',UPDATED)]+[(n,'-O2',b) for n,b in controls.items()]:
            self.assertNotEqual(body, source.INITIAL)
            if name in controls:
                self.assertNotEqual(body, UPDATED)
            unit = self.out/('native-fitting-'+name+'.c')
            unit.write_text(native.HEADER+body+'\n')
            exe = unit.with_suffix('.elf')
            build = subprocess.run([*native_command(opt), '-mstackrealign', '-fno-strict-aliasing',
                str(unit.relative_to(self.root)), str(harness.relative_to(self.root)), '-o', str(exe.relative_to(self.root))],
                cwd=self.root, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run([str(exe)], capture_output=True, text=True)
            exits[name] = result.returncode
            self.assertEqual(result.returncode, 0 if name in ('o2','o0') else 22, result.stderr)
        self.receipt('native-candidate', cases_each=len(list(model.corpus())), exits=exits,
            actual_C_separate_units=True, UBSan=True, no_fwrapv=True,
            extra_signed_zero_guest_cases_not_native=True)

    def test_06_fired_owned_UOPT_traces_preserve_complete_emission(self):
        results = {}
        for variant, mode in itertools.product(('baseline','updated-total'), (5,6)):
            row = source.trace_owner(self.root, variant, mode)
            self.assertTrue(row['code_unchanged'])
            self.assertEqual(row['live_inputs_unchanged'], self.before)
            total = [v for v in row['variables'] if v['storage']=='M' and v['offset']==-8]
            self.assertEqual(len(total), 1)
            self.assertEqual(total[0]['expression'], 14)
            self.assertFalse(row['installable'])
            if mode == 5:
                by_expression = {r['expression']:r for r in row['constraints']}
                self.assertEqual(by_expression[14]['color'], 2 if variant=='baseline' else 1)
                self.assertEqual(by_expression[4]['color'], 1 if variant=='baseline' else 2)
                self.assertEqual(by_expression[158]['color'], 8)
                self.assertEqual(by_expression[0]['color'], 5)
                self.assertEqual(by_expression[6]['color'], 3)
            results[variant+'-'+str(mode)] = {k:row[k] for k in ('trace_sha256','bytes','code_unchanged')}
        with self.assertRaises(ValueError):
            source.trace_owner(self.root, 'unknown')
        with self.assertRaises(ValueError):
            source.trace_owner(self.root, mode=7)
        self.receipt('compiler-observation', traces=results, owned_compilers_completed=4,
            complete_normal_object_and_pools_identical=True, numeric_timings_not_valid=True)

    def test_07_no_production_change_and_baseline_guards_fail_closed(self):
        for key,path in source.PATHS.items():
            self.assertEqual(hashlib.sha256((self.root/path).read_bytes()).hexdigest(), self.before[key], key)
        read = Path.read_bytes
        for key in ('elf','dispatch_owner','guards','timing_assembly','timing_constant_assembly'):
            path = self.out/('before-'+key)
            with patch.object(Path, 'read_bytes', lambda p:read(p)+b'\n' if p==path else read(p)):
                with self.assertRaises((ValueError,AssertionError)):
                    source.freeze(self.root, self.out)
        self.receipt('unchanged-live', inputs=len(self.before), hashes=self.before, installed=False)


if __name__ == '__main__':
    unittest.main()
