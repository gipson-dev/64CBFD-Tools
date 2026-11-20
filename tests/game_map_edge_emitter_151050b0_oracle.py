"""Map-edge emitter semantics under an explicit single-precision/provider model."""
from dataclasses import dataclass
import itertools,struct
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
ENTRY,RECORD,TAIL,SOURCE,ALT,GATE,MARK=0x151050B0,0x30000,0x30028,0x50000,0x51000,0x60000,0x70000
DISPATCH,CHECK,REAL,SPAWN=0x151494E0,0x151464B8,0x150ADA68,0x15106F98
TICKS,TIME,RATE,RANGE,WIDTH=0x800BE9E4,0x800BE9A4,0x800A23B4,0x800A23B8,0x800A23BC
u32=lambda n:n&0xffffffff
short=lambda n:((n&65535)^32768)-32768
DEFINED=tuple(i for i in range(48)if i not in(0x1E,0x1F,0x2D,0x2E,0x2F))
@dataclass(frozen=True)
class Case:
    timer:int=3
    ticks:int=1
    blocked:int=0
    accumulator:int=bits(2.25)
    time:int=bits(1.)
    mutation:int=0
    phase:int=0
    seed:int=0
    fcsr:int=0
    nan:bool=False
    rule:str='left'
def cases():
    for timer,ticks,blocked,acc,time in itertools.product((-1,0,1,32767),(0,1,-1,0x7fffffff,0x80000000),(0,1),(bits(0.),bits(1.),0x3f800001,bits(2.25),bits(3.25),0x7fc12345),(0,bits(1.))):
        yield Case(timer,ticks,blocked,acc,time,seed=timer&3)
    for mutation,phase,seed in itertools.product(range(16),(0,8),range(6)):
        yield Case(mutation=mutation,phase=phase,seed=seed,fcsr=0xA5A50003 if phase else 0)
    for seed,rule in itertools.product(range(6),('left','right')):yield Case(nan=True,seed=seed,rule=rule)
def fixture(c):
    m={STACK+i:(i*17+c.seed+0xA5)&255 for i in range(-768,256)}
    for base,size in((RECORD,160),(SOURCE,24),(ALT,24),(GATE,4),(MARK,4)):m.update({base+i:(i*29+c.seed+0x5A)&255 for i in range(size)})
    m[RECORD+1]=0x18+c.seed;m[RECORD+0xC]=0xE1-c.seed;m[RECORD+0xD]=0;put(m,RECORD+0xE,100,2);m[RECORD+0x10]=255;m[RECORD+0x11]=61
    put(m,TAIL,SOURCE);put(m,TAIL+4,c.timer,2);put(m,TAIL+8,c.accumulator)
    for i in range(12):
        put(m,TAIL+0xC+4*i,0x7fc12345+i if c.nan else bits((i-5)*1.25))
        put(m,TAIL+0x3C+4*i,0xffc34567+i if c.nan else bits((i%5-2)*.5))
    put(m,TAIL+0x6C,GATE);put(m,GATE,0,2);put(m,GATE+2,0 if c.blocked else 1,2);m[SOURCE+0x14]=0xA5
    for a,v in((TICKS,c.ticks),(TIME,c.time),(RATE,0x3D23D70B),(RANGE,0x3D8F5C29),(WIDTH,0x3EA66667),(MARK,0x12345678)):put(m,a,u32(v))
    return m
def public(m):return{a:v for a,v in m.items()if not STACK-768<=a<STACK+256}
def real(c,i):return(0,bits(.125),bits(.5),bits(.75),0x3F7FFFFF,bits(1.))[(c.seed+i)%6]
def effect(m,c,target,index,descriptor=None):
    put(m,MARK,target)
    if c.mutation&1 and target==REAL and index==0:
        put(m,RATE,bits(.125));put(m,RANGE,bits(.25));put(m,TIME,bits(.5));put(m,TAIL+8,bits(2.25))
    if c.mutation&2 and target==REAL and index>0:
        for i in range(12):put(m,TAIL+0xC+4*i,bits((i+index)*.25))
    if c.mutation&4 and target==SPAWN:put(m,TAIL+8,bits(0.))
    if c.mutation&8 and target==SPAWN:
        put(m,WIDTH,bits(.75));m[RECORD+1]^=0x21;m[RECORD+0xC]^=0x17
        if descriptor is not None:descriptor[0x28]^=0x55
