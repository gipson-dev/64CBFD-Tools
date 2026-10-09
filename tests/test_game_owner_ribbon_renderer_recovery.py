"""Full nine-quad recovery qualification; production installation remains byte gated."""
import hashlib
import itertools
import json
import math
import struct
import subprocess
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from tools.experiments import game_owner_ribbon_renderer_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_camera_ribbon_renderer_recovery import CameraRibbonOracle, trunc
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.test_game_record_ring_renderer_recovery import rounded, narrow, external, writes, NATIVE_TYPES
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests import test_game_random_curve_record as native

ACTOR, VIEWS, OTHER_VIEWS, VERTICES, OUTPUT = 0x20000, 0x80000, 0x90000, 0x60000, 0x70000
MATERIALS = (0x151B498C, 0x151B4A14)
VALUES = (0x220005, 0x40600, 255, 255, 255, 255, 255, 255, 255, 255, 0, 5, 0x2B)
COUNTS = dict(func_151D5D60=5, material=14, func_15142B7C=3,
    func_15142C10=6, func_15142CF0=8, func_1513F4E4=3, func_15142E24=11, func_15142FBC=4)


def fixture(flags=0, pattern=0, view=0, selector=0, alias=False, symbols=None):
    symbols = symbols or screen.SYMBOLS
    memory = {STACK + i: (i * 13 + 7) & 255 for i in range(-0x600, 0x140)}
    for base, length in ((ACTOR, 0x400), (VERTICES, 416), (OUTPUT, 320)):
        memory.update({base + i: (i * 17 + 0x35) & 255 for i in range(-16, length)})
    for index in range(10):
        point = ((index * 7.25 - 30., (index % 3) * -5.5 + 2.25, index * -4.75 + 20.),
                 (0., 0., 0.), (index * 2., 0., 0.),
                 (100.25 - index * 9., -99.75 + index * 3.25, index * 5.125))[pattern]
        for axis, value in enumerate(point):
            put(memory, ACTOR + 0x48 + index * 24 + axis * 4, bits(value))
    put(memory, ACTOR + 0x10, flags, 1)
    put(memory, ACTOR + 0x2E, selector, 1)
    put(memory, ACTOR + 0x30, bits(-5.5 if pattern == 3 else 5.5))
    put(memory, ACTOR + 0x13C, (0, 0x12345, 0x80000001, 0xFFFFFFFF)[pattern])
    for base in (VIEWS, OTHER_VIEWS):
        origin = (base + narrow(view, 16) * 0x9A0 + 0x2F8) & 0xFFFFFFFF
        for axis, value in enumerate((0., 0., 0.) if pattern == 2 else (7.25, -8.5, 9.75)):
            put(memory, origin + axis * 4, bits(value + (10. if base == OTHER_VIEWS else 0.)))
    put(memory, symbols['D_800DBFF0'], VIEWS)
    put(memory, symbols['D_800D2C9C'], 0x12340000)
    for index in range(512):
        put(memory, symbols['D_800A4AC8'] + index * 4, 0x81230000 + index * 19)
    for index, target in ((0, MATERIALS[0]), (1, MATERIALS[1]), (255, MATERIALS[1])):
        put(memory, symbols['D_8008FB10'] + index * 4, target)
    return memory, ACTOR + 0x13C if alias else VERTICES


def mutations(name, mode):
    choices = {
        1: ('func_151D5D60', [(screen.SYMBOLS['D_800DBFF0'], OTHER_VIEWS, 4),
                             (ACTOR + 0x2E, 1, 1)]),
        2: ('material', [(screen.SYMBOLS['D_800DBFF0'], OTHER_VIEWS, 4),
                         (ACTOR + 0x10, 14, 1)]),
        3: ('func_15142B7C', [(ACTOR + 0x48, bits(25.5), 4)]),
        4: ('func_1513F4E4', [(screen.SYMBOLS['D_800D2C9C'], 0xFF001100, 4),
                            (screen.SYMBOLS['D_800A4AC8'] + 40, 0x66778899, 4)]),
        5: ('func_15142FBC', [(ACTOR + 0x30, bits(-7.), 4),
                             (ACTOR + 0x13C, 0x80001234, 4),
                             (ACTOR + 0x60, bits(-19.5), 4)]),
    }
    target, values = choices.get(mode, ('', []))
    return values if target == name else []


