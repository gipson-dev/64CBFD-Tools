"""Live attachment identity, unsigned matrix index, callback ABI and guarded ADDU."""

from dataclasses import dataclass, replace
from pathlib import Path
import csv
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_attachment_position as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.match_progress import add_retail_lengths, function_vram, load_symbol_addrs, DEFAULT_SEGMENTS
from tools.tests.test_game_point_transform_match import PointOracle, put, read, external_writes
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_effect_position_payload import complete

ROOT=Path(__file__).resolve().parents[2]
EFFECT,ACTOR,MATRICES=0x28000,0x30000,0x50000
STATUS,DIAGNOSTIC,FLAG=0x800DCA00,0x800DCA04,0x800C3E90
DISTANCE,REMOVE=0x15143E64,0x1516972C
CONVERT,TRANSFORM,TRANSLATE=0x151EFEB8,0x150A7960,0x15142314
COORDS=(0,0x80000000,1,0x007FFFFF,bits(1.75),bits(-2.75),bits(16777216.0),bits(1e20))
LOCAL=(bits(1.0),bits(-2.0),bits(0.5))


@dataclass(frozen=True)
class Case:
    state:int=1
    saved:int=255
    identity:int=255
    joint:int=255
    table:bool=True
    position:tuple=(bits(11.0),bits(-12.0),bits(13.0))
    local:tuple=LOCAL
    alias:int=0
    fixed:int=0


def corpus():
    for i in range(256):
        yield Case(saved=i,identity=i,joint=i,position=tuple(COORDS[(i+j)%len(COORDS)]for j in range(3)))
        yield Case(state=(0,1,0x80000000,0xFFFFFFFF)[i%4],saved=i,identity=i if i&1 else i^128,
                   joint=255-i,table=False,position=tuple(COORDS[(i+j+3)%len(COORDS)]for j in range(3)))
    for state,same,table,zero in itertools.product((0,1,0x80000000,0xFFFFFFFF),(False,True),(False,True),(False,True)):
        yield Case(state,128,128 if same else 127,128,table,local=(0,0x80000000,0)if zero else LOCAL)
    for alias in (1,2,3):
        for state,same in itertools.product((0,1),(False,True)):
            yield Case(state=state,identity=255 if same else 0,table=False,alias=alias)


def active(case):
    return bool(case.state and case.saved==case.identity)


def actor_address(case):
    return (ACTOR,EFFECT+0xC,EFFECT+0x10,EFFECT+0x14)[case.alias]


def fixture(case,callback=1,enabled=1):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x800,0x200)}
    memory.update({EFFECT+i:0xA5 for i in range(-16,0x110)})
    actor=actor_address(case)
    memory.update({actor+i:0xA5 for i in range(-16,0x33C)})
    selected=MATRICES+case.joint*64
    memory.update({selected+i:0xA5 for i in range(-16,80)})
    for i in range(3):
        put(memory,EFFECT+0x18+i*4,bits(100.0+i))
        put(memory,EFFECT+0x24+i*4,bits(200.0+i))
    put(memory,EFFECT+0x10,enabled);put(memory,EFFECT+0x30,callback&255,1)
    put(memory,EFFECT+0xC0,bits(-77.0));put(memory,EFFECT+0xC8,actor)
    put(memory,EFFECT+0xCC,case.saved,1);put(memory,EFFECT+0xCD,case.joint,1)
    for i,w in enumerate(case.local):
        put(memory,EFFECT+0xD0+i*4,w)
    for i,w in enumerate(case.position):
        put(memory,actor+0x14+i*4,w)
    put(memory,actor,case.state);put(memory,actor+0x3B,case.identity,1)
    put(memory,actor+0x1D4,MATRICES if case.table else 0)
    for at in (STATUS,DIAGNOSTIC,STATUS+8,STATUS+12,STATUS+16):
        put(memory,at,0x11223344)
    put(memory,FLAG,case.fixed,1);put(memory,source.TABLE,0x150C5B88);put(memory,source.TABLE+4,source.ENTRY)
    values=[0.0]*16
    values[0],values[5],values[10],values[15]=0.5,1.0,2.0,1.0
    values[12:15]=3.0,-4.0,5.0
    if case.fixed:
        ints=[int(v*65536)&0xFFFFFFFF for v in values]
        payload=struct.pack('>32H',*[w>>16 for w in ints],*[w&65535 for w in ints])
    else:
        payload=struct.pack('>16I',*[bits(v)for v in values])
    memory.update({selected+i:b for i,b in enumerate(payload)})
    return memory


