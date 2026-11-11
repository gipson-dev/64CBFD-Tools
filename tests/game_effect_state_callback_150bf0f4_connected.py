import json,struct
from dataclasses import replace
from tools.tests import game_effect_state_callback_150bf0f4_oracle as g
from tools.tests.test_game_point_transform_match import put,read
PARENT=0x1516D678;END=0x1516D738;RELEASE=0x1516972C;TABLE=0x8008CBA0;BINDING=0x32000;MARK=0x33000
class Connected(g.Oracle):
 def record_call(self,t):
  assert t in(g.ENTRY,RELEASE),hex(t);self.calls.append((t,tuple(self.arguments(1))))
 def hook(self,t):
  assert t==RELEASE and self.calls[-1][1]==(g.RECORD,);put(self.memory,MARK,0x13579BDF)
  for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();parent=struct.unpack_from('>48I',rom,PARENT-0x15000000+0x2D4B0);retail=struct.unpack_from('>74I',rom,0xEC5A4);candidate=g.words('independent-selected');count=0;visits=set();release_count=0
 for c in g.cases():
  for linked in (0,1):
   machines=[]
   for ws in(retail,candidate):
    m=Connected(ws,c);m.memory[g.RECORD+0x23]=8;put(m.memory,TABLE+32,g.ENTRY);put(m.memory,g.RECORD+0x30,BINDING if linked else 0);put(m.memory,MARK,0);put(m.memory,BINDING+4,0x7a7a,2);m.initial=dict(m.memory)
    code=dict(zip(range(PARENT,END,4),parent));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));m.code.update(code);m.entry=PARENT
    initial=dict(m.memory);active=c.active
    if active:
     value=g.signed(active-c.tick);active=0 if value<0 else value&255;initial[g.RECORD+0x24]=active
    expected,result=g.reference(replace(c,active=active),initial)
    if result:
     if linked:put(expected,BINDING+4,0,2)
     put(expected,MARK,0x13579BDF)
    else:
     old=g.signed16(read(expected,g.RECORD+0x10,2))*256+expected[g.RECORD+0x25];rate=g.signed16(read(expected,g.RECORD+0x18,2));fixed=g.signed(old+rate*c.tick);put(expected,g.RECORD+0x10,fixed>>8,2);expected[g.RECORD+0x25]=fixed&255
    m.run();assert g.public(m.memory)==g.public(expected),(c,linked,'memory');assert m.calls==([(g.ENTRY,(g.RECORD,))]+([(RELEASE,(g.RECORD,))]if result else [])),(c,m.calls,result)
    machines.append(m)
   assert g.public(machines[0].memory)==g.public(machines[1].memory) and machines[0].calls==machines[1].calls;count+=1;release_count+=result;visits.update(machines[0].visits)
 report=dict(cases=count,original_parent='func_1516D678',original_parent_words_visited=sum(PARENT+4*i in visits for i in range(48)),return_one_release_paths=release_count,release_helper_modeled=True,linked_and_null_binding=True,source_installed=False)
 (g.out/'connected-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
