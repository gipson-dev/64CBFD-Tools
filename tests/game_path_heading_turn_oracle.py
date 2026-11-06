"""Path heading/turn contracts, mutable providers and bounded original helpers."""
from dataclasses import dataclass
import itertools,math,struct
from tools.experiments import game_path_heading_turn_match as source
from tools.experiments import game_path_heading_turn_roles as roles
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests import test_game_turn_animation_select_match as turn
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
ACTOR,OTHER,TABLE,NODES,SCRIPT,MARK=0x30000,0x40000,0x50000,0x60000,0x70000,0x80000
QUERY,TURN,ATAN,DISPATCH=0x1505A630,0x15056A00,0x150484A0,0x80086730
u32=lambda n:n&0xFFFFFFFF
half=lambda n:((n&65535)^32768)-32768

@dataclass(frozen=True)
class Case:
    index:int=1
    mode:int=1
    current:int=0
    angle:int=0x1234
    threshold:int=3
    mutation:int=0
    phase:int=0
    alias:int=0
    pattern:int=0
    fcsr:int=0xA5A50003
    query_float:int=0x3F000000

def symbols():
    return dict(D_800D154C=0x800D154C,D_800D2104=0x800D2104,D_800D1890=0x800D1890,D_800D1891=0x800D1891,D_80099A3C=0x80099A3C,func_1505A630=QUERY,func_15056A00=TURN)

def actor(c):return STACK+c.phase-40+30-0x78 if c.alias==1 else ACTOR

def fixture(c=Case(),s=None):
    s=symbols() if s is None else s;m={STACK+c.phase+i:(i*17+165)&255 for i in range(-0x600,0x600)}
    for a in{ACTOR,OTHER,actor(c)}:
        m.update({a+i:(i*13+89)&255 for i in range(0x340)})
        m[a+0x13F]=c.index&255;m[a+0x21E]=(c.index*7)&255
        put(m,a+0x14,bits((0.,1.25,-17.5,32768.)[c.pattern%4]));put(m,a+0x1C,bits((0.,-1.5,19.25,-32768.)[c.pattern%4]))
        put(m,a+0x76,c.current,2);put(m,a+0x78,0xA55A,2);put(m,a+0x218,SCRIPT)
    m.update({s['D_80099A3C']+i:(i*29+55)&255 for i in range(2560)})
    for row in range(256):m[s['D_80099A3C']+row*10]=c.threshold&255
    m.update({TABLE+i:0 for i in range(1024)})
    for group in range(256):put(m,TABLE+group*4,NODES)
    m.update({NODES+i:(i*19+21)&255 for i in range(2064)})
    n=NODES+((c.index*7)&255)*8+8
    put(m,n,(-32768,-1,0,32767)[c.pattern%4],2);put(m,n+4,(32767,0,-1,-32768)[c.pattern%4],2)
    put(m,s['D_800D154C'],actor(c));put(m,s['D_800D2104'],TABLE);m[s['D_800D1890']]=c.mode&255;m[s['D_800D1891']]=173
    m.update({SCRIPT+i:(i*7+157)&255 for i in range(64)});put(m,MARK,0);put(m,0x800994D8,bits(1.0))
    return m

def poison_homes(m,sp):
    for i in range(4):put(m,sp+i*4,0xB5000000+i)

def query_effect(m,c,s,root_sp):
    if c.mutation&1:put(m,s['D_800D154C'],OTHER)
    if c.mutation&2:
        m[s['D_800D1890']]=(c.mode^167)&255;m[s['D_800D1891']]=37
        m[s['D_80099A3C']+((c.mode-1)&255)*10]=(c.threshold^129)&255
    if c.mutation&4:
        a=read(m,s['D_800D154C']);put(m,a+0x76,c.current^0x8000,2);put(m,a+0x14,0x7FC12345)
    if c.mutation&8:m[root_sp+30]=213
    put(m,MARK,0xCA110000|c.mutation)

def turn_effect(m,a):
    put(m,MARK+4,0x7A110000|a[1]);m[a[0]+0x244]=a[2]&255

def query_answer(c):
    value=floating(c.query_float)
    integer=math.trunc(value) if math.isfinite(value) else -1
    converted=integer if 0<=integer<2**32 else 0xFFFFFFFF
    return (converted+0x4000)&65535

