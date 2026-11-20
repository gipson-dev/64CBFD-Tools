"""Map-burst reference, actual MIPS streams and bounded helper mutations."""
from dataclasses import dataclass
import itertools,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY,RECORD,TAIL,MARK=0x1510558C,0x30000,0x30110,0x70000
REAL,INTEGER,PRIMARY,POINT,BURST=0x150ADA68,0x150ADA20,0x15102920,0x151C329C,0x15151D6C
FIRST,SECOND,C0,C4,C8=0x800A23A4,0x800A23A8,0x800A23C0,0x800A23C4,0x800A23C8
PARAMETERS=tuple(range(0x800A23CC,0x800A23EC,4))
DEFINED=tuple(i for i in range(88)if i not in(0x32,0x33))
@dataclass(frozen=True)
class Case:
    tag:int=8
    integer:int=0xffffffff
    profile:int=0
    mutation:int=0
    phase:int=0
    seed:int=0
    rule:str='left'

def cases():
    for tag,integer,profile,phase in itertools.product((9,8,0x29,0xffffffff,0),(0,55,56,80,81,0x7fffffff,0x80000000,0xffffffff),range(4),(0,8)):
        yield Case(tag,integer,profile,phase=phase,seed=integer&3)
    for mutation,tag,profile,phase in itertools.product((1,2,4,8,15),(9,8),(0,1),(0,8)):
        yield Case(tag,0x80000000,profile,mutation,phase,mutation&3)
    for profile,tag,rule in itertools.product((4,5),(9,8),('left','right')):
        yield Case(tag,0xffffffff,profile,rule=rule)

def fixture(c):
    m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-768,256)}
    for base,n in((RECORD,0x1B0),(MARK,4)):m.update({base+i:(i*29+c.seed+0x5A)&255 for i in range(n)})
    m[RECORD+1]=0x18+c.seed;m[RECORD+0xC]=0xE1-c.seed;m[RECORD+0xD]=0
    put(m,RECORD+0xE,100,2);m[RECORD+0x10]=255;m[RECORD+0x11]=255
    for i in range(3):
        put(m,TAIL+0x30+4*i,bits((i-1)*1.25))
        put(m,TAIL+0x60+4*i,0x7fc12345+i if c.profile==5 else (0x80000000,bits(.25),bits(-.5))[i])
    put(m,TAIL+0x88,c.tag)
    for a,v in((FIRST,0x12345678),(SECOND,0xABCDEF01),(C0,bits(.5)),(C4,bits(.5)),(C8,bits(.5)),(MARK,0)):
        put(m,a,v)
    for i,a in enumerate(PARAMETERS):put(m,a,bits((i+1)*.25))
    return m

def public(m):return{a:v for a,v in m.items()if not STACK-768<=a<STACK+256}
def real(c,i):
    if i==0:return(bits(.5),bits(.5),0,0x3f7fffff,0x7fc12345,0x7f800000)[c.profile]
    return(0,bits(.5),0x3effffff,bits(1.),0x7fc34567,0)[c.profile]
def integer(c,i):return c.integer if i==0 else(c.integer^0x80000000)&0xffffffff

def effect(m,c,target,index):
    put(m,MARK,target)
    if c.mutation&1 and target==PRIMARY:put(m,TAIL+0x88,8 if read(m,TAIL+0x88)&31==9 else 9)
    if(c.mutation&2 and target==PRIMARY)or(c.mutation&4 and target==POINT):
        for i in range(3):put(m,TAIL+0x30+4*i,bits((i+4)*2.));put(m,TAIL+0x60+4*i,bits((i-2)*.75))
        for i in range(18):m[TAIL+0x6C+i]^=0x35
        m[RECORD+1]^=0x21;m[RECORD+0xC]^=0x17
    if(c.mutation&4 and target==POINT)or(c.mutation&8 and target==REAL and index==2):
        put(m,FIRST,0xAA998877);put(m,SECOND,0x66554433);put(m,C8,bits(1.))
        for i,a in enumerate(PARAMETERS):put(m,a,bits((i+3)*-.5))

