"""Independent ordered RDP bitfield/cache model and actual renderer connection."""
from dataclasses import dataclass
import itertools,struct
from tools.experiments import game_combiner_state_1513f4e4_candidates as c
from tools.tests import game_record_vertex_callback_1513e83c_oracle as render
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests import game_resource_texture_callback_1513bbfc_oracle as ram

ENTRY,HELPER,TABLE,CACHE=0x1513F4E4,0x15143044,0x800A4BA8,0x800DD1BE
OUTPUT,DIRTY,ALT,STACK=0x50000,0x60000,0x70000,ram.STACK
u32,rd,wr,state=ram.u32,ram.rd,ram.wr,ram.state
half=lambda v:((v&65535)^32768)-32768

@dataclass(frozen=True)
class Case:
    index:int=0
    dirty:int=1
    cache:int=0xFFFF
    same:int=0
    result:object=None
    pattern:int=0
    mutation:int=0
    alias:int=0
    phase:int=0
    seed:int=0

def symbols():return dict(func_15143044=HELPER,D_800A4BA8=TABLE,D_800DD1BE=CACHE)
def selected(index,case):return 0x7FFF-(index&255)if case.result is None else half(case.result)
def output(case):return TABLE+(case.index&255)*16 if case.alias==1 else CACHE-2 if case.alias==4 else TABLE+(case.index&255)*16+8 if case.alias==6 else OUTPUT
def dirty(case):return output(case)if case.alias==2 else TABLE+(case.index&255)*16+9 if case.alias==3 else CACHE if case.alias==5 else DIRTY
def arguments(case):return output(case),u32(case.index),dirty(case)

def table_bytes(pattern,seed):
    return bytes(((i*29+seed*11+90)&255)if pattern==0 else 255 if pattern==1 else 0 if pattern==2 else((1<<(i%8))if i%2 else(255^(1<<(i%8))))for i in range(4096))

def fixture(case=Case(),order='big'):
    regions=((OUTPUT,64),(DIRTY,16),(ALT,80),(TABLE-32,4160),(CACHE-32,128),(STACK+case.phase-2048,2560))
    seen=set();m={}
    for p,n in regions:
        addresses={u32(p+i)for i in range(n)};assert not seen&addresses,'Disjoint named arenas required';seen|=addresses
        m.update({u32(p+i):(i*29+case.seed*11+90)&255 for i in range(n)})
    for i,v in enumerate(table_bytes(case.pattern,case.seed)):m[TABLE+i]=v
    wr(m,CACHE,selected(case.index,case)if case.same else case.cache,2,order);m[dirty(case)]=case.dirty&255
    return m

def public(m,case):return{a:v for a,v in m.items()if not STACK+case.phase-2048<=a<STACK+case.phase+512}

def effect(m,case,args,home,order='big'):
    cursor,index,flag=args
    if case.mutation==1:
        m[flag]=1;wr(m,CACHE,0x8000,2,order)
        for i in range(16):m[TABLE+(index&255)*16+i]=(i*37+0xC3)&255
    if case.mutation==2:wr(m,home+4,0xABCD0004,4,order)
    if case.mutation==3:wr(m,home,ALT,4,order);wr(m,home+8,ALT+64,4,order);m[ALT+64]=1

def reference(initial,case=Case(),order='big',home=None,args=None,connected=False):
    m=dict(initial);home=STACK+case.phase if home is None else home;args=arguments(case)if args is None else args
    for i,v in enumerate(args):wr(m,home+i*4,v,4,order)
    answer=selected(args[1],case);calls=[(HELPER,(args[1]&255,0))]
    if connected:assert case.result is None and case.mutation==0
    else:effect(m,case,args,home,order)
    cursor=rd(m,home,4,order);index=rd(m,home+4,4,order)&255;flag=rd(m,home+8,4,order)
    if answer!=half(rd(m,CACHE,2,order)):
        if m[flag]==1:
            wr(m,cursor,0xE7000000,4,order);wr(m,cursor+4,0,4,order);cursor=u32(cursor+8);m[flag]=0
        p=TABLE+16*index
        # Model the packed hardware fields independently of SDK macro spelling.
        fields=((0,20,15),(2,15,31),(4,12,7),(6,9,7),(8,5,15),(10,0,31))
        word=0xFC000000
        for off,shift,mask in fields:word|=(m[p+off]&mask)<<shift
        wr(m,cursor,word,4,order)
        # Reload after w0: a valid guest table/output alias changes these bytes.
        fields=((1,28,15),(3,15,7),(5,12,7),(7,9,7),(9,24,15),(12,21,7),(14,18,7),(11,6,7),(13,3,7),(15,0,7))
        word=0
        for off,shift,mask in fields:word|=(m[p+off]&mask)<<shift
        wr(m,cursor+4,word,4,order);cursor=u32(cursor+8);wr(m,CACHE,answer,2,order)
    return dict(memory=m,observed=public(m,case),calls=calls,value=cursor)

