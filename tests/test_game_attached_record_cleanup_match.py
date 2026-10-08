"""Complete unlinker, unsigned flags, live slot aliases and actual wrapper."""

import csv
import itertools
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.experiments import game_attached_record_cleanup_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import test_game_random_curve_record as native
from tools.tests.game_owner_pool import assert_guard_history, normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_attachment_progress_match import ProgressReference
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK

SOURCE = 'conker/src/game/generated_204660.c'
OWNER, RECORD, NESTED, ALTERNATE = 0x20000, 0x21000, 0x24000, 0x25000
FLAGS = (0, 1, 2, 8, 0x7FFF, 0x8000, 0xFFFD, 0xFFFF)


def fixture(flags=0, layout=0, present=True, byte=0xA5, timer=0xA5A5):
    owner, record, nested = OWNER, RECORD, NESTED
    if layout == 1:
        record = owner
    elif layout == 2:
        nested = owner + 0x28
    elif layout in (3, 4):
        nested = record + (0x1C if layout == 3 else 0x30)
    elif layout == 5:
        owner, record = 0x80020000, 0x8001FFF8
    elif layout in (6, 7):
        owner = OWNER + (4 if layout == 6 else 0)
        record = owner + 0xC
    memory = {owner + i: 0xA5 for i in range(0x20, 0x40)}
    if not present:
        put(memory, owner + 0x28, 0)
        return memory, owner
    memory.update({record + i: 0xA5 for i in range(-16, 0xB0)})
    memory.update({NESTED + i: 0xA5 for i in range(-8, 12)})
    memory.update({ALTERNATE + i: 0xA5 for i in range(-8, 12)})
    if layout == 5:
        alternate_record = record & 0xFFFFFF
        memory.update({alternate_record + i: 0xA5 for i in range(-16, 0xB0)})
        put(memory, alternate_record + 0x98, ALTERNATE)
        put(memory, alternate_record + 0x1E, flags ^ 0xF001, 2)
    put(memory, record + 0x98, nested)
    put(memory, record + 0x30, byte, 1)
    put(memory, record + 0x1C, timer, 2)
    put(memory, record + 0x1E, flags, 2)
    put(memory, owner + 0x28, record)
    return memory, owner


class CleanupReference(ProgressReference):
    def get(self, address, size=4):
        address &= 0xFFFFFFFF
        assert address % size == 0, ('unaligned read', address, size)
        return super().get(address, size)

    def put(self, address, value, size=4):
        address &= 0xFFFFFFFF
        assert address % size == 0, ('unaligned store', address, size)
        value &= (1 << (size * 8)) - 1
        self.events.append(('W', address, size, value))
        assert all(address + i in self.memory for i in range(size)), ('unmapped store', address, size)
        put(self.memory, address, value, size)

    def run(self, owner):
        slot = owner + 0x28
        if not self.get(slot):
            return self
        record = self.get(slot)
        nested = self.get(record + 0x98)
        self.put(record + 0x30, 0, 1)
        for mask, value in ((0xFFFD, 0), (0xFFFF, 8), (0xFFFF, 1)):
            record = self.get(slot)
            self.put(record + 0x1E, (self.get(record + 0x1E, 2) & mask) | value, 2)
        record = self.get(slot)
        self.put(record + 0x1C, 20, 2)
        self.put(nested, 0)
        self.put(slot, 0)
        return self


class CleanupOracle(TriangleOracle):
    def get(self, address, size):
        assert address % size == 0, ('unaligned read', address, size)
        return super().get(address, size)

    def put(self, address, value, size):
        assert address % size == 0, ('unaligned store', address, size)
        super().put(address, value, size)

    def record_call(self, target):
        assert target == screen.ENTRY
        self.calls.append(self.r[4])


def outcome(model, owner=None):
    try:
        model.run() if owner is None else model.run(owner)
        return True
    except AssertionError as error:
        assert error.args and error.args[0][0] in ('unmapped read', 'unmapped store', 'unaligned read', 'unaligned store'), error
        return False


