"""Seven-argument effect callback, ordered accesses, private homes and slot match."""

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

from tools.experiments import game_node_effect_callback_candidates as screen
from tools.experiments.game_actor_classifier_candidates import PROFILES, sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.match_progress import load_elf_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests import test_game_node_action_match as action
from tools.tests import test_game_node_effect_registration_match as effect
from tools.tests import test_game_matrix_pair_resolver_recovery as prior
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.game_owner_pool import assert_guard_history, normalized_pools
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_point_transform_match import put, read

PACKET, ALT_PACKET, NODE, ALT_NODE, ACTOR, ALT_ACTOR, STATE = 0x30000, 0x31000, 0x10000, 0x11000, 0x20000, 0x21000, 0x22000
VALUE, VOLUME, PAN, CENTS, FX, SOUND, ALT_SOUND = 0x50000, 0x50010, 0x50020, 0x50030, 0x50040, 0x50050, 0x50060
ARGS = (PACKET, VALUE, VOLUME, PAN, CENTS, FX, SOUND)
RANDOM, PLAY, STOP, CREATE = (screen.SYMBOLS[n] for n in ('func_150ADA20', 'func_10010FFC', 'func_100111C8', 'func_1000FA64'))
WIDTHS = {RANDOM: 0, PLAY: 6, STOP: 1, CREATE: 12}
KINDS = (0, 1, 0x15E, 0x15F, 0x160, 0x513, 0x7FFF, 0x8000, 0xFFFF)
CACHED = (0, 0x15F, 0x100015F, 0x513, 0x1000513, 0x3A1, 0x80000000, 0xFFFFFFFF)
COUNTERS = (None, 0, 1, 118, 119, 120, 121, 65535)
RANDOMS = (0, 1, 2, 3, 0x80000002, 0xFFFFFFFF)


def fixture(selector=0x4B, volume=1, kind=0x15F, cached=0x513, counter=119, handle=1,
        coordinates=(bits(1.75), bits(-2.75), bits(32767.75)), live=1):
    memory = {prior.STACK+i: 0xA5 for i in range(-0x100, 0x140)}
    for base, size in ((PACKET, 0x30), (ALT_PACKET, 0x30), (NODE, 0x40), (ALT_NODE, 0x40),
            (ACTOR, 0x340), (ALT_ACTOR, 0x340), (STATE, 0x1C0), (VALUE, 0x80)):
        memory.update({base+i: 0xA5 for i in range(size)})
    for base in (PACKET, ALT_PACKET):
        put(memory, base+0x18, NODE)
        put(memory, base+0x1C, ACTOR)
        put(memory, base+0x24, handle, 2)
    for base in (NODE, ALT_NODE):
        put(memory, base+1, selector, 1)
        put(memory, base+0x38, cached)
    for base in (ACTOR, ALT_ACTOR):
        put(memory, base, live)
        put(memory, base+0x84, kind, 2)
        put(memory, base+0x31C, STATE if counter is not None else 0)
        for i, value in enumerate(coordinates):
            put(memory, base+0x14+i*4, value)
    put(memory, STATE+0x19C, counter or 0, 2)
    put(memory, VOLUME, volume)
    return memory


def mutations(target, mode, stack):
    if target == RANDOM:
        return {0: [], 1: [(ACTOR+0x84, 0x1234, 2)], 2: [(PACKET+0x1C, ALT_ACTOR, 4)],
            3: [(stack-8, ALT_ACTOR, 4), (stack-4, ALT_NODE, 4)], 4: [], 5: [], 6: [],
            7: [(stack+4, 0, 4), (stack+12, 0, 4)]}[mode]
    if target == PLAY and mode == 4:
        return [(stack-8, ALT_ACTOR, 4), (stack-4, ALT_NODE, 4), (ALT_ACTOR+0x84, 0x4321, 2)]
    if target == CREATE and mode == 5:
        return [(stack-4, ALT_NODE, 4), (NODE+0x38, 0x12345678, 4)]
    if target == STOP and mode == 6:
        return [(stack, ALT_PACKET, 4), (stack+24, ALT_SOUND, 4)]
    return []


