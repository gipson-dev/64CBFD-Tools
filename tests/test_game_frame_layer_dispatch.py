"""Frame-layer calls, late gates, unsigned wrap and typed caller identity."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,struct,subprocess,unittest
from tools.experiments import game_frame_layer_dispatch as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_command_stream_relocator import StopCode,WindowEnd
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
ROWS=(0x28000,0x28100);PROVIDER=0x152F0000;INDEX=0x800BE9F0
SYMBOLS=dict(func_15165F70=0x15165F70,func_15195FF0=0x15195FF0,func_1510C8A8=0x1510C8A8,
    func_1517DE5C=0x1517DE5C,func_151880C0=0x151880C0,D_800B0E00=0x800B0E00,
    D_800B0DF0=0x800B0DF0,D_8008CD04=0x8008CD04,D_800BE616=0x800BE616,
    D_800CBD4E=0x800CBD4E,D_800BE9E4=0x800BE9E4)
CALLEES=('func_15165F70','func_15195FF0','func_1510C8A8','func_1517DE5C','func_151880C0')
WORDS=(0,1,0xFFFFFFFF,0x80000000,0x7FFFFFFF,0xFFFF8000,0x40000000,0x12345678)
PHASES=(0,1,0x3FF,0x400,0x7FFF,0x8000,0xFFFE,0xFFFF)
NATIVE_DECLARATIONS = """typedef unsigned char u8;typedef unsigned short u16;typedef unsigned int u32;typedef int s32;
typedef struct{u8 bytes[32];}struct104;typedef void(*FrameLayerCallback)(s32);
extern struct104*D_800B0DF0;extern FrameLayerCallback D_8008CD04[];
extern s32 D_800B0E00[],D_800BE9E4;extern u8 D_800BE616;extern u16 D_800CBD4E;
void func_15165F70(void);void func_15195FF0(s32,s32);void func_1510C8A8(void);
void func_1517DE5C(void);void func_151880C0(void);
"""


@dataclass(frozen=True)
class Case:
    selector:int=1
    disabled:int=0
    clock:int=1
    accumulator:int=65535
    view:int=0x87654321
    unused:int=0x12345678
    mode:int=0


def put16(m,at,value):
    m[at]=value>>8&255;m[at+1]=value&255


def read16(m,at):return m[at]<<8|m[at+1]


def fixture(c,phase=0,symbols=None):
    s=symbols or SYMBOLS;m={STACK+phase+i:(i*17+0xA5)&255 for i in range(-0x600,0x400)}
    for base,n in((ROWS[0],32),(ROWS[1],32),(s['D_800B0E00']-8,24),(s['D_800B0DF0']-8,20),
        (s['D_8008CD04'],1024),(s['D_800BE616']-8,20),(s['D_800CBD4E']-8,20),
        (s['D_800BE9E4']-8,20),(INDEX,4)):
        for i in range(n):m.setdefault(base+i,0xA5)
    m[ROWS[0]+11]=c.selector;m[ROWS[1]+11]=(c.selector+1)&255
    put(m,s['D_800B0DF0'],ROWS[0]);put(m,s['D_800B0E00'],c.unused^0x12345678);put(m,s['D_800B0E00']+4,c.view^0xFEDCBA98)
    m[s['D_800BE616']]=c.disabled;put(m,s['D_800BE9E4'],c.clock);put16(m,s['D_800CBD4E'],c.accumulator)
    put(m,INDEX,c.unused)
    for i in range(256):put(m,s['D_8008CD04']+4*i,PROVIDER+4*i)
    return m


def public(m):return {a:v for a,v in m.items()if not STACK-0x600<=a<STACK+0x408}


def effect(m,s,c,kind,entry_sp):
    pair=s['D_800B0E00'];clock=s['D_800BE9E4'];acc=s['D_800CBD4E'];gate=s['D_800BE616']
    if kind==0:
        if c.mode&1:put(m,pair,c.view^0xABCD0001);put(m,pair+4,c.unused^0x12340002)
        if c.mode&8:put(m,entry_sp+4,0x87654321^c.view)
    elif kind==1:
        if c.mode&2:put(m,s['D_800B0DF0'],ROWS[1])
    elif kind==2:
        if c.mode&4:m[gate]^=1;put(m,clock,read(m,clock)^0x80000001);put16(m,acc,read16(m,acc)^0xFF80)
    elif kind>=0x100:
        if c.mode&1:m[gate]=0
        if c.mode&2:put(m,clock,(read(m,clock)+1)&0xFFFFFFFF);put16(m,acc,read16(m,acc)^0xAB00)
    elif kind==3:
        if c.mode&4:m[gate]=1
    elif kind==4:
        if c.mode&1:put(m,clock,read(m,clock)^0xFFFFFFFF);put16(m,acc,0xFFFE)


def reference(c,phase=0,symbols=None,memory=None,entry_sp=None,real_noop=False):
    s=symbols or SYMBOLS;m=dict(fixture(c,phase,s)if memory is None else memory);calls=[]
    sp=STACK+phase if entry_sp is None else entry_sp;put(m,sp,c.unused);put(m,sp+4,c.view)
    def call(kind,args=()):
        target=PROVIDER+4*(kind-0x100)if kind>=0x100 else s[CALLEES[kind]]
        calls.append((target,args))
        if not(real_noop and kind==0):effect(m,s,c,kind,sp)
    call(0);pair=s['D_800B0E00'];call(1,(read(m,pair),read(m,pair+4)));call(2)
    selector=m[read(m,s['D_800B0DF0'])+11]
    if selector:call(0x100+selector,(read(m,sp+4),))
    if not m[s['D_800BE616']]:call(3);call(4)
    put16(m,s['D_800CBD4E'],read16(m,s['D_800CBD4E'])+((read(m,s['D_800BE9E4'])<<6)&0xFFFFFFFF))
    return m,calls


class FrameOracle(TimingOracle):
    def __init__(self,words,c=Case(),phase=0,symbols=None,entry=source.ENTRY,connected=None,memory=None):
        self.frame_case=c;self.anchors=symbols or SYMBOLS;self.leaf_sp=STACK+phase
        super().__init__(words,fixture(c,phase,self.anchors)if memory is None else memory,
            phase=phase,entry=entry,arguments=(c.unused,c.view),connected=connected)
    def record_call(self,target):
        if target==source.ENTRY:
            self.leaf_sp=self.r[29];args=self.arguments(2)
        elif PROVIDER<=target<PROVIDER+1024:args=self.arguments(1)
        else:
            name=next((n for n in CALLEES if self.anchors[n]==target),None)
            assert name is not None,hex(target);args=self.arguments(2)if name==CALLEES[1]else()
        self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        kind=0x100+(target-PROVIDER)//4 if PROVIDER<=target<PROVIDER+1024 else next(i for i,n in enumerate(CALLEES)if self.anchors[n]==target)
        effect(self.memory,self.anchors,self.frame_case,kind,self.leaf_sp)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo,self.condition=0x87654321,0x12345678,True


def corpus():
    for selector,gate,mode in itertools.product(range(256),(0,1),(0,1,6,15)):
        yield Case(selector,gate,WORDS[selector%8],PHASES[(selector+mode)%8],WORDS[(selector+1)%8],WORDS[(selector+3)%8],mode)
    for tick,acc,view,mode in itertools.product(WORDS,PHASES,WORDS,(0,7)):
        yield Case(1,0,tick,acc,view,view^0xA500005A,mode)


def native_harness(body):
    callbacks='\n'.join('static void cb%d(s32 view){call(%d,(u32)view,0);}'%(i,0x100+i)for i in range(256))
    return """typedef unsigned char u8;typedef unsigned short u16;typedef unsigned int u32;typedef int s32;
