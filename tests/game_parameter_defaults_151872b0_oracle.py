"""Ordered word/byte/FP parameter stores and original initializer caller."""
from dataclasses import dataclass,replace
import itertools,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ENTRY,NEXT,LAST=0x151872B0,0x15178EB0,0x15012FE0
OFFSETS=(0x1C,0x20,0x24,0x30,0x34,0x38,0x3C,0x40,0x41)
NAMES=tuple('D_800DE%03X'%n for n in OFFSETS)
SIZES=(4,4,4,4,4,4,4,1,1)
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
    variant:int=0
    seed:int=0
    phase:int=0
def symbols(index=0):
    base=(0x800DE000,0x02337FE0,0x0343FFE0)[index]
    return{n:base+off for n,off in zip(NAMES,OFFSETS)}
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s;m={STACK+i:(i*17+c.seed*23+0xA5)&255 for i in range(-256,256)}
    for address in s.values():
        for i in range(-16,24):m.setdefault(address+i,(i*31+c.seed*13+0x5A)&255)
    return m
def observe(m,s):return tuple(read(m,s[n],size)for n,size in zip(NAMES,SIZES))
def reference(initial,c=Case(),s=None):
    s=symbols()if s is None else s;m=dict(initial);stores=[]
    def write(index,value):
        address=s[NAMES[index]];size=SIZES[index];put(m,address,u32(value),size);stores.append((address,size,u32(value)&((1<<(8*size))-1)))
    for index,value in enumerate((600,180,90,1016,0,1,0x3F800000,1,1)):write(index,value)
    variant=u32(c.variant)
    if variant==0x21:
        for index,value in((0,4800),(1,4799),(2,4798),(3,1010),(4,1),(5,4),(7,0)):write(index,value)
    elif variant==0x22:
        for index,value in((0,2400),(1,2399),(2,2398),(5,4),(7,0)):write(index,value)
    elif variant==0x14:write(8,0)
    elif variant==0x29:
        for index,value in((0,1200),(1,600),(2,300)):write(index,value)
    return m,stores
def cases():
    variants=[*range(-2,256),0x10014,0x10021,0xFFFFFF21,0x80000014,0x80000021,0xFFFFFFFF,0x7FFFFFFF]
    return tuple(Case(v,seed,8 if seed&1 else 0)for v,seed in itertools.product(variants,range(8)))
def aliases():
    rows=[];base=symbols();rows.append({n:0x30000 for n in NAMES})
    for i,j in itertools.combinations(range(9),2):
        s=dict(base);s[NAMES[j]]=s[NAMES[i]];rows.append(s)
    for byte,word,offset in itertools.product(NAMES[7:],NAMES[:7],range(4)):
        s=dict(base);s[byte]=s[word]+offset;rows.append(s)
    for name in NAMES:
        s=dict(base);s[name]=STACK+0x18;rows.append(s)
    return rows
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None,s=None,arguments=None):
        super().__init__(words,memory,c,entry=entry,s=symbols()if s is None else s,connected=connected,arguments=(u32(c.variant),)if arguments is None else arguments)
        self.f=[u32(c.seed*0x9E3779B9+i*0x1010101)for i in range(32)];self.before_f=self.f[:];self.saved_f=self.f[20:];self.before=self.r[:];self.observations=[]
    def record_call(self,t):
        if t==ENTRY:self.calls.append((t,(u32(self.r[4]),)))
        else:assert t in(NEXT,LAST),hex(t);self.calls.append((t,()))
    def hook(self,t):
        assert t in(NEXT,LAST),hex(t);self.observations.append((t,observe(self.memory,self.syms)))
        if t==NEXT:put(self.memory,self.syms[NAMES[0]],read(self.memory,self.syms[NAMES[0]])^0x80000001)
        else:self.memory[self.syms[NAMES[8]]]^=0xA5
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0x7FA00000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=0x12345678 if t==NEXT else 0xABCDEF90
def literal(m):return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses)
def original_object(core,q,out):
    p=out/'original-reference.s';p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.text\n'+(out/'retail-function.s').read_text()+'.size '+core.FUNCTION+',.-'+core.FUNCTION+'\n')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I','conker/include','-o',str(p.with_suffix('.o')),str(p)],cwd=core.ROOT,check=True,capture_output=True)
    q['original'],q['original_refs']=core.function_blob(p.with_suffix('.o'))
def programs(core,q,s=None):
    s=symbols()if s is None else s;original=list(core.bound_blob(q['original'],q['original_refs'],s));normal=list(core.bound_blob(q['normal'],q['normal_refs'],s));assert original==normal
    raw=list(core.bound_blob(q['raw'],q['refs'],s));assert raw==normal
    return original,normal,raw
