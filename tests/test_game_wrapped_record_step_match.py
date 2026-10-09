"""Full wrapped integration, ordered float updates, aliases and nested dispatch."""

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
from tools.experiments import game_wrapped_record_step_candidates as screen
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
from tools.tests import test_game_actor_timer_callbacks_match as timer
from tools.tests import test_game_payload_callback_update_match as prior
from tools.tests import test_game_random_curve_record as native

SOURCE = 'conker/src/game/generated_175250.c'
ACTOR, PAYLOAD, RECORDS = 0x20000, 0x21000, 0x30000


def shapes(root):
    text = (root / SOURCE).read_text()
    old = text.replace(screen.SELECTED, screen.ORIGINAL).replace(screen.DECLARATIONS + '\n', '')
    assert old.count(screen.ORIGINAL) == 1
    return old, old.replace('/* Non-matching placeholders', screen.DECLARATIONS + '\n/* Non-matching placeholders', 1).replace(screen.ORIGINAL, screen.SELECTED)


def fixture(start=3, end=0, count=5, delta=0x3F000000, pattern=0, symbols=None):
    symbols = screen.SYMBOLS if symbols is None else symbols
    memory = {STACK + i: 0xA5 for i in range(-0x600, 0x140)}
    for base, size in ((ACTOR, 256), (PAYLOAD, 128), (RECORDS - 6000, 11200)):
        memory.update({base + i: 0xA5 for i in range(size)})
    put(memory, ACTOR + 0x94, RECORDS); put(memory, ACTOR + 0x98, PAYLOAD)
    for offset, value in ((0x2E, start), (0x2D, end), (0x25, count)):
        put(memory, ACTOR + offset, value, 1)
    for index in range(-300, 260):
        for axis, value in enumerate((index / 8., -index / 4., index / 16., 1.25, 123.5)):
            put(memory, RECORDS + index * 20 + axis * 4, bits(value + pattern / 32.))
    for offset, value in ((4, 0.75), (12, -0.25), (16, 0.125)):
        put(memory, PAYLOAD + offset, bits(value))
    put(memory, symbols['D_800BE9A4'], delta)
    return memory


class LoopBound(Exception):
    pass


class StepReference:
    def __init__(self, memory, symbols=None, bound=300):
        self.memory, self.events, self.calls = dict(memory), [], []
        self.symbols = screen.SYMBOLS if symbols is None else symbols
        self.bound, self.iterations, self.returned = bound, 0, None

    def get(self, address, size=4):
        address &= 0xFFFFFFFF
        assert address % size == 0, ('unaligned read', address, size)
        assert all(address + i in self.memory for i in range(size)), ('unmapped read', address, size)
        value = read(self.memory, address, size)
        self.events.append(('R', address, size, value))
        return value

    def put(self, address, value):
        address &= 0xFFFFFFFF
        assert address % 4 == 0, ('unaligned store', address, 4)
        assert all(address + i in self.memory for i in range(4)), ('unmapped store', address, 4)
        put(self.memory, address, value)
        self.events.append(('W', address, 4, value))

    def run(self):
        records = self.get(ACTOR + 0x94); payload = self.get(ACTOR + 0x98)
        index = timer.signed(self.get(ACTOR + 0x2E, 1), 8) - 1
        delta = self.symbols['D_800BE9A4']
        while True:
            if index < 0:
                index = self.get(ACTOR + 0x25, 1) - 1
            record = (records + index * 20) & 0xFFFFFFFF
            gravity = self.get(payload + 0x10); step = self.get(delta)
            product = bits(floating(gravity) * floating(step))
            vy = self.get(record + 12)
            next_vy = bits(floating(vy) - floating(product))
            x = self.get(record)
            self.put(record + 12, next_vy)
            step = self.get(delta); vx = self.get(payload + 4); vy = self.get(record + 12)
            next_x = bits(floating(x) + floating(bits(floating(vx) * floating(step))))
            y = self.get(record + 4)
            self.put(record, next_x)
            step = self.get(delta)
            next_y = bits(floating(y) + floating(bits(floating(vy) * floating(step))))
            z = self.get(record + 8)
            self.put(record + 4, next_y)
            step = self.get(delta); vz = self.get(payload + 12)
            next_z = bits(floating(z) + floating(bits(floating(vz) * floating(step))))
            self.put(record + 8, next_z)
            end = timer.signed(self.get(ACTOR + 0x2D, 1), 8)
            self.iterations += 1
            if self.iterations >= self.bound:
                raise LoopBound()
            if index == end:
                self.returned = 1
                return self
            index -= 1


