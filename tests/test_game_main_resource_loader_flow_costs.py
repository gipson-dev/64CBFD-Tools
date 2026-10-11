"""Qualify uninstalled status-join measurements and preserve the linked baseline."""
import hashlib
import itertools
import json
import struct
import subprocess
import unittest
from pathlib import Path

from tools.experiments import game_main_resource_loader_flow_costs as flow
from tools.experiments import game_main_resource_loader_guarded_match as matching
from tools.tests import test_game_main_resource_loader as recovery


class GameMainResourceLoaderFlowCostTests(unittest.TestCase):
    entry = 0x15400000
    assemble = classmethod(recovery.GameMainResourceLoaderTests.assemble.__func__)

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/'conker/build/game-main-resource-loader-flow-costs-test'
        cls.out.mkdir(exist_ok=True)
        checkpoint = cls.root/'conker/build/game-main-resource-loader-lifetimes-test'
        cls.parentCheckpoint = (checkpoint/'checkpoint-elf').read_bytes()
        cls.paths = dict(source=recovery.screen.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv',
            rodata='conker/asm/data/23B8A0.rodata.s', symbols='conker/symbol_addrs.us.txt',
            undefined='conker/undefined_funcs_auto.txt', layout='conker/retail_layout.us.txt')
        cls.expected = json.loads((checkpoint/'checkpoint.json').read_text())
        cls.expected.update(source='25fd41ff70c4fb4db5c7649c74c27fbd4d72ed10831f95ffcb1abdaf75f18a52',
            elf='2129eb586ceac58a8201542a83a62601853a16d8589f49596fdeb137fb02fcaf')
        source = matching.parent_source(cls.root).encode('ascii')
        if hashlib.sha256(source).hexdigest() != cls.expected['source']:
            from tools.experiments import game_main_resource_loader_count_lifetimes as count
            banked = cls.root/'conker/build/game-main-resource-loader-count-lifetimes-test'
            for name in cls.paths:
                assert hashlib.sha256((banked/('checkpoint-'+name)).read_bytes()).hexdigest() == cls.expected[name]
            original_source = (banked/'checkpoint-source').read_text()
            count_source = count.install(original_source)
            if source.decode().replace('\r\n', '\n') == count_source:
                meta, words = count.measure(cls.root, cls.out, 'qualified-count-lifetime', count.SELECTED)
                assert (meta['body_words'], meta['frame'], meta['differences']) == (274, 0x78, 98)
            else:
                from tools.experiments import game_main_resource_loader_private_layout as layout
                layout_source = layout.install(count_source)
                if source.decode().replace('\r\n', '\n') == layout_source:
                    meta, words = layout.measure(cls.root, cls.out, 'qualified-private-layout', layout.SELECTED)
                    assert (meta['body_words'], meta['frame'], meta['differences']) == (274, 0x78, 24)
                else:
                    from tools.experiments import game_main_resource_loader_remaining_schedule as schedule
                    assert source.decode().replace('\r\n', '\n') == schedule.install(layout_source)
                    meta, words = schedule.measure(cls.root, cls.out, 'qualified-remaining-schedule', schedule.SELECTED)
                    assert (meta['body_words'], meta['frame'], meta['differences']) == (274, 0x78, 22)
            assert (meta['diagnostics'], meta['pool_bytes']) == ('', 0)
            original_elf = (banked/'checkpoint-elf').read_bytes()
            expected_elf = bytearray(original_elf)
            offset = recovery.elf_slot_offset(original_elf, recovery.screen.ENTRY, 274*4)
            struct.pack_into('>274I', expected_elf, offset, *matching.installed_words(cls.root, words))
            actual_elf = matching.parent_elf(cls.root, original_elf)
            assert bytes(expected_elf) == actual_elf
            assert recovery.metadata(original_elf) == recovery.metadata(actual_elf)
            cls.expected.update(source=hashlib.sha256(source).hexdigest(),
                elf=hashlib.sha256(expected_elf).hexdigest())
        for name, path in cls.paths.items():
            if name == 'guards':
                current = matching.current_guard_bytes(cls.root, (checkpoint/'checkpoint-guards').read_bytes())
                cls.expected[name] = hashlib.sha256(current).hexdigest()
            assert hashlib.sha256(cls.current_input(name, path)).hexdigest() == cls.expected[name]
        cls.retail = list(struct.unpack_from('>274I',
            (cls.root/'conker/conker.us.bin').read_bytes(), recovery.screen.ROM))
        assembly = (cls.root/'conker/asm/6A3D0.s').read_text().split(
            'glabel '+recovery.screen.FUNCTION, 1)[1].split('endlabel '+recovery.screen.FUNCTION, 1)[0]
        cls.assemble('original', '.text\n.set noat\n.set noreorder\n.globl '+recovery.screen.FUNCTION+
            '\n.type '+recovery.screen.FUNCTION+',@function\n'+recovery.screen.FUNCTION+':\n'+assembly+
            '\n.size '+recovery.screen.FUNCTION+',.-'+recovery.screen.FUNCTION+'\n')
        cls.bodies = dict(flow.candidates())
        cls.records = {}
        for name, body in cls.bodies.items():
            cls.records[name] = flow.measure(cls.root, cls.out, name, body)
        (cls.out/'measurements.json').write_text(json.dumps(
            [record[0] for record in cls.records.values()], indent=2)+'\n')

    @classmethod
    def current_input(cls, name, path):
        if name == 'source':
            return matching.parent_source(cls.root).encode('ascii')
        if name == 'elf':
            return matching.parent_elf(cls.root, cls.parentCheckpoint)
        return (cls.root/path).read_bytes()

    def compare(self, memory, forms=None, **settings):
        settings.setdefault('entry', self.entry)
        return recovery.GameMainResourceLoaderTests.compare(self, memory, forms=forms, **settings)

    def receipt(self, name, **values):
        prefix = getattr(self, 'candidate', 'all')
        (self.out/(prefix+'-'+name+'.json')).write_text(json.dumps(values, indent=2)+'\n')

    def test_01_discriminating_complete_shapes(self):
        self.assertEqual(len(list(flow.candidates())), len(self.bodies))
        self.assertEqual(len(self.records), 31)
        for meta, words in self.records.values():
            self.assertEqual((meta['pool_bytes'], meta['diagnostics']), (0, ''))
            self.assertEqual(meta['body_words'], len(words))
            self.assertEqual(meta['profile'], 'retail')
        early, join, presence = (self.records[name][0] for name in
            ('early', 'request-join', 'presence-request-join'))
        self.assertEqual((early['body_words'], early['frame'], early['differences']), (287, 0x80, 262))
        self.assertNotIn(22, early['saved_registers'])
        self.assertEqual((join['body_words'], join['frame'], join['differences']), (276, 0x88, 194))
        self.assertEqual((presence['body_words'], presence['frame'], presence['differences']), (274, 0x88, 194))
        for meta in (join, presence):
            self.assertEqual(meta['saved_registers'], list(range(16, 23)))
            self.assertIn(22, meta['opening_zero_destinations'])
        self.receipt('shape', candidates=31, complete_status_join_selects_S6=True,
            cost_internals_not_observed=True, installed=False, frame_not_restored=True)

    def test_02_full_public_reference_for_every_candidate(self):
        for name, (meta, words) in self.records.items():
            with self.subTest(candidate=name):
                self.candidate, self.meta = name, meta
                self.raw = self.relink(name, recovery.S, self.entry)
                cases, reached = 0, set()
                for first, second, extra, boundary, phase in itertools.product(
                        (0, 1, 3), (0, 1, 3), (0, 2), (False, True), (0, 8)):
                    for failure in (None, 'request', 'extras', 'secondary', 'auxiliary', 'third', 'fourth'):
                        results = {} if failure is None else {failure: 0 if failure == 'request' else 0x80000010}
                        for optional in (0, 7):
                            models = self.compare(recovery.fixture(first_count=first, second_count=second,
                                extra_count=extra, boundary=boundary, flags=0x4000, optional=optional),
                                results=results, phase=phase)
                            reached.update(models[0].visits)
                            cases += 1
                for identity, present in itertools.product((0, 186, 187, 255, 256, 0x7FFFFFFF), (False, True)):
                    models = self.compare(recovery.fixture(identity=identity, present=present), identity=identity)
                    reached.update(models[0].visits)
                    cases += 1
                models = self.compare(recovery.fixture(), results=dict(secondary=4),
                    actions={('cleanup', 0): ((recovery.address('D_800D19A0'), 0, 4),)})
                reached.update(models[0].visits)
                cases += 1
                self.assertEqual(reached, set(range(self.entry, self.entry+274*4, 4))-{self.entry+0x48})
                self.receipt('guest', cases=cases, executions=cases*2, reached_retail_words=len(reached),
                    isolated_entry=self.entry, full_untrimmed_candidate_words=meta['body_words'],
                    independent_public_memory_access_call_error_reference=True)

    def test_03_live_loops_and_cleanup_for_every_candidate(self):
        for name, (meta, words) in self.records.items():
            with self.subTest(candidate=name):
                self.candidate, self.meta = name, meta
                self.raw = self.relink(name, recovery.S, self.entry)
                recovery.GameMainResourceLoaderTests.test_03_live_loops_and_cleanup_callbacks(self)

    def relink(self, name, symbols, entry, size=None):
        script = self.out/'rebase.ld'
        elf = script.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
        subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', recovery.screen.FUNCTION,
            *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(self.out/(name+'.o'))],
            check=True, capture_output=True)
        if size is None:
            size = 274 if name == 'original' else self.records[name][0]['body_words']
        return list(struct.unpack_from('>%dI' % size, recovery.sections(elf)['.text'][1]))

    def test_04_ignored_word_rebases_and_effective_controls(self):
        cases = links = 0
        for entry, delta in ((self.entry, 0), (0x15207FF0, 0x47FFC), (0x15308004, 0x88004)):
            symbols = {name: value+delta if name.startswith('D_') else value for name, value in recovery.S.items()}
            retail = self.relink('original', symbols, entry)
            links += 1
            for name in self.records:
                words = self.relink(name, symbols, entry)
                links += 1
                for identity, unused, present, extras in itertools.product(
                        (-1, 7, 186, 187, 255, 0x7FFFFFFF), (0, 1, 0xFFFFFFFF, 0x80000000),
                        (False, True), (0, 1)):
                    self.compare(recovery.fixture(identity=identity, present=present, symbols=symbols),
                        forms=(retail, words), identity=identity, unused=unused, extras=extras,
                        symbols=symbols, entry=entry)
                    cases += 1
        body = self.bodies['request-join'].replace('        failed = 1;\n        goto done;',
            '        failed = 0;\n        goto done;')
        self.assertNotEqual(body, self.bodies['request-join'])
        negative, _ = flow.lifetime.loader.compile_candidate(self.root, self.out, 'negative-lost-request-error', body)
        wrong = self.relink('negative-lost-request-error', recovery.S, self.entry, negative['body_words'])
        with self.assertRaises(AssertionError):
            self.compare(recovery.fixture(), forms=(self.retail, wrong), results=dict(request=0))
        self.candidate = 'all'
        self.receipt('rebases', cases=cases, executions=cases*2, independent_links=links,
            ignored_incoming_word_qualified=True, effective_lost_request_error_control=True,
            padders_owner_native32_private_frame_faults_not_qualified_for_uninstalled_variants=True)

    def test_05_preserve_current_linked_baseline(self):
        for name, path in self.paths.items():
            self.assertEqual(hashlib.sha256(self.current_input(name, path)).hexdigest(), self.expected[name])
        audit = recovery.audit_layout(self.root/'conker/build/conker.us.elf', self.root/'conker')
        self.assertTrue(audit['exact'], audit)
        self.candidate = 'all'
        self.receipt('baseline', hashes=self.expected,
            installed_source_ELF_data_guards_conversion_rows_unchanged_after_exact_child_projection=True,
            protected_data=audit)


if __name__ == '__main__':
    unittest.main()