class RibbonOracle(CameraRibbonOracle):
    def __init__(self, words, memory, view=0, success=True, material=True, mode=0, phase=0,
                 vertex=VERTICES, entry=screen.ENTRY, connected=None, symbols=None, values=VALUES):
        AreaOracle.__init__(self, words, memory, (OUTPUT, ACTOR, view), phase=phase,
                            entry=entry, connected=connected)
        self.targets = {a: n for n, a in (symbols or screen.SYMBOLS).items() if n in COUNTS}
        self.targets.update({a: 'material' for a in MATERIALS})
        self.success, self.material, self.mode, self.vertex = success, material, mode, vertex
        self.values = values
        self.arguments_by_call, self.forwarded = [], []
        self.symbols = symbols or screen.SYMBOLS

    def get(self, address, size):
        if any((address + i) & 0xFFFFFFFF not in self.memory for i in range(size)):
            raise KeyError(('read', address, size))
        return super().get(address, size)

    def put(self, address, value, size):
        if self.recording and any((address + i) & 0xFFFFFFFF not in self.memory for i in range(size)):
            raise KeyError(('write', address, size))
        super().put(address, value, size)

    def record_call(self, target):
        if target == screen.ENTRY:
            self.forwarded = self.arguments(3)
            return
        name = self.targets[target]
        args = list(self.arguments(COUNTS[name]))
        self.arguments_by_call.append((name, tuple(args)))
        if name == 'func_151D5D60':
            args[3] = 'cursor'
        elif name == 'material':
            args[1:] = ['out' + str(i) for i in range(13)]
        elif name != 'func_15142B7C':
            index = 9 if name == 'func_15142E24' else len(args) - 1
            assert self.get(args[index], 1) == (1 if name == 'func_15142C10' else 0)
            args[index] = 'sync'
        self.calls.append((name, tuple(args)))

    def hook(self, target):
        name, args = self.arguments_by_call[-1]
        result = 0
        if name == 'func_151D5D60':
            self.put(args[3], self.vertex if self.success else 0, 4)
        elif name == 'material':
            for i, (address, value) in enumerate(zip(args[1:], self.values)):
                self.put(address, value, 4 if i < 11 else 1)
            result = int(self.material)
        else:
            self.put(args[0], 0xAA000000 | len(self.calls), 4)
            self.put(args[0] + 4, len(self.calls), 4)
            result = args[0] + 8
            if name != 'func_15142B7C':
                self.put(args[9] if name == 'func_15142E24' else args[-1], 0, 1)
        for address, value, width in mutations(name, self.mode):
            self.put(address, value, width)
        for offset in range(0, 56, 4):
            self.put(self.r[29] + offset, 0xCD000000 + offset, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]
        self.r[2] = result


class RibbonReference:
    def __init__(self, memory, view=0, success=True, material=True, mode=0,
                 vertex=VERTICES, symbols=None, values=VALUES):
        self.memory = memory.copy()
        self.view = narrow(view, 16)
        self.success, self.material, self.mode, self.vertex = success, material, mode, vertex
        self.symbols = symbols or screen.SYMBOLS
        self.values = values
        self.calls, self.events, self.result = [], [], OUTPUT

    def get(self, address, size=4):
        return read(self.memory, address & 0xFFFFFFFF, size)

    def store(self, address, value, size=4):
        address &= 0xFFFFFFFF
        if any((address + i) & 0xFFFFFFFF not in self.memory for i in range(size)):
            raise KeyError(('write', address, size))
        put(self.memory, address, value, size)
        self.events.append(('W', address, size, value & ((1 << (size * 8)) - 1)))

    def call(self, name, *args):
        self.calls.append((name, tuple(a & 0xFFFFFFFF if isinstance(a, int) else a for a in args)))
        if name not in ('func_151D5D60', 'material'):
            self.store(self.result, 0xAA000000 | len(self.calls))
            self.store(self.result + 4, len(self.calls))
            self.result += 8
        for address, value, width in mutations(name, self.mode):
            self.store(address, value, width)

    def point(self, address):
        return [floating(self.get(address + axis * 4)) for axis in range(3)]

    def offset(self, first, second, point, origin):
        tangent = [rounded(b - a) for a, b in zip(first, second)]
        ray = [rounded(v - floating(self.get(origin + axis * 4))) for axis, v in enumerate(point)]
        cross = [rounded(rounded(tangent[1] * ray[2]) - rounded(ray[1] * tangent[2])),
                 rounded(rounded(tangent[2] * ray[0]) - rounded(ray[2] * tangent[0])),
                 rounded(rounded(tangent[0] * ray[1]) - rounded(ray[0] * tangent[1]))]
        squares = [rounded(v * v) for v in cross]
        magnitude2 = rounded(rounded(squares[0] + squares[1]) + squares[2])
        if magnitude2 == 0.:
            return [0., 0., 0.]
        factor = rounded(floating(self.get(ACTOR + 0x30)) / rounded(math.sqrt(magnitude2)))
        return [rounded(v * factor) for v in cross]

    def pair(self, cursor, point, offset, texture):
        for sign, s in ((1, 0), (-1, 0x3C0)):
            for axis in range(3):
                value = rounded(point[axis] + offset[axis]) if sign == 1 else rounded(point[axis] - offset[axis])
                self.store(cursor + axis * 2, trunc(value), 2)
            self.store(cursor + 8, s, 2)
            self.store(cursor + 10, texture, 2)
            for index, value in enumerate((255, 100, 100, 255)):
                self.store(cursor + 12 + index, value, 1)
            cursor += 16
        return cursor

    def run(self):
        if self.get(ACTOR + 0x10, 1) & 14:
            return self
        self.call('func_151D5D60', ACTOR + 0x140, self.view, 0x190, 'cursor', 0)
        if not self.success:
            return self
        origin = (self.get(self.symbols['D_800DBFF0']) + self.view * 0x9A0 + 0x2F8) & 0xFFFFFFFF
        # The unsigned selector is read after resource setup; every callback receives 13 outputs.
        self.get(self.symbols['D_8008FB10'] + self.get(ACTOR + 0x2E, 1) * 4)
        self.call('material', ACTOR, *['out' + str(i) for i in range(13)])
        if not self.material:
            return self
        m1, m2, er, eg, eb, alpha, pr, pg, pb, pa, render, bank, combine = self.values
        self.call('func_15142B7C', self.result, m1, m2)
        self.call('func_15142C10', self.result, pr, pg, pb, pa, 'sync')
        self.call('func_15142CF0', self.result, 0, 0, er, eg, eb, alpha, 'sync')
        self.call('func_1513F4E4', self.result, combine, 'sync')
        self.call('func_15142E24', self.result, self.symbols['D_80090DE8'], 0, 0, 0, 0, 54, 0, 0, 'sync', 3)
        mode = render | 0x80000 | self.get(self.symbols['D_800D2C9C']) | 0x2CA0
        flags = self.get(self.symbols['D_800A4AC8'] + bank * 8 + 4) | self.get(self.symbols['D_800A4AC8'] + bank * 8)
        self.call('func_15142FBC', self.result, mode, flags, 'sync')
        first, second = self.point(ACTOR + 0x48), self.point(ACTOR + 0x60)
        cursor = self.pair(self.vertex, first, self.offset(first, second, first, origin), 0)
        texture = self.get(ACTOR + 0x13C)
        for segment in range(1, 10):
            first = self.point(ACTOR + 0x48 + (segment - 1) * 24)
            second = self.point(ACTOR + 0x48 + segment * 24)
            cursor = self.pair(cursor, second, self.offset(first, second, second, origin), texture)
            texture = (texture + self.get(ACTOR + 0x13C)) & 0xFFFFFFFF
            for word, value in ((0x01004008, cursor - 64), (0x05000204, 0), (0x05020604, 0)):
                self.store(self.result, word)
                self.store(self.result + 4, value)
                self.result += 8
        return self


class GameOwnerRibbonRendererRecoveryTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-owner-ribbon-renderer-test'
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>475I', cls.rom, screen.ROM))
        cls.paths = (screen.SOURCE, 'conker/build/conker.us.elf',
                     'conker/retail_word_patches.us.csv', 'conker/progress.csv')
        cls.baseline = {p: hashlib.sha256((cls.root / p).read_bytes()).hexdigest() for p in cls.paths}
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path = Path(directory.name)

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, view=0, success=True, material=True, mode=0, phase=0,
                vertex=VERTICES, bodies=None, symbols=None, entry=screen.ENTRY, values=VALUES):
        reference = RibbonReference(memory, view, success, material, mode, vertex, symbols, values).run()
        models = [RibbonOracle(body, memory, view, success, material, mode, phase, vertex,
                               entry, symbols=symbols, values=values).run()
                  for body in (bodies or (self.retail, self.words))]
        for model in models:
            self.assertEqual(model.r[2], reference.result)
            self.assertEqual(model.calls, reference.calls)
            self.assertEqual(external(model.memory), external(reference.memory))
            self.assertEqual(writes(model), reference.events)
        return reference, models

    def test_01_complete_profiles_and_reject_installation(self):
        rows = []
        for name, body in screen.candidates():
            for profile in screen.compiler.PROFILES if name == 'selected' else ('o2g3',):
                meta, words = screen.compile_candidate(self.root, self.out, name + '-' + profile, body, profile)
                self.assertEqual(meta['diagnostics'], '')
                self.assertEqual(meta['pool_bytes'], 0)
                self.assertNotEqual(words, self.retail)
                rows.append(meta)
        self.assertEqual(tuple(self.meta[k] for k in ('body_words', 'frame', 'differences')), (477, 304, 432))
        self.receipt('shape', dict(measurements=rows, no_installation_authorized=True,
                                  target_words=475, target_frame=328, guards=0))

    def test_02_full_guest_strip_lazy_exits_aliases_and_coverage(self):
        coverage = [set(), set()]
        cases = 0
        for flags, pattern, success, material, phase, alias in itertools.product(
                (0, 1, 2, 4, 8, 14, 0x80, 0xFF), range(4), (False, True),
                (False, True), (0, 8), (False, True)):
            memory, vertex = fixture(flags, pattern, alias=alias)
            _, models = self.compare(memory, success=success, material=material, phase=phase, vertex=vertex)
            for hits, model in zip(coverage, models):
                hits.update(model.visits)
            cases += 1
        self.assertEqual(coverage[0], set(range(screen.ENTRY, screen.ENTRY + 1900, 4)))
        self.assertEqual(cases, 512)
        self.receipt('guest', dict(cases=cases, executions=cases * 2, retail_words_reached=475,
            independent_public_memory_and_write_trace_equal=True, private_read_trace_not_matching=True,
            strip_vertices=20, strip_quads=9, own_commands=27, untouched_vertex_flag_bytes=40,
            alias_texture_step_receipts=True, hostile_volatile_and_outgoing_home_clobbers=True))

    def test_03_mutation_signed_views_and_callback_output_widths(self):
        cases = 0
        for view, mode, phase, selector, alias in itertools.product(
                (0xFFFF, 0x8000, 0x7FFF, 0x12340002), range(6), (0, 8), (0, 255), (False, True)):
            memory, vertex = fixture(view=view, selector=selector, alias=alias)
            self.compare(memory, view, mode=mode, phase=phase, vertex=vertex)
            cases += 1
        values = (0x87654321, 0x80000000, -1, -32768, 32767, 0xFFFFFFFF, 0x80000000,
                  0x12345678, -255, 257, 0xAA551100, 255, 255)
        memory, vertex = fixture()
        self.compare(memory, values=values)
        self.receipt('mutations', dict(cases=cases + 1, executions=(cases + 1) * 2,
            retained_origin_after_material_callback=True, fresh_points_width_step_and_flags=True,
            signed16_view_boundaries=True, full_word_material_values_and_byte_bank_combine=True))

    def test_04_effective_compiled_semantic_negatives(self):
        controls = {
            'wrong-triangle': screen.SELECTED.replace('1, 3, 2, 0', '0, 2, 3, 0'),
            'zero-holes': screen.SELECTED.replace('cursor++;', 'cursor->v.flag = 0; cursor++;'),
            'wrong-UV': screen.SELECTED.replace('0x3C0', '0x4000'),
            'wrong-loop': screen.SELECTED.replace('offset != 0xF0', 'offset != 0xD8'),
            'late-origin': screen.SELECTED.replace('    first = *(OwnerRibbonPosition32C8 *)(actor + 0x48);',
                '    origin = (OwnerRibbonPosition32C8 *)(D_800DBFF0 + view * 0x9A0 + 0x2F8);\n'
                '    first = *(OwnerRibbonPosition32C8 *)(actor + 0x48);'),
            'cached-step': screen.SELECTED.replace('textureT += *(s32 *)(actor + 0x13C);',
                'textureT += initialStep;').replace('u32 textureT;', 'u32 textureT, initialStep;').replace(
                'textureT = *(s32 *)(actor + 0x13C);', 'textureT = *(s32 *)(actor + 0x13C); initialStep = textureT;'),
        }
        rows = []
        for name, body in controls.items():
            meta, words = screen.compile_candidate(self.root, self.out, name, body)
            memory, vertex = fixture(pattern=1 if name == 'cached-step' else 0)
            if name == 'cached-step':
                vertex = ACTOR + 0x11C
                for axis in range(3):
                    put(memory, VIEWS + 0x2F8 + axis * 4, bits(0.))
            mode = 2 if name == 'late-origin' else 0
            ref = RibbonReference(memory, mode=mode, vertex=vertex).run()
            model = RibbonOracle(words, memory, mode=mode, vertex=vertex).run()
            self.assertTrue((external(model.memory), model.r[2]) !=
                            (external(ref.memory), ref.result), name)
            rows.append(meta)
        self.receipt('negatives', dict(complete_controls=len(rows), detected=len(rows), rows=rows))

    def test_05_actual_owner_neighbors_and_padder_rejection(self):
        before = (self.root / screen.SOURCE).read_text()
        after = before.replace('/* Non-matching placeholders', screen.TYPES + screen.DECLARATIONS +
            '\n/* Non-matching placeholders', 1).replace(screen.ORIGINAL, screen.SELECTED)
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
        self.assertEqual(warnings[0], warnings[1])
        old, of, orels = parse_object(objects[0])
        new, nf, nrels = parse_object(objects[1])
        self.assertEqual(of.keys(), nf.keys())
        for name, f in nf.items():
            if name == screen.FUNCTION:
                continue
            prior = of[name]
            self.assertEqual((f['size'], new[f['value']:f['value'] + f['size']]),
                (prior['size'], old[prior['value']:prior['value'] + prior['size']]), name)
            relative = lambda rs, ff: {o - ff['value']: r for o, r in rs.items()
                                     if ff['value'] <= o < ff['value'] + ff['size']}
            self.assertEqual(relative(nrels, f), relative(orels, prior), name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        isolated, fs, _ = parse_object(self.out / 'selected.o')
        self.assertEqual(new[nf[screen.FUNCTION]['value']:nf[screen.FUNCTION]['value'] + nf[screen.FUNCTION]['size']],
            isolated[fs[screen.FUNCTION]['value']:fs[screen.FUNCTION]['value'] + fs[screen.FUNCTION]['size']])
        with self.assertRaises(ValueError):
            emit_padded_assembly(objects[1], self.root / 'conker/asm/1E0560.s',
                word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_1E0560')
        self.receipt('owner', dict(neighbors=len(nf) - 1, existing_warnings=len(warnings[0]),
            new_warnings=0, pools_and_relative_relocations_preserved=True,
            oversized_actual_padder_rejected=True, not_installed=True))

    def test_06_production_unchanged_protected_data_and_registered_pointer(self):
        self.assertIn(screen.ORIGINAL, (self.root / screen.SOURCE).read_text())
        after = {p: hashlib.sha256((self.root / p).read_bytes()).hexdigest() for p in self.paths}
        self.assertEqual(after, self.baseline)
        elf = sections(self.root / 'conker/build/conker.us.elf')
        start, data = elf['.game_data']
        self.assertEqual(struct.unpack_from('>I', data, 0x8008BF0C - start)[0], screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', self.rom, 0x2309CC)[0], screen.ENTRY)
        self.assertEqual(struct.unpack_from('>2I', self.rom, 0x2345D0), MATERIALS)
        audit = audit_layout(self.root / 'conker/build/conker.us.elf', self.root / 'conker')
        self.assertTrue(audit['exact'], audit)
        self.receipt('unchanged', dict(hashes=after, protected_data=audit,
            registered_pointer='0x8008BF0C', production_placeholder_unchanged=True,
            no_matching_or_conversion_credit=True))

    def test_07_independent_original_relocations_and_semantic_rebases(self):
        owner = (self.root / 'conker/asm/1E0560.s').read_text()
        begin, end = 'glabel ' + screen.FUNCTION, 'endlabel ' + screen.FUNCTION
        original = begin + owner.split(begin, 1)[1].split(end, 1)[0] + end + '\n'
        source, obj = self.out / 'original.s', self.out / 'original.o'
        source.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n' + original)
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(source)],
                       cwd=self.root, check=True, capture_output=True)
        uses = lambda p: Counter(u for group in parse_object(p)[2].values() for u in group)
        self.assertEqual(uses(obj), uses(self.out / 'selected.o'))
        cases = 0
        for index, entry in enumerate((screen.ENTRY, 0x10008000, 0x80007FFC, 0x8FFF8000)):
            symbols = screen.SYMBOLS if index == 0 else {
                n: (entry & 0xF0000000) + 0x180008 + i * 0x10000 for i, n in enumerate(screen.SYMBOLS)}
            script = self.out / ('rebase-%d.ld' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            bodies = []
            for name, path, count in (('original', obj, 475), ('candidate', self.out / 'selected.o', len(self.words))):
                elf = self.out / ('rebase-%d-%s.elf' % (index, name))
                subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                    *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(path)],
                    check=True, capture_output=True)
                bodies.append(list(struct.unpack_from('>%dI' % count, sections(elf)['.text'][1])))
            if index == 0:
                self.assertEqual(bodies[0], self.retail)
                self.assertEqual(bodies[1], self.words)
            for view, pattern, phase in itertools.product((0, 0xFFFF), range(4), (0, 8)):
                memory, vertex = fixture(view=view, pattern=pattern, symbols=symbols)
                self.compare(memory, view, phase=phase, vertex=vertex, bodies=bodies, symbols=symbols, entry=entry)
                cases += 1
        self.receipt('rebases', dict(symbol_sets=4, independent_links=8, cases=cases, executions=cases * 2,
                                    relocation_uses=sum(uses(obj).values()), no_byte_matching_claim=True))

    def test_08_actual_complete_registered_material_callback(self):
        callback = list(struct.unpack_from('>34I', self.rom, 0x1E1E3C))
        start, game = sections(self.root / 'conker/build/conker.us.elf')['.game']
        self.assertEqual(list(struct.unpack_from('>34I', game, MATERIALS[0] - start)), callback)
        cases = 0
        for view, pattern, phase, alias in itertools.product((0, 0xFFFF), range(4), (0, 8), (False, True)):
            memory, vertex = fixture(view=view, pattern=pattern, alias=alias)
            ref = RibbonReference(memory, view, vertex=vertex).run()
            for body in (self.retail, self.words):
                connected = dict(zip(range(MATERIALS[0], MATERIALS[0] + 136, 4), callback))
                model = RibbonOracle(body, memory, view, phase=phase, vertex=vertex, connected=connected).run()
                self.assertEqual(model.calls, ref.calls)
                self.assertEqual(model.r[2], ref.result)
                self.assertEqual(external(model.memory), external(ref.memory))
                self.assertEqual(writes(model), ref.events)
                self.assertTrue(set(range(MATERIALS[0], MATERIALS[0] + 136, 4)) <= model.visits)
            cases += 1
        self.receipt('material', dict(cases=cases, executions=cases * 2, all_registered_helper_words=34,
                                    production_helper_exact=True, second_callback_body_still_open=True))

    def test_09_lazy_reads_and_fault_prefixes(self):
        cases = 0
        memory, vertex = fixture()
        for address in (ACTOR + 0x10, ACTOR + 0x2E, screen.SYMBOLS['D_800DBFF0'],
                screen.SYMBOLS['D_8008FB10'], screen.SYMBOLS['D_800D2C9C'], ACTOR + 0x48,
                ACTOR + 0x60, ACTOR + 0x30, ACTOR + 0x13C, VIEWS + 0x2F8, VERTICES, OUTPUT + 48):
            broken = memory.copy()
            del broken[address]
            ref = RibbonReference(broken)
            with self.assertRaises(KeyError):
                ref.run()
            for body in (self.retail, self.words):
                model = RibbonOracle(body, broken)
                with self.assertRaises(KeyError):
                    model.run()
                self.assertEqual(model.calls, ref.calls)
                self.assertEqual(external(model.memory), external(ref.memory))
                self.assertEqual(writes(model), ref.events)
            cases += 1
        for flags, success, material in ((4, True, True), (0, False, True), (0, True, False)):
            broken, vertex = fixture(flags)
            for address in (ACTOR + 0x48, ACTOR + 0x60, ACTOR + 0x30, ACTOR + 0x13C, VIEWS + 0x2F8):
                del broken[address]
            self.compare(broken, success=success, material=material)
        self.receipt('faults', dict(cases=cases, executions=cases * 2, lazy_cases=3,
                                    public_write_and_call_prefixes_equal=True, portable_C_fault_claim=False))

    def test_10_native32_actual_full_C_strip_and_ABI(self):
        self.fixture = NATIVE_TYPES + screen.TYPES + screen.DECLARATIONS + NATIVE_FIXTURE + '\n' + screen.SELECTED + '\n'
        self.run_host(r"""
static int flagValues[]={0,1,2,4,8,14,0x80,0xFF};
int flag,pat,ok,mat,mode,view,alias,result;
for(flag=0;flag<8;flag++)for(pat=0;pat<4;pat++)for(ok=0;ok<2;ok++)for(mat=0;mat<2;mat++)
for(mode=0;mode<6;mode++)for(view=-2;view<=2;view++)for(alias=0;alias<2;alias++){
 result=one(flagValues[flag],pat,ok,mat,mode,view,alias);if(result)return result;
}
""")
        self.receipt('native', dict(cases=7680, actual_complete_C=True, pointer_bits=32,
            independent_full_actor_and_vertex_and_command_bytes=True, untouched_flag_bytes=True,
            ABI_mutations_signed_views_alias_and_texture_wrap=True, finite_binary32_only=True))


    def test_11_complete_original_registered_graphics_walker(self):
        walker = list(struct.unpack_from('>348I', self.rom, 0x1949A8))
        cases = 0

        class WalkerOracle(RibbonOracle):
            def record_call(self, target):
                if target == 0x15168F84:
                    self.range_arguments = self.arguments(3)
                    return
                super().record_call(target)

            def hook(self, target):
                if target != 0x15168F84:
                    return super().hook(target)
                selector, begin, end = self.range_arguments
                assert selector == 0
                self.put(begin, 0x33, 4)
                self.put(end, 0x34, 4)
                for register in (1, 2, 3, *range(4, 16), 24, 25):
                    self.r[register] = 0xA5000000 + register

        for view, phase, row, present, budget_mode in itertools.product(
                (0, 0xFFFF), (0, 8), (0, 1), (False, True), (0, 1)):
            memory, vertex = fixture(view=view)
            for base, size in ((0x8008B4A8, 0x1500), (0x800DCE50, 0x340),
                    (0x800DD198, 64), (0x800DD1B0, 0x90), (0x8003C8E0, 4),
                    (0x800D2DAB, 1), (0x800BE9C8, 16), (0x800BEBA4, 4)):
                memory.update({base + i: 0 for i in range(size)})
            memory[0x800DD190] = 2
            memory[0x800BE9C0] = 0
            put(memory, 0x800BE9C8, OUTPUT)
            put(memory, 0x800BEBA4, 10000)
            put(memory, 0x8008BF0C, screen.ENTRY)
            put(memory, 0x8008BF04 + 0x30, budget_mode, 1)
            put(memory, 0x800DCE50 + row * 0x1A0 + 0x33 * 4, ACTOR if present else 0)
            put(memory, ACTOR + 8, 0)
            memory.update({OUTPUT + i: (i * 17 + 0x35) & 255 for i in range(1024)})
            expected = RibbonReference(memory, view, vertex=vertex)
            expected.result = OUTPUT + 16
            if present:
                expected.run()
            expected_memory = expected.memory
            put(expected_memory, OUTPUT, 0xDA380003)
            put(expected_memory, OUTPUT + 4, 0x80089470)
            final = expected.result if present else OUTPUT + 8
            if present:
                put(expected_memory, OUTPUT + 8, 0xD9FDFFFF)
                put(expected_memory, OUTPUT + 12, 0)
            put(expected_memory, final, 0xD9FFFFFF)
            put(expected_memory, final + 4, 1)
            models = []
            for body in (self.retail, self.words):
                connected = dict(zip(range(screen.ENTRY, screen.ENTRY + len(body) * 4, 4), body))
                model = WalkerOracle(walker, memory, view, phase=phase, vertex=vertex,
                                     entry=0x151674F8, connected=connected)
                model.r[5] = model.before[5] = 0
                model.r[7] = model.before[7] = row
                model.run()
                self.assertEqual(model.r[2], final + 8)
                self.assertEqual(model.calls, expected.calls if present else [])
                if present:
                    self.assertEqual(model.forwarded, (OUTPUT + 16, ACTOR, narrow(view, 16) & 0xFFFFFFFF))
                else:
                    self.assertEqual(model.forwarded, [])
                for base, size in ((ACTOR, 0x400), (VERTICES, 416), (OUTPUT, 1024)):
                    self.assertEqual(bytes(model.memory[base + i] for i in range(size)),
                                     bytes(expected_memory[base + i] for i in range(size)))
                self.assertEqual(model.memory[0x800DD190], 2)
                self.assertEqual(read(model.memory, 0x800DD198 + 12), 0)
                models.append(model)
            self.assertEqual(external(models[0].memory), external(models[1].memory))
            self.assertEqual(writes(models[0]), writes(models[1]))
            cases += 1
        self.receipt('walker', dict(cases=cases, executions=cases * 2, original_words=348,
            registered_table_pointer_used=True, signed_view_and_returned_cursor=True,
            both_rows_empty_present_and_budget_modes=True, nesting_restored=True,
            range_selector_hook_bounded=True, full_production_walker_recovery_not_claimed=True))

