"""Independent sparse-packet model, exact guest state and native32 providers."""
from dataclasses import dataclass,replace
import itertools,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

ENTRY,FACTORY,COPY,ALLOCATE,NEXT=0x151BD2F8,0x15134DAC,0x10022EC0,0x15167A68,0x151B9F00
OWNER,OUTPUT=0x30000,0x50000
u32=lambda n:n&0xFFFFFFFF
PAYLOADS=(0,0x80000000,1,0x807FFFFF,0x3F800000,0xBF800000,0x7F7FFFFF,
          0x7F800000,0xFF800000,0x7FC12345,0xFFC54321,0x7FA12345)
@dataclass(frozen=True)
class Case:
    owner:int=OWNER
    identity:int=0x87
    outcomes:int=3
    mutation:int=0
    phase:int=0
    seed:int=0
    payload:int=0x3E50E561
    first:int=0x80000000
    second:int=0x7FC12345
    arg1:int=0x123400FF
    arg2:int=0x87650001
    alias:int=0

def symbols(index=0):
    return dict(D_800AA850=(0x800AA850,0x02337FFC,0x0343FFFC)[index],
                func_15134DAC=(FACTORY,0x17F08000,0x1EF0FFFC)[index],
                memcpy=(COPY,0x17017FFC,0x1E008000)[index])
def arguments(c):return tuple(map(u32,(c.owner,c.arg1,c.arg2)))
def data(m,p,n):return bytes(m[u32(p+i)]for i in range(n))
def fixture(c=Case(),s=None):
    s=symbols()if s is None else s
    m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-1024,1024)}
    for base,n in((OWNER-64,256),(OUTPUT-64,768),(s['D_800AA850']-16,64)):
        for i in range(n):m.setdefault(base+i,(i*29+c.seed*11+0x5A)&255)
    if c.owner:m[c.owner+0x3B]=c.identity&255
    put(m,s['D_800AA850'],c.payload)
    return m
def destination(c,index,home):
    if not(c.outcomes>>index&1):return 0
    # Aliases are guest address-model cases; native providers use backed objects.
    if c.alias==1:return OUTPUT
    if c.alias in(2,3,4,5):return home-0x60+{2:0x30,3:0x3C,4:0x20,5:0x25}[c.alias]-0x80
    if c.alias==6:return c.owner+0x3B-0x80
    return OUTPUT+index*0x100
def mutate_factory(m,c,s,packet,index,home):
    if index==0 and c.mutation&1:
        put(m,packet+0x0C,c.first);put(m,packet+0x18,c.second)
    if c.mutation&2:
        m[c.owner+0x3B]^=0x55;put(m,s['D_800AA850'],0xBF123456)
    if c.mutation&4:
        for i in range(3):put(m,home+4*i,0xC5000000+i+index*0x100)
def mutate_copy(m,c,packet,source,size):
    if c.mutation&8 and size==2:
        put(m,source,0x12A5,2)
        put(m,packet+0x0C,0x80000001);put(m,packet+0x18,0xFF800000)
def argument_homes(m,sp):
    for i in range(4):put(m,sp+4*i,0xB5000000+i)

