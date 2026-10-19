"""Independent float32 projection reference and explicit mutable helper providers."""
from dataclasses import dataclass
import math
import struct

from tools.experiments import game_spatial_neighbor_refinement_candidates as source
from tools.tests import game_actor_sine_selector_oracle as previous

core,STACK=previous.core,previous.STACK
put,read,bits,floating,f32,signed=previous.put,previous.read,previous.bits,previous.floating,previous.f32,previous.signed
NODES,LIMIT,CACHE=0x800D2350,0x8009D9D0,0x8008729C
BANKS=(0x20000,0x22000)
ACTOR,OBJECT=0x26000,0x27000
LIST,STATE=ACTOR+0x211,ACTOR+0x212
HEIGHT,CLOSEST,LOOKUP,INSIDE,REFINE=0x15085DA8,0x15085DF8,0x15086C70,0x150A32B4,0x15086364
SEGMENTS=((NODES,4),(LIMIT,4),(CACHE,4),*((b,0x400) for b in BANKS),(ACTOR,0x400),(OBJECT,0x100))
COORDS=((0,0,0),(100,0,0),(0,0,100),(-100,0,0),(0,0,-100),(200,0,0),(0,0,200),(0,0,0),
    (32767,-32768,-32768),(-32768,32767,32767))


def byte(value):return ((value&255)^128)-128


@dataclass(frozen=True)
class Case:
    point:tuple=(20.25,2.75,5.75)
    count:int=1
    option:int=0
    band:int=2
    initial:int=0
    object:int=0
    inside:int=0
    answer:int=1
    radius:int=0
    threshold:float=100000000.0
    neighbors:tuple=(1,2,255,3,4)
    coords:tuple=COORDS
    mutation:int=0
    alias:int=0


def cases():
    for count in (0,1,2,127,128,255,-1,0x80000001,0x12340080):yield Case(count=count)
    for option in (0,1,127,128,255,-1):yield Case(option=option)
    for initial in (0,1,7,255):yield Case(initial=initial)
    for initial in (128,256,0x7FFFFFFF,0xFFFFFFFF):yield Case(count=0,initial=initial)
    for band in (0,1,127,128,254,255):yield Case(band=band)
    for inside in (0,1,-1):
        for answer in (0,1,2,255,256,0xFFFFFFFF):yield Case(object=OBJECT,inside=inside,answer=answer)
    for position in range(5):yield Case(neighbors=tuple(1 if i==position else 255 for i in range(5)))
    for radius in (0,1,5,127,128,254,255):
        for threshold in (0.0,100.0,100000000.0):yield Case(radius=radius,threshold=threshold)
    for point in ((0.,0.,3.),(-20.,-2.,5.),(20.,1.,0.),(-0.,0.,-0.),(0.,0.,0.),
                  (32767.,-32768.,-32768.),(-32768.,32767.,32767.),(123.75,-456.5,789.25)):
        yield Case(point=point)
    yield Case(point=(0.,0.,3.),neighbors=(1,255,255,255,255),threshold=10.)
    yield Case(point=(20.,0.,5.),neighbors=(1,255,255,255,255),threshold=25.)
    yield Case(point=(20.,0.,5.),neighbors=(1,5,255,255,255),answer=5)
    yield Case(point=(-20.,0.,5.),answer=3)
    yield Case(point=(5.,0.,-20.),answer=4)
    yield Case(neighbors=(255,255,255,255,255))
    yield Case(neighbors=(7,255,255,255,255))
    yield Case(radius=5,threshold=100.,neighbors=(255,)*5)
    yield Case(radius=255,threshold=100.,neighbors=(255,)*5,answer=2)
    for mutation in range(1,8):yield Case(mutation=mutation,object=OBJECT,inside=0,answer=2)
    for alias in (1,2):yield Case(alias=alias,object=OBJECT,inside=1)
    for value in (math.nan,math.inf,-math.inf):yield Case(point=(value,0.,0.),object=0)
    yield Case(threshold=math.nan)


def pointers(case):return (STATE if case.alias==1 else NODES if case.alias==2 else LIST,STATE)


