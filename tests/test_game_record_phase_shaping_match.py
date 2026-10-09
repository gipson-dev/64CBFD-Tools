"""Full signed-byte phase shaping, live aliases and actual dispatch connection."""

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
from tools.experiments import game_record_phase_shaping_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_actor_graphics_dispatch_match import DispatchOracle
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK
from tools.tests.test_game_record_callback_update_match import external, public
from tools.tests import test_game_actor_timer_callbacks_match as timer
from tools.tests import test_game_payload_callback_update_match as payload_update
from tools.tests import test_game_random_curve_record as native

SOURCE = 'conker/src/game/generated_175250.c'
ACTOR, PAYLOAD, RECORDS = 0x20000, 0x21000, 0x30000


def shapes(root):
    text = (root / SOURCE).read_text()
    old = text.replace(screen.SELECTED, screen.ORIGINAL).replace(screen.DECLARATIONS + '\n', '')
    assert old.count(screen.ORIGINAL) == 1
    return old, old.replace('/* Non-matching placeholders', screen.DECLARATIONS + '\n/* Non-matching placeholders', 1).replace(screen.ORIGINAL, screen.SELECTED)


def signed(value):
    value &= 255
    return value if value < 128 else value - 256


def fixture(active=5, start=0, head=3, count=5, flags=0):
    memory = {STACK + i: 0xA5 for i in range(-0x600, 0x140)}
    for base, size in ((ACTOR, 256), (PAYLOAD, 128), (RECORDS - 2800, 11600)):
        memory.update({base + i: (i * 17 + 0xA5) & 255 for i in range(size)})
    put(memory, ACTOR + 0x94, RECORDS); put(memory, ACTOR + 0x98, PAYLOAD)
    for offset, value in ((0x2C, active), (0x2D, start), (0x2E, head), (0x25, count)):
        put(memory, ACTOR + offset, value, 1)
    put(memory, PAYLOAD + 0x18, flags, 1)
    return memory


class LoopBound(Exception):
    pass


