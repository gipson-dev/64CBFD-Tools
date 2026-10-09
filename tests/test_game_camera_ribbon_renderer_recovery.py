"""Complete uninstalled camera ribbon recovery with bounded setup callees."""

import hashlib
import itertools
import json
import math
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.experiments import game_camera_ribbon_renderer_candidates as screen
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_buffer_copy_match import CopyOracle
from tools.tests.test_game_record_ring_renderer_recovery import narrow, external, writes, rounded
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests import test_game_random_curve_record as native
from tools.tests.test_game_record_ring_renderer_recovery import NATIVE_TYPES

ACTOR, PAYLOAD, RECORDS, ALTERNATE, ORIGIN = 0x20000, 0x21000, 0x28000, 0x30000, 0x50000
VERTICES, OUTPUT = 0x60000, 0x70000
SOURCE = 'conker/src/game/generated_175250.c'
COUNTS = dict(func_151D5D60=5, func_15144B34=1, func_1514306C=4,
    func_150950D4=10, func_151441A4=14, func_151442FC=14, func_15142B7C=3,
    func_15142C10=6, func_15142CF0=8, func_1513F4E4=3, func_15142FBC=4)
COLORS = ((32767, -32768, -1, 255), (-11, 22, -33, 44))


def fixture(active=3, head=3, start=0, count=4, bank=0, cache=0, pattern=0, flags=0x80):
    memory = {STACK + i: 0xA5 for i in range(-0x600, 0x140)}
    for base, length in ((ACTOR, 256), (PAYLOAD, 128), (ORIGIN, 32),
            (VERTICES, 17000), (OUTPUT, 9000)):
        memory.update({base + i: (i * 17 + 13) & 255 for i in range(-16, length)})
    for base in (RECORDS, ALTERNATE):
        for index in range(-129, 257):
            for offset in range(20): memory[base + index * 20 + offset] = (index + offset * 17 + 13) & 255
            values = (index * 3.25 - 100., (index % 3) * -2.75, index * -4.5 + 50.)
            if pattern == 1: values = (0., 0., 0.)
            elif pattern == 2: values = (index * 2., index * 3., index * 4.)
            for axis, value in enumerate(values):
                put(memory, base + index * 20 + axis * 4, bits(value + (10. if base == ALTERNATE else 0.)))
            put(memory, base + index * 20 + 16, index * 9001 + 65535, 2)
    for offset, value, width in ((0x2C, active, 1), (0x2E, head, 1), (0x2D, start, 1),
            (0x25, count, 1), (0x94, RECORDS, 4), (0x98, PAYLOAD, 4)):
        put(memory, ACTOR + offset, value, width)
    for axis, value in enumerate((7.25, -8.5, 9.75) if pattern != 2 else (0., 0., 0.)):
        put(memory, ORIGIN + axis * 4, bits(value))
    for offset, value, width in ((0, bits(5.5), 4), (0x18, flags, 1), (0x19, 3, 1),
        (0x1A, 254, 1), (0x1B, 129, 1), (0x28, 0x122000, 4), (0x2C, 0x200005, 4),
        (0x30, 0x1F0600, 4), (0x34, 1, 4), (0x3B, 0x4C, 1), (0x3C, 0xAA00, 4),
        (0x40, 0x00550000, 4), (0x44, 128, 1), (0x45, 255, 1)):
        put(memory, PAYLOAD + offset, value, width)
    put(memory, screen.SYMBOLS['D_800BE9C0'], bank, 1)
    put(memory, screen.SYMBOLS['D_800DD1B0'], cache)
    put(memory, screen.SYMBOLS['D_800D2C9C'], 0xAA551234)
    for name in ('D_80091564', 'D_800915A4', 'D_800A4AC8'):
        for index in range(-2, 256): put(memory, screen.SYMBOLS[name] + index * 4, 0x44000000 + index * 17)
    return memory


def mutations(name, mode):
    choices = {
        1: ('func_151D5D60', [(ACTOR + 0x98, ALTERNATE, 4), (ACTOR + 0x94, ALTERNATE, 4)]),
        2: ('func_15144B34', [(ACTOR + 0x94, ALTERNATE, 4)]),
        3: ('func_1514306C', [(ACTOR + 0x94, ALTERNATE, 4), (PAYLOAD + 0x19, 255, 1)]),
        4: ('func_150950D4', [(PAYLOAD + 0x1A, 7, 1), (PAYLOAD + 0x18, 0, 1)]),
        5: ('func_151441A4', [(PAYLOAD + 0x1B, 17, 1), (PAYLOAD + 0x45, 127, 1)]),
        6: ('func_151442FC', [(PAYLOAD + 0x2C, 0x87654321, 4)]),
        7: ('func_15142FBC', [(ACTOR + 0x2E, 0, 1), (ACTOR + 0x2D, 2, 1)]),
        8: ('func_15142FBC', [(ACTOR + 0x94, ALTERNATE, 4), (ACTOR + 0x98, ALTERNATE, 4)]),
        9: ('func_15142FBC', [(PAYLOAD, bits(-7.0), 4), (ORIGIN, bits(100.), 4)]),
    }
    target, changes = choices.get(mode, ('', []))
    return changes if target == name else []