def guest(core,q):
    original_object(core,q,core.ROOT/core.BUILD);count=0;seen=set();rows=[(c,symbols(),ENTRY)for c in cases()]
    for index in(1,2):
        rows.extend((Case(v,seed),symbols(index),0x17007FFC if index==1 else 0x1F00FFFC)for v,seed in itertools.product((0,0x14,0x21,0x22,0x29,0x80000021),(0,7)))
    for c,s,entry in rows:
        initial=fixture(c,s);wanted,stores=reference(initial,c,s);models=[]
        for body in programs(core,q,s)[:2]:
            m=Oracle(body,initial,c,entry=entry,s=s).run();assert(m.memory,m.stores,m.reads)==(wanted,stores,[]),(c,s)
            assert m.r[16:24]==m.before[16:24]and m.r[28:32]==m.before[28:32]and not m.calls
            assert all(m.f[i]==(0x3F800000 if i==4 else m.before_f[i])for i in range(32));models.append(m)
        assert literal(models[0])==literal(models[1]);seen.update(pc-entry for pc in models[0].visits);count+=1
    assert seen==set(range(0,308,4))-{0x118}
    alias_count=0
    for s,c in itertools.product(aliases(),(Case(0),Case(0x14),Case(0x21),Case(0x22),Case(0x29))):
        initial=fixture(c,s);wanted,stores=reference(initial,c,s);models=[Oracle(body,initial,c,s=s).run()for body in programs(core,q,s)[:2]]
        assert all((m.memory,m.stores,m.reads)==(wanted,stores,[])for m in models);assert literal(models[0])==literal(models[1]);alias_count+=1
    cuts=0;cut_rows=[(Case(v),symbols())for v in(0,0x14,0x21,0x22,0x29)]
    cut_rows +=[(Case(v),s)for s in(aliases()[0],aliases()[37],aliases()[-1])for v in(0,0x14,0x21,0x22,0x29)]
    for c,s in cut_rows:
        initial=fixture(c,s);ps=programs(core,q,s)[:2];full=Oracle(ps[0],initial,c,s=s).run()
        for cut in range(full.all_accesses):
            models=[]
            for body in ps:
                m=Oracle(body,initial,c,s=s);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError(('Missing parameter-defaults cut',cut))
                models.append(m)
            assert literal(models[0])==literal(models[1]);cuts+=1
    return dict(cases=count,global_layouts=3,alias_layouts=len(aliases()),alias_cases=alias_count,reachable_words=76,unreachable_preserved_offset=0x118,executed_fault_cuts=cuts,independent_all_memory_and_ordered_store_widths=True,literal_original_C_states_equal=True,exact_FP4_one_payload_and_other_FP_preserved=True,synthetic_aliases_guest_only=True)
class BoundaryCode(WindowCode):
    def __init__(self,code,m,end):super().__init__(code,m);self.m=m;self.end=end;self.ends=()
    def __getitem__(self,pc):
        if pc==self.end:self.m.boundary=pc;raise WindowBoundary
        return super().__getitem__(pc)
class ReferenceCaller(Oracle):
    def hook(self,t):
        if t!=ENTRY:return super().hook(t)
        actual=replace(self.case,variant=u32(self.r[4]));self.memory,_=reference(self.memory,actual,self.syms);self.r[2]=0xF00DBAAD