def reference(initial,c=Case(),s=None,home=None,connected=False):
    """Independent widths, ordered construction and live post-provider reloads."""
    s=symbols()if s is None else s;m=dict(initial)
    home=STACK+c.phase if home is None else home;sp=home-0x60;packet=sp+0x24
    calls=[];observations=[]
    # The full-word argument homes are written before testing the owner.
    put(m,home+8,c.arg2);put(m,sp+0x14,0xDEAD0000);put(m,home,c.owner);put(m,home+4,c.arg1)
    if not c.owner:return m,calls,observations
    tag=m[c.owner+0x3B]
    put(m,sp+0x30,0x41F80000);coefficient=read(m,s['D_800AA850'])
    for off,value,size in((0x28,c.owner,4),(0x2C,1,1),(0x48,0,1),(0x4A,50,2),
                          (0x4C,100,2),(0x4E,300,2),(0x52,4,1),(0x53,4,1),
                          (0x54,3,1),(0x5C,5,1),(0x5D,255,1),(0x20,0,2),(0x24,tag,1),
                          (0x34,0xC2080000,4),(0x38,0xC2EA0000,4),(0x3C,0x420C0000,4),
                          (0x40,0xC1C00000,4),(0x44,0xC3360000,4),(0x58,coefficient,4)):
        put(m,sp+off,value,size)
    for index in range(2):
        calls.append((s['func_15134DAC'],(packet,2)))
        observations.append((index,packet,data(m,packet,60)))
        result=destination(c,index,home)
        mutate_factory(m,c,s,packet,index,home)
        if connected:
            calls.append((ALLOCATE,(0x29,0,0x82,1,255,1)))
            if result:
                calls.append((s['memcpy'],(result+0x18,packet,60)))
                raw=data(m,packet,60)
                for i,b in enumerate(raw):m[result+0x18+i]=b
                half=read(m,packet+0x28,2);put(m,result+0x10,1);put(m,result+0x54,-half,2)
                put(m,result+0x14,0)
                for at in(0x70,0x74,0x78):put(m,result+at,0)
        argument_homes(m,sp)
        if result:
            calls.append((s['memcpy'],(u32(result+0x80),sp+0x20,2)))
            raw=data(m,sp+0x20,2)
            for i,b in enumerate(raw):m[u32(result+0x80+i)]=b
            mutate_copy(m,c,packet,sp+0x20,2);argument_homes(m,sp)
        if index==0:
            left,right=read(m,sp+0x30),read(m,sp+0x3C)
            put(m,sp+0x30,left^0x80000000);put(m,sp+0x3C,right^0x80000000)
    return m,calls,observations

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,s=None,connected=None,args=None):
        super().__init__(words,memory,c,entry=entry,s=symbols()if s is None else s,
                         connected=connected,arguments=arguments(c)if args is None else args)
        self.f=[u32(c.seed*0x9E3779B9+i*0x1020304)for i in range(32)];self.saved_f=self.f[20:]
        self.before=self.r[:];self.before_f=self.f[:];self.factory_count=0;self.allocate_count=0
        self.packet_observations=[];self.following=[]
    def execute(self,word):
        if word>>26==17 and word>>21&31==16 and word&63==7:
            self.dispatched_word=word;self.f[word>>6&31]=self.f[word>>11&31]^0x80000000
        else:super().execute(word)
    def record_call(self,t):
        s=self.syms
        if t==ENTRY:
            self.target_home=self.r[29];a=self.arguments(3)
        elif t==s['func_15134DAC']:
            a=self.arguments(2);index=self.factory_count;self.factory_count+=1
            self.packet_observations.append((index,a[0],data(self.memory,a[0],60)))
        elif t==s['memcpy']:a=self.arguments(3)
        elif t==ALLOCATE:a=self.arguments(6)
        else:assert t==NEXT,hex(t);a=self.arguments(3);self.following.append((a,data(self.memory,OUTPUT,0x200)))
        a=tuple(map(u32,a));self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        c,s=self.case,self.syms;a=self.calls[-1][1];packet=self.target_home-0x3C
        if t in(s['func_15134DAC'],ALLOCATE):
            index=self.factory_count-1 if t==s['func_15134DAC']else self.allocate_count
            if t==ALLOCATE:self.allocate_count+=1;assert a==(0x29,0,0x82,1,255,1),a
            mutate_factory(self.memory,c,s,packet,index,self.target_home)
            value=destination(c,index,self.target_home)
        elif t==s['memcpy']:
            assert a[2]in(2,60),(t,a)
            raw=data(self.memory,a[1],a[2])
            for i,b in enumerate(raw):self.memory[u32(a[0]+i)]=b
            mutate_copy(self.memory,c,packet,a[1],a[2]);value=a[0]
        else:
            assert t==NEXT;self.memory[OUTPUT+3]^=0xA5;value=0xBADF00D
        argument_homes(self.memory,self.r[29])
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo,self.condition=0x87654321,0x12345678,True;self.r[2]=u32(value)