def trunc(value):
    return math.trunc(value) & 0xFFFFFFFF if math.isfinite(value) and -(2**31) <= value < 2**31 else 0x80000000


class CameraRibbonOracle(AreaOracle):
    def __init__(self, words, memory, view=0, success=True, texture=0x12345678, mode=0, phase=0,
                 entry=screen.ENTRY, args=None, connected=None):
        super().__init__(words, memory, args or (ACTOR, OUTPUT, view), phase=phase, entry=entry, connected=connected)
        self.success, self.texture, self.mode = success, texture, mode
        self.targets = {screen.SYMBOLS[n]: n for n in COUNTS}
        self.arguments_by_call = []
        self.forwarded, self.transforms = [], []

    def execute(self, word):
        op, rs, rt, rd, dest, fn = word >> 26, word >> 21 & 31, word >> 16 & 31, word >> 11 & 31, word >> 6 & 31, word & 63
        if op == 32: CopyOracle.execute(self, word)
        elif op == 17 and rs == 16 and fn == 4:
            value = floating(self.f[rd]); self.f[dest] = bits(math.sqrt(value) if value >= 0 else math.nan)
        elif op == 17 and rs == 16 and fn == 13:
            self.f[dest] = trunc(floating(self.f[rd]))
        else: super().execute(word)
        self.r[0] = 0

    def record_call(self, target):
        if target == screen.ENTRY:
            self.forwarded.append(self.arguments(3)); return
        if target == 0x151462C8:
            self.transforms.append(self.arguments(9)); return
        name = self.targets[target]
        args = list(self.arguments(COUNTS[name])); self.arguments_by_call.append((name, tuple(args)))
        if name == 'func_151D5D60':
            args[3] = 'cursor'
        elif name in ('func_151441A4', 'func_151442FC'):
            args[:4] = ['out0', 'out1', 'out2', 'out3']
        elif name in ('func_15142C10', 'func_15142CF0', 'func_1513F4E4', 'func_15142FBC'):
            sync = args[-1]; self.assert_sync = self.get(sync, 1)
            assert self.assert_sync == (1 if name == 'func_15142C10' else 0)
            args[-1] = 'sync'
        self.calls.append((target, tuple(args)))

    def hook(self, target):
        if target == 0x151462C8:
            self.r[2] = self.r[4]; return
        name, args = self.arguments_by_call[-1]
        result = 0
        if name == 'func_151D5D60': self.put(args[3], VERTICES if self.success else 0, 4)
        elif name == 'func_15144B34': result = ORIGIN
        elif name == 'func_1514306C': result = self.texture
        elif name in ('func_151441A4', 'func_151442FC'):
            for address, value in zip(args[:4], COLORS[name == 'func_151442FC']): self.put(address, value, 2)
        else:
            result = args[0] + 8
            if name in ('func_15142C10', 'func_15142CF0', 'func_1513F4E4', 'func_15142FBC'):
                self.put(args[-1], 0, 1)
        for address, value, width in mutations(name, self.mode): self.put(address, value, width)
        for offset in range(0, 32, 4): self.put(self.r[29] + offset, 0xCD000000 + offset, 4)
        for register in (1, 2, 3, *range(4, 16), 24, 25): self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]; self.r[2] = result


