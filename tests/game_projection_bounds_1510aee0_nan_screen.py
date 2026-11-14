"""Compare quiet-NaN ordering under explicit operand-propagation assumptions."""
import itertools,json
from tools.tests import game_projection_bounds_1510aee0_guest_screen as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
staged=bound_blob(*payload(g.out/'staged.o',g.name),g.symbols)
counts={};examples={}
def is_nan(value):return value&0x7f800000==0x7f800000 and value&0x007fffff!=0
class NaNOracle(g.Oracle):
 prefer_left=True
 def execute(self,word):
  if word>>26==17 and (word>>21)&31==16 and (word&63) in (0,1,2,3):
   left=self.f[(word>>11)&31];right=self.f[(word>>16)&31]
   if is_nan(left) or is_nan(right):
    chosen=(left if is_nan(left) else right) if self.prefer_left else (right if is_nan(right) else left)
    self.f[(word>>6)&31]=chosen|0x00400000
    return
  super().execute(word)
for rule in ('left','right'):
 NaNOracle.prefer_left=rule=='left';counts[rule]={'candidate':0,'staged':0};cases=0
 for a,b,c,d in itertools.product((0x7fc00001,0x7fc10002),(0x7fc00003,0x7fc30004),(0,0x7fc50006),(0,0x7fc70008)):
  initial,args=g.fixture(2.,-2.,-5.,0,0)
  for offset,value in ((2,a),(6,b),(10,c),(14,d)):
   g.put(initial,g.MATRIX+offset*4,value if value else g.bits(1.) if offset==10 else 0)
  def observe(code):
   m=NaNOracle(code,initial.copy(),g.Case(),entry=g.entry,s={},arguments=args).run()
   return m.r[2],g.read(m.memory,g.OUTPUT),g.read(m.memory,g.OUTPUT+4)
  retail=observe(g.truth)
  for label,code in (('candidate',g.candidate),('staged',staged)):
   actual=observe(code)
   if actual!=retail:
    counts[rule][label]+=1
    examples.setdefault(rule+'-'+label,{'input':[hex(x) for x in (a,b,c,d)],'retail':[hex(x) for x in retail],'actual':[hex(x) for x in actual]})
  cases+=1
 assert cases==16 and counts[rule]['candidate']>0,counts
report={'cases_per_rule':cases,'modeled_payload_differences':counts,'examples':examples,'nan_rules':'left or right NaN operand wins; quiet bit set', 'hardware_rule_unverified':True,'fcsr_not_modeled':True,'uncredited':True}
(g.out/'nan-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
