"""Ballistic billboard motion: float order, live clock aliases, dispatch result and whole image."""
from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,math,os,re,struct,subprocess,unittest
from tools.experiments import game_ballistic_billboard_gate_match as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_effect_owner_ray import RayOracle
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults
ROOT=Path(__file__).resolve().parents[2];ACTOR=0x22000;UPDATE,POST,FREE=0x1513E6E8,0x15149EC4,0x1516972C
OFFSETS=(0x2C,0x30,0x150,0x4C,0x50,0x38,0x15C)
DEFAULT=tuple(map(bits,(20.,20.,.25,2.,1.,0.,200.)))
FLOATS=(0,0x80000000,1,0x80000001,0x3F000000,0x3F800000,0x3F800001,0x411FFFFF,0x41200000,0x41200001,0x40000000,0xBF800000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC00001,0xFFC12345,0x3EFFFFFF,0x33800000)
@dataclass(frozen=True)
class Case:
    values:tuple=DEFAULT
    step:int=0x3F800000
    alias:int=-1
    phase:int=0
    active:bool=True
    flags:int=0
    life:int=5
    ticks:int=1
    update:bool=False
    update_result:int=1
    post:bool=False
    post_result:int=0
    mutation:int=0
    invoke:bool=True
    alpha:int=200
    cutoff:int=10
    multiplier:int=3

def fixture(c,time_address=None):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,512)};m.update({ACTOR+i:(i*13+0x59)&255 for i in range(-16,0x190)})
    for off,value in zip(OFFSETS,c.values):put(m,ACTOR+off,value)
    addr=ACTOR+c.alias if c.alias>=0 else source.TIME if time_address is None else time_address;put(m,addr,c.step)
    for off,value,size in((0x10,int(c.active),4),(0x58,c.flags,4),(0x1C,c.life&65535,2),(0x24,0,4),(0x70,int(c.update),1),(0x71,28 if c.invoke else 0,1),(0x72,int(c.post),1),(0x5C,c.alpha,1),(0x6C,c.cutoff&65535,2),(0x6E,c.multiplier&65535,2)):put(m,ACTOR+off,value,size)
    put(m,source.TICKS,c.ticks&0xFFFFFFFF);put(m,source.TABLE+28*4,source.ENTRY);put(m,0x80089CB8+4,UPDATE);put(m,0x80089E10+4,POST)
    return m

def public(m):return{a:b for a,b in m.items()if not STACK-1024<=a<STACK+512}
def op(a,b,kind):
    a,b=floating(a),floating(b);return bits(a*b if kind=='*'else a-b if kind=='-'else a+b)
def half(v):return(v^32768)-32768
def reference(initial,c=Case(),time_address=None):
    m=dict(initial);clock=ACTOR+c.alias if c.alias>=0 else source.TIME if time_address is None else time_address
    width,damping,height,velocity,accel=(read(m,ACTOR+off)for off in(0x2C,0x150,0x30,0x50,0x4C))
    width=op(width,op(width,damping,'*'),'-');height=op(height,op(height,damping,'*'),'-');put(m,ACTOR+0x2C,width);put(m,ACTOR+0x30,height)
    step=read(m,clock);linear=op(velocity,step,'*');quadratic=op(op(op(bits(.5),accel,'*'),step,'*'),step,'*');position=op(read(m,ACTOR+0x38),op(linear,quadratic,'+'),'+');put(m,ACTOR+0x38,position)
    late_step=read(m,clock);new_velocity=op(velocity,op(accel,late_step,'*'),'+');put(m,ACTOR+0x50,new_velocity)
    return m,int(not(floating(read(m,ACTOR+0x2C))<10. or floating(read(m,ACTOR+0x30))<10.))
def update_effect(m,c):
    if c.mutation&1:put(m,ACTOR+0x2C,bits(1.0))
    if c.mutation&2:put(m,ACTOR+0x38,bits(300.0))
    if c.mutation&4:put(m,ACTOR+0x1C,0xFFFF,2)
