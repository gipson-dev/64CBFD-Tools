"""Byte oscillators, live float fields and explicit opaque/helper boundaries."""
from dataclasses import dataclass
import itertools,math,struct
from tools.experiments import game_phase_motion_candidates as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.test_game_point_transform_match import put,read
from tools.tests import test_game_trig_match as trig
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object

OWNER,WORKSPACE,MARK=0x30000,0x60000,0x70000
LOOKUP,WRAP,SINE=0x151423D8,0x15144B68,0x15047D60
FIELDS=(0x38,0x3C,0x4C,0x50,0x54,0xA8,0xAC,0xB0,0xB4,0xB8,0xBC,0xC0,0xC4,0xC8)
FLOAT_FIELDS=tuple(x for x in FIELDS if x!=0xAC)
FP=(0,0x80000000,0x3F800000,0xBF800000,0x3F000000,0xC0200000,1,0x00800000,0x3EAAAAAB,0x41200000)
TICKS=(0,1,2,0x7FFFFFFF,0x80000000,0xFFFFFFFF)
SAMPLES=(0,0x80000000,0x3F800000,0xBF800000,0x3F000000,0xBE800000,0x3E000000,0x3F400000)
u32=lambda x:x&0xFFFFFFFF
s8=lambda x:((x&255)^128)-128
add=lambda a,b:bits(floating(a)+floating(b))
mul=lambda a,b:bits(floating(a)*floating(b))

@dataclass(frozen=True)
class Case:
    index:int=0
    ticks:int=1
    phase:int=0
    mode:int=0

def symbols():
    return dict(D_800BE9E4=0x800BE9E4,D_800BE9A4=0x800BE9A4,
                func_151423D8=LOOKUP,func_15144B68=WRAP,sinf=SINE)

def fixture(c=Case(),s=None):
    s=symbols()if s is None else s
    m={STACK+c.phase+i:(i*17+c.index+165)&255 for i in range(-512,512)}
    for p,n in((OWNER-16,288),(WORKSPACE-16,96),(MARK,4)):
        m.update({p+i:(i*29+c.index*13+89)&255 for i in range(n)})
    for i,off in enumerate(FLOAT_FIELDS):put(m,OWNER+off,FP[(c.index+i*3)%len(FP)])
    for off,value in((0xAC,c.index),(0xAD,c.index*73+19),(0xAE,c.index*37+128),(0xAF,c.index*109+255)):
        m[OWNER+off]=value&255
    put(m,s['D_800BE9E4'],c.ticks);put(m,s['D_800BE9A4'],FP[(c.index+4)%len(FP)])
    put(m,MARK,0)
    return m

def observe(m,s):
    return tuple(read(m,OWNER+off)for off in FIELDS)+(read(m,s['D_800BE9E4']),read(m,s['D_800BE9A4']))

def effect(m,c,s,ordinal):
    put(m,MARK,ordinal+1)
    if ordinal==0 and c.mode&1:
        m[OWNER+0xAD]^=0x55;m[OWNER+0xAC]^=0xAA
        for off,v in((0xA8,-2.5),(0xB0,.25),(0xB4,-4.),(0xC8,.5)):put(m,OWNER+off,bits(v))
        put(m,s['D_800BE9A4'],bits(.25))
    if ordinal==1 and c.mode&2:
        for off,v in((0xA8,1.25),(0xB0,-.5),(0xB4,3.),(0xC4,-1.25),(0xC8,-.25)):put(m,OWNER+off,bits(v))
        put(m,s['D_800BE9A4'],bits(.5));put(m,s['D_800BE9E4'],0x87654321)
    if ordinal==2 and c.mode&4:
        for off,v in((0xC4,-9.),(0xC8,7.5),(0xB8,2.),(0xBC,-3.),(0xC0,.125)):put(m,OWNER+off,bits(v))
    if ordinal==3 and c.mode&4:
        for off,v in((0xC4,-3.),(0xB8,-1.5),(0xBC,.25),(0xC0,2.)):put(m,OWNER+off,bits(v))

def provider(c,ordinal):
    if ordinal==2:return bits((c.index%7-3)*.25)
    return SAMPLES[(c.index+ordinal*3)%len(SAMPLES)]

def lookup_reference(argument,table):
    a=argument&255;i=64-(a&63)if a&64 else a&63
    return table[i]^(0 if a&0xC0 in(0,0xC0)else 0x80000000)

def wrap_reference(word,period):
    assert math.isfinite(floating(word))and 0<floating(period)
    steps=0
    while floating(word)>floating(period):
        word=bits(floating(word)-floating(period));steps+=1;assert steps<1024
    while floating(word)<0:
        word=bits(floating(word)+floating(period));steps+=1;assert steps<1024
    return word

