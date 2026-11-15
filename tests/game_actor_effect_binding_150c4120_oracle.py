"""Defined payload bytes with both original factories and original byte copying.

Seven copied C padding bytes are explicitly uncredited during this recovery.
"""
from dataclasses import dataclass
from collections import Counter
from functools import lru_cache
import hashlib,json,struct
from tools.experiments import game_actor_effect_binding_150c4120_recovery as s
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read

OWNER,FIRST,SECOND,MARK=0x30040,0x50040,0x60040,0x70000
FACTORY,EFFECT,ALLOC,ZERO,COPY,RI,RF=0x15149130,0x15130280,0x15167A68,0x100226F0,0x10022EC0,0x150ADA20,0x150ADA68
PALETTE,VECTOR,C1,C2,C3=0x800A0340,0x800A5480,0x800A03AC,0x800A03B0,0x800A03B4
LIFETIMES=(0xFFFFFFFF,0,1,32767,32768,65535,0x1234FFFF,0xABCD8000)
PRIORITIES=(0,1,0xABCDEF7F,0x123456FF)
u32=lambda x:x&0xFFFFFFFF
signed16=lambda x:((x&65535)^32768)-32768
data=lambda m,p,n:bytes(m[p+i] for i in range(n))
M32=(0,4,0xC,0x10,0x24,0x28,0x2C,*range(0x30,0x54,4),0x54,0x58,0x5C,0x6C)
M16=(8,0xA,0x1E,0x20,0x22,0x68)
DEF_PAD=(0x67,0x6A,0x6B);BIND_PAD=(5,6,7,0x17)

@dataclass(frozen=True)
class Case:
    seed:int=0
    outcome:int=3
    mutation:int=0
    phase:int=0
    lifetime:int|None=None
    priority:int|None=None
    context:int|None=None

def cases():
    for seed in range(32):
        for outcome in range(4):
            for mutation in (0,1):
                for phase in (0,8):yield Case(seed,outcome,mutation,phase)

