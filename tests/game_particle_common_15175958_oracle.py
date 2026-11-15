"""Private differential screen; no installation or exact-match credit."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,math,struct
from tools.tests import game_particle_state_15176b84_oracle as base
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.experiments.game_particle_display_151770c8_match import bound
from tools.experiments.game_paired_ground_constructor_match import payload
bits,floating,read,put,u32,signed=base.bits,base.floating,base.read,base.put,base.u32,base.signed
from tools.experiments import game_particle_common_15175958_candidates as source
ROOT,OUT=source.ROOT,source.OUT
ENTRY=0x15175958;P=base.RECORD;CONFIG=0x8008d0b0;SURFACE=0x60000;ATTR=0x61000
FREE,RNG,DIST=base.FREE,base.RANDOM,base.DIST
ATAN,ANGLE,SOUND_ALIVE,SOUND_UPDATE,FLOOR,SIN,COS,SOUND,CULL=0x150484a0,0x150490a8,0x1000f3d0,0x1000f91c,0x1510f8d8,0x150ad78c,0x150ad780,0x10010f88,0x1510aee0
FLOATS=(ATAN,SIN,COS)
COUNTS={FREE:1,RNG:0,DIST:4,ANGLE:1,SOUND_ALIVE:1,SOUND_UPDATE:10,FLOOR:4,SOUND:10,CULL:10}

import re
CONSTANTS=[(int(a,16),int(w,16))for a,w in re.findall(r'/\*\s*[0-9A-F]+\s+(800A71[0-9A-F]{2})\s+([0-9A-F]{8})\s*\*/',(ROOT/'conker/asm/data/24BC30.rodata.s').read_text())]
assert len(CONSTANTS)>=12

@dataclass(frozen=True)
class Case:
    flags:int=0
    state:int=0
    phase:int=0
    seed:int=0
    variant:int=7
    present:int=1
    enabled:int=1
    live:int=1
    fading:int=0
    alpha:int=255
    step:int=1
    sound:int=0
    mode:int=0
    distance:int=100
    angle:int=128
    random:int=0x80000081
    tilt:float=5.
    rate:float=2.
    timer:int=1
    divisor:int=7
    special:int=0
    heading:float=20.
    bank:float=3.
    height:float=50.
    speed:int=10
    acceleration:int=1
    source_y:int=20
    late_divisor:int=7
    cooldown_zero:int=0

def fixture(c):
    m=base.fixture(base.Case(variant=c.variant,opacity=c.alpha,fading=c.fading,step=c.step,present=c.present,enabled=c.enabled,live=c.live,state=c.state,seed=c.seed))
    for lo,n in ((CONFIG,256*56),(0x800c3500,256),(0x800d2100,64),(0x800d35e0,8),(0x800d9b00,0x180),(0x800be9e4,32),(SURFACE,256),(ATTR,128)):
        for i in range(n):m.setdefault(lo+i,0)
    for addr,word in CONSTANTS:put(m,addr,word)
    for i in range(256):
        a=CONFIG+i*56
        for j,v in enumerate((30,2,5,8)):m[a+j]=v
        for off,v in ((4,15.),(8,40.),(16,4.),(24,0.),(32,1.)):put(m,a+off,bits(v))
    for off,v in ((0x98,17.75),(0x9c,c.height),(0xa0,-19.25),(0xa8,c.tilt),(0xac,c.heading),(0xb0,c.bank),(0xb4,-1.),(0xb8,c.rate),(0xbc,100.),(0xc8,1.),(0xcc,0.),(0xe0,40.),(0xe4,60.)):put(m,P+off,bits(v))
    for off,v in ((0x92,c.flags),(0xa4,c.speed),(0xa6,c.acceleration),(0xd0,0),(0xd2,c.source_y),(0xd4,0),(0xd6,200),(0xd8,50),(0xda,c.divisor),(0xdc,c.timer),(0xde,c.timer),(0xee,c.sound)):put(m,P+off,v&65535,2)
    m[P]=19 if c.seed&1 else 18
    put(m,P+0x94,read(m,base.LOW+c.variant*20))
    put(m,0x800be9f0,6 if c.special else 0);m[0x800c35ea]=1;m[0x800c35e8]=15;put(m,0x800c35b0,60)
    put(m,0x800d2138,1 if c.seed&2 else 2)
    put(m,0x800dbe3c,SURFACE);put(m,0x800dbe5c,ATTR)
    for i in range(32):put(m,ATTR+i*4,i^0x12345678)
    m[0x800ddf60+1]=0 if c.seed&4 else 1
    if c.cooldown_zero:
        for i in range(12):m[0x800ddf60+i]=0
    return m

class Oracle(FactoryOracle):
    def __init__(self,w,m,c,entry=ENTRY,connected=None):
        super().__init__(w,m,c,entry=entry,connected=connected,arguments=(P,));self.observed=[];self.before_r=self.r[:];self.before_f=self.f[:]
    def execute(self,w):
        if w>>26==0 and w&63==27 and self.r[w>>16&31]==0:raise base.DivisionBoundary
        if w>>26==17 and w>>21&31==16 and w&63 in(4,5,7):
            fd,fs=w>>6&31,w>>11&31;fn=w&63
            self.f[fd]=bits(math.sqrt(floating(self.f[fs])))if fn==4 else self.f[fs]&0x7fffffff if fn==5 else self.f[fs]^0x80000000
            return
        return super().execute(w)
    def record_call(self,t):
        if t==ENTRY:
            assert self.r[4]==P,('entry-pointer',self.r[4]);return
        if t in FLOATS:a=(self.f[12],self.f[14])if t==ATAN else(self.f[12],)
        else:
            assert t in COUNTS,hex(t);a=tuple(self.arguments(COUNTS[t]))
            if t==ANGLE:a=('relative',read(self.memory,a[0]),read(self.memory,a[0]+8))
            if t==FLOOR:a=(*a[:3],'surface-output')
        self.calls.append((t,a));self.observed.append(base.snapshot(self.memory,P));self.events.append(('CALL',t,a))
    def hook(self,t):
        c=self.case;n=len(self.calls);value=0;fp=bits(0.5 if (n+c.seed)&1 else -0.25)
        if t==RNG:value=u32(c.random+n*19)
        elif t==DIST:value=u32(c.distance)
        elif t==ANGLE:value=u32(c.angle)
        elif t==SOUND_ALIVE:value=c.seed&1
        elif t==CULL:value=(c.seed+n)&1
        elif t==FLOOR:
            put(self.memory,self.arguments(4)[3],SURFACE+12*(c.seed%5)if c.seed&1 else 0);value=5
        if c.mode:
            if c.mode&1:
                for off,v in ((0xa8,3.+n),(0xac,20.+n),(0xb8,-2.+n),(0xbc,100.+n),(0x98,10.+n),(0x9c,70.+n),(0xa0,-20.-n),(0xe0,50.+n),(0xe4,60.+n)):put(self.memory,P+off,bits(v))
                self.memory[P+0x90]=(c.seed+n)%12
                self.memory[P+0xed]=(c.seed+n)%4
                self.memory[P+0x91]=(c.seed+n)%4
            if c.mode&2:
                put(self.memory,base.STEP,n+1);self.memory[0x800c35ea]=0 if n&1 else 1
            if c.mode&4:put(self.memory,P+0x92,(c.flags^(n&7))&65535,2)
        if t==RNG and c.mode&8:put(self.memory,P+0xda,c.late_divisor&65535,2)
        put(self.memory,base.MARK,t^n)
        for i in range(4):self.put(self.r[29]+i*4,0xb5000000+i,4)
        for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
        self.f[:20]=[0xa5000000+i for i in range(20)];self.f[0]=fp;self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value);self.condition=bool(n&1)

def cases():
    yield Case()
    for flags,state,rate,timer,mode in itertools.product((0,4,0x10|4,0x40,0x80,0x200,0x2,0x3ff),(0,2,3),(-2.,0.,2.),(-1,0,1),(0,1,3,7)):
        yield Case(flags=flags,state=state,rate=rate,timer=timer,mode=mode,seed=flags+state,sound=1)
    for v,p,e,f,a in itertools.product((0,7,8,9,255),(0,1),(0,1),(0,1),(0,127,255)):
        yield Case(variant=v,present=p,enabled=e,fading=f,alpha=a,special=1,seed=v)
    for flags,tilt,bank,heading in itertools.product((0,0x20,4,0x40),( -50.,-0.,0.,50.),(-20.,0.,20.),(-1.,0.,359.,361.)):
        yield Case(flags=flags,tilt=tilt,bank=bank,heading=heading,seed=5)
    for divisor,rng,source_y in itertools.product((-32768,-1,1,32767),(0,0x7fffffff,0x80000081,0xffffffff),(-32768,32767)):
        yield Case(flags=0x40,timer=0,divisor=divisor,random=rng,source_y=source_y)
    for distance,angle in itertools.product((49,50,51,200,201),(-1,0,127,128,255,256)):
        yield Case(flags=0x14,distance=distance,angle=angle,state=3)
    for speed,acceleration,step in itertools.product((-32768,0,32767),(-32768,-1,0,1,32767),(-1,0,1,0x7fffffff,0x80000000)):
        yield Case(speed=speed,acceleration=acceleration,step=step)
    for flags,state,field,value in itertools.product((0,4,0x20,0x40,0x200,0x3ff),(2,3),('tilt','heading','bank','rate'),(float('nan'),float('inf'),-float('inf'))):
        yield Case(flags=flags,state=state,**{field:value})
    for divisor,late,mode in itertools.product((1,-1),(1,-1,-32768),(8,9,11,15)):
        yield Case(flags=0x40,timer=0,divisor=divisor,late_divisor=late,mode=mode,seed=5)
    yield Case(seed=5,mode=1,cooldown_zero=1)

def main():
    rom=(ROOT/'conker/conker.us.bin').read_bytes();retail=list(struct.unpack_from('>961I',rom,0x1a2e08));candidate=bound(*payload(OUT/'selected.o','func_15175958'));count=0;seen=set()
    for c in cases():
        initial=fixture(c);pair=[]
        for w in (retail,candidate):
            m=Oracle(w,initial,c)
            try:m.run()
            except Exception:
                print('machine exception',c,'stream',len(pair),'pc',hex(m.current_pc),flush=True);raise
            pair.append(m)
            assert m.r[16:24]==m.before_r[16:24]and m.r[29:31]==m.before_r[29:31]and m.f[20:]==m.before_f[20:]
        a,b=pair
        if (base.public(a.memory),a.calls,a.observed)!=(base.public(b.memory),b.calls,b.observed):
            changes=[(hex(k),a.memory.get(k),b.memory.get(k))for k in a.memory.keys()|b.memory.keys()if a.memory.get(k)!=b.memory.get(k)and not base.STACK-512<=k<base.STACK+512]
            print('FAILED',c,'memory',changes[:30],flush=True)
            print('retail calls',a.calls,'candidate calls',b.calls,flush=True)
            for i,(x,y)in enumerate(zip(a.observed,b.observed)):
                if x!=y:print('snapshot',i,[(hex(j),u,v)for j,(u,v)in enumerate(zip(x,y))if u!=v][:25],flush=True)
            raise AssertionError(c)
        count+=1;seen.update(a.visits)
    controls=[]
    for label,pc,changed,c in (
        ('active-marker',0x15175bc4,lambda w:w&~(31<<16),Case()),
        ('fade-direction',0x15175b88,lambda w:w&~63|33,Case(fading=1,alpha=127)),
        ('speed-floor',0x1517639c,lambda w:w&~(31<<16),Case(speed=0,acceleration=0)),
        ('sound-cooldown',0x15176774,lambda w:w&~(31<<16),Case(seed=5)),
        ('unsigned-height',0x151760a8,lambda w:w&0xffff0000|0x4f00,Case(flags=0x40,timer=0,divisor=-1,random=0x80000081))):
        w=retail[:];at=(pc-ENTRY)//4;v=changed(w[at]);assert v!=w[at];w[at]=v;initial=fixture(c)
        bad=Oracle(w,initial,c);good=Oracle(candidate,initial,c);bad.run();good.run()
        assert (base.public(bad.memory),bad.calls,bad.observed)!=(base.public(good.memory),good.calls,good.observed),'Ineffective control '+label
        controls.append(label)
    zeroes=0
    for flags,mode,seed,late in itertools.product((0x40,0xc0),(0,1,3,7,8,9),(0,5),(0,)):
        c=Case(flags=flags,timer=0,divisor=0 if mode<8 else 7,late_divisor=late,mode=mode,seed=seed);initial=fixture(c);pair=[]
        for w in(retail,candidate):
            m=Oracle(w,initial,c)
            try:m.run()
            except base.DivisionBoundary:pass
            else:raise AssertionError('Missing pre-division boundary')
            assert m.calls[-1][0]==RNG and read(m.memory,P+0xde,2)==65535
            pair.append(m)
        a,b=pair;assert (base.public(a.memory),a.calls,a.observed)==(base.public(b.memory),b.calls,b.observed),c
        zeroes+=1
    report=dict(cases=count,retail_words_visited=len(seen),streams=2,effective_controls=controls,predivision_zero_prefixes=zeroes,private=True,exact_credit=0)
    (OUT/'behavior-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
