"""Delayed effect gates, callback lifetime, ABI and unchanged owner layout."""

import csv
import itertools
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.experiments import game_node_delayed_effect_candidates as screen
from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import test_game_node_action_match as action
from tools.tests import test_game_node_effect_registration_match as effect
from tools.tests import test_game_matrix_pair_resolver_recovery as prior
from tools.tests.game_animation_timeline_oracle import bits, signed
from tools.tests.game_owner_pool import assert_guard_history, normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put

NODE, ACTOR = 0x10000, 0x20000
FLAG, STEP = screen.SYMBOLS['D_800BE616'], screen.SYMBOLS['D_800BE9E4']
NEAR, CREATE, CALLBACK = (screen.SYMBOLS[n] for n in ('func_1508B20C', 'func_1000FA64', 'func_15033BDC'))
STATES = (0, 1, 0x100, 0x513, 0x80000000, 0xFFFFFFFF)
TIMERS = (0, 1, 28, 29, 30, 31, 0x7FFFFFFF, 0x80000000, 0xFFFFFFE2, 0xFFFFFFFF)
STEPS = (0, 1, 2, 31, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF)


def fixture(flag=0, state=0, timer=30, step=1, coordinates=(bits(1.75), bits(-2.75), bits(32767.75))):
    memory = {prior.STACK+i: 0xA5 for i in range(-0x100, 0x100)}
    for base in (NODE, ACTOR):
        memory.update({base+i: 0xA5 for i in range(0x40)})
    put(memory, FLAG, flag, 1)
    put(memory, STEP, step)
    put(memory, NODE+0x38, state)
    put(memory, NODE+0x3C, timer)
    for axis, value in enumerate(coordinates):
        put(memory, ACTOR+0x14+axis*4, value)
    return memory


def mutations(target, mode, node, actor, stack):
    if target == NEAR:
        return {0: [], 1: [(node+0x38, 1, 4)],
            2: [(node+0x38, 0, 4), (node+0x3C, 29, 4), (STEP, 7, 4)],
            3: [(node+0x38, 0, 4), (node+0x3C, 30, 4), (actor+0x14, bits(-17.75), 4)],
            4: [(stack, 0, 4), (stack+4, 0, 4)], 5: [],
            6: [(FLAG, 0, 1), (node+0x38, 0, 4), (node+0x3C, 0x80000000, 4), (STEP, 0xFFFFFFFF, 4)]}[mode]
    if target == CREATE and mode == 5:
        return [(node+0x38, 0xDEADBEEF, 4), (node+0x3C, 0x76543210, 4),
            (stack, 0, 4), (stack+4, 0, 4)]
    return []


class DelayedReference(action.ActionReference):
    def call(self, target, arguments, node, actor):
        self.calls.append((target, *arguments))
        self.observed.append((target, self.get(node+0x38), self.get(node+0x3C)))
        for address, value, size in mutations(target, self.mode, node, actor, self.stack):
            self.put(address, value, size)
        return self.result if target == CREATE else 0xBEEF1234

    def run(self, node=NODE, actor=ACTOR, result=0):
        self.result, self.observed = result, []
        if self.get(FLAG, 1):
            xyz = tuple(self.get(actor+0x14+i*4) for i in range(3))
            self.call(NEAR, (*xyz, bits(900)), node, actor)
        if self.get(node+0x38) == 0:
            timer = self.get(node+0x3C)
            if signed(timer) < 30:
                self.put(node+0x3C, timer+self.get(STEP))
            else:
                xyz = tuple(effect.narrowed(self.get(actor+0x14+i*4)) for i in range(3))
                handle = self.call(CREATE, (0x513, *xyz, 32000, 1000, 500, CALLBACK, node, actor, 0, 0), node, actor)
                self.put(node+0x3C, handle)
                self.put(node+0x38, 0x513)
        return 0


