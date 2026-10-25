"""Embedded motion: float32 ordering, late clocks and signed slot-2 ABI."""

from dataclasses import dataclass, replace
from pathlib import Path
import csv
import itertools
import json
import math
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_compact_embedded_oscillation_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import add_retail_lengths, function_vram, load_symbol_addrs, DEFAULT_SEGMENTS
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_animation_timeline_oracle import bits, floating, signed
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_random_burst import ReturnBoundaryCode, CallerBoundary
from tools.tests import test_game_trig_match as trig
from tools.tests.test_game_sine_phase_update import wrap
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT = Path(__file__).resolve().parents[2]
RECORD, TABLE = 0x30000, 0x80089CB8
UPDATE_CALLER, RELEASE, TICK, WRAP_BOUND = 0x1513CFE4, 0x1516972C, 0x800BE9E4, 0x800A56A4
OFFSETS = (0x40, 0x48, 0x38, 0x118, 0x110, 0x11C, 0x120, 0x128, 0x114)
COORDS = (0., -0., 1.75, -2.75, 16777216., -16777216., 1e20, -1e20)
SYMBOLS = dict(sinf=source.SINE, func_15144B68=source.WRAP, D_800BE9A4=source.CLOCK)


@dataclass(frozen=True)
class Case:
    fields: tuple = tuple(bits(v) for v in (1., -2., 99., .75, 2., -.5, 3., -4., 5.))
    clock: int = bits(1.)
    sine: int = bits(.25)
    wrapped: int = bits(1.5)
    mode: int = 0
    alias: object = None
    seed: int = 0xA5


def corpus():
    for i in range(256):
        yield Case(tuple(bits(v) for v in (COORDS[i%8], COORDS[(i+1)%8], 99.,
            (i%25-12)*.75, COORDS[(i+2)%8], (i%7-3)*.25,
            COORDS[(i+3)%8], COORDS[(i+4)%8], COORDS[(i+5)%8])),
            bits((0., -0., .125, -.25, 1., -1., 4., 2.)[i%8]),
            bits((-.75, -0., 0., .25, 1.)[i%5]), bits((i%17)*.25), i%4, seed=i)
    for angle, clock, mode in itertools.product((-90., -6.2831855, -0., 0., 6.2831855, 90.),
            (0., 1., -1., 4.), range(4)):
        yield replace(Case(), fields=Case().fields[:3]+(bits(angle),)+Case().fields[4:],
            clock=bits(clock), mode=mode)
    for offset, mode, clock in itertools.product((0x40,0x48,0x38,0x118,0x11C,0x120,0x128),
            range(4), (0.,1.)):
        yield Case(alias=offset,mode=mode,clock=bits(clock))
    for offset, value in itertools.product((0,1,2,4,6,7,8),(1,0x80000001,0x7f800000,0xff800000,0x7fc12345)):
        fields=list(Case().fields);fields[offset]=value
        yield replace(Case(),fields=tuple(fields))


def address(case, symbols):
    return RECORD if case.alias is None else symbols['D_800BE9A4']-case.alias


def fixture(case, symbols=None):
    s=symbols or SYMBOLS;p=address(case,s)
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x800,0x400)}
    for base,size in ((p-16,0x200),(s['D_800BE9A4']-16,36)):
        for i in range(size):memory.setdefault(base+i,(i*13+case.seed)&255)
    for at,value in trig.GLOBALS.items():put(memory,at,value)
    put(memory,WRAP_BOUND,0x40C90FDB)
    for at,value in zip(OFFSETS,case.fields):put(memory,p+at,value)
    put(memory,s['D_800BE9A4'],case.clock)
    return memory


def public(memory):
    return {a:v for a,v in memory.items() if not STACK-0x800<=a<STACK+0x400}