def reference(case,initial=None):
    memory=dict(fixture(case)if initial is None else initial)
    actor=read(memory,EFFECT+0xC8)
    if read(memory,actor)==0 or read(memory,EFFECT+0xCC,1)!=read(memory,actor+0x3B,1):
        return 0,tuple(read(memory,EFFECT+0x24+i*4)for i in range(3)),[]
    matrix=read(memory,actor+0x1D4)
    packets=[]
    if matrix:
        args=(EFFECT+0xD0,EFFECT+0x24,matrix+read(memory,EFFECT+0xCD,1)*64)
        local=tuple(read(memory,args[0]+i*4)for i in range(3))
        packets=[(args,local)]
        for i,w in enumerate(local):
            put(memory,EFFECT+0x24+i*4,bits(floating(w)+float(i+1)))
    else:
        for i in range(3):
            live=read(memory,EFFECT+0xC8)
            put(memory,EFFECT+0x24+i*4,read(memory,live+0x14+i*4))
    return 1,tuple(read(memory,EFFECT+0x24+i*4)for i in range(3)),packets


class AttachmentOracle(PointOracle):
    def __init__(self,words,case,phase=0,delta=0,entry=source.ENTRY,connected=None,callback=1,enabled=1):
        self.case,self.delta=case,delta
        self.packets,self.distances,self.removals=[],[],[]
        super().__init__(words,fixture(case,callback,enabled),(EFFECT,),phase=phase,entry=entry,connected=connected)
        self.hi=0

    def execute(self,word):
        if word>>26==32:
            rs,rt=word>>21&31,word>>16&31
            immediate=(word&65535)-(65536 if word&0x8000 else 0)
            value=self.get((self.r[rs]+immediate)&0xFFFFFFFF,1)
            self.r[rt]=((value^128)-128)&0xFFFFFFFF
            self.r[0]=0
        else:
            super().execute(word)

    def record_call(self,target):
        if target==source.TRANSFORM+self.delta:
            args=self.arguments(3)
            local=tuple(read(self.memory,args[0]+i*4)for i in range(3))
            self.packets.append((args,local))
        elif target==source.ENTRY:
            args=self.arguments(1);assert args==(EFFECT,)
        elif target==DISTANCE:
            args=self.arguments(1);self.distances.append(tuple(read(self.memory,args[0]+i*4)for i in range(3)))
        elif target==REMOVE:
            args=self.arguments(1);self.removals.append(args);assert args==(EFFECT,)
        else:
            return super().record_call(target)
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        if target==source.TRANSFORM+self.delta:
            a,b,_=self.arguments(3)
            for i in range(3):
                self.put(b+i*4,bits(floating(read(self.memory,a+i*4))+float(i+1)),4)
        elif target not in (DISTANCE,REMOVE):
            return super().hook(target)
        for i in range(4):
            self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):
            self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=0x87654321;self.hi,self.lo=0x87654321,0x12345678
        if target==DISTANCE:
            self.f[0]=bits(123.5)