def parent_reference(initial,c):
    m=dict(initial);calls=[]
    if not read(m,ACTOR+0x10)&1:return m,calls
    expired=False
    if read(m,ACTOR+0x58)&1:
        put(m,ACTOR+0x1C,(half(read(m,ACTOR+0x1C,2))-read(m,source.TICKS))&65535,2);expired=half(read(m,ACTOR+0x1C,2))<0
    if c.update:calls.append((UPDATE,(ACTOR,)));update_effect(m,c);expired|=not c.update_result
    if c.invoke:calls.append((source.ENTRY,(ACTOR,)));m,result=reference(m,c);expired|=not result
    flags=read(m,ACTOR+0x58);life=half(read(m,ACTOR+0x1C,2));cutoff=half(read(m,ACTOR+0x6C,2));product=signed((life*half(read(m,ACTOR+0x6E,2)))&0xFFFFFFFF)
    if not expired and life<cutoff:
        if flags&0x08000000 and product<m[ACTOR+0x5C]:m[ACTOR+0x5C]=product&255
        if flags&0x10000000 and product<m[ACTOR+0x5C]:m[ACTOR+0x2B]=product&255
    if expired and c.post:calls.append((POST,(ACTOR,)));expired=not c.post_result
    if expired:calls.append((FREE,(ACTOR,)));put(m,ACTOR+0x10,0)
    return m,calls

class MotionOracle(RayOracle):
    def __init__(self,words,memory,c=Case(),entry=source.ENTRY,connected=None):
        TimingOracle.__init__(self,words,memory,phase=c.phase,entry=entry,arguments=(ACTOR,),connected=connected)
        self.case,self.trace=c,[]
    def get(self,address,size):
        v=super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,v))
        return v
    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))
    def record_call(self,target):
        assert target in(source.ENTRY,UPDATE,POST,FREE),hex(target);a=self.arguments(1);self.calls.append((target,a));self.events.append(('CALL',target,a))
    def hook(self,target):
        c=self.case
        if target==UPDATE:update_effect(self.memory,c);result=c.update_result
        elif target==POST:result=c.post_result
        else:assert target==FREE;put(self.memory,ACTOR+0x10,0);result=0xDEAD0001
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result;self.hi,self.lo=0xA5000010,0xA5000011

def controls():
    b=source.SELECTED;velocity='    *(f32 *)(actor + 0x50) += *(f32 *)(actor + 0x4C) * D_800BE9A4;';early=b.replace(velocity+chr(10),'').replace('    *(f32 *)(actor + 0x38) +=',velocity+chr(10)+'    *(f32 *)(actor + 0x38) +=')
    regrouped=b.replace('*(f32 *)(actor + 0x50) * D_800BE9A4 +\n        0.5f * *(f32 *)(actor + 0x4C) * D_800BE9A4 * D_800BE9A4','*(f32 *)(actor + 0x50) * D_800BE9A4;\n    *(f32 *)(actor + 0x38) += 0.5f * *(f32 *)(actor + 0x4C) * D_800BE9A4 * D_800BE9A4')
    return dict(wrong_damping=b.replace('0x150','0x144'),wrong_half=b.replace('0.5f','1.0f'),linear_acceleration=b.replace('* D_800BE9A4 * D_800BE9A4','* D_800BE9A4'),wrong_size=b.replace('< 10.0f','< 9.0f'),wrong_acceleration=b.replace('actor + 0x4C','actor + 0x48'),cached_clock=b.replace('    *(f32 *)(actor + 0x2C) -=','    f32 captured = D_800BE9A4;\n    *(f32 *)(actor + 0x2C) -=').replace('* D_800BE9A4','* captured'),advanced_velocity_position=early,positive_conjunction=b[:b.index('    if (')]+'''    return *(f32 *)(actor + 0x2C) >= 10.0f && *(f32 *)(actor + 0x30) >= 10.0f;
}''',factored_damping=b.replace('*(f32 *)(actor + 0x2C) -= *(f32 *)(actor + 0x2C) * *(f32 *)(actor + 0x150);','*(f32 *)(actor + 0x2C) *= 1.0f - *(f32 *)(actor + 0x150);'),regrouped_position=regrouped,false_return=b.replace('return 1;','return 0;'),spurious_height_limit=b.replace('    if (','    if (*(f32 *)(actor + 0x15C) < *(f32 *)(actor + 0x38)) return 0;\n    if (',1))

