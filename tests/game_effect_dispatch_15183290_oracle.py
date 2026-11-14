from dataclasses import dataclass,replace
from pathlib import Path
import itertools,json,math,struct,sys
from tools.experiments import game_effect_dispatch_15183290_match as source
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
source.ROOT=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();source.OUT=source.ROOT/source.BUILD
ENTRY=0x15183290;POOL,SCENE,TABLE=0x800ddf5c,0x800dbff0,0x800a72f0
BASE,ACTOR,MARK=0x30000,0x50000,0x70000
FLOATS=tuple(range(0x800a7320,0x800a7344,4))
COUNTS={0x15177f90:11,0x151838b0:1,0x15175390:18,0x15184118:1,
        0x15174bf0:9,0x151839f0:2,0x15174fa4:10,0x15183acc:1,0x15183974:1,0x1517aa20:5}
u32=lambda n:n&0xffffffff
TABLE_WORDS=struct.unpack_from('>12I',(source.ROOT/'conker/conker.us.bin').read_bytes(),0x24bdb0)
class ConversionBoundary(Exception):pass
@dataclass(frozen=True)
class Case:
    kind:int=0
    busy:tuple=(1,0,0xff,0)
    values:tuple=(0xffff8000,0x7fffffff,0x80000000,0x12345680,0x87654321,0xffffffff,0x80000001,0x12345678,0x89abcdef)
    view:int=1
    valid:int=1
    mode:int=0
    phase:int=0
    seed:int=0
    coords:tuple=(0x414c0000,0xc1a40000,0x3f000000)
    real_predicate:bool=False

def args(c):return tuple(map(u32,(*c.values[:4],c.kind,c.values[4],c.view,*c.values[5:])))
def scene(c):return u32(BASE+u32(c.view)*0x9a0+0x3d0)
def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-512,512)}
    for i,v in enumerate(args(c)):put(m,STACK+c.phase+4*i,v)
    for i,v in enumerate(c.busy):m[POOL+i]=v
    put(m,SCENE,BASE);put(m,scene(c),ACTOR)
    for i,v in enumerate(c.coords):put(m,ACTOR+0x14+4*i,v)
    put(m,ACTOR+0x3c,bits(3.25));put(m,MARK,0)
    put(m,ACTOR+0x31c,0 if not c.valid and c.seed&1 else 0x60000);m[0x60057]=int(bool(c.valid))
    for i,v in enumerate(TABLE_WORDS):put(m,TABLE+4*i,v)
    for i,a in enumerate(FLOATS):put(m,a,bits(.125*(i+1)+c.seed%3))
    return m
def effects(m,c,ordinal,target):
    put(m,MARK,u32(ordinal*0x1020304^target))
    if c.mode&1:
        for i in range(4):m[POOL+i]=(ordinal*17+i)&255
        put(m,SCENE,BASE+0x1000);put(m,scene(c),ACTOR+0x1000)
        for i,a in enumerate(FLOATS):put(m,a,bits(ordinal*.25+i+.5))
    if c.mode&2:
        for i in range(11):put(m,STACK+c.phase+4*i,0x87650000+ordinal*0x100+i)