class CallbackReference(action.ActionReference):
    def call(self, target, arguments):
        self.calls.append((target, *arguments))
        if target == CREATE:
            self.observed.append(self.get(arguments[8]+0x38))
        for address, value, size in mutations(target, self.mode, self.stack):
            self.put(address, value, size)
        return self.random if target == RANDOM else self.result if target == CREATE else 0xBEEF1234

    def run(self, args=ARGS, random=0, result=0):
        packet, value, volume, pan, cents, fx, sound = args
        self.random, self.result, self.observed = random, result, []
        for i, argument in enumerate(args[4:]):
            put(self.memory, self.stack+16+i*4, argument)
        self.put(self.stack+4, value)
        self.put(self.stack, packet)
        self.put(self.stack+12, pan)
        node = self.get(packet+0x18)
        actor = self.get(packet+0x1C)
        if not node or not actor or not self.get(actor):
            return 1
        for i in range(3):
            self.put(packet+2+i*2, effect.narrowed(self.get(actor+0x14+i*4)), 2)
        volume = self.get(volume)
        selector = self.get(node+1, 1)
        if volume:
            if selector == 0x37:
                cached = self.get(node+0x38)
                kind = self.get(actor+0x84, 2)
                sound_id = -1
                if cached&65535 != kind and kind == 0x15F:
                    self.put(self.stack-8, actor)
                    self.put(self.stack-4, node)
                    sound_id = (self.call(RANDOM, ())&3)+0x444
                    actor, node = self.get(self.stack-8), self.get(self.stack-4)
                if sound_id != -1:
                    self.put(self.stack-8, actor)
                    self.put(self.stack-4, node)
                    self.call(PLAY, (0, sound_id, 24000, 0, 0, actor))
                    actor, node = self.get(self.stack-8), self.get(self.stack-4)
                self.put(node+0x38, self.get(actor+0x84, 2))
                return 0
            state = self.get(actor+0x31C)
            if state and self.get(state+0x19C, 2) < 120 and self.get(node+0x38) == 0x513:
                self.put(node+0x38, 0x3A1)
                xyz = [0, 0, 0]
                for i in (0, 2, 1):
                    xyz[i] = effect.narrowed(self.get(actor+0x14+i*4))
                self.put(self.stack-4, node)
                handle = self.call(CREATE, (0x3A1, *xyz, 32000, 1000, 500, screen.ENTRY, node, actor, 0, 0))
                node = self.get(self.stack-4)
                self.put(node+0x3C, handle)
                return 1
            return 0
        if selector == 0x37:
            handle = self.get(packet+0x24, 2)
            if handle:
                self.put(self.stack, packet)
                self.call(STOP, (handle,))
                packet = self.get(self.stack)
                self.put(packet+0x24, 0, 2)
            sound = self.get(self.stack+24)
            self.put(sound, 0, 2)
            return 0
        return 1


class CallbackOracle(TriangleOracle):
    def __init__(self, words, memory, args=ARGS, phase=0, mode=0, random=0, result=0):
        super().__init__(words, memory, entry=screen.ENTRY, arguments=args, phase=phase)
        self.stack, self.mode, self.random, self.result = prior.STACK+phase, mode, random, result
        self.observed = []

    def record_call(self, target):
        self.calls.append((target, *self.arguments(WIDTHS[target])))

    def hook(self, target):
        if target == CREATE:
            self.observed.append(self.get(self.arguments(12)[8]+0x38, 4))
        for address, value, size in mutations(target, self.mode, self.stack):
            self.put(address, value, size)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000+register
        self.r[2] = self.random if target == RANDOM else self.result if target == CREATE else 0xBEEF1234
        self.f[:20] = [0xA5000000+i for i in range(20)]