def connected(core,q):
    rom=(core.ROOT/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>6I',rom,0x3BA2C);count=0
    for variant,seed,phase,alias in itertools.product((0,0x14,0x21,0x22,0x29,0x10021,0x80000021,0xFFFFFFFF),(0,7),(0,8),(0,1)):
        c=Case(variant,seed,phase);s=symbols()
        if alias:s[NAMES[0]]=STACK+phase+0x18
        initial=fixture(c,s);put(initial,STACK+phase+0x18,u32(variant))
        def build(body=None):
            code={0x1500E594:0}
            if body is not None:code.update(zip(range(ENTRY,ENTRY+308,4),body))
            cls=ReferenceCaller if body is None else Oracle;m=cls(window,initial,c,entry=0x1500E57C,s=s,connected=code,arguments=(0xDEAD0042,));m.code=BoundaryCode(m.code,m,0x1500E594);return m
        def run(m):
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing original initializer continuation')
            return m
        wanted=run(build());assert wanted.calls==[(ENTRY,(u32(variant),)),(NEXT,()),(LAST,())]
        assert(wanted.r[29],wanted.r[31])==(STACK+phase,0x1500E594)
        observe_result=lambda m:(m.boundary,m.memory,m.calls,m.observations,m.r,m.f)
        for body in programs(core,q,s):assert observe_result(run(build(body)))==observe_result(wanted),c
        count+=1
    return dict(cases=count,original_window_words=6,original_JAL_delay_argument_reload=True,full_variant_word=True,following_opaque_services_observe_live_globals=True,target_void_result_poisoned=True,caller_home_global_alias=True,service_arity_and_bodies_not_qualified=True,full_parent_not_claimed=True)

def native(core,out):
    body=core.SELECTED
    controls=dict(stub='void func_151872B0(s32 variant){}',
      missing_first_default=body.replace('    D_800DE01C = 600;',''),
      wrong_second_default=body.replace('D_800DE020 = 180;','D_800DE020 = 181;'),
      wrong_third_default=body.replace('D_800DE024 = 90;','D_800DE024 = 91;'),
      wrong_fourth_default=body.replace('D_800DE030 = 1016;','D_800DE030 = 1017;'),
      missing_float=body.replace('D_800DE03C = 1.0f;',''),
      wrong_initial_byte=body.replace('D_800DE040 = 1;','D_800DE040 = 0;'),
      wrong_variant20_byte=body.replace('D_800DE041 = 0;','D_800DE040 = 0;'),
      wrong_variant33_count=body.replace('D_800DE01C = 4800;','D_800DE01C = 4801;'),
      wrong_first_difference=body.replace('D_800DE01C - 1;','D_800DE01C - 2;'),
      wrong_override_count=body.replace('D_800DE038 = 4;','D_800DE038 = 5;'),
      wrong_variant41_count=body.replace('D_800DE020 = 600;','D_800DE020 = 601;'),
      narrowed_variant=body.replace('switch (variant)','switch ((u8)variant)'))
    assert all(b!=body for b in controls.values());rows=[]
    arr=lambda vs:'{'+','.join(str(u32(v))+'u'for v in vs)+'}'
    for c in cases():
        wanted,_=reference(fixture(c),c);rows.append('{%su,%su,%s}'%(u32(c.variant),c.seed,arr(observe(wanted,symbols()))))
    code='#include <ultra64.h>\ns32 '+','.join(NAMES[:6])+';\nf32 '+NAMES[6]+';\nu8 '+','.join(NAMES[7:])+';\nstatic u8 canary[64];\n'
    code+='typedef struct{u32 variant,seed,expected[9];}Case;static const Case cases[]={'+',\n'.join(rows)+'};\n'
    code+='''_Static_assert(sizeof(s32)==4&&sizeof(f32)==4&&sizeof(u8)==1,"field widths");
    static void wr(void*p,u32 x){__builtin_memcpy(p,&x,4);}
    static u32 rd(const void*p){u32 x;__builtin_memcpy(&x,p,4);return x;}
    '''
    for i,b in enumerate([body,*controls.values()]):code+=b.replace('func_151872B0(','candidate_%d('%i)+'\n'
    code+='static void(*candidates[])(s32)={'+','.join('candidate_%d'%i for i in range(len(controls)+1))+'};\n'
    code+='static void*fields[]={'+','.join('&'+n for n in NAMES[:7])+'};\n'
    code+='''static int run(void){u32 n,j,i,bad,killed=0;const Case*c;
    for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];for(j=0;j<sizeof(candidates)/sizeof(candidates[0]);j++){
      for(i=0;i<7;i++)wr(fields[i],0xA5A5A5A5u+c->seed*0x01010101u+i*0x10203u);
      D_800DE040=(u8)(0xA5u+c->seed);D_800DE041=(u8)(0x5Au+c->seed);
      for(i=0;i<sizeof(canary);i++)canary[i]=(u8)(i*17u+c->seed*13u+0xA5u);
      candidates[j]((s32)c->variant);bad=0;for(i=0;i<7;i++)bad|=rd(fields[i])!=c->expected[i];
      bad|=D_800DE040!=c->expected[7]||D_800DE041!=c->expected[8];
      for(i=0;i<sizeof(canary);i++)bad|=canary[i]!=(u8)(i*17u+c->seed*13u+0xA5u);
      if(!j&&bad)return 2;if(j&&bad)killed|=1u<<(j-1);
    }}for(j=0;j<CONTROL_COUNT;j++)if(!(killed&(1u<<j)))return 10+j;return 0;}
    '''.replace('CONTROL_COUNT',str(len(controls)))
    code+=START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');p=out/'defaults-native.c';p.write_text(code)
    for opt in('-O0','-O2','-O3'):
        exe=out/('defaults-native-'+opt[1:]);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=core.ROOT,capture_output=True,text=True)
        assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr
        run=subprocess.run([str(exe)],capture_output=True,timeout=30);assert run.returncode==0,(opt,run.returncode,run.stderr)
    return dict(cases_per_executable=len(rows),profiles=['-O0','-O2','-O3'],trapping_UBSan=True,effective_controls=list(controls),all_nine_field_widths_and_values=True,exact_float_payload=True,background_canaries=True,synthetic_overlapping_globals_and_caller_home_guest_only=True)
