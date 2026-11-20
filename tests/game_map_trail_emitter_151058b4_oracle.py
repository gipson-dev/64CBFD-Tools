"""Defined trail-packet semantics and explicit unresolved raw-layout witnesses."""
from dataclasses import dataclass,replace
import itertools,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY,RECORD,SOURCE,ALT,GATE,MARK=0x151058B4,0x30000,0x50000,0x51000,0x60000,0x70000
REAL,INTEGER,CHECK,SAMPLE,DIRECTION,SPAWN=0x150ADA68,0x150ADA20,0x151464B8,0x151432BC,0x15143794,0x1515C2F0
RATE,BASE,RANGE_BASE,RANGE_SCALE,LIVE_SCALE,LIVE_BASE=0x800A23EC,0x800A23F0,0x800A23F4,0x800A23F8,0x800A23FC,0x800A2400
PACKET_DEFINED=tuple(i for i in range(60)if i not in(0x22,0x23,0x33,0x3A,0x3B));HEADER_DEFINED=tuple(range(22))
short=lambda x:((x&65535)^32768)-32768
@dataclass(frozen=True)
class Case:
    count:int=bits(3.25)
    blocked:int=0
    integer:int=0xffffffff
    mutation:int=0
    phase:int=0
    seed:int=0
    y:int=-32768
    nan:bool=False
    rule:str='left'

def cases():
    for count,blocked,integer,phase in itertools.product((0,bits(1.),0x3F800001,bits(2.),bits(2.25),bits(3.25),bits(4.),bits(5.25)),(0,1),(0,0x80000000,0xffffffff),(0,8)):
        yield Case(count,blocked,integer,phase=phase,seed=integer&3)
    for mutation,seed,phase in itertools.product((1,2,4,8,15,16),(0,3),(0,8)):
        yield Case(mutation=mutation,seed=seed,phase=phase)
    for y,count in itertools.product((-32768,-1,0,32767),(bits(2.),bits(3.25))):yield Case(count=count,y=y)
    for count,blocked,rule in itertools.product((0x7FC12345,0xFF800000),(0,1),('left','right')):yield Case(count,blocked,rule=rule)
    for count,rule in itertools.product((bits(2.),bits(3.25)),('left','right')):yield Case(count=count,nan=True,rule=rule)

def fixture(c):
    m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-768,256)}
    for a,n in((RECORD,56),(SOURCE,22),(ALT,22),(GATE,4),(MARK,4)):m.update({a+i:(i*29+c.seed+0x5A)&255 for i in range(n)})
    m[RECORD+1]=0x18+c.seed;m[RECORD+0xC]=0xE1-c.seed
    put(m,RECORD+0x28,SOURCE);put(m,RECORD+0x2C,c.count);put(m,RECORD+0x30,GATE);m[RECORD+0x34]=0xA4
    for a,y in((SOURCE,c.y),(ALT,12345)):
        put(m,a,-17,2);put(m,a+2,y,2);put(m,a+4,31,2)
    for a,v in((RATE,0),(BASE,bits(1.)),(RANGE_BASE,0x40ECCCCD),(RANGE_SCALE,0x4122147B),(LIVE_SCALE,0x3FBE3540),(LIVE_BASE,0xC043126F),(MARK,0)):put(m,a,v)
    return m