def reference(initial,c):
    m=dict(initial);calls=[];packets=[];ri=ii=0
    def invoke(t,args=(),packet=None):
        nonlocal ri,ii
        calls.append((t,args));index=ri if t==REAL else ii if t==INTEGER else 0
        value=real(c,ri)if t==REAL else integer(c,ii)if t==INTEGER else 0
        if packet is not None:packets.append(tuple(packet[i]for i in DEFINED))
        effect(m,c,t,index)
        if t==REAL:ri+=1
        if t==INTEGER:ii+=1
        return value
    value=invoke(REAL);first=invoke(INTEGER);second=invoke(INTEGER)
    rate=fp(fp(value,bits(25.),'mul',c.rule),bits(15.),'add',c.rule)
    invoke(PRIMARY,(rate,(first%56+200)&255,TAIL+0x6C,TAIL+0x30,second%81+50,1,1,read(m,TAIL+0x88),m[RECORD+0xC],m[RECORD+1]))
    if read(m,TAIL+0x88)&31==9:
        if floating(invoke(REAL))<floating(read(m,C0)):
            invoke(POINT,(TAIL+0x30,m[RECORD+0xC],m[RECORD+1]))
    else:
        if floating(invoke(REAL))<floating(read(m,C4)):
            invoke(POINT,(TAIL+0x30,m[RECORD+0xC],m[RECORD+1]))
        if floating(invoke(REAL))<floating(read(m,C8)):
            firstWord,secondWord=read(m,FIRST),read(m,SECOND);packet={}
            put(packet,0,1);put(packet,4,3)
            for i in range(3):put(packet,8+4*i,read(m,TAIL+0x30+4*i));put(packet,0x14+4*i,read(m,TAIL+0x60+4*i)^0x80000000)
            for i in range(18):packet[0x20+i]=m[TAIL+0x6C+i]
            for i,a in enumerate(PARAMETERS):put(packet,0x34+4*i if i<5 else 0x4C+4*(i-5),read(m,a))
            put(packet,0x48,15,2);put(packet,0x4A,15,2)
            data=tuple(packet[i]for i in DEFINED)
            invoke(BURST,(data,firstWord,secondWord,1,m[RECORD+0xC],m[RECORD+1]),packet)
    return public(m),calls,packets

class PublicBoundary(Exception):pass
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None,fault=None,arguments=None):
        super().__init__(words,memory,c,entry=entry,connected=connected,arguments=arguments or(RECORD,))
        self.ri=self.ii=0;self.packets=[];self.full_packets=[];self.public_count=0;self.public_cut=fault
    def boundary(self,address):
        if self.own_instruction and not STACK-768<=address<STACK+256:
            if self.public_count==self.public_cut:raise PublicBoundary
            self.public_count+=1
    def get(self,address,n):self.boundary(address);return super().get(address,n)
    def put(self,address,value,n):self.boundary(address);super().put(address,value,n)
    def execute(self,w):
        op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        if op==17 and rs==16 and fn in(0,1,2):self.f[sa]=fp(self.f[rd],self.f[rt],{0:'add',1:'sub',2:'mul'}[fn],self.case.rule)
        elif op==17 and rs==16 and fn==7:self.f[sa]=self.f[rd]^0x80000000
        elif op in(34,38,42,46):
            prior=self.own_instruction;self.own_instruction=True
            try:
                address=(self.r[rs]+(((w&65535)^32768)-32768))&0xffffffff
                assert address%4==(3 if op in(38,46)else 0),'Fixture must honor complete-record alignment'
                if op in(34,38):self.r[rt]=self.get(address&~3,4)
                else:self.put(address&~3,self.r[rt],4)
            finally:self.own_instruction=prior
        else:super().execute(w)
    def record_call(self,t):
        if t in(REAL,INTEGER):args=()
        elif t==ENTRY:args=(self.r[4],)
        elif t==PRIMARY:args=(self.f[12],*self.arguments(10)[1:])
        elif t==POINT:args=self.arguments(3)
        elif t==BURST:
            raw=self.arguments(6);data=tuple(self.memory[raw[0]+i]for i in range(88));self.full_packets.append(data);data=tuple(data[i]for i in DEFINED);self.packets.append(data)
            args=(data,read(self.memory,raw[1]),read(self.memory,raw[2]),*raw[3:])
        else:raise AssertionError(hex(t))
        self.calls.append((t,args));self.events.append(('CALL',t,args))
    def hook(self,t):
        index=self.ri if t==REAL else self.ii if t==INTEGER else 0
        value=real(self.case,self.ri)if t==REAL else integer(self.case,self.ii)if t==INTEGER else 0
        effect(self.memory,self.case,t,index)
        if t==REAL:self.ri+=1
        if t==INTEGER:self.ii+=1
        for i in range(10):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for j in(1,2,3,*range(4,16),24,25):self.r[j]=0xA5000000+j
        self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
        if t==REAL:self.f[0]=value
        else:self.r[2]=value