class DelayedOracle(TriangleOracle):
    def __init__(self, words, memory, args=(NODE, ACTOR), phase=0, mode=0, result=0):
        super().__init__(words, memory, entry=screen.ENTRY, arguments=args, phase=phase)
        self.node, self.actor = args
        self.mode, self.result, self.observed = mode, result, []
        self.stack = prior.STACK+phase

    def record_call(self, target):
        self.assert_target(target)
        arguments = (self.f[12], self.f[14], self.r[6], self.r[7]) if target == NEAR else self.arguments(12)
        self.calls.append((target, *arguments))

    @staticmethod
    def assert_target(target):
        assert target in (NEAR, CREATE), ('unexpected call', target)

    def hook(self, target):
        self.observed.append((target, self.get(self.node+0x38, 4), self.get(self.node+0x3C, 4)))
        for address, value, size in mutations(target, self.mode, self.node, self.actor, self.stack):
            self.put(address, value, size)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000+register
        self.r[2] = self.result if target == CREATE else 0xBEEF1234
        self.f[:20] = [0xA5000000+i for i in range(20)]


class GameNodeDelayedEffectMatchTests(unittest.TestCase):
    run_host = prior.GameMatrixPairResolverRecoveryTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-node-delayed-effect-test'
        cls.out.mkdir(exist_ok=True)
        cls.record, cls.words = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.retail = list(struct.unpack_from('>65I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)

    def receipt(self, name, value):
        (self.out / (name+'.json')).write_text(json.dumps(value, indent=2)+'\n')

    def compare(self, memory, args=(NODE, ACTOR), phase=0, mode=0, result=0):
        reference = DelayedReference(memory, phase, mode)
        expected = reference.run(*args, result)
        models = [DelayedOracle(body, memory, args, phase, mode, result).run() for body in (self.words, self.retail)]
        for model in models:
            self.assertEqual((model.r[2], model.calls, model.observed, prior.public(model.events), prior.external_memory(model.memory)),
                (expected, reference.calls, reference.observed, prior.public(reference.events), prior.external_memory(reference.memory)))
        self.assertEqual((models[0].r, models[0].f, models[0].events, models[0].memory),
            (models[1].r, models[1].f, models[1].events, models[1].memory))
        return models

    def test_01_direct_slot_and_relocations(self):
        self.assertEqual((self.record['body_words'], self.record['frame'], self.record['differences'],
            self.record['pool_bytes'], self.record['diagnostics']), (65, 64, 0, 0, ''))
        self.assertEqual(self.words, self.retail)
        relocations = [r for entries in self.record['relocations'].values() for r in entries]
        self.assertEqual({symbol for _, symbol in relocations}, set(screen.SYMBOLS))
        self.assertEqual([sum(k == kind for k, _ in relocations) for kind in ('R_MIPS_26', 'R_MIPS_HI16', 'R_MIPS_LO16')], [2, 3, 3])
        self.receipt('slot', dict(words=65, bytes=260, frame=64, differences=0, guards=0, padding=0, generated_data=0,
            calls=2, HI_LO_pairs=3))

    def test_02_global_threshold_wrap_results_mutations_and_coordinates(self):
        seen, counts = set(), [0, 0, 0, 0]
        groups = (
            ((fixture(flag, state, timer), phase, 0, 0xFFFF) for flag, state, timer, phase in
                itertools.product(range(256), (0, 0x100, 0x80000000), (29, 30), (0, 8))),
            ((fixture(flag, state, timer, step), phase, 0, 0x1234) for flag, state, timer, step, phase in
                itertools.product((0, 255), STATES, TIMERS, STEPS, (0, 8))),
            ((fixture(flag, state, timer), phase, mode, result) for flag, state, timer, result, mode, phase in
                itertools.product((0, 1), (0, 0x100, 0xFFFFFFFF), (29, 30, 0x80000000), effect.RESULTS, range(7), (0, 8))),
            ((fixture(coordinates=xyz), 0, 0, 0x1234) for xyz in itertools.product(effect.COORDINATES, repeat=3)))
        for group, cases in enumerate(groups):
            for memory, phase, mode, result in cases:
                for model in self.compare(memory, phase=phase, mode=mode, result=result):
                    seen.update(model.visits)
                counts[group] += 1
        missing = sorted((pc-screen.ENTRY)//4 for pc in set(range(screen.ENTRY, screen.ENTRY+260, 4))-seen)
        self.assertEqual(missing, [])
        self.receipt('guest', dict(cases=sum(counts), global_cases=counts[0], lifecycle_cases=counts[1],
            callback_cases=counts[2], coordinate_cases=counts[3], flag_bytes=256, state_patterns=len(STATES),
            timers=len(TIMERS), steps=len(STEPS), mutation_modes=7, results=6, SP_phases=2,
            missing_word_indices=missing, signed_timer_and_guest_modular_add=True,
            independent_public_reference_and_full_C_retail_GP_FP_trace_memory_equal=True,
            invalid_FP_FCSR_and_complete_callees_not_claimed=True))

    def test_03_lazy_reads_fault_prefixes_and_aliases(self):
        lazy = []
        memory = fixture(state=1)
        del memory[NODE+0x3C], memory[STEP], memory[ACTOR+0x14]
        lazy.append((memory, (NODE, 0)))
        memory = fixture(timer=29)
        del memory[ACTOR+0x14]
        lazy.append((memory, (NODE, 0)))
        memory = fixture(timer=30)
        del memory[STEP]
        lazy.append((memory, (NODE, ACTOR)))
        memory = fixture(flag=1, state=1)
        del memory[STEP]
        lazy.append((memory, (NODE, ACTOR)))
        for memory, args in lazy:
            self.compare(memory, args)
        probes = [(fixture(), (0, ACTOR), None), (fixture(), (NODE, 0), None)]
        for flag, timer, missing in ((0, 29, FLAG), (0, 29, NODE+0x38), (0, 29, NODE+0x3C),
                (0, 29, STEP), *((flag, 30, ACTOR+0x14+i*4) for flag in (0, 1) for i in range(3))):
            memory = fixture(flag=flag, timer=timer)
            del memory[missing]
            probes.append((memory, (NODE, ACTOR), missing))
        for memory, args, _ in probes:
            reference = DelayedReference(memory)
            with self.assertRaises(AssertionError) as failure:
                reference.run(*args)
            for words in (self.words, self.retail):
                model = DelayedOracle(words, memory, args)
                with self.assertRaises(AssertionError) as actual:
                    model.run()
                self.assertEqual(actual.exception.args, failure.exception.args)
                self.assertEqual((model.calls, prior.public(model.events), prior.external_memory(model.memory)),
                    (reference.calls, prior.public(reference.events), prior.external_memory(reference.memory)))
        aliases = []
        memory = fixture()
        for i, value in enumerate((bits(-1.75), bits(2.75), bits(17.5))):
            put(memory, NODE+0x14+i*4, value)
        aliases.append((memory, (NODE, NODE)))
        memory = fixture()
        put(memory, STEP-4, 0)
        put(memory, STEP, 29)
        aliases.append((memory, (STEP-0x3C, ACTOR)))
        for memory, args in aliases:
            self.compare(memory, args)
        self.receipt('gates', dict(lazy_cases=len(lazy), fault_prefixes=len(probes), aliases=len(aliases),
            flag_read_before_state_and_callback_changes_observed=True, arbitrary_private_aliases_not_claimed=True))

    def test_04_source_profiles_and_effective_negatives(self):
        records, ordinary, negatives = [], 0, 0
        forms = [(name, body, 'o2g3') for name, body in screen.candidates()]
        forms += [('profile-'+p, screen.SELECTED, p) for p in PROFILES if p != 'o2g3']
        memories = [fixture(flag, state, timer, step) for flag, state, timer, step in (
            (0, 0, 30, 7), (1, 0, 30, 7), (0, 0, 29, 7), (0, 0, 0xFFFFFFFF, 7), (0, 0x100, 30, 7))]
        for name, body, profile in forms:
            record, words = screen.compile_candidate(self.root, self.out, name, body, profile)
            records.append(record)
            caught = False
            for memory in memories:
                reference = DelayedReference(memory)
                expected = reference.run(result=0x1234)
                model = DelayedOracle(words, memory, result=0x1234).run()
                observed = (model.r[2], model.calls, model.observed, prior.external_memory(model.memory))
                required = (expected, reference.calls, reference.observed, prior.external_memory(reference.memory))
                if name.startswith('negative-'):
                    caught |= observed != required
                else:
                    self.assertEqual(observed, required, name)
                    ordinary += 1
            if name.startswith('negative-'):
                self.assertTrue(caught, name)
                negatives += 1
        self.receipt('controls', dict(forms=len(records), ordinary_executions=ordinary, effective_negatives=negatives,
            measurements=records, ordinary_defined_float_to_s16_range_only=True, alternate_private_traces_not_claimed=True))

    def test_05_native32_complete_C_all_results_coordinates_and_canaries(self):
        self.fixture = r'''typedef unsigned char u8;typedef unsigned short u16;typedef short s16;
typedef int s32;typedef unsigned int u32;typedef float f32;
typedef union __attribute__((aligned(8))) {u32 align;u8 b[0x40];} Storage;
typedef char widths[(sizeof(void *)==4&&sizeof(s16)==2&&sizeof(f32)==4&&sizeof(s32)==4)?1:-1];
static Storage node,actor;u8 D_800BE616;s32 D_800BE9E4;
static u16 result;static int scenario,count,error;static int calls[2];
static s16 xyz[3];static u8 seen_results[65536],seen_coordinates[65536];
s32 func_15033BDC(){return 0;}
void func_1508B20C(f32 x,f32 y,f32 z,f32 radius){calls[count++]=1;
    if(x!=*(f32 *)(actor.b+0x14)||y!=*(f32 *)(actor.b+0x18)||z!=*(f32 *)(actor.b+0x1C)||radius!=900.0f)error=1;
    if(scenario==6)*(s32 *)(node.b+0x38)=1;
    if(scenario==7){*(s32 *)(node.b+0x38)=0;*(s32 *)(node.b+0x3C)=30;
        *(f32 *)(actor.b+0x14)=-17.75f;xyz[0]=-17;}
}
u16 func_1000FA64(u16 effect,s16 x,s16 y,s16 z,s32 amount,u16 rate,s16 limit,s32 callback,
    void *n,s32 a,s32 extra,s32 tail){calls[count++]=2;
    if(effect!=0x513||x!=xyz[0]||y!=xyz[1]||z!=xyz[2]||amount!=32000||rate!=1000||limit!=500||
        callback!=(s32)func_15033BDC||n!=node.b||a!=(s32)actor.b||extra||tail)error=2;
    seen_results[result]=1;seen_coordinates[(u16)x]=1;
    *(s32 *)(node.b+0x38)=123;*(s32 *)(node.b+0x3C)=456;return result;
}
''' + screen.SELECTED
        self.run_host(r'''
Storage old_node,old_actor;int v,i,state,timer,near,create;f32 value;
for(v=0;v<65536;v++)for(scenario=0;scenario<8;scenario++){
    for(i=0;i<0x40;i++)node.b[i]=actor.b[i]=0xA5;
    xyz[0]=(s16)(v-32768);xyz[1]=(s16)(32767-v);xyz[2]=17;
    for(i=0;i<3;i++){value=(f32)xyz[i]+(xyz[i]<0?-0.25f:0.25f);*(f32 *)(actor.b+0x14+i*4)=value;}
    near=scenario&1;D_800BE616=near?255:0;D_800BE9E4=7;
    state=(scenario==2||scenario==3||scenario==7)?0x100:0;
    timer=scenario<4?29:30;if(scenario==7)timer=-1;
    if(scenario==6){near=1;D_800BE616=1;}
    *(s32 *)(node.b+0x38)=state;*(s32 *)(node.b+0x3C)=timer;
    result=(u16)v;count=error=0;old_node=node;old_actor=actor;
    if(scenario==6)state=1;
    if(scenario==7){state=0;timer=30;*(f32 *)(old_actor.b+0x14)=-17.75f;}
    create=state==0&&timer>=30;
    if(func_15033AD8(node.b,actor.b)!=0||error||count!=near+create)return 1;
    if(near&&calls[0]!=1)return 2;
    if(create&&calls[near]!=2)return 3;
    if(create){timer=result;state=0x513;}else if(state==0)timer+=7;
    *(s32 *)(old_node.b+0x38)=state;*(s32 *)(old_node.b+0x3C)=timer;
    for(i=0;i<0x40;i++)if(node.b[i]!=old_node.b[i]||actor.b[i]!=old_actor.b[i])return 4;
}
for(v=0;v<65536;v++)if(!seen_results[v]||!seen_coordinates[v])return 5;
''')
        self.receipt('native', dict(cases=524288, pointer_bytes=4, actual_complete_C=True,
            all_u16_results_observed=65536, all_signed16_X_observed=65536, canaries_and_ABI_checked=True,
            signed_overflow_and_out_of_s16_native_conversion_not_claimed=True, axes_correlated=True,
            proximity_and_allocator_are_controlled_hooks=True))

    def test_06_copied_owner_padder_and_independent_relocations(self):
        source = (self.root / 'conker/src/game/generated_5D2C0.c').read_text()
        if screen.SELECTED in source:
            source = source.replace(screen.SELECTED, screen.STUB).replace(screen.ADDED_DECLARATIONS, '', 1)
        self.assertEqual(source.count(screen.STUB), 1)
        selected = source.replace(screen.STUB, screen.SELECTED).replace('#include <ultra64.h>\n',
            '#include <ultra64.h>\n'+screen.ADDED_DECLARATIONS, 1)
        objects = []
        for name, body in (('baseline', source), ('selected', selected)):
            obj, warnings = compile_owner(self.root, self.out, body, 'owner-'+name)
            self.assertEqual(warnings, [])
            processed = self.out / ('owner-'+name+'-postprocessed.o')
            shutil.copyfile(obj, processed)
            subprocess.run([sys.executable, str(self.root / 'tools/asm-processor/asm_processor.py'), '-O2', '-g3',
                str((self.out / ('owner-'+name+'.c')).relative_to(self.root / 'conker')), '--post-process',
                str(processed.relative_to(self.root / 'conker')), '--assembler',
                'mips-linux-gnu-as -EB -mtune=vr4300 -march=vr4300 -mabi=32 -I include',
                '--asm-prelude', 'include/asm_processor_prelude.inc'], cwd=self.root / 'conker', check=True, capture_output=True)
            objects.append(processed)
        old, previous, old_rel = parse_object(objects[0])
        text, current, rel = parse_object(objects[1])
        self.assertEqual(current.keys(), previous.keys())
        for name, function in current.items():
            if name == screen.FUNCTION:
                continue
            before = previous[name]
            self.assertEqual(text[function['value']:function['value']+function['size']],
                old[before['value']:before['value']+before['size']], name)
            self.assertEqual({o-function['value']:r for o,r in rel.items() if function['value'] <= o < function['value']+function['size']},
                {o-before['value']:r for o,r in old_rel.items() if before['value'] <= o < before['value']+before['size']}, name)
        self.assertEqual(normalized_pools(objects[0]), normalized_pools(objects[1]))
        target = current[screen.FUNCTION]
        isolated, _, isolated_rel = parse_object(self.out / 'selected.o')
        self.assertEqual(text[target['value']:target['value']+260], isolated[:260])
        self.assertEqual({o-target['value']:r for o,r in rel.items() if target['value'] <= o < target['value']+260}, isolated_rel)
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/5D2C0.s',
            word_patches_path=self.root / 'conker/retail_word_patches.us.csv', filename='generated_5D2C0', rodata_symbol=action.ANCHOR)
        start = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), start)
        end = assembly.index('\n', end)+1
        self.assertNotIn('.space', assembly[end:assembly.find('.type ', end)])
        asm, obj = self.out / 'padded.s', self.out / 'padded.o'
        asm.write_text('.text\n.set noreorder\n.globl %s\n' % screen.FUNCTION+assembly[start:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        _, functions, relocations = parse_object(obj)
        self.assertEqual(functions[screen.FUNCTION]['size'], 260)
        self.assertEqual(relocations, isolated_rel)
        self.assertNotIn('.rodata', sections(obj))
        bindings = [(screen.ENTRY, dict(screen.SYMBOLS)), (screen.ENTRY+0x01000004, dict(screen.SYMBOLS))]
        for name in screen.SYMBOLS:
            symbols = dict(screen.SYMBOLS)
            symbols[name] += 0x8004 if name.startswith('D_') or name == 'func_15033BDC' else 0x01000000
            bindings.append((screen.ENTRY, symbols))
        for index, (entry, symbols) in enumerate(bindings):
            script, elf = self.out / 'padded.ld', self.out / ('rebased-%d.elf' % index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n' % entry)
            subprocess.run(['mips-linux-gnu-ld', '-m', 'elf32btsmip', '-T', str(script), '-e', screen.FUNCTION,
                *['--defsym=%s=0x%X' % item for item in symbols.items()], '-o', str(elf), str(obj)], check=True, capture_output=True)
            required = self.words.copy()
            for offset, entries in relocations.items():
                self.assertEqual(len(entries), 1)
                kind, symbol = entries[0]
                address, word = symbols[symbol], required[offset//4]
                self.assertIn(kind, ('R_MIPS_26', 'R_MIPS_HI16', 'R_MIPS_LO16'))
                required[offset//4] = word&0xFC000000 | (address>>2)&0x3FFFFFF if kind == 'R_MIPS_26' else (
                    word&0xFFFF0000 | ((address+0x8000)>>16)&65535 if kind == 'R_MIPS_HI16' else word&0xFFFF0000 | address&65535)
            self.assertEqual(list(struct.unpack_from('>65I', sections(elf)['.text'][1])), required)
        self.receipt('owner-padder', dict(unchanged_neighbors=len(current)-1, pools_and_relative_relocations_unchanged=True,
            strict_diagnostics=0, padding_and_generated_data=0, independent_links=len(bindings), signed_LO_carries=3))

    def test_07_installed_or_original_stub_and_guard_history(self):
        source = (self.root / 'conker/src/game/generated_5D2C0.c').read_text()
        installed = screen.SELECTED in source
        self.assertEqual(source.count(screen.SELECTED if installed else screen.STUB), 1)
        with (self.root / 'conker/retail_word_patches.us.csv').open() as stream:
            guards = list(csv.DictReader(stream))
        assert_guard_history(self, guards)
        self.assertFalse(any(row['function'] == screen.FUNCTION for row in guards))
        functions, _, addresses = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'), 'mips-linux-gnu-objdump')
        self.assertEqual(addresses[screen.FUNCTION], screen.ENTRY)
        self.assertEqual(len(functions[screen.FUNCTION]), 65)
        if installed:
            self.assertEqual(functions[screen.FUNCTION], self.retail)
        else:
            self.assertEqual(functions[screen.FUNCTION][:3], [0x00001025, 0x03E00008, 0])
            self.assertFalse(any(functions[screen.FUNCTION][3:]))


if __name__ == '__main__':
    unittest.main()
