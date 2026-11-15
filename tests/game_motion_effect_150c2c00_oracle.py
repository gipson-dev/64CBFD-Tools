"""Private finite semantics with original polar-helper and byte-copy instructions."""
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,struct
from tools.experiments import game_motion_effect_150c2c00_recovery as s
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read

OWNER,MOTION,OUTPUT,MARK=0x30040,0x60040,0x50040,0x70000
CONST,DT,SELECT=0x800a02c0,0x800be9a4,0x80082fa4
RANDF,RANDI,LOOKUP,ANGLE,DIFF,POLAR,EMIT,COPY=(0x150ada68,0x150ada20,0x15144b34,0x150484a0,0x15144c8c,0x1514373c,0x15149550,0x10022ec0)
COS,SIN=0x15047c00,0x15047d60
mul=lambda a,b:fp(a,b,'mul')
add=lambda a,b:fp(a,b,'add')
sub=lambda a,b:fp(a,b,'sub')
lt=lambda a,b:floating(a)<floating(b)

@dataclass(frozen=True)
class Case:
    accumulator:int=0x40500000
    dt:int=0x3f000000
    motion:int=2
    policy:int=0
    outcome:int=1
    mutation:int=0
    phase:int=0
    seed:int=0

def cases():
    for i,(a,m,p,o,mut,phase) in enumerate(itertools.product((-.5,0.,.5,1.,1.0000001192092896,1.5,2.,4.25),range(3),range(3),range(2),range(2),(0,8))):
        yield Case(bits(a),bits((0.,.5,1.)[i%3]),m,p,o,mut,phase,i)

@lru_cache(maxsize=1)
def rom():return (s.ROOT/'conker/conker.us.bin').read_bytes()
def coefficients():return struct.unpack_from('>20I',rom(),0x244d80)
def packet_bytes(m,p):return bytes(m[p+i] if not 0x35<=i<0x38 else 0 for i in range(72))
def public(m):return {a:v for a,v in m.items() if not STACK-2048<=a<STACK+2048}
def data(m,p,n):return bytes(m[p+i] for i in range(n))

def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-2048,2048)}
    for base,n in ((OWNER-32,160),(MOTION-16,64),(OUTPUT-32,448),(CONST,80),(MARK,32),(DT,4),(SELECT,4)):
        m.update({base+i:(i*13+c.seed*11+0x53)&255 for i in range(n)})
    m[OWNER+12]=(c.seed*37)&255;m[OWNER+1]=(c.seed*19+128)&255;m[OWNER+17]=18;m[OWNER+16]=255
    put(m,OWNER+0x28,c.accumulator);put(m,DT,c.dt);put(m,SELECT,(0x80000000+c.seed)&0xffffffff)
    for i,v in enumerate(coefficients()):put(m,CONST+4*i,v)
    x,z=((0.,0.),(1500.,500.),(2000.,-1500.))[c.motion]
    put(m,MOTION,bits(x));put(m,MOTION+8,bits(z));put(m,STACK+c.phase,OWNER)
    return m

def random_float(c,n):return bits((0.,.25,.5,.75,1.,-.5)[(c.seed+n)%6])
def random_integer(c,n):return (0,0x80000000,0xffffffff,150,151,155,156,0x7fffffff)[(c.seed+n)%8]
def result(c,t,n):
    if t==RANDF:return random_float(c,n)
    if t==RANDI:return random_integer(c,n)
    if t==ANGLE:return bits(.125*(1+n))
    if t==DIFF:return bits(.2 if c.policy==0 or c.policy==2 and n%2==0 else .6)
    if t==COS:return bits(.75 if n%2==0 else -.5)
    if t==SIN:return bits(.25 if n%2==0 else -.75)
    if t==LOOKUP:return MOTION
    if t==EMIT:return OUTPUT if c.outcome else 0
    raise AssertionError(hex(t))

def effect(m,c,t,n):
    put(m,MARK,(0x13579bdf+t+n*0x10203)&0xffffffff)
    if not c.mutation:return
    if t==RANDF:put(m,SELECT,read(m,SELECT)^0x55)
    if t==ANGLE:
        put(m,MOTION,bits(2000.+n*100.));put(m,MOTION+8,bits(-1000.-n*50.))
    if t==DIFF and n==0:put(m,OWNER+0x28,bits(3.25))
    if t==EMIT:
        put(m,OWNER+0x28,sub(read(m,OWNER+0x28),bits(.25)))
        m[OWNER+12]^=0x55;m[OWNER+1]^=0xa3
    if t in (ANGLE,DIFF,POLAR,EMIT):
        for i,v in enumerate(coefficients()[3:],3):put(m,CONST+4*i,mul(v,bits(.75 if n%2==0 else 1.25)))

