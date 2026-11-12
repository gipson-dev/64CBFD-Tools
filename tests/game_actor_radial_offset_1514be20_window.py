import itertools,json,struct
from tools.tests import game_actor_radial_offset_1514be20_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
OWNER=0x50000;PAYLOAD=0x60000
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.entered=True;self.target_args=tuple(self.arguments(1))
  else:super().record_call(t)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();text,fs,rs=parse_object(g.out/'independent-selected.o');a,n=fs['func_1514BE20']['value'],fs['func_1514BE20']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n};look={v[1]:v[2][1] for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(text[a:a+n],refs,{nm:look[nm] for es in refs.values() for _,nm in es});retail=struct.unpack_from('>76I',rom,0x1792D0)
 reports={}
 for label,start,end in (('effect',0x1518FC0C,0x1518FC30),('update',0x1514C26C,0x1514C274)):
  words=struct.unpack_from('>%dI'%((end-start)//4),rom,start-0x15000000+0x2D4B0);assert 0x0D452F88 in words;count=0
  for c in (g.Case(*v) for v in itertools.product((-100.,0.,200.),(-100.,0.,200.),(-100.,0.,200.),(0.,.5,1.,2.),(0,1))):
   sample,expected=g.reference(c)
   if label=='effect':
    expected.update({OWNER+i:(i*7+5)&255 for i in range(0x40)});expected.update({PAYLOAD+i:(i*11+3)&255 for i in range(12)});g.put(expected,OWNER+0x2c,g.ACTOR)
    for i,v in enumerate((c.x,c.y,c.z)):g.put(expected,PAYLOAD+4*i,g.bits(v))
   for ws in (retail,candidate):
    m=Caller(ws,c);m.entered=False
    if label=='effect':
     m.memory.update({OWNER+i:(i*7+5)&255 for i in range(0x40)});m.memory.update({PAYLOAD+i:(i*11+3)&255 for i in range(12)});g.put(m.memory,OWNER+0x2c,g.ACTOR)
     for i,v in enumerate((c.x,c.y,c.z)):g.put(m.memory,PAYLOAD+4*i,g.bits(v))
     m.r[4]=OWNER;m.r[5]=PAYLOAD
    else:m.r[29]=g.STACK-0x20;g.put(m.memory,m.r[29]+0x18,g.ACTOR)
    code=dict(zip(range(start,end,4),words));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));code[end]=0;m.code=WindowCode(code,m);m.code.ends=(end,);m.entry=start
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('caller boundary not reached')
    assert m.entered and m.target_args==(g.ACTOR,) and end in m.visits,(label,c,'caller outcome')
    assert m.sample==sample and len(m.calls)==1 and m.r[2]==c.outcome,(label,c,'helper')
    assert g.public(m.memory)==expected,(label,c,'memory')
   count+=1
  reports[label]=count
 report=dict(cases=reports,callers={'effect':'func_1518FC04','update':'func_1514C258'},helper='modeled',full_parents_qualified=False,source_installed=False);(g.out/'caller_1514BE20_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
