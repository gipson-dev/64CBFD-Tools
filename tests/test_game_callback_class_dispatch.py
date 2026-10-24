"""Direct class dispatch: original helpers/caller, native ABI and strict image."""
from dataclasses import dataclass
from pathlib import Path
import itertools
import json
import re
import struct
import subprocess
import unittest

from tools.experiments import game_callback_class_dispatch as source
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
ACTOR,WORLD,TABLE,ROW,MASK=0x30000,0x800BE9F0,0x8008F860,0x151928B0,0x1510F8CC
PARENT,PARENT_ROM=0x15071DF4,0x9F2A4
REAL_ROWS=(0x8008F840,0x8008F850)
REAL_CALLBACKS=(0x15192920,0x151B1AB0)
JT=0x800A8160


@dataclass(frozen=True)
class Case:
    identity:int=0
    kind:int=5
    world:int=20
    table:int=1
    unused:int=0x87654321
    mode:int=0
    null:bool=False
    layout:int=0


def actor_at(c,sp):
    return 0 if c.null else (ACTOR,sp+44-0x184,sp+48)[c.layout]


def fixture(c,phase=0,world=WORLD,table=TABLE,parent=False):
    sp=STACK+phase-48-(24 if parent else 0);actor=actor_at(c,sp)
    m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,1024)}
    if actor:m.update({actor+i:(i*13+0xA5)&255 for i in range(0x400)})
    if actor:put(m,actor+4,c.identity,1);put(m,actor+0x184,c.kind)
    put(m,world,c.world)
    for i in range(5):put(m,JT+4*i,0x151928F4)
    for row,base in enumerate(REAL_ROWS):
        put(m,table+row*4,base)
        for col in range(4):
            value=(REAL_CALLBACKS[row]if col==2 else 0)if c.table==0 else (0x1A003000+row*0x100+col*4 if c.table==1 else 0)
            put(m,base+col*4,value)
    if parent:put(m,0x800D154C,actor);put(m,0x800D1580,c.unused)
    return m,actor,sp


def public(m):return {a:b for a,b in m.items()if not STACK-2048<=a<STACK+1024}


def callback_effect(m,actor,world,mode):
    if mode:put(m,actor+0x3B,0xE7,1);put(m,world,0x87654321)


def reference(initial,c,actor,sp,world=WORLD,table=TABLE):
    m=dict(initial);calls=[]
    put(m,sp+52,c.unused)
    if actor:
        put(m,sp+48,actor);calls.append((ROW,(actor,sp+44)))
        identity=read(m,actor+4,1)
        if identity<=4 or identity==0x53:
            row=identity==0x53;put(m,sp+44,int(row))
            raw=read(m,actor+0x184);calls.append((MASK,(raw,)))
            kind=raw&31
            column=2 if kind==5 and read(m,world)==20 else 3 if kind==6 else 1
            target=read(m,read(m,table+4*int(row))+4*column)
            if target:calls.append((target,(actor,)));callback_effect(m,actor,world,c.mode)
    return m,calls


class DispatchOracle(TimingOracle):
    def __init__(self,words,memory,c=Case(),actor=ACTOR,phase=0,entry=source.ENTRY,connected=None,world=WORLD):
        super().__init__(words,memory,phase=phase,entry=entry,arguments=(actor,c.unused),connected=connected)
        self.dispatch_case,self.dispatch_world=c,world

    def record_call(self,target):
        n=2 if target in(ROW,source.ENTRY)else 1
        assert target in(ROW,MASK,source.ENTRY,*REAL_CALLBACKS)or 0x1A003000<=target<=0x1A00310C,hex(target)
        args=self.arguments(n);self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        assert target in REAL_CALLBACKS or 0x1A003000<=target<=0x1A00310C,hex(target)
        actor=self.calls[-1][1][0];callback_effect(self.memory,actor,self.dispatch_world,self.dispatch_case.mode)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for register in(1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]


def corpus():
    for identity,phase in itertools.product(range(256),(0,8)):
        yield Case(identity=identity),phase
    for identity,kind,world,table,phase,mode in itertools.product((0,4,5,83,84,255),range(32),(19,20,21),(0,1,2),(0,8),(0,1)):
        yield Case(identity,kind|0x87654000,world,table,0xFEDCBA98,mode),phase
    for unused,phase in itertools.product((0,1,0x80000000,0xFFFFFFFF),(0,8)):
        yield Case(unused=unused,null=True),phase


