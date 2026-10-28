"""Record phase/lifetime: signed selector, live callback home, wrap and release integration."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,os,re,struct,subprocess,unittest
from tools.experiments import game_record_phase_lifetime_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2];RECORD,OTHER,NEXT=0x22000,0x23000,0x24000
CALLBACK,NEGATIVE_CALLBACK=0x1516F000,0x1516F100
COUNT,SLOTS=0x800DD190,0x800DD198
@dataclass(frozen=True)
class Case:
    phase_value:int=123
    rate:int=7
    period:int=3
    lifetime:int=10
    ticks:int=2
    selector:int=0
    mutation:int=0
    redirect:bool=False
    clock_alias:int=-1
    phase:int=0

def half(v):return((v&65535)^32768)-32768
def byte(v):return((v&255)^128)-128
def fixture(c,ticks=None,table=None):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-768,512)}
    for base in(RECORD,OTHER):
        m.update({base+i:(i*13+0x59)&255 for i in range(-16,96)})
        for off,v,size in((0,0x5E,1),(8,NEXT,4),(0x24,c.lifetime if base==RECORD else 5,2),(0x26,c.phase_value if base==RECORD else-123,2),(0x28,c.rate if base==RECORD else-7,2),(0x40,c.selector,1),(0x41,c.period,1)):put(m,base+off,v&((1<<(size*8))-1),size)
    clock=RECORD+c.clock_alias if c.clock_alias>=0 else source.TICKS if ticks is None else ticks
    if c.clock_alias<0:put(m,clock,c.ticks&0xFFFFFFFF)
    index=byte(c.selector);fn=NEGATIVE_CALLBACK if index<0 else CALLBACK;table=source.TABLE if table is None else table
    if index:put(m,(table+index*4)&0xFFFFFFFF,fn)
    return m,clock

def callback_effect(m,c,record,clock):
    if c.mutation&1:
        for off,v,size in((0x24,13,2),(0x26,-32768,2),(0x28,-7,2),(0x41,5,1)):put(m,record+off,v&((1<<(size*8))-1),size)
    if c.mutation&2:put(m,clock,0xFFFFFFFF)
    if c.mutation&4:put(m,record+8,NEXT+0x100)
    if c.redirect:put(m,STACK+c.phase,OTHER)

def free_effect(m,record):m[record+0x4A]^=0xA5

def reference(initial,c,clock):
    m=dict(initial);record=RECORD;calls=[];index=byte(m[record+0x40])
    if index:
        calls.append((NEGATIVE_CALLBACK if index<0 else CALLBACK,(record,)));callback_effect(m,c,record,clock)
        if c.redirect:record=read(m,STACK+c.phase)
    ticks=signed(read(m,clock));value=signed((half(read(m,record+0x26,2))+half(read(m,record+0x28,2))*ticks)&0xFFFFFFFF);period=m[record+0x41]*256
    if value>=period:value=signed((value-period)&0xFFFFFFFF)
    elif value<0:value=signed((value+period)&0xFFFFFFFF)
    lifetime=half(read(m,record+0x24,2));put(m,record+0x26,value&65535,2)
    if lifetime:
        left=signed((lifetime-signed(read(m,clock)))&0xFFFFFFFF)
        if left<=0:calls.append((source.FREE,(record,)));free_effect(m,record)
        else:put(m,record+0x24,left&65535,2)
    return m,calls

def public(m):return{a:b for a,b in m.items()if not STACK-768<=a<STACK+512}

class PhaseOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None,free=source.FREE):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(RECORD,),connected=connected);self.case,self.trace,self.free=c,[],free;self.clock=RECORD+c.clock_alias if c.clock_alias>=0 else source.TICKS
    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        assert target in(CALLBACK,NEGATIVE_CALLBACK,self.free,source.ENTRY,source.SCAN,source.ADAPTER,source.UNLINK),hex(target)
        args=self.arguments(2 if target==source.UNLINK else 1);self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        record=self.r[4]
        if target in(CALLBACK,NEGATIVE_CALLBACK):callback_effect(self.memory,self.case,record,self.clock)
        else:
            assert target in(self.free,source.UNLINK)
            if target==source.UNLINK:assert self.r[5]==1
            free_effect(self.memory,record)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011

class WindowBoundary(Exception):pass
class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==self.owner.window_end:raise WindowBoundary
        return super().__getitem__(pc)

def controls():
    b=source.SELECTED
    return dict(unsigned_selector=b.replace('*(s8 *)(record + 0x40)','*(u8 *)(record + 0x40)'),skip_callback=b.replace('if (selector != 0)','if (0)'),wrong_period=b.replace('record[0x41] << 8','record[0x41] << 7'),wrong_rate=b.replace('record + 0x28','record + 0x2A'),unsigned_phase=b.replace('value = *(s16 *)','value = *(u16 *)'),no_negative_wrap=b.replace('value = (s32)((u32)value + (u32)period);','value = value;'),inclusive_lifetime=b.replace('if (lifetime <= 0)','if (lifetime < 0)'),skip_negative_lifetime=b.replace('if (lifetime != 0)','if (lifetime > 0)'),eager_lifetime_store=b.replace('        if (lifetime <= 0)', '        *(s16 *)(record + 0x24) = lifetime;\n        if (lifetime <= 0)'),false_free=b.replace('if (lifetime <= 0)','if (lifetime >= 0)'),full_modulo=b.replace('if ((s32)value >= period)', 'if (period != 0) value = (u32)((s32)value % period);\n    if ((s32)value >= period)'))

def native_harness():
    t=source.HEADERS+r'''
#include "structs.h"
typedef void(*RecordPhaseCallback)(void*);
typedef struct{u8 pad0[0x24];s16 life,phaseValue,rate;u8 pad2A[0x16];s8 selector;u8 period;u8 pad42[2];s32 tickCell;u8 tail[8];}Record;
typedef char ABI[(sizeof(void*)==4&&sizeof(Record)==0x50&&__builtin_offsetof(Record,life)==0x24&&__builtin_offsetof(Record,phaseValue)==0x26&&__builtin_offsetof(Record,rate)==0x28&&__builtin_offsetof(Record,selector)==0x40&&__builtin_offsetof(Record,tickCell)==0x44)?1:-1];
static struct{u32 left[4];Record record;u32 right[4];}actual,expected;
static s32 clockValue,*clockPointer;static u32 mode,callbackCalls,freeCalls,callbackTag;static RecordPhaseCallback backing[512];
#define D_8008CA20 (backing+128)
#define D_800BE9E4 (*clockPointer)
static void callback(void*p,u32 tag){Record*r=(Record*)p;callbackCalls++;callbackTag=tag;if(mode&1){r->life=13;r->phaseValue=-32768;r->rate=-7;r->period=5;}if(mode&2)*clockPointer=-1;}
static void positive(void*p){callback(p,1);}static void negative(void*p){callback(p,2);}
void func_1516972C(struct102*p){freeCalls++;((u8*)p)[0x4A]^=0xA5;}
'''
    for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace('void '+source.FUNCTION,'static void '+name)+'\n'
    t+=r'''
typedef void(*Update)(u8*);
static int check(Update fn){u32 n,pattern,layout,i,wantCallback,wantFree,wantTag;u8*p=(u8*)&actual,*q=(u8*)&expected;s32 initialTick,tick,phaseValue,rate,period,life,left;u32 sum;
 for(n=0;n<65537;n++)for(pattern=0;pattern<4;pattern++)for(layout=0;layout<2;layout++){
  for(i=0;i<sizeof(actual);i++)p[i]=(u8)(i*13+n*3+pattern);
  actual.record.phaseValue=(s16)n;actual.record.rate=(s16)(n*17u);actual.record.period=(u8)(n>>8);actual.record.life=pattern==0?0:pattern==1?1:pattern==2?-1:32767;actual.record.selector=(s8)n;
  mode=pattern;initialTick=(n&3)==0?0:(n&3)==1?1:(n&3)==2?-1:(s32)0x80000000u;clockValue=actual.record.tickCell=initialTick;clockPointer=layout?&actual.record.tickCell:&clockValue;
  if(n==65536){actual.record.phaseValue=-30000;actual.record.rate=-32768;actual.record.period=3;actual.record.life=1;actual.record.selector=0;clockValue=actual.record.tickCell=1;}
  for(i=0;i<sizeof(actual);i++)q[i]=p[i];wantCallback=expected.record.selector!=0;wantTag=expected.record.selector<0?2:1;tick=layout?expected.record.tickCell:clockValue;
  if(wantCallback){if(mode&1){expected.record.life=13;expected.record.phaseValue=-32768;expected.record.rate=-7;expected.record.period=5;}if(mode&2){tick=-1;if(layout)expected.record.tickCell=-1;}}
  phaseValue=expected.record.phaseValue;rate=expected.record.rate;period=expected.record.period*256;sum=(u32)phaseValue+(u32)rate*(u32)tick;phaseValue=(s32)sum;
  if(phaseValue>=period)phaseValue=(s32)((u32)phaseValue-(u32)period);else if(phaseValue<0)phaseValue=(s32)((u32)phaseValue+(u32)period);
  life=expected.record.life;expected.record.phaseValue=(s16)phaseValue;wantFree=0;
  if(life){left=(s32)((u32)life-(u32)tick);if(left<=0){wantFree=1;((u8*)&expected.record)[0x4A]^=0xA5;}else expected.record.life=(s16)left;}
  callbackCalls=freeCalls=callbackTag=0;fn((u8*)&actual.record);
  if(callbackCalls!=wantCallback||freeCalls!=wantFree||(wantCallback&&callbackTag!=wantTag))return 1;for(i=0;i<sizeof(actual);i++)if(p[i]!=q[i])return 1;
 }return 0;}
static int run(void){u32 i;for(i=0;i<512;i++)backing[i]=i<128?negative:positive;if(check(selected))return 10;
'''
    for i,name in enumerate(controls()):t+='if(!check('+name+'))return '+str(20+i)+';\n'
    return t+'return 0;}\n'+START

class RecordPhaseLifetimeTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>48I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,functions=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>48I',data,functions[source.FUNCTION]['value']))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+'\n')
    def compare(self,c=Case(),images=None,entry=source.ENTRY,ticks=None,table=None,free=source.FREE):
        initial,clock=fixture(c,ticks,table);want,calls=reference(initial,c,clock);calls=[(free if t==source.FREE else t,a)for t,a in calls];pair=[]
        for words in images or(self.truth,self.words):
            m=PhaseOracle(words,initial,c,entry,free=free);m.clock=clock;m.run();self.assertEqual((public(m.memory),m.calls),(public(want),calls),c);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
    def linked(self,entry,ticks,table,free):
        if not hasattr(self,'links'):self.links={}
        key=(entry,ticks,table,free)
        if key in self.links:return self.links[key]
        pair=[];number=len(self.links)
        for j,obj in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'selected.o')):
            p=self.fresh/('layout-%d-%d.ld'%(number,j));elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,'--defsym=D_800BE9E4=0x%X'%ticks,'--defsym=D_8008CA20=0x%X'%table,'--defsym=func_1516972C=0x%X'%free,'-o',str(elf),str(obj)],capture_output=True,check=True);pair.append(list(struct.unpack_from('>48I',sections(elf)['.text'][1])))
        self.assertEqual(*pair);self.links[key]=pair;return pair
    def test_01_owner_Make_registration_tables_and_canonical_ABI(self):
        self.assertEqual(self.words,self.truth);source.checked_payload(*source.payload(self.out/'selected.o'))
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertFalse(diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),4)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),3);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_196DB0.c.o.compact'),4)
        self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'proposed-owner.c').read_text());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),3);self.assertNotIn('#pragma GLOBAL_ASM',(self.out/'proposed-owner.c').read_text())
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertEqual([i*4 for i,w in enumerate(ws)if w==source.ENTRY],[0x231280]);self.assertFalse(any(w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws));self.assertEqual(source.REGISTRY+0x5E*0x34,0x8008C7C0)
        data=self.values['conker/asm/data/22FF90.rodata.s'].decode();part=data.split('dlabel D_8008CA20',1)[1].split('enddlabel D_8008CA20',1)[0];self.assertEqual(len(re.findall(r'/\*',part)),11);self.assertEqual(struct.unpack_from('>I',self.rom,0x231280)[0],source.ENTRY)
        self.assertIn('typedef void (*RecordPhaseCallback)(void *);',source.DECLARATIONS);self.assertIn('void func_1516972C(struct102 *);',source.DECLARATIONS);self.assertIn('extern void (*D_8008CA20[])(void *);',self.values['conker/src/game_1944C0.c'].decode())
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=48,frame=24,bindings=5,guards=0,neighbors=3,compact_functions=4,GLOBAL_ASM_routines=0,Make_commands=3,diagnostics=0,registered_type=94,descriptor_stride=52,optional_retail_callbacks=11,canonical_void_pointer_callback_and_struct102_release=True)
    def test_02_guest_signed_selector_wrap_lifetime_clobber_and_alias_cases(self):
        count=0;visits=set()
        for value,rate,period,life,ticks in itertools.product((-32768,-1,0,1,32767),(-32768,-1,0,1,32767),(0,1,3,255),(-32768,-1,0,1,32767),(0,1,0xFFFFFFFF,0x80000000)):
            m=self.compare(Case(value,rate,period,life,ticks));visits.update(m.visits);count+=1
        for selector,mutation,redirect in itertools.product(range(256),(0,1,2,3,4),(False,True)):
            m=self.compare(Case(selector=selector,mutation=mutation,redirect=redirect,phase=(selector&1)*8));visits.update(m.visits);count+=1
        for off,selector,mutation in itertools.product(range(0,80,4),(0,2,128),(0,1,2)):
            images=self.linked(source.ENTRY,RECORD+off,source.TABLE,source.FREE);self.compare(Case(clock_alias=off,selector=selector,mutation=mutation),images);count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+192,4))-{source.ENTRY+172})
        self.receipt['guest']=dict(cases=count,visited_words=47,unreachable_lifetime_store_retained=True,all256_signed_selectors=True,callback_mutations_and_volatile_outgoing_home_clobbers=True,live_incoming_home_redirect=True,signed_wrapped_phase_and_one_adjustment=True,lifetime_zero_positive_negative_and_wrapped_ticks=True,all20_aligned_clock_aliases=True,full_private_state_trace=True,guest_only_invalid_retail_index_and_home_probes=True)
    def test_03_actual_dispatch_window_and_connected_release_helpers(self):
        before=self.values['conker/build/conker.us.elf'];helpers={};sizes={source.FREE:112,source.SCAN:80,source.ADAPTER:32}
        for entry,size in sizes.items():
            raw=self.rom[entry-0x14FD2B50:entry-0x14FD2B50+size];self.assertEqual(before[source.elf_slot_offset(before,entry,size):source.elf_slot_offset(before,entry,size)+size],raw);helpers.update({entry+4*i:w for i,w in enumerate(struct.unpack('>%dI'%(size//4),raw))})
        va=0x15167158;parent=list(struct.unpack_from('>11I',self.rom,va-0x14FD2B50));count=0
        for selector,life,ticks,mutation in itertools.product((0,2,128),(-1,0,5),(0,1,10),(0,4)):
            c=Case(selector=selector,lifetime=life,ticks=ticks,mutation=mutation);initial,clock=fixture(c);put(initial,COUNT,1,1);put(initial,SLOTS,RECORD);put(initial,SLOTS+4,0xDEADBEEF);put(initial,source.REGISTRY+94*52,source.ENTRY);put(initial,0x8008B4D0+94*52,0);want,calls=reference(initial,c,clock);put(want,SLOTS+4,NEXT);expected=[(source.ENTRY,(RECORD,))]
            for t,a in calls:
                expected.append((t,a))
                if t==source.FREE:
                    expected.extend([(source.SCAN,a),(source.ADAPTER,a),(source.UNLINK,(a[0],1))]);put(want,SLOTS,read(want,a[0]+8))
            pair=[]
            for words in(self.truth,self.words):
                connected={**helpers,**{source.ENTRY+4*i:w for i,w in enumerate(words)}};m=PhaseOracle(parent,initial,c,va,connected);m.r[16]=RECORD;m.r[18]=source.REGISTRY+94*52;m.r[19]=COUNT;m.r[20]=SLOTS;m.window_end=va+44;m.code=WindowCode(dict(m.code),m);m.clock=clock
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual((public(m.memory),m.calls),(public(want),expected),c);pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);count+=1
        self.assertIn('s32 func_151670C0() {\n    return 0;\n}',self.values['conker/src/game_1944C0.c'].decode());self.receipt['caller']=dict(original_dispatch_words=11,connected_cases=count,retained_helper_words=[28,20,8],retained_helpers_equal_current_ELF=True,queued_next_before_call_and_release_scan=True,current_dispatcher_stub_unchanged=True,bounded_final_unlink_provider_no_full_list_gameplay_claim=True)
    def test_04_native32_valid_storage_signed_index_and_effective_controls(self):
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=65537*4*2,effective_controls=len(controls()),trapping_UBSan=True,valid_typed_record_and_512_callback_cells=True,all256_signed_selectors_and_period_bytes=True,all_halfword_phase_encodings=True,whole_storage_fences=True,valid_disjoint_or_s32_tick_cell=True,guest_live_home_and_overlapping_halfword_clock_separate=True)
    def test_05_fired_access_prefixes_lazy_zero_selector_and_lifetime(self):
        cuts=0
        for selector,life,mutation,redirect in itertools.product((0,128),(-1,0,5),(0,3),(False,True)):
            c=Case(selector=selector,lifetime=life,mutation=mutation,redirect=redirect);initial,_=fixture(c);good=self.compare(c)
            for cut in range(good.root_accesses):
                pair=[]
                for words in(self.truth,self.words):
                    m=PhaseOracle(words,initial,c);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,cut);pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
        for words in(self.truth,self.words):
            c=Case(selector=0,lifetime=0);initial,_=fixture(c);m=PhaseOracle(words,initial,c).run();self.assertEqual(sum(e[0]=='R'and e[1]==source.TICKS for e in m.trace),1);self.assertFalse(m.calls);self.assertFalse(any(e[0]=='W'and e[1]>=STACK for e in m.trace))
        self.receipt['faults']=dict(fired_prefix_pairs=cuts,full_private_state_trace_PC_delay=True,zero_selector_needs_no_table_mapping_or_incoming_home_store=True,zero_lifetime_has_one_clock_read_and_no_release=True)
    def test_06_real_padder_raw_controls_and_three_GNU_rebases(self):
        raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[100]^=1
        for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,{**rs,156:[('R_MIPS_26','wrong')]})):
            with self.assertRaises(ValueError):source.checked_payload(b,bindings)
        p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());cases=0
        for entry,ticks,table,free in((source.ENTRY,source.TICKS,source.TABLE,source.FREE),(0x17007FFC,0x800B7FFC,0x80088004,0x17012340),(0x2500FFFC,0x800C8004,0x80087FFC,0x25123400)):
            images=self.linked(entry,ticks,table,free)
            for selector,life in itertools.product((0,2,128),(0,-1,5)):
                self.compare(Case(selector=selector,lifetime=life),images,entry,ticks,table,free);cases+=1
        self.receipt['rebases']=dict(layouts=3,guest_cases=cases,four_HI_LO_and_one_J26_bindings=True,signed_low_half_carry_and_negative_index=True,GNU_original_and_compiler_objects=True,raw_binding_controls=3,guards=0)
    def test_07_actually_compiled_cached_clock_rejected_by_value(self):
        body=source.SELECTED.replace('    s32 lifetime;','    s32 lifetime;\n    s32 captured;').replace('    value = *(s16 *)','    captured = D_800BE9E4;\n    value = *(s16 *)').replace('(u32)D_800BE9E4','(u32)captured');obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+body,'negative-cached-clock');self.assertFalse(diag);p=self.fresh/'negative.ld';elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x15169988 : SUBALIGN(4) { *(.text) } }\n');subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,'--defsym=D_800BE9E4=0x22024','--defsym=D_8008CA20=0x8008CA20','--defsym=func_1516972C=0x1516972C','-o',str(elf),str(obj)],capture_output=True,check=True);raw=sections(elf)['.text'][1];words=list(struct.unpack('>%dI'%(len(raw)//4),raw));c=Case(phase_value=0,rate=1,period=3,lifetime=-1,clock_alias=0x24);initial,clock=fixture(c);m=PhaseOracle(words,initial,c).run();want,_=reference(initial,c,clock);self.assertEqual((read(m.memory,RECORD+0x24,2),read(want,RECORD+0x24,2)),(65535,64767));self.receipt['compiled_control']=dict(actually_compiled_cached_clock_rejected=True,live_phase_word_alias_changes_remaining_lifetime=True,value_failure_not_unmapped_read=True)
    def test_08_strict_entire_image_extent_and_corruptions(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+192];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,192);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
        for offset in(20,at,at+180,at+192,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        self.assertEqual(sum(x!=y for x,y in zip(before,expected)),136);self.receipt['image']=dict(changed_bytes=136,code_bytes=135,size_bytes=1,other6055_bodies_and6056_addresses_fixed=True,all_named_definitions_checked=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,guard_manifest_shared_headers_helper_and_current_dispatcher_unchanged=True)