typedef struct{u8 bytes[32];}struct104;typedef void(*FrameLayerCallback)(s32);
static struct104 rows[2];struct104*D_800B0DF0;FrameLayerCallback D_8008CD04[256];
s32 D_800B0E00[2],D_800BE9E4;u8 D_800BE616;u16 D_800CBD4E;
typedef struct{u32 selector,gate,clock,acc,view,unused,mode,pair0,pair1,row,count,events[8][3];}State;
static State actual,expected;static u32 fences[4]={0xA5A5A5A5,0x5A5A5A5A,0x12345678,0x87654321};
static void invoke(State*s,u32 kind,u32 a,u32 b){
 u32 n=s->count++;s->events[n][0]=kind;s->events[n][1]=a;s->events[n][2]=b;
 if(kind==0){if(s->mode&1){s->pair0=s->view^0xABCD0001;s->pair1=s->unused^0x12340002;}}
 else if(kind==1){if(s->mode&2)s->row=1;}
 else if(kind==2){if(s->mode&4){s->gate^=1;s->clock^=0x80000001;s->acc^=0xFF80;}}
 else if(kind>=0x100){if(s->mode&1)s->gate=0;if(s->mode&2){s->clock++;s->acc^=0xAB00;}}
 else if(kind==3){if(s->mode&4)s->gate=1;}
 else if(kind==4){if(s->mode&1){s->clock^=0xFFFFFFFF;s->acc=0xFFFE;}}
}
static void push(void){
 D_800B0DF0=&rows[actual.row];rows[0].bytes[11]=(u8)actual.selector;rows[1].bytes[11]=(u8)(actual.selector+1);
 D_800B0E00[0]=(s32)actual.pair0;D_800B0E00[1]=(s32)actual.pair1;
 D_800BE9E4=(s32)actual.clock;D_800CBD4E=(u16)actual.acc;D_800BE616=(u8)actual.gate;
}
static void pull(void){actual.clock=(u32)D_800BE9E4;actual.acc=D_800CBD4E;actual.gate=D_800BE616;
 actual.pair0=(u32)D_800B0E00[0];actual.pair1=(u32)D_800B0E00[1];actual.row=D_800B0DF0==&rows[1];}