def native_harness():
    t=source.HEADERS+r'''
static f32 clockValue,*clockPointer;
#define D_800BE9A4 (*clockPointer)
static union{f32 v[128];u8 bytes[512];}actual,expected;
static f32 real(u32 b){union{f32 f;u32 b;}x;x.b=b;return x.f;}
static u32 word(f32 f){union{f32 f;u32 b;}x;x.f=f;return x.b;}
static int nanword(u32 w){return(w&0x7F800000u)==0x7F800000u&&(w&0x7FFFFFu)!=0;}
typedef char ABI[(sizeof(void*)==4&&sizeof(f32)==4&&sizeof(s32)==4)?1:-1];
'''
    for name,b in dict(selected=source.SELECTED,**controls()).items():t+=b.replace('s32 '+source.FUNCTION,'static s32 '+name)+chr(10)
    t+=r'''
typedef s32(*Update)(u8*);
static int check(Update fn){const u32 fp[]={FLOATS};const u32 initial[]={DEFAULT};const u32 fields[]={11,12,84,19,20,14,87};u32 n,layout,i,seed=0x12345678u,input[8],got,want;f32 *p,*q,*expectedClock,oldVelocity,accel,firstStep,linear,quadratic,sum,pos,product,difference;int result;
 for(n=0;n<2048;n++)for(layout=0;layout<89;layout++){
  for(i=0;i<512;i++)actual.bytes[i]=(u8)(i*13+0x59);p=actual.v+4;
  for(i=0;i<8;i++){seed=seed*1664525u+1013904223u;input[i]=n<160?(i==n/20?fp[n%20]:initial[i]):fp[(seed>>24)%20];}
  if(n==160){for(i=0;i<8;i++)input[i]=initial[i];input[3]=0x40C00000u;input[4]=0xE0AD78ECu;input[5]=0x60AD78ECu;}
  if(n==161){for(i=0;i<8;i++)input[i]=initial[i];input[0]=0x411FFFFFu;input[2]=0;}
  for(i=0;i<7;i++)p[fields[i]]=real(input[i]);clockValue=real(input[7]);clockPointer=layout<88?p+layout:&clockValue;*clockPointer=clockValue;
  for(i=0;i<512;i++)expected.bytes[i]=actual.bytes[i];q=expected.v+4;expectedClock=layout<88?q+layout:&clockValue;
  oldVelocity=q[20];accel=q[19];product=q[11]*q[84];difference=q[11]-product;q[11]=difference;product=q[12]*q[84];difference=q[12]-product;q[12]=difference;
  firstStep=*expectedClock;linear=oldVelocity*firstStep;quadratic=0.5f*accel;quadratic=quadratic*firstStep;quadratic=quadratic*firstStep;sum=linear+quadratic;pos=q[14]+sum;q[14]=pos;product=accel**expectedClock;q[20]=oldVelocity+product;
  want=!(q[11]<10.0f||q[12]<10.0f);result=fn((u8*)p);if(result!=(s32)want)return 1;
  for(i=0;i<128;i++){got=word(actual.v[i]);want=word(expected.v[i]);if(got!=want&&!((i==15||i==16||i==18||i==24)&&nanword(got)&&nanword(want)))return 1;}
 }
 return 0;
}
static int run(void){if(check(selected))return 10;
'''.replace('FLOATS',','.join('0x%Xu'%v for v in FLOATS)).replace('DEFAULT',','.join('0x%Xu'%v for v in(*DEFAULT,bits(1.0))))
    for i,name in enumerate(controls()):t+='if(!check('+name+'))return '+str(20+i)+';'+chr(10)
    return t+'return 0;}'+chr(10)+START