def reference(initial,c=Case(),s=None,actual=None):
    s=symbols()if s is None else s;m=dict(initial);calls=[];snapshots=[]
    # The second clock read follows the first byte store, including guest aliases.
    first=m[OWNER+0xAC]+s8(m[OWNER+0xAE])*read(m,s['D_800BE9E4'])
    second_phase=m[OWNER+0xAD];second_speed=s8(m[OWNER+0xAF])
    m[OWNER+0xAC]=first&255
    m[OWNER+0xAD]=(second_phase+second_speed*read(m,s['D_800BE9E4']))&255
    def call(name,arg):
        ordinal=len(calls);calls.append((s[name],(u32(arg),)));snapshots.append(observe(m,s))
        if actual is None:
            answer=provider(c,ordinal);effect(m,c,s,ordinal);return answer
        if ordinal<2:return lookup_reference(arg,actual['table'])
        if ordinal==2:return wrap_reference(arg,actual['period'])
        return trig.reference(arg)
    x=call('func_151423D8',(first-64)&255)
    y=call('func_151423D8',(m[OWNER+0xAD]-64)&255)
    put(m,OWNER+0x38,add(read(m,OWNER+0xA8),mul(read(m,OWNER+0xB0),x)))
    put(m,OWNER+0x3C,add(read(m,OWNER+0xA8),mul(read(m,OWNER+0xB4),y)))
    phase=add(read(m,OWNER+0xC4),mul(read(m,OWNER+0xC8),read(m,s['D_800BE9A4'])))
    put(m,OWNER+0xC4,phase);phase=call('func_15144B68',phase);put(m,OWNER+0xC4,phase)
    value=call('sinf',phase)
    for off,scale in((0x4C,0xB8),(0x50,0xBC),(0x54,0xC0)):put(m,OWNER+off,mul(read(m,OWNER+scale),value))
    return m,calls,1,snapshots

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=source.ENTRY,connected=None,arguments=None):
        self.c,self.s=c,symbols()if s is None else s;self.snapshots=[]
        super().__init__(words,memory,c,entry=entry,s={},connected=connected,arguments=(OWNER,WORKSPACE)if arguments is None else arguments)
        self.before_f=self.f[:]
    def execute(self,w):
        op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        if op==0 and fn==3:self.r[rd]=u32(signed(self.r[rt])>>fd)
        elif op==17 and rs==16 and fn==7:self.f[fd]=self.f[rd]^0x80000000
        elif op==17 and rs==16 and fn==13:self.f[fd]=u32(math.trunc(floating(self.f[rd])))
        elif op==17 and rs==16 and fn==50:self.condition=floating(self.f[rd])==floating(self.f[rt])
        else:super().execute(w)
        self.r[0]=0
    def record_call(self,t):
        if t==source.ENTRY:a=tuple(self.arguments(2))
        else:
            assert t in(self.s['func_151423D8'],self.s['func_15144B68'],self.s['sinf']),hex(t)
            a=(self.r[4],)if t==self.s['func_151423D8']else(self.f[12],)
            self.snapshots.append(observe(self.memory,self.s))
        self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        ordinal=len(self.snapshots)-1;assert 0<=ordinal<4
        answer=provider(self.c,ordinal);effect(self.memory,self.c,self.s,ordinal)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
        self.r[2]=0xDEADBEEF;self.f[0]=answer

def public(m,c):
    return{a:v for a,v in m.items()if not STACK+c.phase-512<=a<STACK+c.phase+512}

def payload(obj):
    t,fs,rs=parse_object(obj);f=fs[source.FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:v for p,v in rs.items()if a<=p<a+n}

def bound(obj,s=None):return bound_blob(*payload(obj),symbols()if s is None else s)

def cases():
    for i,phase,mode in itertools.product(range(256),(0,8),(0,1,2,7)):
        yield Case(i,TICKS[i%len(TICKS)],phase,mode)
    for i,ticks,phase,mode in itertools.product((0,1,127,128,255),TICKS,(0,8),(0,7)):
        yield Case(i,ticks,phase,mode)

def controls():
    b=source.SELECTED
    return dict(narrow_velocity=b.replace('(u32)(s32)*(s8 *)(owner + 0xAE)','(u32)(owner[0xAE] & 127)').replace('(u32)(s32)*(s8 *)(owner + 0xAF)','(u32)(owner[0xAF] & 127)'),
        wrong_ticks=b.replace('(u32)D_800BE9E4','((u32)D_800BE9E4 + 1u)'),
        wrong_phase_bias=b.replace('motion->firstPhase - 64','motion->firstPhase - 63'),
        cached_second_phase=b.replace('    f32 first;','    f32 first;\n    u8 savedPhase = owner[0xAD];').replace('motion->secondPhase - 64','savedPhase - 64'),
        wrong_time_scale=b.replace('motion->rate * D_800BE9A4','motion->rate * 1.0f'),
        ignored_wrapped_phase=b.replace('motion->phase = func_15144B68(motion->phase);','(void)func_15144B68(motion->phase);'),
        wrong_last_scale=b.replace('motion->scale[2] * scale','motion->scale[0] * scale'),
        false_return=b.replace('return 1;','return 0;'))
