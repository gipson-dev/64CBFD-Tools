"""Whole owner point initializer frame/private-home fitting qualification."""
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_points_initializer_candidates as base
from tools.experiments import game_owner_points_initializer_fitting as fitting
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_owner_points_initializer_recovery as recovery


class GameOwnerPointsInitializerFittingTests(recovery.GameOwnerPointsInitializerRecoveryTests):
    @classmethod
    def setUpClass(cls):
        for name, value in (('RECOVERED', fitting.SELECTED), ('TYPES', fitting.TYPES)):
            handle = patch.object(base, name, value)
            handle.start()
            cls.addClassCleanup(handle.stop)
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-points-initializer-fitting-test'
        cls.meta, cls.words = base.compile_candidate(cls.root, cls.out, 'recovered')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>157I', cls.rom, base.ROM))
        cls.paths = dict(source=base.SOURCE, elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv')
        if not (cls.out / 'baseline.json').exists():
            hashes = {}
            for name, path in cls.paths.items():
                data = (cls.root / path).read_bytes()
                (cls.out / ('before-' + name)).write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
            (cls.out / 'baseline.json').write_text(json.dumps(hashes, indent=2) + '\n')
        cls.baseline = json.loads((cls.out / 'baseline.json').read_text())
        prior = cls.root / 'conker/build/game-owner-points-initializer-test/baseline.json'
        if prior.exists():
            assert cls.baseline == json.loads(prior.read_text())
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)

    def test_01_full_shape_profiles_source_forms_and_slot_gate(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences', 'pool_bytes')),
                         (157, 96, 137, 0))
        self.assertEqual(self.meta['diagnostics'], '')
        self.assertNotEqual(self.words, self.retail)
        self.assertEqual((-self.retail[0]) & 65535, 96)
        rows = []
        for profile in base.compiler.PROFILES:
            meta, words = base.compile_candidate(self.root, self.out, 'profile-' + profile, profile=profile)
            self.compare(recovery.fixture(), bodies=(self.retail, words))
            rows.append(meta)
        forms = []
        for name, body in fitting.candidates():
            meta, words = fitting.compile_candidate(self.root, self.out, name, body)
            failures = []
            for pattern, phase in itertools.product(range(4), (0, 8)):
                try:
                    self.compare(recovery.fixture(pattern), phase=phase, bodies=(self.retail, words))
                except AssertionError as error:
                    failures.append(str(error).splitlines()[0])
            forms.append(dict(meta, contract_cases=8, contract_failures=failures))
        self.assertTrue(all(not item['contract_failures'] for item in forms), forms)
        self.receipt('shape', dict(selected=self.meta, profiles=rows, forms=forms,
            frame_and_position_home_fit=True, original_saved_FP_home=True,
            installed=False, guards=0, real_word_differences=137))

    def test_03_independent_scales_aliases_and_effective_negatives(self):
        cases = 0
        for scales, pattern, phase in itertools.product(
                ((recovery.SCALE,) * 3, (recovery.bits(1.), recovery.bits(-1.), 0),
                 (1, 0x80000001, recovery.bits(2.)),
                 (recovery.bits(.25), recovery.bits(-.5), recovery.bits(4.))), range(4), (0, 8)):
            self.compare(recovery.fixture(pattern, scales=scales), phase=phase)
            cases += 1
        for actor, pattern in itertools.product(
                (0x800AA394 - 0x48, 0x800AA394 - 0x54, 0x800AA394 - 0x50), range(4)):
            self.compare(recovery.fixture(pattern, actor=actor), actor=actor)
            cases += 1
        negatives = (
            fitting.SELECTED.replace('owner->flags &= ~2;', 'owner->flags |= 2;'),
            fitting.SELECTED.replace('return 1;', 'return 0;'),
            fitting.SELECTED.replace('count = 10;', 'count = 6;'),
            fitting.SELECTED.replace('position.x += step.x;', 'position.x -= step.x;'),
            fitting.SELECTED.replace('step.z = delta.z * D_800AA39C;', 'step.z = delta.z * D_800AA394;'),
            fitting.SELECTED.replace('points[0].velocity.z = 0.0f;',
                                    'points[0].velocity.z = 1.0f;'),
        )
        for i, body in enumerate(negatives):
            self.assertNotEqual(body, fitting.SELECTED)
            _, words = fitting.compile_candidate(self.root, self.out, 'negative-%d' % i, body)
            with self.assertRaises(AssertionError):
                self.compare(recovery.fixture(scales=(recovery.bits(.25), recovery.bits(-.5), recovery.bits(2.))),
                             bodies=(words,))
        self.receipt('mutations', dict(cases=cases, executions=cases * 2,
            first_record_constant_aliases=True, effective_compiled_negatives=len(negatives)))

    def test_07_actual_owner_neighbors_padder_and_frame_rejection(self):
        before = (self.out / 'before-source').read_text()
        after = before.replace('/* Non-matching placeholders', fitting.TYPES.split('\n', 1)[1] +
            base.DECLARATIONS + '\n/* Non-matching placeholders', 1).replace(base.ORIGINAL, fitting.SELECTED)
        objects, warnings = [], []
        for name, body in (('owner-before', before), ('owner-after', after)):
            obj, diagnostics = compile_owner(self.root, self.out, body, name)
            subprocess.run(['python3', str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / (name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(obj.relative_to(self.root / 'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker',
                check=True, capture_output=True)
            objects.append(obj)
            warnings.append(diagnostics)
        self.assertEqual(warnings, [[], []])
        old, of, orels = parse_object(objects[0])
        new, nf, nrels = parse_object(objects[1])
        self.assertEqual(of.keys(), nf.keys())
        for name, function in nf.items():
            if name == base.FUNCTION:
                continue
            prior = of[name]
            self.assertEqual((function['size'], new[function['value']:function['value'] + function['size']]),
                (prior['size'], old[prior['value']:prior['value'] + prior['size']]), name)
            relative = lambda rels, f: {o - f['value']: r for o, r in rels.items()
                if f['value'] <= o < f['value'] + f['size']}
            self.assertEqual(relative(nrels, function), relative(orels, prior), name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        isolated, fs, _ = parse_object(self.out / 'recovered.o')
        target = nf[base.FUNCTION]
        self.assertEqual(target['size'], 628)
        self.assertEqual(new[target['value']:target['value'] + 628],
                         isolated[fs[base.FUNCTION]['value']:fs[base.FUNCTION]['value'] + 628])
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/1E0560.s',
            word_patches_path=self.root / self.paths['guards'], filename='generated_1E0560')
        emitted = assembly.split(base.FUNCTION + ':\n', 1)[1].split('.size ' + base.FUNCTION, 1)[0]
        emitted_words = [int(line.split()[1], 16) for line in emitted.splitlines() if line.startswith('.word')]
        # Compare raw words without relocations against the actual padded slot.
        raw_words = list(struct.unpack_from('>157I', new, target['value']))
        self.assertEqual(emitted_words, raw_words)
        self.assertNotIn('.space', emitted)
        (self.out / 'padded.s').write_text(assembly)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(self.out / 'padded.o'),
            str(self.out / 'padded.s')], check=True, capture_output=True)
        self.assertEqual(self.meta['frame'], 96)
        self.assertNotEqual(self.words, self.retail)
        self.receipt('owner', dict(neighbors=len(nf) - 1, existing_warnings=0, new_warnings=0,
            pools_and_relative_relocations_preserved=True, slot_and_frame_fit_actual_padder=True,
            raw_padder_unchanged_no_guards_or_padding=True, installation_rejected_words=True))

    def test_10_actual_private_frame_bytes_and_home_addresses(self):
        cases = 0
        for pattern, phase, scales in itertools.product(range(4), (0, 8),
                ((recovery.SCALE,) * 3, (recovery.bits(.25), recovery.bits(-.5), recovery.bits(2.)))):
            models = self.compare(recovery.fixture(pattern, scales=scales), phase=phase)
            self.assertEqual(models[0].memory, models[1].memory)
            frame = recovery.STACK + phase - 96
            for model in models:
                private_writes = [e for e in model.events if e[0] == 'W' and
                    recovery.STACK - 0x600 <= e[1] < recovery.STACK + 0x140]
                touched = set(a for _, address, size, _ in private_writes for a in range(address, address + size))
                self.assertEqual(touched, set(range(frame + 8, frame + 16)) | set(range(frame + 0x44, frame + 0x50)))
            cases += 1
        self.receipt('private', dict(cases=cases, executions=cases * 2, frame_bytes=96,
            position_home='SP+0x44', saved_FP_home='SP+0x08', entire_final_private_memory_equal=True,
            no_extra_private_writes=True, instruction_order_not_matching=True))

    def test_11_native_actor_layout_and_complete_static_offsets(self):
        self.fixture = '''
typedef unsigned int u32; typedef int s32; typedef unsigned char u8; typedef float f32;
''' + fitting.TYPES + '\n'
        self.run_host("""
if(sizeof(OwnerRibbonPosition32C8)!=12 || sizeof(OwnerPointRecord3A7C)!=24 ||
    sizeof(OwnerPoints3A7C)!=0x138) return 1;
if(__builtin_offsetof(OwnerPoints3A7C,flags)!=0x10 ||
    __builtin_offsetof(OwnerPoints3A7C,start)!=0x14 ||
    __builtin_offsetof(OwnerPoints3A7C,end)!=0x20 ||
    __builtin_offsetof(OwnerPoints3A7C,points)!=0x48) return 2;
""")
        self.receipt('layout', dict(actual_native32=True, actor_bytes=312, point_stride=24,
            flags=16, start=20, end=32, points=72, exact_public_layout=True))
