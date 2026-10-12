"""Qualification of owned-process diagnostics, not a new function match."""
import hashlib
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from tools.experiments import game_text_measurer_uopt_trace as trace


class GameTextMeasurerUoptTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-text-measurer-uopt-trace-test'
        cls.body = dict(trace.screen.candidates())['flag-branches-captured']
        cls.paths = ('conker/src/game/generated_6E770.c', 'conker/build/conker.us.elf',
                     'conker/retail_word_patches.us.csv', 'conker/Makefile')
        cls.before = {path: hashlib.sha256((cls.root / path).read_bytes()).hexdigest()
                      for path in cls.paths}
        cls.record = trace.trace_uopt(cls.root, cls.out, 'valid', cls.body)
        cls.valid = cls.out / 'valid'
        cls.log = (cls.valid / 'debugger.txt').read_text()

    def disposable(self, name):
        work = self.out / name
        work.mkdir(exist_ok=True)
        for filename in ('baseline.o', 'trace.o', 'uoptlist'):
            shutil.copy2(self.valid / filename, work / filename)
        return work

    def rejected(self, work, code=0, log=None, message='UOPT trace failed'):
        with self.assertRaisesRegex(ValueError, message):
            trace.validate_trace(self.root, work, code, self.log if log is None else log)
        self.assertFalse(json.loads((work / 'trace.json').read_text())['code_unchanged'])

    def test_01_real_diagnostic_preserves_code_and_contains_allocation(self):
        self.assertTrue(self.record['code_unchanged'])
        meta = self.record['baseline']
        self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), (222, 0x80, 146))
        text = (self.valid / 'uoptlist').read_text()
        self.assertIn('assigned (constrained)', text)
        self.assertIn('live range', text)
        self.assertIn('global coloring of func_150428D4', text)
        self.assertIn(trace.EXIT_MARKER, self.log.splitlines())
        self.assertIn('numeric timings are not valid', self.record['caveat'])

    def test_02_effective_failed_partial_empty_and_missing_controls(self):
        self.rejected(self.disposable('failed'), code=1)
        self.rejected(self.disposable('no-exit'), log='SIGABRT\n')
        self.rejected(self.disposable('bad-driver-exit'), log=self.log.replace(trace.EXIT_MARKER,
                                                                            'TRACE_EXIT inferior=1 code=11'))
        for name, contents in (('empty', ''), ('partial', 'register allocation\n')):
            work = self.disposable(name)
            (work / 'uoptlist').write_text(contents)
            self.rejected(work)
        work = self.disposable('missing')
        (work / 'trace.o').unlink()
        self.rejected(work)

    def test_03_effective_text_function_relocation_and_pool_controls(self):
        parse = trace.screen.compiler.parse_object
        for kind in ('text', 'function', 'relocation'):
            work = self.disposable('changed-' + kind)
            def changed(path):
                text, functions, relocs = parse(path)
                if Path(path).name == 'trace.o':
                    if kind == 'text':
                        text = bytes((text[0] ^ 1,)) + text[1:]
                    elif kind == 'function':
                        functions = {name: dict(info) for name, info in functions.items()}
                        functions[trace.screen.FUNCTION]['size'] += 4
                    else:
                        relocs = list(relocs) + [('negative-control',)]
                return text, functions, relocs
            with self.subTest(kind=kind), patch.object(trace.screen.compiler, 'parse_object',
                                                       side_effect=changed):
                self.rejected(work, message='changed text, functions, relocations or pools')
        section = trace.screen.compiler.sections
        def changed_pool(path):
            values = dict(section(path))
            if Path(path).name == 'trace.o':
                values['.rodata'] = ('negative-control', b'\x01')
            return values
        with patch.object(trace.screen.compiler, 'sections', side_effect=changed_pool):
            self.rejected(self.disposable('changed-pool'),
                          message='changed text, functions, relocations or pools')

    def test_04_fingerprint_gate_precedes_compilation_and_rechecks_after(self):
        with patch.object(trace, 'compiler_fingerprints', return_value={}), \
                patch.object(trace.screen, 'compile_candidate') as compile:
            with self.assertRaisesRegex(ValueError, 'fingerprint mismatch'):
                trace.trace_uopt(self.root, self.out, 'wrong-compiler', self.body)
            compile.assert_not_called()
            self.rejected(self.disposable('changed-compiler'), message='fingerprint changed')

    def test_05_owned_path_mode_and_recipe_boundaries(self):
        for out, name, mode in ((self.root / 'DOCS', 'invalid', 6),
                                (self.out, '../invalid', 6), (self.out, 'invalid', 3)):
            with self.subTest(name=name, mode=mode), self.assertRaisesRegex(ValueError, 'mode/name/output'):
                trace.trace_uopt(self.root, out, name, self.body, mode)
        redirect = self.out / 'outside-redirect'
        redirect.unlink(missing_ok=True)
        redirect.symlink_to(self.root / 'DOCS', target_is_directory=True)
        try:
            with self.assertRaisesRegex(ValueError, 'mode/name/output'):
                trace.trace_uopt(self.root, self.out, redirect.name, self.body)
        finally:
            redirect.unlink()
        script = (self.valid / 'compiler-child.gdb').read_text()
        self.assertIn('set auto-load off', script)
        self.assertIn('refusing to resume a failed compiler', script)
        self.assertNotIn('\nattach ', script)
        self.assertNotIn('target remote', script)
        self.assertNotIn('\nshell ', script)

    def test_06_production_and_prepared_compilers_unchanged(self):
        self.assertEqual(trace.compiler_fingerprints(self.root), trace.COMPILERS)
        self.assertEqual(self.before, {path: hashlib.sha256((self.root / path).read_bytes()).hexdigest()
                                      for path in self.paths})

    def test_07_mode5_qualifies_distinct_flag_constraints_without_code_changes(self):
        candidates = dict(trace.screen.candidates())
        expected = {'early': (218, 0x80, 174, 48, 17, [1, 2, 3, 14, 15, 16]),
                    'late': (222, 0x80, 146, 52, 2, [1])}
        records = {}
        for name, key in (('early', 'capture-declaration-after-record'),
                          ('late', 'flag-branches-captured')):
            record = trace.trace_uopt(self.root, self.out, 'mode5-' + name, candidates[key], 5)
            meta = record['baseline']
            self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), expected[name][:3])
            self.assertTrue(record['code_unchanged'])
            self.assertEqual(record['mode'], 5)
            text = (self.out / ('mode5-' + name) / 'uoptlist').read_text()
            constraints = trace.allocation_constraints(text)
            self.assertGreater(len(constraints), 20)
            flag = next(item for item in constraints if item['identity'] == '923|0')
            self.assertEqual((flag['expression'], flag['color'], flag['forbidden']), expected[name][3:])
            self.assertIn(43, flag['interference'])
            records[name] = dict(trace=record, flag=flag)
        self.assertIn(2, records['early']['flag']['forbidden'])
        self.assertNotIn(2, records['late']['flag']['forbidden'])
        (self.out / 'mode5-flag-constraints.json').write_text(json.dumps(records, indent=2) + '\n')
        self.test_06_production_and_prepared_compilers_unchanged()

    def test_08_constraint_parser_and_six_source_shape_rejections(self):
        valid = '>>>active<<<{923|0} 52 2\nadjsave, hasstore: true\nforbidden: [ 1]\n:::interfere with::: 43\n'
        self.assertEqual(trace.allocation_constraints(valid)[0]['forbidden'], [1])
        self.assertEqual(trace.allocation_constraints(''), [])
        for bad in (valid.replace('52 2', 'bad'), valid.replace('forbidden: [ 1]', 'forbidden: [ x]'),
                    valid.replace(':::interfere with::: 43', 'missing'), valid.splitlines()[0]):
            with self.assertRaisesRegex(ValueError, 'Malformed mode5'):
                trace.allocation_constraints(bad)
        candidates = dict(trace.screen.candidates())
        for prefix, reference, expected in (
                ('capture', 'capture-declaration-after-record', (218, 0x80, 174)),
                ('flag-branches', 'flag-branches-captured', (222, 0x80, 146))):
            _, original = trace.screen.compile_candidate(self.root, self.out, prefix + '-reference', candidates[reference])
            for suffix in ('volatile-spill', 'union-flag'):
                name = prefix + '-' + suffix
                meta, words = trace.screen.compile_candidate(self.root, self.out, name, candidates[name])
                self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), expected)
                self.assertEqual(words, original)
            name = prefix + '-parameter-glyph'
            meta, words = trace.screen.compile_candidate(self.root, self.out, name, candidates[name])
            self.assertEqual((meta['body_words'], meta['frame'], meta['differences']),
                             (217, 0x80, 205) if prefix == 'capture' else (221, 0x80, 197))
            self.assertEqual(words[1], 0xAFB70038 if prefix == 'capture' else 0xAFB60038)
            if prefix == 'flag-branches':
                self.assertEqual(words[:13], original[:13])

    def test_09_front_end_marker_and_memory_residence_are_distinct(self):
        text = '{ 923|0} 48 isvar M 750 -48vreg\n'
        self.assertTrue(trace.variable_expressions(text)[0]['virtual_register'])
        self.assertFalse(trace.variable_expressions(text.replace('vreg', ''))[0]['virtual_register'])
        self.assertEqual(trace.variable_expressions(''), [])
        for bad in (text.replace('-48vreg', 'bad'), text.replace('750', 'bad'),
                    text.replace('48 isvar', 'bad isvar')):
            with self.assertRaisesRegex(ValueError, 'Malformed UOPT variable'):
                trace.variable_expressions(bad)
        candidates = dict(trace.screen.candidates())
        early = trace.trace_uopt(self.root, self.out, 'eligibility-early',
                                candidates['capture-declaration-after-record'], 5)
        addressed = trace.trace_uopt(self.root, self.out, 'eligibility-addressed',
                                    candidates['capture-inline-address-void-cast'], 5)
        records = {}
        for name, record in (('early', early), ('addressed', addressed)):
            folder = self.out / ('eligibility-' + name)
            text = (folder / 'uoptlist').read_text()
            variable = next(item for item in trace.variable_expressions(text) if item['identity'] == '923|0')
            color = next(item for item in trace.allocation_constraints(text) if item['identity'] == '923|0')
            self.assertEqual((variable['expression'], variable['storage'], variable['offset']), (48, 'M', -48))
            self.assertEqual(variable['virtual_register'], name == 'early')
            self.assertEqual(color['color'], 17 if name == 'early' else -1)
            self.assertTrue(record['code_unchanged'])
            records[name] = dict(trace=record, variable=variable, allocation=color)
        _, words = trace.screen.compile_candidate(self.root, self.out, 'addressed-memory-code',
                                                  candidates['capture-inline-address-void-cast'])
        call = words.index(0x0D410B10)
        self.assertEqual(words[call + 6], 0xAFA00050)
        self.assertNotIn(0x00004025, words)
        (self.out / 'flag-eligibility.json').write_text(json.dumps(records, indent=2) + '\n')
        self.test_06_production_and_prepared_compilers_unchanged()

    def test_10_fifteen_additional_source_forms_fail_the_retail_shape(self):
        candidates = dict(trace.screen.candidates())
        _, original = trace.screen.compile_candidate(self.root, self.out, 'eligibility-reference',
                                                     candidates['capture-declaration-after-record'])
        identical = ('capture-bitfield-word-s32', 'capture-bitfield-word-u32',
                     'capture-inline-address-direct', 'capture-reset-in-condition',
                     'capture-reset-call-expression', 'capture-enum-flag')
        shapes = {**{name: (218, 0x80, 174) for name in identical},
                  'capture-addressed-flag-mutable': (223, 0x88, 174),
                  'capture-addressed-flag-const': (223, 0x88, 174),
                  'capture-inline-address-void-cast': (222, 0x80, 164),
                  'capture-wide-flag-s64': (227, 0x88, 196),
                  'capture-wide-flag-u64': (227, 0x88, 196),
                  'capture-conditional-result': (228, 0x98, 155),
                  'capture-conditional-effects': (228, 0x98, 155),
                  'capture-direct-condition-result': (230, 0x98, 160),
                  'capture-direct-condition-effects': (230, 0x98, 160)}
        records = []
        for name, expected in shapes.items():
            meta, words = trace.screen.compile_candidate(self.root, self.out, name, candidates[name])
            self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), expected)
            self.assertEqual(meta['pool_bytes'], 0)
            if name in identical:
                self.assertEqual(words, original)
            self.assertNotEqual((meta['body_words'], meta['frame'], meta['differences']), (219, 0x80, 0))
            records.append(meta)
        (self.out / 'flag-source-shapes.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