def args(c):return (OWNER,LIFETIMES[c.seed%8] if c.lifetime is None else u32(c.lifetime),
    PRIORITIES[c.seed//2%4] if c.priority is None else u32(c.priority),
    u32(0x81234567+c.seed) if c.context is None else u32(c.context))

def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-2048,2048)}
    for p,n in ((OWNER-32,128),(FIRST-32,256),(SECOND-32,256),(MARK,4),(PALETTE,16),(VECTOR,12),(C1,12)):
        m.update({p+i:(i*13+c.seed*11+0x53)&255 for i in range(n)})
    m[OWNER+4]=(0x33,0x34,0x35)[c.seed//4%3];m[OWNER+0x3B]=(c.seed*41+7)&255
    for i,v in enumerate((0,15,255,0xDEADBEEF)):put(m,PALETTE+4*i,v)
    for i,v in enumerate((bits(.125),bits(-2.5),bits(13.25))):put(m,VECTOR+4*i,v)
    for p,v in ((C1,.5),(C2,.75),(C3,-.25)):put(m,p,bits(v))
    put(m,MARK,0);return m

def integer(c,n):return (0,0xFFFFFFFF,0x80000000,5,6,255,256)[(c.seed+n)%7]
def real(c,n):return bits((0.,.25,.5,1.,-.0,1.5)[(c.seed+n)%6])

def effect(m,c,t,n):
    put(m,MARK,u32(0x13579BDF+t+n*0x10203))
    if not c.mutation:return
    if t==ALLOC:
        m[OWNER+4]^=3;m[OWNER+0x3B]^=0x55
    if t==RI and n==0:
        for i in range(4):put(m,PALETTE+4*i,0xAA00+i)
    if t==RF:
        put(m,C1,bits(1.25+n));put(m,C2,bits(2.5+n))
    if t==RI and n in (4,5):
        for i in range(3):put(m,VECTOR+4*i,bits(float(10+n+i)))
        put(m,C3,bits(-3.5-n))

def initialized(m,c,p,n,count):
    for i in range(count):m[p+i]=(i*19+c.seed*7+n*23+0x31)&255

def allowed_padding(c):
    result=set()
    if c.outcome&1:result.update(FIRST+40+i for i in BIND_PAD)
    if c.outcome==3:result.update(SECOND+16+i for i in DEF_PAD)
    return result

def public(m,c):
    skip=allowed_padding(c)
    return {p:v for p,v in m.items() if not STACK-2048<=p<STACK+2048 and p not in skip}

def definition(m,c,ri,rf,palette):
    d={i:0 for i in range(112)}
    for i in DEF_PAD:d.pop(i)
    for at,v in ((0,0x200005),(0x58,0xC000|((ri[5]&1)*0x40)|((ri[6]&1)*0x80)),(0x24,bits(1.)),(0x28,bits(700.)),(0x2C,bits(700.)),(0x6C,read(m,C3))):put(d,at,v)
    for at,v in ((8,0x2203),(0xA,300),(0x1E,1),(0x20,255),(0x22,1)):put(d,at,v,2)
    for at in (0x17,0x1B,0x1C,0x66):d[at]=255
    d[0x1D]=palette[ri[4]&3]&255
    for at,v in ((0x60,6),(0x61,8),(0x62,0x26),(0x63,255),(0x64,255)):d[at]=v
    for at in (0x30,0x3C,0x48):
        for i,value in enumerate(rf['vector']):put(d,at+4*i,value)
    return d

def reference(initial,c):
    m=dict(initial);calls=[];counts=Counter();packets=[]
    def call(t,*a):
        calls.append((t,tuple(map(u32,a))));n=counts[t];counts[t]+=1
        if t in (ALLOC,ZERO,RI,RF):effect(m,c,t,n)
        return n
    lifetime=signed16(args(c)[1]);priority=args(c)[2]&255;context=args(c)[3]
    binding={i:0 for i in range(28) if i not in BIND_PAD}
    put(binding,0,OWNER);binding[4]=m[OWNER+0x3B]
    put(binding,0x14,0x54 if m[OWNER+4]==0x34 else 0xFFFF,2);binding[0x16]=int(m[OWNER+4]==0x34)
    call(FACTORY,300 if lifetime==-1 else lifetime,-1,83,-1,int(lifetime!=-1),64,28,priority,context)
    call(ALLOC,35,context,68,1,priority,1)
    if not c.outcome&1:return public(m,c),calls,packets
    initialized(m,c,FIRST,0,68)
    for off,v in ((13,int(lifetime!=-1)),(16,255),(17,83),(18,255),(19,64)):m[FIRST+off]=v
    put(m,FIRST+14,300 if lifetime==-1 else lifetime,2)
    call(ZERO,FIRST+20,16)
    for i in range(16):m[FIRST+20+i]=0
    call(COPY,FIRST+40,0,28)
    for i,b in binding.items():m[FIRST+40+i]=b
    packets.append(('binding',binding))
    palette=tuple(read(m,PALETTE+4*i) for i in range(4));ri=[];rf={}
    for i in range(4):call(RI);ri.append(integer(c,i))
    call(RF);h=fp(fp(fp(real(c,0),bits(.25),'mul'),read(m,C1),'add'),bits(700.),'mul')
    call(RF);v=fp(fp(fp(real(c,1),bits(.25),'mul'),read(m,C2),'add'),bits(700.),'mul')
    call(RI);ri.append(integer(c,4));rf['vector']=tuple(read(m,VECTOR+4*i) for i in range(3))
    call(RI);ri.append(integer(c,5));call(RI);ri.append(integer(c,6))
    d=definition(m,c,ri,rf,palette);extra={i:0 for i in range(16)}
    for i,vv in enumerate((ri[0]&255,ri[1]&255,ri[2]%6+5,ri[3]%6+5)):extra[i]=vv
    for at,vv in ((4,bits(700.)),(8,h),(12,v)):put(extra,at,vv)
    call(EFFECT,0,1,0,16,priority,context);packets.append(('definition',d))
    call(ALLOC,82,context,184,1,priority,1)
    if c.outcome==3:
        initialized(m,c,SECOND,1,184);call(COPY,SECOND+16,0,112)
        for i,b in d.items():m[SECOND+16+i]=b
        m[SECOND+0x9C]=0
    put(m,FIRST+52,SECOND if c.outcome==3 else 0)
    if c.outcome==3:
        call(COPY,SECOND+168,0,16)
        for i,b in extra.items():m[SECOND+168+i]=b
        packets.append(('random',extra))
    return public(m,c),calls,packets

@lru_cache(maxsize=1)
def helper_code():
    rom=(s.OUT/'production-baseline/conker/conker.us.bin').read_bytes();code={}
    for entry,offset,n in ((FACTORY,0x1765E0,49),(EFFECT,0x15D730,61),(COPY,0x22EC0,11)):
        code.update(zip(range(entry,entry+4*n,4),struct.unpack_from('>%dI'%n,rom,offset)))
    return code

class Oracle(FactoryOracle):
    def __init__(self,words,initial,c,entry=s.ENTRY,connected=None):
        code=dict(helper_code());code.update(connected or {})
        super().__init__(words,initial,c,entry=entry,arguments=args(c),connected=code)
        self.counts=Counter();self.packets=[];self.before_f=self.f[:];self.entries=[]
    def execute(self,w):
        if w>>26==0 and w&63==38:
            self.r[w>>11&31]=u32(self.r[w>>21&31]^self.r[w>>16&31]);self.r[0]=0;return
        if w>>26==17 and w>>21&31==16 and w&63 in (0,1,2):
            self.f[w>>6&31]=fp(self.f[w>>11&31],self.f[w>>16&31],('add','sub','mul')[w&63]);return
        return super().execute(w)
    def record_call(self,t):
        if t==s.ENTRY:self.entries.append(tuple(self.arguments(4)));return
        a=tuple(self.arguments({FACTORY:9,EFFECT:6,ALLOC:6,ZERO:2,COPY:3,RI:0,RF:0}[t]))
        if t==COPY:
            p,q,n=a;skip=BIND_PAD if n==28 else DEF_PAD if n==112 else ()
            self.packets.append(({28:'binding',112:'definition',16:'random'}[n],{i:self.memory[q+i] for i in range(n) if i not in skip}));a=(p,0,n)
        if t==EFFECT:
            self.packets.append(('definition',{i:self.memory[a[0]+i] for i in range(112) if i not in DEF_PAD}));a=(0,*a[1:])
        self.calls.append((t,tuple(map(u32,a))));self.events.append(('CALL',t,a))
    def hook(self,t):
        assert t in (ALLOC,ZERO,RI,RF),'Real factory/copy instructions must execute'
        n=self.counts[t];self.counts[t]+=1;effect(self.memory,self.case,t,n);answer=0xD00D0000
        if t==ALLOC:
            answer=FIRST if not n and self.case.outcome&1 else SECOND if n==1 and self.case.outcome==3 else 0
            if answer:initialized(self.memory,self.case,answer,n,68 if n==0 else 184)
        elif t==ZERO:
            p,count=self.calls[-1][1];assert count==16
            for i in range(count):self.memory[p+i]=0
        elif t==RI:answer=integer(self.case,n)
        elif t==RF:answer=real(self.case,n)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xA5000000
        if t==RF:self.f[0]=answer
        else:self.r[2]=u32(answer)

def check(words,c):
    initial=fixture(c);expected,calls,packets=reference(initial,c);m=Oracle(words,initial,c);m.run()
    assert public(m.memory,c)==expected,('memory',c,[(hex(p),v,public(m.memory,c).get(p)) for p,v in expected.items() if public(m.memory,c).get(p)!=v][:10])
    assert m.calls==calls,('calls',c,m.calls,calls)
    # The effect's definition is observed once at submission and again at its
    # real factory copy; compare the latter too without treating it as a draw.
    expected_packets=[]
    for kind,d in packets:
        expected_packets.append((kind,d))
        if kind=='definition' and c.outcome==3:expected_packets.append((kind,d))
    assert m.packets==expected_packets,('packet',c,m.packets,expected_packets)
    assert m.r[16:24]==m.before[16:24] and m.r[29]==m.before[29] and m.f[20:]==m.before_f[20:]
    return m

def main():
    programs=s.programs();visited=set();coverage=Counter();n=0
    for c in cases():
        for i,words in enumerate(programs):
            m=check(words,c)
            if not i:visited.update(m.visits);coverage.update(t for t,a in m.calls)
        n+=1
    assert {FACTORY,EFFECT,ALLOC,ZERO,COPY,RI,RF}==set(coverage)
    report=dict(cases=n,streams=2,original_factory_words=110,original_copy_words=11,visited_retail_words=sum(s.ENTRY<=v<s.ENTRY+s.SIZE for v in visited),
        binding_bytes=28,definition_bytes=112,random_bytes=16,defined_public_bytes_compared=True,padding_bytes_uncredited=7,
        coverage={hex(t):v for t,v in coverage.items()},finite_only=True,installed=False,c_match_credit=0)
    (s.OUT/'oracle-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