def controls():
    b=source.SELECTED[source.FUNCTION]
    return dict(selected=b,wrong_kind5=b.replace('case 5:','case 4:'),wrong_kind6=b.replace('case 6:','case 7:'),
        wrong_world=b.replace('== 0x14','== 0x13'),wrong_special=b.replace('column = 2;','column = 3;'),
        wrong_six=b.replace('column = 3;','column = 2;'),wrong_default=b.replace('default:\n                column = 1;','default:\n                column = 2;'),
        wrong_row=b.replace('D_8008F860[row]','D_8008F860[row ^ 1]'),
        wrong_actor=b.replace('callback(actor);','callback(wrongActor);'),
        missing_callback=b.replace('callback(actor);','(void)actor;'),
        reject_four=b.replace('func_151928B0(actor, &row))','func_151928B0(actor, &row) && ((u8 *)actor)[4] != 4)'))


def native_harness(values):
    helper=values[source.SOURCE].decode();lo,hi=source.function_span(helper,'func_151928B0')
    caller=values[source.CALLER_SOURCE].decode();a,z=source.function_span(caller,'func_15071DF4')
    text=source.HEADERS+'#include "structs.h"\n'+source.DECLARATIONS+'''
static struct127 actual,other;
static void *wrongActor=&other;
struct127 *D_800D154C;
s32 D_800D1580,D_800BE9F0;
static ClassCallback1BFCB0 rows[2][4];
ClassCallback1BFCB0 *D_8008F860[]={rows[0],rows[1]};
static u32 calls,rowCalls,maskCalls,seenKind,seenIndex,seenActor,mode;
static void cb0(u8*p){calls++;seenIndex=0;seenActor=p==(u8*)&actual;if(mode){p[0x3B]=0xE7;D_800BE9F0=(s32)0x87654321u;}}
static void cb1(u8*p){cb0(p);seenIndex=1;}
static void cb2(u8*p){cb0(p);seenIndex=2;}
static void cb3(u8*p){cb0(p);seenIndex=3;}
static void cb4(u8*p){cb0(p);seenIndex=4;}
static void cb5(u8*p){cb0(p);seenIndex=5;}
static void cb6(u8*p){cb0(p);seenIndex=6;}
static void cb7(u8*p){cb0(p);seenIndex=7;}
static ClassCallback1BFCB0 functions[]={cb0,cb1,cb2,cb3,cb4,cb5,cb6,cb7};
typedef char actor_kind_offset[__builtin_offsetof(struct127,unk184)==0x184?1:-1];
'''+helper[lo:hi].replace('func_151928B0','row_helper')+'''
s32 func_151928B0(u8*p,s32*out){rowCalls++;return row_helper(p,out);}
s32 func_1510F8CC(s32 word){maskCalls++;seenKind=(u32)word;return word&31;}
'''
    for name,body in controls().items():
        if name!='selected'and body==source.SELECTED[source.FUNCTION]:raise ValueError(name)
        text+=body.replace(source.FUNCTION,name)+'\n'
    text+='void func_15192800(void*p,s32 v){selected(p,v);}\n'+caller[a:z]+'''
typedef void(*Dispatch)(void*,s32);
static int variant(Dispatch fn,u32 wrapped){
 u32 id,kind,world,table,i,row,col,want,valid,expectCalls,upper,mutation;
 for(id=0;id<256;id++)for(kind=0;kind<32;kind++)for(world=19;world<=21;world++)for(table=0;table<3;table++)for(mutation=0;mutation<2;mutation++){
  for(i=0;i<sizeof(actual);i++)((u8*)&actual)[i]=(u8)(i*13+0xA5);
  for(i=0;i<sizeof(other);i++)((u8*)&other)[i]=(u8)(i*7+0x55);
  upper=(id&1)?0x87654000u:0;actual.id=(u8)id;actual.unk184=(s32)(upper|kind);
  for(row=0;row<2;row++)for(col=0;col<4;col++)rows[row][col]=table==1?functions[row*4+col]:(table==0&&col==2?functions[row*4+col]:0);
  D_800BE9F0=(s32)world;D_800D154C=&actual;D_800D1580=(s32)0xFEDCBA98u;
  mode=mutation;calls=rowCalls=maskCalls=0;seenKind=seenIndex=seenActor=0;
  valid=id<=4||id==83;row=id==83;col=kind==5&&world==20?2:kind==6?3:1;
  expectCalls=valid&&(table==1||(table==0&&col==2));want=row*4+col;
  if(wrapped)func_15071DF4();else fn(&actual,(s32)0xFEDCBA98u);
  if(rowCalls!=1||maskCalls!=valid||calls!=expectCalls)return 23;
  if(valid&&seenKind!=(upper|kind))return 23;
  if(expectCalls&&(seenIndex!=want||!seenActor))return 23;
  if((u32)D_800BE9F0!=(expectCalls&&mutation?0x87654321u:world))return 23;
  for(i=0;i<sizeof(actual);i++){
   u8 expected=(u8)(i*13+0xA5);
   if(i==4)expected=(u8)id;
   if(i>=0x184&&i<0x188)expected=((u8*)&actual.unk184)[i-0x184];
   if(i==0x3B&&expectCalls&&mutation)expected=0xE7;
   if(((u8*)&actual)[i]!=expected)return 23;
  }
  if((u32)actual.unk184!=(upper|kind))return 23;
 }
 for(i=0;i<4;i++){calls=rowCalls=maskCalls=0;fn(0,(s32)(0x87654321u+i));if(calls||rowCalls||maskCalls)return 23;}
 return 0;
}
int run(void){
'''
    for i,label in enumerate(controls()):text+='if(variant(%s,0)!=%d)return %d;\n'%(label,0 if label=='selected'else 23,i+1)
    return text+'if(variant(selected,1))return 70;return 0;}\n'+START


class ClassDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.receipt={}
        if(ROOT/source.SOURCE).read_bytes()==cls.values[source.SOURCE]:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        else:source.audit(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>44I',cls.rom,source.ROM))
        cls.images=[]
        for obj in(cls.out/'after-owner.o',cls.out/'qualified-padded.o',cls.out/'make-shadow-target/src/game/generated_1BFCB0.c.o'):
            data,fs=source.link_owner(ROOT,cls.out,obj,source.OWNER);cls.images.append(list(struct.unpack_from('>44I',data,fs[source.FUNCTION]['value'])))
        cls.connected={ROW+4*i:w for i,w in enumerate(struct.unpack_from('>26I',cls.rom,0x1BFD60))}
        cls.connected.update({MASK+4*i:w for i,w in enumerate(struct.unpack_from('>3I',cls.rom,0x13CD7C))})

    def compare(self,c,phase=0,parent=False):
        initial,actor,sp=fixture(c,phase,parent=parent);expected,calls=reference(initial,c,actor,sp)
        connected=dict(self.connected);models=[]
        for words in(self.truth,*self.images):
            code=words;entry=source.ENTRY
            if parent:connected.update({source.ENTRY+4*i:w for i,w in enumerate(words)});code=list(struct.unpack_from('>11I',self.rom,PARENT_ROM));entry=PARENT
            m=DispatchOracle(code,initial,c,actor,phase,entry,connected=connected).run()
            self.assertEqual(public(m.memory),public(expected),c)
            want=[(source.ENTRY,(actor,c.unused))]+calls if parent else calls
            self.assertEqual(m.calls,want,c);models.append(m)
        for m in models[1:]:self.assertEqual(complete(models[0]),complete(m))
        return models[0]

    def test_01_direct_body_bindings_and_full_owner_make(self):
        for words in self.images:self.assertEqual(words,self.truth)
        self.assertEqual(source.payload(self.out/'after-owner.o',source.FUNCTION),source.payload(source.original(ROOT,self.out,source.FUNCTION),source.FUNCTION))
        self.assertEqual(source.payload(self.out/'after-owner.o',source.FUNCTION)[1],source.BINDINGS)
        q=json.loads((self.out/'qualification.json').read_text());self.assertEqual(q['preserved_neighbors'],1);self.assertEqual(q['caller_functions_preserved'],328)
        plan=json.loads((self.out/'make-shadow.json').read_text());self.assertEqual([x['actual_Make_commands']for x in plan],[3,5])
        self.receipt.update(words=44,frame=48,bindings=6,new_guards=0,compiler_only=True,preserved_neighbors=1,caller_functions_preserved=328,actual_Make_commands=[3,5])

    def test_02_all_actor_bytes_classes_worlds_original_helpers(self):
        count=0;visits=set()
        for c,phase in corpus():m=self.compare(c,phase);visits.update(m.visits);count+=1
        missing=set(range(source.ENTRY,source.ENTRY+176,4))-visits
        self.assertEqual(missing,{source.ENTRY+0x70})
        self.assertTrue(set(range(ROW,ROW+104,4))<=visits);self.assertTrue(set(range(MASK,MASK+12,4))<=visits)
        self.receipt.update(guest_root_phases=count,actor_id_bytes=256,class_values=32,world_boundaries=[19,20,21],table_layouts=3,
            executable_root_words=43,retained_unreachable_word=28,connected_original_helper_words=29)

    def test_03_full_original_caller_and_actual_table_registration(self):
        ptr=struct.pack('>I',source.ENTRY);self.assertFalse(any(self.rom[i:i+4]==ptr for i in range(0,len(self.rom),4)))
        jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF));sites=[i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal]
        self.assertEqual(sites,[PARENT_ROM+20])
        self.assertEqual(struct.unpack_from('>2I',self.rom,0x234320),REAL_ROWS)
        for i,callback in enumerate(REAL_CALLBACKS):self.assertEqual(struct.unpack_from('>4I',self.rom,0x234300+i*16),(0,0,callback,0))
        count=0
        for identity,kind,world,phase in itertools.product(range(256),(5,6),(19,20),(0,8)):
            self.compare(Case(identity,kind,world,table=0),phase,parent=True);count+=1
        self.receipt.update(actual_caller_words=11,actual_caller_phases=count,direct_call_sites=sites,real_table_rows=2,callback_bodies_bounded=True)

    def test_04_native32_actual_C_parent_and_ten_effective_controls(self):
        unit=self.out/'native32.c';unit.write_text(native_harness(self.values))
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('native32'+opt);p=subprocess.run([*native_command(opt),str(unit),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,(p.stdout+p.stderr)[:10000]);p=subprocess.run([str(exe)],capture_output=True,timeout=90)
            self.assertEqual(p.returncode,0,(opt,p.stdout,p.stderr))
        self.receipt.update(native_cases_per_optimization=147456,native_actual_parent_cases_per_optimization=147456,native_optimizations=['O0','O2','O3'],
            effective_wrong_C_controls=10,trap_UBSan=True,full_struct127_backing=True,actual_C_row_helper=True,native_private_alias_or_callback_bodies_claimed=False)

    def test_05_fired_literal_access_prefixes(self):
        count=0
        for c in(Case(),Case(null=True),Case(identity=255),Case(kind=6,table=0),Case(layout=1),Case(layout=2)):
            initial,actor,sp=fixture(c);done=DispatchOracle(self.truth,initial,c,actor,connected=self.connected).run()
            for cut in range(done.root_accesses):
                models=[]
                for words in(self.truth,*self.images):
                    m=DispatchOracle(words,initial,c,actor,connected=self.connected);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    models.append(m)
                for m in models[1:]:self.assertEqual(complete(models[0]),complete(m))
                count+=1
        self.receipt.update(fired_root_access_prefixes=count,complete_private_state_equal=True,portable_C_fault_semantics_claimed=False)

    def test_06_independent_GNU_links_and_carry_rebases(self):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        from tools.experiments.game_actor_classifier_candidates import sections
        objects=(source.original(ROOT,self.out,source.FUNCTION),self.out/'qualified-padded.o',self.out/'make-shadow-target/src/game/generated_1BFCB0.c.o');links=count=0
        for index,(entry,world,table)in enumerate(((source.ENTRY,WORLD,TABLE),(0x18017FFC,0x800A7FFC,0x800B8000),(0x1A028000,0x800A8000,0x800B7FFC))):
            images=[]
            for k,obj in enumerate(objects):
                data,fs,rs=source.parse_object(obj);symbols={'D_800BE9F0':world,'D_8008F860':table,'func_151928B0':ROW,'func_1510F8CC':MASK}
                asm,unknown=emit_function(data,fs[source.FUNCTION],rs,source.FUNCTION,symbols);self.assertFalse(unknown)
                p=self.out/('rebase-%d-%d'%(index,k));p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>44I',sections(p.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for identity,kind,level,phase in itertools.product((0,83),(5,6),(19,20),(0,8)):
                c=Case(identity,kind,level);initial,actor,sp=fixture(c,phase,world,table);expected,calls=reference(initial,c,actor,sp,world,table);models=[]
                for words in images:
                    m=DispatchOracle(words,initial,c,actor,phase,entry,connected=self.connected,world=world).run()
                    self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.calls,calls);models.append(m)
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual(complete(models[0]),complete(models[2]));count+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=count,HI_LO_carry_boundaries=True)

    def test_07_private_home_aliases_and_null_gate_order(self):
        count=0
        for layout,unused,kind,phase in itertools.product((1,2),(0,0x53000000,0xFF000000),(5,6),(0,8)):
            c=Case(kind=kind,unused=unused,layout=layout);m=self.compare(c,phase);count+=1
            if layout==1:self.assertTrue(any(t==MASK and args==(0,)for t,args in m.calls))
        c=Case(null=True);m=self.compare(c);self.assertFalse(m.calls)
        self.receipt.update(private_alias_phases=count,full_unused_argument_home=True,row_output_overlaps_kind=True,unused_home_overlaps_actor_id=True,
            null_actor_dereference_or_table_lookup=False)

    def test_08_strict_image_and_unchanged_guards(self):
        old=self.values['conker/build/conker.us.elf'];bodies=source.truths(self.values)
        actual=(self.out/'first-linked.elf').read_bytes();self.assertEqual(source.predicted_image(old,bodies),actual)
        for at in(0,len(actual)-1,source.elf_slot_offset(actual,source.ENTRY,176)):
            bad=bytearray(actual);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(old,bytes(bad),bodies)
        self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),self.values['conker/retail_word_patches.us.csv'])
        self.receipt.update(strict_image_negative_controls=3,metadata_exclusions=0,guard_CSV_byte_identical=True,caller_padded_object_byte_identical=True)
