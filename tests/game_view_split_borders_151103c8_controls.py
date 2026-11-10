"""Compiled viewport and split-border counterexamples with completed witnesses."""
import json
from tools.experiments import game_view_split_borders_151103c8_match as p
from tools.tests import game_view_split_borders_151103c8_oracle as g
def main():
 old=(p.out/'frozen'/p.SOURCE).read_text(encoding='utf-8');s=(p.out/'selected-body.c').read_text(encoding='utf-8')
 variants={'wrong-stride':s.replace('* 0x180','* 0x100'),'wrong-left':s.replace('(s32)view->left','(s32)view->top'),'right-inclusive':s.replace('view->right - 1.0f','view->right'),'wrong-color':s.replace('D_800DBEA8[2]','D_800DBEA8[0]'),'mode-gate':s.replace('D_80082FA0 != 0','D_80082FA0 == 0'),'view-gate':s.replace('D_80082FA4 == 0','D_80082FA4 != 0'),'missing-sync':s.replace('        gDPPipeSync(commands++);',''),'fill-color':s.replace('0x00010001','0x00000000'),'scissor-view':s.replace('commands, 0xFF','commands, 0'),'horizontal-thickness':s.replace('>> 1) - 6','>> 1) - 5'),'vertical-thickness':s.replace('>> 1) + 1','>> 1) + 2'),'logical-half':s.replace('D_800BE624 >> 1','(u32)D_800BE624 >> 1'),'wrong-second-gate':s.replace('D_80082FA0 != 1','D_80082FA0 == 1'),'lost-fill-cursor':s.replace('commands = func_15110544','(void)func_15110544'),'lost-rectangle-cursor':s.replace('commands = func_1501A6CC','(void)func_1501A6CC')}
 cs=[g.Case(index=i,mode=mode,height=height,mutation=mu,after=after,returns=ret)for i in(0,1)for mode in(0,1,2)for height in(216,0xFFFFFFF1)for mu,after,ret in((0,0,0),(1,2,1),(4,1,1),(15,0,0))]
 report={}
 for label,selected in variants.items():
  assert selected!=s;obj,diag=p.compile_owner(p.root,p.out,p.proposal(old,selected),'control-'+label);assert not diag,diag;ws=g.words(obj);errors=0
  for c in cs:
   memory=g.fixture(c)
   if label=='wrong-stride'and c.index:
    for at,value in((0x24,3.),(0x28,61.),(0x2C,2.),(0x30,101.)):g.put(memory,g.VIEWS+c.index*0x100+at,g.bits(value))
   m=g.Oracle(ws,memory,c)
   try:m.run()
   except(AssertionError,KeyError,ValueError,g.ConversionBoundary):errors+=1;continue
   try:g.check(m,c)
   except AssertionError:report[label]=dict(case=c.__dict__,normal_completion=True,execution_errors_before_witness=errors);break
  assert label in report,(label,'no completed witness',errors)
 result=dict(controls=len(report),effective_compiled_controls=report,execution_errors_counted_as_witnesses=False);(p.out/'controls.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(controls=len(report),all_normal=True)),flush=True);return result
if __name__=='__main__':main()