def initial(case):
    rows=[(NODES,BANKS[0],4),(LIMIT,bits(case.threshold),4),(LIST,0x31,1),(STATE,0x42,1),(ACTOR+0x213,0x66,1)]
    for axis,v in enumerate(case.point):rows.append((ACTOR+0x14+axis*4,bits(v),4))
    for bank,base in enumerate(BANKS):
        coords=list(case.coords)
        if bank:coords[1],coords[2]=coords[2],coords[1]
        for i in range(16):
            xyz=coords[i%len(coords)]
            rows.extend((base+i*16+j*2,v,2) for j,v in enumerate(xyz))
            rows.extend(((base+i*16+7,0x40+bank*16+i,1),(base+i*16+8,0,1)))
            for j in range(5):rows.append((base+i*16+9+j,255,1))
        if 0<=case.initial<16:
            rows.append((base+case.initial*16+8,case.radius,1))
            rows.extend((base+case.initial*16+9+j,v,1) for j,v in enumerate(case.neighbors))
    return rows


def fixture(case):
    memory={STACK+i:(i*19+0xA5)&255 for i in range(-0x1600,0x400)}
    for base,size in SEGMENTS:memory.update({base+i:0xA5 for i in range(size)})
    for a,v,n in initial(case):put(memory,a,v,n)
    return memory


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x1600<=a<STACK+0x400}


def changes(case,target):
    stage={1:HEIGHT,2:CLOSEST,3:LOOKUP,4:INSIDE,5:REFINE,7:LOOKUP}.get(case.mutation)
    if case.mutation==6:
        return [(NODES,BANKS[1] if target==HEIGHT else BANKS[0],4)] if target in (HEIGHT,LOOKUP) else []
    if stage!=target:return []
    return [(LIMIT,bits(0.0),4)] if case.mutation==7 else [(NODES,BANKS[1],4)]


def answer(case,target):
    return {HEIGHT:case.band,CLOSEST:case.initial,LOOKUP:case.object,INSIDE:case.inside,REFINE:case.answer}[target]&0xFFFFFFFF


def provider(memory,case,target,args):
    stores=[]
    for a,v,n in changes(case,target):put(memory,a,v,n);stores.append((a,n,v&((1<<(n*8))-1)))
    if target==REFINE:
        value=case.answer&255;put(memory,args[3],value,1);stores.append((args[3],1,value))
        value=(read(memory,args[4],1)+1)&255;put(memory,args[4],value,1);stores.append((args[4],1,value))
    return answer(case,target),stores


def reference(memory,case):
    m=memory.copy();calls=[];stores=[];transcript=[]
    def call(target,*args):
        args=tuple(a&0xFFFFFFFF for a in args);calls.append((target,*args))
        result,writes=provider(m,case,target,args);stores.extend(writes)
        transcript.append((target,args,result,writes));return result
    x,y,z=map(f32,case.point);band=call(HEIGHT,bits(y))
    index=call(CLOSEST,bits(x),bits(y),bits(z),0,byte(band))
    refined=255;selected=255
    if byte(case.count)>0 and index!=255:
        obj=call(LOOKUP,index)
        if obj:
            if any(not math.isfinite(v) or not -2147483648<=math.trunc(v)<=2147483647 for v in (x,y,z)):
                raise ValueError('Outside bounded native integer-conversion domain')
            contained=call(INSIDE,obj,*map(math.trunc,(x,y,z)))!=0
        else:contained=False
        if contained:refined=call(REFINE,index,byte(case.count),byte(case.option),*pointers(case))
        else:
            nodes=read(m,NODES,4);node=nodes+index*16
            radius=f32(read(m,node+8,1));diameter=f32(radius+radius);minimum=floating(read(m,LIMIT,4))
            if minimum<f32(diameter*diameter):refined=call(REFINE,index,byte(case.count),byte(case.option),*pointers(case))
            else:
                for slot in range(5):
                    candidate=read(m,node+9+slot,1)
                    if candidate==255:continue
                    other=nodes+candidate*16
                    ox=((read(m,node,2)^32768)-32768);oz=((read(m,node+4,2)^32768)-32768)
                    dx=f32(((read(m,other,2)^32768)-32768)-ox)
                    dz=f32(((read(m,other+4,2)^32768)-32768)-oz)
                    length=f32(math.sqrt(f32(f32(dx*dx)+f32(dz*dz))))
                    inv=f32(1.0/length) if length else math.inf
                    nx=f32(dx*inv);nz=f32(dz*inv)
                    base=f32(f32(f32(ox)*nx)+f32(f32(oz)*nz))
                    dot=f32(f32(x*nx)+f32(z*nz));projection=f32(dot+-base)
                    if projection>0.:
                        rx=f32(x-f32(f32(ox)+f32(nx*projection)))
                        rz=f32(z-f32(f32(oz)+f32(nz*projection)))
                        distance=f32(f32(rx*rx)+f32(rz*rz))
                        if distance<minimum:minimum,selected=distance,candidate
                if selected!=255:
                    value=call(REFINE,index,byte(case.count),byte(case.option),*pointers(case))
                    if value==selected:refined=value
    return (refined if refined!=255 else index)&0xFFFFFFFF,m,calls,stores,transcript,selected


