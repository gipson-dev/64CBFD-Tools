"""Independent ordered selector reference with optional actual single-precision sine."""
from dataclasses import dataclass
import math
import struct

from tools.experiments import game_actor_sine_selector_candidates as source
from tools.tests import test_game_route_record_copy_match as core
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests import test_game_trig_match as trig

STACK,put,read=core.STACK,core.put,core.read
ACTORS,CONTEXT,SINE=0x800CC2D0,0x800D23B0,0x15047D60
BANKS=(0x20000,0x22000)
COEFFICIENT=0x8009DA44
CONSTANTS={0x8009DA44:0x443B8000,0x8009DA48:0x455AC000,0x8009DA4C:0x44BB8000,
    0x8009DA50:0xC9742400,0x8009DA54:0xBFC90FDB,0x8009DA58:0x40C90FDB}
SEGMENTS=tuple((b,0x1800) for b in BANKS)+((ACTORS,26*0x32C),(CONTEXT,4),(0x8009DA44,24),
    (0x80085EB0,16),(0x80098D90,20),(0x8002C920,4))


def bits(v):return struct.unpack('>I',struct.pack('>f',v))[0]
def floating(v):return struct.unpack('>f',struct.pack('>I',v))[0]
def f32(v):return floating(bits(v))
def signed(v):return (v&0x7FFFFFFF)-(v&0x80000000)
def public(m):return {a:v for a,v in m.items() if not STACK-0x500<=a<STACK+0x100}


@dataclass(frozen=True)
class Case:
    count:int=4
    slot:int=25
    wide:int=0
    active:int=0xFFFFFFFF
    eligible:int=0xFFFF0000
    states:tuple=()
    points:tuple=()
    mutation:int=0
    answers:tuple=()


def cases():
    for count in (-2147483648,-7,-1,0,1,2,8,16,26):
        for wide in (0,1):yield Case(count=count,wide=wide)
    for active in (0,1,2,3,0x8000,0x10000,0x80000000,0xFFFFFFFF):
        for eligible in (0,0x10000,0x20000,0x80000000,0xFFFF0000):yield Case(count=26,active=active,eligible=eligible)
    for minimum,maximum in ((750.,3500.),(1500.,8000.)):
        for distance in (0.,minimum,floating(bits(minimum)-1),floating(bits(minimum)+1),
                         (minimum+maximum)*.5,maximum,floating(bits(maximum)-1),floating(bits(maximum)+1),32000.):
            yield Case(wide=minimum==1500.,points=((distance,0.),(0.,distance),(-distance,0.),(0.,-distance)))
    for states in ((3,)*8,(-1,0,1,2,3,4,0x80000000,0x7FFFFFFF),(0,3,0,3,0,3,0,3)):
        yield Case(count=8,states=states)
    for slot in (0,7,25):
        for wide in (0,-1,0x80000000):yield Case(slot=slot,wide=wide,count=8)
    for mutation in range(1,5):
        for answers in ((),(0.,)*4,(.5,-.5,1.,-1.)):yield Case(mutation=mutation,answers=answers)
    for answers in ((-1.,)*4,(1.,)*4,(0.,)*4,(0.,1.,1.,0.),(0.,-.5,-1.,-1.)):
        yield Case(answers=answers)


def initial(case):
    rows=[(CONTEXT,BANKS[0],4),(BANKS[0]+0x10,case.count,4),(BANKS[0]+0x14,case.active,4),
          (BANKS[0]+case.slot*4+0x15C,case.wide,4),(BANKS[0]+case.slot*4+0x16C0,case.eligible,4),
          (BANKS[1]+0x10,0,4),(BANKS[1]+0x14,0,4),(BANKS[1]+case.slot*4+0x16C0,case.eligible,4)]
    for i in range(26):
        x,z=case.points[i%len(case.points)] if case.points else ((0.,750.,1500.,2125.,3500.,4750.,8000.,16000.)[i%8],0.)
        rows.extend(((ACTORS+i*0x32C+0x14,bits(x),4),(ACTORS+i*0x32C+0x1C,bits(z),4),
            (BANKS[0]+0xE64+i*4,case.states[i%len(case.states)] if case.states else 0,4),(BANKS[1]+0xE64+i*4,3,4)))
    if case.slot>=max(case.count,0):
        rows.extend(((ACTORS+case.slot*0x32C+0x14,bits(0.),4),(ACTORS+case.slot*0x32C+0x1C,bits(0.),4)))
    rows.extend((a,v,4) for a,v in {**CONSTANTS,**trig.GLOBALS}.items())
    return rows


def fixture(case):
    m={STACK+i:0xA5 for i in range(-0x500,0x100)}
    for base,size in SEGMENTS:m.update({base+i:0xA5 for i in range(size)})
    for a,v,n in initial(case):put(m,a,v,n)
    return m