def public(m):return{a:v for a,v in m.items()if not STACK-768<=a<STACK+256}
def real(c,index):return 0x7FC12345 if c.nan and index==0 else(0,bits(.25),bits(.5),0x3F7FFFFF)[(c.seed+index)%4]
def integer(c,index):return(c.integer+index*0x9E3779B9)&0xffffffff
def sample(m,source,index):return(bits(short(read(m,source,2))+index*.25),bits(short(read(m,source+4,2))-index*.5),bits(short(read(m,source+2,2))+8.),bits(float(short(read(m,source+2,2)))))
def direction(yaw,pitch,radius):return(bits(short(yaw)*.125),bits(short(pitch)*.25),radius)
def effect(m,c,target,index,header=None,packet=None):
    put(m,MARK,target)
    if c.mutation&1 and target==REAL and index==0:
        put(m,RATE,bits(.125));put(m,BASE,bits(.75));put(m,RECORD+0x2C,bits(4.))
    if c.mutation&2 and target==SAMPLE:
        put(m,RECORD+0x28,ALT);m[RECORD+1]^=0x21;m[RECORD+0xC]^=0x17
    if c.mutation&4 and target==SPAWN:
        put(m,RANGE_BASE,bits(99.));put(m,RANGE_SCALE,bits(5.));put(m,LIVE_SCALE,bits(-.5));put(m,LIVE_BASE,bits(.75))
    if c.mutation&8 and target==SPAWN:
        header[0x14]^=3;packet[0x21]^=1;m[RECORD+0x34]=0x40
    if c.mutation&16 and target==CHECK:
        put(m,RECORD+0x2C,bits(3.25));put(m,RATE,0);put(m,BASE,bits(1.))

def reference(initial,c):
    m=dict(initial);calls=[];packets=[];ri=ii=si=0;header={};packet={}
    def invoke(target,args=()):
        nonlocal ri,ii,si
        calls.append((target,args));index=ri if target==REAL else ii if target==INTEGER else si if target==SAMPLE else 0
        answer=real(c,ri)if target==REAL else integer(c,ii)if target==INTEGER else c.blocked if target==CHECK else sample(m,args[0],si)if target==SAMPLE else None
        effect(m,c,target,index,header,packet)
        if target==REAL:ri+=1
        if target==INTEGER:ii+=1
        if target==SAMPLE:si+=1
        return answer
    if invoke(CHECK,(read(m,RECORD+0x30),)):return public(m),calls,packets
    rv=invoke(REAL);op=lambda x,y,k:fp(x,y,k,c.rule)
    count=op(op(op(rv,read(m,RATE),'mul'),read(m,BASE),'add'),read(m,RECORD+0x2C),'mul')
    if not floating(count)>1.:return public(m),calls,packets
    put(header,0xE,21,2);put(header,0x10,10);header[0x14]=255
    for at,value in((0x14,4),(0x15,2),(0x16,3),(0x17,0x61),(0x18,0xF2),(0x19,255),(0x1B,255),(0x1C,255),(0x1D,255),(0x1E,255),(0x1F,255),(0x20,3),(0x21,0x24),(0x32,0),(0x38,255),(0x39,0)):packet[at]=value
    for at,value in((0x24,0x200005),(0x28,0x60600),(0x34,bits(1.))):put(packet,at,value)
    for at,value in((0x2C,20),(0x2E,12),(0x30,1)):put(packet,at,value,2)
    put(header,4,bits(float(short(read(m,read(m,RECORD+0x28)+2,2)))))
    base,scale=read(m,RANGE_BASE),read(m,RANGE_SCALE);loops=0
    while floating(count)>1.:
        packet[0x1A]=(invoke(INTEGER)%101+155)&255;header[0x15]=(invoke(INTEGER)&3)+3
        values=invoke(SAMPLE,(read(m,RECORD+0x28),0,0,0,0));put(header,0,values[0]);put(header,8,values[1])
        put(header,0xC,invoke(INTEGER)%31+30,2);put(packet,0,op(op(invoke(REAL),scale,'mul'),base,'add'))
        first=invoke(INTEGER);second=invoke(INTEGER);radius=op(op(invoke(REAL),bits(20.),'mul'),bits(30.),'add')
        yaw,pitch=short(first&255),short(second%22-54);args=(yaw&0xffffffff,pitch&0xffffffff,radius,0)
        invoke(DIRECTION,args)
        for i,v in enumerate(direction(yaw,pitch,radius)):put(packet,4+4*i,v)
        put(packet,0x10,op(op(invoke(REAL),read(m,LIVE_SCALE),'mul'),read(m,LIVE_BASE),'add'))
        data=(tuple(header[i]for i in HEADER_DEFINED),tuple(packet[i]for i in PACKET_DEFINED));packets.append(data)
        invoke(SPAWN,(data[0],0,data[1],0,m[RECORD+0xC],m[RECORD+1]));count=op(count,bits(1.),'sub');loops+=1;assert loops<20
    return public(m),calls,packets