def literal(m):
    return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses,m.packet_observations,m.following)
def original_object(core,q,out):
    text=(out/'frozen/conker/asm/1E73B0.s').read_text();a=text.index('glabel '+core.FUNCTION);b=text.index('endlabel '+core.FUNCTION,a)+len('endlabel '+core.FUNCTION)
    p=out/'original-reference.s';p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.text\n'+text[a:b]+'\n.size '+core.FUNCTION+',.-'+core.FUNCTION+'\n')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I','conker/include','-o',str(p.with_suffix('.o')),str(p)],cwd=core.ROOT,check=True,capture_output=True)
    q['original'],q['original_refs']=core.function_blob(p.with_suffix('.o'))
def programs(core,q,s=None):
    s=symbols()if s is None else s
    original=list(core.bound_blob(q['original'],q['original_refs'],s))
    candidate=list(core.bound_blob(q['normal'],q['normal_refs'],s))
    assert original==candidate
    return original,candidate
def cases():
    return tuple(Case(owner=owner,identity=tag,outcomes=outcome,mutation=mode,phase=8 if mode&1 else 0,
                      seed=(mode+tag)%8,payload=payload,first=PAYLOADS[(mode+tag)%len(PAYLOADS)],second=PAYLOADS[(mode+outcome+3)%len(PAYLOADS)])
                 for owner,tag,outcome,mode,payload in itertools.product((0,OWNER),(0,0x80,255),range(4),range(16),PAYLOADS[::3]))
def guest(core,q):
    original_object(core,q,core.ROOT/core.BUILD);count=0;seen=set();rows=[(c,symbols(),ENTRY)for c in cases()]
    for i in(1,2):rows.extend((Case(outcomes=v,mutation=15,payload=p),symbols(i),0x17007FFC if i==1 else 0x1F00FFFC)for v,p in itertools.product(range(4),PAYLOADS))
    for c,s,entry in rows:
        initial=fixture(c,s);expected,calls,observations=reference(initial,c,s)
        models=[Oracle(body,initial,c,entry=entry,s=s).run()for body in programs(core,q,s)]
        for m in models:
            assert(m.memory,m.calls,m.packet_observations)==(expected,calls,observations),(c,s)
            assert m.r[16:24]==m.before[16:24]and m.r[28:32]==m.before[28:32]
            assert m.f[20:]==m.before_f[20:]
        assert literal(models[0])==literal(models[1]);seen.update(pc-entry for pc in models[0].visits);count+=1
    assert seen==set(range(0,308,4)),sorted(set(range(0,308,4))-seen)
    aliases=0
    for alias,outcome,mode,phase in itertools.product(range(1,7),range(4),(0,1,8,15),(0,8)):
        c=Case(alias=alias,outcomes=outcome,mutation=mode,phase=phase)
        initial=fixture(c);expected,calls,obs=reference(initial,c)
        models=[Oracle(body,initial,c).run()for body in programs(core,q)]
        for m in models:assert(m.memory,m.calls,m.packet_observations)==(expected,calls,obs),(c,'alias')
        assert literal(models[0])==literal(models[1]);aliases+=1
    for source in(0x20,0x30,0x68):
        c=Case(owner=STACK-0x60+source-0x3B,mutation=0,outcomes=3)
        initial=fixture(c);expected,calls,obs=reference(initial,c)
        models=[Oracle(body,initial,c).run()for body in programs(core,q)]
        assert all((m.memory,m.calls,m.packet_observations)==(expected,calls,obs)for m in models)
        assert literal(models[0])==literal(models[1]);aliases+=1
    cuts=0
    for c in(Case(owner=0),Case(outcomes=0),Case(outcomes=1,mutation=15),Case(outcomes=2,mutation=8),Case(outcomes=3,alias=2,mutation=1)):
        initial=fixture(c);ps=programs(core,q);full=Oracle(ps[0],initial,c).run()
        for cut in range(full.all_accesses):
            models=[]
            for p in ps:
                m=Oracle(p,initial,c);m.cut=cut
                try:m.run();raise AssertionError(('Unfired cut',cut))
                except AccessBoundary:pass
                models.append(m)
            assert literal(models[0])==literal(models[1]);cuts+=1
    return dict(cases=count,code_global_helper_layouts=3,all77_words_reached=True,alias_cases=aliases,
                fault_prefix_cuts=cuts,literal_full_state=True,independent_complete_memory=True,exact_padding_and_incoming_homes=True,
                synthetic_frame_aliases_guest_only=True,FP_payload_negation_is_bitwise=True,FCSR_exception_equivalence_not_claimed=True)

