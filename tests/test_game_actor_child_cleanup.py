"""Five-child teardown: live slots, typed native storage and both real dispatchers."""
from dataclasses import dataclass
from pathlib import Path
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_actor_child_cleanup as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
OWNER,OTHER,ALT=0x20000,0x28000,0x38000
CHILDREN=tuple(0x30000+i*0x400 for i in range(5))
COUNT,SLOTS,DESTRUCTORS=0x800DD190,0x800DD198,0x8008B4D0
SCAN,SOFT_DEFAULT,HARD_DEFAULT=0x151696DC,0x15169804,0x15169824
SOFT_FREE,UNLINK,HEAP,BASE_A,BASE_B,PROVIDER=0x15168B10,0x15168A9C,0x10004074,0x1513CA48,0x1513CAD4,0x15600000
CHAIN={0x1516972C:112,0x1516979C:104,SCAN:80,SOFT_DEFAULT:32,HARD_DEFAULT:44,0x1513CA6C:52,0x1513CAA0:52}


@dataclass(frozen=True)
class Case:
    mask:int=31
    pattern:int=0
    mode:int=0
    seed:int=0xA5


def fixture(c,phase=0):
    m={STACK+i:(i*17+c.seed)&255 for i in range(-2048,512)}
    for base,size in((OWNER-16,0x200),(OTHER-16,0x200),*((v-16,0x250)for v in CHILDREN),(ALT-16,0x250)):
        m.update({base+i:(i*13+c.seed)&255 for i in range(size)})
    for i in range(5):
        node=CHILDREN[(i+c.pattern)%5]if c.pattern<2 else CHILDREN[c.pattern%5]
        put(m,OWNER+0x12C+4*i,node if c.mask>>i&1 else 0)
    return m


def effects(m,c,entered,n):
    if c.mode&1 and n==0:
        put(m,OWNER+0x130,CHILDREN[4]);put(m,OWNER+0x138,0)
    if c.mode&2:
        put(m,OWNER+0x13C,CHILDREN[n%5]if n%2==0 else 0)
    if c.mode&4:put(m,entered,OTHER)
    m[OWNER+0x11B]=(m[OWNER+0x11B]+n+1)&255


def reference(m,c,t,entered):
    m=dict(m);put(m,entered,OWNER);calls=[];n=0
    for i in range(5):
        node=read(m,OWNER+0x12C+4*i)
        if node:
            calls.append((t['release'],(node,)));effects(m,c,entered,n);n+=1
    calls.append((t['finish'],(read(m,entered),)))
    return m,calls


def public(m):
    return {a:b for a,b in m.items()if not STACK-2048<=a<STACK+512}


class CleanupOracle(RayOracle):
    def __init__(self,words,memory,c,t,phase=0,entry=None,connected=None,helpers=None,other_callbacks=()):
        TimingOracle.__init__(self,words,memory,phase=phase,entry=t['entry']if entry is None else entry,
            arguments=(OWNER,),connected=connected)
        self.case,self.target=c,t;self.entered=STACK+phase;self.releases=0
        self.cleanup_helpers=helpers or(t['release'],t['finish'])
        self.other_callbacks=set(other_callbacks)
        self.chain_mode=False

    def record_call(self,target):
        if target==self.target['entry']:self.entered=self.r[29]
        count=2 if target==SOFT_FREE else 1
        args=self.arguments(count);self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        if target==self.cleanup_helpers[0] and not self.chain_mode:
            effects(self.memory,self.case,self.entered,self.releases);self.releases+=1
        elif target not in(self.cleanup_helpers[1],BASE_A,BASE_B,SOFT_FREE,UNLINK,HEAP,PROVIDER)and target not in self.other_callbacks:
            raise AssertionError(('unbounded cleanup provider',hex(target)))
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo,self.condition=0x87654321,0x12345678,True;self.r[2]=0xB5000002


def controls(body):
    loop='for (index = 0; index < 2; index++)'
    return dict(selected=body,
        short_loop=body.replace('index < 2','index < 1'),
        wrong_loop_slot=body.replace('children[index]','children[index + 1]'),
        skip_third=body.replace('if (state->children[2] != NULL)','if (0)'),
        skip_fourth=body.replace('if (state->children[3] != NULL)','if (0)'),
        skip_fifth=body.replace('if (state->children[4] != NULL)','if (0)'),
        null_calls=body.replace('!= NULL','== NULL'),
        wrong_last_slot=body.replace('children[4]','children[0]'),
        wrong_family=body.replace('func_1516972C','func_1516979C')if 'func_1516972C'in body else body.replace('func_1516979C','func_1516972C'),
        no_finish=body.replace('    func_1513CA6C(owner);','').replace('    func_1513CAA0(owner);',''),
        wrong_finish_owner=body.replace('(owner);','((struct210 *)state);'),
        cached_tail=body.replace('    s32 index;','    s32 index;\n    struct102 *last = state->children[4];')
            .replace('if (state->children[4] != NULL)','if (last != NULL)').replace('(state->children[4]);','(last);'))