def effects(memory,p,clock,ordinal,mode):
    if ordinal==1 and mode&1:
        for off,value in ((0x114,7.),(0x110,-11.),(0x118,.75),(0x11C,-.5)):
            put(memory,p+off,bits(value))
        put(memory,clock,bits(2.))
    if ordinal==2 and mode&2:
        for off,value in ((0x118,77.),(0x40,10.),(0x48,20.),(0x120,3.25),(0x128,-4.5)):
            put(memory,p+off,bits(value))
        put(memory,clock,bits(.125))


def add(a,b):return bits(floating(a)+floating(b))
def mul(a,b):return bits(floating(a)*floating(b))


def reference(case, symbols=None, real=False, memory=None):
    s=symbols or SYMBOLS;p=address(case,s);m=dict(fixture(case,s) if memory is None else memory);calls=[]
    def call(name,value):
        calls.append((s[name],value))
        result=(trig.reference(value) if name=='sinf' else wrap(value)) if real else (
            case.sine if name=='sinf' else case.wrapped)
        if not real:effects(m,p,s['D_800BE9A4'],len(calls),case.mode)
        return result
    sine=call('sinf',read(m,p+0x118))
    put(m,p+0x38,add(mul(sine,read(m,p+0x114)),read(m,p+0x110)))
    phase=add(read(m,p+0x118),mul(read(m,p+0x11C),read(m,s['D_800BE9A4'])))
    put(m,p+0x118,phase)
    put(m,p+0x118,call('func_15144B68',phase))
    put(m,p+0x40,add(read(m,p+0x40),mul(read(m,p+0x120),read(m,s['D_800BE9A4']))))
    put(m,p+0x48,add(read(m,p+0x48),mul(read(m,p+0x128),read(m,s['D_800BE9A4']))))
    return m,calls


class MotionOracle(TimingOracle):
    def __init__(self,words,case,phase=0,symbols=None,entry=source.ENTRY,connected=None,
            real=False,memory=None,boundary=None):
        self.case,self.targets,self.real=case,symbols or SYMBOLS,real
        self.record=address(case,self.targets);self.visits=set()
        super().__init__(words,fixture(case,self.targets) if memory is None else memory,
            phase=phase,entry=entry,arguments=(self.record,),connected=connected)
        if boundary is not None:self.code=ReturnBoundaryCode(self.code,boundary,self)

    def execute(self,word):
        self.visits.add(self.current_pc)
        op,rs,rt,rd,fd,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63
        if op==0 and fn==3:self.r[rd]=signed(self.r[rt])>>fd&0xFFFFFFFF
        elif op==32:
            offset=(word&0xFFFF)-0x10000 if word&0x8000 else word&0xFFFF
            value=self.get((self.r[rs]+offset)&0xFFFFFFFF,1)
            self.r[rt]=(value-256 if value&128 else value)&0xFFFFFFFF
        elif op==17 and rs==16 and fn==13:self.f[fd]=math.trunc(floating(self.f[rd]))&0xFFFFFFFF
        elif op==17 and rs==16 and fn==7:self.f[fd]=self.f[rd]^0x80000000
        else:super().execute(word)

    def record_call(self,target):
        if target in (self.targets['sinf'],self.targets['func_15144B68']):args=self.f[12]
        elif target==source.ENTRY:args=(self.r[4],)
        else:raise AssertionError(('Unbounded motion call',hex(target)))
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        name='sinf' if target==self.targets['sinf'] else 'func_15144B68'
        assert target==self.targets[name]
        result=(trig.reference(self.f[12]) if name=='sinf' else wrap(self.f[12])) if self.real else (
            self.case.sine if name=='sinf' else self.case.wrapped)
        ordinal=sum(t in (self.targets['sinf'],self.targets['func_15144B68']) for t,_ in self.calls)
        if not self.real:effects(self.memory,self.record,self.targets['D_800BE9A4'],ordinal,self.case.mode)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=result
        self.hi,self.lo=0x87654321,0x12345678