def native_harness(body,cases):
    rows=[]
    for c in cases:
        result,position,_=reference(c)
        rows.append('{%s,{%s},{%s},{%s}}'%(
            ','.join('0x%Xu'%w for w in (c.state,c.saved,c.identity,c.joint,c.table,result)),
            ','.join('0x%Xu'%w for w in c.position),
            ','.join('0x%Xu'%w for w in c.local),
            ','.join('0x%Xu'%w for w in position)))
    return '''typedef unsigned int u32;typedef int s32;typedef unsigned char u8;typedef float f32;
typedef struct struct255 struct255;
typedef struct{ s32 interaction_state;u8 pad4[0x10];f32 x_position,y_position,z_position;
u8 pad20[0x1B];u8 unique_id;u8 pad3C[0x198];struct255 *unk1D4;}struct127;
#define NULL ((void *)0)
''' + source.DECLARATIONS.replace('#include "structs.h"','') + body + '''
typedef struct{u32 state,saved,identity,joint,table,result,position[3],local[3],output[3];}Case;
static const Case cases[]={''' + ',\n'.join(rows) + '''};
static const Case *item;
static union{double align;u8 bytes[16+0x100+16];}storage;
static union{double align;u8 bytes[256*64];}matrices;
static struct{u32 before[4];struct127 actor;u32 after[4];}owner;
static int calls,error;
static u8 *effect;
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
__attribute__((noinline))void func_15143134(f32 *point,f32 *out,u8 *matrix){
    u32 i;
    calls++;
    if(point!=(f32 *)(effect+0xD0) || out!=(f32 *)(effect+0x24) ||
       matrix!=matrices.bytes+item->joint*64){error=1;return;}
    for(i=0;i<3;i++){
        if(word(point[i])!=item->local[i])error=1;
        out[i]=point[i]+(f32)(i+1);
    }
}
static int test_all(void){
    u32 n,i,result;int expectedCalls;u8 old[0x100];
    s32 (*callbacks[2])(u8 *)={0,func_150C5BD4};
    if(sizeof(void *)!=4 || __builtin_offsetof(struct127,x_position)!=0x14 ||
       __builtin_offsetof(struct127,unique_id)!=0x3B || __builtin_offsetof(struct127,unk1D4)!=0x1D4)return 90;
    for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
        item=&cases[n];calls=error=0;effect=storage.bytes+16;
        for(i=0;i<sizeof(storage);i++)storage.bytes[i]=0xA5;
        for(i=0;i<sizeof(owner);i++)((u8 *)&owner)[i]=0xA5;
        owner.actor.interaction_state=(s32)item->state;owner.actor.unique_id=(u8)item->identity;
        owner.actor.unk1D4=item->table?(struct255 *)matrices.bytes:0;
        owner.actor.x_position=real(item->position[0]);owner.actor.y_position=real(item->position[1]);owner.actor.z_position=real(item->position[2]);
        *(struct127 **)(effect+0xC8)=&owner.actor;effect[0xCC]=(u8)item->saved;effect[0xCD]=(u8)item->joint;
        for(i=0;i<3;i++){*(f32 *)(effect+0x24+i*4)=(f32)(200+i);*(f32 *)(effect+0xD0+i*4)=real(item->local[i]);}
        for(i=0;i<0x100;i++)old[i]=effect[i];
        result=(u32)callbacks[1](effect);expectedCalls=item->result && item->table;
        if(error || calls!=expectedCalls || result!=item->result)return 23;
        for(i=0;i<3;i++)if(word(*(f32 *)(effect+0x24+i*4))!=item->output[i])return 23;
        for(i=0;i<0x100;i++)if((i<0x24 || i>=0x30) && effect[i]!=old[i])return 24;
        for(i=0;i<16;i++)if(storage.bytes[i]!=0xA5 || storage.bytes[0x110+i]!=0xA5)return 25;
        for(i=0;i<4;i++)if(owner.before[i]!=0xA5A5A5A5u || owner.after[i]!=0xA5A5A5A5u)return 26;
        if(word(owner.actor.x_position)!=item->position[0] || word(owner.actor.y_position)!=item->position[1] ||
           word(owner.actor.z_position)!=item->position[2] || owner.actor.unique_id!=item->identity ||
           (u32)owner.actor.interaction_state!=item->state)return 27;
    }
    return 0;
}
__attribute__((noreturn))void _start(void){int status=test_all();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class AttachmentPositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=ROOT/source.BUILD
        cls.installed=source.digest((ROOT/source.SOURCE).read_bytes())!=source.INPUTS[source.SOURCE]
        if cls.installed:
            source.audit(ROOT,cls.output)
        else:
            source.freeze(ROOT,cls.output)
            if not (cls.output/'first-link.json').exists():
                source.qualify(ROOT,cls.output);source.make_shadow(ROOT,cls.output);source.predict(ROOT,cls.output)
        cls.values=source.snapshot(cls.output)
        cls.obj,diag=source.compile_owner(ROOT,cls.output,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:
            raise ValueError(diag)
        data,functions=source.link_owner(ROOT,cls.output,cls.obj,source.OWNER)
        cls.raw=list(struct.unpack_from('>40I',data,functions[source.FUNCTION]['value']))
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>40I',cls.rom,source.ROM))
        cls.fitted=cls.raw.copy();cls.fitted[34]=0x010C3021
        cls.cases=list(corpus());cls.native_cases=[c for c in cls.cases if not c.alias]
        cls.receipt=dict(installed=cls.installed,cases=len(cls.cases),native_cases=len(cls.native_cases),guards=1)

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('attachment position qualification:',cls.receipt)

    def test_01_exact_guard_closed_commutation_frame_and_dead_words(self):
        self.assertEqual([i for i,(a,b)in enumerate(zip(self.raw,self.truth))if a!=b],[34])
        self.assertEqual(self.fitted,self.truth)
        raw,bindings=source.payload(self.obj)
        self.assertEqual(source.normalized(raw,bindings),source.payload(source.original(ROOT,self.output)))
        self.assertEqual(bindings,{0x84:[('R_MIPS_26','func_15143134')]})
        self.assertEqual(self.raw[0],0x27BDFFE8)
        for word in (self.raw[34],self.truth[34]):
            self.assertEqual((word>>26,word&63,word>>11&31),(0,33,6))
            self.assertEqual({word>>21&31,word>>16&31},{8,12})
        for a,b in itertools.product((0,1,63,64,0x7FFFFFFF,0x80000000,0xFFFFFFC0,0xFFFFFFFF),repeat=2):
            self.assertEqual((a+b)&0xFFFFFFFF,(b+a)&0xFFFFFFFF)
        self.assertEqual([self.raw[i]for i in (10,17,29)],[0x8C430000,0x8C6801D4,0x904B0005])
        self.receipt.update(raw_words=40,frame=24,raw_differences=1,guarded_differences=0,
            only_commutative_wrapping_ADDU=True,retained_unreachable_words=[10,17,29])

    def test_02_three_way_complete_states_independent_reference_and_aliases(self):
        visits=set();indices=set()
        for case,phase in itertools.product(self.cases,(0,8)):
            models=[AttachmentOracle(code,case,phase).run()for code in (self.truth,self.raw,self.fitted)]
            expected,position,packets=reference(case)
            for m in models:
                self.assertEqual(m.r[2],expected)
                self.assertEqual(tuple(read(m.memory,EFFECT+0x24+i*4)for i in range(3)),position)
                self.assertEqual(m.packets,packets)
                for reg in (*range(16,24),28,29,30,31):
                    self.assertEqual(m.r[reg],m.before[reg])
                self.assertEqual(m.f[20:],m.saved_f);visits.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[1]))
            self.assertEqual(complete(models[0]),complete(models[2]))
            if case.table and active(case):
                indices.add(case.joint)
        self.assertEqual(indices,set(range(256)))
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+160,4))-visits,
                         {source.ENTRY+i*4 for i in (10,17,29)})
        self.receipt.update(three_way_model_phases=len(self.cases)*2,reachable_target_words=37,
            all_unsigned_matrix_indices=True,guest_overlap_cases=sum(bool(c.alias)for c in self.cases))
        for case in (Case(state=0),Case(identity=0),Case(table=False)):
            for code in (self.truth,self.raw,self.fitted):
                m=AttachmentOracle(code,case)
                missing=ACTOR+0x1D4 if not active(case) else EFFECT+0xD0
                del m.memory[missing]
                m.run()
        for code in (self.truth,self.raw,self.fitted):
            m=AttachmentOracle(code,Case())
            put(m.memory,EFFECT+0xC8,0)
            with self.assertRaises(AssertionError):
                m.run()
            self.assertIn(source.ENTRY+5*4,m.visits)
        self.receipt.update(lazy_inactive_and_world_copy_reads=True,
            NULL_actor_faults_at_original_state_read=True,portable_C_NULL_claimed=False)

    def native(self,body,label,opt='-O2'):
        unit=self.output/(label+'.c');unit.write_text(native_harness(body,self.native_cases))
        binary=self.output/(label+opt)
        args=['gcc','-m32',opt,'-std=c99','-fno-strict-aliasing','-ffreestanding','-nostdlib','-static',
            '-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-mstackrealign','-ffp-contract=off',
            '-fsanitize=undefined,float-cast-overflow','-fsanitize-undefined-trap-on-error',
            '-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(unit),'-o',str(binary)]
        p=subprocess.run(args,capture_output=True,text=True)
        (self.output/(label+opt+'-compiler.log')).write_text(p.stdout+p.stderr)
        self.assertEqual(p.returncode,0,p.stderr[:3000])
        return subprocess.run([str(binary)],capture_output=True,timeout=30).returncode

    def test_03_native32_callback_and_effective_compiled_controls(self):
        for opt in ('-O0','-O2','-O3'):
            self.assertEqual(self.native(source.SELECTED,'native',opt),0)
        controls={
            'missing-live-gate':source.SELECTED.replace('->interaction_state == 0','->interaction_state == 12345'),
            'wrong-identity-gate':source.SELECTED.replace('attachment[4] !=','attachment[4] =='),
            'wrong-x-field':source.SELECTED.replace('->x_position','->y_position'),
            'wrong-output':source.SELECTED.replace('effect + 0x24','effect + 0x20'),
            'wrong-point':source.SELECTED.replace('attachment + 8','attachment + 4'),
            'wrong-index-width':source.SELECTED.replace('attachment[5] << 6','(attachment[5] & 127) << 6'),
            'wrong-index-stride':source.SELECTED.replace('attachment[5] << 6','attachment[5] << 5'),
            'wrong-success-value':source.SELECTED.replace('return 1;','return 2;'),
            'wrong-failure-value':source.SELECTED.replace('return 0;','return 1;'),
        }
        for name,body in controls.items():
            self.assertNotEqual(body,source.SELECTED)
            self.assertEqual(self.native(body,name),23,name)
        self.receipt.update(native_optimizations=3,trap_UBSan=True,compiled_semantic_controls=len(controls),
            valid_native32_callback_ABI=True,native_overlap_claimed=False)

    def test_04_guard_prefix_expected_word_binding_and_omission_controls(self):
        old=self.values['conker/retail_word_patches.us.csv']
        wanted=source.guard_bytes(self.values)
        self.assertEqual(wanted,old+source.GUARD_ROW)
        if self.installed:
            self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),wanted)
        for label,row in (
            ('wrong-expected',source.GUARD_ROW.replace(b'0x01883021',b'0x01883020')),
            ('wrong-offset',source.GUARD_ROW.replace(b'0x088',b'0x084')),
            ('wrong-binding',source.GUARD_ROW.replace(b',-,-,',b',R_MIPS_26:func_15143134,-,'))):
            path=self.output/(label+'-guards.csv');path.write_bytes(old+row)
            with self.assertRaises(ValueError):
                source.emit_padded_assembly(self.output/'after-owner.o',ROOT/source.ASM,word_patches_path=path,filename=source.OWNER)
        bad=bytearray(source.payload(self.obj)[0]);struct.pack_into('>I',bad,0x88,0x01883020)
        with self.assertRaises(ValueError):
            source.normalized(bad,source.payload(self.obj)[1])
        with self.assertRaises(ValueError):
            source.normalized(source.payload(self.obj)[0],{})
        self.assertNotEqual(self.raw,self.truth)
        # A wrong replacement can emit assembly, so check the actual assembled result.
        path=self.output/'wrong-replacement-guards.csv'
        path.write_bytes(old+source.GUARD_ROW.replace(b'0x010C3021',b'0x010C3023'))
        assembly=self.output/'wrong-replacement.s'
        assembly.write_text(source.emit_padded_assembly(self.output/'after-owner.o',ROOT/source.ASM,
            word_patches_path=path,filename=source.OWNER))
        obj=assembly.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
            '-I',str(ROOT/'conker/include'),'-o',str(obj),str(assembly)],capture_output=True,check=True)
        data,functions=source.link_owner(ROOT,self.output,obj,source.OWNER)
        bad=list(struct.unpack_from('>40I',data,functions[source.FUNCTION]['value']))
        self.assertEqual(bad[34],0x010C3023);self.assertNotEqual(bad,self.truth)
        self.assertNotEqual(AttachmentOracle(bad,Case()).run().packets,reference(Case())[2])
        self.receipt.update(guard_prefix_byte_identical=True,guard_corruption_controls=6,
            omission_breaks_word_identity=True)

    def test_05_callback_inventory_and_complete_original_caller(self):
        symbols=load_symbol_addrs(str(ROOT/'conker/symbol_addrs.us.txt'))
        rows=list(csv.DictReader((ROOT/'conker/progress.csv').open()))
        add_retail_lengths(rows,'us',DEFAULT_SEGMENTS['us'],symbols)
        opcode=0x0C000000|(source.ENTRY>>2&0x3FFFFFF);found=[]
        for row in rows:
            if row['version']!='us' or row['section'] not in DEFAULT_SEGMENTS['us']:
                continue
            base,start=DEFAULT_SEGMENTS['us'][row['section']];entry=function_vram(row,symbols)
            words=struct.unpack_from('>%dI'%row['_retail_nwords'],self.rom,entry-base+start)
            found.extend((row['function'],entry+i*4)for i,w in enumerate(words)if w==opcode)
        self.assertEqual(found,[])
        pointers=[i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==struct.pack('>I',source.ENTRY)]
        self.assertEqual(pointers,[0x22D224])
        self.assertEqual(struct.unpack_from('>2I',self.rom,0x22D220),(0x150C5B88,source.ENTRY))
        caller=list(struct.unpack_from('>79I',self.rom,0xF2A18))
        self.assertEqual(caller[29],0x0320F809)
        count=0;visits=set()
        for case,callback,enabled,phase in itertools.product(
                (Case(),Case(table=False),Case(state=0),Case(identity=0),
                 Case(local=tuple(map(bits,(199.0,-2.0,0.5)))),
                 Case(local=tuple(map(bits,(199.0,199.0,0.5)))),
                 Case(local=tuple(map(bits,(199.0,199.0,199.0))))),(1,-1),(0,1),(0,8)):
            initial=fixture(case,callback,enabled);reached=callback==1 and enabled
            ok,new,_=reference(case,initial) if reached else (1,tuple(read(initial,EFFECT+0x24+i*4)for i in range(3)),[])
            expected_delta=tuple(bits(floating(read(initial,EFFECT+0x18+i*4))-floating(new[i]))for i in range(3))
            old_delta=tuple(bits(floating(read(initial,EFFECT+0x18+i*4))-floating(read(initial,EFFECT+0x24+i*4)))for i in range(3))
            moved=bool(enabled and ok and expected_delta!=old_delta)
            models=[]
            for code in (self.truth,self.raw,self.fitted):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+160,4),code))
                m=AttachmentOracle(caller,case,phase,entry=source.CALLER,connected=connected,callback=callback,enabled=enabled).run()
                self.assertEqual(m.removals,[(EFFECT,)] if reached and not ok else [])
                self.assertEqual(m.distances,[expected_delta] if moved else [])
                self.assertEqual(read(m.memory,EFFECT+0xC0),bits(123.5)if moved else bits(-77.0))
                models.append(m);visits.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(complete(models[0]),complete(models[2]));count+=1
        self.assertTrue(set(range(source.CALLER,source.CALLER+316,4))<=visits)
        self.receipt.update(direct_JALs=found,aligned_target_pointers=pointers,
            complete_caller_phases=count,all79_caller_words=True,callback_result_controls_removal=True,
            distance_and_remove_bounded=True)

    def test_06_independent_GNU_call_rebases(self):
        count=0
        for delta in (0x10000,0xCF20,0x18000):
            images=[]
            for i,path in enumerate((self.obj,source.original(ROOT,self.output))):
                elf=self.output/('rebase-%d-%d.elf'%(delta,i));script=self.output/'rebase.ld'
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    '--defsym=func_15143134=0x%X'%(source.TRANSFORM+delta),'-o',str(elf),str(path)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>40I',sections(elf)['.text'][1])))
            a,b=images
            fitted=a.copy();fitted[34]=0x010C3021;self.assertEqual(fitted,b)
            for case in self.cases[::31]:
                models=[AttachmentOracle(code,case,delta=delta).run()for code in (a,b,fitted)]
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(complete(models[0]),complete(models[2]));count+=1
        self.receipt.update(rebase_sets=3,independent_rebase_phases=count)

    def test_07_actual_transform_helper_and_original_lower_math(self):
        helpers={source.TRANSFORM:(0x1705E4,98),CONVERT:(0x21D368,46),TRANSFORM:(0xD4E10,40),TRANSLATE:(0x16F7C4,49)}
        connected={}
        for address,(offset,words)in helpers.items():
            connected.update(zip(range(address,address+words*4,4),struct.unpack_from('>%dI'%words,self.rom,offset)))
        count=0;visits=set()
        locals_=(LOCAL,(bits(1.0),0,0),(0,bits(-2.0),0),(0,0,bits(0.5)),(0,0x80000000,0))
        for fixed,joint,local,phase in itertools.product((0,1,255),(0,128,255),locals_,(0,8)):
            case=Case(fixed=fixed,joint=joint,local=local)
            zero=not any(floating(w)!=0.0 for w in local)
            expected=tuple(bits(floating(local[i])*(0.5,1.0,2.0)[i]+(3.0,-4.0,5.0)[i])for i in range(3))
            models=[]
            for code in (self.truth,self.raw,self.fitted):
                m=AttachmentOracle(code,case,phase,connected=connected).run()
                self.assertEqual(m.r[2],1)
                self.assertEqual(tuple(read(m.memory,EFFECT+0x24+i*4)for i in range(3)),expected)
                self.assertEqual(read(m.memory,STATUS),0)
                statuses=[e[3]for e in external_writes(m)if e[1]==STATUS]
                self.assertEqual(statuses,[1,7,8,0]if zero else [1,2,3,4,0]if fixed else [1,2,5,6,0])
                models.append(m);visits.update(m.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(complete(models[0]),complete(models[2]));count+=1
        wanted=set(connected)-{CONVERT+45*4}
        self.assertEqual(wanted-visits,{source.TRANSFORM+0x148})
        self.assertEqual(connected[source.TRANSFORM+0x30],0x12000045)
        self.assertEqual(connected[source.TRANSFORM+0x148],0x240F0007)
        self.receipt.update(original_math_chain_phases=count,reachable_helper_words=97,
            helper_slot_words=98,NULL_only_helper_word_unreached=82,
            sdk_slot_words=46,sdk_reachable_words=45,all40_matrix_words=True,all49_translation_words=True,
            finite_exact_fixed_domain=True,hardware_FCSR_claimed=False)

    def test_08_strict_image_controls(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+160]
        predicted=source.predicted_image(before,truth)
        self.assertEqual(predicted,(self.output/'first-linked.elf').read_bytes())
        offsets=(20,source.elf_slot_offset(predicted,source.ENTRY,160),
            source.elf_slot_offset(predicted,0x15001000,4),source.elf_slot_offset(predicted,0x80082B20,4),
            next(at+8 for at,name,_,_ in source.symbol_rows(predicted)if name==source.FUNCTION))
        for at in offsets:
            bad=bytearray(predicted);bad[at]^=1
            with self.assertRaises(ValueError):
                source.check_image(before,bad,truth)
        for bad in (predicted[:-1],predicted+b'\0'):
            with self.assertRaises(ValueError):
                source.check_image(before,bad,truth)
        self.receipt['strict_image_controls']=7
