import json,struct
from dataclasses import replace
from tools.tests import game_paired_packet_constructors_guest as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
START=0x1514d248;END=0x1514d270;TABLE=0x8008aa70
class Caller(g.Oracle):
 def record_call(self,t):
  if t==self.target:
   self.entered=True;self.target_args=tuple(self.arguments(1))
  else:super().record_call(t)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();data,fs,rs=parse_object(g.out/'paired.o');look={v[1]:v[2][1]for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())};window=struct.unpack_from('>10I',rom,START-0x15000000+0x2d4b0);reports=[]
 for name,entry,offset,width,glob,index in (('func_1514E00C',0x1514e00c,0x17b4bc,0x41a00000,0x800a5e08,1),('func_1514E194',0x1514e194,0x17b644,0x41800000,0x800a5e10,2)):
  assert struct.unpack_from('>I',rom,0x22f530+index*4)[0]==entry
  a,n=fs[name]['value'],fs[name]['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};candidate=bound_blob(data[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});retail=struct.unpack_from('>98I',rom,offset);count=0
  for case in g.cases():
   c=replace(case,phase=-0x180);sp=g.STACK+c.phase
   for words in (retail,candidate):
    m=Caller(words,case,entry,glob);m.case=c;m.target=entry;m.entered=False;m.r[29]=sp;m.r[2]=index;m.r[3]=0x5a
    g.put(m.memory,sp+0x48,g.OWNER);g.put(m.memory,TABLE+index*4,entry)
    code=dict(zip(range(entry,entry+4*len(words),4),words));code.update(zip(range(START,END,4),window));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=START
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('caller boundary not reached')
    assert m.entered and m.target_args==(g.OWNER,) and m.packet==g.expected(c,width,glob),(name,c,m.target_args)
    assert m.r[3]==0x5a and m.r[2]==0x87654321 and [x[0]for x in m.calls]==[g.ALLOC,g.ATTACH,g.EFFECT]
   count+=1
  reports.append(dict(target=name,table_index=index,cases=count,caller='func_1514D15C callback window',helpers='modeled'))
 report=dict(targets=reports,caller_window_only=True,full_parent_qualified=False,source_installed=False);(g.out/'window_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