def changes(case,ordinal):
    if ordinal:return []
    state=BANKS[0]
    if case.mutation==1:return [(CONTEXT,BANKS[1],4),(BANKS[1]+case.slot*4+0x16C0,0,4)]
    if case.mutation==2:return [(CONTEXT,BANKS[1],4),(state+0x10,0,4),(state+0x14,0,4)]
    if case.mutation==3:return [(state+0xE68,3,4),(state+0x10,0,4),(state+0x14,0,4)]
    if case.mutation==4:return [(COEFFICIENT+16,bits(0.),4),(COEFFICIENT+20,bits(3.141592741),4),
        (ACTORS+case.slot*0x32C+0x14,bits(1000.),4),(ACTORS+2*0x32C+0x14,bits(3000.),4)]
    return []


def reference(memory,case):
    m=memory.copy();calls=[];stores=[];state=read(m,CONTEXT,4);rows=state+0xE64
    wide=read(m,state+case.slot*4+0x15C,4);active=read(m,state+0x14,4);count=signed(read(m,state+0x10,4))
    minimum=floating(read(m,COEFFICIENT+8 if wide else COEFFICIENT,4));maximum=8000. if wide else floating(read(m,COEFFICIENT+4,4))
    best=floating(read(m,COEFFICIENT+12,4));selected=-1
    if count<=0:return selected,m,calls,stores
    phase=floating(read(m,COEFFICIENT+16,4))
    if count>32:raise ValueError('Outside bounded completed selector reference')
    for i in range(count):
        bit=1<<(i&31)
        if read(m,rows+i*4,4)==3 or not active&bit:continue
        current=read(m,CONTEXT,4)
        if not read(m,current+case.slot*4+0x16C0,4)&((bit<<16)&0xFFFFFFFF):continue
        factor=f32(floating(read(m,COEFFICIENT+20,4))/f32(maximum-minimum))
        actor=(ACTORS+i*0x32C)&0xFFFFFFFF
        if actor:
            subject=(ACTORS+case.slot*0x32C)&0xFFFFFFFF
            dx=f32(floating(read(m,subject+0x14,4))-floating(read(m,actor+0x14,4)))
            dz=f32(floating(read(m,subject+0x1C,4))-floating(read(m,actor+0x1C,4)))
            distance=f32(math.sqrt(f32(f32(dx*dx)+f32(dz*dz))))
        else:distance=32000.
        if maximum<distance:distance=maximum
        if distance<minimum:distance=minimum
        angle=bits(f32(f32(f32(distance-minimum)*factor)+phase));ordinal=len(calls)
        value=bits(case.answers[ordinal%len(case.answers)]) if case.answers else trig.reference(angle)
        calls.append((SINE,angle,value))
        for a,v,n in changes(case,ordinal):put(m,a,v,n);stores.append((a,n,v&((1<<(8*n))-1)))
        score=f32(floating(value)+1.)
        if best<score:best=score;selected=i
    return selected,m,calls,stores


class SelectorModel(TriangleOracle,core.CopyModel):
    def __init__(self,words,memory,case,phase=0,connected=None,entry=source.ENTRY):
        core.CopyModel.__init__(self,words,memory,(case.slot,),phase=phase,connected=connected,entry=entry)
        self.case=case;self.condition=False;self.ordinal=0;self.requested=None
        self.f[20:]=[0x3F800000+i for i in range(20,32)];self.saved_f=self.f[20:].copy()

    def get(self,address,size):self.requested=('R',address,size);return super().get(address,size)
    def put(self,address,value,size):self.requested=('W',address,size);return super().put(address,value,size)

    def execute(self,word):
        op,rs,rt,rd,fd,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63
        if op==17 and rs==16 and fn==4:self.f[fd]=bits(math.sqrt(floating(self.f[rd])))
        elif op==17 and rs==16 and fn==7:self.f[fd]=self.f[rd]^0x80000000
        elif op==17 and rs==16 and fn==13:self.f[fd]=math.trunc(floating(self.f[rd]))&0xFFFFFFFF
        elif op==0 and fn==3:self.r[rd]=signed(self.r[rt])>>fd&0xFFFFFFFF
        else:super().execute(word)

    def record_call(self,target):
        if target==source.ENTRY:self.caller_args.append((self.r[4],));return
        assert target==SINE,hex(target)
        self.calls.append((target,self.f[12]));self.events.append(('CALL',target,self.f[12]))

    def hook(self,target):
        assert target==SINE;self.in_hook=True
        try:
            result=bits(self.case.answers[self.ordinal%len(self.case.answers)]) if self.case.answers else trig.reference(self.f[12])
            for a,v,n in changes(self.case,self.ordinal):self.put(a,v,n)
            self.ordinal+=1
            for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
            self.f[:20]=[0xA5000000+i for i in range(20)];self.f[0]=result
        finally:self.in_hook=False