class RefinementModel(previous.SelectorModel):
    def __init__(self,words,memory,case,phase=0,connected=None,entry=source.ENTRY):
        core.CopyModel.__init__(self,words,memory,(0,0,bits(f32(case.point[2])),case.count),
            phase=phase,connected=connected,entry=entry)
        self.case=case;self.condition=False;self.requested=None;self.raw_calls=[]
        self.f[12],self.f[14]=map(lambda v:bits(f32(v)),case.point[:2])
        self.f[20:]=[0x3F800000+i for i in range(20,32)];self.saved_f=self.f[20:].copy()
        for i,value in enumerate((case.option,*pointers(case))):put(self.memory,STACK+phase+0x10+i*4,value,4)

    def args(self,n):return tuple(self.r[4+i] if i<4 else read(self.memory,self.r[29]+i*4,4) for i in range(n))

    def record_call(self,target):
        if target==source.ENTRY:
            self.caller_args.append((self.f[12],self.f[14],self.r[6],self.r[7],*self.args(7)[4:]));return
        if target==HEIGHT:raw=(self.f[12],);logical=raw
        elif target==CLOSEST:
            raw=(self.f[12],self.f[14],self.r[6],self.r[7],read(self.memory,self.r[29]+16,4))
            logical=(*raw[:4],byte(raw[4])&0xFFFFFFFF)
        elif target==LOOKUP:raw=logical=self.args(1)
        elif target==INSIDE:raw=logical=self.args(4)
        elif target==REFINE:raw=logical=self.args(5)
        else:raise AssertionError('Unexpected refinement helper: %X'%target)
        self.current_args=raw;self.raw_calls.append((target,*raw));self.calls.append((target,*logical))
        self.events.append(('CALL',target,*logical))

    def hook(self,target):
        self.in_hook=True
        try:
            result,writes=provider(self.memory,self.case,target,self.current_args)
            # Reapply prescribed effects through the trace without inventing dispatched accesses.
            for a,n,v in writes:self.put(a,v,n)
            count=5 if target in (CLOSEST,REFINE) else 4
            for i in range(count):self.put(self.r[29]+i*4,0xBA000000+len(self.calls)*16+i,4)
            for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
            self.f[:20]=[0xA5000000+i for i in range(20)];self.condition=bool(len(self.calls)&1)
            self.r[2]=result
        finally:self.in_hook=False


