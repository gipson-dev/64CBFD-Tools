import itertools,json,struct,sys
from dataclasses import dataclass
from pathlib import Path
from tools.experiments import game_four_damping_callbacks_match as p
out=p.out;root=p.root
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.pad_generated_object import parse_object
TARGETS=(('150BB260','E8090',2),('150CAC28','F5800',9),('150CBCE0','F8590',7),('150CC8D4','F9430',8));RECORD=0x30000;TICK=0x800BE9E4
@dataclass(frozen=True)
class Case:
 tick:int;x:int;z:int;factor:int;phase:int=0;seed:int=0
def cases():
 values=((bits(1.),bits(-2.)),(bits(-0.),bits(.5)),(bits(-2.25),bits(3.75)),(bits(.125),bits(-.75)))
 for i,(tick,(x,z),factor,phase) in enumerate(itertools.product((0,1,2,3,4,5,7,8,9,15,16),values,(bits(0.),bits(-1.),bits(.5),bits(.75),bits(1.25)),(0,8))):yield Case(tick,x,z,factor,phase,i%3)
def fixture(c):
 m={STACK+i:(i*17+c.seed*13+165)&255 for i in range(-512,512)};m.update({RECORD+i:(i*19+c.seed*11+37)&255 for i in range(0xac)})
 for a,v in ((TICK,c.tick),(RECORD+0x58,c.x),(RECORD+0x60,c.z),(RECORD+0xa8,c.factor)):put(m,a,v)
 return m
def public(m):return {a:v for a,v in m.items() if not STACK-512<=a<STACK+512}
def reference(c,initial):
 m=dict(initial)
 for i in range(c.tick):
  put(m,RECORD+0x58,fp(read(m,RECORD+0x58),read(m,RECORD+0xa8),'mul'));put(m,RECORD+0x60,fp(read(m,RECORD+0x60),read(m,RECORD+0xa8),'mul'))
 return m,[],1
class Oracle(FactoryOracle):
 def __init__(self,words,c,entry):
  super().__init__(words,fixture(c),c,entry=entry,arguments=(RECORD,0x89abcdef));self.initial=dict(self.memory);self.before=self.r[:];self.before_f=self.f[:]
 def record_call(self,t):raise AssertionError(('unexpected call',hex(t)))
 def hook(self,t):raise AssertionError(('unexpected helper',hex(t)))
def words(target,tag='ptr_'):
 data,fs,rs=parse_object(out/(tag+target+'.o'));a,n=fs['func_'+target]['value'],fs['func_'+target]['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};look={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};return bound_blob(data[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es})
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();reports=[]
 for target,owner,index in TARGETS:
  entry=int(target,16);candidate=words(target);retail=struct.unpack_from('>106I',rom,entry-0x15000000+0x2d4b0);seen=set();count=0
  for c in cases():
   for ws in (retail,candidate):
    m=Oracle(ws,c,entry);m.run();expected,calls,result=reference(c,m.initial)
    assert (public(m.memory),m.calls,m.r[2])==(public(expected),calls,result),(target,c)
    assert m.r[16:24]==m.before[16:24] and m.r[28:]==m.before[28:] and m.f[20:]==m.before_f[20:]
    if ws is retail:seen.update(m.visits)
   count+=1
  visits=sum(entry+4*i in seen for i in range(106));assert visits==106,(target,visits);reports.append(dict(target=target,cases=count,retail_words_visited=visits))
 report=dict(targets=reports,helpers='none',valid_disjoint_record_only=True,source_installed=False);(out/'guest_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