class BallisticBillboardGateTests(unittest.TestCase):
    receipt={}
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);source.verify_prepared(cls.out);cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE];cls.fresh=cls.out/('canonical-run-'+str(os.getpid()));cls.fresh.mkdir(exist_ok=False);cls.rom=cls.values['conker/conker.us.bin'];cls.truth=list(struct.unpack_from('>48I',cls.rom,source.ROM));local=cls.fresh/'qualified-padded.o';local.write_bytes((cls.out/'qualified-padded.o').read_bytes());data,fs=source.link_owner(ROOT,cls.fresh,local,source.OWNER);cls.words=list(struct.unpack_from('>48I',data,fs[source.FUNCTION]['value']))
    @classmethod
    def tearDownClass(cls):(cls.out/('test-receipt-'+str(os.getpid())+'.json')).write_text(json.dumps(cls.receipt,indent=2)+chr(10))
    def linked(self,entry,clock):
        if not hasattr(self,'links'):self.links={}
        key=(entry,clock)
        if key in self.links:return self.links[key]
        pair=[];number=len(self.links)
        for j,obj in enumerate((self.out/('original-'+source.FUNCTION+'.o'),self.out/'selected.o')):
            p=self.fresh/('layout-%d-%d.ld'%(number,j));elf=p.with_suffix('.elf');p.write_text(('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }'%entry)+chr(10));subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,'--defsym=D_800BE9A4=0x%X'%clock,'-o',str(elf),str(obj)],capture_output=True,check=True);pair.append(list(struct.unpack_from('>48I',sections(elf)['.text'][1])))
        self.assertEqual(*pair);self.links[key]=pair;return pair
    def compare(self,c=Case(),images=None,entry=source.ENTRY,clock=None):
        initial=fixture(c,clock);want,result=reference(initial,c,clock);pair=[]
        for words in images or(self.truth,self.words):
            m=MotionOracle(words,initial,c,entry).run();self.assertEqual((public(m.memory),m.r[2],m.calls),(public(want),result,[]),c);pair.append(m)
        self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);return pair[0]
    def test_01_owner_Make_literal_table_and_callback_ABI(self):
        self.assertEqual(self.words,self.truth)
        for label in('before','after'):
            obj,diag=source.compile_owner(ROOT,self.fresh,(self.out/(label+'-owner.c')).read_text(),'fresh-'+label);self.assertEqual(diag.count('Warning 712:'),1);self.assertIn('func_1514BF50(arg0);',diag);self.assertEqual(source.same_functions(obj,self.out/(label+'-owner.o')),36)
        self.assertEqual(source.same_functions(self.out/'before-owner.o',self.out/'after-owner.o',(source.FUNCTION,)),35);self.assertEqual(source.normalized_pools(self.out/'before-owner.o'),source.normalized_pools(self.out/'after-owner.o'));self.assertEqual(source.same_functions(self.out/'after-owner.o',self.out/'make-shadow/src/game/generated_176A00.c.o.compact'),36)
        self.assertEqual(source.recovered_owner(self.values[source.SOURCE].decode()),(self.out/'proposed-owner.c').read_text());self.assertEqual(len(json.loads((self.out/'Make-commands.json').read_text())),5)
        ws=struct.unpack('>%dI'%(len(self.rom)//4),self.rom);self.assertFalse(any(w in(0x0C000000|(source.ENTRY>>2&0x3FFFFFF),0x08000000|(source.ENTRY>>2&0x3FFFFFF))for w in ws));self.assertEqual([4*i for i,w in enumerate(ws)if w==source.ENTRY],[0x22E890]);table=self.rom[0x22E820:0x22E8D0];self.assertEqual(struct.unpack_from('>I',table,28*4)[0],source.ENTRY)
        old=self.values['conker/build/conker.us.elf'];self.assertEqual(old[source.elf_slot_offset(old,source.TABLE,176):source.elf_slot_offset(old,source.TABLE,176)+176],table)
        if self.installed:source.audit(ROOT,self.out)
        self.receipt['owner']=dict(words=48,frame=0,bindings=2,guards=0,neighbors=35,compact_functions=36,GLOBAL_ASM_routines=1,Make_commands=5,selected_diagnostics=0,unchanged_owner_warnings=1,registered_slot=28,table_entries=44,typed_s32_u8_pointer_callback=True)
    def test_02_float_boundaries_rounding_and_all_clock_aliases(self):
        count=0;visits=set()
        for field,value,phase in itertools.product(range(8),FLOATS,(0,8)):
            values=list(DEFAULT)+[bits(1.0)];values[field]=value;m=self.compare(Case(values=tuple(values[:7]),step=values[7],phase=phase));visits.update(m.visits);count+=1
        for w,h,damping,limit in itertools.product((0x411FFFFF,0x41200000,0x41200001,bits(20.0),0x7FC00001),(0x411FFFFF,0x41200000,bits(20.0),0xFFC12345),(0,bits(.5),bits(1.0)),(0,bits(2.0),bits(200.0),0x7FC12345)):
            self.compare(Case(values=(w,h,damping,bits(2.),bits(1.),0,limit)));count+=1
        for alias,value in itertools.product(range(0,0x160,4),(0,bits(.5),bits(1.),0x7FC00001)):
            c=Case(alias=alias,step=value);self.compare(c,self.linked(source.ENTRY,ACTOR+alias));count+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+192,4)))
        self.receipt['guest']=dict(cases=count,all48_root_words_visited=True,all88_clock_word_aliases=True,rounded_multiply_subtract_and_add=True,position_before_velocity_and_late_global_reload=True,quiet_NaN_infinity_subnormal_signed_zero_and_10_boundaries=True,full_private_state_trace=True,FCSR_EPC_exception_hardware_not_claimed=True)
    def test_03_complete_original_dispatcher_and_return_driven_cleanup(self):
        old=self.values['conker/build/conker.us.elf'];parent=list(struct.unpack_from('>195I',self.rom,0x16A494));assembly=self.values['conker/asm/nonmatchings/game_169510/func_1513CFE4.s'].decode();literal=[int(w,16)for w in re.findall(r'/\*\s*[0-9A-F]+\s+[0-9A-F]+\s+([0-9A-F]{8})\s*\*/',assembly)];self.assertEqual(parent,literal);self.assertEqual(struct.unpack_from('>3I',old,source.elf_slot_offset(old,source.CALLER,12)),(0x00001025,0x03E00008,0));self.assertIn('s32 func_1513CFE4() {\n    return 0;\n}',self.values['conker/src/game_169510.c'].decode());count=0;visits=set()
        for active,flags,life,update,post,result,mutation,size in itertools.product((False,True),(0,1,0x18000000,0x18000001),(-1,1,5),(False,True),(False,True),(0,1),(0,1,2,4),(bits(20.),bits(1.))):
            vals=list(DEFAULT);vals[0]=size;c=Case(values=tuple(vals),active=active,flags=flags,life=life,update=update,post=post,update_result=result,post_result=result,mutation=mutation);initial=fixture(c);want,calls=parent_reference(initial,c);pair=[]
            for target in(self.truth,self.words):
                connected={source.ENTRY+4*i:w for i,w in enumerate(target)};m=MotionOracle(parent,initial,c,entry=source.CALLER,connected=connected).run();self.assertEqual((public(m.memory),m.calls),(public(want),calls),c);visits.update(p for p in m.visits if source.CALLER<=p<source.CALLER+780);pair.append(m)
            self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);count+=1
        self.assertIn(0x1513D090,visits);self.assertIn(0x1513D2D8,visits)
        self.receipt['caller']=dict(mapped_original_dispatcher_words=195,current_dispatcher_is_unchanged_placeholder=True,visited_parent_words=len(visits),cases=count,actual_slot28_indirect_call=True,zero_result_requests_post_callback_or_cleanup=True,timer_and_optional_pre_callback_and_color_paths=True,animation_rate_zero_scope=True,bounded_pre_post_and_release_providers=True,no_complete_animation_provider_or_gameplay_claim=True)
    def test_04_native32_actual_C_aliases_rounding_and_controls(self):
        for opt in('-O0','-O2','-O3'):
            p=self.fresh/('native-'+opt[1:]+'.c');p.write_text(native_harness());binary=p.with_suffix('');q=subprocess.run(native_command(opt)+['-mstackrealign',str(p),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True);p.with_suffix('.diagnostics.txt').write_text(q.stdout+q.stderr);self.assertEqual(q.returncode,0,q.stdout+q.stderr);self.assertEqual(subprocess.run([str(binary)],timeout=45).returncode,0,opt)
        self.receipt['native']=dict(profiles=['O0','O2','O3'],positive_cases_each_profile=2048*89,effective_controls=len(controls()),trapping_UBSan=True,valid_float_storage_and_byte_view=True,all88_clock_aliases_and_disjoint_global=True,complete_storage_fences=True,NaN_results_compared_by_class_not_payload=True,separate_quadratic_rounding_and_unordered_rejection=True,no_FCSR_or_MIPS_NaN_payload_claim=True)
    def test_05_fired_fault_prefixes_and_exact_access_order(self):
        cuts=0
        for value,limit,alias in itertools.product((bits(1.),bits(20.),0x7FC00001),(bits(-1.),bits(200.)),(-1,0x2C,0x50,0x38)):
            vals=list(DEFAULT);vals[0]=value;vals[6]=limit;c=Case(values=tuple(vals),alias=alias);images=self.linked(source.ENTRY,ACTOR+alias)if alias>=0 else(self.truth,self.words);initial=fixture(c);good=self.compare(c,images)
            for cut in range(good.root_accesses):
                pair=[]
                for words in images:
                    m=MotionOracle(words,initial,c);m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                    self.assertEqual(m.root_accesses,cut);pair.append(m)
                self.assertEqual(complete(pair[0]),complete(pair[1]));self.assertEqual(pair[0].trace,pair[1].trace);self.assertEqual((pair[0].current_pc,pair[0].delay_of),(pair[1].current_pc,pair[1].delay_of));cuts+=1
        c=Case();m=self.compare(c);writes=[e for e in m.trace if e[0]=='W'];self.assertEqual([e[1]-ACTOR for e in writes],[0x2C,0x30,0x38,0x50]);self.assertEqual(sum(e[0]=='R'and e[1]==source.TIME for e in m.trace),2)
        sparse={a:b for a,b in fixture(c).items()if not ACTOR+0x15C<=a<ACTOR+0x160}
        for words in(self.truth,self.words):self.assertEqual(MotionOracle(words,sparse,c).run().r[2],1)
        self.receipt['faults']=dict(unused_height_limit_needs_no_mapping=True,fired_prefix_pairs=cuts,full_private_state_trace_PC_delay=True,four_store_order_and_two_live_clock_reads=True)
    def test_06_actual_padder_corruptions_and_independent_GNU_rebases(self):
        raw,rs=source.checked_payload(*source.payload(self.out/'selected.o'));bad=bytearray(raw);bad[100]^=1
        for b,bindings in((raw[:-4],rs),(bytes(bad),rs),(raw,{0:[('R_MIPS_HI16','wrong')],4:rs[4]})):
            with self.assertRaises(ValueError):source.checked_payload(b,bindings)
        p=self.fresh/'padded.s';p.write_text(source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=ROOT/'conker/retail_word_patches.us.csv',filename=source.OWNER));obj=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True);self.assertEqual(obj.read_bytes(),(self.out/'qualified-padded.o').read_bytes());cases=0
        for entry,clock in((source.ENTRY,source.TIME),(0x17007FFC,0x800B7FFC),(0x2500FFFC,0x800C8004)):
            images=self.linked(entry,clock)
            for field in range(8):
                values=list(DEFAULT)+[bits(1.)];values[field]=0x7FC00001;self.compare(Case(values=tuple(values[:7]),step=values[7]),images,entry,clock);cases+=1
        self.receipt['rebases']=dict(layouts=3,guest_cases=cases,two_HI_LO_bindings_and_low_half_carry=True,GNU_original_and_compiled_objects=True,raw_corruption_controls=3,guards=0)
    def test_07_actually_compiled_cached_clock_rejected_by_alias_result(self):
        obj,diag=source.compile_owner(ROOT,self.fresh,source.HEADERS+source.DECLARATIONS+controls()['cached_clock'],'negative-cached-clock');self.assertFalse(diag);p=self.fresh/'negative.ld';elf=p.with_suffix('.elf');p.write_text('SECTIONS { .text 0x1514AF74 : SUBALIGN(4) { *(.text) } }'+chr(10));subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p),'-e',source.FUNCTION,'--defsym=D_800BE9A4=0x22038','-o',str(elf),str(obj)],capture_output=True,check=True);raw=sections(elf)['.text'][1];words=list(struct.unpack('>%dI'%(len(raw)//4),raw));c=Case(alias=0x38);m=MotionOracle(words,fixture(c),c).run();want,_=reference(fixture(c),c);self.assertNotEqual(public(m.memory),public(want));self.assertEqual(read(want,ACTOR+0x50),bits(7.0));self.assertEqual(read(m.memory,ACTOR+0x50),bits(3.0));self.receipt['compiled_control']=dict(actually_compiled_cached_clock_rejected=True,result_failure_not_unmapped_read=True)
    def test_08_strict_entire_image_metadata_and_corruptions(self):
        v=source.check_inputs(ROOT,self.out,self.installed);source.verify_prepared(self.out);before=v['conker/build/conker.us.elf'];truth=v['conker/conker.us.bin'][source.ROM:source.ROM+192];expected=source.predicted_image(before,truth);source.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth);at=source.elf_slot_offset(before,source.ENTRY,192);symbol=next(p for p,n,f,_ in source.symbol_rows(before)if n==source.FUNCTION)+8
        for offset in(20,at,at+100,at+192,source.elf_slot_offset(before,0x80082B20,4),symbol):
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        self.assertEqual(sum(x!=y for x,y in zip(before,expected)),139);self.receipt['image']=dict(changed_bytes=139,code_bytes=138,metadata_bytes=1,other6055_bodies_and6056_addresses_fixed=True,protected_owners=720,protected_bytes=189088,exclusions=0,effective_corruptions=6,guards_shared_headers_and_callback_tables_unchanged=True)