def reference(initial,c):
    m=dict(initial);calls=[];slot=next((i for i in range(4) if not m[POOL+i]),4)
    if slot==4:return m,calls,0xffffffff
    h=STACK+c.phase;arg=lambda i:read(m,h+i*4)
    for i in (7,8,9):put(m,h+i*4,u32(arg(i)<<4))
    actor=read(m,u32(read(m,SCENE)+u32(arg(6)*0x9a0)+0x3d0));kind=arg(4)
    def call(target,*a):
        calls.append((target,tuple(map(u32,a))))
        if target!=0x15184118 or not c.real_predicate:effects(m,c,len(calls),target)
    def packet(scale,vals):
        return (arg(3),slot,arg(0),arg(1),arg(2),*vals,read(m,scale),bits(.5),arg(10))
    if kind in (0,1):call(0x15177f90,arg(3)&255,0 if kind==0 else 0x800cc2e4,0xfe,arg(0),arg(1),arg(2),0,0x7fff,255,1,0)
    elif kind==2:
        call(0x151838b0,0);call(0x15175390,*packet(FLOATS[0],(63,arg(6),30,0,0x30003,10,0,0,1,2)))
    elif kind==3:
        call(0x15184118,actor)
        if not c.valid:return m,calls,0xffffffff
        call(0x15174bf0,arg(3),slot,arg(0),arg(1),arg(2),arg(6),read(m,FLOATS[1]),bits(.5),arg(10))
    elif kind==8:return m,calls,0xffffffff
    elif kind in (4,10):
        if kind==4:call(0x151839f0,7,10)
        else:call(0x15183acc,7)
        call(0x15174fa4,arg(3),slot,arg(0),arg(1),arg(2),u32(arg(7)<<2),arg(6),int(kind==10),read(m,FLOATS[2 if kind==4 else 3]),bits(.5))
    elif kind in (5,11):
        for index in (2,3,4,5):call(0x15183acc,index)
        call(0x15175390,*packet(FLOATS[5 if kind==5 else 4],(arg(7),arg(6),arg(8),arg(9),0x4d,0x15,3,2,-1,2 if kind==5 else 0)))
    elif kind==6:
        call(0x15183974,8);call(0x15175390,*packet(FLOATS[6],(arg(7),arg(6),arg(8),arg(9),0x7d,0x44,2,8,-1,2)))
    elif kind==7:
        call(0x15183acc,6);a=packet(FLOATS[7],(arg(7),arg(6),arg(8),arg(9),0x4d,0x14,0,6,0,2));call(0x15175390,*a[:-2],read(m,FLOATS[8]),a[-1])
    elif kind==9:
        coords=[floating(read(m,actor+0x14+4*i)) for i in range(3)]
        if any(not math.isfinite(v) or not -2147483648<=v<2147483648 for v in coords):return m,calls,None
        call(0x1517aa20,read(m,actor+0x3c),*map(math.trunc,coords),arg(3))
    if kind!=9:m[POOL+slot]=1
    return m,calls,slot

class Oracle(FactoryOracle):
    def __init__(self,words,initial,c,entry=ENTRY,connected=None,arguments=None):
        super().__init__(words,initial,c,entry=entry,arguments=args(c) if arguments is None else arguments,connected=connected)
        self.initial_r=self.r[:];self.initial_f=self.f[:]
    def execute(self,w):
        if w>>26==17 and w>>21&31==16 and w&63==13:
            v=floating(self.f[w>>11&31])
            if not math.isfinite(v) or not -2147483648<=v<2147483648:raise ConversionBoundary
            self.f[w>>6&31]=u32(math.trunc(v))
        else:super().execute(w)
    def record_call(self,t):
        if t==ENTRY:a=tuple(self.arguments(11))
        else:
            assert t in COUNTS,hex(t);a=list(self.arguments(COUNTS[t]))
            if t==0x1517aa20:a[0]=self.f[12]
            a=tuple(a)
        self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        effects(self.memory,self.case,sum(t!=ENTRY for t,_ in self.calls),t)
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011
        self.r[2]=self.case.valid if t==0x15184118 else (0xffffffff if self.case.seed&1 else 0)

def bound(obj):
    raw,refs=payload(obj,source.NAME);s={n:TABLE if n in ('.rodata','jtbl_800A72F0') else int(n.split('_')[1],16) for rows in refs.values() for _,n in rows};return bound_blob(raw,refs,s)
def public(m):return {a:v for a,v in m.items() if not STACK-512<=a<STACK+512}
def state(m):return m.memory,m.r,m.f,m.calls,m.trace,m.hi,m.lo
def cases():
    for k,busy,valid,mode,phase in itertools.product((*range(12),12,0x80000000,0xffffffff),((0,0,0,0),(1,0,255,0),(1,2,255,0),(1,2,3,4)),(0,1),(0,1,2,3),(0,8)):
        yield Case(k,busy,valid=valid,mode=mode,phase=phase,seed=k&255)
    for i in range(256):
        yield Case(i,((i+1)&255,i,0,255),view=(0,1,3,0xffffffff,0x80000001)[i%5],seed=i)

