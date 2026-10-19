"""Independent mutable-table assignment reference and bounded native32 fixtures."""
from dataclasses import dataclass

from tools.experiments import game_balanced_target_assignment_candidates as source
from tools.tests import test_game_route_record_copy_match as core

STACK,put,read=core.STACK,core.put,core.read
CONTEXT,BANK=0x800D23B0,0x20000
SEGMENTS=((CONTEXT,4),(BANK,0x2000))


def signed(value):return (value&0x7FFFFFFF)-(value&0x80000000)


@dataclass(frozen=True)
class Case:
    count:int=8
    current:int=0
    flags:tuple=(2,0,3,1)
    teams:tuple=(1,2,1,2)
    active:tuple=(1,)
    scores:tuple=(100,110,120,130)
    position:int=0
    sentinel:int=16
    pattern:int=0


def cases():
    for n in (-2147483648,-1,0,1,2,3,4,5,7,8,9,15,16):yield Case(count=n)
    for n in (17,31,32,39,40):yield Case(count=n,active=(0,))
    for flags in ((0,),(1,),(2,),(3,),(4,),(258,),(259,),(-1,),(2147483647,),(-2147483648,),(0,2,0,3)):
        yield Case(flags=flags)
    for teams in ((1,),(2,1),(1,2,2,1),(0,-1,0,-1),(2147483647,-2147483648)):
        for current in (0,1,7,15):yield Case(teams=teams,current=current)
    for active in ((0,),(-1,),(-2147483648,),(2147483647,),(1,0,-1,1)):yield Case(active=active)
    for score in (-2147483648,-2000000000,-2,-1,0,1,9999999,10000000,10000001,0x40000001):
        yield Case(scores=(score,))
    for position in (-1,0,1,7,14,15):
        for sentinel in (0,4,15,16):yield Case(position=position,sentinel=sentinel)
    for pattern in (0,1,2):yield Case(count=16,pattern=pattern)
    # Non-special receiver0 must follow special receiver2 despite its lower index.
    yield Case(count=4,flags=(0,0,2,0),scores=(1,),teams=(1,2,1,2))
    for tag in (258,259):
        yield Case(count=4,flags=(tag,0,2,0),scores=(1,),teams=(1,2,1,2))


def initial(case):
    rows=[(CONTEXT,BANK,4),(BANK+4,case.current,4),(BANK+0x10,case.count,4)]
    for i in range(40):
        rows.extend(((BANK+0x15C+i*4,case.flags[i%len(case.flags)],4),
            (BANK+0x39C+i*4,case.active[i%len(case.active)],4),
            (BANK+0xE64+i*4,case.teams[i%len(case.teams)],4)))
    # Longer count fixtures are deliberately inactive; their backed tables overlap.
    if case.count<=16:
        for candidate in range(16):
            for j in range(16):
                receiver=(j+case.position)&15
                value=-1 if j==case.sentinel else 99 if case.position<0 else receiver
                score=case.scores[candidate%len(case.scores)]
                if case.pattern==1:score+=j*17
                if case.pattern==2:score=0x40000000+(candidate+j)*13
                rows.extend(((BANK+0x5DC+(candidate*16+j)*4,value,4),
                    (BANK+0x9DC+(candidate*16+j)*4,score,4)))
    return rows


def fixture(case,poison=0xA5):
    memory={STACK+i:poison for i in range(-0x500,0x100)}
    for base,size in SEGMENTS:memory.update({base+i:(i*37+0xA5)&255 for i in range(size)})
    for a,v,n in initial(case):put(memory,a,v,n)
    return memory


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x500<=a<STACK+0x100}


def reference(memory):
    m=memory.copy();base=read(m,CONTEXT,4)
    current=signed(read(m,base+4,4));count=signed(read(m,base+0x10,4))
    if count>40:raise ValueError('Outside the bounded forty-cell assignment reference')
    own=signed(read(m,base+0xE64+current*4,4));used=[0]*max(count,0);stores=[]
    for special_pass in (True,False):
        for receiver in range(max(count,0)):
            flag=signed(read(m,base+0x15C+receiver*4,4))
            if (flag in (2,3))!=special_pass:continue
            if signed(read(m,base+0xE64+receiver*4,4))!=own:continue
            best,selected=10000000,-1
            for candidate in range(count):
                if signed(read(m,base+0x39C+candidate*4,4))<=0:continue
                if signed(read(m,base+0xE64+candidate*4,4))==own:continue
                score=None
                for j in range(16):
                    at=candidate*16+j;neighbor=signed(read(m,base+0x5DC+at*4,4))
                    if neighbor==-1:break
                    if neighbor==receiver:
                        score=signed(read(m,base+0x9DC+at*4,4));break
                if score is None or score==-1:continue
                score=signed((score&0xFFFFFFFF)<<(used[candidate]&31)&0xFFFFFFFF)
                if score<best:best,selected=score,candidate
            if selected!=-1:used[selected]=(used[selected]+1)&255
            for offset,value in ((0x45C,best),(0x49C,selected)):
                a=base+offset+receiver*4;put(m,a,value,4);stores.append((a,4,value&0xFFFFFFFF))
    return m,stores


