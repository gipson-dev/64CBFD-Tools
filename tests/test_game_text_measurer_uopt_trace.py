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
                                (self.out, '../invalid', 6), (self.out, 'invalid', 5)):
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


if __name__ == '__main__':
    unittest.main()