class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None,arguments=None):
        super().__init__(words,memory,c,entry=entry,connected=connected,arguments=arguments or(RECORD,));self.ri=self.ii=self.si=0;self.packets=[];self.full_packets=[];self.private_arguments=[]
    def execute(self,w):
        op,rs,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        if op==17 and rs==16 and fn in(0,1,2):self.f[fd]=fp(self.f[fs],self.f[rt],('add','sub','mul')[fn],self.case.rule)
        elif op==17 and rs==20 and fn==32:self.f[fd]=bits(float(signed(self.f[fs])))
        else:super().execute(w)
    def record_call(self,t):
        if t in(REAL,INTEGER):args=()
        elif t==ENTRY:args=(self.r[4],)
        elif t==CHECK:args=(self.r[4],)
        elif t==SAMPLE:
            raw=self.arguments(5);assert raw[1:]==tuple(self.r[29]+n for n in(0xCC,0xD4,0x8C,0x88));args=(raw[0],0,0,0,0);self.private_arguments.append((t,raw[1:]))
        elif t==DIRECTION:
            raw=self.arguments(4);assert raw[3]==self.r[29]+0x94;args=(*raw[:3],0);self.private_arguments.append((t,(raw[3],)))
        elif t==SPAWN:
            raw=self.arguments(6);assert raw[0]==self.r[29]+0xCC and raw[2]==self.r[29]+0x90;self.private_arguments.append((t,(raw[0],raw[2])))
            h=tuple(self.memory[raw[0]+i]for i in range(24));p=tuple(self.memory[raw[2]+i]for i in range(60));self.full_packets.append((h,p))
            data=(tuple(h[i]for i in HEADER_DEFINED),tuple(p[i]for i in PACKET_DEFINED));self.packets.append(data);args=(data[0],raw[1],data[1],*raw[3:])
        else:raise AssertionError(hex(t))
        self.calls.append((t,args));self.events.append(('CALL',t,args))
    def hook(self,t):
        index=self.ri if t==REAL else self.ii if t==INTEGER else self.si if t==SAMPLE else 0
        value=real(self.case,self.ri)if t==REAL else integer(self.case,self.ii)if t==INTEGER else self.case.blocked if t==CHECK else 0
        raw=self.arguments(6)if t==SPAWN else self.arguments(5)if t==SAMPLE else self.arguments(4)if t==DIRECTION else()
        if t==SAMPLE:
            for a,v in zip(raw[1:],sample(self.memory,raw[0],self.si)):put(self.memory,a,v)
        if t==DIRECTION:
            for i,v in enumerate(direction(raw[0],raw[1],raw[2])):put(self.memory,raw[3]+4*i,v)
        h={i:self.memory[raw[0]+i]for i in range(24)}if t==SPAWN else None;p={i:self.memory[raw[2]+i]for i in range(60)}if t==SPAWN else None
        effect(self.memory,self.case,t,index,h,p)
        if t==SPAWN:
            for i,v in h.items():put(self.memory,raw[0]+i,v,1)
            for i,v in p.items():put(self.memory,raw[2]+i,v,1)
        if t==REAL:self.ri+=1
        if t==INTEGER:self.ii+=1
        if t==SAMPLE:self.si+=1
        for i in range(6):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
        if t==REAL:self.f[0]=value
        else:self.r[2]=value

