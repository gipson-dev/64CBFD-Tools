import json,struct
from tools.tests import game_four_damping_callbacks_guest as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
START=0x15130A0C;END=0x15130A50;TABLE=0x80089760
class Caller(g.Oracle):
 def record_call(self,t):
  if t==self.target:self.called=True;self.target_args=tuple(self.arguments(2))
  else:super().record_call(t)
def run(m,window,ws,entry):
 code=dict(zip(range(START,END,4),window));code.update(zip(range(entry,entry+4*len(ws),4),ws));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
 try:m.run()
 except WindowBoundary:pass
 else:raise AssertionError('caller boundary not reached')
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();window=struct.unpack_from('>%dI'%((END-START)//4),rom,START-0x15000000+0x2d4b0);assert 0x0320f809 in window;reports=[]
 for target,owner,index in g.TARGETS:
  entry=int(target,16);retail=struct.unpack_from('>106I',rom,entry-0x15000000+0x2d4b0);candidate=g.words(target);assert struct.unpack_from('>I',rom,0x22e220+4*index)[0]==entry;count=0
  for c in g.cases():
   for ws in (retail,candidate):
    m=Caller(ws,c,entry);m.target=entry;m.called=False;m.r[7]=0;m.memory[g.RECORD+0x72]=index;g.put(m.memory,TABLE+4*index,entry);m.initial=dict(m.memory);run(m,window,ws,entry);expected,calls,result=g.reference(c,m.initial)
    assert m.called and m.target_args==(g.RECORD,g.STACK+c.phase+0x48) and END in m.visits
    assert (g.public(m.memory),m.calls,m.r[2],m.r[7])==(g.public(expected),calls,result,0),(target,c)
   count+=1
  assert retail.count(0x24020001)==1;zero=tuple(0x24020000 if w==0x24020001 else w for w in retail);controls=0
  for c in (next(x for x in g.cases() if x.tick==0),next(x for x in g.cases() if x.tick==1)):
   m=Caller(zero,c,entry);m.target=entry;m.called=False;m.r[7]=0;m.memory[g.RECORD+0x72]=index;g.put(m.memory,TABLE+4*index,entry);m.initial=dict(m.memory);run(m,window,zero,entry);expected,calls,_=g.reference(c,m.initial)
   assert m.called and (g.public(m.memory),m.calls,m.r[2],m.r[7])==(g.public(expected),calls,0,1);controls+=1
  reports.append(dict(target=target,index=index,cases=count,return_negative_controls=controls))
 report=dict(targets=reports,caller='func_151303EC callback window',table='D_80089760',full_parent_qualified=False,helpers='none',source_installed=False);(g.out/'window_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