def public(memory):
    return {a: v for a, v in memory.items() if not STACK - 0x100 <= a < STACK + 0x100}


class GameAttachedRecordCleanupTests(unittest.TestCase):
    run_host = native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-attached-record-cleanup-test'
        cls.out.mkdir(exist_ok=True)
        cls.record, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.rom = (cls.root / 'conker/conker.us.bin').read_bytes()
        cls.retail = list(struct.unpack_from('>26I', cls.rom, screen.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)

    def receipt(self, name, data):
        (self.out / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')

    def compare(self, memory, owner=OWNER, phase=0, words=None, entry=screen.ENTRY):
        ref = CleanupReference(memory)
        completed = outcome(ref, owner)
        model = CleanupOracle(words if words is not None else self.words, memory, phase=phase,
                              entry=entry, arguments=(owner,))
        self.assertEqual(outcome(model), completed)
        self.assertEqual((model.memory, model.events), (ref.memory, ref.events))
        if entry == screen.ENTRY:
            retail = CleanupOracle(self.retail, memory, phase=phase, entry=entry, arguments=(owner,))
            self.assertEqual(outcome(retail), completed)
            self.assertEqual((model.r, model.f, model.events, model.memory),
                             (retail.r, retail.f, retail.events, retail.memory))
        if completed:
            self.assertEqual(model.r[2], (owner + 0x28) & 0xFFFFFFFF)
        return model, completed

    def test_01_direct_complete_slot_and_profiles(self):
        self.assertEqual((self.record['body_words'], self.record['frame'], self.record['differences']), (26, 0, 0))
        self.assertEqual((self.record['diagnostics'], self.record['pool_bytes'], self.record['relocations']), ('', 0, {}))
        self.assertEqual(self.words, self.retail)
        profiles = []
        for profile in ('o2g3', 'o2', 'o1g3', 'o1'):
            meta, _ = screen.compile_candidate(self.root, self.out, 'profile-' + profile, profile=profile)
            profiles.append(meta)
        self.assertEqual([(m['body_words'], m['frame'], m['differences']) for m in profiles],
                         [(26, 0, 0), (26, 0, 0), (36, 8, 36), (36, 8, 36)])
        self.receipt('slot', dict(words=26, bytes=104, frame=0, direct_words=26, guards=0,
            relocations=0, profiles=profiles, typed_void_interface=True, V0_observed_not_new_return_API=True))

    def test_02_all_flags_bytes_aliases_and_reached_words(self):
        count, seen, faults = 0, set(), 0
        for flags in range(65536):
            memory, owner = fixture(flags, timer=flags ^ 0xFFFF)
            model, completed = self.compare(memory, owner, (flags & 1) * 8)
            self.assertTrue(completed)
            seen.update(model.visits)
            count += 1
        for flags, layout, phase, present in itertools.product(FLAGS, range(8), (0, 8), (False, True)):
            memory, owner = fixture(flags, layout, present)
            model, completed = self.compare(memory, owner, phase)
            faults += not completed
            seen.update(model.visits)
            count += 1
        for byte, phase in itertools.product(range(256), (0, 8)):
            memory, owner = fixture(byte=byte)
            self.compare(memory, owner, phase)
            count += 1
        self.assertEqual(seen, set(range(screen.ENTRY, screen.ENTRY + 104, 4)))
        self.receipt('guest', dict(cases=count, all_65536_unsigned_flags_and_old_timer_patterns=True,
            all_clear_byte_patterns=True, alias_layouts=8, SP_phases=2, guest_alias_faults=faults,
            all_26_words_reached=True, complete_GP_FP_memory_trace_equality=True,
            pointer_representation_aliases_are_guest_not_portable_C_claims=True))

    def test_03_lazy_null_required_and_alias_fault_prefixes(self):
        count = 0
        for phase in (0, 8):
            memory = {}
            put(memory, OWNER + 0x28, 0)
            model, completed = self.compare(memory, phase=phase)
            self.assertTrue(completed)
            self.assertEqual(model.events, [('R', OWNER + 0x28, 4, 0)])
        for layout, phase in itertools.product(range(8), (0, 8)):
            memory, owner = fixture(layout=layout)
            ref = CleanupReference(memory)
            outcome(ref, owner)
            for address, size in dict.fromkeys((e[1], e[2]) for e in ref.events):
                broken = dict(memory)
                if address + size - 1 not in broken:
                    continue
                del broken[address + size - 1]
                _, completed = self.compare(broken, owner, phase)
                self.assertFalse(completed)
                count += 1
        memory, owner = fixture()
        put(memory, RECORD + 0x98, 0)
        _, completed = self.compare(memory, owner)
        self.assertFalse(completed)
        count += 1
        self.receipt('faults', dict(cases=count, lazy_null_cases=2, complete_fault_prefix_equality=True,
            guest_alignment_mapping_faults_not_portable_C_or_CP0_metadata=True))

    def test_04_actual_native32_C_all_flags_and_canaries(self):
        self.fixture = NATIVE_PREFIX + screen.SELECTED + '\n' + NATIVE_CHECK
        self.run_host('unsigned flags,layout,present; if(sizeof(void *)!=4 || sizeof(u16)!=2)return 10;\n'
            'for(flags=0;flags<65536;flags++)for(layout=0;layout<6;layout++)for(present=0;present<2;present++)\n'
            'if(check(flags,layout,present))return 11;')
        self.receipt('native', dict(executions=65536 * 6 * 2, layouts=6, null_nonnull=True,
            all_unsigned_flag_and_old_timer_patterns=True, actual_C_volatile_typed_call=True,
            full_512_byte_canaries=True, numeric_pointer_reference_independent=True,
            prepared_native32_byte_alias_not_universal_pointer_representation=True))

    def test_05_source_forms_and_effective_negatives(self):
        records, ordinary, negatives = [], 0, 0
        for name, body in screen.candidates():
            meta, words = screen.compile_candidate(self.root, self.out, 'control-' + name, body)
            records.append(meta)
            if name == 'return-slot-probe':
                continue
            state_equal, trace_equal = [], []
            for flags, layout, present in itertools.product(FLAGS, range(8), (False, True)):
                memory, owner = fixture(flags, layout, present)
                ref = CleanupReference(memory)
                expected = outcome(ref, owner)
                model = CleanupOracle(words, memory, entry=screen.ENTRY, arguments=(owner,))
                completed = outcome(model)
                state_equal.append((completed, model.memory) == (expected, ref.memory))
                trace_equal.append(model.events == ref.events)
            if name.startswith('negative-'):
                self.assertFalse(all(state_equal) and all(trace_equal), name)
                negatives += 1
            else:
                self.assertTrue(all(state_equal), name)
                ordinary += len(state_equal)
        self.receipt('controls', dict(forms=len(records), ordinary_executions=ordinary,
            effective_behavior_or_order_negatives=negatives, return_probe_measurement_only=True, measurements=records))

    def test_06_copied_owner_prototype_real_padder_and_independent_links(self):
        source = (self.root / SOURCE).read_text().replace(screen.SELECTED, screen.ORIGINAL).replace(screen.PROTOTYPE, screen.OLD_PROTOTYPE)
        self.assertEqual(source.count(screen.ORIGINAL), 1)
        selected = source.replace(screen.ORIGINAL, screen.SELECTED).replace(screen.OLD_PROTOTYPE, screen.PROTOTYPE)
        objects, diagnostics = [], []
        for name, body in (('baseline', source), ('selected', selected)):
            obj, warnings = compile_owner(self.root, self.out, body, 'owner-' + name)
            diagnostics.append(warnings)
            processed = self.out / ('owner-' + name + '-processed.o')
            processed.write_bytes(obj.read_bytes())
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / ('owner-' + name + '.c')).relative_to(self.root / 'conker')), '--post-process',
                str(processed.relative_to(self.root / 'conker')), '--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
            objects.append(processed)
        self.assertEqual(diagnostics[0], diagnostics[1])
        old, previous, old_rel = parse_object(objects[0])
        text, current, rel = parse_object(objects[1])
        self.assertEqual(current.keys(), previous.keys())
        for name, fn in current.items():
            if name == screen.FUNCTION:
                continue
            before = previous[name]
            self.assertEqual(text[fn['value']:fn['value'] + fn['size']], old[before['value']:before['value'] + before['size']], name)
            self.assertEqual({o - fn['value']: r for o, r in rel.items() if fn['value'] <= o < fn['value'] + fn['size']},
                             {o - before['value']: r for o, r in old_rel.items() if before['value'] <= o < before['value'] + before['size']}, name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        target = current[screen.FUNCTION]
        isolated, _, isolated_rel = parse_object(self.out / 'selected.o')
        self.assertEqual(text[target['value']:target['value'] + 104], isolated[:104])
        self.assertEqual(isolated_rel, {})
        self.assertEqual({o: r for o, r in rel.items() if target['value'] <= o < target['value'] + 104}, {})
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/204660.s',
            word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_204660')
        start = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), start)
        end = assembly.index('\n', end) + 1
        self.assertNotIn('.space', assembly[end:assembly.find('.type ', end)])
        asm, obj = self.out / 'padded.s', self.out / 'padded.o'
        asm.write_text('.text\n.set noreorder\n.globl %s\n' % screen.FUNCTION + assembly[start:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        _, functions, relocations = parse_object(obj)
        self.assertEqual((functions[screen.FUNCTION]['size'], relocations), (104, {}))
        count = 0
        for index, entry in enumerate((screen.ENTRY, screen.ENTRY - 0x100004, 0x80000000, 0x8FFF7FFC, 0x10007FFC, 0x7FFF8000)):
            script, elf = self.out / 'padded.ld', self.out / ('rebased-%d.elf' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                '-o', str(elf), str(obj)], check=True, capture_output=True)
            words = list(struct.unpack_from('>26I', sections(elf)['.text'][1]))
            self.assertEqual(words, self.retail)
            for flags, layout, phase in itertools.product(FLAGS, range(8), (0, 8)):
                memory, owner = fixture(flags, layout)
                self.compare(memory, owner, phase, words, entry)
                count += 1
        self.receipt('owner-padder', dict(neighbors=len(current) - 1, unchanged_warning_count=len(diagnostics[0]),
            pools_relative_relocations_and_wrapper_unchanged=True, typed_prototype_qualified=True,
            padded_bytes=104, guards=0, relocations=0, independent_links=6, executions=count))

    def test_07_actual_complete_wrapper_connection(self):
        wrapper = list(struct.unpack_from('>8I', self.rom, 0x2048B4))
        count = 0
        for flags, layout, phase, present in itertools.product(FLAGS, range(7), (0, 8), (False, True)):
            memory, owner = fixture(flags, layout, present)
            memory.update({STACK + i: 0xA5 for i in range(-0x100, 0x100)})
            ref = CleanupReference(memory)
            self.assertTrue(outcome(ref, owner))
            models = []
            for words in (self.words, self.retail):
                connected = dict(zip(range(screen.ENTRY, screen.ENTRY + 104, 4), words))
                model = CleanupOracle(wrapper, memory, phase=phase, entry=0x151D7404,
                                      arguments=(owner,), connected=connected).run()
                self.assertEqual((model.calls, public(model.memory), model.r[2]), ([owner], public(ref.memory), owner + 0x28))
                self.assertEqual([e for e in model.events if not STACK - 0x100 <= e[1] < STACK + 0x100], ref.events)
                models.append(model)
            self.assertEqual((models[0].r, models[0].f, models[0].events, models[0].memory),
                             (models[1].r, models[1].f, models[1].events, models[1].memory))
            count += 1
        self.receipt('connected', dict(cases=count, actual_wrapper_words=8, complete_wrapper_and_epilogue=True,
            V0_survives_but_callers_do_not_consume_return=True, full_float_gate_caller_hardware_gameplay_not_qualified=True))

    def test_08_current_linked_slot_and_unchanged_guard_history(self):
        functions, _, addresses = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
        self.assertEqual((addresses[screen.FUNCTION], functions[screen.FUNCTION]), (screen.ENTRY, self.retail))
        self.assertEqual(functions['func_151D7404'], list(struct.unpack_from('>8I', self.rom, 0x2048B4)))
        source = (self.root / SOURCE).read_text()
        installed = screen.SELECTED in source
        self.assertEqual(source.count(screen.SELECTED if installed else screen.ORIGINAL), 1)
        self.assertEqual(source.count(screen.PROTOTYPE if installed else screen.OLD_PROTOTYPE), 1)
        with (self.root / 'conker/retail_word_patches.us.csv').open() as stream:
            guards = list(csv.DictReader(stream))
        assert_guard_history(self, guards)
        self.assertIn(len(guards), (11155, 11168, 11205))
        self.receipt('installed', dict(complete_linked_target_and_wrapper_exact=True, guards_added=0,
            complete_guard_history_checked=True, guard_rows=len(guards), hardware_gameplay_not_qualified=True))


NATIVE_PREFIX = r'''
typedef unsigned char u8;typedef unsigned short u16;typedef int s32;typedef unsigned int u32;
#define NULL ((void *)0)
static u8 arena[512] __attribute__((aligned(256)));
static u8 expected[512] __attribute__((aligned(4)));
static u32 eword(unsigned offset){return *(u32 *)(expected+offset);}
static unsigned offset(u32 pointer){return pointer-(u32)arena;}
'''

NATIVE_CHECK = r'''
static int check(u32 flags,unsigned layout,int present){
 unsigned i,slot,p,nested;u8 *owner=arena+0x38,*record=arena+0x100;u32 *link=(u32 *)(arena+0x1E0);
 void (*volatile invoke)(u8 *)=func_151D77C8;
 for(i=0;i<512;i++)arena[i]=(u8)(i*17+0xA5);
 if(layout==1)record=owner;
 if(layout==2)link=(u32 *)(owner+0x28);
 if(layout==3)link=(u32 *)(record+0x1C);
 if(layout==4)link=(u32 *)(record+0x30);
 if(layout==5){record=owner-8;*(u32 **)(arena+0x98)=(u32 *)(arena+0x1D0);}
 *(u32 **)(record+0x98)=link;
 record[0x30]=(u8)flags;
 *(u16 *)(record+0x1C)=(u16)(flags^0xFFFF);
 *(u16 *)(record+0x1E)=(u16)flags;
 *(u8 **)(owner+0x28)=present?record:NULL;
 for(i=0;i<512;i++)expected[i]=arena[i];
 slot=offset((u32)owner)+0x28;
 if(eword(slot)){
   p=offset(eword(slot));nested=offset(eword(p+0x98));
   if(p+0x98>=512||nested>508)return 1;
   expected[p+0x30]=0;
   for(i=0;i<3;i++){
     u16 v;p=offset(eword(slot));if(p>0x180)return 2;
     v=*(u16 *)(expected+p+0x1E);
     if(i==0)v&=0xFFFD;else v|=(i==1?8:1);
     *(u16 *)(expected+p+0x1E)=v;
   }
   p=offset(eword(slot));*(u16 *)(expected+p+0x1C)=20;
   *(u32 *)(expected+nested)=0;*(u32 *)(expected+slot)=0;
 }
 invoke(owner);
 for(i=0;i<512;i++)if(arena[i]!=expected[i])return 3;
 return 0;
}
'''
