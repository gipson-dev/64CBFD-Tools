"""Qualify complete private-lifetime forms without promoting them to production."""

import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_camera_ribbon_renderer_fitting as fitting
from tools.tests import test_game_camera_ribbon_renderer_recovery as recovery
from tools.tests.test_game_record_ring_renderer_recovery import external, writes


FORMS = {
    'selected-inline-rays': (543, 0x120, 544, [28, 26, 24, 22, 20]),
    'outer-indexed-mixed-normalX-normalY-normalZ-deltaX':
        (546, 0x120, 513, [30, 28, 26, 24, 22, 20]),
}


class GameCameraRibbonFittingTests(unittest.TestCase):
    compare = recovery.GameCameraRibbonRecoveryTests.compare
    receipt = recovery.GameCameraRibbonRecoveryTests.receipt
    run_host = recovery.GameCameraRibbonRecoveryTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.base = cls.root / 'conker/build/game-camera-ribbon-fitting-test'
        cls.bodies = dict(fitting.candidates())
        cls.compiled = {}
        for name in FORMS:
            out = cls.base / name
            cls.compiled[name] = fitting.base.compile_candidate(cls.root, out, name, cls.bodies[name])
        cls.retail = list(struct.unpack_from('>546I',
            (cls.root / 'conker/conker.us.bin').read_bytes(), fitting.base.ROM))
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)

    def select(self, name):
        self.out = self.base / name
        self.record, self.words = self.compiled[name]

    def test_01_shapes_and_unchanged_production_baseline(self):
        baseline = json.loads((self.root /
            'conker/build/game-camera-ribbon-renderer-test/baseline.json').read_text())
        for key, path in (('source', recovery.SOURCE), ('elf', 'conker/build/conker.us.elf'),
                ('guards', 'conker/retail_word_patches.us.csv'), ('progress', 'conker/progress.csv')):
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), baseline[key])
        self.assertIn(fitting.base.ORIGINAL, (self.root / recovery.SOURCE).read_text())
        for name, expected in FORMS.items():
            self.select(name)
            self.assertEqual(tuple(self.record[k] for k in
                ('body_words', 'frame', 'differences', 'saved_FP')), expected)
            self.assertEqual((self.record['diagnostics'], self.record['pool_bytes']), ('', 0))
            saved_gpr = [(word >> 16 & 31, word & 65535) for word in self.words[:30]
                if word >> 26 == 43 and word >> 21 & 31 == 29 and 16 <= word >> 16 & 31 <= 23]
            self.assertEqual(saved_gpr, [(17, 0x6C), (16, 0x68), (18, 0x70)]
                if name == 'selected-inline-rays' else [(18, 0x74), (17, 0x70), (16, 0x6C), (19, 0x78)])
            self.receipt('shape', dict(self.record, saved_gpr=saved_gpr, installed=False, guards_added=0))

    def test_02_full_geometry_and_all_byte_widths(self):
        for name in FORMS:
            with self.subTest(form=name):
                self.select(name)
                recovery.GameCameraRibbonRecoveryTests.test_02_full_guest_geometry_setup_and_byte_width_cases(self)

    def test_03_live_setup_mutations_and_abi_clobbers(self):
        for name in FORMS:
            with self.subTest(form=name):
                self.select(name)
                recovery.GameCameraRibbonRecoveryTests.test_03_setup_mutations_failure_and_live_captured_pointer_lifetimes(self)

    def test_04_fault_prefixes_aliases_and_cyclic_prefixes(self):
        memory = recovery.fixture()
        retail = recovery.CameraRibbonOracle(self.retail, memory).run()
        public = sorted({address + i for event, address, width, value in retail.events
            if event in ('R', 'W') and not recovery.STACK - 0x600 <= address < recovery.STACK + 0x140
            for i in range(width)})

        class Prefix(recovery.CameraRibbonOracle):
            def put(self, address, value, size):
                super().put(address, value, size)
                if len(writes(self)) >= 200:
                    raise RuntimeError('public write bound')

        for name in FORMS:
            self.select(name)
            for missing in public[::3]:
                altered = dict(memory)
                del altered[missing]
                models = [recovery.CameraRibbonOracle(body, altered) for body in (self.words, self.retail)]
                for model in models:
                    with self.assertRaisesRegex(AssertionError, 'unmapped'):
                        model.run()
                self.assertEqual(external(models[0].memory), external(models[1].memory))
                self.assertEqual(models[0].calls, models[1].calls)
                self.assertEqual(writes(models[0]), writes(models[1]))
            for pointer in (recovery.RECORDS - 4, recovery.RECORDS, recovery.RECORDS + 4,
                    recovery.PAYLOAD, recovery.PAYLOAD + 4):
                altered = recovery.fixture()
                recovery.put(altered, recovery.ACTOR + 0x94, pointer)
                self.compare(altered)
            for altered in (recovery.fixture(count=4, head=3, start=255),
                    recovery.fixture(count=255, head=0, start=253)):
                models = [Prefix(body, altered) for body in (self.words, self.retail)]
                for model in models:
                    with self.assertRaisesRegex(RuntimeError, 'public write bound'):
                        model.run()
                self.assertEqual(external(models[0].memory), external(models[1].memory))
                self.assertEqual(models[0].calls, models[1].calls)
                self.assertEqual(writes(models[0]), writes(models[1]))
            self.receipt('prefixes', dict(missing_byte_pairs=len(public[::3]), aliases=5,
                cyclic_pairs=2, public_write_bound=200, production_bound_added=False))

    def test_05_actual_native32_complete_outputs(self):
        for name in FORMS:
            with self.subTest(form=name):
                self.select(name)
                # The existing native fixture must compile this form, not the old selected body.
                with patch.object(recovery.screen, 'SELECTED', self.bodies[name]):
                    recovery.GameCameraRibbonRecoveryTests.test_07_actual_native32_full_vertex_bytes_commands_and_typed_callbacks(self)

    def test_06_complete_dispatcher_and_protected_table(self):
        for name in FORMS:
            with self.subTest(form=name):
                self.select(name)
                recovery.GameCameraRibbonRecoveryTests.test_08_actual_graphics_dispatcher_protected_table_and_full_leaf(self)

    def test_07_effective_invalid_reuse_control(self):
        body = fitting.base.SELECTED.replace('    f32 offsetX, offsetY, offsetZ;\n', '')
        for axis in 'XYZ':
            body = body.replace('offset' + axis, 'delta' + axis)
        body = body.replace('f32 length, scale;', 'f32 length;').replace(
            'scale =', 'deltaX =').replace('* scale;', '* deltaX;')
        meta, words = fitting.base.compile_candidate(self.root, self.base, 'invalid-factor-overlap', body)
        memory = recovery.fixture()
        model = recovery.CameraRibbonOracle(words, memory).run()
        reference = recovery.CameraRibbonReference(memory).run()
        self.assertNotEqual(external(model.memory), external(reference.memory))
        self.assertTrue(all('-mixed-deltaX-deltaY-deltaZ-deltaX' not in name for name in self.bodies))
        (self.base / 'invalid-reuse.json').write_text(json.dumps(dict(meta,
            effective=True, witness='default finite geometry', accepted=False), indent=2) + '\n')

    def test_08_copied_owner_isolation_and_actual_padding(self):
        original = (self.root / recovery.SOURCE).read_text()
        objects = []
        for name, body in [('before', original)] + [(name, original.replace(fitting.base.ORIGINAL,
                self.bodies[name]).replace('#include <ultra64.h>\n',
                '#include <ultra64.h>\n' + fitting.base.DECLARATIONS, 1)) for name in FORMS]:
            obj, diagnostics = recovery.compile_owner(self.root, self.base, body, 'owner-' + name)
            self.assertEqual(diagnostics, [])
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'),
                '-O2', '-g3', str((self.base / ('owner-' + name + '.c')).relative_to(self.root / 'conker')),
                '--post-process', str(obj.relative_to(self.root / 'conker')),
                '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker',
                check=True, capture_output=True)
            objects.append(obj)
        before, old, old_rel = recovery.parse_object(objects[0])
        for name, obj in zip(FORMS, objects[1:]):
            text, current, rel = recovery.parse_object(obj)
            self.assertEqual(current.keys(), old.keys())
            for symbol, fn in current.items():
                if symbol == fitting.base.FUNCTION:
                    continue
                prior = old[symbol]
                self.assertEqual((fn['size'], text[fn['value']:fn['value'] + fn['size']]),
                    (prior['size'], before[prior['value']:prior['value'] + prior['size']]), symbol)
                self.assertEqual({o - fn['value']: r for o, r in rel.items()
                    if fn['value'] <= o < fn['value'] + fn['size']},
                    {o - prior['value']: r for o, r in old_rel.items()
                    if prior['value'] <= o < prior['value'] + prior['size']}, symbol)
            self.assertEqual(recovery.normalized_pools(objects[0]), recovery.normalized_pools(obj))
            assembly = recovery.emit_padded_assembly(obj, self.root / 'conker/asm/175250.s',
                word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_175250')
            self.assertTrue(assembly)
            self.select(name)
            self.receipt('owner', dict(neighbors=len(current) - 1, diagnostics=0,
                unchanged_pools_and_relative_relocations=True, padder_accepts=True,
                byte_exact=False, production_installed=False))


if __name__ == '__main__':
    unittest.main()