def verify(m,initial,c):
    want,calls,result=reference(initial,c)
    assert (public(m.memory),m.calls)==(public(want),calls),(c,m.calls,calls)
    if result is not None:
        assert m.r[2]==result,(c,m.r[2],result)
        assert m.r[16:24]==m.initial_r[16:24] and m.r[29]==m.initial_r[29] and m.f[20:]==m.initial_f[20:]
    # Incoming parameter homes deliberately change, even on unsupported kinds.
    for i in (7,8,9):assert read(m.memory,STACK+c.phase+4*i)==read(want,STACK+c.phase+4*i)

def main():
    programs=[bound(source.OUT/name) for name in ('retail.o','selected.o','guarded.o')];assert programs[0]==programs[2]
    count=0;seen=set()
    for c in cases():
        initial=fixture(c);models=[]
        for ws in programs:
            m=Oracle(ws,initial,c).run();verify(m,initial,c);models.append(m)
        assert state(models[0])==state(models[2]);seen.update(models[0].visits);count+=1
    assert seen==set(range(ENTRY,ENTRY+392*4,4)),len(seen)
    prefixes=0
    for k in range(12):
        c=Case(k,mode=3);initial=fixture(c);full=Oracle(programs[0],initial,c).run()
        for cut in range(full.all_accesses):
            models=[]
            for ws in (programs[0],programs[2]):
                m=Oracle(ws,initial,c);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError('Missing memory boundary')
                models.append(m)
            assert state(models[0])==state(models[1]);prefixes+=1
    invalid=0
    for i,v in itertools.product(range(3),(0x7f800000,0xff800000,0x7fc01234,0x4f000000)):
        coords=list(Case().coords);coords[i]=v;c=Case(9,coords=tuple(coords));initial=fixture(c);models=[]
        for ws in programs:
            m=Oracle(ws,initial,c)
            try:m.run()
            except ConversionBoundary:pass
            else:raise AssertionError('Missing float conversion boundary')
            verify(m,initial,c);models.append(m)
        assert state(models[0])==state(models[2]);invalid+=1
    callers=0;rom=(source.ROOT/'conker/conker.us.bin').read_bytes()
    window=struct.unpack_from('>23I',rom,0xcf9b8)
    assert window[-2]==0x0d460ca4 and window[-1]==0xafae0018,hex(window[-1])
    for k,mode,valid in itertools.product(range(12),(0,1,3),(0,1)):
        c=Case(k,values=(0xffff8000,50,32767,0xab,0xffff8000,0xfffffe12,0x80,0xef,0x89abcdef),mode=mode,valid=valid)
        initial=fixture(c);record=0x90000
        for a,v in ((0,0x8000),(2,0xffe2),(4,0x7fff),(6,0x8000)):put(initial,record+a,v,2)
        put(initial,record+0x18,0xfe1280ab);put(initial,record+0x1c,0xef050000);put(initial,record+0x20,c.values[-1]);put(initial,STACK+0x44,c.view)
        models=[]
        for ws in programs:
            connected=dict(zip(range(ENTRY,ENTRY+1568,4),ws));connected[0x150a2564]=0
            m=Oracle(window,initial,c,entry=0x150a2508,connected=connected,arguments=(0,))
            m.r[2]=k;m.r[16]=record;m.before=m.r[:];m.initial_r=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(0x150a2564,)
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing caller end')
            assert m.calls.pop(0)==(ENTRY,args(c)),(k,m.calls)
            verify(m,initial,c);models.append(m)
        assert state(models[0])==state(models[2]);callers+=1
    predicate=0;predvisits=set();code=dict(zip(range(0x15184118,0x15184144,4),struct.unpack_from('>11I',rom,0x1b15c8)))
    for valid,seed,mode,phase in itertools.product((0,1),(0,1),(0,1,3),(0,8)):
        c=Case(3,valid=valid,seed=seed,mode=mode,phase=phase,real_predicate=True);initial=fixture(c);models=[]
        for ws in programs:
            m=Oracle(ws,initial,c,connected=code).run();verify(m,initial,c);models.append(m);predvisits.update(m.visits)
        assert state(models[0])==state(models[2]);predicate+=1
    assert len(set(code)&predvisits)==10
    report={'guest_cases':count,'visited_words':len(seen),'memory_prefixes':prefixes,'conversion_prefixes':invalid,'caller_cases':callers,'real_predicate_cases':predicate,'predicate_reachable_words':10}
    (source.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