class PhaseReference:
    def __init__(self, memory, bound=260):
        self.memory, self.events = dict(memory), []
        self.bound, self.iterations, self.returned = bound, 0, None

    def get(self, address, size=4):
        address &= 0xFFFFFFFF
        assert address % size == 0, ('unaligned read', address, size)
        assert all(address + i in self.memory for i in range(size)), ('unmapped read', address, size)
        value = read(self.memory, address, size)
        self.events.append(('R', address, size, value))
        return value

    def put(self, address, value, size):
        address &= 0xFFFFFFFF
        assert address % size == 0, ('unaligned store', address, size)
        assert all(address + i in self.memory for i in range(size)), ('unmapped store', address, size)
        put(self.memory, address, value, size)
        self.events.append(('W', address, size, value & ((1 << (size * 8)) - 1)))

    def run(self):
        active = signed(self.get(ACTOR + 0x2C, 1))
        if active < 3:
            self.returned = 0
            return self
        self.put(ACTOR + 0x2C, active - 1, 1)
        divisor = signed(self.get(ACTOR + 0x2C, 1))
        payload = self.get(ACTOR + 0x98); records = self.get(ACTOR + 0x94)
        flags = self.get(payload + 0x18, 1)
        step = (4096 // divisor) & 65535
        index = signed(self.get(ACTOR + 0x2D, 1))
        phase = 4096 if flags & 0x20 else 0
        head = signed(self.get(ACTOR + 0x2E, 1))
        self.put(ACTOR + 0x2E, head - 1, 1)
        head = signed(self.get(ACTOR + 0x2E, 1))
        if head < 0:
            self.put(ACTOR + 0x2E, self.get(ACTOR + 0x25, 1) - 1, 1)
            head = signed(self.get(ACTOR + 0x2E, 1))
        while index != head:
            self.put(records + index * 20 + 0x10, phase, 2)
            self.iterations += 1
            flags = self.get(payload + 0x18, 1)
            phase = (phase - step if flags & 0x20 else phase + step) & 65535
            count = self.get(ACTOR + 0x25, 1)
            index += 1
            if index == count:
                index = 0
            head = signed(self.get(ACTOR + 0x2E, 1))
            if self.iterations >= self.bound:
                raise LoopBound()
        self.returned = 1
        return self


class PhaseOracle(DispatchOracle):
    def __init__(self, words, memory, phase=0, entry=screen.ENTRY, bound=260, connected=None):
        TriangleOracle.__init__(self, words, memory, arguments=(ACTOR,), phase=phase, entry=entry, connected=connected)
        self.bound, self.iterations = bound, 0

    def get(self, address, size):
        value = super().get(address, size)
        if address == ACTOR + 0x2E and size == 1 and self.iterations >= self.bound:
            raise LoopBound()
        return value

    def put(self, address, value, size):
        if self.recording:
            assert address % size == 0, ('unaligned store', address, size)
            assert all(address + i in self.memory for i in range(size)), ('unmapped store', address, size)
        super().put(address, value, size)
        if size == 2 and address != ACTOR + 0x1C:
            self.iterations += 1

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


class GameRecordPhaseShapingMatchTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-record-phase-shaping-test'
        cls.out.mkdir(exist_ok=True)
        cls.meta, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.retail = list(struct.unpack_from('>70I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.directory = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)
        if not (cls.out / 'baseline.json').exists():
            old, _ = shapes(cls.root)
            assert (cls.root / SOURCE).read_text() == old
            slots, _ = timer.slot_records(cls.root)
            before = json.loads((cls.root / 'conker/build/game-wrapped-record-step-test/after.json').read_text())
            assert slots == before['slots'] and len(slots) == 6058
            data = (cls.root / 'conker/build/conker.us.elf').read_bytes()
            (cls.out / 'before.elf').write_bytes(data)
            for name in ('retail_word_patches.us.csv', 'progress.csv'):
                (cls.out / ('before-' + name)).write_bytes((cls.root / 'conker' / name).read_bytes())
            (cls.out / 'baseline.json').write_text(json.dumps(dict(slots=slots,
                source_sha256=hashlib.sha256(old.encode()).hexdigest(), elf_sha256=hashlib.sha256(data).hexdigest()), indent=2) + '\n')

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, phase=0, bound=260, words=None, entry=screen.ENTRY):
        ref = PhaseReference(memory, bound)
        expected_state = state(ref)
        models = []
        for body in ((words,) if words is not None else (self.words, self.retail)):
            model = PhaseOracle(body, memory, phase, entry, bound)
            self.assertEqual(state(model), expected_state)
            self.assertEqual((external(model.memory), public(model.events), model.iterations),
                (external(ref.memory), ref.events, ref.iterations))
            if expected_state == 'returned': self.assertEqual(model.r[2], ref.returned)
            models.append(model)
        if words is None:
            self.assertEqual((models[0].r, models[0].f, models[0].lo, models[0].events, models[0].memory),
                (models[1].r, models[1].f, models[1].lo, models[1].events, models[1].memory))
        return expected_state, models

    def test_01_complete_direct_slot_profiles_and_no_guards_or_relocations(self):
        self.assertEqual((self.meta['body_words'], self.meta['frame'], self.meta['differences']), (70, 0, 0))
        self.assertEqual(self.words, self.retail)
        self.assertEqual((self.meta['diagnostics'], self.meta['pool_bytes'], self.meta['relocations']), ('', 0, {}))
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream:
            self.assertFalse(any(row['function'] == screen.FUNCTION for row in csv.DictReader(stream)))
        profiles = [screen.compile_candidate(self.root, self.out, 'profile-' + p, screen.SELECTED, p)[0] for p in screen.PROFILES]
        self.receipt('slot', dict(words=70, bytes=280, frame=0, guards=0, profiles=profiles))

    def test_02_all_byte_metadata_and_complete_reachable_stream(self):
        visited, count, bounded = set(), 0, 0
        for field, value, phase in itertools.product(('active', 'start', 'head', 'count', 'flags'), range(256), (0, 8)):
            kwargs = {}; kwargs[field] = value
            if field == 'count': kwargs['head'] = 0
            result, models = self.compare(fixture(**kwargs), phase)
            visited.update(models[0].visits); bounded += result != 'returned'; count += 1
        for active, start, head, total, flags in itertools.product((3, 4, 127), (0, 1, 128, 255),
                (0, 1, 128, 255), (0, 1, 5, 127, 128, 255), (0, 0x20)):
            result, models = self.compare(fixture(active, start, head, total, flags), bound=32)
            visited.update(models[0].visits); bounded += result != 'returned'; count += 1
        missing = set(range(screen.ENTRY, screen.ENTRY + 280, 4)) - visited
        self.assertEqual(missing, {screen.ENTRY + i * 4 for i in (17, 21, 22, 23, 54)})
        self.receipt('guest', dict(cases=count, executions=count * 2, bounded_prefixes=bounded,
            reachable_words=len(visited), unreachable_word_indices=[17, 21, 22, 23, 54],
            all_public_byte_patterns=True, complete_public_trace_and_return_agreement=True,
            raw_and_retail_full_state_agreement=True, no_production_iteration_limit=True))

    def test_03_lazy_gates_missing_bytes_and_bounded_loop_prefixes(self):
        for active in (0, 2, 128, 255):
            memory = {ACTOR + 0x2C: active}
            self.assertEqual(self.compare(memory)[0], 'returned')
        count = 0
        for kwargs in ({}, dict(head=0), dict(flags=0x20, start=255), dict(head=1)):
            memory = fixture(**kwargs)
            _, models = self.compare(memory)
            touched = {address + i for _, address, size, _ in public(models[0].events) for i in range(size)}
            for address in touched:
                missing = dict(memory); del missing[address]
                self.compare(missing); count += 1
        empty = fixture(head=1)
        for address in list(empty):
            if RECORDS - 2800 <= address < RECORDS + 8800: del empty[address]
        del empty[ACTOR + 0x25]
        self.assertEqual(self.compare(empty)[0], 'returned')
        prefixes = [dict(head=0, count=0), dict(head=128, count=5), dict(head=0, count=255), dict(start=127, head=0, count=0)]
        for kwargs in prefixes:
            self.assertEqual(self.compare(fixture(**kwargs), bound=12)[0], 'bounded-loop-prefix')
        self.receipt('faults', dict(missing_byte_pairs=count, lazy_inactive_only_active_byte=True,
            lazy_empty_record_contents_and_count=True, bounded_loop_cases=len(prefixes), observed_iterations=12,
            small_table_wrap_cycle_witnesses=[prefixes[1], prefixes[2]], zero_count_prefixes_not_infinite_loop_claims=True,
            emitted_order_not_portable_C_fault_guarantees=True))

    def test_04_live_public_aliases_and_captured_pointer_witnesses(self):
        count = 0
        for location, flags, phase in itertools.product((ACTOR + 0x24, ACTOR + 0x2E,
                ACTOR + 0x94, ACTOR + 0x98, PAYLOAD + 0x18), (0, 0x20), (0, 8)):
            memory = fixture(flags=flags)
            put(memory, ACTOR + 0x94, location - 0x10)
            self.compare(memory, phase, bound=12); count += 1
        for active, phase in itertools.product((5, 64, 127), (0, 8)):
            memory = fixture(active=active)
            put(memory, ACTOR + 0x98, ACTOR + 0x14)
            self.compare(memory, phase); count += 1
        self.receipt('aliases', dict(cases=count, executions=count * 2, captured_records_and_payload=True,
            live_flags_count_head_and_ordered_halfword_stores=True,
            emitted_streams_not_portable_partial_struct_or_private_alias_claims=True))

    def test_05_complete_forms_and_effective_semantic_negatives(self):
        negatives = {
            'unsigned-active': screen.SELECTED.replace('*(s8 *)(actor + 0x2C)', 'actor[0x2C]'),
            'unsigned-start': screen.SELECTED.replace('*(s8 *)(actor + 0x2D)', 'actor[0x2D]'),
            'signed-count': screen.SELECTED.replace('actor[0x25]', '*(s8 *)(actor + 0x25)'),
            'unsigned-head': screen.SELECTED.replace('*(s8 *)(actor + 0x2E)', 'actor[0x2E]'),
            'cached-flags': screen.SELECTED.replace('    u16 phase;', '    u16 phase;\n    u8 cached;').replace(
                '        phase = (payload[0x18] & 0x20)', '        cached = payload[0x18];\n        phase = (cached & 0x20)').replace(
                'if (payload[0x18] & 0x20)', 'if (cached & 0x20)'),
            'wrong-phase-direction': screen.SELECTED.replace('phase -= step;', 'phase += step;'),
            'wrong-divisor': screen.SELECTED.replace('0x1000 / *(s8 *)(actor + 0x2C)', '0x1000 / (*(s8 *)(actor + 0x2C) + 1)'),
        }
        alias = fixture(flags=0x20); put(alias, ACTOR + 0x94, PAYLOAD + 8)
        samples = [fixture(), fixture(active=255), fixture(start=255), fixture(count=255, head=0),
            fixture(flags=0x20), fixture(head=128, start=127), fixture(start=126, head=2, count=128), alias]
        records = []
        for name, body in [*screen.candidates(), *negatives.items()]:
            meta, words = screen.compile_candidate(self.root, self.out, 'form-' + name, body)
            changed, traces = 0, 0
            for memory in samples:
                ref, model = PhaseReference(memory, bound=12), PhaseOracle(words, memory, bound=12)
                expected, observed = state(ref), state(model)
                self.assertNotEqual(observed, 'fault', name)
                changed += (expected, external(ref.memory), ref.returned) != (observed, external(model.memory), model.r[2] if observed == 'returned' else None)
                traces += ref.events != public(model.events)
            self.assertEqual(bool(changed), name in negatives, name)
            records.append(dict(meta, semantic_differences=changed, public_trace_differences=traces))
        self.receipt('forms', dict(complete_forms=len(records), samples_per_form=len(samples),
            effective_negatives=list(negatives), records=records))

    def test_06_owner_postprocessing_neighbors_actual_padding_and_rebased_links(self):
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
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/175250.s',
            word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_175250')
        start = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('\n', assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), start)) + 1
        self.assertNotIn('.space', assembly[start:end])
        asm, obj = self.out / 'solo.s', self.out / 'solo.o'
        asm.write_text('.text\n.set noreorder\n' + assembly[start:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        self.assertEqual(parse_object(obj)[1][screen.FUNCTION]['size'], 280); self.assertEqual(parse_object(obj)[2], {})
        count = 0
        for variant, entry in enumerate((screen.ENTRY, 0x10007FFC, 0x80008000, 0x8FFF7FFC)):
            script, elf = self.out / ('rebase-%d.ld' % variant), self.out / ('rebase-%d.elf' % variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack_from('>70I', sections(elf)['.text'][1]))
            self.assertEqual(words, self.retail)
            for active, flags, head, phase in itertools.product((2, 3, 127, 128), (0, 0x20), (0, 128), (0, 8)):
                self.compare(fixture(active=active, flags=flags, head=head), phase, bound=16, words=words, entry=entry)
                count += 1
        self.receipt('owner', dict(neighbors=len(current) - 1, diagnostics=len(warnings[0]),
            pools_and_relative_relocations_unchanged=True, complete_asm_postprocessing=True,
            actual_padding_bytes=280, guards=0, independent_links=4, cases=count,
            no_global_or_call_relocations_to_rebase=True))

    def test_07_whole_ELF_identical_guards_unchanged_and_one_conversion_row(self):
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
        self.assertEqual((self.root / 'conker/retail_word_patches.us.csv').read_bytes(), (self.out / 'before-retail_word_patches.us.csv').read_bytes())
        with (self.root / 'conker/retail_word_patches.us.csv').open(newline='') as stream: guards = list(csv.DictReader(stream))
        self.receipt('linked', dict(installed=installed, symbols=len(slots), full_ELF_byte_identical=True,
            guards=len(guards), guards_byte_identical=True, conversion_changes=1 if installed else 0,
            elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest()))
        if installed: self.receipt('after', dict(slots=slots, guards=guards, progress=after))

    def test_08_actual_native32_all_head_count_pairs_and_full_canaries(self):
        self.fixture = r'''typedef unsigned char u8;typedef signed char s8;
typedef unsigned short u16;typedef unsigned int u32;typedef int s32;
''' + screen.DECLARATIONS + r'''
static union {u32 align;u8 b[256];} actor,wantedActor;
static union {u32 align;u8 b[128];} payload,wantedPayload;
static PhaseRecord15148DE0 records[580],wanted[580];
static int expected(void) {
    int active=(s8)wantedActor.b[0x2C],index,head,count,step,phase,iterations=0;
    if(active<3) return 0;
    wantedActor.b[0x2C]=(u8)(active-1);step=4096/(s8)wantedActor.b[0x2C];
    index=(s8)wantedActor.b[0x2D];phase=(wantedPayload.b[0x18]&32)?4096:0;
    wantedActor.b[0x2E]=(u8)((s8)wantedActor.b[0x2E]-1);
    if((s8)wantedActor.b[0x2E]<0) wantedActor.b[0x2E]=(u8)(wantedActor.b[0x25]-1);
    head=(s8)wantedActor.b[0x2E];count=wantedActor.b[0x25];
    while(index!=head) {
        wanted[140+index].phase=(u16)phase;
        phase=(phase+((wantedPayload.b[0x18]&32)?-step:step))&65535;
        if(++index==count) index=0;
        if(++iterations>400) return -1;
    }
    return 1;
}
''' + screen.SELECTED + r'''
static int check(int active,int index,int head,int count,int flags) {
    int i,result;
    for(i=0;i<256;i++) actor.b[i]=(u8)(i*17+0xA5);
    for(i=0;i<128;i++) payload.b[i]=(u8)(i*17+0xA5);
    for(i=0;i<(int)sizeof(records);i++) ((u8 *)records)[i]=(u8)(i*17+0xA5);
    *(PhaseRecord15148DE0 **)(actor.b+0x94)=records+140;*(u8 **)(actor.b+0x98)=payload.b;
    actor.b[0x2C]=(u8)active;actor.b[0x2D]=(u8)index;actor.b[0x2E]=(u8)head;
    actor.b[0x25]=(u8)count;payload.b[0x18]=(u8)flags;
    wantedActor=actor;wantedPayload=payload;
    for(i=0;i<(int)sizeof(records);i++) ((u8 *)wanted)[i]=((u8 *)records)[i];
    result=expected();if(result<0 || func_15148DE0(actor.b)!=result) return 1;
    for(i=0;i<256;i++) if(actor.b[i]!=wantedActor.b[i]) return 2;
    for(i=0;i<128;i++) if(payload.b[i]!=wantedPayload.b[i]) return 3;
    for(i=0;i<(int)sizeof(records);i++) if(((u8 *)records)[i]!=((u8 *)wanted)[i]) return 4;
    return 0;
}
'''
        self.run_host(r'''
int head,count,end,index,active,i,j;
for(head=0;head<256;head++) for(count=0;count<256;count++) {
    end=(s8)(head-1);if(end<0) end=(s8)(count-1);
    index=(end==-128 || (end==count && count))?end:end-1;
    active=3+(head+count)%125;
    if(check(active,index,head,count,(head+count)&255)) return 1;
}
for(active=0;active<256;active++) if(check(active,0,3,5,active)) return 2;
for(end=0;end<128;end++) for(i=0;i<2;i++) for(j=0;j<3;j++)
    if(check(j==0?3:j==1?4:127,0,end+1,255,i?32:0)) return 3;
''')
        self.receipt('native', dict(cases=65536 + 256 + 128 * 2 * 3, head_count_pairs=65536,
            all_active_byte_patterns=True, ascending_and_descending_phase=True, actual_32_bit_C=True,
            canary_bytes=dict(actor=256, payload=128, records=11600),
            cyclic_inputs_emitted_prefix_only_not_native_calls=True))

    def test_09_actual_timer_payload_leaf_connection_and_table_identity(self):
        elf = self.root / 'conker/build/conker.us.elf'; base, data = load_section(elf, '.game_data')
        self.assertEqual(struct.unpack_from('>I', data, 0x8008A3F0 - base)[0], screen.ENTRY)
        self.assertEqual(struct.unpack_from('>I', data, 0x8008A204 - base)[0], payload_update.screen.ENTRY)
        _, functions = timer.slot_records(self.root)
        outer, middle = functions[timer.screen.FUNCTION], functions[payload_update.screen.FUNCTION]
        self.assertEqual(len(outer), 100); self.assertEqual(len(middle), 97)
        count = 0
        for active, head, flags, phase in itertools.product((3, 5, 127), (1, 3), (0, 0x20), (0, 8)):
            memory = fixture(active=active, head=head, flags=flags)
            for offset, value, size in ((0x1E, 0, 2), (0x2F, 1, 1), (0x30, 0, 1), (0x24, 255, 1)):
                put(memory, ACTOR + offset, value, size)
            for offset, value in ((0x20, 4), (0x21, 0), (0x22, 0)):
                put(memory, PAYLOAD + offset, value, 1)
            put(memory, 0x8008A204, payload_update.screen.ENTRY); put(memory, 0x8008A3F0, screen.ENTRY)
            ref = PhaseReference(memory); self.assertEqual(state(ref), 'returned')
            for i in range(3): put(ref.memory, ACTOR + 0x54 + i * 4, read(ref.memory, RECORDS + i * 4))
            models = []
            for leaf in (self.words, self.retail):
                connected = {payload_update.screen.ENTRY + i * 4: w for i, w in enumerate(middle)}
                connected.update({screen.ENTRY + i * 4: w for i, w in enumerate(leaf)})
                model = PhaseOracle(outer, memory, phase, timer.screen.ENTRY, connected=connected).run()
                self.assertEqual(model.calls, [(payload_update.screen.ENTRY, (ACTOR,)), (screen.ENTRY, (ACTOR,))])
                self.assertEqual(external(model.memory), external(ref.memory))
                models.append(model)
            self.assertEqual((models[0].r, models[0].f, models[0].events, models[0].memory),
                (models[1].r, models[1].f, models[1].events, models[1].memory))
            count += 1
        self.receipt('connected', dict(cases=count, executions=count * 2, complete_words=[100, 97, 70],
            actual_table_witnesses=['0x8008A204', '0x8008A3F0'], no_external_callback_or_cleanup_hooks=True,
            success_path_only_other_callbacks_upstream_hardware_and_gameplay_open=True))


if __name__ == '__main__':
    unittest.main()
