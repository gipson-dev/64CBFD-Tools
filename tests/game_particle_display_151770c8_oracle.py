"""Particle draw packets, matrix snapshots, aliased commands and real callback ABI."""
from dataclasses import dataclass
import itertools,json,struct
from tools.experiments import game_particle_display_151770c8_match as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
RECORD,COMMANDS,MARK,TRACK=0x50000,0x60000,0x70000,0x71000
CULL,EULER,MATRIX,DELEGATE=0x1510aee0,0x150a8050,0x150a7790,0x15176df0
TABLE,PAGE,MODELS=0x800d9c10,0x800be9c0,0x800dde80
FLOATS=(0x800d9b20,0x800d35e0,0x800d35e4)
u32=lambda v:v&0xffffffff
half=lambda v:((v&65535)^32768)-32768

@dataclass(frozen=True)
class Case:
    state:int=0
    reject:int=0
    view:int=1
    page:int=0
    mutation:int=0
    phase:int=0
    alias:int=0
    seed:int=0

def commands(c):return (COMMANDS,RECORD+0x98,MODELS+0xc4)[c.alias]
def args(c):return commands(c),RECORD,u32(c.view)
def scratch(c):return STACK+c.phase-0x40
def cases():
    for i,(state,reject,view,page,mode,phase) in enumerate(itertools.product((0,1,2,3,4,255),(0,1),(-1,0,1,3,0x12348000),(0,1),(0,1,2,3),(0,8))):
        yield Case(state,reject,view,page,mode,phase,i%3,i%17)
    for v in range(256):yield Case(state=v,seed=v,mutation=v%4,page=v&1)
    for page in (2,127,255):yield Case(page=page,view=32767,mutation=2)

def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-512,512)}
    m.update({RECORD+i:(i*29+c.seed*11+0x59)&255 for i in range(248)})
    m.update({COMMANDS+i:0xa5 for i in range(128)})
    for i,a in enumerate(FLOATS):put(m,a,(0x3f4ccccd,0xbf000000,0x80000000,0x7fc01234)[(c.seed+i)%4])
    for i,a in enumerate((0x98,0x9c,0xa0,0xa8,0xac,0xb0)):put(m,RECORD+a,(0x3f800000,0xbf800000,0x80000000,0x7fc01234)[(c.seed+i)%4])
    for i in range(55):put(m,MODELS+i*4,0x81230000+i*0x100+c.seed)
    m[RECORD+0x91]=c.state;m[PAGE]=c.page;put(m,MARK,0)
    for i,v in enumerate(args(c)):put(m,STACK+c.phase+4*i,v)
    return m

def effects(m,c,target,a,ordinal,home):
    put(m,MARK,u32(target^ordinal*0x1020304))
    if target==EULER:
        for i in range(16):put(m,a[0]+4*i,0x3f000000+i*0x10000+ordinal*0x80)
    elif target==MATRIX:
        for i in range(64):m[a[1]+i]=(i*7+ordinal*3+c.seed)&255
    elif target==DELEGATE:put(m,a[0],0xf1000000|ordinal);put(m,a[0]+4,0x12340000|ordinal)
    if c.mutation&1:
        m[RECORD+0x91]=(c.seed+ordinal)%4;m[PAGE]^=1
        for i,off in enumerate((0x98,0x9c,0xa0,0xa8,0xac,0xb0)):put(m,RECORD+off,0x3f800000+(ordinal*8+i)*0x10000)
        for i in range(55):put(m,MODELS+i*4,0x87650000+ordinal*256+i)
        for i,address in enumerate(FLOATS):put(m,address,0xbf000000+(ordinal*3+i)*0x10000)
    if c.mutation&2:put(m,home+8,0x87650000|((ordinal+2)&3))

def reference(initial,c):
    m=dict(initial);calls=[];observations=[];home=STACK+c.phase;cursor=commands(c)
    def call(t,*a):
        a=tuple(map(u32,a));calls.append((t,a));observations.append(tuple(read(m,a[0]+i*4) for i in range(16)) if t==MATRIX else ())
        effects(m,c,t,a,len(calls),home)
        return u32(c.reject) if t==CULL else u32(a[0]+8*(1+c.seed%2)) if t==DELEGATE else 0xdeadbeef
    rejected=call(CULL,u32(TABLE+half(c.view)*64),*(read(m,RECORD+a) for a in (0x98,0x9c,0xa0)),read(m,FLOATS[0]),0x457a0000,read(m,FLOATS[1]),read(m,FLOATS[2]),0,0)
    if rejected:return m,calls,observations,cursor
    if m[RECORD+0x91]==0:
        call(EULER,scratch(c),*(read(m,RECORD+a) for a in (0xa8,0xac,0xb0)))
        for i,a in enumerate((0x98,0x9c,0xa0)):put(m,scratch(c)+48+4*i,read(m,RECORD+a))
        call(MATRIX,scratch(c),RECORD+m[PAGE]*64+16)
        put(m,cursor,0xda380003);put(m,cursor+4,RECORD+m[PAGE]*64+16);cursor+=8
        put(m,cursor,0xdb060004);put(m,cursor+4,read(m,MODELS+0xcc));cursor+=8
        put(m,cursor,0xde000000);put(m,cursor+4,read(m,MODELS+0xd4));cursor+=8
    else:cursor=call(DELEGATE,cursor,RECORD,u32(half(read(m,home+8))))
    return m,calls,observations,u32(cursor)

