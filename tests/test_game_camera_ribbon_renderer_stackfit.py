"""Qualify complete same-frame/save-slot forms and typed private-layout evidence."""

import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_camera_ribbon_renderer_stackfit as stackfit
from tools.tests import test_game_camera_ribbon_renderer_recovery as recovery
from tools.tests import test_game_camera_ribbon_renderer_fitting as fitting
from tools.tests import test_game_camera_ribbon_renderer_lifetimes as lifetime
from tools.tests.test_game_record_ring_renderer_recovery import external


FORMS = {
    'selected-last-output-scale-deltaX-deltaY-deltaZ': (547, 0x120, 463),
    'outer-active-last-output-scale-deltaX-deltaY-deltaZ': (545, 0x120, 512),
}


class GameCameraRibbonStackFitTests(unittest.TestCase):
    select = lifetime.GameCameraRibbonLifetimeTests.select
    compare = recovery.GameCameraRibbonRecoveryTests.compare
    receipt = recovery.GameCameraRibbonRecoveryTests.receipt
    run_host = recovery.GameCameraRibbonRecoveryTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.base = cls.root / 'conker/build/game-camera-ribbon-stackfit-test'
        cls.bodies = dict(stackfit.candidates())
        cls.compiled = {name: stackfit.base.compile_candidate(cls.root, cls.base / name, name, cls.bodies[name])
            for name in FORMS}
        cls.retail = list(struct.unpack_from('>546I',
            (cls.root / 'conker/conker.us.bin').read_bytes(), stackfit.base.ROM))
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)

    def exercise(self, method):
        with patch.object(fitting, 'FORMS', FORMS), patch.object(lifetime, 'FORMS', FORMS):
            method(self)

    def test_01_baseline_and_retail_frame_save_slots(self):
        baseline = json.loads((self.root /
            'conker/build/game-camera-ribbon-renderer-test/baseline.json').read_text())
        for key, path in (('source', recovery.SOURCE), ('elf', 'conker/build/conker.us.elf'),
                ('guards', 'conker/retail_word_patches.us.csv'), ('progress', 'conker/progress.csv')):
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), baseline[key])
        self.assertIn(stackfit.base.ORIGINAL, (self.root / recovery.SOURCE).read_text())
        for name, expected in FORMS.items():
            self.select(name)
            self.assertEqual(tuple(self.record[k] for k in ('body_words', 'frame', 'differences')), expected)
            self.assertEqual((self.record['diagnostics'], self.record['pool_bytes']), ('', 0))
            saved_gpr = [(w >> 16 & 31, w & 65535) for w in self.words[:30]
                if w >> 26 == 43 and w >> 21 & 31 == 29 and 16 <= w >> 16 & 31 <= 23
                and (w & 65535) < self.record['frame']]
            saved_fp = [(w >> 16 & 31, w & 65535) for w in self.words[:30]
                if w >> 26 == 61 and w >> 21 & 31 == 29]
            self.assertEqual(saved_gpr, [(18, 0x6C), (17, 0x68), (16, 0x64), (19, 0x70)])
            self.assertEqual(saved_fp, [(28, 0x58), (26, 0x50), (24, 0x48), (22, 0x40), (20, 0x38)])
            self.receipt('shape', dict(self.record, saved_gpr=saved_gpr, saved_fp=saved_fp,
                installed=False, guards_added=0, source_sha256=hashlib.sha256(self.bodies[name].encode()).hexdigest()))

    def test_02_complete_geometry_and_byte_domains(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_02_full_geometry_and_all_byte_widths)

    def test_03_mutations_and_abi_clobbers(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_03_live_setup_mutations_and_abi_clobbers)

    def test_04_faults_aliases_and_cyclic_prefixes(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_04_fault_prefixes_aliases_and_cyclic_prefixes)

    def test_05_actual_native32_complete_outputs(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_05_actual_native32_complete_outputs)

    def test_06_actual_dispatcher_and_protected_pointer(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_06_complete_dispatcher_and_protected_table)

    def test_07_nonlinear_guest_and_actual_native32(self):
        self.exercise(lifetime.GameCameraRibbonLifetimeTests.test_08_nonlinear_float32_geometry_guest_and_native)

    def test_08_copied_owner_neighbors_and_padding_boundary(self):
        original = (self.root / recovery.SOURCE).read_text()
        objects = []
        sources = [('before', original)] + [(name, original.replace(stackfit.base.ORIGINAL,
            self.bodies[name]).replace('#include <ultra64.h>\n',
            '#include <ultra64.h>\n' + stackfit.base.DECLARATIONS, 1)) for name in FORMS]
        for name, body in sources:
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
                if symbol == stackfit.base.FUNCTION:
                    continue
                prior = old[symbol]
                self.assertEqual((fn['size'], text[fn['value']:fn['value'] + fn['size']]),
                    (prior['size'], before[prior['value']:prior['value'] + prior['size']]), symbol)
                self.assertEqual({o - fn['value']: r for o, r in rel.items()
                    if fn['value'] <= o < fn['value'] + fn['size']},
                    {o - prior['value']: r for o, r in old_rel.items()
                    if prior['value'] <= o < prior['value'] + prior['size']}, symbol)
            self.assertEqual(recovery.normalized_pools(objects[0]), recovery.normalized_pools(obj))
            accepted = FORMS[name][0] <= stackfit.base.WORDS
            if accepted:
                assembly = recovery.emit_padded_assembly(obj, self.root / 'conker/asm/175250.s',
                    word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_175250')
                self.assertTrue(assembly)
            else:
                with self.assertRaisesRegex(ValueError, 'patched func_1514803C .* retail'):
                    recovery.emit_padded_assembly(obj, self.root / 'conker/asm/175250.s',
                        word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_175250')
            self.select(name)
            self.receipt('owner', dict(neighbors=len(current) - 1, diagnostics=0,
                unchanged_pools_and_relative_relocations=True, padder_accepts=accepted,
                byte_exact=False, production_installed=False))

    def test_09_last_output_scale_and_early_overwrite_negative(self):
        name = next(iter(FORMS))
        body = self.bodies[name]
        assignment = 'deltaX = normalX * deltaZ;'
        self.assertEqual(body.count(assignment), 2)
        broken = body.replace(assignment, 'deltaZ = normalX * deltaZ; deltaX = deltaZ;')
        meta, words = stackfit.base.compile_candidate(self.root, self.base, 'negative-early-scale-overwrite', broken)
        memory = next(lifetime.nonlinear_cases())
        reference = recovery.CameraRibbonReference(memory).run()
        model = recovery.CameraRibbonOracle(words, memory).run()
        self.assertNotEqual((external(model.memory), model.calls, model.r[2]),
            (external(reference.memory), reference.calls, reference.result))
        (self.base / 'negative.json').write_text(json.dumps(dict(meta, effective=True,
            allowed_scale_last_output=True, first_output_overwrite=False), indent=2) + '\n')

    def test_10_typed_decompiler_private_layout_and_remaining_limits(self):
        output = self.base / 'decompiler'
        text = stackfit.decompile(self.root, output)
        context = output / 'layout.c'
        fields = {'environmentA': 0xB4, 'environmentR': 0xBA, 'primitiveA': 0xBC, 'primitiveR': 0xC2,
            'records': 0xEC, 'origin': 0xF0, 'previous': 0xFC, 'current': 0x108, 'sync': 0x117, 'cursor': 0x118}
        checks = ['_Static_assert(sizeof(struct _m2c_stack_func_1514803C)==0x120,"frame");']
        checks += ['_Static_assert(offsetof(struct _m2c_stack_func_1514803C,%s)==%d,"%s");' %
            (field, offset, field) for field, offset in fields.items()]
        context.write_text('#include <stddef.h>\n' + stackfit.decompiler_context() + '\n' + '\n'.join(checks))
        subprocess.run(['gcc', '-m32', '-std=c11', '-Wall', '-Wextra', '-Werror', '-c', str(context),
            '-o', str(output / 'layout.o')], check=True, capture_output=True)
        self.assertIn('CameraRibbonPosition current;', text)
        self.assertIn('CameraRibbonPosition previous;', text)
        self.assertIn('previous.y - origin->position.y', text)
        self.assertIn('previous.z - origin->position.z', text)
        self.assertIn('(bitwise f32) previous', text)
        self.assertIn('cursor + 0x10', text)
        (output / 'receipt.json').write_text(json.dumps(dict(frame=0x120, offsets=fields,
            real_native32_layout_assertions=True, context_sha256=hashlib.sha256(context.read_bytes()).hexdigest(),
            decompiler_sha256=hashlib.sha256(text.encode()).hexdigest(),
            output_compiled_or_installed=False, unresolved_first_field_casts_and_pointer_units=True), indent=2) + '\n')

    def test_11_complete_catalog_finite_controls(self):
        records, groups = [], {}
        memory = next(lifetime.nonlinear_cases())
        for name, body in stackfit.candidates():
            meta, words = stackfit.base.compile_candidate(self.root, self.base / 'screen', name, body)
            for sample, mode in ((memory, 0), (recovery.fixture(bank=1, pattern=1), 0), (recovery.fixture(), 2)):
                self.compare(sample, words=words, mode=mode, write_order=False)
            fingerprint = hashlib.sha256(struct.pack('>%dI' % len(words), *words)).hexdigest()
            groups.setdefault(fingerprint, []).append(name)
            records.append(dict(meta, words_sha256=fingerprint,
                source_sha256=hashlib.sha256(body.encode()).hexdigest()))
        (self.base / 'catalog.json').write_text(json.dumps(dict(forms=records, emitted_groups=list(groups.values()),
            finite_samples_per_form=3, full_qualification_for_every_form=False,
            write_order_required=False), indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
