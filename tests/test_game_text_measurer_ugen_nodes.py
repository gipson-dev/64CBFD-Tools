"""Qualify positive UGEN node observations without earning matching credit."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import unittest
from unittest.mock import patch

from tools.experiments import game_text_measurer_ugen_nodes as trace


class GameTextMeasurerUgenNodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-text-measurer-ugen-node-test'
        cls.paths = ('conker/src/game/generated_6E770.c', 'conker/build/conker.us.elf',
                     'conker/retail_word_patches.us.csv', 'conker/Makefile')
        cls.before = {path: hashlib.sha256((cls.root / path).read_bytes()).hexdigest()
                      for path in cls.paths}
        candidates = dict(trace.screen.candidates())
        cls.records = {name: trace.trace_nodes(cls.root, cls.out, name, candidates[key])
                       for name, key in (('early', 'capture-declaration-after-record'),
                                         ('late', 'flag-branches-captured'))}
        cls.valid = cls.out / 'late'
        cls.log = (cls.valid / 'debugger.txt').read_text()

    def disposable(self, name):
        work = self.out / name
        work.mkdir(exist_ok=True)
        for filename in ('baseline.o', 'trace.o'):
            shutil.copy2(self.valid / filename, work / filename)
        return work

    def rejected(self, work, code=0, log=None, message='UGEN trace failed'):
        with self.assertRaisesRegex(ValueError, message):
            trace.validate_trace(self.root, work, code, self.log if log is None else log)
        record = json.loads((work / 'trace.json').read_text())
        self.assertFalse(record['code_unchanged'])
        self.assertFalse(record['installable'])

    def test_01_real_probes_fire_on_already_assigned_register_nodes(self):
        for name, expected in (('early', (218, 0x80, 174, 19)),
                               ('late', (222, 0x80, 146, 3))):
            with self.subTest(name=name):
                record = self.records[name]
                meta = record['baseline']
                self.assertEqual((meta['body_words'], meta['frame'], meta['differences']), expected[:3])
                self.assertTrue(record['code_unchanged'])
                self.assertFalse(record['installable'])
                self.assertEqual(record['event_count'], 90)
                log = (self.out / name / 'debugger.txt').read_text()
                self.assertLess(log.index(trace.REMOVED), log.index('/as1\n'))
                self.assertEqual({event['opcode'] for event in record['events']}, {82})
                register_offsets = {event['raw44'] for event in record['events']
                                    if event['type_storage'] >> 5 == 3}
                self.assertIn(expected[3] * 4, register_offsets)
                text, _functions, _relocs = trace.screen.compiler.parse_object(self.out / name / 'trace.o')
                self.assertIn(struct.pack('>I', 0x8FA00068 | (expected[3] << 16)), text)
                # The observed register is also the final flag-test operand in emitted code.
                words = struct.unpack('>' + 'I' * (len(text) // 4), text)
                self.assertTrue(any(word & 0xFFFF0000 == 0x10000000 | (expected[3] << 21)
                                    for word in words))

    def test_02_failed_missing_unfired_and_debugger_error_controls(self):
        self.rejected(self.disposable('failed'), code=1)
        for name, log in (('no-exit', self.log.replace(trace.qualified.EXIT_MARKER, '')),
                          ('bad-driver', self.log.replace(trace.qualified.EXIT_MARKER,
                                                         'TRACE_EXIT inferior=1 code=11')),
                          ('not-installed', self.log.replace(trace.INSTALLED, '')),
                          ('child-failed', self.log.replace(trace.CHILD_EXIT, 'UGEN_NODE_CHILD_EXIT code=11')),
                          ('not-removed', self.log.replace(trace.REMOVED, '')),
                          ('python-error', self.log + '\nPython Exception\n'),
                          ('script-error', self.log + '\nError in sourced command file\n')):
            self.rejected(self.disposable(name), log=log)
        no_events = '\n'.join(line for line in self.log.splitlines()
                              if not line.startswith(trace.PREFIX))
        self.rejected(self.disposable('unfired'), log=no_events, message='probe did not fire')
        for name, log in (('outside-child', self.log + '\n' + trace.PREFIX +
                           json.dumps(self.records['late']['events'][0]) + '\n'),
                          ('late-cleanup', self.log.replace(trace.REMOVED, '') + '\n' + trace.REMOVED + '\n')):
            self.rejected(self.disposable(name), log=log, message='outside owned child lifetime')
        work = self.disposable('missing')
        (work / 'trace.o').unlink()
        self.rejected(work)
        work = self.disposable('empty')
        (work / 'trace.o').write_bytes(b'')
        self.rejected(work)

    def test_03_effective_text_function_relocation_and_all_pool_controls(self):
        parse = trace.screen.compiler.parse_object
        for kind in ('text', 'function', 'relocation'):
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
            with self.subTest(kind=kind), patch.object(trace.screen.compiler, 'parse_object', side_effect=changed):
                self.rejected(self.disposable('changed-' + kind),
                              message='changed text, functions, relocations or pools')
        sections = trace.screen.compiler.sections
        for pool in ('.rodata', '.rdata', '.data', '.sdata', '.lit4', '.bss', '.sbss'):
            def changed_pool(path):
                values = dict(sections(path))
                if Path(path).name == 'trace.o':
                    values[pool] = ('negative-control', b'\x01')
                return values
            with self.subTest(pool=pool), patch.object(trace.screen.compiler, 'sections', side_effect=changed_pool):
                self.rejected(self.disposable('changed-' + pool[1:]),
                              message='changed text, functions, relocations or pools')

    def test_04_event_parser_rejects_malformed_or_impossible_register_nodes(self):
        node = self.records['late']['events'][0]
        self.assertEqual(trace.node_events(trace.PREFIX + json.dumps(node)), [node])
        self.assertEqual(trace.node_events('other output'), [])
        for changes in ({'raw44': 3}, {'raw44': 288}, {'node': 0}, {'node': 1},
                        {'opcode': 256}, {'type_storage': 256}, {'raw36': -1},
                        {'raw48': True}, {'raw40': '4'}):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, 'Malformed UGEN'):
                trace.node_events(trace.PREFIX + json.dumps(dict(node, **changes)))
        for payload in ('null', '[]', '{}', '{bad', json.dumps(dict(node, extra=0))):
            with self.subTest(payload=payload), self.assertRaisesRegex(ValueError, 'Malformed UGEN'):
                trace.node_events(trace.PREFIX + payload)
        self.rejected(self.disposable('malformed'), log=self.log + '\nUGEN_NODE {}\n',
                      message='Malformed UGEN')

    def test_05_fingerprint_and_owned_path_gates(self):
        with patch.object(trace, 'compiler_fingerprints', return_value={}), \
                patch.object(trace.screen, 'compile_candidate') as compile:
            with self.assertRaisesRegex(ValueError, 'fingerprint mismatch'):
                trace.trace_nodes(self.root, self.out, 'wrong-compiler', trace.screen.SELECTED)
            compile.assert_not_called()
            self.rejected(self.disposable('changed-compiler'), message='fingerprint changed')
        for out, name in ((self.root / 'DOCS', 'invalid'), (self.out, '../invalid'), (self.out, '.')):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'name/output'):
                trace.trace_nodes(self.root, out, name, trace.screen.SELECTED)
        redirect = self.out / 'outside-redirect'
        redirect.unlink(missing_ok=True)
        redirect.symlink_to(self.root / 'DOCS', target_is_directory=True)
        try:
            with self.assertRaisesRegex(ValueError, 'name/output'):
                trace.trace_nodes(self.root, self.out, redirect.name, trace.screen.SELECTED)
        finally:
            redirect.unlink()

    def test_06_read_only_recipe_and_unchanged_production(self):
        script = trace.debugger_script(self.root)
        self.assertIn('set auto-load off', script)
        self.assertIn('read_memory', script)
        self.assertIn('refusing to resume a failed compiler', script)
        for forbidden in ('write_memory', '\ncall ', '\nattach ', 'target remote', '\nshell '):
            self.assertNotIn(forbidden, script)
        self.assertEqual(trace.compiler_fingerprints(self.root),
                         dict(trace.qualified.COMPILERS, ugen=trace.UGEN_SHA256))
        self.assertEqual(self.before, {path: hashlib.sha256((self.root / path).read_bytes()).hexdigest()
                                      for path in self.paths})


if __name__ == '__main__':
    unittest.main()
