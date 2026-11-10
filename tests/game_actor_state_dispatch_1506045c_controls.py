"""Require normal functional witnesses for independently compiled mistakes."""
import json
from tools.experiments import game_actor_state_dispatch_1506045c_match as p
from tools.tests import game_actor_state_dispatch_1506045c_oracle as g
def mutants(source):
 edits={
 'wrong-disable-value':('D_800C35EA == 1','D_800C35EA != 0'),
 'wrong-timer-edge':('D_800BE9E4 < *(u16 *)','D_800BE9E4 <= *(u16 *)'),
 'wrong-timer-amount':('-= (u32)D_800BE9E4;','-= (u32)D_800BE9E4 + 1U;'),
 'masked-fallback':('command = state[0x7C];','command = state[0x7C] & 0x7F;'),
 'wrong-mode-exclusion':('D_800BE9F0 != 0x29','D_800BE9F0 != 0x28'),
 'wrong-controller-bit':('D_800CC284 & 0x20','D_800CC284 & 0x10'),
 'stale-state-after-query':('    state = (u8 *)actor->unk31C;\n    if (state[0x78]','    if (state[0x78]'),
 'wrong-overlay-priority':('command = 0x2A;','command = 0x1A;'),
 'wrong-category12':('case 0xC: command = 8;','case 0xC: command = 9;'),
 'wrong-category35':('command = 0x1B;','command = 0x1C;'),
 'wrong-force-command':('command = 0x3C;','command = 0x3B;'),
 'wrong-recursive-mode':('func_1506045C(actor, buttons, flags, height, 1);','func_1506045C(actor, buttons, flags, height, 2);'),
 'stale-restore-pointer':('((u8 *)actor->unk31C)[0x75] = saved;','state[0x75] = saved;'),
 'stale-clear-pointer':('((u8 *)actor->unk31C)[0x78] = 0;','state[0x78] = 0;'),
 'missing-stun-button-clear':('        buttons = 0;','        buttons = 1;'),
 'wrong-final-flag':('flags & 0x4000','flags & 0x2000'),
 'dropped-result-forward':('height, force, result);','height, force, 0);')}
 result={}
 for n,(a,b)in edits.items():assert a in source,(n,a);result[n]=source.replace(a,b)
 return result
def main():
 source=(g.out/'selected-source.c').read_text();part=p.body(source,p.NAME);report={}
 cs=[g.Case(),g.Case(disabled=2),g.Case(timer=1,ticks=1),g.Case(timer=2,ticks=1),g.Case(command=0,fallback=0x81),g.Case(mode=0x29,controls=32,query=1),g.Case(controls=32,query=1),g.Case(controls=32,query=1,mutation=1),g.Case(overlay=0x2A),g.Case(identity=1,category=12),g.Case(identity=1,category=35),g.Case(force_command=1),g.Case(overlay=0x89),g.Case(overlay=0x89,mutation=4,flags=0x4000),g.Case(stunned=1),g.Case(flags=0x4000),g.Case(command=0,flags=0x4000),g.Case(extra=1)]
 for name,body in mutants(part).items():
  obj,_=p.compile_owner(p.root,p.out,source.replace(part,body),'negative-'+name);ws=g.words(obj)
  for i,c in enumerate(cs):
   m=g.Oracle(ws,g.fixture(c),c);m.run();expected,calls=g.reference(m.initial,c)
   if m.calls!=calls or g.public(m.memory)!=g.public(expected):
    report[name]=dict(case=i,normal_completion=True,execution_errors=0);break
  assert name in report,('No functional witness',name);print(name,json.dumps(report[name]),flush=True)
 result=dict(effective_compiled_controls=report,controls=len(report));(p.out/'controls.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':main()