def helper_code(rom):return dict(zip(range(HELPER,HELPER+40,4),struct.unpack_from('>10I',rom,0x1704F4)))

class Oracle(FactoryOracle):
    def __init__(self,words,memory,case=Case(),entry=ENTRY,connected=None,args=None):
        self.home=STACK+case.phase
        super().__init__(words,memory,case,entry=entry,s=symbols(),connected=connected,arguments=arguments(case)if args is None else args)
    def record_call(self,t):
        assert t==HELPER,hex(t);a=tuple(map(u32,self.arguments(2)));self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        assert t==HELPER;args=arguments(self.case);answer=selected(self.calls[-1][1][0],self.case);effect(self.memory,self.case,args,self.home)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=u32(answer)

class CallerOracle(render.Oracle):
    def __init__(self,words,memory,rc,case=Case(),connected=None,provider=False):
        self.combiner_case=case;self.provider=provider
        super().__init__(words,memory,rc,entry=render.CALLER,arguments=(render.GFX,render.ACTOR,u32(rc.view)),connected=connected,reference_leaf=True)
    def record_call(self,t):
        if t==HELPER:
            a=tuple(map(u32,self.arguments(2)));self.calls.append((t,a));self.events.append(('CALL',t,a))
        else:super().record_call(t)
    def hook(self,t):
        if t!=ENTRY:return super().hook(t)
        assert self.provider
        e=reference(self.memory,self.combiner_case,home=self.r[29],args=self.calls[-1][1],connected=True);self.memory=e['memory'];self.calls.extend(e['calls']);self.events.extend(('CALL',t,a)for t,a in e['calls'])
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=e['value']

def caller_fixture(rc,case,flags=0,enabled=1,visible=255,attached=0,animation=255):
    assert not case.alias and not case.mutation and case.result is None
    m=render.caller_fixture(rc,flags,enabled,visible,attached,animation)
    # The renderer's existing color arena overlaps part of this table. Extend
    # that arena only; reject any unexpected pre-existing overlap elsewhere.
    for p,n in((TABLE-32,4160),(CACHE-32,128)):
        for i in range(n):
            a=p+i
            if a in m:assert 0x800A4AC8<=a<0x800A4AC8+2048
            else:m[a]=(i*29+case.seed*11+90)&255
    for i,v in enumerate(table_bytes(case.pattern,case.seed)):m[TABLE+i]=v
    wr(m,CACHE,case.cache,2)
    return m

def cases():
    for index,dirty_byte,same,pattern in itertools.product(range(256),(0,1,2,255),(0,1),(0,1)):
        yield Case(index=index,dirty=dirty_byte,same=same,pattern=pattern,seed=index%3)
    for result,cache,dirty_byte in itertools.product((0x8000,0xFFFF,0,0x7FFF),(0x8000,0xFFFF,0,0x7FFF),(0,1,255)):
        yield Case(result=result,cache=cache,dirty=dirty_byte,pattern=3)
    for alias,index,dirty_byte,pattern in itertools.product(range(1,7),(0,1,17,255),(0,1,255),(0,1,3)):
        yield Case(alias=alias,index=index,dirty=dirty_byte,pattern=pattern)
    for mutation,index,phase in itertools.product((1,2,3),(0,1,255,0xABCDFF80),(0,8)):
        yield Case(mutation=mutation,index=index,phase=phase)
    for index in(0xFFFFFF00,0xABCDEF01,0x800000FF):yield Case(index=index,pattern=3)

def native_cases():return tuple(case for case in cases()if not case.alias and not case.phase and not case.mutation)