def reference(initial,c):
    m=dict(initial);calls=[];payloads=[];ri=0;packet={i:0 for i in range(48)}
    def invoke(t,args=(),data=None):
        nonlocal ri
        index=ri if t==REAL else 0;calls.append((t,args))
        if data is not None:payloads.append(data)
        answer=real(c,ri)if t==REAL else c.blocked if t==CHECK else 0
        effect(m,c,t,index,packet if t==SPAWN else None)
        if t==REAL:ri+=1
        return answer
    if short(read(m,TAIL+4,2))<0:m[read(m,TAIL)+0x14]=1;return public(m),calls,payloads
    m[read(m,TAIL)+0x14]=0;put(m,TAIL+4,short(u32(short(read(m,TAIL+4,2))-read(m,TICKS))),2)
    if short(read(m,TAIL+4,2))<0:invoke(DISPATCH,(0,0x39));invoke(DISPATCH,(0,0x4B))
    if invoke(CHECK,(read(m,TAIL+0x6C),))!=0:return public(m),calls,payloads
    rv=invoke(REAL);op=lambda a,b,k:fp(a,b,k,c.rule)
    put(m,TAIL+8,op(read(m,TAIL+8),op(op(read(m,RATE),op(rv,read(m,RANGE),'mul'),'add'),read(m,TIME),'mul'),'add'))
    if not floating(read(m,TAIL+8))>1.:return public(m),calls,payloads
    width=read(m,WIDTH)
    for i,v in enumerate((10.,15.,20.,44.,37.)):put(packet,4*i,bits(v))
    for off,v in((0x14,100),(0x16,0),(0x18,10),(0x1A,1),(0x1C,10)):put(packet,off,v,2)
    put(packet,0x20,4);put(packet,0x24,2)
    for i,v in enumerate((0x7E,0xF9,0xFF,0x37,200)):packet[0x28+i]=v
    count=0
    while floating(read(m,TAIL+8))>1.:
        first=int(floating(op(invoke(REAL),bits(3.),'mul')))&255
        second=int(floating(op(op(op(invoke(REAL),bits(2.),'mul'),bits(1.),'add'),bits(float(first)),'add')))&255
        if second>=4:second=(second-4)&255
        points=[]
        for index in(first,second):
            value=invoke(REAL);points.append(tuple(op(op(read(m,TAIL+0x3C+12*index+4*j),value,'mul'),read(m,TAIL+0xC+12*index+4*j),'add')for j in range(3)))
        invoke(SPAWN,(points[0],points[1],3,0,width,2,m[RECORD+0xC],m[RECORD+1]),tuple(packet[i]for i in DEFINED))
        put(m,TAIL+8,op(read(m,TAIL+8),bits(1.),'sub'));count+=1;assert count<20
    return public(m),calls,payloads
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c=Case(),entry=ENTRY,connected=None,fault=None):
        super().__init__(words,memory,c,entry=entry,connected=connected,arguments=(RECORD,));self.fcsr=self.initial_fcsr=c.fcsr;self.ri=0;self.packets=[];self.full_packets=[]
        self.public_cut=fault;self.public_count=0
    def boundary(self,address):
        if self.own_instruction and not STACK-768<=address<STACK+256:
            if self.public_count==self.public_cut:raise PublicBoundary
            self.public_count+=1
    def get(self,address,size):
        self.boundary(address);return super().get(address,size)
    def put(self,address,value,size):
        self.boundary(address);super().put(address,value,size)
    def execute(self,w):
        op,rs,fn=w>>26,w>>21&31,w&63
        if op==17 and(rs in(2,6)or(rs==16 and fn==36)):AreaOracle.execute(self,w)
        elif op==17 and rs==16 and fn in(0,1,2):self.f[w>>6&31]=fp(self.f[w>>11&31],self.f[w>>16&31],('add','sub','mul')[fn],self.case.rule)
        else:super().execute(w)
    def record_call(self,t):
        assert self.fcsr==self.initial_fcsr,('conversion control state leaked',hex(t))
        if t==DISPATCH:args=self.arguments(2)
        elif t==CHECK:args=(self.r[4],)
        elif t==REAL:args=()
        elif t==ENTRY:args=(self.r[4],)
        elif t==SPAWN:
            raw=self.arguments(8);args=(tuple(read(self.memory,raw[0]+4*j)for j in range(3)),tuple(read(self.memory,raw[1]+4*j)for j in range(3)),raw[2],0,*raw[4:]);data=tuple(self.memory[raw[3]+i]for i in range(48));self.full_packets.append(data);self.packets.append(tuple(data[i]for i in DEFINED))
        else:raise AssertionError(('helper',hex(t)))
        self.calls.append((t,args));self.events.append(('CALL',t,args))
    def hook(self,t):
        c=self.case;index=self.ri if t==REAL else 0;value=real(c,self.ri)if t==REAL else c.blocked if t==CHECK else 0
        descriptor={i:self.memory[self.r[7]+i]for i in range(48)}if t==SPAWN else None
        effect(self.memory,c,t,index,descriptor)
        if descriptor is not None:
            for i,v in descriptor.items():self.memory[self.r[7]+i]=v
        if t==REAL:self.ri+=1
        for j in range(4):self.put(self.r[29]+4*j,0xB5000000+j,4)
        for j in(1,2,3,*range(4,16),24,25):self.r[j]=0xA5000000+j
        self.f[:20]=[0xA5000000+j for j in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
        if t==REAL:self.f[0]=value
        else:self.r[2]=value
def preserved(m,c):
    assert m.r[29]==STACK+c.phase and all(m.r[j]==m.before[j]for j in(*range(16,24),28,30,31))and m.f[20:]==m.saved_f and m.fcsr==c.fcsr
def guest_checks(truth,raw):
    visits=[set(),set()];count=0;padding=set()
    for c in cases():
        initial=fixture(c);want=reference(initial,c);full=[];traces=[]
        for i,words in enumerate((truth,raw)):
            m=Oracle(words,initial,c).run();assert(public(m.memory),m.calls,m.packets)==want,(i,c,m.calls,want[1]);preserved(m,c);visits[i].update(m.visits);full.append(m.full_packets)
            traces.append([v for v in m.trace if not STACK-768<=v[1]<STACK+256])
        assert traces[0]==traces[1],('public access schedule',c)
        assert full[0]==full[1],('complete 48-byte copied descriptor',c)
        for a,b in zip(*full):padding.update(i for i in range(48)if a[i]!=b[i])
        count+=1
    assert padding<=set(range(48))-set(DEFINED)
    return dict(cases=count,streams=2,visited_words=[len(v)for v in visits],unvisited_offsets=[sorted(set(range(0,len(w)*4,4))-set((a-ENTRY)for a in v))for w,v in zip((truth,raw),visits)],defined_packet_bytes=43,
        observed_raw_padding_differences=sorted(padding),all_48_copied_guest_bytes_equal=True,public_access_order_equal=True,two_NaN_selection_models=True,bounded_FP_control_model=True,hardware_FCSR_not_claimed=True,full_raw_private_frame_identity_not_claimed=True)
def caller_checks(truth,raw,root):
    rom=(root/'conker/conker.us.bin').read_bytes();parent=list(struct.unpack_from('>45I',rom,0x176714));count=0
    assert struct.unpack_from('>I',rom,0x22F09C)[0]==ENTRY
    for c in list(cases())[::20]:
        initial=fixture(c);put(initial,0x8008A5DC,ENTRY);want=reference(initial,c)
        for words in(truth,raw):
            linked=dict(zip(range(ENTRY,ENTRY+4*len(words),4),words));m=Oracle(parent,initial,c,entry=0x15149264,connected=linked).run();assert(public(m.memory),m.calls,m.packets)==(want[0],[(ENTRY,(RECORD,)),*want[1]],want[2]);preserved(m,c)
        count+=1
    return dict(scenarios=count,streams=2,original_parent_words=45,registry=0x8008A4E8,slot=61,other_parent_paths_not_qualified=True)
class PublicBoundary(Exception):pass
def prefix_checks(truth,raw):
    count=0
    for c in(Case(timer=-1),Case(timer=0),Case(blocked=1),Case(mutation=8),Case(nan=True)):
        initial=fixture(c);all_accesses=Oracle(truth,initial,c).run().public_count
        for cut in range(all_accesses):
            results=[]
            for words in(truth,raw):
                m=Oracle(words,initial,c,fault=cut)
                try:m.run();raise AssertionError('Unfired public access boundary')
                except PublicBoundary:pass
                results.append((public(m.memory),m.calls,m.packets,[v for v in m.trace if not STACK-768<=v[1]<STACK+256]))
            assert results[0]==results[1];count+=1
    return dict(public_prefixes=count,streams=2,private_address_or_PC_identity_not_claimed=True,portable_C_fault_semantics_not_claimed=True)
