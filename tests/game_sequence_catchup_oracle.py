"""Independent live-state contract and bounded providers for sequence catch-up."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowBoundary
from tools.experiments import game_sequence_catchup_candidates as candidate
ENTRY=candidate.ENTRY
A,B,C,D,E=0x1501E81C,0x1501E400,0x150242F8,0x1501EC38,0x15020EC4
HELPERS=(A,B,C,D,E)
NAMES=('func_1501E81C','func_1501E400','func_150242F8','func_1501EC38','func_15020EC4')
u32=lambda n:n&0xFFFFFFFF
signed=lambda n:(u32(n)^0x80000000)-0x80000000
@dataclass(frozen=True)
class Case:
    slot:int=0
    active:int=1
    stamp:int=0
    limit:int=0
    flag:int=0
    mode:int=1
    phase:int=0
    result:int=0x81234560
    call_limit:int=48

def symbols():
    return dict(zip(NAMES,HELPERS),D_800C35EA=0x800C35EA,D_800C35B0=0x800C35B0,D_800C3640=0x800C3640,D_800C3C8C=0x800C3C8C)

def address(base,slot,width=4):return u32(base+u32(slot)*width)

def fixture(c=Case(),s=None):
    s=symbols()if s is None else s
    memory={STACK+i:(i*17+165)&255 for i in range(-2048,2048)}
    for name in('D_800C35EA','D_800C35B0','D_800C3640','D_800C3C8C'):
        for i in range(-32,64):memory[u32(s[name]+i)]=(i*13+91)&255
    for slot in range(-2,4):
        put(memory,address(s['D_800C35B0'],slot),0);put(memory,address(s['D_800C3640'],slot),0)
        put(memory,address(s['D_800C35EA'],slot,1),1,1)
    put(memory,address(s['D_800C35B0'],c.slot),c.stamp);put(memory,address(s['D_800C3640'],c.slot),c.limit)
    put(memory,address(s['D_800C35EA'],c.slot,1),c.active,1);put(memory,s['D_800C3C8C'],c.flag,1)
    for at,value,size in((0x800DBFF0,17,4),(0x800C35E8,37,1),(0x800C35E9,91,1),
                           (0x800C3A58,7,1),(0x800C35B8,0x12345678,4),(0x800D23A9,0,1)):
        put(memory,at,value,size)
    return memory

def observation(memory,s):
    return tuple(read(memory,address(s['D_800C35EA'],i,1),1)for i in(0,1))+\
        tuple(read(memory,address(s['D_800C35B0'],i))for i in(0,1))+\
        tuple(read(memory,address(s['D_800C3640'],i))for i in(0,1))+(read(memory,s['D_800C3C8C'],1),)

def public(memory):return{a:b for a,b in memory.items()if not STACK-2048<=a<STACK+2048}

def effect(memory,c,s,t,args,counters):
    kind=next((i for i,n in enumerate(NAMES,1)if s[n]==t),None)
    if kind is None:return
    counters[kind]=counters.get(kind,0)+1
    def active(slot,value):put(memory,address(s['D_800C35EA'],slot,1),value,1)
    def flag(value):put(memory,s['D_800C3C8C'],value,1)
    if kind==1:
        if c.mode==0:active(signed(args[1]),0)
        elif c.mode==2:active(signed(args[1]),2)
        elif c.mode==4:flag(1)
        elif c.mode==7 and counters[1]>=2:active(signed(args[1]),0)
    if kind==2 and c.mode==5:active(0,0)
    if kind==4 and c.mode==5:active(0,1)
    if kind==5:
        if c.mode==1:active(0,0)
        elif c.mode==3:
            put(memory,address(s['D_800C35B0'],0),0x80000000);put(memory,address(s['D_800C3640'],0),0x7FFFFFFF)
        elif c.mode==5:flag(255)
        elif c.mode==6 and counters[5]>=3:active(0,0)
    return

def reference(initial,c=Case(),s=None):
    s=symbols()if s is None else s;m=dict(initial);calls=[];observations=[];counters={};slot=c.slot
    def call(kind,*args):
        t=s[NAMES[kind-1]];args=tuple(map(u32,args));calls.append((t,args));observations.append(observation(m,s))
        effect(m,c,s,t,args,counters)
    for iteration in range(10):
        if read(m,address(s['D_800C35EA'],slot,1),1)!=1:break
        if signed(read(m,address(s['D_800C35B0'],slot)))<signed(read(m,address(s['D_800C3640'],slot))):break
        if read(m,s['D_800C3C8C'],1):put(m,s['D_800C3C8C'],2,1);break
        call(1,0,slot)
        if read(m,address(s['D_800C35EA'],slot,1),1)!=1:break
        call(2,0);slot=0
        call(3,1,0);call(4,0);call(3,0,0);call(5,0)
    else:raise AssertionError('Reference fixture does not terminate')
    return m,calls,observations

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=ENTRY,connected=None,arguments=None):
        self.s=symbols()if s is None else s;self.observations=[];self.counters={};self.prefix=[]
        super().__init__(words,memory,c,entry=entry,s=self.s,connected=connected,arguments=(u32(c.slot),)if arguments is None else arguments)
        self.hi,self.lo,self.condition=0x89ABCDEF,0x76543210,False
    def record_call(self,t):
        if t in(0x15169040,0x1501E1B4):
            self.prefix.append((t,tuple(map(u32,self.arguments(2))),self.r[29]));raise WindowBoundary
        if len(self.calls)>=self.case.call_limit:raise WindowBoundary
        counts=dict(zip((self.s[n]for n in NAMES),(2,1,2,1,1)));counts.update({ENTRY:1,0x15087CC0:0})
        if t not in counts:raise AssertionError(('Unknown sequence provider',hex(t)))
        a=tuple(map(u32,self.arguments(counts[t])));self.calls.append((t,a));self.events.append(('CALL',t,a));self.observations.append(observation(self.memory,self.s))
    def hook(self,t):
        effect(self.memory,self.case,self.s,t,self.calls[-1][1],self.counters)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo,self.condition=0xA5000010,0xA5000011,True;self.r[2]=u32(self.case.result)

def cases():
    pairs=((0,0),(0,1),(1,0),(0x80000000,0x7FFFFFFF),(0x7FFFFFFF,0x80000000),(0xFFFFFFFF,0),(0,0xFFFFFFFF),(0x80000000,0x80000000))
    for slot,active,(stamp,limit),flag,phase in itertools.product((0,1),(0,1,2,255),pairs,(0,1,2,255),(0,8)):
        yield Case(slot,active,stamp,limit,flag,1,phase)
    for slot,mode,phase,result in itertools.product((0,1),range(8),(0,8),(0,0xFFFFFFFF)):
        yield Case(slot=slot,mode=mode,phase=phase,result=result)

def controls():
    b=candidate.SELECTED
    return dict(active=b.replace('D_800C35EA[slot] != 1','D_800C35EA[slot] == 1',1),
        signed=b.replace('D_800C35B0[slot] < D_800C3640[slot]','(u32)D_800C35B0[slot] < (u32)D_800C3640[slot]'),
        tied=b.replace('D_800C35B0[slot] < D_800C3640[slot]','D_800C35B0[slot] <= D_800C3640[slot]'),
        flag=b.replace('D_800C3C8C == 0','D_800C3C8C != 0'),
        flag_store=b.replace('D_800C3C8C = 2','D_800C3C8C = 1'),
        postcheck=b.replace('            if (D_800C35EA[slot] != 1) break;\n',''),
        reset=b.replace('slot = 0','slot = 1'),
        current=b.replace('func_1501E81C(0, slot)','func_1501E81C(0, 0)'),
        phase=b.replace('func_150242F8(1, 0)','func_150242F8(2, 0)'),
        order=b.replace('func_150242F8(1, 0);\n            func_1501EC38(0);','func_1501EC38(0);\n            func_150242F8(1, 0);'),
        final=b.replace('            func_15020EC4(0);',''))

def packet_hash(calls,observations,s):
    result=2166136261
    for(t,args),observed in zip(calls,observations):
        kind=next(i for i,n in enumerate(NAMES,1)if s[n]==t)
        for word in(kind,len(args),*args,*observed):result=u32((result^word)*16777619)
    return result

def native_source(body):
    rows=[];s=symbols()
    for c in cases():
        if c.phase:continue
        initial=fixture(c);after,calls,observations=reference(initial,c)
        before=observation(initial,s);answer=observation(after,s)
        encode=lambda values:','.join('0x%Xu'%u32(v)for v in values)
        rows.append('{'+encode((c.slot,c.mode))+',{'+encode(before)+'},{'+encode(answer)+'},'+encode((len(calls),packet_hash(calls,observations,s)))+'}')
    return '''typedef unsigned int u32;typedef int s32;typedef unsigned char u8;
u8 D_800C35EA[2],D_800C3C8C; s32 D_800C35B0[2],D_800C3640[2];
static u32 hash,calls,counters[6],mode;
static void quit(u32 status){__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
static void mix(u32 v){hash=(hash^v)*16777619u;}
static void provider(u32 kind,u32 argc,u32 a,u32 b){
if(calls++>=48)quit(1);mix(kind);mix(argc);if(argc)mix(a);if(argc==2)mix(b);
mix(D_800C35EA[0]);mix(D_800C35EA[1]);mix((u32)D_800C35B0[0]);mix((u32)D_800C35B0[1]);mix((u32)D_800C3640[0]);mix((u32)D_800C3640[1]);mix(D_800C3C8C);
counters[kind]++;
if(kind==1){if(mode==0)D_800C35EA[b]=0;else if(mode==2)D_800C35EA[b]=2;else if(mode==4)D_800C3C8C=1;else if(mode==7&&counters[1]>=2)D_800C35EA[b]=0;}
if(kind==2&&mode==5)D_800C35EA[0]=0;if(kind==4&&mode==5)D_800C35EA[0]=1;
if(kind==5){if(mode==1)D_800C35EA[0]=0;else if(mode==3){D_800C35B0[0]=(s32)0x80000000u;D_800C3640[0]=0x7FFFFFFF;}else if(mode==5)D_800C3C8C=255;else if(mode==6&&counters[5]>=3)D_800C35EA[0]=0;}
}
s32 func_1501E81C(s32 a,s32 b){provider(1,2,a,b);return (s32)0x81234560u;}
s32 func_1501E400(s32 a){provider(2,1,a,0);return 0;}
s32 func_150242F8(s32 a,s32 b){provider(3,2,a,b);return -1;}
s32 func_1501EC38(s32 a){provider(4,1,a,0);return 17;}
s32 func_15020EC4(s32 a){provider(5,1,a,0);return 0;}
'''+body+'''
typedef struct {u32 slot,mode,before[7],after[7],calls,hash;} Row;
static const Row rows[]={'''+',\n'.join(rows)+'''};
void _start(void){u32 i,j,typed;void(*call)(s32)=func_1501E2F8;
if(sizeof(void*)!=4)quit(9);
for(typed=0;typed<2;typed++)for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
const Row*r=&rows[i];D_800C35EA[0]=r->before[0];D_800C35EA[1]=r->before[1];D_800C35B0[0]=(s32)r->before[2];D_800C35B0[1]=(s32)r->before[3];D_800C3640[0]=(s32)r->before[4];D_800C3640[1]=(s32)r->before[5];D_800C3C8C=r->before[6];
mode=r->mode;calls=0;hash=2166136261u;for(j=0;j<6;j++)counters[j]=0;
if(typed)call((s32)r->slot);else func_1501E2F8((s32)r->slot);
if(D_800C35EA[0]!=r->after[0]||D_800C35EA[1]!=r->after[1]||(u32)D_800C35B0[0]!=r->after[2]||(u32)D_800C35B0[1]!=r->after[3]||(u32)D_800C3640[0]!=r->after[4]||(u32)D_800C3640[1]!=r->after[5]||D_800C3C8C!=r->after[6]||calls!=r->calls||hash!=r->hash)quit(1);
}quit(0);}
'''