def reference(initial,c,s=None,ra=0,query_return=source.ENTRY+0x7C,connected_query=False,connected_turn=False):
    s=symbols() if s is None else s;m=dict(initial);sp=STACK+c.phase-40
    put(m,sp+20,ra);a=read(m,s['D_800D154C']);group=m[a+0x13F];entry=m[a+0x21E]
    p=read(m,read(m,s['D_800D2104'])+group*4)+entry*8+8
    x=fp(bits(float(half(read(m,p,2)))),read(m,a+0x14),'sub');z=fp(read(m,a+0x1C),bits(float(half(read(m,p+4,2)))),'sub')
    row=(m[s['D_800D1890']]-1)&255;m[sp+30]=row;calls=[(s['func_1505A630'],(x,z,0))]
    if connected_query:
        put(m,sp-4,query_return);put(m,sp,x);put(m,sp+8,0)
        calls.append((ATAN,(x^0x80000000,z)));query_effect(m,c,s,sp);poison_homes(m,sp-24);value=query_answer(c)
    else:query_effect(m,c,s,sp);poison_homes(m,sp);value=c.angle
    a=read(m,s['D_800D154C']);row=m[sp+30];put(m,a+0x78,value,2)
    a=read(m,s['D_800D154C']);delta=(read(m,a+0x78,2)-read(m,a+0x76,2))&65535
    # Independent circular-byte formula, including the retained 128 tie.
    high=delta//256;distance=min(high,256-high)
    if m[s['D_80099A3C']+row*10]<distance:
        m[a+0x250]=m[s['D_800D1891']];a=read(m,s['D_800D154C']);args=(a,distance,row);calls.append((s['func_15056A00'],args))
        if connected_turn:m=turn.reference(m,turn.Case(),table=s['D_80099A3C'],raw_arguments=args,sp=sp)
        else:turn_effect(m,args);poison_homes(m,sp)
    return m,calls

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),s=None,entry=source.ENTRY,connected=None):
        self.c,self.s=c,symbols() if s is None else s
        super().__init__(words,memory,c,entry=entry,s={},connected=connected,arguments=())
        self.before_f=self.f[:];self.fcsr=self.initial_fcsr=c.fcsr;self.poison=0;self.poison_hits=0
    def execute(self,w):
        op,fmt,fn=w>>26,w>>21&31,w&63
        if op==17 and (fmt in(2,6) or fmt==16 and fn in(7,36)):AreaOracle.execute(self,w)
        elif op==17 and fmt==16 and fn==2:
            self.f[w>>6&31]=bits(floating(self.f[w>>11&31])*floating(self.f[w>>16&31]));self.r[0]=0
        else:super().execute(w)
    def record_call(self,t):
        if t==source.ENTRY:a=()
        elif t==self.s['func_1505A630']:a=(self.f[12],self.f[14],self.r[6])
        elif t==ATAN:a=(self.f[12],self.f[14])
        else:
            assert t==self.s['func_15056A00'],hex(t);a=tuple(self.arguments(3))
        self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        sp=self.target_home-40
        if t in(self.s['func_1505A630'],ATAN):query_effect(self.memory,self.c,self.s,sp)
        else:assert t==self.s['func_15056A00'];turn_effect(self.memory,self.calls[-1][1])
        poison_homes(self.memory,self.r[29])
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
        if t==ATAN:self.f[0]=self.c.query_float
        else:self.r[2]=u32(self.c.angle if t==self.s['func_1505A630'] else 0xDEADBEEF)

def bound(obj,s=None):
    raw,b=source.function_blob(obj);return roles.bound_blob(raw,b,symbols() if s is None else s)

def helper_code(rom,query=False,turning=False):
    code={}
    for use,entry,offset,count in((query,QUERY,0x87AE0,50),(turning,TURN,0x83EB0,66)):
        if use:code.update(zip(range(entry,entry+count*4,4),struct.unpack_from('>%dI'%count,rom,offset)))
    return code

class PoisonCode(WindowCode):
    def __getitem__(self,pc):
        if pc==0x1507BD68:self.owner.r[2]=self.owner.poison;self.owner.poison_hits+=1
        return super().__getitem__(pc)

def cases():
    for i,mode,current,angle,threshold,mutation,phase in itertools.product(range(2),(0,1,128,255),(0,0xFF00),(0,0x100,0x7FFF,0x8000,0xFF00),(0,127,128),(0,7),(0,8)):
        yield Case(i,mode,current,angle,threshold,mutation,phase,pattern=(i+mode)%4)
    for v in range(256):yield Case(v,v,((v*257)^0x7FFF)&65535,(v*263)&65535,v,7,pattern=v%4)

def controls():
    b=source.candidate.SELECTED
    return dict(unsigned_x=b.replace('node[1].x','(u16)node[1].x'),unsigned_z=b.replace('node[1].z','(u16)node[1].z'),
        wrong_entry=b.replace('node[1]','node[0]'),wrong_mode=b.replace('D_800D1890 - 1','D_800D1890'),
        doubled_stride=b.replace('row * 10','row * 20'),inclusive=b.replace('threshold < distance','threshold <= distance'),
        wrong_sign=b.replace('distance & 0x80','distance & 0x40'),missing_fold=b.replace('magnitude = distance = -distance & 0xFF;','magnitude = distance;'),
        wrong_shift=b.replace('>> 8','>> 7'),wrong_output=b.replace('->unk250','->unk24F'),wrong_notice=b.replace('= D_800D1891;','= D_800D1890;'),
        lost_snapshot=b.replace('magnitude, row);','magnitude, D_800D1890 - 1);'),
        cached_actor=b.replace('    f32 x;','    struct127 *actor = D_800D154C;\n    f32 x;').replace('D_800D154C->','actor->').replace('func_15056A00(D_800D154C,','func_15056A00(actor,'))