def native_harness(body,corpus):
    offsets=[];total=0
    for _,size in SEGMENTS:total=(total+15)&~15;offsets.append(total);total+=size
    patches=[];calls=[];rows=[]
    def patch_row(a,v,n):return '{0x%Xu,0x%Xu,%d,%d}'%(a,v&0xFFFFFFFF,n,a==NODES and n==4)
    for case in corpus:
        result,_,_,stores,transcript,_=reference(fixture(case),case)
        first=len(patches);patches.extend(patch_row(*p) for p in initial(case));count=len(patches)-first
        wanted=len(patches);patches.extend(patch_row(a,v,n) for a,n,v in stores);written=len(patches)-wanted
        call_first=len(calls)
        for target,args,value,writes in transcript:
            start=len(patches);patches.extend(patch_row(a,v,n) for a,n,v in writes)
            args=(*args,*([0]*(5-len(args))))
            calls.append('{0x%Xu,%d,{%s},0x%Xu,%d,%d,%d}'%(target,1 if target==HEIGHT else
                {CLOSEST:5,LOOKUP:1,INSIDE:4,REFINE:5}[target],','.join('0x%Xu'%(a&0xFFFFFFFF) for a in args),
                value,target==LOOKUP and bool(value),start,len(patches)-start))
        fields=(first,count,wanted,written,call_first,len(transcript),*[bits(f32(v)) for v in case.point],
            case.count&0xFFFFFFFF,case.option&0xFFFFFFFF,*pointers(case),result)
        rows.append('{'+','.join('0x%Xu'%v for v in fields)+'}')
    return r'''
typedef unsigned char u8;typedef signed char s8;typedef short s16;typedef unsigned short u16;typedef unsigned int u32;typedef int s32;typedef float f32;
static u8 actual[SIZE] __attribute__((aligned(16))),wanted[SIZE] __attribute__((aligned(16)));
static const u32 regions[][3]={REGIONS};
static __attribute__((noreturn)) void fail(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code));__builtin_unreachable();}
static u8*address(u32 a,u8*b){u32 i;for(i=0;i<sizeof(regions)/sizeof(regions[0]);i++)
 if(a>=regions[i][0]&&a-regions[i][0]<regions[i][1])return b+regions[i][2]+a-regions[i][0];fail(29);}
static u32 guest(u32 p){u32 i,a;for(i=0;i<sizeof(regions)/sizeof(regions[0]);i++){
 a=(u32)(actual+regions[i][2]);if(p>=a&&p-a<regions[i][1])return regions[i][0]+p-a;}return p;}
struct Patch{u32 a,v,n,pointer;};static const struct Patch patches[]={PATCHES};
struct Call{u32 target,n,a[5],result,pointer,first,count;};static const struct Call calls[]={CALLS};
struct Case{u32 first,count,wanted,written,call_first,call_count,x,y,z,mode,option,list,state,result;};
static const struct Case cases[]={CASES};static const struct Case*c;static u32 ordinal;
static f32 real(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}
static u32 word(f32 v){union{u32 u;f32 f;}x;x.f=v;return x.u;}
static void apply(u8*b,u32 first,u32 count){u32 i,v;const struct Patch*q;u8*p;
 for(i=0;i<count;i++){q=patches+first+i;v=q->pointer?(u32)address(q->v,actual):q->v;p=address(q->a,b);
 if(q->n==1)*p=(u8)v;else if(q->n==2)*(s16*)p=(s16)v;else*(u32*)p=v;}}
static s32 invoke(u32 target,u32 n,const u32*a){u32 i;const struct Call*q;
 if(ordinal>=c->call_count)fail(22);q=calls+c->call_first+ordinal++;
 if(target!=q->target||n!=q->n)fail(22);for(i=0;i<n;i++)if(a[i]!=q->a[i])fail(23);
 apply(actual,q->first,q->count);return q->pointer?(s32)address(q->result,actual):(s32)q->result;}
#define D_800D2350 (*(u8**)address(0x800D2350u,actual))
#define D_8009D9D0 (*(f32*)address(0x8009D9D0u,actual))
s32 func_15085DA8(f32 y){u32 a[]={word(y)};return invoke(0x15085DA8u,1,a);}
s32 func_15085DF8(f32 x,f32 y,f32 z,s8 mode,s8 band){u32 a[]={word(x),word(y),word(z),(u32)(s32)mode,(u32)(s32)band};return invoke(0x15085DF8u,5,a);}
s32 func_15086C70(s32 index){u32 a[]={(u32)index};return invoke(0x15086C70u,1,a);}
s32 func_150A32B4(s32 object,s32 x,s32 y,s32 z){u32 a[]={guest((u32)object),(u32)x,(u32)y,(u32)z};return invoke(0x150A32B4u,4,a);}
s32 func_15086364(s32 index,s32 count,s32 option,u8*list,u8*state){u32 a[]={(u32)index,(u32)count,(u32)option,guest((u32)list),guest((u32)state)};return invoke(0x15086364u,5,a);}
f32 sqrtf(f32 value){f32 result;__asm__("sqrtss %1,%0":"=x"(result):"x"(value));return result;}
BODY
void _start(void){u32 n,i;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
 c=cases+n;ordinal=0;for(i=0;i<SIZE;i++)actual[i]=wanted[i]=0xA5;
 apply(actual,c->first,c->count);apply(wanted,c->first,c->count);apply(wanted,c->wanted,c->written);
 if((u32)func_15086098(real(c->x),real(c->y),real(c->z),(s8)c->mode,(s8)c->option,address(c->list,actual),address(c->state,actual))!=c->result)fail(21);
 if(ordinal!=c->call_count)fail(25);for(i=0;i<SIZE;i++)if(actual[i]!=wanted[i])fail(24);
 }fail(0);}
'''.replace('SIZE',str(total)).replace('REGIONS',','.join('{0x%Xu,%d,%d}'%(b,n,o) for (b,n),o in zip(SEGMENTS,offsets))).replace(
        'PATCHES',','.join(patches)).replace('CALLS',',\n'.join(calls)).replace('CASES',',\n'.join(rows)).replace('BODY',body)
