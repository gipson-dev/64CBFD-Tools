"""Signed clock arithmetic, full record snapshots and bounded chime effects."""
import itertools,json,struct
from tools.experiments import game_clock_update_1510aa44_match as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
OWNER,OTHER,SEED,STEP,MARK=0x30000,0x50000,0x800BE3E4,0x800BE9E4,0x70000
HELPER=0x15114D24;LENGTH=272
f32=lambda v:floating(bits(v))
div=lambda n,d:(abs(n)//d)*(-1 if n<0 else 1)
rem=lambda n,d:n-div(n,d)*d
data=lambda m,p:bytes(m[p+i]for i in range(LENGTH))
public=lambda m:{p:v for p,v in m.items()if not STACK-512<=p<STACK+512}

def fixture(clock,step,seed,initialized,chimes,last=-1,mode=0,phase=0,owner=OWNER):
    m={STACK+i:(i*17+0x41)&255 for i in range(-512,512)}
    for p,n in((owner,LENGTH),(OTHER,LENGTH),(SEED,4),(STEP,4),(MARK,4)):
        for i in range(n):m[p+i]=(i*29+0x5a)&255
    for p,v in((SEED,seed),(STEP,step),(owner+60,clock),(owner+132,initialized),(owner+124,chimes),(owner+128,last)):put(m,p,v&0xffffffff)
    return m,(owner,mode,phase)

def effect(m,owner,mode,home):
    put(m,MARK,0x13579bdf)
    if mode&1:
        for at,v in((60,0xabcdef01),(124,17),(128,99),(104,0x3f000000),(264,0x3f800000),(168,0x40000000),(8,0x40400000)):put(m,owner+at,v)
    if mode&2:put(m,SEED,0xffffffff);put(m,STEP,0x80000000)
    if mode&4:put(m,home,OTHER)
    if mode&8:put(m,home-28,bits(75.));put(m,home-8,19)

def model(initial,args):
    m=dict(initial);owner,mode,phase=args;home=STACK+phase;previous=rem(div(signed(read(m,owner+60)),3600),60)
    if read(m,owner+132)==0 and read(m,SEED)!=0:
        put(m,owner+132,1);put(m,owner+60,((read(m,SEED)*180)&0xffffffff)%43200)
        put(m,owner+60,read(m,owner+60)*60);previous=rem(div(signed(read(m,owner+60)),3600),60)
    if previous<0:previous+=60
    clock=signed((read(m,owner+60)+read(m,STEP))&0xffffffff);put(m,owner+60,clock&0xffffffff)
    if clock>=2592000:clock-=2592000;put(m,owner+60,clock&0xffffffff)
    second=div(clock,60);minute=div(second,60);angle=f32(f32(div(second,300))*2.5)
    if angle>360.:put(m,owner+60,(clock-2592000)&0xffffffff)
    minute=rem(minute,60)
    if minute<0:minute+=60
    if previous!=minute and div(previous,15)!=div(minute,15):
        count=int(f32(angle/30.))if div(minute,15)&3==0 else 1
        if div(minute,15)&3==0 and count==0:count=12
        put(m,owner+124,count&0xffffffff);put(m,owner+128,0xffffffff)
    calls=[];snapshots=[]
    if read(m,owner+124)!=0 and signed(read(m,owner+128))!=second:
        put(m,owner+128,second&0xffffffff);put(m,owner+124,(read(m,owner+124)-1)&0xffffffff)
        calls.append((HELPER,(owner,0x4cc,32767,200,1000,12)));snapshots.append(data(m,owner))
        put(m,home,owner);put(m,home-28,bits(angle));put(m,home-8,minute)
        effect(m,owner,mode,home);owner=read(m,home);angle=floating(read(m,home-28));minute=signed(read(m,home-8))
    for at,v in((104,bits(5.)),(264,bits(5.)),(168,bits(-angle)),(8,bits(-f32(f32(minute)*6.)))):put(m,owner+at,v)
    return m,calls,snapshots

def corpus():
    clocks=(0,1,59,60,3599,3600,53999,54000,215999,216000,2591999,2592000,2592001,-1,-60,-3599,-3600,-2147483648,2147483647)
    for i,values in enumerate(itertools.product(clocks,(0,1,59,60,3600,-1,-2147483648,2147483647),(0,1,-1,0x10000001),(0,1),(0,3))):
        clock,step,seed,initialized,chimes=values;yield (*fixture(*values,last=div(clock,60)if i%3==0 else -1,mode=i%4,phase=(i%2)*8),True)
    for owner,mode,phase in itertools.product((OWNER,SEED-132,SEED-60,STEP-60),range(16),(0,8)):
        yield (*fixture(3599,1,2,0,3,mode=mode,phase=phase,owner=owner),False)
    for count in(-2147483648,-1,2147483647):yield (*fixture(0,60,0,1,count),True)

class Oracle(FactoryOracle):
    def __init__(self,w,m,args,entry=source.ENTRY,connected=None):
        owner,mode,phase=args;self.clock_mode=mode;self.snapshots=[]
        super().__init__(w,m,Case(phase=phase),entry=entry,connected=connected,arguments=(owner,))
    def execute(self,w):
        if w>>26==17 and w>>21&31==16 and w&63==7:self.f[w>>6&31]=self.f[w>>11&31]^0x80000000
        else:super().execute(w)
    def record_call(self,t):
        if t==source.ENTRY:return
        assert t==HELPER;packet=tuple(self.arguments(6));self.calls.append((t,packet));self.events.append(('CALL',t,packet));self.snapshots.append(data(self.memory,packet[0]))
    def hook(self,t):
        assert t==HELPER;effect(self.memory,self.calls[-1][1][0],self.clock_mode,self.target_home)
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xa5000000+r
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011

def main():
    programs=[source.bound(*payload(source.OUT/n,source.NAME))for n in('retail.o','selected.o','guarded.o')];assert programs[0]==programs[2]
    rows=list(corpus());seen=set();prefixes=0
    for initial,args,native in rows:
        want,calls,snapshots=model(initial,args)
        for w in programs:
            m=Oracle(w,initial,args).run();assert(public(m.memory),m.calls,m.snapshots)==(public(want),calls,snapshots),(args,native)
        seen.update(Oracle(programs[0],initial,args).run().visits)
    controls=[]
    for offset,old,new in((0x84,0x24190001,0x24190002),(0x1c8,0x2401012c,0x2401012d),(0x310,0x240504cc,0x240504cb),(0x364,0x3c0140c0,0x3c0140a0)):
        changed=programs[0][:];assert changed[offset//4]==old and old!=new;changed[offset//4]=new;killed=False
        for initial,args,native in rows:
            want,calls,snapshots=model(initial,args);m=Oracle(changed,initial,args).run()
            if(public(m.memory),m.calls,m.snapshots)!=(public(want),calls,snapshots):killed=True;break
        assert killed,hex(offset);controls.append(hex(offset))
    for initial,args,native in rows[::max(1,len(rows)//8)]:
        full=Oracle(programs[0],initial,args).run()
        for cut in range(full.all_accesses):
            pair=[]
            for w in(programs[0],programs[2]):
                m=Oracle(w,initial,args);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError('Missing memory prefix boundary')
                pair.append(m)
            a,b=pair;assert(a.memory,a.r,a.f,a.condition,a.trace,a.current_pc,a.delay_of)==(b.memory,b.r,b.f,b.condition,b.trace,b.current_pc,b.delay_of);prefixes+=1
    report=dict(cases=len(rows),streams=3,visited_words=len(seen),full_state_prefixes=prefixes,emitted_controls=controls,whole_record_bytes=LENGTH,private_mutation_modes=16,raw_fault_order_claimed=False,hardware_claimed=False)
    (source.OUT/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