class Oracle(FactoryOracle):
    def __init__(self,words,initial,c,entry=source.ENTRY,connected=None):
        super().__init__(words,initial,c,entry=entry,arguments=args(c),connected=connected)
        self.observations=[];self.before_r,self.before_f=self.r[:],self.f[:]
    def record_call(self,t):
        if t==source.ENTRY:assert tuple(self.arguments(3))==args(self.case);return
        a=tuple(map(u32,self.arguments({CULL:10,EULER:4,MATRIX:2,DELEGATE:3}[t])))
        self.calls.append((t,a));self.events.append(('CALL',t,a))
        self.observations.append(tuple(read(self.memory,a[0]+4*i) for i in range(16)) if t==MATRIX else ())
    def hook(self,t):
        a=self.calls[-1][1];effects(self.memory,self.case,t,a,len(self.calls),self.target_home)
        value=u32(self.case.reject) if t==CULL else u32(a[0]+8*(1+self.case.seed%2)) if t==DELEGATE else 0xdeadbeef
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=value

def public(m):return {a:v for a,v in m.items() if not STACK-512<=a<STACK+512}
def verify(m,initial,c):
    want,calls,obs,value=reference(initial,c)
    assert (public(m.memory),m.calls,m.observations,m.r[2])==(public(want),calls,obs,value),c
    assert m.r[16:24]==m.before_r[16:24] and m.r[29]==m.before_r[29] and m.r[30]==m.before_r[30] and m.f[20:]==m.before_f[20:]
def state(m):return m.memory,m.r,m.f,m.calls,m.observations,m.trace,m.hi,m.lo,m.current_pc,m.delay_of

def main():
    programs=[source.bound(*payload(source.OUT/name,source.NAME)) for name in ('retail.o','selected.o','guarded.o')];assert programs[0]==programs[2]
    count=0;seen=set()
    for c in cases():
        initial=fixture(c);machines=[]
        for words in programs:
            m=Oracle(words,initial,c);m.run();verify(m,initial,c);machines.append(m)
        assert state(machines[0])==state(machines[2]);seen.update(machines[0].visits);count+=1
    prefixes=0
    for c in (Case(),Case(alias=2),Case(state=3,mutation=3),Case(reject=1)):
        initial=fixture(c);m=Oracle(programs[0],initial,c);m.run()
        for cut in range(m.all_accesses):
            machines=[]
            for words in (programs[0],programs[2]):
                m=Oracle(words,initial,c);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError('Missing guest access boundary')
                machines.append(m)
            assert state(machines[0])==state(machines[1]);prefixes+=1
    rom=(source.ROOT/'conker/conker.us.bin').read_bytes();caller_cases=0
    assert struct.unpack_from('>I',rom,0x23034c)[0]==source.ENTRY
    start,end=0x15167898,0x151678b8;window=struct.unpack_from('>8I',rom,0x194d48)
    for status,reject,mode,phase in itertools.product((0,1,2,3,255),(0,1),(0,1,2,3),(0,8)):
        c=Case(state=status,reject=reject,mutation=mode,phase=phase,seed=caller_cases%7)
        initial=fixture(c);put(initial,TRACK,0x12345678);put(initial,RECORD+8,0x87654321)
        for words in programs:
            code=dict(zip(range(source.ENTRY,source.ENTRY+source.SIZE,4),words));code[end]=0
            m=Oracle(window,initial,c,entry=start,connected=code)
            m.r[16],m.r[17],m.r[19],m.r[22],m.r[25]=RECORD,TRACK,commands(c),u32(c.view),source.ENTRY
            m.before_r=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing registry dispatcher continuation')
            expected=dict(initial);put(expected,TRACK,0x87654321);verify(m,expected,c)
        caller_cases+=1
    missing=sorted(pc-source.ENTRY for pc in set(range(source.ENTRY,source.ENTRY+source.SIZE,4))-seen)
    assert missing==[0xb4],missing
    report=dict(cases=count,streams=3,visited_words=101-len(missing),unvisited_offsets=[hex(x) for x in missing],callback_cases=caller_cases,registry_slots=[0x8008b88c],full_state_prefixes=prefixes,aliased_commands=True,provider_matrix_snapshots=True,raw_fault_order_claimed=False)
    (source.OUT/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