def preserved(m,c):
    assert m.r[29]==STACK+c.phase and all(m.r[j]==m.before[j]for j in(*range(16,24),28,30,31))and m.f[20:]==m.saved_f

def guest_checks(truth,raw):
    visits=[set(),set()];count=0
    for c in cases():
        initial=fixture(c);expected=reference(initial,c);full=[];traces=[]
        for i,words in enumerate((truth,raw)):
            m=Oracle(words,initial,c).run();assert(public(m.memory),m.calls,m.packets)==expected,(c,i,m.calls,expected[1])
            preserved(m,c);visits[i].update(m.visits);full.append(m.full_packets);traces.append([v for v in m.trace if not STACK-768<=v[1]<STACK+256])
        assert full[0]==full[1]and traces[0]==traces[1],c;count+=1
    assert all(len(v)==175 for v in visits),[len(v)for v in visits]
    return dict(cases=count,streams=2,visited_words=[len(v)for v in visits],all_88_guest_packet_bytes_equal=True,defined_packet_bytes=86,public_access_order_equal=True,
        helper_mutations=True,full_40_byte_outgoing_area_clobbered=True,two_NaN_selection_models=True,hardware_FCSR_not_claimed=True)

def caller_checks(truth,raw,root):
    rom=(root/'conker/conker.us.bin').read_bytes();parent=list(struct.unpack_from('>58I',rom,0x1F1A0C));assert struct.unpack_from('>I',rom,0x2346A4)[0]==ENTRY
    count=0
    for c in list(cases())[::12]:
        initial=fixture(c);put(initial,0x8008FBE4,ENTRY);put(initial,0x800E0940,0)
        initial[TAIL]=2;initial[TAIL+0x9C]=5;put(initial,TAIL+0x8C,bits(.25))
        expected_initial=dict(initial);put(expected_initial,TAIL+0x8C,bits(-.75));expected=reference(expected_initial,c)
        for words in(truth,raw):
            linked=dict(zip(range(ENTRY,ENTRY+4*len(words),4),words));m=Oracle(parent,initial,c,entry=0x151C455C,connected=linked,arguments=(RECORD,TAIL,bits(1.))).run()
            assert(public(m.memory),m.calls,m.packets)==(expected[0],[(ENTRY,(RECORD,)),*expected[1]],expected[2]);preserved(m,c)
        count+=1
    return dict(scenarios=count,streams=2,original_parent_words=58,slot=5,registry=0x8008FBD0,countdown_expiry_path_qualified=True,optional_attached_object_callback_not_qualified=True)

def prefix_checks(truth,raw):
    count=0
    for c in(Case(tag=9),Case(profile=1),Case(mutation=15),Case(profile=5)):
        initial=fixture(c);limit=Oracle(truth,initial,c).run().public_count
        for cut in range(limit):
            states=[]
            for words in(truth,raw):
                m=Oracle(words,initial,c,fault=cut)
                try:m.run();raise AssertionError('Unfired prefix')
                except PublicBoundary:pass
                states.append((public(m.memory),m.calls,m.packets,[v for v in m.trace if not STACK-768<=v[1]<STACK+256]))
            assert states[0]==states[1];count+=1
    return dict(public_prefixes=count,streams=2,raw_private_PC_identity_not_claimed=True)