class CameraRibbonReference:
    def __init__(self, memory, view=0, success=True, texture=0x12345678, mode=0):
        self.memory, self.view = dict(memory), narrow(view, 16)
        self.success, self.texture, self.mode = success, texture, mode
        self.calls, self.events, self.segments = [], [], 0

    def get(self, address, width=4): return read(self.memory, address & 0xFFFFFFFF, width)

    def number(self, address): return floating(self.get(address))

    def store(self, address, value, width=4):
        address &= 0xFFFFFFFF; put(self.memory, address, value, width)
        self.events.append(('W', address, width, value & ((1 << (width * 8)) - 1)))

    def call(self, name, *args):
        self.calls.append((screen.SYMBOLS[name], tuple(a & 0xFFFFFFFF if isinstance(a, int) else a for a in args)))
        for address, value, width in mutations(name, self.mode): self.store(address, value, width)

    def position(self, point): return [self.number(point + axis * 4) for axis in range(3)]

    def offset(self, previous, current, endpoint):
        direction = [rounded(a - b) for a, b in zip(previous, current)]
        ray = [rounded(endpoint[i] - self.number(ORIGIN + i * 4)) for i in range(3)]
        normal = [rounded(rounded(direction[1] * ray[2]) - rounded(ray[1] * direction[2])),
            rounded(rounded(direction[2] * ray[0]) - rounded(ray[2] * direction[0])),
            rounded(rounded(direction[0] * ray[1]) - rounded(ray[0] * direction[1]))]
        squared = [rounded(v * v) for v in normal]
        length = rounded(math.sqrt(rounded(rounded(squared[0] + squared[1]) + squared[2])))
        if length == 0.: return (0., 0., 0.)
        scale = rounded(self.number(self.payload) / length)
        return tuple(rounded(v * scale) for v in normal)

    def pair(self, position, point, offset):
        for side in (1, -1):
            for axis in range(3): self.store(self.cursor + axis * 2,
                trunc(rounded(position[axis] + offset[axis] if side == 1 else position[axis] - offset[axis])), 2)
            self.store(self.cursor + 10, self.get(point + 16, 2) + 0x4000, 2)
            self.store(self.cursor + 8, 0x43C0 if side == 1 else 0x4000, 2)
            for channel in range(4): self.store(self.cursor + 12 + channel, 255, 1)
            self.store(self.cursor + 6, 0, 2); self.cursor += 16

    def prior(self, index): return self.get(ACTOR + 0x25, 1) - 1 if index < 0 else index

    def run(self):
        self.result = OUTPUT; self.payload = self.get(ACTOR + 0x98)
        if narrow(self.get(ACTOR + 0x2C, 1), 8) < 2: return self
        self.call('func_151D5D60', ACTOR + 0x84, self.view, self.get(ACTOR + 0x25, 1) * 32 - 32, 'cursor', 0)
        if not self.success: return self
        self.cursor = VERTICES
        if self.get(screen.SYMBOLS['D_800BE9C0'], 1): self.cursor += (self.get(ACTOR + 0x25, 1) * 2 - 2) * 16
        self.call('func_15144B34', self.view)
        records = self.get(ACTOR + 0x94)
        self.call('func_1514306C', 0, self.get(self.payload + 0x19, 1), 0, 2)
        if self.texture != self.get(screen.SYMBOLS['D_800DD1B0']):
            self.store(screen.SYMBOLS['D_800915A4'], self.get(screen.SYMBOLS['D_80091564'] + self.get(self.payload + 0x19, 1) * 4))
            self.call('func_150950D4', self.result, screen.SYMBOLS['D_800915A4'], 0, 0, 0, 0, 2, 256, 256,
                62 if self.get(self.payload + 0x18, 1) & 0x80 else 3)
            self.result += 8; self.store(screen.SYMBOLS['D_800DD1B0'], self.texture)
        for name, offset in (('func_151441A4', 0x44), ('func_151442FC', 0x45)):
            self.call(name, 'out0', 'out1', 'out2', 'out3', 0, 0, 0, 0, 0, 0, 0,
                self.get(self.payload + 0x1B, 1), self.get(self.payload + 0x1A, 1), narrow(self.get(self.payload + offset, 1), 8))
        self.call('func_15142B7C', self.result, self.get(self.payload + 0x2C), self.get(self.payload + 0x30)); self.result += 8
        self.call('func_15142C10', self.result, *COLORS[1], 'sync'); self.result += 8
        self.call('func_15142CF0', self.result, 0, 0, *COLORS[0], 'sync'); self.result += 8
        self.call('func_1513F4E4', self.result, self.get(self.payload + 0x3B, 1), 'sync'); self.result += 8
        render = self.get(self.payload + 0x28) | 0x80000 | self.get(screen.SYMBOLS['D_800D2C9C']) | 0x2C00 | self.get(self.payload + 0x3C) | self.get(self.payload + 0x40)
        table = screen.SYMBOLS['D_800A4AC8'] + narrow(self.get(self.payload + 0x34), 32) * 8
        self.call('func_15142FBC', self.result, render, self.get(table + 4) | self.get(table), 'sync'); self.result += 8
        previous_index = self.prior(narrow(self.get(ACTOR + 0x2E, 1), 8) - 1)
        index = self.prior(previous_index - 1); point = records + index * 20
        previous, current = self.position(records + previous_index * 20), self.position(point)
        self.pair(previous, records + previous_index * 20, self.offset(previous, current, previous))
        for _ in range(256):
            offset = self.offset(previous, current, current); previous_index, index = index, index - 1
            self.pair(current, point, offset)
            for word, value in ((0x01004008, self.cursor - 64), (0x05000204, 0), (0x05020604, 0)):
                self.store(self.result, word); self.store(self.result + 4, value); self.result += 8
            point -= 20
            if index < 0: index = self.get(ACTOR + 0x25, 1) - 1; point = records + index * 20
            previous, current = self.position(records + previous_index * 20), self.position(point)
            self.segments += 1
            if previous_index == narrow(self.get(ACTOR + 0x2D, 1), 8): return self
        raise AssertionError('reference ring is cyclic')


class GameCameraRibbonRecoveryTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-camera-ribbon-renderer-test'; cls.out.mkdir(parents=True, exist_ok=True)
        cls.record, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.retail = list(struct.unpack_from('>%dI' % screen.WORDS, (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        files = dict(source=SOURCE, elf='conker/build/conker.us.elf', guards='conker/retail_word_patches.us.csv', progress='conker/progress.csv')
        baseline = cls.out / 'baseline.json'
        if not baseline.exists():
            record = {}
            for name, path in files.items():
                data = (cls.root / path).read_bytes(); (cls.out / ('before-' + name)).write_bytes(data)
                record[name] = hashlib.sha256(data).hexdigest()
            for name, cwd in (('parent', cls.root), ('tools', cls.root / 'tools'), ('standalone', cls.root.parent / '64CBFD Tools')):
                record[name + '_HEAD'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=cwd, text=True).strip()
            baseline.write_text(json.dumps(record, indent=2) + '\n')
        cls.directory = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)

    def receipt(self, name, data): (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, view=0, success=True, texture=0x12345678, mode=0, phase=0, words=None, write_order=True):
        ref = CameraRibbonReference(memory, view, success, texture, mode).run()
        models = []
        for body in (self.words if words is None else words, self.retail):
            model = CameraRibbonOracle(body, memory, view, success, texture, mode, phase).run()
            self.assertEqual(external(model.memory), external(ref.memory))
            self.assertEqual(model.calls, ref.calls)
            if write_order: self.assertEqual(writes(model), ref.events)
            self.assertEqual(model.r[2], ref.result); models.append(model)
        return ref, models

    def test_01_complete_uninstalled_candidate_and_current_baseline(self):
        self.assertEqual((self.record['body_words'], self.record['frame'], self.record['differences']), (547, 304, 443))
        self.assertEqual((self.record['diagnostics'], self.record['pool_bytes'], self.record['saved_FP']), ('', 0, [28, 26, 24, 22, 20]))
        self.assertIn(screen.ORIGINAL, (self.root / SOURCE).read_text())
        self.assertFalse(STACK - 0x600 <= ORIGIN < STACK + 0x140)
        baseline = json.loads((self.out / 'baseline.json').read_text())
        for name, path in (('source', SOURCE), ('elf', 'conker/build/conker.us.elf'),
                ('guards', 'conker/retail_word_patches.us.csv'), ('progress', 'conker/progress.csv')):
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), baseline[name])
        functions = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')[0]
        self.assertEqual(functions[screen.FUNCTION], self.retail)
        self.receipt('slot', dict(self.record, installed=False, retail_words=546, retail_frame=288, guards_added=0))

    def test_02_full_guest_geometry_setup_and_byte_width_cases(self):
        coverage = [set(), set()]; count = 0
        cases = [dict(active=a) for a in range(256)]
        cases += [dict(head=h, count=c, start=s) for h, c, s in
            ((0, 4, 0), (1, 4, 2), (2, 4, 0), (127, 128, 125), (128, 128, 126),
             (255, 4, 1), (0, 255, 127), (1, 0, 255), (0, 1, 0))]
        cases += [dict(pattern=p, bank=b, cache=c) for p, b, c in itertools.product(range(3), (0, 1, 255), (0, 0x12345678))]
        cases += [dict(head=h, start=0, count=128) for h in range(256)]
        cases += [dict(head=2, start=0, count=c) for c in range(256)]
        cases += [dict(flags=f) for f in (0, 1, 127, 255)]
        for i, parameters in enumerate(cases):
            memory = fixture(**parameters)
            ref, models = self.compare(memory, view=(-32768, -1, 0, 32767, 0x18000)[i % 5], phase=(i % 2) * 8)
            for j, model in enumerate(models): coverage[j].update(model.visits)
            count += 1
        for width in (0., -0., -7., 1e-20, 1000.):
            memory = fixture(); put(memory, PAYLOAD, bits(width)); self.compare(memory); count += 1
        self.receipt('guest', dict(cases=count, executions=count * 2, covered_words=list(map(len, coverage)),
            uncovered_retail=[(a - screen.ENTRY) // 4 for a in range(screen.ENTRY, screen.ENTRY + screen.WORDS * 4, 4) if a not in coverage[1]],
            full_public_memory=True, writes_and_callbacks=True, fcsr='bounded nontrapping float model, not hardware'))

    def test_03_setup_mutations_failure_and_live_captured_pointer_lifetimes(self):
        count = 0
        for mode, bank, phase, cache in itertools.product(range(10), (0, 1), (0, 8), (0, 0x12345678)):
            self.compare(fixture(bank=bank, cache=cache), view=0xFFFF8000, mode=mode, phase=phase); count += 1
        for active, success in itertools.product((0, 1, 2, 127, 128, 255), (False, True)):
            self.compare(fixture(active=active), success=success); count += 1
        self.receipt('mutations', dict(cases=count, executions=count * 2, modes=10, caller_scratch_clobbered=True,
            first_eight_argument_homes_clobbered=True, setup_helpers='bounded hooks'))

    def test_04_effective_compiled_negative_controls(self):
        negatives = {
            'unsigned-active': screen.SELECTED.replace('*(s8 *)(actor + 0x2C)', 'actor[0x2C]'),
            'unsigned-head': screen.SELECTED.replace('*(s8 *)(actor + 0x2E)', 'actor[0x2E]'),
            'wrong-bank': screen.SELECTED.replace('if (D_800BE9C0)', 'if (!D_800BE9C0)'),
            'wrong-phase': screen.SELECTED.replace('->phase + 0x4000', '->phase + 0x4001'),
            'wrong-normal': screen.SELECTED.replace('deltaY * rayZ - rayY * deltaZ', 'rayY * deltaZ - deltaY * rayZ'),
            'wrong-triangle': screen.SELECTED.replace('1, 3, 2, 0', '1, 2, 3, 0'),
            'wrong-texture-cache': screen.SELECTED.replace('texture != D_800DD1B0', 'texture == D_800DD1B0'),
            'cached-records-too-early': screen.SELECTED.replace('        records = *(CameraRibbonRecord **)(actor + 0x94);\n', '').replace(
                '    payload = *(u8 **)(actor + 0x98);', '    payload = *(u8 **)(actor + 0x98);\n    records = *(CameraRibbonRecord **)(actor + 0x94);'),
        }
        cases = [(fixture(), 0), (fixture(active=255), 0), (fixture(head=128, count=4, start=1), 0),
            (fixture(), 2), (fixture(cache=0x12345678), 0)]
        records = []
        for name, body in negatives.items():
            meta, words = screen.compile_candidate(self.root, self.out, 'negative-' + name, body)
            changes = 0
            for memory, mode in cases:
                reference = CameraRibbonReference(memory, mode=mode).run()
                model = CameraRibbonOracle(words, memory, mode=mode)
                try:
                    model.run()
                    changes += (external(model.memory), model.calls, model.r[2]) != (external(reference.memory), reference.calls, reference.result)
                except AssertionError as error:
                    self.assertIn('budget exhausted', str(error))
                    self.assertNotEqual((external(model.memory), model.calls),
                        (external(reference.memory), reference.calls))
                    changes += 1
            self.assertGreater(changes, 0, name); records.append(dict(meta, differing_samples=changes))
        self.receipt('negatives', dict(effective=len(records), samples=len(cases), records=records))

    def test_05_copied_owner_neighbors_pools_and_relocations(self):
        original = (self.root / SOURCE).read_text()
        updated = original.replace(screen.ORIGINAL, screen.SELECTED).replace('#include <ultra64.h>\n',
            '#include <ultra64.h>\n' + screen.DECLARATIONS, 1)
        objects, warnings = [], []
        for name, body in (('before', original), ('candidate', updated)):
            obj, warning = compile_owner(self.root, self.out, body, 'owner-' + name)
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / ('owner-' + name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(obj.relative_to(self.root / 'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
            objects.append(obj); warnings.append(warning)
        self.assertEqual(warnings, [[], []])
        before, old, old_rel = parse_object(objects[0]); text, current, rel = parse_object(objects[1])
        self.assertEqual(current.keys(), old.keys())
        for name, fn in current.items():
            if name == screen.FUNCTION: continue
            prior = old[name]
            self.assertEqual((fn['size'], text[fn['value']:fn['value'] + fn['size']]),
                (prior['size'], before[prior['value']:prior['value'] + prior['size']]), name)
            self.assertEqual({o - fn['value']: r for o, r in rel.items() if fn['value'] <= o < fn['value'] + fn['size']},
                {o - prior['value']: r for o, r in old_rel.items() if prior['value'] <= o < prior['value'] + prior['size']}, name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        with self.assertRaisesRegex(ValueError, 'patched func_1514803C .* retail'):
            emit_padded_assembly(objects[1], self.root / 'conker/asm/175250.s',
                word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_175250')
        self.receipt('owner', dict(neighbors=len(current) - 1, diagnostics=0, pools_and_relative_relocations_unchanged=True,
            candidate_fits_original_slot=False, production_installed=False))

    def test_06_mapped_memory_fault_prefixes_aliases_and_profile_controls(self):
        memory = fixture(); retail = CameraRibbonOracle(self.retail, memory).run()
        public = sorted({a + i for event, a, width, value in retail.events if event in ('R', 'W')
            and not STACK - 0x600 <= a < STACK + 0x140 for i in range(width)})
        count = 0
        for missing in public[::3]:
            altered = dict(memory); del altered[missing]
            models = [CameraRibbonOracle(words, altered) for words in (self.words, self.retail)]
            for model in models:
                with self.assertRaisesRegex(AssertionError, 'unmapped'): model.run()
            self.assertEqual(external(models[0].memory), external(models[1].memory))
            self.assertEqual(models[0].calls, models[1].calls)
            self.assertEqual(writes(models[0]), writes(models[1])); count += 1
        aliases = 0
        for pointer in (RECORDS - 4, RECORDS, RECORDS + 4, PAYLOAD, PAYLOAD + 4):
            altered = fixture(); put(altered, ACTOR + 0x94, pointer)
            self.compare(altered); aliases += 1
        records = []
        for profile in screen.PROFILES:
            meta, words = screen.compile_candidate(self.root, self.out, 'profile-' + profile, profile=profile)
            self.compare(fixture(), words=words, write_order=False); records.append(meta)
        self.receipt('mapped', dict(missing_byte_pairs=count, public_aliases=aliases, profiles=records,
            fault_order='emitted prefixes, not portable C fault semantics', private_stack_aliases=False))

    def test_07_actual_native32_full_vertex_bytes_commands_and_typed_callbacks(self):
        cases = [dict(active=a) for a in range(256)]
        cases += [dict(head=2, start=0, count=c) for c in range(256)]
        cases += [dict(pattern=p, bank=b, cache=c, flags=f) for p, b, c, f in
            itertools.product(range(3), (0, 1), (0, 0x12345678), (0, 0x80))]
        arrays, invocations = [], []
        for case, parameters in enumerate(cases):
            memory = fixture(**parameters); reference = CameraRibbonReference(memory).run()
            end = getattr(reference, 'cursor', VERTICES)
            # Native tables retain the untouched bytes as well as the written vertex fields.
            rows = []
            for address in range(VERTICES, end, 16):
                values = [narrow(read(reference.memory, address + offset, 2), 16) for offset in (0, 2, 4, 6, 8, 10)]
                values += [read(reference.memory, address + offset, 1) for offset in (12, 13, 14, 15)]
                rows.append('{%s}' % ','.join(map(str, values)))
            arrays.append('static const int expected%d[][10]={%s};\n' % (case, ','.join(rows or ['{0}'])))
            command = []
            for address in range(OUTPUT, reference.result, 8):
                if read(reference.memory, address) in (0x01004008, 0x05000204, 0x05020604):
                    first, second = read(reference.memory, address), read(reference.memory, address + 4)
                    value = '(u32)((u8 *)vertices+%d)' % (second - VERTICES) if first == 0x01004008 else str(second)
                    command.append('if(commands[%d].words.w0!=0x%X||commands[%d].words.w1!=%s)return 11;' %
                        ((address - OUTPUT) // 8, first, (address - OUTPUT) // 8, value))
            invocation = 'initialize(%d,%d,%d,%d,%d,%d,%d,%d);\n' % tuple(parameters.get(n, d) for n, d in
                (('active', 3), ('head', 3), ('start', 0), ('count', 4), ('bank', 0), ('cache', 0), ('pattern', 0), ('flags', 128)))
            invocation += 'if(func_1514803C(actor,commands,0)!=commands+%d||error)return 1;\n' % ((reference.result - OUTPUT) // 8)
            invocation += 'if(check_vertices(expected%d,%d))return 2;\n' % (case, len(rows))
            invocation += '\n'.join(command) + '\n'
            begin = min((e[1] - OUTPUT for e in reference.events if e[0] == 'W' and OUTPUT <= e[1] < OUTPUT + 9000), default=0)
            invocation += 'if(check_commands_tail(%d,%d))return 4;\n' % (begin, reference.result - OUTPUT)
            invocation += 'if(!unchanged())return 3;\n'
            invocations.append(invocation)
        self.fixture = NATIVE_TYPES + 'float sqrtf(float);\n' + screen.DECLARATIONS + NATIVE_FIXTURE + '\n' + screen.SELECTED + '\n' + ''.join(arrays)
        self.run_host(''.join(invocations))
        self.receipt('native', dict(cases=len(cases), actual_native32=True, complete_vertex_bytes=True,
            actual_typed_callbacks=True, argument_checks=True, full_actor_payload_records_canaries=True,
            signed_active_and_unsigned_count_all_bytes=True, reference='independent Python float32 geometry',
            cyclic_and_invalid_float_cast_cases=False, native_aliases_and_mutations=False))

    def test_08_actual_graphics_dispatcher_protected_table_and_full_leaf(self):
        elf = screen.sections(self.root / 'conker/build/conker.us.elf')
        table = 0x8008A2A8
        containing = [(base, data) for base, data in elf.values() if base <= table and table + 4 <= base + len(data)]
        self.assertEqual(len(containing), 1)
        base, data = containing[0]; self.assertEqual(struct.unpack_from('>I', data, table - base)[0], screen.ENTRY)
        rom = (self.root / 'conker/conker.us.bin').read_bytes()
        dispatcher = list(struct.unpack_from('>52I', rom, 0x1750FC)); count = 0
        for bank, view, phase, flags in itertools.product((0, 1), (-32768, 32767), (0, 8), (0, 32)):
            memory = fixture(bank=bank); put(memory, ACTOR + 0x31, 1, 1); put(memory, ACTOR + 0x1E, flags, 2)
            put(memory, table, screen.ENTRY)
            reference = CameraRibbonReference(memory, view=view).run()
            for body in (self.words, self.retail):
                connected = dict(zip(range(screen.ENTRY, screen.ENTRY + len(body) * 4, 4), body))
                model = CameraRibbonOracle(dispatcher, memory, view=view, phase=phase, entry=0x15147C4C,
                    args=(OUTPUT, ACTOR, view), connected=connected).run()
                self.assertEqual(model.forwarded, [(ACTOR, OUTPUT, view & 0xFFFFFFFF)])
                optional = read(memory, ACTOR + 0x28) if flags else 0
                self.assertEqual(model.transforms, [(OUTPUT, ACTOR + 0x34, 0, 0, 0, view & 0xFFFFFFFF, ACTOR + 0x54, 2, optional)])
                self.assertEqual(external(model.memory), external(reference.memory))
                self.assertEqual(model.calls, reference.calls); self.assertEqual(model.r[2], reference.result)
                count += 1
        self.receipt('connected', dict(executions=count, cases=count // 2, dispatcher_words=52,
            candidate_words=len(self.words), retail_words=546, actual_protected_table=hex(table),
            transform_and_graphics_helpers='bounded hooks', gameplay_hardware=False))

    def test_09_complete_form_screening_and_cyclic_emitted_prefixes(self):
        records = []
        for name, body in screen.candidates():
            meta, words = screen.compile_candidate(self.root, self.out, 'form-' + name, body)
            for memory, mode in ((fixture(), 0), (fixture(bank=1, pattern=1), 0), (fixture(), 7)):
                self.compare(memory, words=words, mode=mode, write_order=False)
            records.append(meta)
        class Prefix(CameraRibbonOracle):
            def put(self, address, value, size):
                super().put(address, value, size)
                if len(writes(self)) >= 200: raise RuntimeError('public write bound')
        count = 0
        for memory in (fixture(count=4, head=3, start=255), fixture(count=255, head=0, start=253)):
            models = [Prefix(words, memory) for words in (self.words, self.retail)]
            for model in models:
                with self.assertRaisesRegex(RuntimeError, 'public write bound'): model.run()
            self.assertEqual(external(models[0].memory), external(models[1].memory))
            self.assertEqual(writes(models[0]), writes(models[1])); self.assertEqual(models[0].calls, models[1].calls)
            count += 1
        self.receipt('forms', dict(forms=records, finite_samples_per_form=3, cyclic_prefix_pairs=count,
            prefix_public_write_bound=200, production_limit_added=False, full_qualification_for_each_form=False))


NATIVE_FIXTURE = r'''
u8 D_800BE9C0;s32 D_800DD1B0,D_80091564[256];u32 D_800915A4[256],D_800D2C9C,D_800A4AC8[256];
static u8 actor[256] __attribute__((aligned(8))),payload[128] __attribute__((aligned(8)));
static CameraRibbonRecord records[386];static Vtx vertices[1064];static Gfx commands[1125];
static u8 actorBefore[256],payloadBefore[128],recordsBefore[7720];static f32 origin[3];
static int error;static Gfx *first;
float sqrtf(float value){float result;__asm__("sqrtss %1,%0":"=x"(result):"x"(value));return result;}
static void initialize(int active,int head,int start,int count,int bank,int cache,int p,int flags){
 int i,j;u8 *bytes;error=0;first=commands;
 for(i=0;i<256;i++)actor[i]=(i*17+13)&255;
 for(i=0;i<128;i++)payload[i]=(i*17+13)&255;
 for(i=0;i<386;i++){
  int index=i-129;bytes=(u8 *)(records+i);for(j=0;j<20;j++)bytes[j]=(index+j*17+13)&255;
  records[i].position.x=p==1?0:p==2?index*2.0f:index*3.25f-100.0f;
  records[i].position.y=p==1?0:p==2?index*3.0f:((index%3+3)%3)*-2.75f;
  records[i].position.z=p==1?0:p==2?index*4.0f:index*-4.5f+50.0f;
  records[i].phase=index*9001+65535;
 }
 origin[0]=p==2?0:7.25f;origin[1]=p==2?0:-8.5f;origin[2]=p==2?0:9.75f;
 *(CameraRibbonRecord **)(actor+148)=records+129;*(u8 **)(actor+152)=payload;
 actor[44]=active;actor[46]=head;actor[45]=start;actor[37]=count;
 *(f32 *)payload=5.5f;payload[24]=flags;payload[25]=3;payload[26]=254;payload[27]=129;
 *(u32 *)(payload+40)=0x122000;*(u32 *)(payload+44)=0x200005;*(u32 *)(payload+48)=0x1F0600;
 *(s32 *)(payload+52)=1;payload[59]=0x4C;*(u32 *)(payload+60)=0xAA00;*(u32 *)(payload+64)=0x00550000;
 payload[68]=128;payload[69]=255;
 D_800BE9C0=bank;D_800DD1B0=cache;D_800D2C9C=0xAA551234;
 for(i=0;i<256;i++)D_80091564[i]=D_800A4AC8[i]=D_800915A4[i]=0x44000000+i*17;
 bytes=(u8 *)vertices;for(i=0;i<(int)sizeof(vertices);i++)bytes[i]=((i%16<12?(i^1):i)*17+13)&255;
 bytes=(u8 *)commands;for(i=0;i<(int)sizeof(commands);i++)bytes[i]=(i*17+13)&255;
 for(i=0;i<256;i++){actorBefore[i]=actor[i];}
 for(i=0;i<128;i++){payloadBefore[i]=payload[i];}
 bytes=(u8 *)records;for(i=0;i<7720;i++)recordsBefore[i]=bytes[i];
}
void func_151D5D60(void *slots,s16 view,s32 size,Vtx **cursor,u8 *fresh){
 if(slots!=actor+132||view||size!=actor[37]*32-32||fresh){error=1;}
 *cursor=vertices;
}
f32 *func_15144B34(s32 view){if(view)error=2;return origin;}
s32 func_1514306C(void *source,s32 index,s32 subindex,u8 kind){
 if(source||index!=3||subindex||kind!=2){error=3;}
 return 0x12345678;
}
Gfx *func_150950D4(Gfx *p,void *source,s32 a,s32 b,s32 c,s32 d,s32 kind,s32 x,s32 y,s32 flags){
 if(p!=first||source!=D_800915A4||a||b||c||d||kind!=2||x!=256||y!=256||flags!=((payload[24]&128)?62:3))error=4;
 if(D_800915A4[0]!=(u32)D_80091564[3]){error=5;}
 return p+1;
}
void func_151441A4(s16 *a,s16 *b,s16 *c,s16 *d,u8 i0,u8 i1,u8 i2,u8 i3,u8 j0,u8 j1,u8 j2,u8 j3,u8 scale,u8 mode){
 if(i0||i1||i2||i3||j0||j1||j2||j3!=129||scale!=254||mode!=128)error=6;
 *a=32767;*b=-32768;*c=-1;*d=255;
}
void func_151442FC(s16 *a,s16 *b,s16 *c,s16 *d,u8 i0,u8 i1,u8 i2,u8 i3,u8 j0,u8 j1,u8 j2,u8 j3,u8 scale,u8 mode){
 if(i0||i1||i2||i3||j0||j1||j2||j3!=129||scale!=254||mode!=255)error=7;
 *a=-11;*b=22;*c=-33;*d=44;
}
Gfx *func_15142B7C(Gfx *p,u32 a,u32 b){if(a!=0x200005||b!=0x1F0600)error=8;return p+1;}
Gfx *func_15142C10(Gfx *p,s32 r,s32 g,s32 b,s32 a,u8 *sync){
 if(r!=-11||g!=22||b!=-33||a!=44||*sync!=1){error=9;}
 *sync=0;return p+1;
}
Gfx *func_15142CF0(Gfx *p,s32 lod,s32 fraction,s32 r,s32 g,s32 b,s32 a,u8 *sync){
 if(lod||fraction||r!=32767||g!=-32768||b!=-1||a!=255||*sync){error=10;}
 return p+1;
}
Gfx *func_1513F4E4(Gfx *p,u8 kind,u8 *sync){if(kind!=0x4C||*sync)error=11;return p+1;}
Gfx *func_15142FBC(Gfx *p,u32 a,u32 b,u8 *sync){
 if(a!=(0x122000|0x80000|0xAA551234|0x2C00|0xAA00|0x00550000)||b!=(D_800A4AC8[3]|D_800A4AC8[2])||*sync)error=12;
 return p+1;
}
static int check_vertices(const int expected[][10],int n){
 int i,j;u8 *bytes=(u8 *)vertices;
 for(i=0;i<n;i++){
  for(j=0;j<3;j++)if(vertices[i].v.ob[j]!=expected[i][j])return 1;
  if(vertices[i].v.flag!=(u16)expected[i][3])return 2;
  for(j=0;j<2;j++)if(vertices[i].v.tc[j]!=expected[i][4+j])return 3;
  for(j=0;j<4;j++)if(vertices[i].v.cn[j]!=expected[i][6+j])return 4;
 }
 for(i=n*16;i<(int)sizeof(vertices);i++)if(bytes[i]!=(((i%16<12?(i^1):i)*17+13)&255))return 5;
 return 0;
}
static int unchanged(void){
 int i;u8 *bytes=(u8 *)records;
 for(i=0;i<256;i++)if(actorBefore[i]!=actor[i])return 0;
 for(i=0;i<128;i++)if(payloadBefore[i]!=payload[i])return 0;
 for(i=0;i<7720;i++)if(recordsBefore[i]!=bytes[i])return 0;
 return 1;
}
static int check_commands_tail(int begin,int end){
 int i;u8 *bytes=(u8 *)commands;
 for(i=0;i<(int)sizeof(commands);i++)if((i<begin||i>=end)&&bytes[i]!=((i*17+13)&255))return 1;
 return 0;
}
'''


if __name__ == '__main__': unittest.main()