class UpdateOracle(MotionOracle):
    def record_call(self, target):
        if target == RELEASE:
            self.calls.append((target, (self.r[4],)))
            self.events.append(('CALL', target, (self.r[4],)))
        else:
            super().record_call(target)

    def hook(self, target):
        if target != RELEASE:
            return super().hook(target)
        put(self.memory, self.r[4] + 0x10, 0)
        for register in (1, 2, 3, *range(4, 16), 24, 25):
            self.r[register] = 0xA5000000 + register
        self.f[:20] = [0xA5000000 + i for i in range(20)]


def native_harness(body,cases):
    rows=[]
    for c in cases:
        initial=fixture(c);expected,calls=reference(c)
        values=[read(initial,RECORD+i*4)for i in range(75)]
        wanted=[read(expected,RECORD+i*4)for i in range(75)]
        rows.append('{{%s},{%s},%s}'%(','.join('0x%Xu'%v for v in values),','.join('0x%Xu'%v for v in wanted),
            ','.join('0x%Xu'%v for v in(c.clock,c.sine,c.wrapped,c.mode,calls[0][1],calls[1][1],read(expected,source.CLOCK)))))
    return """typedef unsigned char u8;typedef unsigned int u32;typedef int s32;typedef float f32;
""" + source.TYPES + """
typedef struct{u8 header[0x38];f32 oscillation;u8 reserved3C[4];f32 x;u8 reserved44[4];
 f32 z;u8 reserved4C[0xC4];CompactEmbeddedOscillatingMotion motion;}Actor;
typedef char size_tail[sizeof(CompactEmbeddedOscillatingMotion)==0x1C?1:-1];
typedef char size_actor[sizeof(Actor)==0x12C?1:-1];
typedef char off_motion[__builtin_offsetof(Actor,motion)==0x110?1:-1];
typedef char off_x[__builtin_offsetof(Actor,x)==0x40?1:-1];
typedef char off_z[__builtin_offsetof(Actor,z)==0x48?1:-1];
typedef char off_oscillation[__builtin_offsetof(Actor,oscillation)==0x38?1:-1];
""" + '\n'.join('typedef char off_%X[__builtin_offsetof(CompactEmbeddedOscillatingMotion,%s)==0x%X?1:-1];'%(off,name,off)
        for off,name in((0,'base'),(4,'amplitude'),(8,'phase'),(12,'phaseRate'),(16,'velocityX'),(24,'velocityZ'))) + """
typedef struct{u32 initial[75],expected[75],clock,sine,wrapped,mode,arg1,arg2,clockAfter;}Case;
static const Case cases[]={""" + ',\n'.join(rows) + """};
static struct{u32 left[4];Actor actor;u32 right[4];}storage;
static const Case*c;static u32 ordinal,error;
f32 D_800BE9A4;
static u32 word(f32 x){union{u32 w;f32 f;}v;v.f=x;return v.w;}
static f32 number(u32 x){union{u32 w;f32 f;}v;v.w=x;return v.f;}
static void effect(u32 n){CompactEmbeddedOscillatingMotion*m=&storage.actor.motion;
 if(n==1&&(c->mode&1)){m->amplitude=7;m->base=-11;m->phase=.75f;m->phaseRate=-.5f;D_800BE9A4=2;}
 if(n==2&&(c->mode&2)){m->phase=77;storage.actor.x=10;storage.actor.z=20;m->velocityX=3.25f;m->velocityZ=-4.5f;D_800BE9A4=.125f;}
}
__attribute__((noinline)) f32 sinf(f32 x){if(ordinal++!=0||word(x)!=c->arg1)error=23;effect(1);return number(c->sine);}
__attribute__((noinline)) f32 func_15144B68(f32 x){if(ordinal++!=1||word(x)!=c->arg2)error=23;effect(2);return number(c->wrapped);}
""" + body + """
static s32(*volatile callback)(u8*)=func_151B8CFC;
static int run(void){u32 n,i,j;u8*p=(u8*)&storage.actor;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];ordinal=error=0;
  for(i=0;i<4;i++){storage.left[i]=0xA5A5A5A5;storage.right[i]=0x5A5A5A5A;}
  for(i=0;i<75;i++)for(j=0;j<4;j++)p[4*i+j]=(u8)(c->initial[i]>>(8*j));
  D_800BE9A4=number(c->clock);
  if(callback((u8*)&storage.actor)!=1||ordinal!=2||error||word(D_800BE9A4)!=c->clockAfter)return 23;
  for(i=0;i<75;i++)for(j=0;j<4;j++)if(p[4*i+j]!=(u8)(c->expected[i]>>(8*j)))return 23;
  for(i=0;i<4;i++)if(storage.left[i]!=0xA5A5A5A5||storage.right[i]!=0x5A5A5A5A)return 23;
 }return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
"""



class CompactEmbeddedOscillatingMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=ROOT/source.BUILD
        cls.installed=source.digest((ROOT/source.SOURCE).read_bytes())!=source.INPUTS[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.output)
        else:
            source.freeze(ROOT,cls.output)
            if not (cls.output/'first-link.json').exists():
                source.qualify(ROOT,cls.output);source.make_shadow(ROOT,cls.output);source.predict(ROOT,cls.output)
        cls.values=source.snapshot(cls.output);cls.rom=cls.values['conker/conker.us.bin']
        cls.obj,diag=source.compile_owner(ROOT,cls.output,
            '#include <ultra64.h>\n'+source.DECLARATIONS+source.TYPES+source.SELECTED,'fresh-selected')
        if diag:raise ValueError(diag)
        data,functions=source.link_owner(ROOT,cls.output,cls.obj,source.OWNER)
        cls.words=list(struct.unpack_from('>43I',data,functions[source.FUNCTION]['value']))
        cls.truth=list(struct.unpack_from('>43I',cls.rom,source.ROM));cls.cases=list(corpus())
        cls.native_cases=[c for c in cls.cases if c.alias is None and all(math.isfinite(floating(x))
            for x in c.fields) and all(not math.isnan(floating(read(reference(c)[0],RECORD+off))) for off in OFFSETS)]
        cls.receipt=dict(installed=cls.installed,cases=len(cls.cases),native_cases=len(cls.native_cases),guards=0)

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('oscillating-motion qualification:',cls.receipt)

    def test_01_direct_C_extent_bindings_owner_and_real_old_stub(self):
        self.assertEqual(self.words,self.truth);raw,bindings=source.payload(self.obj)
        self.assertEqual((len(raw),self.words[0]),(172,0x27BDFFE0))
        self.assertEqual(sum(map(len,bindings.values())),6)
        source.checked_payload(raw, bindings)
        for index in range(43):
            wrong = bytearray(raw);wrong[index * 4] ^= 1
            with self.assertRaises(ValueError):source.checked_payload(bytes(wrong), bindings)
        for offset in bindings:
            wrong = dict(bindings);wrong[offset] = [(bindings[offset][0][0], 'D_800BE9E4')]
            with self.assertRaises(ValueError):source.checked_payload(raw, wrong)
        self.assertEqual(self.rom[source.ROM + 172:source.ROM + 180], bytes(8))
        padded, fs, _ = source.parse_object(self.output/'qualified-padded.o')
        end = fs[source.FUNCTION]['value'] + 172
        self.assertEqual(padded[end:end + 8], bytes(8))
        self.assertEqual(source.payload(source.original(ROOT,self.output)),(raw,bindings))
        self.assertEqual(source.payload(self.output/'qualified-padded.o'),(raw,bindings))
        old=list(struct.unpack_from('>43I',self.values['conker/build/conker.us.elf'],
            source.elf_slot_offset(self.values['conker/build/conker.us.elf'],source.ENTRY,172)))
        m=MotionOracle(old,Case()).run();self.assertEqual(m.r[2],0);self.assertFalse(m.calls)
        q=json.loads((self.output/'qualification.json').read_text());self.assertEqual(q['preserved_neighbors'],3)
        self.assertEqual(json.loads((self.output/'make-shadow.json').read_text())['actual_Make_commands'],3)
        self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
        self.receipt.update(words=43,frame=32,bindings=6,compiler_only=True,actual_old_stub_rejected=True,
            preserved_neighbors=3,actual_Make_commands=3,guard_manifest_unchanged=True,
            alignment_words=2,word_corruptions_rejected=43,binding_corruptions_rejected=6)

    def test_02_complete_model_late_reads_clock_aliases_and_untouched_bytes(self):
        visits=set();aliases=0
        for c,phase in itertools.product(self.cases,(0,8)):
            expected,calls=reference(c);models=[]
            for words in (self.truth,self.words):
                m=MotionOracle(words,c,phase).run()
                self.assertEqual((public(m.memory),m.calls),(public(expected),calls))
                self.assertEqual((m.r[2],m.r[29]),(1,STACK+phase));models.append(m);visits.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));aliases+=int(c.alias is not None)
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+172,4))<=visits)
        self.receipt.update(modeled_phases=len(self.cases)*2,guest_clock_alias_phases=aliases,
            all43_words_executed=True,post_helper_mutations=True,native_alias_claimed=False)

    def native(self,body,label,opt='-O2'):
        path=self.output/(label+opt+'.c');exe=path.with_suffix('.elf')
        path.write_text(native_harness(body,self.native_cases))
        subprocess.run(['gcc','-m32','-std=c99',opt,'-fno-pie','-no-pie','-nostdlib','-fno-stack-protector',
            '-fno-builtin','-msse2','-mfpmath=sse','-ffp-contract=off','-mstackrealign',
            '-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-Werror=implicit-function-declaration',
            '-Wl,-e,_start',str(path),'-o',str(exe)],capture_output=True,check=True)
        return subprocess.run([str(exe)],capture_output=True).returncode

    def test_03_native32_layout_three_optimizations_and_semantic_negatives(self):
        for opt in ('-O0','-O2','-O3'):self.assertEqual(self.native(source.SELECTED,'native',opt),0)
        controls={
            'wrong-oscillation-output':source.SELECTED.replace('*(f32 *)(actor + 0x38) =','*(f32 *)(actor + 0x40) ='),
            'missing-base':source.SELECTED.replace(' + motion->base',''),
            'wrong-amplitude':source.SELECTED.replace('* motion->amplitude','* motion->phaseRate'),
            'wrong-rate':source.SELECTED.replace('motion->phaseRate *','motion->velocityX *'),
            'wrong-wrap-input':source.SELECTED.replace('func_15144B68(motion->phase)','func_15144B68(motion->phase + 1.0f)'),
            'lost-wrap-result':source.SELECTED.replace('motion->phase = func_15144B68','func_15144B68'),
            'wrong-x-velocity':source.SELECTED.replace('(actor + 0x40) += motion->velocityX','(actor + 0x40) += motion->velocityZ'),
            'wrong-z-velocity':source.SELECTED.replace('(actor + 0x48) += motion->velocityZ','(actor + 0x48) += motion->velocityX'),
            'lost-x-accumulation':source.SELECTED.replace('(actor + 0x40) +=','(actor + 0x40) ='),
            'lost-success':source.SELECTED.replace('return 1;','return 0;'),
            'cached-clock':source.SELECTED.replace('    *(f32 *)(actor + 0x38) =','    f32 cached = D_800BE9A4;\n    *(f32 *)(actor + 0x38) =').replace('* D_800BE9A4','* cached'),
            'reserved-clear':source.SELECTED.replace('return 1;','motion->reserved14[0] = 0;\n    return 1;'),
        }
        for name,body in controls.items():
            self.assertNotEqual(body,source.SELECTED);self.assertEqual(self.native(body,name),23,name)
        self.receipt.update(native_optimizations=3,trap_UBSan=True,separate_float32_operations=True,
            typed_record_and_fences=True,compiled_semantic_negatives=len(controls),scripted_native_math=True)

    def test_04_complete_original_sine_and_wrap_chain(self):
        self.assertEqual(struct.unpack_from('>I',self.rom,0x24A164)[0],0x40C90FDB)
        connected={source.SINE+i*4:w for i,w in enumerate(struct.unpack_from('>104I',self.rom,0x75210))}
        connected.update({source.WRAP+i*4:w for i,w in enumerate(struct.unpack_from('>24I',self.rom,0x172018))})
        count=0;visits=set()
        for angle,clock,phase in itertools.product((-90.,-7.,-0.,0.,.25,1.5,7.,90.,floating(0x7FC12345)),
                (0.,1.,-1.,4.),(0,8)):
            c=replace(Case(),fields=Case().fields[:3]+(bits(angle),)+Case().fields[4:],clock=bits(clock))
            expected,calls=reference(c,real=True);models=[]
            for words in (self.truth,self.words):
                m=MotionOracle(words,c,phase,connected=connected,real=True).run()
                self.assertEqual((public(m.memory),m.calls),(public(expected),calls))
                self.assertEqual(m.r[2],1);models.append(m);visits.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertTrue(set(range(source.WRAP,source.WRAP+96,4))<=visits)
        self.receipt.update(real_math_phases=count,sine_helper_words=104,wrap_helper_words=24,
            visited_helper_words=len(set(connected)&visits),all24_wrap_words_executed=True,
            huge_or_infinite_wrap_completion_not_claimed=True,FCSR_or_hardware_parity_not_claimed=True)

    def test_05_actual_slot35_original_dispatcher_return_gate_and_retained_stub(self):
        jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF));ptr=struct.pack('>I',source.ENTRY)
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[])
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==ptr],[0x22E804])
        registry=struct.unpack_from('>42I',self.rom,0x22E778)
        self.assertEqual((registry[0],registry[35]),(0,source.ENTRY))
        caller=list(struct.unpack_from('>195I',self.rom,0x16A494));count=0
        for active,slot,timer,counter,tick,mode,phase in itertools.product(
                range(2),(0,35),range(2),(-1,0,4),(0,1,3),range(4),(0,8)):
            c=Case(mode=mode);memory=fixture(c);p=address(c,SYMBOLS)
            for off,value,size in ((0x10,active,4),(0x58,timer,4),(0x70,slot,1),
                    (0x71,0,1),(0x72,0,1),(0x24,0,4),(0x1C,counter,2)):
                put(memory,p+off,value,size)
            put(memory,TICK,tick)
            for index,value in enumerate(registry):put(memory,TABLE+index*4,value)
            expected=dict(memory);calls=[];stop=False
            if active:
                if timer:
                    value=(counter-tick+32768)%65536-32768
                    put(expected,p+0x1C,value,2);stop=value<0
                if slot:
                    calls.append((source.ENTRY,(p,)))
                    expected,math_calls=reference(c,memory=expected);calls+=math_calls
                if stop:
                    put(expected,p+0x10,0);calls.append((RELEASE,(p,)))
            models=[]
            for words in (self.truth,self.words):
                connected={source.ENTRY+i*4:w for i,w in enumerate(words)}
                m=UpdateOracle(caller,c,phase,entry=UPDATE_CALLER,connected=connected,memory=memory).run()
                self.assertEqual((public(m.memory),m.calls),(public(expected),calls))
                self.assertEqual(m.r[29],STACK+phase);models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        old=self.values['conker/build/conker.us.elf']
        stale_words=struct.unpack_from('>43I',old,source.elf_slot_offset(old,source.ENTRY,172))
        c=Case();memory=fixture(c);p=address(c,SYMBOLS)
        for off,value,size in ((0x10,1,4),(0x58,0,4),(0x70,35,1),(0x71,0,1),(0x72,0,1),(0x24,0,4)):
            put(memory,p+off,value,size)
        put(memory,TABLE+35*4,source.ENTRY)
        stale=UpdateOracle(caller,c,entry=UPDATE_CALLER,memory=memory,
            connected={source.ENTRY+i*4:w for i,w in enumerate(stale_words)}).run()
        self.assertIn((RELEASE,(p,)),stale.calls)
        retained=struct.unpack_from('>195I',old,source.elf_slot_offset(old,UPDATE_CALLER,780))
        self.assertEqual(retained[:3],(0x00001025,0x03E00008,0))
        current=UpdateOracle(retained,c,entry=UPDATE_CALLER,memory=memory).run()
        self.assertFalse(current.calls);self.assertEqual(public(current.memory),public(memory))
        self.receipt.update(direct_sites=0,literal_pointer_ROM='22E804',callback_table='80089CB8',callback_slot=35,
            registry_entries=42,full_original_caller_words=195,connected_original_caller_phases=count,
            bounded_no_animation_no_secondary_callback=True,scripted_release_provider=True,
            all195_caller_words_executed_claimed=False,retained_parent_stub_bytes=12,
            retained_dispatcher_parity_claimed=False,production_gameplay_claimed=False,
            old_target_stub_wrong_return_gate_rejected=True)

    def test_06_independent_GNU_calls_and_signed_low_HILO_rebases(self):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        count=0
        for index,entry in enumerate((source.ENTRY,0x18017FFC,0x1A028000)):
            symbols=SYMBOLS if index==0 else dict(sinf=0x15088004+index*0x10000,
                func_15144B68=0x15197FFC+index*0x10000,D_800BE9A4=0x80348000+index*0x100000)
            images=[]
            for label,obj in (('original',source.original(ROOT,self.output)),('C',self.obj),('padded',self.output/'qualified-padded.o')):
                data,fs,rs=source.parse_object(obj);text,unknown=emit_function(data,fs[source.FUNCTION],rs,source.FUNCTION,symbols)
                self.assertEqual(unknown,[]);stem=self.output/('rebase-%d-%s'%(index,label))
                asm=stem.with_suffix('.s');asm.write_text(text);compiled=stem.with_suffix('.o');script=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(compiled),str(asm)],capture_output=True,check=True)
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%p for p in symbols.items()],'-o',str(elf),str(compiled)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>43I',sections(elf)['.text'][1])))
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for alias,mode,phase in itertools.product((None,0x40,0x118),range(4),(0,8)):
                c=Case(alias=alias,mode=mode);expected,calls=reference(c,symbols);models=[]
                for words in images:
                    m=MotionOracle(words,c,phase,symbols,entry).run()
                    self.assertEqual((public(m.memory),m.calls),(public(expected),calls));models.append(m)
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(complete(models[0]),complete(models[2]));count+=1
        self.receipt.update(independent_GNU_links=9,rebase_phases=count,six_bindings=True,signed_low_carry=True)

    def test_07_every_target_access_prefix_is_guest_only_evidence(self):
        count=0
        for mode,alias,phase in itertools.product((0,3),(None,0x40),(0,8)):
            c=Case(mode=mode,alias=alias)
            good=MotionOracle(self.truth,c,phase).run()
            for cut in range(good.root_accesses):
                models=[MotionOracle(words,c,phase)for words in (self.truth,self.words)]
                for m in models:
                    m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,cut)
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.assertGreater(count,0)
        self.receipt.update(target_access_fault_prefixes=count,portable_C_fault_claimed=False)

    def test_08_strict_image_and_live_input_history_negatives(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+172]
        predicted=source.predicted_image(before,truth);source.check_image(before,predicted,truth)
        at=source.elf_slot_offset(before,source.ENTRY,172)
        for offset in (0,at-1,at,at+168,at+172,len(before)-1):
            wrong=bytearray(predicted);wrong[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),truth)
        with self.assertRaises(ValueError):source.check_image(before,predicted[:-1],truth)
        for name,wanted in source.INPUTS.items():
            old=(self.output/('before-'+name.replace('/','_'))).read_bytes()
            self.assertEqual(source.digest(old),wanted)
            expected=source.recovered_owner(old.decode()).encode() if self.installed and name==source.SOURCE else (
                (self.output/'qualified-padded.o').read_bytes() if self.installed and name==source.OBJECT else
                predicted if self.installed and name=='conker/build/conker.us.elf' else old)
            self.assertEqual((ROOT/name).read_bytes(),expected)
        self.receipt.update(strict_image_negatives=7,frozen_and_live_inputs=len(source.INPUTS))

    def test_09_compiled_post_wrap_clock_cache_is_effectively_wrong_for_guest_alias(self):
        body=source.SELECTED.replace('    *(f32 *)(actor + 0x38) =',
            '    f32 cached;\n    *(f32 *)(actor + 0x38) =')
        body=body.replace('    *(f32 *)(actor + 0x40) +=',
            '    cached = D_800BE9A4;\n    *(f32 *)(actor + 0x40) +=')
        for name in ('velocityX','velocityZ'):
            body=body.replace('motion->'+name+' * D_800BE9A4','motion->'+name+' * cached')
        self.assertNotEqual(body,source.SELECTED)
        obj,diag=source.compile_owner(ROOT,self.output,
            '#include <ultra64.h>\n'+source.DECLARATIONS+source.TYPES+body,'negative-planar-clock-cache')
        self.assertFalse(diag)
        raw,bindings=source.payload(obj)
        with self.assertRaises(ValueError):source.checked_payload(raw,bindings)
        data,functions=source.link_owner(ROOT,self.output,obj,source.OWNER)
        words=struct.unpack_from('>%dI'%(len(raw)//4),data,functions[source.FUNCTION]['value'])
        case=Case(alias=0x40)
        correct=MotionOracle(self.truth,case).run();wrong=MotionOracle(words,case).run()
        self.assertNotEqual(public(correct.memory),public(wrong.memory))
        self.receipt.update(effective_compiled_planar_clock_cache_negative=True,
            guest_X_store_changes_clock_before_Z_load=True,portable_native_alias_claimed=False)

    def test_10_installed_input_map_and_six_live_and_frozen_mutations(self):
        original=Path.read_bytes
        actual={ROOT/name:data for name,data in self.values.items()}
        actual[ROOT/source.SOURCE]=source.recovered_owner(self.values[source.SOURCE].decode()).encode()
        actual[ROOT/source.OBJECT]=original(self.output/'qualified-padded.o')
        actual[ROOT/'conker/build/conker.us.elf']=source.predicted_image(
            self.values['conker/build/conker.us.elf'],self.rom[source.ROM:source.ROM+172])
        def read_input(path):return actual[path] if path in actual else original(path)
        with patch.object(Path,'read_bytes',read_input):source.audit_inputs(ROOT,self.output)
        names=(source.SOURCE,source.OBJECT,'conker/build/conker.us.elf',
            'conker/retail_word_patches.us.csv','conker/build/src/game_169510.c.o','conker/include/structs.h')
        count=0
        for name in names:
            for path in (ROOT/name,self.output/('before-'+name.replace('/','_'))):
                old=actual[path] if path in actual else original(path)
                wrong=bytearray(old);wrong[len(wrong)//2]^=1
                def corrupted(p):return bytes(wrong) if p==path else read_input(p)
                with patch.object(Path,'read_bytes',corrupted),self.assertRaises(ValueError):
                    source.audit_inputs(ROOT,self.output)
                count+=1
        with patch.object(Path,'read_bytes',lambda p:self.values[source.OBJECT] if p==ROOT/source.OBJECT else read_input(p)):
            with self.assertRaises(ValueError):source.audit_inputs(ROOT,self.output)
        self.receipt.update(valid_installed_map_accepted=True,installed_and_frozen_input_mutations_rejected=count,
            stale_installed_object_rejected=True,qualified_object_not_predecessor_required=True)