def native_harness(body,corpus,sine_source):
    offsets=[];total=0
    for _,size in SEGMENTS:total=(total+15)&~15;offsets.append(total);total+=size
    def patch_row(a,v,n):return '{0x%Xu,0x%Xu,%d,%d}'%(a,v&0xFFFFFFFF,n,a==CONTEXT)
    rows=[];patches=[];calls=[]
    for case in corpus:
        memory=fixture(case);result,_,expected,stores=reference(memory,case)
        first=len(patches);patches.extend(patch_row(*p) for p in initial(case));count=len(patches)-first
        wanted=len(patches);patches.extend(patch_row(a,v,n) for a,n,v in stores);written=len(patches)-wanted
        call_first=len(calls)
        for ordinal,(_,angle,value) in enumerate(expected):
            start=len(patches);patches.extend(patch_row(*p) for p in changes(case,ordinal))
            calls.append('{0x%Xu,0x%Xu,%d,%d,%d}'%(angle,value,bool(case.answers),start,len(patches)-start))
        rows.append('{%d,%d,%d,%d,%d,%d,%d,%d}'%(case.slot,first,count,wanted,written,call_first,len(expected),result))
    defines=[]
    entries=[('D_800D23B0',CONTEXT,'s32*',False),('D_800CC2D0',ACTORS,'u8*',True)]
    entries += [('D_%08X'%a,a,'f32*',False) for a in CONSTANTS]
    entries += [('D_%08X'%a,a,'f32*',False) for a in trig.GLOBALS if not 0x80098D90<=a<0x80098DA4]
    entries += [('D_80098D90',0x80098D90,'f32*',True)]
    for name,a,ctype,array in entries:
        value='((%s)address(0x%Xu,actual))'%(ctype,a)
        defines.append('#define '+name+' '+(value if array else '(*'+value+')'))
    sine=sine_source[sine_source.index('f32 sinf('):].replace('f32 sinf(','static f32 realSine(',1)
    return r'''
typedef unsigned char u8;typedef unsigned int u32;typedef int s32;typedef float f32;
static u8 actual[SIZE] __attribute__((aligned(16))),wanted[SIZE] __attribute__((aligned(16)));
static const u32 regions[][3]={REGIONS};
static u8*address(u32 a,u8*buffer){u32 i;for(i=0;i<sizeof(regions)/sizeof(regions[0]);i++)
 if(a>=regions[i][0]&&a-regions[i][0]<regions[i][1])return buffer+regions[i][2]+a-regions[i][0];__builtin_trap();}
struct Patch{u32 a,v,n,pointer;};static const struct Patch patches[]={PATCHES};
struct Call{u32 angle,value,forced,first,count;};static const struct Call calls[]={CALLS};
struct Case{s32 slot;u32 first,count,wanted,written,callFirst,callCount;s32 result;};
static const struct Case cases[]={CASES};static const struct Case*c;static u32 number,error;
static void apply(u8*buffer,u32 first,u32 count){u32 i,v;u8*p;const struct Patch*q;for(i=0;i<count;i++){
 q=patches+first+i;v=q->pointer?(u32)address(q->v,actual):q->v;p=address(q->a,buffer);if(q->n==1)*p=(u8)v;else*(u32*)p=v;}}
static f32 real(u32 b){union{u32 b;f32 f;}v;v.b=b;return v.f;}
static u32 word(f32 f){union{u32 b;f32 f;}v;v.f=f;return v.b;}
DEFINES
SINE
f32 sinf(f32 angle){const struct Call*q;f32 value;if(number>=c->callCount){error=22;return 0;}
 q=calls+c->callFirst+number++;if(word(angle)!=q->angle)error=23;
 value=q->forced?real(q->value):realSine(angle);if(word(value)!=q->value)error=24;
 apply(actual,q->first,q->count);return value;}
f32 sqrtf(f32 value){f32 result;__asm__("sqrtss %1,%0":"=x"(result):"x"(value));return result;}
BODY
void _start(void){u32 n,i;s32 result;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
 c=cases+n;number=error=0;for(i=0;i<SIZE;i++)actual[i]=wanted[i]=0xA5;
 apply(actual,c->first,c->count);apply(wanted,c->first,c->count);apply(wanted,c->wanted,c->written);
 result=func_15089F9C(c->slot);if(result!=c->result)error=21;if(number!=c->callCount)error=25;
 for(i=0;i<SIZE;i++)if(actual[i]!=wanted[i])error=26;if(error)break;}
 __asm__ volatile("int $0x80"::"a"(1),"b"(error));__builtin_unreachable();}
'''.replace('SIZE',str(total)).replace('REGIONS',','.join('{0x%Xu,%d,%d}'%(b,n,o) for (b,n),o in zip(SEGMENTS,offsets))).replace(
        'PATCHES',','.join(patches)).replace('CALLS',','.join(calls)).replace('CASES',',\n'.join(rows)).replace(
        'DEFINES','\n'.join(defines)).replace('SINE',sine).replace('BODY',body)
