"""Full growth callback: live integration, insertion, stack step and phase loop."""

import csv
import hashlib
import itertools
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.check_game_data_layout import audit_layout, load_section
from tools.experiments import game_record_growth_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_graphics_dispatch_match import DispatchOracle
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_callback_update_match import external, public
from tools.tests.test_game_record_phase_shaping_match import PhaseReference, signed
from tools.tests import test_game_wrapped_record_step_match as motion
from tools.tests import test_game_actor_timer_callbacks_match as timer
from tools.tests import test_game_payload_callback_update_match as dispatcher
from tools.tests import test_game_random_curve_record as native

SOURCE = 'conker/src/game/generated_175250.c'
ACTOR, PAYLOAD, RECORDS = motion.ACTOR, motion.PAYLOAD, motion.RECORDS
TIME = 0x800BE9A4


def shapes(root):
    text = (root / SOURCE).read_text()
    old = text.replace(screen.SELECTED, screen.ORIGINAL).replace(screen.DECLARATIONS + '\n', '')
    assert old.count(screen.ORIGINAL) == 1
    return old, old.replace('/* Non-matching placeholders', screen.DECLARATIONS + '\n/* Non-matching placeholders', 1).replace(screen.ORIGINAL, screen.SELECTED)


def fixture(active=2, start=0, head=2, count=5, flags=0, phase=0, prior_step=0x3456, delta=0x3F000000):
    memory = motion.fixture(start=head, end=start, count=count, delta=delta)
    put(memory, ACTOR + 0x2C, active, 1); put(memory, PAYLOAD + 0x18, flags, 1)
    put(memory, PAYLOAD + 8, bits(1.5))
    for i, value in enumerate((9., -3., 5.)):
        put(memory, ACTOR + 0x10 + i * 4, bits(value))
    put(memory, STACK + phase - 16, prior_step, 2)
    return memory


class LoopBound(Exception):
    pass


