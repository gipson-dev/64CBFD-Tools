"""Compiled semantic counterexamples; private addresses/padding are normalized."""
import json
from tools.experiments import game_owner_payload_effect_151b4cd0_match as p
from tools.tests import game_owner_payload_effect_151b4cd0_oracle as g
def observed(memory,calls,answer,packets,copies):
 normalized=[]
 for t,a in calls:
  if t==g.CREATE:a=(0,*a[1:])
  if t==g.COPY:a=(a[0],0,*a[2:])
  normalized.append((t,a))
 return g.public(memory),normalized,answer,[bytes(v for i,v in enumerate(packet)if i not in g.PADDING)for packet in packets],copies
def main():
 old=(p.out/'frozen'/p.SOURCE).read_text(encoding='utf-8');s=(p.out/'selected-body.c').read_text(encoding='utf-8');variants={
 'wrong-type-gate':s.replace('type == 99','type == 98'),'wrong-class-gate':s.replace('] == 2','] == 1'),'wrong-notification':s.replace('(40, owner, 22)','(40, owner, 21)'),
 'wrong-identity':s.replace('owner[0x3B]','owner[0x3A]'),'wrong-attachment':s.replace('attachment = 2','attachment = 1'),'wrong-vector':s.replace('-27.0f','-26.0f'),'wrong-scale':s.replace('value24 = D_800AA3D0','value24 = 0.0f'),
 'wrong-modulus':s.replace('% 21U','% 20U'),'wrong-duration-base':s.replace('+ 40;','+ 41;'),'wrong-flags':s.replace('flags = 6','flags = 4'),'wrong-kind':s.replace('kind = 8','kind = 9'),'wrong-callback':s.replace('callback = -1','callback = 0'),'wrong-mode':s.replace('mode = 7','mode = 6'),
 'wrong-payload-gate':s.replace('] == 1','] != 1'),'wrong-output-offset':s.replace('created + 0x58','created + 0x59'),'wrong-copy-size':s.replace('payload, 1','payload, 2'),'wrong-allocation-size':s.replace('&descriptor, 1,','&descriptor, 0,'),'wrong-selector':s.replace('1, selector, category','1, selector ^ 1, category'),'wrong-result':s.replace('return created;','return created ? owner : NULL;')}
 block=s[s.index('    if (D_800A3FE6[type * 0x10] == 1)'):s.index('    created = func_1513418C')]
 variants['early-payload-snapshot']=s.replace(block,'').replace('    descriptor.duration =',block+'    descriptor.duration =')
 variants['early-scale-snapshot']=s.replace('    descriptor.value24 = D_800AA3D0;\n','').replace('    func_1516962C(40, owner, 22);','    descriptor.value24 = D_800AA3D0;\n    func_1516962C(40, owner, 22);')
 cs=[g.Case(kind=k,class_byte=cl,mutation=mu,after=after,outcome=o,random=r)for k,cl,mu,after,o,r in((1,1,0,0,1,0xFFFFFFFF),(1,1,4,0,1,20),(1,1,2,1,1,21),(1,2,0,0,1,0),(99,0,0,0,1,0),(1,0,0,0,0,0))];report={}
 for label,selected in variants.items():
  assert selected!=s;obj,diag=p.compile_owner(p.root,p.out,p.proposal(old,selected),'control-'+label);assert not diag,diag;ws=g.words(obj);errors=0
  for c in cs:
   m=g.Oracle(ws,g.fixture(c),c)
   try:m.run()
   except(AssertionError,KeyError,ValueError):errors+=1;continue
   expected=g.reference(m.initial,c)
   if observed(m.memory,m.calls,m.r[2],m.packets,m.copies)!=observed(*expected):report[label]=dict(case=c.__dict__,normal_completion=True,execution_errors_before_witness=errors);break
  assert label in report,(label,'No completed semantic witness',errors)
 result=dict(controls=len(report),effective_compiled_controls=report,private_addresses_and_padding_not_witnesses=True,execution_errors_counted_as_witnesses=False);(p.out/'controls.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(controls=len(report),all_normal=True)),flush=True);return result
if __name__=='__main__':main()
