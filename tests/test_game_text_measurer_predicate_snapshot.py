"""Snapshot spelling and a Boolean value are not retail's shared early reset."""
import itertools
import json
from pathlib import Path
import subprocess
import sys
import unittest

from tools.experiments import game_text_measurer_frontend_trace as front
from tools.experiments import game_text_measurer_predicate_snapshot as screen
from tools.tests import test_game_text_measurer_font_controls as fonts
from tools.tests import test_game_text_measurer_logic_candidates as semantics
from tools.tests import test_game_text_measurer_recovery as recovery


class TextObserver(fonts.FontObserver):
    def __init__(self, *args, **kwargs):
        self.text_pending = False
        self.first_text_t0 = []
        super().__init__(*args, **kwargs)

    def record_call(self, target):
        if target == recovery.lookup.ENTRY:
            self.text_pending = True
        super().record_call(target)

    def get(self, address, size):
        if self.text_pending and address == self.before[4] and size == 1:
            self.first_text_t0.append(self.r[8])
            self.text_pending = False
        return super().get(address, size)


class GameTextMeasurerPredicateSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-text-measurer-predicate-snapshot-test'
        cls.out.mkdir(exist_ok=True)
        cls.assignments = dict(screen.assignment_candidates())
        cls.defaults = dict(screen.default_candidates())
        cls.compiled = {name: screen.logic.screen.compile_candidate(cls.root, cls.out, name, body)
                        for name, body in (*cls.assignments.items(), *cls.defaults.items())}
        cls.references = {name: screen.logic.screen.compile_candidate(cls.root, cls.out, name, body)
                          for name, body in screen.logic.compound_candidates()}
        recovery.GameTextMeasurerRecoveryTests.setUpClass()
        cls.oracle = recovery.GameTextMeasurerRecoveryTests('test_05_production_and_protected_data_unchanged')
        cls.semantic = semantics.GameTextMeasurerLogicTests('test_02_all_nine_distinct_bodies_preserve_complete_public_semantics')
        cls.semantic.oracle = cls.oracle

    def test_01_assignment_spelling_checks_words_not_only_equal_counts(self):
        changed = [30, 151, 152, 155, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166,
                   167, 168, 169, 170, 178, 179, 181, 183, 186, 187, 188, 191, 196, 198,
                   199, 201, 206, 208, 209, 211, 216, 218]
        shapes = {'explicit-named': (226, 0x90, 197), 'explicit-inline-address': (230, 0x90, 222),
                  'explicit-scoped': (227, 0x90, 222)}
        for name, reference in (('explicit-named', 'compound-named'),
                                ('explicit-inline-address', 'compound-inline-void-address'),
                                ('explicit-scoped', 'compound-scoped-initializer')):
            self.assertNotEqual(self.assignments[name], dict(screen.logic.compound_candidates())[reference])
            meta, words = self.compiled[name]
            self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), shapes[name])
            self.assertNotEqual(words, self.oracle.retail)
            self.assertEqual([i for i, (a, b) in enumerate(zip(words, self.references[reference][1])) if a != b],
                             changed if name == 'explicit-inline-address' else [])
            parser = screen.logic.screen.compiler.parse_object
            left_object, right_object = parser(self.out / (name + '.o')), parser(self.out / (reference + '.o'))
            if name == 'explicit-inline-address':
                self.assertNotEqual(left_object[0], right_object[0])
                self.assertEqual(left_object[1:], right_object[1:])
            else:
                self.assertEqual(left_object, right_object)
            left, right = (screen.logic.screen.compiler.sections(self.out / (tag + '.o')) for tag in (name, reference))
            for section in left.keys() | right.keys():
                if section.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss')):
                    self.assertEqual(left.get(section), right.get(section))

    def test_02_three_pure_predicate_shapes_remain_rejected(self):
        shapes = {'pure-ordinary-direct-font': (228, 0x90, 220),
                  'pure-ordinary-font-address': (226, 0x88, 221),
                  'pure-ordinary-discard-effects': (222, 0x88, 214)}
        self.assertEqual(len({tuple(self.compiled[name][1]) for name in self.defaults}), 3)
        for name, shape in shapes.items():
            meta, words = self.compiled[name]
            self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), shape)
            self.assertNotEqual(words[:13], self.oracle.retail[:13])
            self.assertNotEqual(words, self.oracle.retail)
            self.assertFalse(any(word >> 26 == 2 for word in words))
            sections = screen.logic.screen.compiler.sections(self.out / (name + '.o'))
            self.assertTrue(all(not value[1] for section, value in sections.items()
                if section.startswith(('.rodata', '.rdata', '.data', '.sdata', '.lit', '.bss', '.sbss'))))
        words = self.compiled['pure-ordinary-discard-effects'][1]
        self.assertEqual(words[77], 0xAFA80058)
        self.assertEqual(words[83], 0x8FA80058)
        self.assertNotIn(0x00004025, words)
        self.assertNotIn(0xAFA80068, words)

    def test_03_all_six_bodies_preserve_bounded_public_semantics(self):
        counts = {}
        self.assertEqual(len({tuple(words) for _, words in self.compiled.values()}), 6)
        for name in self.compiled:
            words = self.compiled[name][1]
            count = 0
            for byte, phase in itertools.product(range(256), (0, 8)):
                self.semantic.compare(words, bytes((byte, 0, 0)) if byte != 0xBC else bytes((byte, 7, 65, 0)), phase=phase)
                count += 1
            for text, alias, phase, scales in itertools.product((b'\0', b'A\0', b'A\nB\0', b' AB\0',
                    bytes((0xBC, 0, 65, 0)), bytes((0xA8, 0xAA, 0xBA, 0xAE, 65, 0))),
                    range(10), (0, 8), ((1.0, 1.0), (0.75, 1.25))):
                self.semantic.compare(words, text, alias, phase, scales)
                count += 1
            self.semantic.compare(words, b'A\0', null=True)
            self.semantic.compare(words, bytes((0xAA, 0)), factor=1.0 / 18.0)
            memory, args = self.oracle.font_pointer_fixture()
            model = semantics.LogicalMeasurerOracle(words, memory, args, self.oracle.connected).run()
            expected = recovery.Reference(memory, args).run()
            self.assertEqual(recovery.public(model.memory), recovery.public(expected.memory))
            self.assertEqual(model.calls, expected.calls)
            counts[name] = count + 3
            self.assertEqual(counts[name], 755)
        self.assertEqual(sum(counts.values()), 4530)
        (self.out / 'public.json').write_text(json.dumps(dict(counts=counts, comparisons=sum(counts.values()),
            actual_helpers=True, installable=False, full_private_fault_native_owner_qualification=False), indent=2) + '\n')

    def test_04_discard_effects_passes_space_value_but_fails_first_text_read(self):
        records = []
        words = self.compiled['pure-ordinary-discard-effects'][1]
        for phase, text in itertools.product((0, 8), (b' \0', b'A\0', b'AB\n\xA8\0')):
            memory, args = recovery.fixture(text, self.oracle.table)
            original = TextObserver(self.oracle.retail, memory, args, self.oracle.connected,
                                    phase=phase, entry=screen.logic.screen.ENTRY).run()
            candidate = TextObserver(words, memory, args, self.oracle.connected, phase=phase).run()
            plain = semantics.LogicalMeasurerOracle(words, memory, args, self.oracle.connected, phase=phase).run()
            self.assertEqual(candidate.events, plain.events)
            self.assertEqual(candidate.r, plain.r)
            self.assertEqual(candidate.f, plain.f)
            self.assertEqual(candidate.memory, plain.memory)
            expected = recovery.Reference(memory, args).run()
            self.assertEqual(recovery.public(candidate.memory), recovery.public(expected.memory))
            self.assertEqual(candidate.calls, expected.calls)
            if text == b' \0':
                self.assertEqual(original.first_width_t0, [0])
                self.assertEqual(candidate.first_width_t0, [0])
            elif text == b'A\0':
                self.assertEqual(original.first_text_t0, [0])
                self.assertEqual(candidate.first_text_t0, [1])
            else:
                self.assertEqual(candidate.metric_t0, [0])
            records.append(dict(phase=phase, text=text.hex(), first_text_t0=candidate.first_text_t0,
                                first_width_t0=candidate.first_width_t0, metrics_t0=candidate.metric_t0, installable=False))
        (self.out / 'roles.json').write_text(json.dumps(records, indent=2) + '\n')

    def test_05_completed_wire_captures_distinguish_assignment_and_real_call_save(self):
        captures = {name: front.capture_frontend(self.root, self.out, 'capture-' + name, body)
                    for name, body in (('compound', dict(screen.logic.compound_candidates())['compound-named']),
                                       ('explicit', self.assignments['explicit-named']),
                                       ('discard', self.defaults['pure-ordinary-discard-effects']))}
        for name in ('compound', 'explicit'):
            capture = captures[name]
            self.assertTrue(capture['code_unchanged'])
            self.assertFalse(capture['installable'])
            self.assertEqual((capture['frontend']['bytes'], capture['record_count'],
                              capture['optimizer']['bytes'], capture['optimizer_record_count']), (18960, 861, 18456, 825))
            loads = [x for x in capture['records'] if x['name'] == 'lod' and x['storage'] == 'M' and x['offset'] == -44]
            self.assertEqual(loads[0]['byte_offset'], 4760 if name == 'compound' else 4776)
            self.assertEqual([x['byte_offset'] for x in capture['records'] if x['name'] == 'cup'], [1472, 2816])
            self.assertFalse(any(x['name'] in ('rstr', 'rlod') for x in capture['optimizer_records']))
        capture = captures['discard']
        self.assertTrue(capture['code_unchanged'])
        self.assertFalse(capture['installable'])
        self.assertEqual((capture['frontend']['bytes'], capture['record_count'],
                          capture['optimizer']['bytes'], capture['optimizer_record_count']), (18392, 829, 18192, 813))
        vregs = [x for x in capture['records'] if x['name'] == 'vreg']
        self.assertEqual([(x['byte_offset'], x['storage'], x['level'], x['length'], x['offset']) for x in vregs],
                         [(1520, 'M', 1, 4, -48)])
        saves = [x for x in capture['optimizer_records'] if x['name'] in ('rstr', 'rlod')]
        self.assertEqual([(x['byte_offset'], x['name'], x['storage'], x['level'], x['offset']) for x in saves],
                         [(2984, 'rstr', 'M', 8, -48), (3016, 'rlod', 'M', 8, -48)])
        self.assertEqual([x['byte_offset'] for x in capture['optimizer_records'] if x['name'] == 'cup'], [1752, 3000])
        self.assertEqual(0x88 + saves[0]['offset'], 0x58)

    def test_06_effective_source_cli_and_immutable_controls(self):
        body = self.defaults['pure-ordinary-discard-effects']
        bad = body.replace('(u32)*width + 4', '(u32)*width + 5')
        self.assertNotEqual(bad, body)
        _, words = screen.logic.screen.compile_candidate(self.root, self.out, 'wrong-space', bad)
        with self.assertRaises(AssertionError):
            self.semantic.compare(words, b' \0')
        for arguments in (('--assignments', '--defaults'), ('--assignments', '--filter', 'pure-ordinary-direct-font')):
            result = subprocess.run([sys.executable, '-m', 'tools.experiments.game_text_measurer_predicate_snapshot',
                                     *arguments], cwd=self.root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('error:', result.stderr)
        self.assertEqual(front.compiler_fingerprints(self.root),
                         dict(front.trace.qualified.COMPILERS, ugen=front.trace.UGEN_SHA256, cfe=front.CFE_SHA256))
        self.oracle.test_05_production_and_protected_data_unchanged()
        self.oracle.test_06_effective_immutable_production_controls()


if __name__ == '__main__':
    unittest.main()
