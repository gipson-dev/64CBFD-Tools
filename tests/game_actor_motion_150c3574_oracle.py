"""Private finite-domain comparison with explicit helper mutation contracts.

This is not a whole-caller, hardware-FCSR, or production match claim.
"""
from dataclasses import dataclass,replace
from collections import Counter
from functools import lru_cache
import hashlib,json,math,struct
from tools.experiments import game_actor_motion_150c3574_recovery as s
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read

OWNER,MARK=0x30040,0x70000
COEFF=(0x800A0320,0x800A0324,0x800A0328,0x800A032C,0x800A0330)
DT,SOUND,CURRENT,OBJECTS=0x800BE9A8,0x800D1580,0x800D154C,0x800CC2D0
APPROACH,DECEL,PREPARE,STUN,MOVE,SPECIAL,ANGLE,TURN,ANIMATE,STOP,PLAYING,PLAY,VOLUME=(
    0x1505A250,0x1505A3A8,0x15056B08,0x150562FC,0x15059140,0x1506E8D8,
    0x1505A630,0x150599C8,0x15052490,0x100109D0,0x100107F8,0x1506E5FC,0x1001091C)
FLOATS=(0x14,0x18,0x1C,0x24,0x28,0x2C,0x34,0x3C,0x44,0xBC,0x148,0x14C,0x164,0x168)
HALVES=(0x78,0x7A,0x160,0x224)
add=lambda a,b:fp(a,b,'add')
sub=lambda a,b:fp(a,b,'sub')
mul=lambda a,b:fp(a,b,'mul')
lt=lambda a,b:floating(a)<floating(b)

@dataclass(frozen=True)
class Case:
    seed:int=0
    mutation:int=0
    phase:int=0
    kind:int=0x25
    flags:int=4
    stunned:int=0
    playing:int=0
    pattern:int=3
    timer:int=0

