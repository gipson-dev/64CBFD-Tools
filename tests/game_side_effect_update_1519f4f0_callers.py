"""Real slot-5 dispatcher and the original height-query wrapper's three routes."""
from dataclasses import replace
from functools import lru_cache
import itertools,json,struct
from tools.experiments import game_side_effect_update_1519f4f0_match as s
from tools.tests import game_side_effect_update_1519f4f0_oracle as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
DISPATCH,RETIRE,PRIMARY,FALLBACK=0x15147740,0x1516972C,0x15047004,0x15045780

@lru_cache(None)
def retail(entry,n):
    off=entry-0x15000000+0x2D4B0;blob=(s.ROOT/'conker/conker.us.bin').read_bytes()[off:off+n*4]
    elf=(s.ROOT/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,entry,len(blob));assert elf[at:at+len(blob)]==blob,hex(entry)
    return struct.unpack('>'+str(n)+'I',blob)

def clobber(q,value):
    for i in range(4):q.put(q.r[29]+4*i,0xB5000000+i,4)
    for k in (1,2,3,*range(4,16),24,25):q.r[k]=0xA5000000+k
    q.f[:20]=[0xA5000000+i for i in range(20)];q.hi=q.lo=0xDEADBEEF;q.r[2]=value&0xFFFFFFFF

class Parent(g.Machine):
    def record_call(self,t):
        if t==g.QUERY:return super().record_call(t)
        assert t in (s.ENTRY,RETIRE),hex(t);self.calls.append((t,tuple(self.arguments(1)),b''))
    def hook(self,t):
        if t==g.QUERY:
            a=self.calls[-1][1];ordinal=sum(target==g.QUERY for target,args,snapshot in self.calls)-1
            clobber(self,g.query(self.memory,self.c,ordinal,a[0],a[3]));return
        assert t==RETIRE,hex(t)
        assert self.calls[-1][1]==(g.EFFECT,);g.put(self.memory,g.ALT+4,0x0BAD5EED);clobber(self,0xDEADBEEF)

def parent(streams):
    words=retail(DISPATCH,100);assert words[0]==0x27BDFFE0
    table=s.symbols()['D_8008A200'];elf=(s.ROOT/'conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,table,60)
    raw=elf[at:at+60];assert raw==(s.ROOT/'conker/conker.us.bin').read_bytes()[0x22ECC0:0x22ECFC]
    rows=struct.unpack('>15I',raw);assert rows[5]==s.ENTRY
    count=0
    for cap,kind,n,effects,hit,phase in itertools.product((2,5),(6,7),(0,1,4),(0,1,2,4,8,15),(0,1,2),(0,8)):
        c=g.Case(cap=cap,tail=cap-1,count=n,kind=kind,effects=effects,hit=hit,phase=phase)
        initial=g.fixture(c);g.put(initial,g.EFFECT+0x1E,0,2);initial[g.EFFECT+0x2F]=5;initial[g.EFFECT+0x30]=0
        for i,v in enumerate(raw):initial[table+i]=v
        expected,value,calls,fp=g.reference(initial,replace(c,phase=phase-32));expected_calls=[(s.ENTRY,(g.EFFECT,),b'')]+calls
        if not value:g.put(expected,g.ALT+4,0x0BAD5EED);expected_calls.append((RETIRE,(g.EFFECT,),b''))
        observations=[]
        for w in streams.values():
            code=dict(zip(range(s.ENTRY,s.ENTRY+s.SIZE,4),w));q=Parent(words,initial.copy(),c,entry=DISPATCH,connected=code).run()
            assert (g.public(q.memory,c),q.calls,q.fp_ops)==(g.public(expected,c),expected_calls,fp),('slot5',c,q.calls,expected_calls,[(hex(p),v,q.memory.get(p)) for p,v in g.public(expected,c).items() if v!=q.memory.get(p)][:8])
            observations.append((q.memory,q.calls))
        # Root private save homes differ; compare public state and full calls.
        count+=1
    return count

class ConnectedQuery(g.Machine):
    def __init__(self,w,m,c,route):
        self.route=route;self.root_queries=[];code=dict(zip(range(g.QUERY,g.QUERY+128,4),retail(g.QUERY,32)))
        super().__init__(w,m,c,connected=code)
    def record_call(self,t):
        if t==g.QUERY:
            super().record_call(t);self.root_queries.append(self.calls[-1]);return
        assert t in (PRIMARY,FALLBACK),hex(t)
        a=tuple(self.arguments(3 if t==PRIMARY else 4));root=self.root_queries[-1][1]
        assert a==((root[0],root[2],root[3]) if t==PRIMARY else root),(t,a,root)
        self.calls.append((t,a,b''))
    def hook(self,t):
        if t==PRIMARY:
            args=self.root_queries[-1][1];g.query(self.memory,self.c,len(self.root_queries)-1,args[0],args[3]);clobber(self,self.route)
        elif t==FALLBACK:clobber(self,self.c.hit)
        else:raise AssertionError(hex(t))

def queries(streams):
    count=0
    for route,cap,effects,phase in itertools.product((0,1,2),(2,5),(0,1,2,4,8,15),(0,8)):
        for hit in ((0,1) if route==0 else (0,) if route==1 else (1,)):
            c=g.Case(cap=cap,tail=cap-1,count=cap,effects=effects,phase=phase,hit=hit);initial=g.fixture(c)
            expected,result,calls,fp=g.reference(initial,c)
            for w in streams.values():
                q=ConnectedQuery(w,initial.copy(),c,route).run()
                assert (g.public(q.memory,c),q.r[2],q.root_queries,q.fp_ops)==(g.public(expected,c),result,calls,fp),('real query wrapper',route,c,q.calls)
                assert sum(t==PRIMARY for t,a,z in q.calls)==len(calls)
                assert sum(t==FALLBACK for t,a,z in q.calls)==(len(calls) if route==0 else 0)
            count+=1
    return count

def main():
    streams=s.programs();rom=(s.ROOT/'conker/conker.us.bin').read_bytes();jal=0x0C000000|((s.ENTRY>>2)&0x3FFFFFF)
    direct=[i for i in range(0x2D4B0,len(rom)-3,4) if struct.unpack_from('>I',rom,i)[0]==jal];assert not direct
    report=dict(original_dispatcher_words=100,slot=5,table_address='0x8008A200',parent_cases_per_stream=parent(streams),
                original_query_wrapper_words=32,query_routes=3,connected_query_cases_per_stream=queries(streams),streams=3,
                direct_JAL_sites=0,code_image_bytes=len(rom),full_asset_ROM_census=False,dispatcher_return_uncredited=True)
    (s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