class AssignmentModel(core.CopyModel):
    def __init__(self,words,memory,phase=0,connected=None,entry=source.ENTRY):
        super().__init__(words,memory,(),connected=connected,phase=phase,entry=entry)
        self.condition=False;self.requested=None

    def get(self,address,size):
        if self.recording:self.requested=('R',address,size)
        return super().get(address,size)

    def put(self,address,value,size):
        if self.recording:self.requested=('W',address,size,value&((1<<(size*8))-1))
        super().put(address,value,size)

    def record_call(self,target):
        assert target==source.ENTRY,hex(target)
        self.caller_args.append(())

    def hook(self,target):raise AssertionError('Unexpected assignment provider: %X'%target)


def native_harness(body,corpus):
    offsets=[];total=0
    for _,size in SEGMENTS:total=(total+15)&~15;offsets.append(total);total+=size
    patches=[];rows=[]
    def row(a,v,n):return '{0x%Xu,0x%Xu,%d,%d}'%(a,v&0xFFFFFFFF,n,a==CONTEXT)
    for case in corpus:
        _,stores=reference(fixture(case));first=len(patches)
        patches.extend(row(*p) for p in initial(case));count=len(patches)-first
        start=len(patches);patches.extend(row(a,v,n) for a,n,v in stores)
        rows.append('{%d,%d,%d,%d}'%(first,count,start,len(patches)-start))
    return r'''
typedef unsigned char u8;typedef signed char s8;typedef unsigned int u32;typedef int s32;
static u8 actual[SIZE] __attribute__((aligned(16))),wanted[SIZE] __attribute__((aligned(16)));
static const u32 regions[][3]={REGIONS};
static u8*address(u32 a,u8*b){u32 i;for(i=0;i<sizeof(regions)/sizeof(regions[0]);i++)
 if(a>=regions[i][0]&&a-regions[i][0]<regions[i][1])return b+regions[i][2]+a-regions[i][0];__builtin_trap();}
struct Patch{u32 a,v,n,pointer;};static const struct Patch patches[]={PATCHES};
struct Case{u32 first,count,start,written;};static const struct Case cases[]={CASES};
static void apply(u8*b,u32 first,u32 count){u32 i,v;const struct Patch*q;for(i=0;i<count;i++){
 q=patches+first+i;v=q->pointer?(u32)address(q->v,actual):q->v;
 if(q->n==1)*address(q->a,b)=(u8)v;else*(u32*)address(q->a,b)=v;}}
#define D_800D23B0 (*(s32*)address(CONTEXT,actual))
BODY
void _start(void){u32 n,i,j,error=0;const struct Case*c;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  for(j=0;j<sizeof(regions)/sizeof(regions[0]);j++)for(i=0;i<regions[j][1];i++)
   actual[regions[j][2]+i]=wanted[regions[j][2]+i]=(u8)(i*37+0xA5);
  c=cases+n;apply(actual,c->first,c->count);apply(wanted,c->first,c->count);apply(wanted,c->start,c->written);
  if(func_1508BF14()!=0)error=21;
  for(i=0;i<SIZE;i++)if(actual[i]!=wanted[i])error=25;if(error)break;
 }
 __asm__ volatile("int $0x80"::"a"(1),"b"(error));__builtin_unreachable();}
'''.replace('SIZE',str(total)).replace('REGIONS',','.join('{0x%Xu,%d,%d}'%(b,n,o) for (b,n),o in zip(SEGMENTS,offsets))).replace(
        'PATCHES',','.join(patches)).replace('CASES',',\n'.join(rows)).replace('CONTEXT','0x%Xu'%CONTEXT).replace('BODY',body)
