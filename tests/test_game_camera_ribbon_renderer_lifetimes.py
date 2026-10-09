"""Complete lifetime forms, nonlinear float32 geometry, and unsafe capture controls."""

import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_camera_ribbon_renderer_lifetimes as lifetime
from tools.tests import test_game_camera_ribbon_renderer_recovery as recovery
from tools.tests import test_game_camera_ribbon_renderer_fitting as fitting
from tools.tests.test_game_record_ring_renderer_recovery import external


FORMS = {
    'selected-typed-1-1': (547, 0x130, 440),
    'inline-local-stride': (545, 0x120, 526),
}


def nonlinear_cases():
    state = 0x1514803C

    def value():
        nonlocal state
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        return ((state >> 8) % 6001 - 3000) / 16.0

    for case in range(128):
        memory = recovery.fixture(bank=case % 2)
        for index in range(4):
            for axis in range(3):
                recovery.put(memory, recovery.RECORDS + index * 20 + axis * 4, recovery.bits(value()))
        for axis in range(3):
            recovery.put(memory, recovery.ORIGIN + axis * 4, recovery.bits(value()))
        recovery.put(memory, recovery.PAYLOAD, recovery.bits(value() / 4.0))
        yield memory


class GameCameraRibbonLifetimeTests(unittest.TestCase):
    compare = recovery.GameCameraRibbonRecoveryTests.compare
    receipt = recovery.GameCameraRibbonRecoveryTests.receipt

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.base = cls.root / 'conker/build/game-camera-ribbon-lifetime-test'
        cls.bodies = dict(lifetime.candidates())
        cls.compiled = {}
        for name in FORMS:
            cls.compiled[name] = lifetime.base.compile_candidate(cls.root, cls.base / name, name, cls.bodies[name])
        cls.retail = list(struct.unpack_from('>546I',
            (cls.root / 'conker/conker.us.bin').read_bytes(), lifetime.base.ROM))
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)

    def select(self, name):
        self.name = name
        self.out = self.base / name
        self.record, self.words = self.compiled[name]

    def exercise(self, method):
        with patch.object(fitting, 'FORMS', FORMS):
            method(self)

    def run_host(self, body):
        if self.name == 'selected-typed-1-1':
            body = body.replace('func_1514803C(actor,', 'func_1514803C((CameraRibbonActor *)actor,')
        recovery.GameCameraRibbonRecoveryTests.run_host(self, body)

    def test_01_production_baseline_and_complete_shapes(self):
        baseline = json.loads((self.root /
            'conker/build/game-camera-ribbon-renderer-test/baseline.json').read_text())
        for key, path in (('source', recovery.SOURCE), ('elf', 'conker/build/conker.us.elf'),
                ('guards', 'conker/retail_word_patches.us.csv'), ('progress', 'conker/progress.csv')):
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), baseline[key])
        self.assertIn(lifetime.base.ORIGINAL, (self.root / recovery.SOURCE).read_text())
        for name, expected in FORMS.items():
            self.select(name)
            self.assertEqual(tuple(self.record[k] for k in ('body_words', 'frame', 'differences')), expected)
            self.assertEqual((self.record['diagnostics'], self.record['pool_bytes'], self.record['saved_FP']),
                ('', 0, [28, 26, 24, 22, 20]))
            saved = [(word >> 16 & 31, word & 65535) for word in self.words[:30]
                if word >> 26 == 43 and word >> 21 & 31 == 29 and 16 <= word >> 16 & 31 <= 23
                and (word & 65535) < self.record['frame']]
            self.assertEqual(saved, [(18, 0x6C), (17, 0x68), (16, 0x64), (19, 0x70)]
                if name == 'selected-typed-1-1' else [(17, 0x6C), (16, 0x68), (18, 0x70)])
            self.receipt('shape', dict(self.record, saved_gpr=saved, installed=False, guards_added=0,
                source_sha256=hashlib.sha256(self.bodies[name].encode()).hexdigest()))

    def test_02_full_geometry_and_all_byte_widths(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_02_full_geometry_and_all_byte_widths)

    def test_03_setup_mutations_and_abi_clobbers(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_03_live_setup_mutations_and_abi_clobbers)

    def test_04_faults_aliases_and_cyclic_prefixes(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_04_fault_prefixes_aliases_and_cyclic_prefixes)

    def test_05_native32_complete_byte_domain_outputs(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_05_actual_native32_complete_outputs)

    def test_06_actual_dispatcher_and_protected_pointer(self):
        self.exercise(fitting.GameCameraRibbonFittingTests.test_06_complete_dispatcher_and_protected_table)

    def test_07_copied_owner_neighbors_and_padding_boundary(self):
        original = (self.root / recovery.SOURCE).read_text()
        objects = []
        sources = [('before', original)] + [(name, original.replace(lifetime.base.ORIGINAL,
            self.bodies[name]).replace('#include <ultra64.h>\n',
            '#include <ultra64.h>\n' + lifetime.base.DECLARATIONS, 1)) for name in FORMS]
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
                if symbol == lifetime.base.FUNCTION:
                    continue
                prior = old[symbol]
                self.assertEqual((fn['size'], text[fn['value']:fn['value'] + fn['size']]),
                    (prior['size'], before[prior['value']:prior['value'] + prior['size']]), symbol)
                self.assertEqual({o - fn['value']: r for o, r in rel.items()
                    if fn['value'] <= o < fn['value'] + fn['size']},
                    {o - prior['value']: r for o, r in old_rel.items()
                    if prior['value'] <= o < prior['value'] + prior['size']}, symbol)
            self.assertEqual(recovery.normalized_pools(objects[0]), recovery.normalized_pools(obj))
            if name == 'selected-typed-1-1':
                with self.assertRaisesRegex(ValueError, 'patched func_1514803C .* retail'):
                    recovery.emit_padded_assembly(obj, self.root / 'conker/asm/175250.s',
                        word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_175250')
                accepted = False
            else:
                assembly = recovery.emit_padded_assembly(obj, self.root / 'conker/asm/175250.s',
                    word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_175250')
                self.assertTrue(assembly)
                accepted = True
            self.select(name)
            self.receipt('owner', dict(neighbors=len(current) - 1, diagnostics=0,
                unchanged_pools_and_relative_relocations=True, padder_accepts=accepted,
                byte_exact=False, production_installed=False))

    def test_08_nonlinear_float32_geometry_guest_and_native(self):
        memories = list(nonlinear_cases())
        arrays, invocations = [], []
        for case, memory in enumerate(memories):
            reference = recovery.CameraRibbonReference(memory).run()
            rows = []
            for address in range(recovery.VERTICES, reference.cursor, 16):
                values = [recovery.narrow(recovery.read(reference.memory, address + offset, 2), 16)
                    for offset in (0, 2, 4, 6, 8, 10)]
                values += [recovery.read(reference.memory, address + offset, 1) for offset in (12, 13, 14, 15)]
                rows.append('{%s}' % ','.join(map(str, values)))
            arrays.append('static const int expected%d[][10]={%s};\n' % (case, ','.join(rows)))
            invocation = 'initialize(3,3,0,4,%d,0,0,128);\n' % (case % 2)
            for index in range(4):
                for axis, field in enumerate('xyz'):
                    invocation += '*(u32 *)&records[%d].position.%s=0x%X;\n' % (
                        129 + index, field, recovery.read(memory, recovery.RECORDS + index * 20 + axis * 4))
            for axis in range(3):
                invocation += '*(u32 *)(origin+%d)=0x%X;\n' % (axis, recovery.read(memory, recovery.ORIGIN + axis * 4))
            invocation += '*(u32 *)payload=0x%X;\n' % recovery.read(memory, recovery.PAYLOAD)
            invocation += ('{int i;u8 *p=(u8 *)records;for(i=0;i<7720;i++)recordsBefore[i]=p[i];'
                'for(i=0;i<128;i++)payloadBefore[i]=payload[i];}\n')
            invocation += 'if(func_1514803C(actor,commands,0)!=commands+%d||error)return 1;\n' % (
                (reference.result - recovery.OUTPUT) // 8)
            invocation += 'if(check_vertices(expected%d,%d))return 2;\n' % (case, len(rows))
            for address in range(recovery.OUTPUT + 48, reference.result, 8):
                first, second = recovery.read(reference.memory, address), recovery.read(reference.memory, address + 4)
                expected = '(u32)((u8 *)vertices+%d)' % (second - recovery.VERTICES) if first == 0x01004008 else str(second)
                slot = (address - recovery.OUTPUT) // 8
                invocation += 'if(commands[%d].words.w0!=0x%X||commands[%d].words.w1!=%s)return 3;\n' % (
                    slot, first, slot, expected)
            invocation += 'if(check_commands_tail(48,%d)||!unchanged())return 4;\n' % (
                reference.result - recovery.OUTPUT)
            invocations.append(invocation)
        for name in FORMS:
            self.select(name)
            for memory in memories:
                self.compare(memory)
            self.fixture = (recovery.NATIVE_TYPES + 'float sqrtf(float);\n' + lifetime.base.DECLARATIONS
                + recovery.NATIVE_FIXTURE + '\n' + self.bodies[name] + '\n' + ''.join(arrays))
            self.run_host(''.join(invocations))
            self.receipt('nonlinear', dict(cases=len(memories), guest_executions=len(memories) * 2,
                actual_native32_cases=len(memories), seed='0x1514803C', full_vertex_command_bytes=True,
                finite_nontrapping_float32=True, native_aliases_mutations_invalid_casts=False))

    def test_09_unsafe_decompiler_capture_and_texture_narrowing_controls(self):
        body = self.bodies['selected-typed-1-1']
        captured = body.replace('        origin = func_15144B34(view);\n        records = actor->records;',
            '        records = actor->records;\n        origin = func_15144B34(view);')
        narrowed = body.replace('    s32 texture;', '    s16 texture;')
        early_head = body.replace('        previousIndex = actor->head - 1;\n', '').replace(
            '        output = func_15142FBC(', '        previousIndex = actor->head - 1;\n        output = func_15142FBC(')
        records = []
        for name, altered, mode in (('records-before-origin', captured, 2), ('narrow-texture', narrowed, 0),
                ('head-before-render', early_head, 7)):
            self.assertNotEqual(altered, body)
            meta, words = lifetime.base.compile_candidate(self.root, self.base, 'negative-' + name, altered)
            memory = recovery.fixture()
            reference = recovery.CameraRibbonReference(memory, mode=mode).run()
            model = recovery.CameraRibbonOracle(words, memory, mode=mode).run()
            self.assertNotEqual((external(model.memory), model.calls, model.r[2]),
                (external(reference.memory), reference.calls, reference.result))
            records.append(dict(meta, effective=True, mode=mode))
        (self.base / 'negatives.json').write_text(json.dumps(records, indent=2) + '\n')

    def test_10_complete_catalog_finite_controls_and_emitted_fingerprints(self):
        records, fingerprints = [], {}
        nonlinear = next(nonlinear_cases())
        for name, body in lifetime.candidates():
            meta, words = lifetime.base.compile_candidate(self.root, self.base / 'screen', name, body)
            for memory, mode in ((nonlinear, 0), (recovery.fixture(bank=1, pattern=1), 0),
                    (recovery.fixture(), 2)):
                self.compare(memory, words=words, mode=mode, write_order=False)
            fingerprint = hashlib.sha256(struct.pack('>%dI' % len(words), *words)).hexdigest()
            fingerprints.setdefault(fingerprint, []).append(name)
            records.append(dict(meta, words_sha256=fingerprint,
                source_sha256=hashlib.sha256(body.encode()).hexdigest()))
        (self.base / 'catalog.json').write_text(json.dumps(dict(forms=records,
            emitted_groups=list(fingerprints.values()), finite_samples_per_form=3,
            full_qualification_for_every_form=False, write_order_required=False), indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
