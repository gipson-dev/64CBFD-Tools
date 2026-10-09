"""Qualify full renderer input-view staging and measured private stack slots."""

import hashlib
import itertools
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_camera_ribbon_renderer_staging as staging
from tools.tests import test_game_camera_ribbon_renderer_recovery as recovery
from tools.tests import test_game_camera_ribbon_renderer_fitting as fitting
from tools.tests import test_game_camera_ribbon_renderer_lifetimes as lifetime
from tools.tests import test_game_camera_ribbon_renderer_stackfit as stackfit
from tools.tests.test_game_record_ring_renderer_recovery import external


FORMS = {
    'selected-short-input-local-view': (547, 0x120, 433),
    'selected-wide-input-local-view': (545, 0x120, 519),
}
VIEWS = (0, 1, -1, 32767, -32768, 32768, -32769, 65535, 0x10001,
    0x18000, 0x7FFF8000, 0x80008000, 0x7FFFFFFF, 0x80000000)


class GameCameraRibbonStagingTests(unittest.TestCase):
    select = lifetime.GameCameraRibbonLifetimeTests.select
    compare = recovery.GameCameraRibbonRecoveryTests.compare
    receipt = recovery.GameCameraRibbonRecoveryTests.receipt
    def run_host(self, body):
        if self.name == 'selected-callback-compatible':
            self.fixture += '''
static u8 *(*renderCallback)(u8 *,u8 *,s16)=func_1514803C;
static Gfx *invoke_callback(u8 *a,Gfx *p,s32 view){
    return (Gfx *)renderCallback(a,(u8 *)p,(s16)view);
}
'''
            body = body.replace('func_1514803C(', 'invoke_callback(')
        recovery.GameCameraRibbonRecoveryTests.run_host(self, body)

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.base = cls.root / 'conker/build/game-camera-ribbon-staging-test'
        cls.bodies = dict(staging.candidates())
        cls.compiled = {name: staging.compile_form(cls.root, cls.base / name, name, cls.bodies[name])
            for name in FORMS}
        cls.retail = list(struct.unpack_from('>546I',
            (cls.root / 'conker/conker.us.bin').read_bytes(), staging.base.ROM))
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)

    def exercise(self, method):
        with patch.object(fitting, 'FORMS', FORMS), patch.object(lifetime, 'FORMS', FORMS), \
                patch.object(stackfit, 'FORMS', FORMS):
            method(self)

    def test_01_baseline_frame_save_slots_and_private_cursor_sync_origin(self):
        baseline = json.loads((self.root /
            'conker/build/game-camera-ribbon-renderer-test/baseline.json').read_text())
        for key, path in (('source', recovery.SOURCE), ('elf', 'conker/build/conker.us.elf'),
                ('guards', 'conker/retail_word_patches.us.csv'), ('progress', 'conker/progress.csv')):
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), baseline[key])
        self.assertIn(staging.base.ORIGINAL, (self.root / recovery.SOURCE).read_text())
        for name, expected in FORMS.items():
            self.select(name)
            self.assertEqual(tuple(self.record[k] for k in ('body_words', 'frame', 'differences')), expected)
            self.assertEqual((self.record['diagnostics'], self.record['pool_bytes']), ('', 0))
            gpr = [(w >> 16 & 31, w & 65535) for w in self.words[:30]
                if w >> 26 == 43 and w >> 21 & 31 == 29 and 16 <= w >> 16 & 31 <= 23
                and (w & 65535) < self.record['frame']]
            fp = [(w >> 16 & 31, w & 65535) for w in self.words[:30]
                if w >> 26 == 61 and w >> 21 & 31 == 29]
            self.assertEqual(gpr, [(18, 0x6C), (17, 0x68), (16, 0x64), (19, 0x70)]
                if name == 'selected-short-input-local-view' else [(17, 0x68), (16, 0x64), (19, 0x70), (18, 0x6C)])
            self.assertEqual(fp, [(28, 0x58), (26, 0x50), (24, 0x48), (22, 0x40), (20, 0x38)])
            backend = self.words.index(0x0D475758)
            origin = self.words.index(0x0D4512CD)
            self.assertIn(0x27A70118, self.words[max(0, backend - 8):backend + 2])
            self.assertTrue(any(w >> 26 == 40 and w >> 21 & 31 == 29 and w & 65535 == 0x117
                for w in self.words[backend:origin + 2]))
            self.assertIn(0xAFA200F0, self.words[origin:origin + 10])
            self.assertTrue(any(w & 0xFFE0FFFF == 0x27A000FC for w in self.words))
            self.assertTrue(any(w & 0xFFE0FFFF == 0x27A00108 for w in self.words))
            self.receipt('shape', dict(self.record, saved_gpr=gpr, saved_fp=fp,
                cursor=0x118, sync=0x117, origin=0xF0, previous=0xFC, current=0x108,
                register_roles_and_colors_match=False, installed=False, guards_added=0))

    def test_02_complete_geometry_and_all_byte_domains(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_02_full_geometry_and_all_byte_widths)

    def test_03_setup_mutations_and_abi_clobbers(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_03_live_setup_mutations_and_abi_clobbers)

    def test_04_faults_aliases_and_cyclic_prefixes(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_04_fault_prefixes_aliases_and_cyclic_prefixes)

    def test_05_actual_native32_complete_outputs(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_05_actual_native32_complete_outputs)

    def test_06_actual_dispatcher_and_protected_pointer(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_06_complete_dispatcher_and_protected_table)

    def test_07_nonlinear_guest_and_actual_native32(self):
        self.exercise(lifetime.GameCameraRibbonLifetimeTests.test_08_nonlinear_float32_geometry_guest_and_native)

    def test_08_copied_owner_neighbors_and_actual_padding(self):
        self.exercise(stackfit.GameCameraRibbonStackFitTests.test_08_copied_owner_neighbors_and_padding_boundary)

    def test_09_raw_view_clipping_guest_and_native32(self):
        reference = recovery.CameraRibbonReference(recovery.fixture()).run()
        rows = []
        for address in range(recovery.VERTICES, reference.cursor, 16):
            values = [recovery.narrow(recovery.read(reference.memory, address + offset, 2), 16)
                for offset in (0, 2, 4, 6, 8, 10)]
            values += [recovery.read(reference.memory, address + offset, 1) for offset in (12, 13, 14, 15)]
            rows.append('{%s}' % ','.join(map(str, values)))
        array = 'static const int viewExpected[][10]={%s};\n' % ','.join(rows)
        fixture = recovery.NATIVE_FIXTURE.replace('||view||size', '||view!=expectedView||size').replace(
            'if(view)error=2;', 'if(view!=expectedView)error=2;')
        self.assertNotEqual(fixture, recovery.NATIVE_FIXTURE)
        calls = []
        for view in VIEWS:
            call = '{s32 rawView=(s32)0x%X;\n' % (view & 0xFFFFFFFF)
            call += 'initialize(3,3,0,4,0,0,0,128); expectedView=%d;\n' % recovery.narrow(view, 16)
            call += 'if(func_1514803C(actor,commands,rawView)!=commands+%d||error)return 1;\n' % (
                (reference.result - recovery.OUTPUT) // 8)
            call += 'if(check_vertices(viewExpected,%d)||!unchanged())return 2;\n' % len(rows)
            for address in range(recovery.OUTPUT + 48, reference.result, 8):
                first, second = recovery.read(reference.memory, address), recovery.read(reference.memory, address + 4)
                value = '(u32)((u8 *)vertices+%d)' % (second - recovery.VERTICES) if first == 0x01004008 else str(second)
                slot = (address - recovery.OUTPUT) // 8
                call += 'if(commands[%d].words.w0!=0x%X||commands[%d].words.w1!=%s)return 3;\n' % (
                    slot, first, slot, value)
            call += 'if(check_commands_tail(48,%d))return 4;\n' % (reference.result - recovery.OUTPUT)
            call += '}\n'
            calls.append(call)
        for name in FORMS:
            self.select(name)
            for view, phase, bank in itertools.product(VIEWS, (0, 8), (0, 1)):
                self.compare(recovery.fixture(bank=bank), view=view, phase=phase)
            self.fixture = recovery.NATIVE_TYPES + 'float sqrtf(float);\n' + staging.base.DECLARATIONS + \
                'static s16 expectedView;\n' + fixture + '\n' + self.bodies[name] + '\n' + array
            self.run_host(''.join(calls))
            self.receipt('views', dict(raw_values=len(VIEWS), guest_cases=len(VIEWS) * 4,
                guest_executions=len(VIEWS) * 8, actual_native32_cases=len(VIEWS),
                full_vertices_commands_and_canaries=True, clipped_both_helper_arguments=True,
                original_source_parameter_type_proven=False))

    def test_10_unclipped_view_negative(self):
        body = self.bodies['selected-wide-input-local-view']
        broken = body.replace('    s16 view;', '    s32 view;').replace('view = (s16)inputView;', 'view = inputView;')
        self.assertNotEqual(broken, body)
        meta, words = staging.compile_form(self.root, self.base, 'negative-unclipped-view', broken)
        memory = recovery.fixture()
        model = recovery.CameraRibbonOracle(words, memory, view=0x18000).run()
        reference = recovery.CameraRibbonReference(memory, view=0x18000).run()
        self.assertNotEqual((external(model.memory), model.calls, model.r[2]),
            (external(reference.memory), reference.calls, reference.result))
        (self.base / 'negative.json').write_text(json.dumps(dict(meta, effective=True,
            raw_view='0x18000', observable_helper_argument_difference=True), indent=2) + '\n')

    def test_11_catalog_profile_controls_and_restored_profile_registry(self):
        original_profiles = dict(staging.base.PROFILES)
        records, groups, unroll = [], {}, {}
        memory = next(lifetime.nonlinear_cases())
        for name, body in staging.candidates():
            for profile in ('o2g3', 'o2', 'o2g3-no-unroll'):
                meta, words = staging.compile_form(self.root, self.base / 'screen', name + '-' + profile, body, profile)
                self.assertEqual(staging.base.PROFILES, original_profiles)
                for sample, mode in ((memory, 0), (recovery.fixture(bank=1, pattern=1), 0), (recovery.fixture(), 2)):
                    self.compare(sample, words=words, mode=mode, view=0x18000, write_order=False)
                fingerprint = hashlib.sha256(struct.pack('>%dI' % len(words), *words)).hexdigest()
                groups.setdefault(fingerprint, []).append(name + '-' + profile)
                records.append(dict(meta, words_sha256=fingerprint,
                    source_sha256=hashlib.sha256(body.encode()).hexdigest()))
                if profile != 'o2':
                    unroll.setdefault(name, {})[profile] = fingerprint
        self.assertTrue(all(row['o2g3'] == row['o2g3-no-unroll'] for row in unroll.values()))
        (self.base / 'catalog.json').write_text(json.dumps(dict(forms=records, emitted_groups=list(groups.values()),
            finite_samples_per_form=3, full_qualification_for_every_form=False, write_order_required=False,
            no_unroll_changes_emitted_words=False, profile_registry_restored=True), indent=2) + '\n')


    def test_12_compact_geometry_nonlinear_guest_and_native32(self):
        compact = ('compact-geometry', 'compact-retained-rays')
        for name in compact:
            self.compiled[name] = staging.compile_form(self.root, self.base / name, name, self.bodies[name])
        with patch.object(lifetime, 'FORMS', {name: None for name in compact}):
            lifetime.GameCameraRibbonLifetimeTests.test_08_nonlinear_float32_geometry_guest_and_native(self)

    def test_13_compact_normal_input_overwrite_negative(self):
        body = self.bodies['compact-geometry']
        lines = body.splitlines(True)
        replacements = 0
        indices = [index for index, line in enumerate(lines) if line.strip().startswith('normalX = deltaY *')]
        for index in indices:
            self.assertTrue(lines[index + 1].strip().startswith('deltaZ = deltaZ *'))
            lines[index], lines[index + 1] = lines[index + 1], lines[index]
            replacements += 1
        self.assertEqual(replacements, 2)
        meta, words = staging.compile_form(self.root, self.base, 'negative-normal-input-overwrite', ''.join(lines))
        memory = next(lifetime.nonlinear_cases())
        model = recovery.CameraRibbonOracle(words, memory).run()
        reference = recovery.CameraRibbonReference(memory).run()
        self.assertNotEqual((external(model.memory), model.calls, model.r[2]),
            (external(reference.memory), reference.calls, reference.result))
        (self.base / 'compact-negative.json').write_text(json.dumps(dict(meta, effective=True,
            swapped_normal_xy_overwrites_live_delta_z=True), indent=2) + '\n')


    def test_14_native_recovered_callback_type_projection(self):
        caller = (self.root / 'conker/src/game/generated_174BF0.c').read_text()
        self.assertIn('extern u8 *(*D_8008A2A4[])(u8 *, u8 *, s16);', caller)
        name = 'selected-callback-compatible'
        self.compiled[name] = staging.compile_form(self.root, self.base / name, name, self.bodies[name])
        meta, _ = self.compiled[name]
        self.assertEqual((meta['body_words'], meta['frame']), (549, 0x128))
        with patch.dict(globals(), FORMS={name: None}):
            self.test_09_raw_view_clipping_guest_and_native32()
        self.select(name)
        self.receipt('callback-type', dict(actual_native32_cases=len(VIEWS),
            exact_recovered_function_pointer_type_checked_by_native_compiler=True,
            callbacks_and_complete_vertices_commands_canaries=True,
            full_native_caller_not_proven=True, production_installed=False, slot_fits=False))


if __name__ == '__main__':
    unittest.main()
