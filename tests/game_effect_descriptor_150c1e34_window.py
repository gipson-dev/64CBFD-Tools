import json,struct
from tools.tests import game_effect_descriptor_150c1e34_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob

class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.entered=True;self.target_args=tuple(self.arguments(15))
  else:super().record_call(t)

def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();data,fs,rs=parse_object(g.out/'independent-selected.o')
 a,n=fs['func_150C1E34']['value'],fs['func_150C1E34']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n}
 look={v[1]:v[2][1] for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())}
 candidate=bound_blob(data[a:a+n],refs,{nm:look[nm] for es in refs.values() for _,nm in es})
 retail=struct.unpack_from('>72I',rom,0xEF2E4)
 windows=(('ring',0x1514C3BC,0x1514C3FC,(3.,3.,7.5,4.,3.,5.)),
  ('line',0x1514C5B4,0x1514C604,(-.5,2.,3.,4.,3.,5.)),
  ('random-ring',0x1514C7B0,0x1514C7F4,(3.,3.,7.5,4.,3.,5.)),
  ('offset-ring',0x1514C9C8,0x1514CA10,(1.25,5.,2.5,3.,4.,5.)))
 report={}
 for label,start,end,position in windows:
  raw=struct.unpack_from('>%dI'%((end-start)//4),rom,start-0x15000000+0x2d4b0)
  assert raw[-2]==0x0040f809,(label,hex(raw[-2]))
  count=0
  for scale in (0.,6.,-19.75,32767.):
   for rand in (0,1,15,0xffffffff):
    for seed in (0,1):
     c=g.Case(*position,scale,rand,0,seed)
     for ws in (retail,candidate):
      m=Caller(ws,c);m.entered=False;m.r[29]=g.STACK-0x180;m.r[2]=g.ENTRY;m.r[4:6]=[1,7]
      for i,v in ((2,1.25 if label=='offset-ring' else 7.5),(8,4.),(12,2.5),(20,-.5),(22,2.),(24,3.),(26,4.),(28,5.),(30,scale)):m.f[i]=g.bits(v)
      for i,v in ((16,0x77),(18,0x34),(20,0x56),(22,0x12345678),(23,0x9988),(30,0x5a)):m.r[i]=v
      g.put(m.memory,m.r[29]+0xac,g.bits(3.));g.put(m.memory,m.r[29]+0xb0,g.bits(5.));g.put(m.memory,m.r[29]+0x100,g.bits(scale))
      g.put(m.memory,m.r[29]+0xb0,0x40500000 if label=='random-ring' else g.bits(5.))
      words=dict(zip(range(start,end,4),raw));words.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));words[end]=0
      m.code=WindowCode(words,m);m.code.ends=(end,);m.entry=start
      try:m.run()
      except WindowBoundary:pass
      else:raise AssertionError((label,'caller boundary not reached'))
      assert m.entered and m.r[2]==1,(label,c,'call outcome')
      expected=g.args(c)
      for i in (2,3,4,5,6,7,12):assert m.target_args[i]==expected[i],(label,i,hex(m.target_args[i]),hex(expected[i]))
      assert m.packet=={k:v for k,(_,v) in g.reference(c).items()},(label,c,m.packet,g.reference(c))
      assert [x[0] for x in m.calls]==[g.COLOR,g.COLOR,g.RANDOM,g.EMIT]
     count+=1
  report[label]=count
 result=dict(cases=report,helpers='modeled',caller_windows_only=True,full_callers_qualified=False,source_installed=False)
 (g.out/'caller_150C1E34_screen.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
