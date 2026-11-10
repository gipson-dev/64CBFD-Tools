"""Actual three caller windows connected to complete recursive target bodies."""
import itertools,json,struct
from dataclasses import replace
from tools.tests import game_actor_state_dispatch_1506045c_oracle as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
WINDOWS=((0x1504EF68,8,0x1504EF88),(0x1505F6F4,5,0x1505F708),(0x1505FEA8,9,0x1505FECC))
def machine(ws,rom,c,start,n,end):
 c=replace(c,secondary=c.secondary if start==0x1505F6F4 else 0,buttons=c.controls&65535 if start==0x1504EF68 else c.buttons)
 mem=g.fixture(c);g.put(mem,g.ACTOR+0x28,c.height);g.put(mem,0x800CC288,c.flags);g.put(mem,g.STACK+c.phase+0x68,c.buttons)
 code=dict(zip(range(g.ENTRY,g.ENTRY+796,4),ws));code[end]=0
 m=g.Oracle.__new__(g.Oracle);m.c=c
 window=struct.unpack_from('>%dI'%n,rom,start-0x15000000+0x2D4B0)
 FactoryOracle.__init__(m,window,mem,c,entry=start,arguments=(g.ACTOR,g.u32(c.buttons),g.u32(c.flags),g.u32(c.height),g.u32(c.secondary)),connected=code)
 m.r[16]=g.ACTOR;m.r[12]=g.u32(c.secondary);m.r[8]=0x12345678;m.f[12]=0x3F654321;m.f[14]=c.height
 m.before=m.r[:];m.before_f=m.f[:];m.initial=dict(m.memory);m.code=WindowCode(m.code,m);m.code.ends=(end,)
 return m,c
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();programs={'raw':g.words(g.out/'selected.o'),'original':struct.unpack_from('>199I',rom,0x8D90C)}
 cs=[g.Case(overlay=overlay,flags=flags,controls=32,query=1,mutation=mutation,timer=timer,secondary=secondary,seed=i%7,phase=(i&1)*8)for i,(overlay,flags,mutation,timer,secondary)in enumerate(itertools.product((0,1,0x1A,0x2A,0x89),(0,0x4000),(0,1,4,16,28),(0,1),(0,1)))]
 visits={};runs=0;pairs=0
 for start,n,end in WINDOWS:
  seen=set()
  for c in cs:
   machines=[]
   for label,ws in programs.items():
    m,effective=machine(ws,rom,c,start,n,end)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller window did not reach its recorded continuation')
    expected,calls=g.reference(m.initial,effective);entry=(g.ENTRY,tuple(map(g.u32,(g.ACTOR,effective.buttons,effective.flags,effective.height,effective.secondary))))
    assert m.calls==[entry]+calls,(hex(start),effective,m.calls,[entry]+calls)
    assert g.public(m.memory)==g.public(expected),(hex(start),effective)
    assert m.r[29]==g.STACK+c.phase and m.r[16]==g.ACTOR
    seen.update(pc for pc in m.visits if start<=pc<end);machines.append(m);runs+=1
   a,b=machines;assert (a.memory,a.r,a.f,a.calls,a.trace)==(b.memory,b.r,b.f,b.calls,b.trace),(hex(start),c);pairs+=1
  assert seen==set(range(start,end,4)),(hex(start),seen);visits[hex(start)]=len(seen)
 result=dict(cases_per_window=len(cs),executions=runs,full_state_and_access_trace_pairs=pairs,window_coverage=visits,all_three_external_JAL_sites=True,recursive_original_call_executed=True,full_large_parent_algorithms_qualified=False,staged_window_input_boundary=True,incidental_V0_preserved_in_guest=True)
 (g.out/'callers.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