class GrowthReference(PhaseReference):
    def __init__(self, memory, phase=0, bound=64, delta=TIME, stack=None):
        super().__init__(memory, bound)
        self.stack = STACK + phase - 16 if stack is None else stack
        self.delta, self.head_reads = delta, 0

    def get(self, address, size=4):
        value = super().get(address, size)
        if address == ACTOR + 0x2E and size == 1:
            self.head_reads += 1
            if self.head_reads >= self.bound:
                raise LoopBound()
        return value

    def run(self):
        index = signed(self.get(ACTOR + 0x2D, 1)); head = signed(self.get(ACTOR + 0x2E, 1))
        records = self.get(ACTOR + 0x94); payload = self.get(ACTOR + 0x98)
        while index != head:
            record = (records + index * 20) & 0xFFFFFFFF
            gravity = self.get(payload + 16); delta = self.get(self.delta)
            product = bits(floating(gravity) * floating(delta)); index += 1
            vy = self.get(record + 12); next_vy = bits(floating(vy) - floating(product))
            x = self.get(record); self.put(record + 12, next_vy, 4)
            delta = self.get(self.delta); vx = self.get(payload + 4); vy = self.get(record + 12)
            next_x = bits(floating(x) + floating(bits(floating(vx) * floating(delta))))
            y = self.get(record + 4); self.put(record, next_x, 4)
            delta = self.get(self.delta)
            next_y = bits(floating(y) + floating(bits(floating(vy) * floating(delta))))
            z = self.get(record + 8); self.put(record + 4, next_y, 4)
            delta = self.get(self.delta); vz = self.get(payload + 12)
            self.put(record + 8, bits(floating(z) + floating(bits(floating(vz) * floating(delta)))), 4)
            if index == self.get(ACTOR + 0x25, 1): index = 0
            head = signed(self.get(ACTOR + 0x2E, 1))
        count = self.get(ACTOR + 0x25, 1); active = signed(self.get(ACTOR + 0x2C, 1))
        flags = self.get(payload + 0x18, 1)
        if active < count - 1:
            phase = 4096 if flags & 32 else 0
            if active:
                step = (4096 // abs(active)) * (1 if active > 0 else -1)
                self.put(self.stack, step, 2)
            position = self.get(ACTOR + 0x10)
            self.put(ACTOR + 0x2C, active + 1, 1)
            record = records + head * 20
            self.put(record, position, 4)
            self.put(record + 4, self.get(ACTOR + 0x14), 4)
            self.put(record + 8, self.get(ACTOR + 0x18), 4)
            head = signed(self.get(ACTOR + 0x2E, 1)); vy = self.get(payload + 8)
            self.put(records + head * 20 + 12, vy, 4)
            head = signed(self.get(ACTOR + 0x2E, 1)); count = self.get(ACTOR + 0x25, 1)
            self.put(ACTOR + 0x2E, head + 1, 1); head = signed(self.get(ACTOR + 0x2E, 1))
            if head == count:
                self.put(ACTOR + 0x2E, 0, 1); head = signed(self.get(ACTOR + 0x2E, 1))
            index = signed(self.get(ACTOR + 0x2D, 1))
            if index != head:
                step = self.get(self.stack, 2)
                while True:
                    self.put(records + index * 20 + 16, phase, 2)
                    flags = self.get(payload + 24, 1)
                    phase = (phase - step if flags & 32 else phase + step) & 65535
                    count = self.get(ACTOR + 0x25, 1); index += 1
                    if index == count: index = 0
                    head = signed(self.get(ACTOR + 0x2E, 1))
                    if index == head: break
        else:
            self.put(payload + 0x20, 3 if flags & 0x17 else 2, 1)
        self.returned = 1
        return self


class GrowthOracle(DispatchOracle):
    def __init__(self, words, memory, phase=0, entry=screen.ENTRY, bound=64, connected=None):
        TriangleOracle.__init__(self, words, memory, arguments=(ACTOR,), phase=phase, entry=entry, connected=connected)
        self.bound, self.head_reads = bound, 0

    def get(self, address, size):
        value = super().get(address, size)
        if address == ACTOR + 0x2E and size == 1:
            self.head_reads += 1
            if self.head_reads >= self.bound: raise LoopBound()
        return value

    def put(self, address, value, size):
        if self.recording:
            assert address % size == 0, ('unaligned store', address, size)
            assert all(address + i in self.memory for i in range(size)), ('unmapped store', address, size)
        super().put(address, value, size)

    def record_call(self, target):
        self.calls.append((target, self.arguments(1)))

    def hook(self, target):
        raise AssertionError(('unexpected external call', target))


def state(model):
    try:
        model.run()
        return 'returned'
    except LoopBound:
        return 'bounded-prefix'
    except AssertionError as error:
        assert isinstance(error.args[0], tuple) and error.args[0][0] in (
            'unmapped read', 'unmapped store', 'unaligned read', 'unaligned store'), error
        return 'fault'


class GameRecordGrowthMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-record-growth-test'; cls.out.mkdir(exist_ok=True)
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.retail = list(struct.unpack_from('>140I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.directory = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)
        if not (cls.out / 'baseline.json').exists():
            old, _ = shapes(cls.root); assert (cls.root / SOURCE).read_text() == old
            slots, _ = timer.slot_records(cls.root)
            assert slots == json.loads((cls.root / 'conker/build/game-record-phase-shaping-test/after.json').read_text())['slots']
            data = (cls.root / 'conker/build/conker.us.elf').read_bytes(); (cls.out / 'before.elf').write_bytes(data)
            for name in ('retail_word_patches.us.csv', 'progress.csv'):
                (cls.out / ('before-' + name)).write_bytes((cls.root / 'conker' / name).read_bytes())
            (cls.out / 'baseline.json').write_text(json.dumps(dict(slots=slots,
                source_sha256=hashlib.sha256(old.encode()).hexdigest(), elf_sha256=hashlib.sha256(data).hexdigest()), indent=2) + '\n')

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, phase=0, bound=64, words=None, entry=screen.ENTRY, delta=TIME):
        ref = GrowthReference(memory, phase, bound, delta); expected = state(ref)
        models = []
        for body in ((words,) if words is not None else (self.words, self.retail)):
            model = GrowthOracle(body, memory, phase, entry, bound)
            self.assertEqual(state(model), expected)
            self.assertEqual((external(model.memory), public(model.events), model.head_reads),
                (external(ref.memory), public(ref.events), ref.head_reads))
            if expected == 'returned': self.assertEqual(model.r[2], 1)
            models.append(model)
        if words is None:
            self.assertEqual((models[0].r, models[0].f, models[0].lo, models[0].events, models[0].memory),
                (models[1].r, models[1].f, models[1].lo, models[1].events, models[1].memory))
        return expected, models

    def test_01_full_direct_slot_and_relocations(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (140, 16, 0))
        self.assertEqual(self.words, self.retail)
        self.assertEqual((self.meta['diagnostics'], self.meta['pool_bytes']), ('', 0))
        self.assertEqual(dict(self.meta['relocations']), {28: [('R_MIPS_HI16', 'D_800BE9A4')], 32: [('R_MIPS_LO16', 'D_800BE9A4')]})
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
            self.assertFalse(any(row['function'] == screen.FUNCTION for row in csv.DictReader(stream)))
        self.receipt('slot', self.meta)

    def test_02_byte_metadata_floats_stack_lifetime_and_coverage(self):
        visited, count, bounded = set(), 0, 0
        for field, value, phase in itertools.product(('active', 'start', 'head', 'count', 'flags'), range(256), (0, 8)):
            kwargs = {field: value, 'phase': phase}
            result, models = self.compare(fixture(**kwargs), phase, bound=24)
            visited.update(models[0].visits); count += 1; bounded += result != 'returned'
        for active, flags, prior_step, phase, delta in itertools.product((0, 1, 255), (0, 32),
                (0, 1, 0x3456, 65535), (0, 8), (0, 0x80000000, 0x3DCCCCCD, 0x3F800001, 0xBF000000)):
            result, models = self.compare(fixture(active=active, flags=flags, prior_step=prior_step, phase=phase, delta=delta), phase)
            visited.update(models[0].visits); count += 1; bounded += result != 'returned'
            stack_events = [e for e in models[0].events if e[1] == STACK + phase - 16]
            self.assertEqual(any(e[0] == 'W' for e in stack_events), active != 0)
        for flags in (1, 2, 4, 8, 16, 32):
            result, models = self.compare(fixture(active=4, flags=flags))
            visited.update(models[0].visits); count += 1; bounded += result != 'returned'
        missing = sorted((address - screen.ENTRY) // 4 for address in set(range(screen.ENTRY, screen.ENTRY + 560, 4)) - visited)
        self.assertEqual(missing, [66, 72, 115, 128, 136])
        self.receipt('guest', dict(cases=count, executions=2 * count, bounded_prefixes=bounded,
            unreachable_word_indices=missing, reachable_words=len(visited), all_byte_metadata=True,
            raw_retail_full_state_and_reference_public_trace_agreement=True,
            conditional_stack_step_prior_values=[0, 1, 0x3456, 65535], production_bound=False))

    def test_03_missing_bytes_empty_window_and_live_aliases(self):
        count = 0
        for kwargs in ({}, dict(active=4, start=2, head=2), dict(active=0, start=2, head=2), dict(flags=32)):
            memory = fixture(**kwargs); _, models = self.compare(memory)
            touched = {a + i for _, a, size, _ in models[0].events for i in range(size)}
            for address in sorted(touched):
                missing = dict(memory); del missing[address]
                self.compare(missing); count += 1
        memory = fixture(active=4, start=2, head=2)
        for address in list(memory):
            if RECORDS - 6000 <= address < RECORDS + 5200: del memory[address]
        del memory[TIME]
        self.assertEqual(self.compare(memory)[0], 'returned')
        aliases = 0
        for location, active, flags, phase in itertools.product((ACTOR + 0x10, ACTOR + 0x24,
                ACTOR + 0x2C, ACTOR + 0x94, ACTOR + 0x98, PAYLOAD + 0x18), (0, 2), (0, 32), (0, 8)):
            memory = fixture(active=active, flags=flags, phase=phase)
            put(memory, ACTOR + 0x94, location - 16)
            self.compare(memory, phase, bound=12); aliases += 1
        memory = fixture(active=4, start=0, head=1)
        for i in range(-16, 24): memory[TIME + i] = 0
        for i, value in enumerate((2., 3., 4., 1.)): put(memory, TIME - 12 + i * 4, bits(value))
        put(memory, ACTOR + 0x94, TIME - 12); self.compare(memory); aliases += 1
        self.receipt('faults-aliases', dict(missing_byte_pairs=count, aliases=aliases, alias_executions=2 * aliases,
            empty_full_capacity_skips_records_and_time=True, complete_public_order_and_pointer_capture=True,
            emitted_fault_prefix_and_private_stack_not_portable_C_guarantees=True))

    def test_04_effective_semantic_negatives(self):
        negatives = {
            'unsigned-active': screen.SELECTED.replace('*(s8 *)(actor + 0x2C)', 'actor[0x2C]'),
            'unsigned-start': screen.SELECTED.replace('*(s8 *)(actor + 0x2D)', 'actor[0x2D]'),
            'signed-count': screen.SELECTED.replace('actor[0x25]', '*(s8 *)(actor + 0x25)'),
            'unsigned-head': screen.SELECTED.replace('*(s8 *)(actor + 0x2E)', 'actor[0x2E]'),
            'guessed-zero-step': screen.SELECTED.replace('u16 step;', 'u16 step = 0;'),
            'wrong-phase-direction': screen.SELECTED.replace('phase -= step;', 'phase += step;'),
            'wrong-initial-velocity': screen.SELECTED.replace('*(f32 *)(payload + 0x08)', '*(f32 *)(payload + 0x04)'),
            'wrong-selector-mask': screen.SELECTED.replace('payload[0x18] & 0x17', 'payload[0x18] & 0x01'),
            'cached-time': screen.SELECTED.replace('    s32 active;', '    s32 active;\n    f32 time = D_800BE9A4;').replace(
                ' * D_800BE9A4;', ' * time;'),
        }
        samples = [fixture(), fixture(active=0), fixture(active=255), fixture(start=255),
            fixture(start=126, head=127, count=128), fixture(head=128, start=127), fixture(flags=32),
            fixture(active=4, flags=2), fixture(active=4, start=2, head=2)]
        alias = fixture(active=4, start=0, head=1)
        for i in range(-16, 24): alias[TIME + i] = 0
        for i, value in enumerate((2., 3., 4., 1.)): put(alias, TIME - 12 + i * 4, bits(value))
        put(alias, ACTOR + 0x94, TIME - 12); samples.append(alias)
        receipts = []
        for name, body in negatives.items():
            meta, words = screen.compile_candidate(self.root, self.out, 'negative-' + name, body)
            changed = 0
            for memory in samples:
                ref, model = GrowthReference(memory, bound=12), GrowthOracle(words, memory, bound=12)
                expected, observed = state(ref), state(model)
                changed += (expected, external(ref.memory)) != (observed, external(model.memory))
            self.assertGreater(changed, 0, name)
            receipts.append(dict(meta, behavioral_differences=changed))
        self.receipt('negatives', dict(effective_negatives=len(receipts), samples=len(samples), records=receipts))

    def test_05_owner_postprocessing_neighbors_actual_padding_and_rebases(self):
        objects, warnings = [], []
        for name, text in zip(('baseline', 'selected'), shapes(self.root)):
            obj, warning = compile_owner(self.root, self.out, text, 'owner-' + name)
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / ('owner-' + name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(obj.relative_to(self.root / 'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
            objects.append(obj); warnings.append(warning)
        self.assertEqual(warnings, [[], []])
        old, before, old_rel = parse_object(objects[0]); text, current, rel = parse_object(objects[1])
        self.assertEqual(current.keys(), before.keys())
        for name, fn in current.items():
            if name == screen.FUNCTION: continue
            prev = before[name]
            self.assertEqual((fn['size'], text[fn['value']:fn['value'] + fn['size']]),
                (prev['size'], old[prev['value']:prev['value'] + prev['size']]), name)
            self.assertEqual({o - fn['value']: r for o, r in rel.items() if fn['value'] <= o < fn['value'] + fn['size']},
                {o - prev['value']: r for o, r in old_rel.items() if prev['value'] <= o < prev['value'] + prev['size']}, name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/175250.s',
            word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_175250')
        start = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('\n', assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), start)) + 1
        self.assertNotIn('.space', assembly[start:end])
        asm, obj = self.out / 'solo.s', self.out / 'solo.o'
        asm.write_text('.text\n.set noreorder\n' + assembly[start:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        self.assertEqual(parse_object(obj)[1][screen.FUNCTION]['size'], 560)
        self.assertEqual(parse_object(obj)[2], self.meta['relocations'])
        count = 0
        for variant, (entry, delta) in enumerate(((screen.ENTRY, TIME), (0x10007FFC, 0x80007FFC),
                (0x80008000, 0x80008000), (0x8FFF7FFC, 0x8000FFF0))):
            script, elf = self.out / ('rebase-%d.ld' % variant), self.out / ('rebase-%d.elf' % variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                '--defsym=D_800BE9A4=0x%X' % delta, '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack_from('>140I', sections(elf)['.text'][1]))
            if not variant: self.assertEqual(words, self.retail)
            for active, flags, phase in itertools.product((0, 2, 4, 255), (0, 32), (0, 8)):
                memory = fixture(active=active, flags=flags, phase=phase)
                put(memory, delta, read(memory, TIME)); del memory[TIME]
                if delta == TIME: put(memory, delta, 0x3F000000)
                self.compare(memory, phase, words=words, entry=entry, delta=delta); count += 1
        self.receipt('owner', dict(neighbors=len(current) - 1, diagnostics=0, guards=0, padding_bytes=560,
            relative_relocations_and_pools_unchanged=True, independent_links=4, cases=count))

    def test_06_whole_ELF_identical_guards_unchanged_and_one_conversion_row(self):
        baseline = json.loads((self.out / 'baseline.json').read_text()); old, new = shapes(self.root)
        self.assertEqual(hashlib.sha256(old.encode()).hexdigest(), baseline['source_sha256'])
        installed = (self.root / SOURCE).read_text() == new
        slots, functions = timer.slot_records(self.root)
        self.assertEqual(slots, baseline['slots']); self.assertEqual(functions[screen.FUNCTION], self.retail)
        elf = self.root / 'conker/build/conker.us.elf'
        self.assertEqual(elf.read_bytes(), (self.out / 'before.elf').read_bytes())
        self.assertTrue(audit_layout(elf, self.root / 'conker')['exact'])
        with (self.out / 'before-progress.csv').open(newline='') as stream: progress = list(csv.DictReader(stream))
        with (self.root / 'conker/progress.csv').open(newline='') as stream: after = list(csv.DictReader(stream))
        self.assertEqual(after, [dict(row, language='c') if installed and row['function'] == screen.FUNCTION else row for row in progress])
        self.assertEqual((self.root / 'conker/retail_word_patches.us.csv').read_bytes(), (self.out / 'before-retail_word_patches.us.csv').read_bytes())
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream: guards = list(csv.DictReader(stream))
        self.receipt('linked', dict(installed=installed, symbols=len(slots), full_ELF_byte_identical=True,
            guards=len(guards), guards_byte_identical=True, conversion_changes=1 if installed else 0,
            elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest()))
        if installed: self.receipt('after', dict(slots=slots, guards=guards, progress=after))

    def test_07_actual_native32_defined_cases_and_full_canaries(self):
        self.fixture = r'''typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;
typedef unsigned int u32;typedef int s32;typedef float f32;
typedef struct {u32 words[3];} ActorPosition15147EB8;
''' + screen.DECLARATIONS + r'''
static union {u32 align;u8 b[256];} actor,wantedActor;
static union {u32 align;u8 b[128];} payload,wantedPayload;
static GrowthRecord151488C4 records[560],wanted[560];
f32 D_800BE9A4;
static int expected(void) {
    int index=(s8)wantedActor.b[0x2D],head=(s8)wantedActor.b[0x2E],count=wantedActor.b[0x25];
    int active=(s8)wantedActor.b[0x2C],step,phase;
    volatile f32 product;GrowthRecord151488C4 *p;
    while(index!=head) {
        p=wanted+300+index;
        product=*(f32 *)(payload.b+16)*D_800BE9A4;p->velocityY-=product;
        product=*(f32 *)(payload.b+4)*D_800BE9A4;p->x+=product;
        product=p->velocityY*D_800BE9A4;p->y+=product;
        product=*(f32 *)(payload.b+12)*D_800BE9A4;p->z+=product;
        if(++index==count) index=0;
    }
    if(active<count-1) {
        if(!active) return -1;
        step=(u16)(4096/active);phase=(payload.b[24]&32)?4096:0;
        wantedActor.b[0x2C]=(u8)(active+1);p=wanted+300+head;
        *(ActorPosition15147EB8 *)p=*(ActorPosition15147EB8 *)(wantedActor.b+16);
        p->velocityY=*(f32 *)(payload.b+8);
        head=(s8)(head+1);if(head==count) head=0;wantedActor.b[0x2E]=(u8)head;
        index=(s8)wantedActor.b[0x2D];
        while(index!=head) {
            wanted[300+index].phase=(u16)phase;
            phase=(phase+((payload.b[24]&32)?-step:step))&65535;
            if(++index==count) index=0;
        }
    } else wantedPayload.b[32]=(payload.b[24]&0x17)?3:2;
    return 1;
}
'''
        # GCC diagnoses the deliberately retained retail stack lifetime even
        # though these native fixtures exclude paths that read an unset step.
        self.fixture += '\n#pragma GCC diagnostic push\n#pragma GCC diagnostic ignored "-Wmaybe-uninitialized"\n'
        self.fixture += screen.SELECTED + '\n#pragma GCC diagnostic pop\n' + r'''
static int check(int active,int index,int head,int count,int flags) {
    int i,result;
    for(i=0;i<256;i++) actor.b[i]=(u8)(i*17+0xA5);
    for(i=0;i<128;i++) payload.b[i]=(u8)(i*17+0xA5);
    for(i=0;i<560;i++) {records[i].x=i/8.0f;records[i].y=-i/4.0f;
        records[i].z=i/16.0f;records[i].velocityY=1.25f;records[i].phase=0xA5A5;records[i].reserved=0xA5A5;}
    *(GrowthRecord151488C4 **)(actor.b+148)=records+300;*(u8 **)(actor.b+152)=payload.b;
    actor.b[44]=(u8)active;actor.b[45]=(u8)index;actor.b[46]=(u8)head;actor.b[37]=(u8)count;
    payload.b[24]=(u8)flags;*(f32 *)(payload.b+4)=0.75f;*(f32 *)(payload.b+8)=1.5f;
    *(f32 *)(payload.b+12)=-0.25f;*(f32 *)(payload.b+16)=0.125f;
    *(f32 *)(actor.b+16)=9.0f;*(f32 *)(actor.b+20)=-3.0f;*(f32 *)(actor.b+24)=5.0f;
    D_800BE9A4=0.50000006f;wantedActor=actor;wantedPayload=payload;
    for(i=0;i<(int)sizeof(records);i++) ((u8 *)wanted)[i]=((u8 *)records)[i];
    result=expected();if(result!=1 || func_151488C4(actor.b)!=1) return 1;
    for(i=0;i<256;i++) if(actor.b[i]!=wantedActor.b[i]) return 2;
    for(i=0;i<128;i++) if(payload.b[i]!=wantedPayload.b[i]) return 3;
    for(i=0;i<(int)sizeof(records);i++) if(((u8 *)records)[i]!=((u8 *)wanted)[i]) return 4;
    return 0;
}
'''
        self.run_host(r'''
int count,head,active,flags;
for(count=2;count<128;count++) for(head=0;head<count;head++) for(flags=0;flags<2;flags++)
    if(check(1,0,head,count,flags?32:0)) return 1;
for(active=1;active<256;active++) for(flags=0;flags<256;flags++)
    if(check(active,0,2,5,flags)) return 2;
''')
        self.receipt('native', dict(cases=81534, actual_native32=True,
            canary_bytes=dict(actor=256, payload=128, records=11200),
            zero_active_uninitialized_step_and_cyclic_inputs_emitted_only=True))

    def test_08_actual_timer_dispatch_connection_and_table_identity(self):
        elf = self.root / 'conker/build/conker.us.elf'; base, data = load_section(elf, '.game_data')
        self.assertEqual(struct.unpack_from('>I', data, 0x8008A3E4 - base)[0], screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', data, 0x8008A204 - base)[0], dispatcher.screen.ENTRY)
        _, functions = timer.slot_records(self.root)
        outer, middle = functions[timer.screen.FUNCTION], functions[dispatcher.screen.FUNCTION]
        self.assertEqual((len(outer), len(middle)), (100, 97)); count = 0
        for active, flags, phase in itertools.product((0, 2, 4, 255), (0, 32, 2), (0, 8)):
            memory = fixture(active=active, flags=flags, phase=phase)
            for offset, value, size in ((0x1E, 0, 2), (0x2F, 1, 1), (0x30, 0, 1), (0x24, 255, 1)):
                put(memory, ACTOR + offset, value, size)
            for offset, value in ((0x20, 1), (0x21, 0), (0x22, 0)): put(memory, PAYLOAD + offset, value, 1)
            put(memory, 0x8008A204, dispatcher.screen.ENTRY); put(memory, 0x8008A3E4, screen.ENTRY)
            # The callers own 0x20/0x30-byte frames before this 0x10-byte leaf.
            ref = GrowthReference(memory, phase, stack=STACK + phase - 0x60)
            self.assertEqual(state(ref), 'returned')
            if signed(read(ref.memory, ACTOR + 44, 1)) > 0:
                for i in range(3): put(ref.memory, ACTOR + 0x54 + i * 4, read(ref.memory, RECORDS + i * 4))
            else:
                for i in range(3): put(ref.memory, ACTOR + 0x54 + i * 4, 0)
            models = []
            for leaf in (self.words, self.retail):
                connected = {dispatcher.screen.ENTRY + i * 4: w for i, w in enumerate(middle)}
                connected.update({screen.ENTRY + i * 4: w for i, w in enumerate(leaf)})
                model = GrowthOracle(outer, memory, phase, timer.screen.ENTRY, connected=connected).run()
                self.assertEqual(model.calls, [(dispatcher.screen.ENTRY, (ACTOR,)), (screen.ENTRY, (ACTOR,))])
                self.assertEqual(external(model.memory), external(ref.memory)); models.append(model)
            self.assertEqual((models[0].r, models[0].f, models[0].events, models[0].memory),
                (models[1].r, models[1].f, models[1].events, models[1].memory)); count += 1
        self.receipt('connected', dict(cases=count, executions=2 * count, words=[100, 97, 140],
            table_witnesses=['0x8008A204', '0x8008A3E4'], no_external_hooks=True,
            hardware_gameplay_and_other_callbacks_open=True))


if __name__ == '__main__':
    unittest.main()