def native_harness():
    text=source.HEADERS+source.DECLARATIONS+'''
typedef char state_size[sizeof(ChildReleaseState11C2B0)==48?1:-1];
typedef struct {u8 prefix[0x110];ChildReleaseState11C2B0 state;u8 suffix[32];} NativeOwner;
typedef char child_offset[__builtin_offsetof(NativeOwner,state)+__builtin_offsetof(ChildReleaseState11C2B0,children)==0x12C?1:-1];
static NativeOwner actual,expected;static struct102 children[5];
static u32 actualCalls[6],wantedCalls[6],calls,wantedCount,mode,error,family,step;
static void change(NativeOwner *p,u32 n){
 if((mode&1)&&n==0){p->state.children[1]=children+4;p->state.children[3]=0;}
 if(mode&2)p->state.children[4]=n%2==0?children+n%5:0;
 p->state.opaque0[11]=(u8)(p->state.opaque0[11]+n+1);
}
static void release(struct102 *p,u32 kind){
 if(calls>=5){error=1;return;}actualCalls[calls++]=(u32)p;
 if(kind!=family)error=2;change(&actual,step++);
}
void func_1516972C(struct102 *p){release(p,0);}
void func_1516979C(struct102 *p){release(p,1);}
static void finish(struct210 *p,u32 kind){
 if(calls>=6){error=3;return;}actualCalls[calls++]=(u32)p;if(kind!=family)error=4;
}
void func_1513CA6C(struct210 *p){finish(p,0);}
void func_1513CAA0(struct210 *p){finish(p,1);}
'''
    names=[]
    for n,body in source.SELECTED.items():
        for label,b in controls(body).items():
            fn=n+'_'+label;names.append((fn,label,n));text+=b.replace(n,fn)+'\n'
    text+='''typedef void (*Create)(struct210 *);
static int variant(Create fn,u32 kind){
 u32 mask,p,m,i,j,n;family=kind;
 for(mask=0;mask<32;mask++)for(p=0;p<5;p++)for(m=0;m<4;m++){
  for(i=0;i<sizeof(actual);i++)((u8*)&actual)[i]=((u8*)&expected)[i]=(u8)(i*13+mask+p);
  for(i=0;i<5;i++)actual.state.children[i]=expected.state.children[i]=(mask>>i&1)?children+(p<2?(i+p)%5:p%5):0;
  mode=m;wantedCount=n=0;
  for(i=0;i<5;i++){
   struct102 *node=expected.state.children[i];
   if(node){wantedCalls[wantedCount++]=(u32)node;change(&expected,n++);}
  }
  wantedCalls[wantedCount++]=(u32)&actual;calls=step=error=0;
  fn((struct210*)&actual);
  if(error||calls!=wantedCount)return 23;
  for(j=0;j<calls;j++)if(actualCalls[j]!=wantedCalls[j])return 23;
  for(i=0;i<sizeof(actual);i++)if(((u8*)&actual)[i]!=((u8*)&expected)[i])return 23;
 }
 return 0;
}
int run(void){
'''
    for i,(fn,label,name)in enumerate(names):
        text+=' if(variant(%s,%d)!=%d)return %d;\n'%(fn,list(source.FUNCTIONS).index(name),0 if label=='selected'else 23,i+1)
    return text+' return 0;\n}\n'+START


def caller_harness(caller):
    text=source.HEADERS+'''
static struct210 owner;static u32 calls,which,error;
void (*D_80089EF8[13])(void);void (*D_80089F2C[13])(void);
'''
    for i in range(13):
        text+='static void slot%d(struct210 *p){calls++;which=%d;if(p!=&owner)error=1;}\n'%(i,i)
    for name in('func_1513CB58','func_1513CBA4'):
        lo,hi=source.function_span(caller,name);text+=caller[lo:hi]+'\n'
    text+='int run(void){u32 i,gate,index;\n'
    for i in range(13):text+=' D_80089EF8[%d]=D_80089F2C[%d]=(void(*)(void))slot%d;\n'%(i,i,i)
    text+=''' for(gate=0;gate<2;gate++)for(index=0;index<13;index++)for(i=0;i<2;i++){
 owner.unk58=gate?0x400000:0;owner.unk18.b.unk1=(u8)index;calls=error=0;which=255;
 if(i)func_1513CBA4(&owner);else func_1513CB58(&owner);
 if(error||calls!=1||which!=(gate?index:0))return 1;
 }
 return 0;
}
'''
    return text+START


class ActorChildCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.rom=cls.values['conker/conker.us.bin'];cls.images={};cls.objects={};cls.parents={};cls.tables={};cls.receipt={}
        for name,t in source.TARGETS.items():
            obj,diag=source.compile_owner(ROOT,cls.out,source.HEADERS+source.DECLARATIONS+source.SELECTED[name],'fresh-'+name)
            if diag:raise ValueError(diag)
            data,fs=source.link_owner(ROOT,cls.out,obj,source.OWNER);at=fs[name]['value']
            cls.images[name]=(list(struct.unpack_from('>44I',cls.rom,t['rom'])),list(struct.unpack_from('>44I',data,at)))
            cls.objects[name]=obj;rom=t['parent']-0x15000000+0x2D4B0
            cls.parents[name]=list(struct.unpack_from('>19I',cls.rom,rom))
            cls.tables[name]=list(struct.unpack_from('>13I',cls.rom,t['table_rom']))

    def compare(self,name,c,phase=0,images=None,entry=None,helpers=None):
        t=source.TARGETS[name];m=fixture(c,phase);expected,calls=reference(m,c,t,STACK+phase)
        if helpers:calls=[(helpers[0]if p==t['release']else helpers[1],a)for p,a in calls]
        models=[]
        for words in(images or self.images[name]):
            model=CleanupOracle(words,m,c,t,phase,entry,helpers=helpers);saved=model.r[16:24]
            model.run();self.assertEqual(model.r[16:24],saved);models.append(model)
        for model in models:
            self.assertEqual(public(model.memory),public(expected),c);self.assertEqual(model.calls,calls)
            self.assertEqual(model.r[29],STACK+phase);self.assertEqual(model.r[31],0xDEAD0000)
        self.assertEqual(complete(models[0]),complete(models[1]));return models[0]

    def test_01_direct_words_complete_owners_actual_Make_and_old_stubs(self):
        q=json.loads((self.out/'qualification.json').read_text())
        self.assertEqual((q['total_words'],q['new_guards'],q['preserved_neighbors'],q['caller_functions_preserved']),(88,0,42,59))
        for name,t in source.TARGETS.items():
            self.assertEqual(*self.images[name]);self.assertEqual(self.images[name][0][0],0x27BDFFD8)
            self.assertEqual(source.payload(self.objects[name],name),source.payload(source.original(ROOT,self.out,name),name))
            self.assertEqual(sum(map(len,source.payload(self.objects[name],name)[1].values())),5)
            at=source.elf_slot_offset(self.values['conker/build/conker.us.elf'],t['entry'],176)
            old=list(struct.unpack_from('>44I',self.values['conker/build/conker.us.elf'],at));c=Case()
            model=CleanupOracle(old,fixture(c),c,t).run();self.assertFalse(model.calls)
            self.assertNotEqual(model.calls,self.compare(name,c).calls)
        source.check_inputs(ROOT,self.out,self.installed)
        self.receipt.update(words_each=44,frame_each=40,bindings_each=5,compiler_only=True,new_guards=0,
            preserved_neighbors=42,caller_functions_preserved=59,actual_Make_commands=[3,5],inherited_caller_warnings_unchanged=43)

    def test_02_all_null_masks_live_future_slots_and_late_owner_home(self):
        phases=0
        for name,t in source.TARGETS.items():
            visits=set()
            for mask,pattern,mode,phase in itertools.product(range(32),(0,3),range(8),(0,8)):
                model=self.compare(name,Case(mask,pattern,mode),phase);visits.update(model.visits);phases+=1
            self.assertEqual(visits,set(range(t['entry'],t['entry']+176,4)))
        self.receipt.update(ordinary_guest_phases=phases,all_root_words_visited=True,all_32_null_masks=True,
            captured_child_state_and_late_owner_home=True,portable_C_home_alias_claimed=False)

    def test_03_native32_typed_children_and_eleven_effective_controls(self):
        unit=self.out/'native32.c';unit.write_text(native_harness())
        for opt in('-O0','-O2','-O3'):
            binary=self.out/('native32'+opt)
            p=subprocess.run([*native_command(opt),str(unit),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            p=subprocess.run([str(binary)],capture_output=True,timeout=90);self.assertEqual(p.returncode,0,(opt,p.stdout,p.stderr))
        self.receipt.update(native_selected_calls_per_optimization=1280,native_optimizations=['O0','O2','O3'],
            effective_wrong_C_controls_each=11,trap_UBSan=True,native_complete_typed_child_objects=True,
            native_owner_state_storage_typed=True,lower_teardown_providers_bounded=True)

    def test_04_both_tables_and_complete_actual_dispatchers(self):
        phases=0
        for name,t in source.TARGETS.items():
            ptr=struct.pack('>I',t['entry']);jal=struct.pack('>I',0x0C000000|(t['entry']>>2&0x3FFFFFF))
            self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==ptr],[t['table_rom']+28])
            self.assertFalse(any(self.rom[i:i+4]==jal for i in range(0,len(self.rom),4)))
            old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,t['parent'],76)
            self.assertEqual(list(struct.unpack_from('>19I',old,at)),self.parents[name])
            at=source.elf_slot_offset(old,t['table'],52);self.assertEqual(old[at:at+52],self.rom[t['table_rom']:t['table_rom']+52])
            self.assertEqual(self.tables[name][7],t['entry']);visits=set()
            for selector,gate,mask,phase in itertools.product(range(13),(0,0x400000,0xFFFFFFFF),(0,5,31),(0,8)):
                c=Case(mask);m=fixture(c,phase);m[OWNER+0x19]=selector;put(m,OWNER+0x58,gate)
                for i,v in enumerate(self.tables[name]):put(m,t['table']+i*4,v)
                index=selector if gate&0x400000 else 0;callback=self.tables[name][index];calls=[(callback,(OWNER,))]
                expected=dict(m)
                if index==7:
                    expected,more=reference(m,c,t,STACK+phase-24);calls+=more
                models=[]
                for words in self.images[name]:
                    connected={t['entry']+i*4:w for i,w in enumerate(words)}
                    model=CleanupOracle(self.parents[name],m,c,t,phase,t['parent'],connected,other_callbacks=self.tables[name]).run()
                    self.assertEqual(public(model.memory),public(expected));self.assertEqual(model.calls,calls)
                    self.assertEqual(model.r[29],STACK+phase);visits.update(model.visits);models.append(model)
                self.assertEqual(complete(models[0]),complete(models[1]));phases+=1
            self.assertTrue(set(range(t['parent'],t['parent']+76,4))<=visits)
        self.receipt.update(caller_phases=phases,actual_dispatcher_words_each=19,all_caller_words_visited=True,
            actual_registration_indices=[7,7],actual_tables_each=13,other_callbacks_bounded=True,
            unchecked_out_of_range_selector_safety_claimed=False)

    def test_05_native_actual_caller_bodies_explicit_owner_argument(self):
        caller=source.recovered_caller(self.values[source.CALLER_SOURCE].decode())
        unit=self.out/'native-callers.c';unit.write_text(caller_harness(caller))
        for opt in('-O0','-O2','-O3'):
            binary=self.out/('native-callers'+opt)
            p=subprocess.run([*native_command(opt),str(unit),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            self.assertEqual(subprocess.run([str(binary)],capture_output=True,timeout=60).returncode,0,opt)
        self.receipt.update(native_actual_dispatcher_calls_per_optimization=52,native_dispatcher_callback_boundary_probes=True,
            native_complete_struct210_owner=True,full_native_dispatcher_callee_closure_claimed=False)

    def test_06_actual_current_release_and_base_teardown_chains(self):
        connected={};old=self.values['conker/build/conker.us.elf']
        for entry,size in CHAIN.items():
            rom=entry-0x15000000+0x2D4B0;raw=self.rom[rom:rom+size];at=source.elf_slot_offset(old,entry,size)
            self.assertEqual(old[at:at+size],raw);connected.update(zip(range(entry,entry+size,4),struct.unpack('>%dI'%(size//4),raw)))
        phases=0;visits=set()
        for name,t in source.TARGETS.items():
            hard=name==source.FUNCTIONS[1];default=HARD_DEFAULT if hard else SOFT_DEFAULT
            for kind,count,callback,pattern,phase in itertools.product((0,1,2,7,255),(0,1,3,127,128,255),(0,1),(0,3),(0,8)):
                c=Case(31,pattern);m=fixture(c,phase);m[COUNT]=count
                for node in CHILDREN:m[node]=kind;put(m,node+8,ALT)
                for i in range(127):put(m,SLOTS+4*i,CHILDREN[0]if i%2==0 else ALT)
                put(m,DESTRUCTORS+52*kind+(4 if hard else 0),PROVIDER if callback else 0)
                expected=dict(m);calls=[]
                def tail(owner):
                    return [(UNLINK,(owner,)),(HEAP,(owner,))]if hard else[(SOFT_FREE,(owner,1))]
                for i in range(5):
                    node=read(expected,OWNER+0x12C+i*4);calls.extend(((t['release'],(node,)),(SCAN,(node,))))
                    if 0<count<128:
                        for j in range(count):
                            if read(expected,SLOTS+j*4)==node:put(expected,SLOTS+j*4,ALT)
                    if hard or kind>=2:
                        calls+=([(PROVIDER,(node,))]if callback else[(default,(node,)),*tail(node)])
                calls.extend(((t['finish'],(OWNER,)),(BASE_A,(OWNER,)),(BASE_B,(OWNER,)),(default,(OWNER,))))
                calls+=tail(OWNER);models=[]
                for words in self.images[name]:
                    model=CleanupOracle(words,m,c,t,phase,connected=connected);model.chain_mode=True;model.run()
                    self.assertEqual(public(model.memory),public(expected));self.assertEqual(model.calls,calls)
                    visits.update(model.visits);models.append(model)
                self.assertEqual(complete(models[0]),complete(models[1]));phases+=1
        self.assertTrue(set(connected)<=visits)
        self.receipt.update(retained_chain_words=len(connected),chain_phases=phases,all_chain_words_visited=True,
            signed_scan_count_and_callback_default_paths=True,base_substeps_and_heap_providers_bounded=True,
            full_heap_or_hardware_acceptance_claimed=False)

    def linked(self,name,obj,entry,helpers,label):
        t=source.TARGETS[name];text,fs,rs=source.parse_object(obj)
        symbols={'func_%08X'%t['release']:helpers[0],'func_%08X'%t['finish']:helpers[1]}
        asm,unknown=emit_function(text,fs[name],rs,name,symbols);self.assertFalse(unknown)
        p=self.out/label;p.with_suffix('.s').write_text(asm)
        p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',name,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
        return list(struct.unpack_from('>44I',sections(p.with_suffix('.elf'))['.text'][1]))

    def test_07_independent_rebases_and_all_root_access_prefixes(self):
        links=phases=cuts=0
        for name,t in source.TARGETS.items():
            profiles=((t['entry'],(t['release'],t['finish'])),(0x18017FFC,(0x18207FFC,0x18308000)),(0x1A028000,(0x1B047FF0,0x1C008000)))
            for i,(entry,helpers)in enumerate(profiles):
                objects=(source.original(ROOT,self.out,name),self.out/'qualified-padded.o',self.out/'make-shadow-target/src/game/generated_11C2B0.c.o')
                images=[self.linked(name,obj,entry,helpers,'rebased-'+name+'-%d-%d'%(i,j))for j,obj in enumerate(objects)];links+=3
                self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
                for mask,mode,phase in itertools.product((0,5,31),range(8),(0,8)):
                    self.compare(name,Case(mask,3,mode),phase,images[:2],entry,helpers);phases+=1
            for mask,mode,phase in itertools.product((0,5,31),(0,3,7),(0,8)):
                c=Case(mask,3,mode);m=fixture(c,phase);done=CleanupOracle(self.images[name][0],m,c,t,phase).run()
                for cut in range(done.root_accesses):
                    models=[CleanupOracle(w,m,c,t,phase)for w in self.images[name]]
                    for model in models:
                        model.root_fault=cut
                        with self.assertRaises(faults.AccessBoundary):model.run()
                    self.assertEqual(complete(models[0]),complete(models[1]))
                    self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=phases,fired_root_access_prefixes=cuts,
            portable_C_fault_semantics_claimed=False)

    def test_08_strict_image_and_frozen_inputs(self):
        before=self.values['conker/build/conker.us.elf'];bodies=source.truths(self.values)
        expected=source.predicted_image(before,bodies);source.check_image(before,expected,bodies);positions={0,len(before)-1}
        for name,t in source.TARGETS.items():
            at=source.elf_slot_offset(before,t['entry'],176);sym=[offset for offset,n,_,_ in source.symbol_rows(before)if n==name][0]
            positions.update((at-1,at,at+172,at+176,sym+4,sym+8))
        for pos in positions:
            bad=bytearray(expected);bad[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),bodies)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],bodies)
        source.check_inputs(ROOT,self.out,self.installed)
        self.receipt.update(strict_image_negatives=len(positions)+1,guard_manifest_byte_identical=True,metadata_exclusions=0)