class StepOracle(DispatchOracle):
    def __init__(self, words, memory, phase=0, entry=screen.ENTRY, bound=300, connected=None):
        TriangleOracle.__init__(self, words, memory, arguments=(ACTOR,), phase=phase, entry=entry, connected=connected)
        self.bound, self.iterations = bound, 0

    def execute(self, word):
        if word >> 26 == 0 and word & 63 == 38:
            rs, rt, rd = word >> 21 & 31, word >> 16 & 31, word >> 11 & 31
            self.r[rd] = (self.r[rs] ^ self.r[rt]) & 0xFFFFFFFF
            self.r[0] = 0
        else:
            super().execute(word)

    def get(self, address, size):
        value = super().get(address, size)
        if address == ACTOR + 0x2D and size == 1:
            self.iterations += 1
            if self.iterations >= self.bound:
                raise LoopBound()
        return value

    def record_call(self, target):
        self.calls.append((target, self.arguments(1)))

    def hook(self, target):
        raise AssertionError(('unexpected external call', target))


def state(model):
    try:
        model.run()
        return 'returned'
    except LoopBound:
        return 'bounded-loop-prefix'
    except AssertionError as error:
        assert isinstance(error.args[0], tuple) and error.args[0][0] in (
            'unmapped read', 'unmapped store', 'unaligned read', 'unaligned store'), error
        return 'fault'


class GameWrappedRecordStepMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-wrapped-record-step-test'
        cls.out.mkdir(exist_ok=True)
        cls.meta, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.words = screen.normalize(cls.raw)
        cls.retail = list(struct.unpack_from('>44I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.directory = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)
        if not (cls.out / 'baseline.json').exists():
            old, _ = shapes(cls.root)
            assert (cls.root / SOURCE).read_text() == old
            slots, _ = timer.slot_records(cls.root)
            before = json.loads((cls.root / 'conker/build/game-payload-callback-update-test/after.json').read_text())
            assert slots == before['slots'] and len(slots) == 6058
            data = (cls.root / 'conker/build/conker.us.elf').read_bytes()
            (cls.out / 'before.elf').write_bytes(data)
            for name in ('retail_word_patches.us.csv', 'progress.csv'):
                (cls.out / ('before-' + name)).write_bytes((cls.root / 'conker' / name).read_bytes())
            (cls.out / 'baseline.json').write_text(json.dumps(dict(slots=slots,
                source_sha256=hashlib.sha256(old.encode()).hexdigest(), elf_sha256=hashlib.sha256(data).hexdigest()), indent=2) + '\n')

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, phase=0, bound=300, words=None, entry=screen.ENTRY, symbols=None):
        ref = StepReference(memory, symbols, bound)
        expected_state = state(ref)
        models = []
        for body in ((words,) if words is not None else (self.raw, self.words, self.retail)):
            model = StepOracle(body, memory, phase, entry, bound)
            self.assertEqual(state(model), expected_state)
            self.assertEqual((external(model.memory), public(model.events), model.iterations),
                (external(ref.memory), ref.events, ref.iterations))
            if expected_state == 'returned': self.assertEqual(model.r[2], 1)
            models.append(model)
        if words is None:
            self.assertTrue(all((m.r, m.f, m.events, m.memory) == (models[0].r, models[0].f, models[0].events, models[0].memory) for m in models))
        return expected_state, models

    def test_01_complete_slot_single_commutative_guard_profiles_and_relocations(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (44, 0, 1))
        self.assertEqual(self.words, self.retail)
        self.assertEqual((self.meta['diagnostics'], self.meta['pool_bytes']), ('', 0))
        self.assertEqual({i for i, (a, b) in enumerate(zip(self.raw, self.words)) if a != b}, {16})
        stale = list(self.raw); stale[16] ^= 1
        with self.assertRaises(AssertionError): screen.normalize(stale)
        control = list(self.raw); control[1] ^= 1
        self.assertEqual(screen.normalize(control)[1], control[1])
        relocs = self.meta['relocations']
        self.assertEqual(dict(relocs), {0: [('R_MIPS_HI16', 'D_800BE9A4')], 16: [('R_MIPS_LO16', 'D_800BE9A4')]})
        profiles = [screen.compile_candidate(self.root, self.out, 'profile-' + p, screen.SELECTED, p)[0] for p in screen.PROFILES]
        self.receipt('slot', dict(words=44, bytes=176, frame=0, guards=1, profiles=profiles))

    def test_02_full_byte_metadata_float_samples_and_complete_loop(self):
        visited, count, bounded = set(), 0, 0
        for field, value, phase in itertools.product(('start', 'end', 'count'), range(256), (0, 8)):
            kwargs = dict(start=3, end=0, count=5); kwargs[field] = value
            if field == 'count': kwargs['start'] = 0
            result, models = self.compare(fixture(**kwargs), phase, bound=260)
            visited.update(models[1].visits); bounded += result != 'returned'; count += 1
        for delta, pattern, start, end, total in itertools.product(
                (0, 0x80000000, 0x3DCCCCCD, 0x3F800001, 0xBF000000), (0, 1, 7),
                (0, 1, 5, 0x80), (0, 1, 4), (5, 7)):
            result, models = self.compare(fixture(start, end, total, delta, pattern), bound=20)
            visited.update(models[1].visits); bounded += result != 'returned'; count += 1
        self.assertEqual(visited, set(range(screen.ENTRY, screen.ENTRY + 176, 4)))
        self.receipt('guest', dict(cases=count, executions=count * 3, bounded_prefixes=bounded,
            all_44_words_reached=True, all_metadata_bytes=True, complete_public_trace_agreement=True,
            normalized_and_raw_full_state_agree=True, finite_floats_and_signed_zero=True))

    def test_03_zero_count_cycles_and_missing_public_bytes(self):
        cyclical = [(0, 0, 0), (0, 128, 5), (255, 255, 255), (128, 127, 1)]
        for start, end, count in cyclical:
            result, _ = self.compare(fixture(start, end, count), bound=12)
            self.assertEqual(result, 'bounded-loop-prefix')
        self.assertEqual(self.compare(fixture(0, 255, 0))[0], 'returned')
        count = 0
        for start in (0, 1, 3):
            memory = fixture(start=start)
            _, models = self.compare(memory)
            touched = {address + i for _, address, size, _ in public(models[0].events) for i in range(size)}
            for address in touched:
                missing = dict(memory); del missing[address]
                self.compare(missing)
                count += 1
        lazy = fixture(start=1, end=0)
        del lazy[ACTOR + 0x25]
        self.compare(lazy)
        self.receipt('faults', dict(missing_byte_triples=count, cyclic_fixtures=len(cyclical), cycle_observation_iterations=12,
            zero_count_minus_one_record_preserved=True, fallback_count_lazy=True,
            emitted_order_not_portable_C_fault_or_hardware_acceptance=True))

    def test_04_complete_forms_effective_negatives_and_live_global_alias(self):
        alias = fixture(start=1, end=0)
        delta = screen.SYMBOLS['D_800BE9A4']
        for i in range(-16, 24): alias[delta + i] = 0
        for i, value in enumerate((2., 3., 4., 1.)):
            put(alias, delta - 12 + i * 4, bits(value))
        put(alias, ACTOR + 0x94, delta - 12)
        self.compare(alias)
        negatives = {
            'unsigned-head': screen.SELECTED.replace('*(s8 *)(actor + 0x2E)', 'actor[0x2E]'),
            'signed-count': screen.SELECTED.replace('actor[0x25]', '*(s8 *)(actor + 0x25)'),
            'unsigned-end': screen.SELECTED.replace('*(s8 *)(actor + 0x2D)', 'actor[0x2D]'),
            'cached-time': screen.SELECTED.replace('    MotionRecord15148AF4 *record;', '    MotionRecord15148AF4 *record;\n    f32 time = D_800BE9A4;').replace(' * D_800BE9A4;', ' * time;'),
            'pre-gravity-y': screen.SELECTED.replace('        record->velocityY -= *(f32 *)(payload + 0x10) * D_800BE9A4;', '').replace('        record->z +=', '        record->velocityY -= *(f32 *)(payload + 0x10) * D_800BE9A4;\n        record->z +='),
            'early-empty-exit': screen.SELECTED.replace('    do {', '    if (actor[0x25] == 0) { return 1; }\n    do {'),
        }
        samples = [fixture(), fixture(start=128, count=255), fixture(start=0, end=255, count=0),
            fixture(start=0, end=0, count=0), alias]
        records = []
        invalid = {'index-s8', 'index-u8', 'index-u32'}
        for name, body in [*screen.candidates(), *negatives.items()]:
            meta, words = screen.compile_candidate(self.root, self.out, 'form-' + name, body)
            changed, trace_changes = 0, 0
            for memory in samples:
                ref, model = StepReference(memory, bound=12), StepOracle(words, memory, bound=12)
                expected, observed = state(ref), state(model)
                self.assertNotEqual(observed, 'fault', name)
                changed += (expected, external(ref.memory)) != (observed, external(model.memory))
                trace_changes += ref.events != public(model.events)
            self.assertEqual(bool(changed), name in negatives or name in invalid, name)
            records.append(dict(meta, semantic_differences=changed, public_trace_differences=trace_changes))
        self.receipt('forms', dict(complete_forms=len(records), samples_per_form=len(samples),
            effective_negatives=[*negatives, *sorted(invalid)], live_global_alias=True, records=records))

    def test_05_owner_postprocessing_neighbors_padding_and_independent_links(self):
        objects, warnings = [], []
        for name, text in zip(('baseline', 'selected'), shapes(self.root)):
            obj, warning = compile_owner(self.root, self.out, text, 'owner-' + name)
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / ('owner-' + name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(obj.relative_to(self.root / 'conker')), '--assembler', 'mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
            objects.append(obj); warnings.append(warning)
        self.assertEqual(warnings[0], warnings[1])
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
        with (self.out / 'before-retail_word_patches.us.csv').open(newline='') as stream: rows = list(csv.DictReader(stream))
        guard_file = self.out / 'candidate-guards.csv'
        with guard_file.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows + screen.guard_rows())
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/175250.s', word_patches_path=guard_file, filename='generated_175250')
        start = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('\n', assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), start)) + 1
        self.assertNotIn('.space', assembly[start:end])
        asm, obj = self.out / 'solo.s', self.out / 'solo.o'
        asm.write_text('.text\n.set noreorder\n' + assembly[start:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        self.assertEqual(parse_object(obj)[1][screen.FUNCTION]['size'], 176)
        self.assertEqual(parse_object(obj)[2], self.meta['relocations'])
        count = 0
        for variant, (entry, delta) in enumerate(((screen.ENTRY, 0x800BE9A4), (0x10007FFC, 0x80007FFC),
                (0x80008000, 0x80008000), (0x8FFF7FFC, 0x8000FFF0))):
            symbols = dict(D_800BE9A4=delta)
            script, elf = self.out / ('rebase-%d.ld' % variant), self.out / ('rebase-%d.elf' % variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                '--defsym=D_800BE9A4=0x%X' % delta, '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack_from('>44I', sections(elf)['.text'][1]))
            if not variant: self.assertEqual(words, self.retail)
            for start, phase, sample in itertools.product((0, 1, 5, 128, 255), (0, 8), (0x3F000000, 0xBF000000)):
                self.compare(fixture(start=start, delta=sample, symbols=symbols), phase, words=words, entry=entry, symbols=symbols)
                count += 1
        self.receipt('owner', dict(neighbors=len(current) - 1, diagnostics=len(warnings[0]),
            pools_and_relative_relocations_unchanged=True, complete_asm_postprocessing=True,
            actual_padding_bytes=176, guards=1, independent_links=4, cases=count))

    def test_06_whole_ELF_identical_guards_append_and_one_conversion_row(self):
        baseline = json.loads((self.out / 'baseline.json').read_text())
        old, new = shapes(self.root)
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
        before = (self.out / 'before-retail_word_patches.us.csv').read_bytes()
        self.assertTrue((self.root / 'conker/retail_word_patches.us.csv').read_bytes().startswith(before))
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream: guards = list(csv.DictReader(stream))
        with (self.out / 'before-retail_word_patches.us.csv').open(newline='') as stream: old_guards = list(csv.DictReader(stream))
        self.assertEqual(guards, old_guards + (screen.guard_rows() if installed else []))
        self.receipt('linked', dict(installed=installed, symbols=len(slots), full_ELF_byte_identical=True,
            guards=len(guards), conversion_changes=1 if installed else 0, elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest()))
        if installed: self.receipt('after', dict(slots=slots, guards=guards, progress=after))

    def test_07_actual_native32_all_head_count_bytes_and_float_rounding(self):
        self.fixture = r'''typedef unsigned char u8;typedef signed char s8;
typedef unsigned int u32;typedef int s32;typedef float f32;
''' + screen.DECLARATIONS + r'''
static union { u32 align;u8 b[256]; } actor;
static union { u32 align;u8 b[128]; } payload;
static MotionRecord15148AF4 records[560],wanted[560];
f32 D_800BE9A4;
static u32 word(f32 x) {union {f32 f;u32 u;} q;q.f=x;return q.u;}
static f32 number(u32 x) {union {f32 f;u32 u;} q;q.u=x;return q.f;}
static int expected(int head,int end,int count) {
    int index=(s8)head-1,iterations=0;MotionRecord15148AF4 *p;volatile f32 product;
    do {
        if(index<0) index=count-1;
        p=wanted+300+index;
        product=*(f32 *)(payload.b+16)*D_800BE9A4;p->velocityY=p->velocityY-product;
        product=*(f32 *)(payload.b+4)*D_800BE9A4;p->x=p->x+product;
        product=p->velocityY*D_800BE9A4;p->y=p->y+product;
        product=*(f32 *)(payload.b+12)*D_800BE9A4;p->z=p->z+product;
        if(++iterations>300) return -1;
        if(index==(s8)end) return iterations;
        index--;
    } while(1);
}
''' + screen.SELECTED + r'''
static int check(int head,int end,int count,u32 delta) {
    int i,j,iterations;
    for(i=0;i<256;i++) actor.b[i]=(u8)(i*17+0xA5);
    for(i=0;i<128;i++) payload.b[i]=(u8)(i*17+0xA5);
    for(i=0;i<560;i++) {
        records[i].x=(f32)(i-300)/8.0f;records[i].y=number(0x3F800001u+(u32)(i%7));
        records[i].z=(f32)(i-300)/16.0f;records[i].velocityY=1.25f;records[i].reserved=123.5f;
        wanted[i]=records[i];
    }
    *(MotionRecord15148AF4 **)(actor.b+0x94)=records+300;*(u8 **)(actor.b+0x98)=payload.b;
    actor.b[0x2E]=(u8)head;actor.b[0x2D]=(u8)end;actor.b[0x25]=(u8)count;
    *(f32 *)(payload.b+4)=0.75f;*(f32 *)(payload.b+12)=-0.25f;*(f32 *)(payload.b+16)=0.125f;
    D_800BE9A4=number(delta);iterations=expected(head,end,count);
    if(iterations<1 || func_15148AF4(actor.b)!=1) return 1;
    for(i=0;i<560;i++) for(j=0;j<5;j++)
        if(word(((f32 *)(records+i))[j])!=word(((f32 *)(wanted+i))[j])) return 2;
    if(actor.b[0x2E]!=(u8)head || actor.b[0x2D]!=(u8)end || actor.b[0x25]!=(u8)count) return 3;
    return 0;
}
'''
        self.run_host(r'''
static u32 steps[]={0,0x80000000u,0x3DCCCCCDu,0x3F800001u,0xBF000000u};
int head,count,end,i;
for(head=0;head<256;head++) for(count=0;count<256;count++) {
    end=count?((count-1)&127):255;
    if(check(head,end,count,steps[(head+count)%5])) return 1;
}
for(end=0;end<128;end++) for(i=0;i<5;i++)
    if(check(0,end,255,steps[i])) return 2;
''')
        self.receipt('native', dict(cases=65536 + 128 * 5, head_count_combinations=65536,
            reachable_signed_endpoints=128, time_samples=5, record_canary_bytes=560 * 20,
            actual_32_bit_C=True, ordered_float32_products=True,
            cyclic_inputs_emitted_prefix_only_not_native_invocations=True,
            hardware_FCSR_NaN_payload_FTZ_and_interrupts_not_claimed=True))

    def test_08_actual_timer_payload_leaf_connection_and_table_identity(self):
        elf = self.root / 'conker/build/conker.us.elf'; base, data = load_section(elf, '.game_data')
        self.assertEqual(struct.unpack_from('>I', data, 0x8008A3E8 - base)[0], screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', data, 0x8008A204 - base)[0], prior.screen.ENTRY)
        _, functions = timer.slot_records(self.root)
        outer, middle = functions[timer.screen.FUNCTION], functions[prior.screen.FUNCTION]
        self.assertEqual(len(outer), 100); self.assertEqual(len(middle), 97)
        count = 0
        for head, end, total, phase in itertools.product((0, 1, 5, 128, 255), (0, 1), (5, 7), (0, 8)):
            memory = fixture(head, end, total)
            for offset, value, size in ((0x1E, 0, 2), (0x2F, 1, 1), (0x30, 0, 1), (0x24, 255, 1), (0x2C, 1, 1)):
                put(memory, ACTOR + offset, value, size)
            for offset, value in ((0x20, 2), (0x21, 0), (0x22, 0), (0x18, 0)):
                put(memory, PAYLOAD + offset, value, 1)
            put(memory, 0x8008A204, prior.screen.ENTRY); put(memory, 0x8008A3E8, screen.ENTRY)
            ref = StepReference(memory); self.assertEqual(state(ref), 'returned')
            for i in range(3): put(ref.memory, ACTOR + 0x54 + i * 4, read(ref.memory, RECORDS + end * 20 + i * 4))
            models = []
            for leaf in (self.raw, self.words, self.retail):
                connected = {prior.screen.ENTRY + i * 4: w for i, w in enumerate(middle)}
                connected.update({screen.ENTRY + i * 4: w for i, w in enumerate(leaf)})
                model = StepOracle(outer, memory, phase, timer.screen.ENTRY, connected=connected).run()
                self.assertEqual(model.calls, [(prior.screen.ENTRY, (ACTOR,)), (screen.ENTRY, (ACTOR,))])
                self.assertEqual(external(model.memory), external(ref.memory))
                models.append(model)
            self.assertTrue(all((m.r, m.f, m.events, m.memory) == (models[0].r, models[0].f, models[0].events, models[0].memory) for m in models))
            count += 1
        self.receipt('connected', dict(cases=count, executions=count * 3, complete_words=[100, 97, 44],
            actual_table_witnesses=['0x8008A204', '0x8008A3E8'], no_callback_or_cleanup_hooks_needed=True,
            upstream_dispatch_gameplay_and_hardware_not_executed=True))


if __name__ == '__main__':
    unittest.main()