static void call(u32 kind,u32 a,u32 b){pull();invoke(&actual,kind,a,b);push();}
void func_15165F70(void){call(0,0,0);}
void func_15195FF0(s32 a,s32 b){call(1,(u32)a,(u32)b);}
void func_1510C8A8(void){call(2,0,0);}
void func_1517DE5C(void){call(3,0,0);}
void func_151880C0(void){call(4,0,0);}
""" + callbacks + '\n' + body + """
static void reference(void){u32 selected;invoke(&expected,0,0,0);
 invoke(&expected,1,expected.pair0,expected.pair1);invoke(&expected,2,0,0);
 selected=(expected.selector+expected.row)&255;if(selected)invoke(&expected,0x100+selected,expected.view,0);
 if(!expected.gate){invoke(&expected,3,0,0);invoke(&expected,4,0,0);}
 expected.acc=(expected.acc+(expected.clock<<6))&65535;
}
static int run(void){
 const u32 words[]={0,1,0xFFFFFFFF,0x80000000,0x7FFFFFFF,0xFFFF8000,0x40000000,0x12345678};
 const u32 phases[]={0,1,0x3FF,0x400,0x7FFF,0x8000,0xFFFE,0xFFFF},gates[]={0,1,128,255};
 FrameLayerCallback callbacks[]={""" + ','.join('cb%d'%i for i in range(256)) + """};
 u32 sel,g,t,mode,i,j,n=0;
 for(i=0;i<256;i++)D_8008CD04[i]=callbacks[i];
 for(sel=0;sel<256;sel++)for(g=0;g<4;g++)for(t=0;t<8;t++)for(mode=0;mode<8;mode++){
  actual=(State){0};actual.selector=sel;actual.gate=gates[g];actual.clock=words[t];
  actual.acc=phases[(sel+mode)%8];actual.view=words[(sel+g+mode)%8];actual.unused=words[(t+3)%8];actual.mode=mode;
  actual.pair0=actual.unused^0x12345678;actual.pair1=actual.view^0xFEDCBA98;expected=actual;push();reference();
  func_151749F8((s32)actual.unused,(s32)actual.view);pull();
  if(actual.count!=expected.count||actual.acc!=expected.acc||actual.clock!=expected.clock||actual.gate!=expected.gate
    ||actual.pair0!=expected.pair0||actual.pair1!=expected.pair1||actual.row!=expected.row)return 23;
  for(i=0;i<actual.count;i++)for(j=0;j<3;j++)if(actual.events[i][j]!=expected.events[i][j])return 23;
  if(fences[0]!=0xA5A5A5A5||fences[1]!=0x5A5A5A5A||fences[2]!=0x12345678||fences[3]!=0x87654321)return 23;
  for(i=0;i<256;i++)if(D_8008CD04[i]!=callbacks[i])return 23;n++;
 }return n==65536?0:24;
}
__attribute__((force_align_arg_pointer)) void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
"""


class FrameLayerDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out)
        cls.installed=(ROOT/source.SOURCE).read_text()==source.recovered_owner(cls.values[source.SOURCE].decode())
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.obj,diag=source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.DECLARATIONS+source.EXTRA_DECLARATIONS+source.SELECTED,'fresh-selected')
        if diag:raise ValueError(diag)
        data,fs=source.link_owner(ROOT,cls.out,cls.obj,source.OWNER);cls.rom=cls.values['conker/conker.us.bin']
        cls.words=list(struct.unpack_from('>43I',data,fs[source.FUNCTION]['value']));cls.truth=list(struct.unpack_from('>43I',cls.rom,source.ROM))
        cls.receipt=dict(installed=cls.installed);cls.native_common={}
    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n');print(cls.receipt)
    def compare(self,c,phase=0,words=None,symbols=None,entry=source.ENTRY,connected=None,real_noop=False):
        expected,calls=reference(c,phase,symbols,real_noop=real_noop);models=[]
        for w in words or(self.truth,self.words):
            m=FrameOracle(w,c,phase,symbols,entry,connected).run();self.assertEqual((public(m.memory),m.calls),(public(expected),calls));models.append(m)
        self.assertEqual(complete(models[0]),complete(models[1]));return models
    def test_01_direct_words_typed_caller_Make_and_effective_stub(self):
        self.assertEqual(self.words,self.truth);self.assertEqual(source.payload(self.obj),source.payload(source.original(ROOT,self.out)))
        q=json.loads((self.out/'qualification.json').read_text());m=json.loads((self.out/'make-shadow.json').read_text())
        self.assertEqual((q['words'],q['frame'],q['relocations'],q['preserved_neighbors'],q['preserved_caller_functions']),(43,24,17,3,16))
        self.assertTrue(m['entire_caller_object_identical']);self.assertEqual(m['actual_Make_commands'],6)
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,source.ENTRY,172)
        stale=FrameOracle(struct.unpack_from('>43I',old,at)).run();self.assertFalse(stale.calls);self.assertTrue(self.compare(Case())[0].calls)
        self.receipt.update(words=43,frame=24,bindings=17,new_guards=0,compiler_only=True,neighbors=3,caller_functions=16,caller_object_unchanged=True,actual_Make_commands=6,old_stub_rejected=True)
    def test_02_full_bytes_boundaries_late_effects_homes_and_unsigned_wrap(self):
        count=0;visits=set()
        for c,phase in itertools.product(corpus(),(0,8)):
            m=self.compare(c,phase)[0];visits.update(m.visits);count+=1
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+172,4)),visits)
        self.receipt.update(guest_phases=count,all43_words_visited=True,synthetic_256_entry_backed_table=True,private_incoming_home_mutation_guest_only=True,late_gates_config_pair_clock_and_phase=True)
    def native(self,body,label,opt='-O2'):
        flags=native_command(opt)
        if opt not in self.native_common:
            common=self.out/('native-common'+opt+'.c');obj=common.with_suffix('.o')
            common.write_text(native_harness('void func_151749F8(s32,s32);'))
            q=subprocess.run([*flags,'-c',str(common),'-o',str(obj)],cwd=ROOT,capture_output=True,text=True)
            (self.out/('native-common'+opt+'-diagnostics.txt')).write_text(q.stdout+q.stderr)
            self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.native_common[opt]=obj
        p=self.out/(label+opt);c=p.with_suffix('.c');obj=c.with_suffix('.o')
        c.write_text(NATIVE_DECLARATIONS+body)
        log=''
        for cmd in([*flags,'-c',str(c),'-o',str(obj)],[*flags,str(obj),str(self.native_common[opt]),'-o',str(p)]):
            q=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);log+=q.stdout+q.stderr
            (self.out/(label+opt+'-diagnostics.txt')).write_text(log);self.assertEqual(q.returncode,0,log)
        return subprocess.run([str(p)],capture_output=True).returncode
    def test_03_native32_three_optimizations_and_defined_wrong_C(self):
        for opt in('-O0','-O2','-O3'):self.assertEqual(self.native(source.SELECTED,'native',opt),0)
        b=source.SELECTED
        controls=dict(noFirst=b.replace('    func_15165F70();',''),wrongPair=b.replace('D_800B0E00[0], D_800B0E00[1]','D_800B0E00[1], D_800B0E00[0]'),
            wrongOrder=b.replace('func_15195FF0(D_800B0E00[0], D_800B0E00[1]);\n    func_1510C8A8();','func_1510C8A8();\n    func_15195FF0(D_800B0E00[0], D_800B0E00[1]);'),
            skipCallback=b.replace('if (((u8 *)D_800B0DF0)[0xB] != 0)','if (0)'),wrongView=b.replace('](view);','](view ^ 1);'),
            wrongGate=b.replace('D_800BE616 == 0','D_800BE616 != 0'),omitLast=b.replace('        func_151880C0();',''),wrongShift=b.replace('<< 6','<< 5'),
            resetPhase=b.replace('D_800CBD4E +=','D_800CBD4E ='),
            cachedClock=b.replace('    func_15165F70();','    u32 cached = (u32)D_800BE9E4;\n    func_15165F70();').replace('+= (u32)D_800BE9E4','+= cached'),
            cachedPhase=b.replace('    func_15165F70();','    u16 cached = D_800CBD4E;\n    func_15165F70();').replace('D_800CBD4E += (u32)D_800BE9E4 << 6;','D_800CBD4E = cached + ((u32)D_800BE9E4 << 6);'))
        controls['cachedSelector']=b.replace('    func_15165F70();','    u8 cached = ((u8 *)D_800B0DF0)[0xB];\n    func_15165F70();')
        start=controls['cachedSelector'].index('    func_15165F70();')
        controls['cachedSelector']=controls['cachedSelector'][:start]+controls['cachedSelector'][start:].replace('((u8 *)D_800B0DF0)[0xB]','cached')
        for label,body in controls.items():self.assertNotEqual(body,b);self.assertEqual(self.native(body,label),23,label)
        self.receipt.update(native32_cases_per_optimization=65536,native_optimizations=['O0','O2','O3'],trap_UBSan=True,defined_wrong_C_controls=len(controls),native_private_home_alias_claimed=False,separate_runtime_and_body_units=True,common_harness_compiles=3)
    def linked(self,obj,symbols,entry,label):
        data,fs,rs=source.parse_object(obj);asm,unknown=emit_function(data,fs[source.FUNCTION],rs,source.FUNCTION,symbols);self.assertFalse(unknown)
        p=self.out/label;a=p.with_suffix('.s');o=p.with_suffix('.o');ld=p.with_suffix('.ld');elf=p.with_suffix('.elf')
        a.write_text(asm);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(o),str(a)],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%x for x in symbols.items()],'-o',str(elf),str(o)],capture_output=True,check=True)
        return struct.unpack_from('>43I',sections(elf)['.text'][1])
    def test_04_independent_GNU_rebases_and_every_target_access_prefix(self):
        count=cuts=0
        for i,entry in enumerate((source.ENTRY,0x18017FFC,0x1A028000)):
            s=SYMBOLS if not i else {n:(0x17010000+0x1000*j+4*i if n in CALLEES else 0x80308000+0x100*j+0x100000*i)for j,n in enumerate(SYMBOLS)}
            images=[self.linked(obj,s,entry,'rebase-%d-%d'%(i,j))for j,obj in enumerate((source.original(ROOT,self.out),self.obj,self.out/'qualified-padded.o'))]
            self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for selector,gate,mode,phase in itertools.product((0,255),(0,1),(0,15),(0,8)):
                self.compare(Case(selector,gate,mode=mode),phase,images[:2],s,entry);count+=1
        for c,phase in itertools.product((Case(0),Case(1),Case(255,1,mode=15)),(0,8)):
            good=FrameOracle(self.truth,c,phase).run()
            for cut in range(good.root_accesses):
                models=[FrameOracle(w,c,phase)for w in(self.truth,self.words)]
                for m in models:
                    m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=9,rebase_phases=count,fired_target_access_prefixes=cuts,portable_C_fault_MMU_claimed=False)
    def test_05_actual_frame_caller_window_and_whole_caller_identity(self):
        jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF));ptr=struct.pack('>I',source.ENTRY)
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==jal],[0x46760])
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==ptr],[])
        window=struct.unpack_from('>6I',self.rom,0x46754);count=0
        for value,mode,phase in itertools.product(WORDS,(0,15),(0,8)):
            c=Case(view=0,unused=value,mode=mode);m=fixture(c,phase);expected,calls=reference(c,phase,memory=m,entry_sp=STACK+phase-40);models=[]
            for w in(self.truth,self.words):
                a=FrameOracle(window,c,phase,entry=0x150192A4,memory=m,connected={source.ENTRY+i*4:v for i,v in enumerate(w)})
                a.r[29]-=40;a.code=StopCode(a.code,a,0x150192B8)
                with self.assertRaises(WindowEnd):a.run()
                self.assertEqual(a.calls,[(source.ENTRY,(value,0))]+calls);self.assertEqual(public(a.memory),public(expected));models.append(a)
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt.update(actual_caller_window_phases=count,actual_caller_window_words=5,caller_initial_view_zero=True,full_parent_execution_claimed=False)
    def test_06_original_current_noop_and_static_table_holes(self):
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,SYMBOLS[CALLEES[0]],8)
        self.assertEqual(old[at:at+8],struct.pack('>2I',0x03E00008,0))
        rom=SYMBOLS[CALLEES[0]]-0x15000000+0x2D4B0;self.assertEqual(old[at:at+8],self.rom[rom:rom+8])
        table=struct.unpack_from('>28I',self.rom,0x2317C4);self.assertEqual([i for i,x in enumerate(table)if not x],[0,12,27])
        count=0
        for selector,gate,mode,phase in itertools.product((0,1,11,13,26),(0,1),(0,15),(0,8)):
            self.compare(Case(selector,gate,mode=mode),phase,connected={SYMBOLS[CALLEES[0]]:0x03E00008,SYMBOLS[CALLEES[0]]+4:0},real_noop=True);count+=1
        self.receipt.update(real_noop_phases=count,real_noop_words=2,retail_table_entries=28,retail_null_slots=[0,12,27],nonzero_null_or_out_of_range_selector_safety_claimed=False,other_helpers_and_callbacks_bounded_hooks=True)
    def test_07_guest_private_argument_home_mutation_is_effective(self):
        c=Case(selector=1,view=0x12345678,mode=8)
        m=self.compare(c)[0];callbacks=[args for target,args in m.calls if PROVIDER<=target<PROVIDER+1024]
        self.assertEqual(callbacks,[(0x87654321^c.view,)])
        self.assertNotEqual(callbacks,[(c.view,)])
        self.receipt.update(private_view_home_mutation_effective=True,portable_native_caller_private_alias_claimed=False)
    def test_08_pins_strict_image_and_unchanged_guard_manifest(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+172];pred=source.predicted_image(before,truth)
        source.check_image(before,pred,truth);at=source.elf_slot_offset(before,source.ENTRY,172)
        symbol_positions=[offset for offset,name,_,_ in source.symbol_rows(before)if name in('D_8008CD04','func_1517A84C')]
        string_positions=[string for _,name,_,string in source.symbol_rows(before)if name in('D_8008CD04','func_1517A84C')]
        for pos in(0,at-1,at,at+168,at+172,len(before)-1,*symbol_positions,*string_positions):
            wrong=bytearray(pred);wrong[pos]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(wrong),truth)
        with self.assertRaises(ValueError):source.check_image(before,pred[:-1],truth)
        for name,wanted in source.INPUTS.items():
            old=self.values[name];self.assertEqual(source.digest(old),wanted)
            expected=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else source.recovered_caller(old.decode()).encode()if self.installed and name==source.CALLER_SOURCE else pred if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),expected,name)
        self.receipt.update(pinned_inputs=len(source.INPUTS),strict_image_negatives=11,guard_manifest_unchanged=True,canonical_symbols_preserved_after_checked_serialization=True)