class GameNodeEffectCallbackMatchTests(unittest.TestCase):
    run_host = prior.GameMatrixPairResolverRecoveryTests.run_host

    @classmethod
    def setUpClass(cls):
        assert not any(prior.STACK-0x600 <= address < prior.STACK+0x140 for address in
            (PACKET, ALT_PACKET, NODE, ALT_NODE, ACTOR, ALT_ACTOR, STATE, VALUE, VOLUME, PAN, CENTS, FX, SOUND, ALT_SOUND))
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root / 'conker/build/game-node-effect-callback-test'
        cls.out.mkdir(exist_ok=True)
        cls.record, cls.raw = screen.compile_candidate(cls.root, cls.out, 'selected')
        cls.words = screen.normalize(cls.raw)
        cls.retail = list(struct.unpack_from('>137I', (cls.root / 'conker/conker.us.bin').read_bytes(), screen.ROM))
        cls.directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path = Path(cls.directory.name)

    def receipt(self, name, value):
        (self.out / (name+'.json')).write_text(json.dumps(value, indent=2)+'\n')

    def compare(self, memory, args=ARGS, phase=0, mode=0, random=0, result=0):
        reference = CallbackReference(memory, phase, mode)
        expected = reference.run(args, random, result)
        models = [CallbackOracle(body, memory, args, phase, mode, random, result).run() for body in (self.raw, self.words, self.retail)]
        for model in models:
            self.assertEqual((model.r[2], model.calls, model.observed, prior.public(model.events), prior.external_memory(model.memory)),
                (expected, reference.calls, reference.observed, prior.public(reference.events), prior.external_memory(reference.memory)))
        for model in models[:2]:
            self.assertEqual((model.r, model.f, model.events, model.memory),
                (models[2].r, models[2].f, models[2].events, models[2].memory))
        return models

    def test_01_raw_slot_closed_schedule_and_symbolic_interface(self):
        self.assertEqual((self.record['body_words'], self.record['frame'], self.record['differences'],
            self.record['pool_bytes'], self.record['diagnostics']), (137, 64, 2, 0, ''))
        self.assertEqual(self.words, self.retail)
        self.assertEqual([i for i,(a,b) in enumerate(zip(self.raw, self.words)) if a != b], [66, 68])
        self.assertEqual(sorted(self.raw[66:69]), sorted(self.words[66:69]))
        self.assertEqual(self.raw[67], 0x10000041)
        relocs = [r for entries in self.record['relocations'].values() for r in entries]
        self.assertEqual({symbol for _,symbol in relocs}, set(screen.SYMBOLS))
        self.assertEqual([sum(k == kind for k,_ in relocs) for kind in ('R_MIPS_26','R_MIPS_HI16','R_MIPS_LO16')], [4,1,1])
        for index in (66, 67, 68):
            stale = self.raw.copy()
            stale[index] ^= 1
            with self.assertRaises(AssertionError):
                screen.normalize(stale)
        self.receipt('slot', dict(words=137, bytes=548, frame=64, raw_differences=2, normalized_differences=0,
            guards=2, padding=0, generated_data=0, closed_origin_permutation=True, branch_and_relocations_unchanged=True))

    def test_02_selectors_types_counters_callbacks_coordinate_grid_and_coverage(self):
        seen, counts = set(), [0,0,0,0]
        groups = (
            ((fixture(selector, volume, kind), phase, 0, 3, 0xFFFF) for selector, volume, kind, phase in
                itertools.product(range(256), (0,1,0x80000000), (0,0x15F), (0,8))),
            ((fixture(selector, kind=kind, cached=cached, counter=counter), phase, 0, 2, 0) for selector, kind, cached, counter, phase in
                itertools.product((0x37,0x4B), KINDS, CACHED, COUNTERS, (0,8))),
            ((fixture(selector, volume=volume, cached=cached, handle=handle), phase, mode, random, result)
                for (selector,volume,cached,handle),mode,random,result,phase in itertools.product(
                    ((0x37,1,0,1),(0x37,1,0x15F,1),(0x4B,1,0x513,1),(0x37,0,0,0),(0x37,0,0,0xFFFF)),
                    range(8), RANDOMS, effect.RESULTS, (0,8))),
            ((fixture(coordinates=xyz), 0, 0, 0, 0x1234) for xyz in itertools.product(effect.COORDINATES, repeat=3)))
        for group, cases in enumerate(groups):
            for memory,phase,mode,random,result in cases:
                for model in self.compare(memory, phase=phase, mode=mode, random=random, result=result):
                    seen.update(model.visits)
                counts[group] += 1
        missing = sorted((pc-screen.ENTRY)//4 for pc in set(range(screen.ENTRY,screen.ENTRY+548,4))-seen)
        self.assertEqual(missing, [69,118])
        self.receipt('guest', dict(cases=sum(counts), selector_cases=counts[0], gate_cases=counts[1], mutation_cases=counts[2],
            coordinate_cases=counts[3], selectors=256, mutation_modes=8, random_words=6, results=6, SP_phases=2,
            missing_word_indices=missing, independent_public_reference_and_full_raw_normalized_retail_GP_FP_memory_equal=True,
            unused_pointer_arguments_not_read=True, invalid_FP_FCSR_and_actual_callees_not_claimed=True))

    def test_03_lazy_storage_partial_faults_and_aliases(self):
        lazy = []
        memory = fixture();put(memory,PACKET+0x18,0);del memory[ACTOR]
        lazy.append((memory, (PACKET,0,0,0,0,0,0)))
        memory = fixture(live=0);del memory[ACTOR+0x14]
        lazy.append((memory, (PACKET,0,0,0,0,0,0)))
        memory = fixture(selector=0x37,cached=0x15F);del memory[ACTOR+0x31C]
        lazy.append((memory, (PACKET,0,VOLUME,0,0,0,0)))
        memory = fixture(selector=0x4B,volume=0);del memory[NODE+0x38],memory[ACTOR+0x31C],memory[PACKET+0x24]
        lazy.append((memory, (PACKET,0,VOLUME,0,0,0,0)))
        for memory,args in lazy:
            self.compare(memory,args)
        probes = [(fixture(), (0,*ARGS[1:]))]
        for missing in (PACKET+0x18,PACKET+0x1C,ACTOR,ACTOR+0x14,PACKET+2,ACTOR+0x18,PACKET+4,
                ACTOR+0x1C,PACKET+6,VOLUME,NODE+1,ACTOR+0x31C,STATE+0x19C,NODE+0x38,NODE+0x3C):
            memory = fixture();del memory[missing];probes.append((memory,ARGS))
        for missing in (NODE+0x38,ACTOR+0x84):
            memory = fixture(selector=0x37,cached=0);del memory[missing];probes.append((memory,ARGS))
        for missing in (PACKET+0x24,SOUND):
            memory = fixture(selector=0x37,volume=0);del memory[missing];probes.append((memory,ARGS))
        for memory,args in probes:
            reference = CallbackReference(memory)
            with self.assertRaises(AssertionError) as failure:
                reference.run(args)
            for body in (self.raw,self.words,self.retail):
                model = CallbackOracle(body,memory,args)
                with self.assertRaises(AssertionError) as actual:
                    model.run()
                self.assertEqual(actual.exception.args,failure.exception.args)
                self.assertEqual((model.calls,prior.public(model.events),prior.external_memory(model.memory)),
                    (reference.calls,prior.public(reference.events),prior.external_memory(reference.memory)))
        aliases = []
        for packet in (NODE,ACTOR):
            memory = fixture();put(memory,packet+0x18,NODE);put(memory,packet+0x1C,ACTOR)
            aliases.append((memory,(packet,*ARGS[1:])))
        memory = fixture(selector=0x37,volume=0)
        aliases.append((memory,(*ARGS[:6],PACKET+0x24)))
        for memory,args in aliases:
            self.compare(memory,args)
        self.receipt('gates',dict(lazy_cases=len(lazy),fault_prefixes=len(probes),aliases=len(aliases),
            coordinate_partial_stores_preserved=True,callback_home_reload_and_live_type_reads=True,
            raw_fault_GP_timing_and_arbitrary_private_aliases_not_claimed=True))

    def test_04_profiles_and_effective_semantic_negatives(self):
        records,ordinary,negatives = [],0,0
        forms = [(n,b,'o2g3') for n,b in screen.candidates()]
        forms += [('profile-'+p,screen.SELECTED,p) for p in PROFILES if p != 'o2g3']
        memories = [fixture(**kw) for kw in (dict(selector=0x37,cached=0),dict(selector=0x37,cached=0x100015F),
            dict(counter=120),dict(counter=119),dict(selector=0x37,volume=0),dict(selector=0x4B,volume=0))]
        for name,body,profile in forms:
            record,words = screen.compile_candidate(self.root,self.out,name,body,profile)
            records.append(record);caught = False
            for memory in memories:
                reference = CallbackReference(memory);expected = reference.run(random=3,result=0x1234)
                model = CallbackOracle(words,memory,random=3,result=0x1234).run()
                observed = (model.r[2],model.calls,model.observed,prior.external_memory(model.memory))
                required = (expected,reference.calls,reference.observed,prior.external_memory(reference.memory))
                if name.startswith('negative-'):
                    caught |= observed != required
                else:
                    self.assertEqual(observed,required,name);ordinary += 1
            if name.startswith('negative-'):
                self.assertTrue(caught,name);negatives += 1
        self.receipt('controls',dict(forms=len(records),ordinary_executions=ordinary,effective_negatives=negatives,
            measurements=records,ordinary_defined_float_to_s16_range_only=True,alternate_private_frames_not_claimed=True))

    def test_05_native32_complete_C_all_types_counters_results_and_canaries(self):
        self.fixture = r'''typedef unsigned char u8;typedef unsigned short u16;typedef short s16;
typedef int s32;typedef unsigned int u32;typedef float f32;
typedef union __attribute__((aligned(8))) {u32 align;u8 b[0x340];} Actor;
typedef union __attribute__((aligned(8))) {u32 align;u8 b[0x40];} Storage;
typedef union __attribute__((aligned(8))) {u32 align;u8 b[0x1C0];} Attachment;
typedef char widths[(sizeof(void *)==4&&sizeof(s16)==2&&sizeof(f32)==4)?1:-1];
static Actor actor;static Storage node,packet;static Attachment state;static s32 volume;
static u16 sound,result;static int count,error;static int calls[2];static s16 xyz[3];
static u8 seen_results[65536],seen_coordinates[65536],seen_types[65536],seen_counters[65536];
s32 func_15033BDC(u8 *,s32 *,s32 *,s32 *,s32 *,s32 *,u16 *);
s32 func_150ADA20(void){calls[count++]=1;return 3;}
u16 func_10010FFC(s32 a,s32 b,u16 c,s16 d,u8 e,void *f){calls[count++]=2;
    if(a||b!=0x447||c!=24000||d||e||f!=actor.b)error=1;
    *(u16 *)(actor.b+0x84)=0xFFFF;return 0;
}
void func_100111C8(u16 a){calls[count++]=3;if(a!=result)error=2;*(u16 *)(packet.b+0x24)=123;sound=234;}
u16 func_1000FA64(u16 a,s16 x,s16 y,s16 z,s32 amount,u16 rate,s16 limit,s32 callback,
    void *n,s32 b,s32 c,s32 d){calls[count++]=4;
    if(a!=0x3A1||x!=xyz[0]||y!=xyz[1]||z!=xyz[2]||amount!=32000||rate!=1000||limit!=500||
        callback!=(s32)func_15033BDC||n!=node.b||b!=(s32)actor.b||c||d||*(s32 *)(node.b+0x38)!=0x3A1)error=3;
    seen_results[result]=1;seen_coordinates[(u16)x]=1;*(s32 *)(node.b+0x38)=0x12345678;return result;
}
''' + screen.SELECTED
        self.run_host(r'''
Storage old_node,old_packet;Attachment old_state;Actor old_actor;u16 old_sound;int v,k,i,expect,create,play,stop,valid;f32 coordinate;
for(v=0;v<65536;v++)for(k=0;k<8;k++){
    for(i=0;i<0x340;i++)actor.b[i]=0xA5;
    for(i=0;i<0x40;i++)node.b[i]=packet.b[i]=0xA5;
    for(i=0;i<0x1C0;i++)state.b[i]=0xA5;
    xyz[0]=(s16)(v-32768);xyz[1]=(s16)(32767-v);xyz[2]=17;
    for(i=0;i<3;i++){coordinate=(f32)xyz[i]+(xyz[i]<0?-0.25f:0.25f);*(f32 *)(actor.b+0x14+i*4)=coordinate;}
    *(u32 *)(packet.b+0x18)=k==0?0:(u32)node.b;*(u32 *)(packet.b+0x1C)=(u32)actor.b;
    *(u32 *)actor.b=k==7?0:1;*(u16 *)(actor.b+0x84)=(u16)v;*(u32 *)(actor.b+0x31C)=(u32)state.b;
    *(u16 *)(state.b+0x19C)=0;
    node.b[1]=(k==1||k==2||k==5)?0x37:0x4B;
    *(u32 *)(node.b+0x38)=k==1?(0x10000u|(u32)v):0x513;
    *(u16 *)(packet.b+0x24)=(u16)v;result=(u16)v;sound=0xA55A;volume=(k==5||k==6)?0:1;
    if(k==3)*(u16 *)(state.b+0x19C)=(u16)v;
    if(k==4)*(u16 *)(state.b+0x19C)=119;
    valid=k!=0&&k!=7;create=valid&&(k==3?v<120:k==4);play=k==2&&v==0x15F;stop=k==5&&v!=0;
    expect=!valid||create||k==6?1:0;count=error=0;old_node=node;old_packet=packet;old_actor=actor;old_state=state;old_sound=sound;
    if(valid)for(i=0;i<3;i++)*(s16 *)(old_packet.b+2+i*2)=xyz[i];
    if(k==1||k==2){*(u32 *)(old_node.b+0x38)=play?0xFFFF:(u16)v;seen_types[v]=1;}
    if(play)*(u16 *)(old_actor.b+0x84)=0xFFFF;
    if(k==3)seen_counters[v]=1;
    if(create){*(u32 *)(old_node.b+0x38)=0x12345678;*(u32 *)(old_node.b+0x3C)=result;}
    if(k==5){*(u16 *)(old_packet.b+0x24)=0;old_sound=0;}
    if(func_15033BDC(packet.b,0,&volume,0,0,0,&sound)!=expect||error||count!=play*2+stop+create)return 1;
    if(play&&(calls[0]!=1||calls[1]!=2))return 2;
    if(stop&&calls[0]!=3)return 3;
    if(create&&calls[0]!=4)return 4;
    for(i=0;i<0x340;i++)if(actor.b[i]!=old_actor.b[i])return 5;
    for(i=0;i<0x40;i++)if(node.b[i]!=old_node.b[i]||packet.b[i]!=old_packet.b[i])return 6;
    for(i=0;i<0x1C0;i++)if(state.b[i]!=old_state.b[i])return 6;
    if(sound!=old_sound)return 7;
}
for(v=0;v<65536;v++)if(!seen_results[v]||!seen_coordinates[v]||!seen_types[v]||!seen_counters[v])return 8;
''')
        self.receipt('native',dict(cases=524288,pointer_bytes=4,actual_complete_C=True,all_u16_types=65536,
            all_u16_counters=65536,all_u16_results_observed_in_create=65536,all_signed16_X_observed_in_create=65536,
            complete_ABI_and_all_input_canaries_checked=True,unused_parameters_null=True,
            axes_correlated=True,private_home_mutation_and_actual_callees_not_claimed=True))

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
        self.assertEqual(text[target['value']:target['value']+548], isolated[:548])
        self.assertEqual({o-target['value']:r for o,r in rel.items() if target['value'] <= o < target['value']+548}, isolated_rel)
        with (self.root / 'conker/retail_word_patches.us.csv').open() as stream:
            reader = csv.DictReader(stream)
            fields, guards = reader.fieldnames, list(reader)
        existing = [row for row in guards if row['function'] == screen.FUNCTION]
        self.assertIn(existing, ([], screen.owner_guards()))
        prepared = [row for row in guards if row['function'] != screen.FUNCTION]+screen.owner_guards()
        patches = self.out / 'prepared-guards.csv'
        with patches.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(prepared)
        assembly = emit_padded_assembly(objects[1], self.root / 'conker/asm/5D2C0.s',
            word_patches_path=patches, filename='generated_5D2C0', rodata_symbol=action.ANCHOR)
        for field, value in (('expected', '0xAD0F0039'), ('expected_relocations', 'R_MIPS_HI16:func_15033BDC')):
            stale = [dict(row) for row in prepared]
            stale[-1][field] = value
            with (self.out / 'stale-guards.csv').open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(stale)
            with self.assertRaises(ValueError):
                emit_padded_assembly(objects[1], self.root / 'conker/asm/5D2C0.s',
                    word_patches_path=self.out / 'stale-guards.csv', filename='generated_5D2C0', rodata_symbol=action.ANCHOR)
        start = assembly.index('.type %s, @function' % screen.FUNCTION)
        end = assembly.index('.size %s, . - %s' % (screen.FUNCTION, screen.FUNCTION), start)
        end = assembly.index('\n', end)+1
        self.assertNotIn('.space', assembly[end:assembly.find('.type ', end)])
        asm, obj = self.out / 'padded.s', self.out / 'padded.o'
        asm.write_text('.text\n.set noreorder\n.globl %s\n' % screen.FUNCTION+assembly[start:end])
        subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(obj), str(asm)], check=True, capture_output=True)
        _, functions, relocations = parse_object(obj)
        self.assertEqual(functions[screen.FUNCTION]['size'], 548)
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
            self.assertEqual(list(struct.unpack_from('>137I', sections(elf)['.text'][1])), required)
        self.receipt('owner-padder', dict(unchanged_neighbors=len(current)-1, pools_and_relative_relocations_unchanged=True,
            strict_diagnostics=0, padding_and_generated_data=0, independent_links=len(bindings), signed_LO_carries=1, real_padder_stale_word_and_relocation_rejected=True))

    def test_07_installed_or_original_stub_and_guard_history(self):
        source = (self.root / 'conker/src/game/generated_5D2C0.c').read_text()
        installed = screen.SELECTED in source
        self.assertEqual(source.count(screen.SELECTED if installed else screen.STUB),1)
        with (self.root / 'conker/retail_word_patches.us.csv').open() as stream:
            guards = list(csv.DictReader(stream))
        assert_guard_history(self,guards)
        self.assertEqual([r for r in guards if r['function'] == screen.FUNCTION],screen.owner_guards() if installed else [])
        functions,_,addresses = load_elf_functions(str(self.root / 'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
        self.assertEqual(addresses[screen.FUNCTION],screen.ENTRY)
        if installed:
            self.assertEqual(functions[screen.FUNCTION],self.retail)
        else:
            self.assertEqual(functions[screen.FUNCTION],[0x00001025,0x03E00008]+[0]*135)


if __name__ == '__main__':
    unittest.main()