NATIVE_FIXTURE = r'''
u8 *D_800DBFF0; u8 D_80090DE8[16]; u32 D_800D2C9C,D_800A4AC8[512];
Gfx *func_151B32C8(Gfx *,u8 *,s16);
static union {u32 a;u8 b[1024];} actor,wantedActor;
static union {u32 a;u8 b[5*0x9A0+0x310];} views,otherViews;
static Vtx vertices[26],wantedVertices[26]; static Gfx commands[40],wantedCommands[40];
static int error,used,mode,success,materialOK,alias,pattern;static s16 expectedView;
static u8 *expectedOrigin;
f32 sqrtf(f32 value){f32 result;__asm__("sqrtss %1,%0":"=x"(result):"x"(value));return result;}
static f32 plus(f32 a,f32 b){volatile f32 v=a+b;return v;}
static f32 minus(f32 a,f32 b){volatile f32 v=a-b;return v;}
static f32 times(f32 a,f32 b){volatile f32 v=a*b;return v;}
static f32 divide(f32 a,f32 b){volatile f32 v=a/b;return v;}
static void effect(u8 *p,int id){
 if(mode==1 && id==0){p[0x2E]=1;}
 if(mode==2 && id==1){p[0x10]=14;}
 if(mode==3 && id==2){*(f32 *)(p+0x48)=25.5f;}
 if(mode==5 && id==7){*(f32 *)(p+0x30)=-7.0f;*(u32 *)(p+0x13C)=0x80001234;*(f32 *)(p+0x60)=-19.5f;}
}
static void mutation(int id){
 effect(actor.b,id);effect(wantedActor.b,id);
 if((mode==1 && id==0) || (mode==2 && id==1))D_800DBFF0=otherViews.b+2*0x9A0;
 if(mode==4 && id==5){D_800D2C9C=0xFF001100;D_800A4AC8[10]=0x66778899;}
}
void func_151D5D60(void *p,s16 view,s32 size,Vtx **out,u8 *fresh){
 if(used++ || p!=actor.b+0x140 || view!=expectedView || size!=0x190 || fresh)error=1;
 *out=success?(alias?(Vtx *)(actor.b+0x13C):vertices):NULL;mutation(0);
 expectedOrigin=D_800DBFF0+expectedView*0x9A0+0x2F8;
}
static s32 mat(u8 *a,s32 *v0,s32 *v1,s32 *v2,s32 *v3,s32 *v4,s32 *v5,
 s32 *v6,s32 *v7,s32 *v8,s32 *v9,s32 *v10,u8 *bank,u8 *combine){
 if(used++!=1 || a!=actor.b)error=2;
 *v0=0x220005;*v1=0x40600;*v2=*v3=*v4=*v5=*v6=*v7=*v8=*v9=255;*v10=0;
 *bank=5;*combine=0x2B;mutation(1);return materialOK;
}
s32 (*D_8008FB10[])(u8 *,s32 *,s32 *,s32 *,s32 *,s32 *,s32 *,s32 *,s32 *,
 s32 *,s32 *,s32 *,u8 *,u8 *)={mat,mat};
static Gfx *step(Gfx *g,int id,u8 *sync){
 if(used!=id || g!=commands+id-2)error=3;
 if(sync){if(*sync!=(id==3?1:0))error=4;*sync=0;}
 g->words.w0=wantedCommands[id-2].words.w0=0xAA000000|(id+1);
 g->words.w1=wantedCommands[id-2].words.w1=id+1;
 mutation(used++);return g+1;
}
Gfx *func_15142B7C(Gfx *g,u32 a,u32 b){
 if(a!=0x220005 || b!=0x40600){error=5;}return step(g,2,NULL);
}
Gfx *func_15142C10(Gfx *g,s32 r,s32 gg,s32 b,s32 a,u8 *sync){
 if(r!=255 || gg!=255 || b!=255 || a!=255){error=6;}return step(g,3,sync);
}
Gfx *func_15142CF0(Gfx *g,s32 a,s32 b,s32 r,s32 gg,s32 bb,s32 alpha,u8 *sync){
 if(a || b || r!=255 || gg!=255 || bb!=255 || alpha!=255){error=7;}return step(g,4,sync);
}
Gfx *func_1513F4E4(Gfx *g,u8 k,u8 *sync){
 if(k!=0x2B){error=8;}return step(g,5,sync);
}
Gfx *func_15142E24(Gfx *g,void *tex,s32 a,s32 b,s32 c,s32 d,s32 n,u8 f,u8 *zero,u8 *sync,s32 k){
 if(tex!=D_80090DE8 || a || b || c || d || n!=54 || f || zero || k!=3)error=9;
 return step(g,6,sync);
}
Gfx *func_15142FBC(Gfx *g,u32 a,u32 b,u8 *sync){
 if(a!=(D_800D2C9C|0x80000|0x2CA0) || b!=(D_800A4AC8[11]|D_800A4AC8[10]))error=10;
 return step(g,7,sync);
}
static void normal(f32 *first,f32 *second,f32 *point,f32 *out){
 f32 t[3],ray[3],cross[3],squares[3],length,scale;int i;
 for(i=0;i<3;i++){t[i]=minus(second[i],first[i]);ray[i]=minus(point[i],((f32 *)expectedOrigin)[i]);}
 cross[0]=minus(times(t[1],ray[2]),times(ray[1],t[2]));
 cross[1]=minus(times(t[2],ray[0]),times(ray[2],t[0]));
 cross[2]=minus(times(t[0],ray[1]),times(ray[0],t[1]));
 for(i=0;i<3;i++)squares[i]=times(cross[i],cross[i]);
 length=plus(plus(squares[0],squares[1]),squares[2]);
 if(length==0){for(i=0;i<3;i++)out[i]=0;}
 else{scale=divide(*(f32 *)(wantedActor.b+0x30),sqrtf(length));for(i=0;i<3;i++)out[i]=times(cross[i],scale);}
}
static Vtx *pair(Vtx *v,f32 *point,f32 *offset,u32 texture){
 int i,j;
 for(j=0;j<2;j++){
  for(i=0;i<3;i++)v->v.ob[i]=(s32)(j?minus(point[i],offset[i]):plus(point[i],offset[i]));
  v->v.tc[0]=j?0x3C0:0;v->v.tc[1]=texture;
  v->v.cn[0]=255;v->v.cn[1]=100;v->v.cn[2]=100;v->v.cn[3]=255;v++;
 }
 return v;
}
static int one(int flags,int pat,int ok,int matOK,int mutationMode,s16 view,int va){
 int i,j,segment;Gfx *result,*g;Vtx *v;f32 first[3],second[3],offset[3];u32 texture;
 mode=mutationMode;success=ok;materialOK=matOK;expectedView=view;alias=va;pattern=pat;
 error=used=0;D_800DBFF0=views.b+2*0x9A0;D_800D2C9C=0x12340000;
 for(i=0;i<512;i++)D_800A4AC8[i]=0x81230000+i*19;
 for(i=0;i<1024;i++)actor.b[i]=(u8)(i*17+0x35);
 for(i=0;i<(int)sizeof(vertices);i++)((u8 *)vertices)[i]=(u8)(i*17+0x35);
 for(i=0;i<(int)sizeof(commands);i++)((u8 *)commands)[i]=(u8)(i*17+0x35);
 actor.b[0x10]=flags;actor.b[0x2E]=0;
 *(f32 *)(actor.b+0x30)=pat==3?-5.5f:5.5f;
 *(u32 *)(actor.b+0x13C)=(u32[]){0,0x12345,0x80000001,0xFFFFFFFF}[pat];
 for(j=0;j<10;j++){
  f32 p[3]={j*7.25f-30.0f,(j%3)*-5.5f+2.25f,j*-4.75f+20.0f};
  if(pat==1){p[0]=p[1]=p[2]=0;}
  if(pat==2){p[0]=j*2.0f;p[1]=p[2]=0;}
  if(pat==3){p[0]=100.25f-j*9.0f;p[1]=-99.75f+j*3.25f;p[2]=j*5.125f;}
  for(i=0;i<3;i++)*(f32 *)(actor.b+0x48+j*24+i*4)=p[i];
 }
 for(j=0;j<5;j++)for(i=0;i<3;i++){
  f32 p=pat==2?0.0f:(i==0?7.25f:i==1?-8.5f:9.75f);
  *(f32 *)(views.b+j*0x9A0+0x2F8+i*4)=p;
  *(f32 *)(otherViews.b+j*0x9A0+0x2F8+i*4)=p+10.0f;
 }
 for(i=0;i<1024;i++)wantedActor.b[i]=actor.b[i];
 for(i=0;i<(int)sizeof(vertices);i++)((u8 *)wantedVertices)[i]=((u8 *)vertices)[i];
 for(i=0;i<(int)sizeof(commands);i++)((u8 *)wantedCommands)[i]=((u8 *)commands)[i];
 result=func_151B32C8(commands,actor.b,view);
 if(flags&14){if(used || result!=commands)return 1;}
 else if(!ok){if(used!=1 || result!=commands)return 2;}
 else if(!matOK){if(used!=2 || result!=commands)return 3;}
 else{
  if(used!=8 || result!=commands+33)return 4;
  v=va?(Vtx *)(wantedActor.b+0x13C):wantedVertices;
  for(i=0;i<3;i++){first[i]=*(f32 *)(wantedActor.b+0x48+i*4);second[i]=*(f32 *)(wantedActor.b+0x60+i*4);}
  normal(first,second,first,offset);v=pair(v,first,offset,0);
  texture=*(u32 *)(wantedActor.b+0x13C);g=wantedCommands+6;
  for(segment=1;segment<10;segment++){
   for(i=0;i<3;i++){first[i]=*(f32 *)(wantedActor.b+0x48+(segment-1)*24+i*4);second[i]=*(f32 *)(wantedActor.b+0x48+segment*24+i*4);}
   normal(first,second,second,offset);v=pair(v,second,offset,texture);
   texture+=*(u32 *)(wantedActor.b+0x13C);
   g->words.w0=0x01004008;g->words.w1=(u32)(va?(Vtx *)(actor.b+0x13C)+(v-(Vtx *)(wantedActor.b+0x13C))-4:
        vertices+(v-wantedVertices)-4);g++;
   g->words.w0=0x05000204;g->words.w1=0;g++;
   g->words.w0=0x05020604;g->words.w1=0;g++;
  }
 }
 if(error)return 5;
 for(i=0;i<1024;i++)if(actor.b[i]!=wantedActor.b[i])return 6;
 for(i=0;i<(int)sizeof(vertices);i++)if(((u8 *)vertices)[i]!=((u8 *)wantedVertices)[i])return 7;
 for(i=0;i<(int)sizeof(commands);i++)if(((u8 *)commands)[i]!=((u8 *)wantedCommands)[i])return 8;
 return 0;
}
'''


if __name__ == '__main__':
    unittest.main()