def preserved(m,c):assert m.r[29]==STACK+c.phase and all(m.r[i]==m.before[i]for i in(*range(16,24),28,30,31))and m.f[20:]==m.saved_f
def public_trace(m):return[v for v in m.trace if not STACK-768<=v[1]<STACK+256]
def guest_checks(truth,raw):
    visits=[set(),set()];padding=[set(),set()];count=read_order_cases=0
    for c in cases():
        initial=fixture(c);want=reference(initial,c);machines=[]
        for i,words in enumerate((truth,raw)):
            m=Oracle(words,initial,c).run();assert(public(m.memory),m.calls,m.packets)==want,(i,c,m.calls,want[1]);preserved(m,c);visits[i].update(m.visits);machines.append(m)
        for left,right in zip(machines[0].full_packets,machines[1].full_packets):
            for i,(a,b)in enumerate(zip(left,right)):padding[i].update(j for j,(x,y)in enumerate(zip(a,b))if x!=y)
        read_order_cases+=public_trace(machines[0])!=public_trace(machines[1]);count+=1
    assert padding[0]<=set(range(24))-set(HEADER_DEFINED)and padding[1]<=set(range(60))-set(PACKET_DEFINED)
    assert padding[1]and read_order_cases
    assert all(len(v)==196 for v in visits),[len(v)for v in visits]
    return dict(cases=count,streams=2,visited_words=[len(v)for v in visits],retained_unreachable_break_offset=0x1C4,
        defined_header_bytes=22,defined_packet_bytes=55,raw_padding_differences=[sorted(v)for v in padding],public_read_order_difference_cases=read_order_cases,
        raw_frame_delta=8,source_ABI_registers_preserved=True,matching_credit=0,raw_private_prefix_and_padding_NOT_qualified=True)

def caller_checks(truth,raw,root):
    rom=(root/'conker/conker.us.bin').read_bytes();wrapper=list(struct.unpack_from('>27I',rom,0x132CF8));count=0
    for c,command in itertools.product(list(cases())[::15],(0x38,0x39,0x37,0x138)):
        initial=fixture(c);want=reference(initial,c)if command&255==0x38 else(public(initial),[],[])
        final=dict(want[0]);final[RECORD+0x34]=(final[RECORD+0x34]|1)if command&255==0x38 else final[RECORD+0x34]&254 if command&255==0x39 else final[RECORD+0x34]
        for words in(truth,raw):
            linked=dict(zip(range(ENTRY,ENTRY+4*len(words),4),words));m=Oracle(wrapper,initial,c,entry=0x15105848,connected=linked,arguments=(RECORD,0xDEADBEEF,command)).run()
            calls=([(ENTRY,(RECORD,)),*want[1]]if command&255==0x38 else[])
            assert(public(m.memory),m.calls,m.packets)==(final,calls,want[2]),(c,command,m.calls,calls);preserved(m,c)
        count+=1
    return dict(cases=count,streams=2,original_wrapper_words=27,commands=[0x38,0x39,0x37,0x138],actual_wrapper_path=True)

def layout_witness(truth,raw):
    c=Case();initial=fixture(c);a,b=(Oracle(words,initial,c).run()for words in(truth,raw))
    differences=[]
    for left,right in zip(a.private_arguments,b.private_arguments):
        assert left[0]==right[0]
        delta=[y-x for x,y in zip(left[1],right[1])];assert all(v==-8 for v in delta);differences.append(dict(target=left[0],pointer_deltas=delta))
    ta,tb=public_trace(a),public_trace(b);first=next((i for i,(x,y)in enumerate(zip(ta,tb))if x!=y),None);assert first is not None
    assert truth[0x1C4//4]==raw[0x1C4//4]==0x0007000D
    return dict(raw_minus_retail_private_address=-8,private_call_witnesses=differences,first_public_access_difference=first,
                retail_access=ta[first],raw_access=tb[first],unreachable_break_word='0007000D',matching_credit=0,
                remaining_frame_public_prefix_and_padding_gates_open=True)