def reference(initial,c):
    m=dict(initial);calls=[];observed=[];copies=[];counts={};packet={i:0 for i in range(72)}
    def call(t,*args):
        n=counts.get(t,0);counts[t]=n+1;calls.append((t,tuple(args)));effect(m,c,t,n)
        return result(c,t,n)
    def constant(off):return read(m,CONST+off)
    sample=call(RANDF)
    amount=mul(mul(mul(sample,bits(20.)),constant(0)),read(m,DT))
    put(m,OWNER+0x28,add(read(m,OWNER+0x28),mul(amount,constant(4))))
    if lt(bits(1.),read(m,OWNER+0x28)):
        call(LOOKUP,read(m,SELECT))
        x,z=read(m,MOTION),read(m,MOTION+8)
        speed=add(mul(x,x),mul(z,z))
        if lt(constant(8),speed):
            for off,v in ((4,bits(-390.)),(0x40,constant(12)),(0x44,constant(16)),(0x3c,0),(0x30,4)):put(packet,off,v)
            angleLimit,headingBase,headingScale,effectScale=(constant(i) for i in (20,24,28,32))
            for off,v in ((0x20,0x6231),(0x22,0x1a4d),(0x2a,1)):put(packet,off,v,2)
            for off,v in ((0x29,255),(0x2d,255),(0x2e,20),(0x2f,1),(0x34,25)):packet[off]=v
            loops=0
            while True:
                loops+=1;assert loops<32,'Unbounded fixture'
                heading=add(mul(call(RANDF),headingScale),headingBase)
                angle=call(ANGLE,read(m,MOTION),read(m,MOTION+8))
                distance=call(DIFF,angle,heading)
                if lt(distance,angleLimit):
                    radius=add(mul(call(RANDF),constant(36)),constant(40))
                    # The actual polar helper calls cosine then sine, stores X
                    # from sine, and stores Z from its saved cosine result.
                    call_index=counts.get(POLAR,0);counts[POLAR]=call_index+1
                    calls.append((POLAR,(heading,radius,0,8)));effect(m,c,POLAR,call_index)
                    cosine=call(COS,heading);sine=call(SIN,heading)
                    put(packet,0,mul(radius,sine));put(packet,8,mul(radius,cosine))
                    scale1=mul(add(mul(call(RANDF),constant(44)),constant(48)),effectScale)
                    sample2=call(RANDF)
                    put(packet,0xc,mul(constant(52),scale1));put(packet,0x14,mul(constant(56),scale1))
                    scale2=mul(add(mul(sample2,constant(60)),constant(64)),effectScale)
                    for off,k in ((0x10,68),(0x18,72),(0x1c,76)):put(packet,off,mul(constant(k),scale2))
                    put(packet,0x24,call(RANDI)%151+50,2)
                    put(packet,0x38,mul(mul(call(RANDF),bits(500.)),effectScale))
                    packet[0x2c]=(call(RANDI)%156+100)&255
                    args=(0,10,1,0,m[OWNER+12],m[OWNER+1]);observed.append((packet_bytes(packet,0),args))
                    created=call(EMIT,*args)
                    if created:
                        calls.append((COPY,(created+0x160,0,4)));copies.append((heading,created+0x160,4))
                        put(m,created+0x160,heading)
                put(m,OWNER+0x28,sub(read(m,OWNER+0x28),bits(1.)))
                if not lt(bits(1.),read(m,OWNER+0x28)):break
        else:
            while True:
                put(m,OWNER+0x28,sub(read(m,OWNER+0x28),bits(1.)))
                if not lt(bits(1.),read(m,OWNER+0x28)):break
    return public(m),calls,observed,copies

def helper_code():
    code={}
    for entry,offset,n in ((POLAR,0x170bec,22),(COPY,0x22ec0,11)):
        code.update(zip(range(entry,entry+n*4,4),struct.unpack_from('>%dI'%n,rom(),offset)))
    return code