def helper_code(rom):
    result={}
    for entry,offset,n in((FACTORY,0x16225C,39),(COPY,0x22EC0,11)):
        result.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
    return result
def connections(core,q):
    rom=(core.ROOT/'conker/conker.us.bin').read_bytes();checks=0;helpers=helper_code(rom)
    for c in(Case(owner=owner,outcomes=outcome,mutation=mode,phase=phase)
             for owner,outcome,mode,phase in itertools.product((0,OWNER),range(4),(0,1,2,4),(0,8))):
        initial=fixture(c);wanted,calls,obs=reference(initial,c,connected=True);models=[]
        for body in programs(core,q):
            m=Oracle(body,initial,c,connected=helpers).run()
            # Literal helper stack scratch is compared between original and C;
            # the independent reference compares complete non-stack effects.
            public=lambda mem:{a:v for a,v in mem.items()if not STACK-1024<=a<STACK+1024}
            assert(public(m.memory),m.calls,m.packet_observations)==(public(wanted),calls,obs),(c,'helpers')
            models.append(m)
        assert literal(models[0])==literal(models[1]);checks+=1
    # Original window sets A1, places A2 in the JAL delay slot, then overwrites
    # all three arguments for the following service before it can observe V0.
    start,end=0x1514F1F0,0x1514F20C
    window=struct.unpack_from('>7I',rom,0x17C6A0)
    assert window==(0x240500FF,0x0D46F4BE,0x24060001,0x02002025,0x240500FF,0x0D46E7C0,0x24060001)
    caller=0
    for c in(Case(owner=owner,outcomes=outcome,mutation=mode,phase=phase,arg1=255,arg2=1)
             for owner,outcome,mode,phase in itertools.product((0,OWNER),range(4),(0,1,8,15),(0,8))):
        initial=fixture(c);wanted,calls,obs=reference(initial,c);models=[]
        # The target's saved RA is the literal return into the caller window.
        put(wanted,STACK+c.phase-0x60+0x14,start+12)
        wanted[OUTPUT+3]^=0xA5;argument_homes(wanted,STACK+c.phase)
        for body in programs(core,q):
            code=dict(zip(range(ENTRY,ENTRY+308,4),body));code[end]=0
            m=Oracle(window,initial,c,entry=start,connected=code,args=(c.owner,0xDEAD0000,0xABCD0000));m.r[16]=c.owner
            m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
            try:m.run();raise AssertionError('Missing caller boundary')
            except WindowBoundary:pass
            assert m.memory==wanted and m.packet_observations==obs,(c,'caller')
            assert m.calls==[(ENTRY,arguments(c)),*calls,(NEXT,(c.owner,255,1))]
            assert m.following and m.following[0][0]==(c.owner,255,1)
            models.append(m)
        assert literal(models[0])==literal(models[1]);caller+=1
    return dict(original_factory_and_memcpy_cases=checks,actual_factory_words=39,actual_memcpy_words=11,
                bounded_allocator_arguments=6,caller_cases=caller,caller_words=7,caller_start=hex(start),
                caller_end=hex(end),delay_slot_arg2=True,following_service_no_target_V0_consumption=True,
                full_parent_and_allocator_not_qualified=True)

