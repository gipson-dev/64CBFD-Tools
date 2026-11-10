"""Compiled action-dispatch counterexamples with normally completed witnesses."""
import json
from tools.experiments import game_event_dispatch_1509d780_match as p
from tools.tests import game_event_dispatch_1509d780_oracle as g
def main():
 old=(p.out/'frozen'/p.SOURCE).read_text(encoding='utf-8');source=(p.out/'selected-body.c').read_text(encoding='utf-8')
 variants={'wrong-flag':source.replace('D_800D9920 = 0','D_800D9920 = 1'),'missing-mask':source.replace(' & 0xFFF',''),'wrong-mask':source.replace('0xFFF','0xFF'),'wrong-byte':source.replace('record[7]','record[6]'),'signed-byte':source.replace('record[7]','(s8)record[7]'),'unsigned-half':source.replace('*(s16 *)','*(u16 *)'),'wrong-half-offset':source.replace('record + 6','record + 4'),'wrong-word-offset':source.replace('record + 4','record + 8'),'wrong-sound':source.replace('0x29, 0x18','0x28, 0x18'),'wrong-category':source.replace('0x20, 0x18','0x20, 0x19'),'missing-second-submit':source.replace('            func_151616D0(0x24, 0x28, 0);',''),'reversed-submits':source.replace('0x23, 0x28','0x25, 0x28').replace('0x24, 0x28','0x23, 0x28').replace('0x25, 0x28','0x24, 0x28'),'wrong-case':source.replace('case 41:','case 40:'),'missing-case':source.replace('            func_150B3DD0();',''),'wrong-release-command':source.replace('command >> 6','command'),'wrong-lookup-gate':source.replace('actor != NULL','actor == NULL'),'wrong-null-result':source.replace('return 0;','return 1;')}
 cs=[g.Case(command=cmd,found=found)for cmd,found in((2,1),(9,0),(9,1),(36,1),(39,1),(19,1),(18,1),(38,1),(21,1),(22,1),(41,1),(8,1),(4,1))]
 report={}
 for label,selected in variants.items():
  proposed=p.proposal(old,selected)
  if label=='signed-byte':proposed=proposed.replace('void func_150F9720(u8);','void func_150F9720(s32);')
  if label=='unsigned-half':proposed=proposed.replace('void func_151D2718(s16);','void func_151D2718(u16);')
  obj,diag=p.compile_owner(p.root,p.out,proposed,'control-'+label);ws=g.words(obj);seen=0;errors=0
  # Controls keep retail table layout only when their emitted layout is unchanged.
  # Build each control's own compact pool, preserving the C compiler's destinations.
  from tools.tests.game_owner_pool import normalized_pools
  pools=normalized_pools(obj);offsets=[delta for at,name,delta in pools['.rodata'][1]]
  for c in cs:
   mem=g.fixture(c)
   for i,delta in enumerate(offsets):g.put(mem,g.TABLE+4*i,g.ENTRY+delta)
   # The switch lower bound can shift for a changed extreme case.
   lower=2
   if label=='wrong-case':assert len(offsets)==39
   m=g.Oracle(ws,mem,c)
   try:m.run()
   except(AssertionError,KeyError,ValueError):errors+=1;continue
   expected,calls,result=g.reference(m.initial,c)
   if(m.calls,g.public(m.memory),m.r[2])!=(calls,g.public(expected),result):seen=1;report[label]=dict(case=c.__dict__,normal_completion=True,execution_errors_before_witness=errors);break
  assert seen,(label,'no effective completed control',errors)
 result=dict(controls=len(report),effective_compiled_controls=report,execution_errors_counted_as_witnesses=False);(p.out/'controls.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