def cases():
    for i in range(1536):
        yield Case(i,i%3,(i%2)*8,(0x10,0x25,0xAC,0xFF)[i%4],
            (0,1,4,0x80,0xFF)[i%5],i//4%2,i//8%2,i//16%8,i//128%3)

@lru_cache(maxsize=1)
def coefficients():
    rom=(s.OUT/'production-baseline/conker/conker.us.bin').read_bytes()
    return struct.unpack_from('>5I',rom,0x244DE0)

def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-1024,1024)}
    for base,n in ((OWNER-32,0x280),(MARK,4),(DT,4),(SOUND,4),(CURRENT,4)):
        m.update({base+i:(i*13+c.seed*11+0x53)&255 for i in range(n)})
    for p,value in zip(COEFF,coefficients()):put(m,p,value)
    put(m,OWNER,24);m[OWNER+4]=c.kind;m[OWNER+0x87]=c.flags;m[OWNER+0x13D]=c.stunned
    dx=(0.,.125,.25,.5,.5000000596046448,1.,3.,16.)[c.pattern]
    vals={0x14:dx,0x18:-327.75,0x1C:0.,0x24:9.,0x28:(29.999998,30.,30.000002)[c.timer],
        0x2C:0.,0x34:0.,0x3C:(0.,9.,100.)[c.seed%3],
        0x44:(0.,.19999999,.2,11.2,20.)[c.seed%5],0xBC:19.,0x148:23.,
        0x14C:(0.,1.,2.,-1.)[c.seed%4],0x164:5.,0x168:-6.}
    for off,v in vals.items():put(m,OWNER+off,bits(v))
    for off,v in ((0x78,(0,0x3FFF,0x4000,0x7FFF,0x8000,0xFFFF)[c.seed%6]),
                  (0x7A,(0,0x4000,0x8000,0xFFFF)[c.seed//6%4]),(0x160,0x8765),(0x224,0x9876)):
        put(m,OWNER+off,v,2)
    put(m,DT,bits((.5,1.,2.)[c.seed//12%3]));put(m,SOUND,0x12345678);put(m,CURRENT,0x76543210);put(m,MARK,0)
    return m

def public(m):return {p:v for p,v in m.items() if not STACK-1024<=p<STACK+1024}

def effect(m,c,t,n):
    put(m,MARK,(0x13579BDF+t+n*0x10203)&0xFFFFFFFF)
    if not c.mutation:return
    if t==APPROACH:
        put(m,OWNER+0x164,bits(.75));put(m,OWNER+0x168,bits(-.5))
        if c.mutation==2:m[OWNER+0x87]^=1
    elif t==PREPARE and c.mutation==2:m[OWNER+4]=0x25
    elif t==MOVE and c.mutation==2:
        put(m,OWNER+0x14,bits(2.));put(m,OWNER+0x1C,bits(-3.));put(m,DT,bits(.5))
    elif t==SPECIAL:
        m[OWNER+0x87]=8;put(m,OWNER+0xBC,bits(7.));put(m,OWNER+0x148,bits(-9.))
    elif t==ANGLE and c.mutation==2:put(m,OWNER+0x7A,0x8000,2)
    elif t==TURN and c.mutation==2:
        put(m,OWNER+0x28,bits(31.));put(m,OWNER+0x44,bits(16.));m[OWNER+0x13D]^=1
    elif t==PLAYING and c.mutation==2:
        m[OWNER+4]=0x25;put(m,OWNER+0x44,bits(50.))
    elif t in (PLAY,VOLUME) and c.mutation==2:put(m,OWNER+0x44,bits(.1))
    elif t==STOP and c.mutation==2:put(m,OWNER+0x44,bits(.3))

def answer(c,t):
    if t==PLAYING:return c.playing
    if t==ANGLE:return (0,0x7FFF,0x8000,0xFFFF)[c.seed%4]
    return 0xD00D0000

def reference(initial,c):
    m=dict(initial);calls=[];counts=Counter()
    def call(t,*args):
        calls.append((t,tuple(v&0xFFFFFFFF for v in args)));n=counts[t];counts[t]+=1
        effect(m,c,t,n);return answer(c,t)
    def f(off):return read(m,OWNER+off)
    def store(off,v):put(m,OWNER+off,v)
    scale=bits(.5);decel=bits(.25);m[OWNER+0x80]=10
    if m[OWNER+4]==0x25:
        call(APPROACH,0,0,bits(.15),OWNER+0x164,OWNER+0x168)
        decel=read(m,COEFF[0])
        if m[OWNER+0x87]&1:put(m,OWNER+0x224,math.trunc(floating(f(0x18))),2)
        put(m,OWNER+0x160,0,2)
    call(DECEL,0,OWNER,bits(2.),decel,0);store(0x24,bits(3.))
    if m[OWNER+4]==0x10:scale=bits(.375)
    if m[OWNER+4]==0xAC:scale=bits(1.5)
    scale=mul(scale,bits(.75));call(PREPARE,OWNER)
    if m[OWNER+0x13D]:call(STUN,OWNER)
    call(MOVE,OWNER)
    store(0xBC,mul(sub(f(0x14),f(0x2C)),read(m,DT)))
    store(0x148,mul(sub(f(0x1C),f(0x34)),read(m,DT)))
    speed=bits(math.sqrt(floating(add(mul(f(0xBC),f(0xBC)),mul(f(0x148),f(0x148))))))
    plus=add(speed,bits(4.))
    if lt(add(plus,plus),f(0x3C)):store(0x3C,add(speed,speed))
    if m[OWNER+0x87]==4:
        put(m,SOUND,0xFF020133);put(m,CURRENT,OBJECTS);call(SPECIAL)
        put(m,CURRENT,OWNER);store(0x164,f(0xBC));store(0x168,f(0x148));store(0x3C,0)
    m[OWNER+0x87]=(m[OWNER+0x87]*2)&255
    if lt(bits(.5),speed) and not m[OWNER+0x13D]:
        value=call(ANGLE,sub(f(0x14),f(0x2C)),sub(f(0x34),f(0x1C)),0)
        put(m,OWNER+0x78,value,2)
    current=read(m,OWNER+0x78,2);desired=current
    if not ((read(m,OWNER+0x7A,2)-current-0x4000)&0x8000):desired^=0x8000
    call(TURN,OWNER,2,desired)
    store(0x44,mul(f(0x44),read(m,COEFF[1])) if lt(bits(30.),f(0x28)) else add(speed,speed))
    if m[OWNER+0x13D]:store(0x44,0)
    call(ANIMATE,OWNER,read(m,OWNER+0x78,2),f(0x44),mul(sub(bits(2.),f(0x14C)),scale))
    if lt(f(0x44),read(m,COEFF[2])):call(STOP,OWNER)
    elif not call(PLAYING,OWNER):
        put(m,SOUND,{0xAC:0x630,0x25:0x67A}.get(m[OWNER+4],0x62A));call(PLAY)
    else:
        volume=min(28000,math.trunc(floating(mul(f(0x44),read(m,COEFF[3])))))
        if m[OWNER+4]==0x25:volume>>=1
        call(VOLUME,OWNER,volume)
    if lt(f(0x44),read(m,COEFF[4])):call(STOP,OWNER)
    return public(m),calls

class Oracle(FactoryOracle):
    def __init__(self,words,m,c,entry=s.ENTRY,connected=None):
        super().__init__(words,m,c,entry=entry,arguments=(OWNER,),connected=connected)
        self.before_f=self.f[:];self.counts=Counter();self.entries=[]
    def execute(self,w):
        op,fmt,fn=w>>26,w>>21&31,w&63
        if op==17 and fmt==16 and fn in (0,1,2):
            self.f[w>>6&31]=fp(self.f[w>>11&31],self.f[w>>16&31],('add','sub','mul')[fn]);return
        if op==17 and fmt==16 and fn in (4,13):
            value=floating(self.f[w>>11&31])
            self.f[w>>6&31]=bits(math.sqrt(value)) if fn==4 else math.trunc(value)&0xFFFFFFFF
            return
        if op==14:
            self.r[w>>16&31]=self.r[w>>21&31]^(w&65535);self.r[0]=0;return
        return super().execute(w)
    def record_call(self,t):
        if t==s.ENTRY:self.entries.append(self.r[4]);return
        if t==APPROACH:a=(self.f[12],self.f[14],self.r[6],self.r[7],self.get(self.r[29]+16,4))
        elif t==DECEL:a=(self.f[12],self.r[5],self.r[6],self.r[7],self.get(self.r[29]+16,4))
        elif t==ANGLE:a=(self.f[12],self.f[14],self.r[6])
        elif t in (PREPARE,STUN,MOVE,STOP,PLAYING):a=(self.r[4],)
        elif t in (SPECIAL,PLAY):a=()
        elif t==TURN:a=tuple(self.arguments(3))
        elif t==ANIMATE:a=tuple(self.arguments(4))
        elif t==VOLUME:a=tuple(self.arguments(2))
        else:raise AssertionError(hex(t))
        self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        n=self.counts[t];self.counts[t]+=1;effect(self.memory,self.case,t,n)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi=self.lo=0xA5000000
        self.r[2]=answer(self.case,t)

def check(words,c):
    initial=fixture(c);expected,calls=reference(initial,c);m=Oracle(words,initial,c);m.run()
    assert public(m.memory)==expected,('memory',c,[(hex(p),expected[p],public(m.memory).get(p)) for p in expected if public(m.memory).get(p)!=expected[p]][:12])
    assert m.calls==calls,('calls',c,m.calls,calls)
    assert m.r[16:24]==m.before[16:24] and m.r[29]==m.before[29]
    assert m.f[20:]==m.before_f[20:]
    return m

def main():
    truth,raw=s.programs();coverage=Counter();visited=[set(),set()]
    for c in cases():
        for i,words in enumerate((truth,raw)):
            m=check(words,c);visited[i].update(m.visits)
            if not i:coverage.update(t for t,a in m.calls)
    # An effective behavioral mutation control: the state transition must double.
    broken=raw[:];idx=next(i for i,w in enumerate(broken) if w==0x00027040);broken[idx]=0x00027080
    try:check(broken,Case())
    except AssertionError:pass
    else:raise AssertionError('Ineffective mutation control')
    assert set(coverage)=={APPROACH,DECEL,PREPARE,STUN,MOVE,SPECIAL,ANGLE,TURN,ANIMATE,STOP,PLAYING,PLAY,VOLUME}
    report=dict(cases=1536,streams=2,finite_only=True,helper_contracts='modeled with mutations and o32 caller-save clobbers',
        frame=56,neighbors=17,coverage={hex(k):v for k,v in coverage.items()},effective_controls=1,
        visited_words=[len(v) for v in visited],
        installed=False,c_match_credit=0)
    (s.OUT/'oracle-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