def native_text(core,selected=None):
    selected=core.SELECTED if selected is None else selected
    return '#include <ultra64.h>\n#include <string.h>\n'+selected+r'''
static u8 ownerData[128],output[2][256],expectedOutput[2][256];
static u32 payloads[]={0,0x80000000u,1,0x807FFFFFu,0x3F800000u,0xBF800000u,0x7F7FFFFFu,0x7F800000u,0xFF800000u,0x7FC12345u,0xFFC54321u};
static int mode,outcomes,aliasOutput,count,copies,error;
static u32 coefficient,firstMirror,secondMirror;static u16 zeroExpected;
static MirroredEffectPacket *live;
f32 D_800AA850;
static void bytes(void*d,const void*s,unsigned n){u8*a=d;const u8*b=s;unsigned i;for(i=0;i<n;i++)a[i]=b[i];}
static u32 bits(f32 v){u32 r;bytes(&r,&v,4);return r;}
static void assign(f32*p,u32 v){bytes(p,&v,4);}
typedef char Layout[(sizeof(void*)==4&&sizeof(MirroredEffectPacket)==60&&
 __builtin_offsetof(MirroredEffectPacket,parameters)==12&&
 __builtin_offsetof(MirroredEffectPacket,field26)==38&&
 __builtin_offsetof(MirroredEffectPacket,coefficient)==52&&
 __builtin_offsetof(MirroredEffectPacket,field39)==57)?1:-1];
void *func_15134DAC(MirroredEffectPacket*p,s32 flag){
 int index=count++,slot=aliasOutput?0:index;u32 expected[6]={0x41F80000,0xC2080000,0xC2EA0000,0x420C0000,0xC1C00000,0xC3360000};unsigned i;
 if(index>1||flag!=2||p->owner!=ownerData||p->ownerTag!=ownerData[0x3B]||p->enabled!=1||
 p->kind!=0||p->field26!=50||p->field28!=100||p->field2A!=300||p->field2E!=4||p->field2F!=4||p->field30!=3||p->field38!=5||p->field39!=-1||bits(p->coefficient)!=coefficient)error=1;
 if(index){expected[0]=firstMirror^0x80000000u;expected[3]=secondMirror^0x80000000u;if(p!=live)error=1;}
 for(i=0;i<6;i++)if(bits(p->parameters[i])!=expected[i])error=1;
 live=p;
 if(index==0){
  if(mode&1){assign(&p->parameters[0],firstMirror=payloads[(coefficient+3)%11]);assign(&p->parameters[3],secondMirror=payloads[(coefficient+7)%11]);}
  else {firstMirror=expected[0];secondMirror=expected[3];}
 }
 if(mode&2)assign(&D_800AA850,0xBF123456);
 return(outcomes>>index&1)?output[slot]:0;
}
void *memcpy(void*d,const void*s,size_t n){
 int index=count-1,slot=aliasOutput?0:index;u16 observed;
 if(n!=2||d!=output[slot]+128||!live)error=1;
 bytes(&observed,s,2);if(observed!=zeroExpected)error=1;
 bytes(d,s,n);bytes(expectedOutput[slot]+128,&zeroExpected,2);copies++;
 if(mode&8){u16 changed=0x12A5;bytes((void*)s,&changed,2);zeroExpected=changed;
  assign(&live->parameters[0],firstMirror=0x80000001);assign(&live->parameters[3],secondMirror=0xFF800000);}
 return d;
}
static int run(void){
 unsigned present,tag,out,md,pl,al,i,j;int cases=0;
 for(present=0;present<2;present++)for(tag=0;tag<3;tag++)for(out=0;out<4;out++)for(md=0;md<16;md++)for(pl=0;pl<11;pl++)for(al=0;al<2;al++){
  for(i=0;i<128;i++)ownerData[i]=(u8)(i*17+0xA5);ownerData[0x3B]=(u8)(tag==0?0:tag==1?128:255);
  for(i=0;i<2;i++)for(j=0;j<256;j++)output[i][j]=expectedOutput[i][j]=(u8)(i*29+j*31+0x5A);
  coefficient=payloads[pl];assign(&D_800AA850,coefficient);mode=md;outcomes=out;aliasOutput=al;
  count=copies=error=0;zeroExpected=0;live=0;
  func_151BD2F8(present?ownerData:0,(s32)0x800000FFu,(s32)0xFFFF0001u);
  if(error||count!=(present?2:0)||copies!=(int)(present?((out&1)+((out>>1)&1)):0))return 1;
  for(i=0;i<2;i++)for(j=0;j<256;j++)if(output[i][j]!=expectedOutput[i][j])return 2;
  cases++;
 }
 return cases==8448?0:3;
}
'''+START
def controls(core):
    s=core.SELECTED
    rows={
        'stub':s[:s.index('/* Submit')]+ 'void func_151BD2F8(u8 *owner,s32 a,s32 b){}',
        'wrong_tag':s.replace('owner[0x3B]','owner[0x3A]'),
        'wrong_owner':s.replace('packet.owner = owner;','packet.owner = owner + 1;'),
        'wrong_mode':s.replace('func_15134DAC(&packet, 2)','func_15134DAC(&packet, 3)'),
        'wrong_enable':s.replace('packet.enabled = 1;','packet.enabled = 0;'),
        'wrong_half_width':s.replace('packet.field26 = 50;','packet.field26 = 49;'),
        'wrong_tail':s.replace('packet.field39 = -1;','packet.field39 = 0;'),
        'wrong_float':s.replace('packet.parameters[2] = -117.0f;','packet.parameters[2] = -118.0f;'),
        'wrong_coefficient':s.replace('packet.coefficient = D_800AA850;','packet.coefficient = 1.0f;'),
        'wrong_zero':s.replace('zero[0] = 0;','zero[0] = 1;'),
        'wrong_copy_size':s.replace('zero, 2);','zero, 1);'),
        'wrong_copy_offset':s.replace('result + 0x80','result + 0x7F'),
        'cached_first':s.replace('-packet.parameters[0]','-31.0f'),
        'cached_second':s.replace('-packet.parameters[3]','-35.0f'),
        'missing_mirror':s.replace('packet.parameters[0] = -packet.parameters[0];','packet.parameters[0] = packet.parameters[0];'),
        'missing_second':s.replace('        result = func_15134DAC(&packet, 2);\n        if (result != 0) {\n            memcpy(result + 0x80, zero, 2);\n        }\n    }','    }'),
    }
    assert all(v!=s for v in rows.values())
    return rows
def native(core,out):
    rows=[('valid-'+opt[1:],None,opt,True)for opt in('-O0','-O2','-O3')]
    rows +=[(name,body,'-O2',False)for name,body in controls(core).items()]
    result=[]
    for name,body,opt,valid in rows:
        p=out/('native-'+name);p.with_suffix('.c').write_text(native_text(core,body))
        compile=subprocess.run([*native_command(opt),'-mstackrealign',str(p.with_suffix('.c')),'-o',str(p)],cwd=core.ROOT,capture_output=True,text=True)
        if compile.returncode or compile.stdout or compile.stderr:raise AssertionError((name,compile.stdout,compile.stderr))
        run=subprocess.run([str(p)],capture_output=True,text=True,timeout=30)
        assert not run.stdout and not run.stderr and((run.returncode==0)==valid),(name,run.returncode,run.stdout,run.stderr)
        result.append(dict(name=name,opt=opt,exit=run.returncode,valid=valid))
    return dict(cases_per_profile=8448,profiles=['O0','O2','O3'],trapping_UBSan=True,effective_controls=len(controls(core)),records=result,
                native_distinct_objects_or_same_backed_output=True,padding_not_read_as_C_values=True)
