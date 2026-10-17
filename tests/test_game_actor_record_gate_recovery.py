"""Public recovery evidence and explicit rejection of the unmatched private ABI."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_actor_record_gate_recovery as source
from tools.tests import game_view_point_projection_oracle as point
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.game_animation_timeline_oracle import signed
from tools.check_game_data_layout import audit_layout

STACK,STATE,RECORDS,MASKS,OBJECT,BANK,ALT=point.STACK,0x20000,0x30000,0x90000,0x50000,0x60000,0x61000
LOOKUP,CLEAN,RESET,SOUND,REFRESH,MODE,FIND,OVERLAY=(source.SYMBOLS[n] for n in
    ('func_151149AC','func_15060F28','func_15136C3C','func_10010630','func_15145A50','func_1507CD64','func_15083E90','func_15196318'))
COUNTS={LOOKUP:1,CLEAN:2,RESET:8,SOUND:5,REFRESH:1,MODE:2,FIND:1,OVERLAY:3}
COUNT=0x800DBEF0

def quotient(delta):
    value=signed(delta&0xffffffff)
    return (abs(value)//160)*(-1 if value<0 else 1)

def fixture(gate=2,masks=0,selector=100,value=7,present=True,delta=0,symbols=None):
    s=symbols or source.SYMBOLS
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x600,0x180)}
    for base,size in ((STATE,0x140),(RECORDS,640),(MASKS-64,128),(OBJECT,0x310),(BANK,32),(ALT,32)):
        memory.update({base+i:0xA5 for i in range(size)})
    for name in ('D_800CC5EC','D_800DBEF4','D_800DBF94','D_800BE4F0'):
        for i in range(4):memory[s[name]+i]=0
    put(memory,s['D_800CC5EC'],STATE if gate else 0);put(memory,STATE+0x120,1 if gate==1 else 0,1)
    put(memory,s['D_800DBEF4'],RECORDS);put(memory,s['D_800DBF94'],MASKS);put(memory,COUNT,4)
    put(memory,s['D_800CC40C'],selector,1);put(memory,s['D_800CC49A'],0xA5,1)
    put(memory,s['D_800BE4F0'],BANK);put(memory,OBJECT+0x2E4,value&0xffffffff)
    for i in range(4):
        put(memory,RECORDS+i*160+0x72,250-i,1)
        put(memory,BANK+i*4,0xA0000+i*0x100);put(memory,ALT+i*4,0xB0000+i*0x100)
        for base in (0xA0000+i*0x100,0xB0000+i*0x100):memory.update({base+j:0xA5 for j in range(32)})
    for i in range(2):put(memory,(MASKS+16+quotient(delta+i*160)*4)&0xffffffff,0)
    for i in range(2):put(memory,(MASKS+quotient(delta+i*160)*4)&0xffffffff,(masks>>i)&1)
    return memory

def public(memory):return {a:v for a,v in memory.items() if not STACK-0x600<=a<STACK+0x180}

def effects(memory,target,ordinal,mode,s):
    if mode==1 and target==LOOKUP:
        put(memory,s['D_800DBF94'],MASKS+16);put(memory,MASKS+16,1);put(memory,MASKS+20,1)
    if mode==2 and target==OVERLAY and ordinal==1:put(memory,s['D_800BE4F0'],ALT)
    if mode==3 and target==RESET:put(memory,s['D_800CC5EC'],0)
    if mode==4 and target==FIND:put(memory,OBJECT+0x2E4,0xfffffffd)

def reference(initial,selector=100,value=7,present=True,delta=0,mode=0,symbols=None,actual_offsets=False):
    s=symbols or source.SYMBOLS;memory=dict(initial);calls=[];counts={}
    def call(target,*args):
        args=tuple(a&0xffffffff for a in args);calls.append((target,args));counts[target]=counts.get(target,0)+1
        effects(memory,target,counts[target],mode,s)
        if actual_offsets and target==s['func_15196318'] and args[0]:
            put(memory,args[0]+0x12,args[1]&255,1);put(memory,args[0]+0x13,args[2]&255,1)
        if target==s['func_151149AC']:return (RECORDS+delta+(250-args[0])*160)&0xffffffff
        if target==s['func_15083E90']:return OBJECT if present else 0
        return 0
    state=read(memory,s['D_800CC5EC'])
    if not state or read(memory,state+0x120,1):return memory,calls
    for selector_id in (250,249):
        record=call(s['func_151149AC'],selector_id)
        index=quotient(record-read(memory,s['D_800DBEF4']))
        mask=read(memory,(read(memory,s['D_800DBF94'])+index*4)&0xffffffff)
        if mask&1:
            current=read(memory,s['D_800CC40C'],1)
            if current:call(s['func_15060F28'],s['D_800CC2D0']+current*812-81200,0)
            put(memory,s['D_800CC49A'],0,1)
            call(s['func_15136C3C'],s['D_800CC2D0'],0,0,1,1,0,255,1)
            call(s['func_10010630'],0x627,s['D_800CC2D0'],0x6D60,500,1000)
            call(s['func_15145A50'],s['D_800CC2D0']);call(s['func_1507CD64'],s['D_800CC2D0'],6)
            break
    obj=call(s['func_15083E90'],14);value=read(memory,obj+0x2E4) if obj else 0
    for i,xy in enumerate(((value,0),(0,(-value)&0xffffffff),(value,0),((-value)&0xffffffff,0))):
        call(s['func_15196318'],read(memory,read(memory,s['D_800BE4F0'])+i*4),*xy)
    return memory,calls

class Oracle(point.PointProjectionOracle):
    def __init__(self,words,memory,phase=0,delta=0,present=True,mode=0,connected=None,symbols=None,entry=source.ENTRY):
        self.targets=symbols or source.SYMBOLS;self.delta=delta;self.present=present;self.effect_mode=mode;self.counts={}
        super().__init__(words,memory,(0xfedcba98,),[],phase,entry,connected)

    def args(self,count):return tuple(self.r[4+i] if i<4 else read(self.memory,self.r[29]+i*4) for i in range(count))

    def record_call(self,target):
        name=next(n for n,v in self.targets.items() if v==target);count=COUNTS[source.SYMBOLS[name]]
        self.calls.append((target,self.args(count)));self.observations.append((target,self.r[29]))

    def hook(self,target):
        name=next(n for n,v in self.targets.items() if v==target);canonical=source.SYMBOLS[name]
        args=self.args(COUNTS[canonical]);self.counts[canonical]=self.counts.get(canonical,0)+1
        effects(self.memory,canonical,self.counts[canonical],self.effect_mode,self.targets);result=0
        if canonical==LOOKUP:result=(RECORDS+self.delta+(250-args[0])*160)&0xffffffff
        if canonical==FIND:result=OBJECT if self.present else 0
        for i in range(4):put(self.memory,self.r[29]+i*4,0xB5000000+i)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result

def private(m):return point.state(m),m.condition,m.lo

class RecordGateRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes();cls.truth=list(struct.unpack_from('>139I',cls.rom,source.ROM))
        cls.lookup={LOOKUP+i*4:w for i,w in enumerate(struct.unpack_from('>28I',cls.rom,0x141E5C))}
        cls.offsets={OVERLAY+i*4:w for i,w in enumerate(struct.unpack_from('>6I',cls.rom,0x1C37C8))}

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,gate=2,masks=0,selector=100,value=7,present=True,delta=0,mode=0,phase=0,connected=False,actual_offsets=False,null_handle=False):
        memory=fixture(gate,masks,selector,value,present,delta)
        if null_handle:put(memory,BANK+4,0)
        want,calls=reference(memory,selector,value,present,delta,mode,actual_offsets=actual_offsets)
        code=dict(self.lookup) if connected else {}
        if actual_offsets:code.update(self.offsets)
        models=[Oracle(w,memory,phase,delta,present,mode,code).run() for w in (self.truth,self.words)]
        for m in models:self.assertEqual((public(m.memory),m.calls),(public(want),calls))
        return models

    def test_01_shape_screens_and_owner_isolation(self):
        row=self.row['candidate']
        self.assertEqual((row['words'],row['frame'],row['differences'],row['extent_gap']),(137,64,118,-2))
        self.assertEqual(self.row['unchanged_raw_padded_neighbors'],11)
        self.assertEqual(self.row['padded_full_slot_differences'],120)
        self.assertTrue(self.row['owner_pools_unchanged']);self.assertFalse(self.row['installed'])
        self.assertEqual(len(self.row['screen']),7);self.assertTrue(self.row['no_matching_credit'])
        self.assertEqual([(r['label'],r['words'],r['differences']) for r in self.row['screen']],
            [('semantic',137,118),('nounroll',137,118),('o2',136,134),('o1',126,124),('named-index',137,115),('retry-scan',138,122),('object-condition',137,118)])
        self.receipt('shape',candidate_words=137,retail_words=139,raw_differences=118,frame=64,
            padded_full_slot_differences=120,
            saved_GPRs_candidate=6,saved_GPRs_retail=5,unchanged_raw_padded_neighbors=11,
            seven_reproducible_screens=True,no_install_or_matching_credit=True)

    def test_02_public_effects_gates_width_and_wrap_domain(self):
        cases=0
        for gate,masks,selector,value,present,phase in itertools.product(range(3),range(4),(0,1,100,255),
                (0,1,0xffffffff,0x80000000,0x7fffffff),(False,True),(0,8)):
            self.compare(gate,masks,selector,value,present,phase=phase);cases+=1
        sparse=0
        for delta,masks,mode,phase in itertools.product((-321,-160,-159,-1,0,159,160,321,0x7fffffff,0x80000000),
                range(4),range(5),(0,8)):
            self.compare(masks=masks,delta=delta,mode=mode,phase=phase);sparse+=1
        connected=0
        for masks,present,phase in itertools.product(range(4),(False,True),(0,8)):
            self.compare(masks=masks,present=present,phase=phase,connected=True);connected+=1
        offsets=0
        for value,null_handle,phase in itertools.product((0,255,256,0xffffffff,0x80000000,0x7fffffff),(False,True),(0,8)):
            self.compare(masks=2,value=value,phase=phase,connected=True,actual_offsets=True,null_handle=null_handle);offsets+=1
        self.receipt('public',retail_candidate_cases=cases,sparse_and_provider_mutation_cases=sparse,
            actual_28_word_lookup_cases=connected,actual_lookup_and_six_word_byte_offset_setter_cases=offsets,
            null_handle_and_low_byte_offsets=True,all_selector_byte_endpoints=True,
            signed32_pointer_difference_division=True,NEGU_word_wrap=True,
            full_private_or_fault_equivalence_not_claimed=True,remaining_providers_scripted=True)

    def test_03_first_private_fault_counterexample_and_global_reads(self):
        memory=fixture();models=[Oracle(w,memory) for w in (self.truth,self.words)]
        for m in models:
            m.access_fault=2
            with self.assertRaises(faults.AccessBoundary):m.run()
            self.assertEqual(m.all_accesses,2)
        self.assertNotEqual(private(models[0]),private(models[1]))
        self.assertNotEqual(read(models[0].memory,STACK-64+56),read(models[1].memory,STACK-64+56))
        complete=self.compare();address=source.SYMBOLS['D_800CC5EC']
        counts=[sum(e[0]=='R' and e[1]==address for e in m.events) for m in complete]
        self.assertEqual(counts,[2,1])
        self.receipt('rejection',first_differing_access_boundary=2,private_saved_word=56,
            retail_register=20,candidate_register=21,initial_global_reads=counts,
            full_private_fault_contract_rejected=True,no_guard_or_install=True)

    def test_04_native32_and_semantic_negative_controls(self):
        head='#include <ultra64.h>\n'+source.TYPE
        driver=self.out/'native-driver.c';driver.write_text(head+NATIVE)
        controls={'selector':source.SELECTED.replace('250 - i','248 - i'),
            'overlay':source.SELECTED.replace('D_800BE4F0[1], 0, -value','D_800BE4F0[1], -value, 0')}
        for opt in ('-O2','-O0'):
            for label,body in (('semantic',source.SELECTED),*controls.items()):
                path=self.out/('native-'+label+'.c');path.write_text(head+body+'\n');exe=self.out/('native-'+label+opt)
                subprocess.run(native_command(opt)+['-mstackrealign','-fno-builtin',str(path.relative_to(self.root)),
                    str(driver.relative_to(self.root)),'-o',str(exe)],cwd=self.root,capture_output=True,check=True)
                result=subprocess.run([str(exe)],capture_output=True)
                self.assertEqual(result.returncode,0 if label=='semantic' else 22,(opt,label,result.stderr))
        self.receipt('native',cases_per_profile=256,profiles=['O2','O0'],UBSan=True,effective_controls=4,
            separately_typed_caller=True,valid_same_array_pointer_subtraction=True,complete_objects=True,
            INT_MIN_negation_and_sparse_guest_indices_excluded=True,public_only_not_matching_credit=True)

    def test_05_production_image_data_and_every_input_unchanged(self):
        source.freeze(self.root,self.out)
        for key,path in source.PATHS.items():self.assertEqual((self.root/path).read_bytes(),(self.out/('before-'+key)).read_bytes())
        report=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertEqual((report['exact'],report['bytes'],report['owner_count'],report['different_bytes']),(True,189088,720,0))
        self.receipt('unchanged',protected_entries=len(source.PATHS),distinct_paths=len(set(source.PATHS.values())),
            production_ELF_sha=hashlib.sha256((self.root/source.PATHS['elf']).read_bytes()).hexdigest(),
            all_production_sources_and_guards_unchanged=True,game_data=report,installed=False)

NATIVE=r'''
void func_150F2A60(u8 *);
static union {u32 align;u8 bytes[640];} records,state;
static union {u32 align;u8 bytes[1024];} object;
static u32 masks[4];static u8 handles[8][4];static u8 *bank[4],*alternate[4];
u8 *D_800CC5EC=state.bytes,*D_800DBEF4=records.bytes; s32 *D_800DBF94=(s32 *)masks;
u8 D_800CC40C,D_800CC49A;u8 D_800CC2D0[156*812+32] __attribute__((aligned(4)));
u8 **D_800BE4F0=bank;
static int pattern,error,lookups,cleaned,resets,sounds,refreshes,modes,found,overlays;
u8 *func_151149AC(u8 selector){if(selector!=250-lookups)error=1;return records.bytes+160*lookups++;}
void func_15060F28(u8 *a,s32 b){if(a!=D_800CC2D0+(D_800CC40C-100)*812||b)error=1;cleaned++;}
void func_15136C3C(u8 *a,s32 b,s32 c,s32 d,s32 e,s32 f,s32 g,s32 h){if(a!=D_800CC2D0||b||c||d!=1||e!=1||f||g!=255||h!=1||D_800CC49A)error=1;resets++;}
void func_10010630(s32 a,u8 *b,s32 c,s32 d,s32 e){if(a!=0x627||b!=D_800CC2D0||c!=0x6D60||d!=500||e!=1000)error=1;sounds++;}
void func_15145A50(u8 *a){if(a!=D_800CC2D0)error=1;refreshes++;}
void func_1507CD64(u8 *a,s32 b){if(a!=D_800CC2D0||b!=6)error=1;modes++;}
u8 *func_15083E90(s32 a){if(a!=14)error=1;found++;return pattern&8?object.bytes:(u8 *)0;}
void func_15196318(u8 *a,s32 x,s32 y){s32 v=pattern&8?*(s32 *)(object.bytes+0x2E4):0;int i=overlays++;
u8 *expected=(pattern&128&&i)?alternate[i]:bank[i];
if(a!=expected||x!=(i==0||i==2?v:i==3?-v:0)||y!=(i==1?-v:0))error=1;
if((pattern&128)&&!i)D_800BE4F0=alternate;}
static int run(void){int i,active,matched,wanted;
for(pattern=0;pattern<256;pattern++){
error=lookups=cleaned=resets=sounds=refreshes=modes=found=overlays=0;
for(i=0;i<4;i++){masks[i]=(pattern>>i)&1;bank[i]=handles[i];alternate[i]=handles[i+4];}
D_800BE4F0=bank;D_800CC5EC=pattern&16?(u8 *)0:state.bytes;state.bytes[0x120]=!!(pattern&32);
D_800CC40C=pattern&64?255:100;D_800CC49A=0xA5;*(s32 *)(object.bytes+0x2E4)=(pattern-128)*71;
func_150F2A60((u8 *)0);
active=!(pattern&16)&&!(pattern&32);matched=!!(pattern&3);wanted=active?(pattern&1?1:2):0;
if(error||lookups!=wanted||cleaned!=(active&&matched)||resets!=(active&&matched)||sounds!=(active&&matched)||refreshes!=(active&&matched)||modes!=(active&&matched)||found!=active||overlays!=4*active)return 22;
if(D_800CC49A!=(active&&matched?0:0xA5))return 22;
}return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''

if __name__=='__main__':unittest.main()