class Oracle(FactoryOracle):
    def __init__(self,words,initial,c,entry=s.ENTRY,connected=None):
        code=helper_code();code.update(connected or {})
        super().__init__(words,initial,c,entry=entry,arguments=(OWNER,),connected=code)
        self.before_f=self.f[:];self.observed=[];self.copies=[];self.counts={};self.target_entries=[]
    def execute(self,w):
        if w>>26==17 and w>>21&31==16 and w&63 in (0,1,2):self.f[w>>6&31]=fp(self.f[w>>11&31],self.f[w>>16&31],('add','sub','mul')[w&63])
        else:super().execute(w)
    def record_call(self,t):
        if t==s.ENTRY:
            assert self.r[4]==OWNER;self.target_entries.append(t);return
        if t in (RANDF,RANDI):a=()
        elif t==LOOKUP:a=(self.r[4],)
        elif t in (ANGLE,DIFF):a=(self.f[12],self.f[14])
        elif t in (COS,SIN):a=(self.f[12],)
        elif t==POLAR:
            a=(self.f[12],self.f[14],0,8)
            assert self.r[7]==self.r[6]+8 and self.r[29]<=self.r[6]<STACK
        elif t==EMIT:
            raw=tuple(self.arguments(6));assert self.r[29]<=raw[0]<STACK and raw[0]+72<=STACK+self.case.phase
            a=(0,*raw[1:]);self.observed.append((packet_bytes(self.memory,raw[0]),a))
        elif t==COPY:
            a=tuple(self.arguments(3));assert a[2]==4
            self.copies.append((read(self.memory,a[1]),a[0],4));a=(a[0],0,4)
        else:raise AssertionError(hex(t))
        self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        assert t not in (POLAR,COPY),'Helpers must execute original instructions'
        n=self.counts.get(t,0);self.counts[t]=n+1;effect(self.memory,self.case,t,n);value=result(self.case,t,n)
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi=self.lo=0xa5000000
        if t in (RANDF,ANGLE,DIFF,COS,SIN):self.f[0]=value
        else:self.r[2]=value
    def run(self):
        # POLAR is connected, so its entry effects must occur before its own
        # cosine/sine providers. A code-fetch wrapper fires that boundary.
        base=self.code;outer=self
        class Code(dict):
            def __getitem__(self,pc):
                if pc==POLAR:
                    n=outer.counts.get(POLAR,0);outer.counts[POLAR]=n+1;effect(outer.memory,outer.case,POLAR,n)
                return base[pc]
        self.code=Code(base)
        return super().run()

def verify(m,initial,c):
    expected,calls,observed,copies=reference(initial,c)
    assert public(m.memory)==expected,(c,'memory',[(hex(a),v,expected.get(a)) for a,v in public(m.memory).items() if expected.get(a)!=v][:12])
    assert m.calls==calls,(c,'calls',m.calls,calls)
    assert m.observed==observed,(c,'packets',m.observed,observed)
    assert m.copies==copies,(c,'copies',m.copies,copies)
    assert m.r[16:24]==m.before[16:24] and m.r[28:31]==m.before[28:31] and m.f[20:]==m.before_f[20:]

def main():
    programs=s.programs();seen=[set(),set()];n=emissions=copied=0;shapes=set()
    for c in cases():
        initial=fixture(c);expected,calls,observed,copies=reference(initial,c)
        for i,words in enumerate(programs):
            m=Oracle(words,initial,c);m.run();verify(m,initial,c);seen[i].update(m.visits)
        emissions+=len(observed);copied+=len(copies);shapes.add((len(observed),len(copies)));n+=1
    controls=0
    for old,new in ((0x24150097,0x24150096),(0x2416009c,0x2416009b),(0x240c0019,0x240c0018),(0x9279000c,0x9279000b)):
        words=programs[0][:];assert words.count(old)==1;words[words.index(old)]=new
        c=Case(seed=6);initial=fixture(c)
        try:m=Oracle(words,initial,c);m.run();verify(m,initial,c)
        except AssertionError:controls+=1
        else:raise AssertionError('Ineffective instruction control: '+hex(old))
    assert [len(v&set(range(s.ENTRY,s.ENTRY+4*len(w),4))) for v,w in zip(seen,programs)]==[241,len(programs[1])]
    assert set(helper_code())<=seen[0] and set(helper_code())<=seen[1]
    report=dict(finite_cases=n,streams=2,emissions=emissions,copies=copied,observed_shapes=sorted(shapes),target_words_visited=[len(v&set(range(s.ENTRY,s.ENTRY+4*len(w),4))) for v,w in zip(seen,programs)],polar_original_words=len(set(range(POLAR,POLAR+88,4))&seen[0]),copy_original_words=len(set(range(COPY,COPY+44,4))&seen[0]),instruction_controls=controls,unreachable_retail_words=2,packet_defined_bytes=69,packet_padding_bytes_uncredited=3,private_uninstalled=True,physical_stack_not_credited=True,exceptional_fp_fcsr_not_claimed=True)
    (s.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
