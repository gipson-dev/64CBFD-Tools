import itertools,json,struct
from tools.tests import game_localized_trail_preset_151dbaa8_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
END=0x15029BA4
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY:self.entered=True;self.target_args=tuple(self.arguments(5))
  else:super().record_call(t)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();text,fs,rs=parse_object(g.out/'independent-selected.o');a,n=fs['func_151DBAA8']['value'],fs['func_151DBAA8']['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n};look={v[1]:v[2][1] for v in symbol_rows((g.root/'conker/build/conker.us.elf').read_bytes())};candidate=bound_blob(text[a:a+n],refs,{nm:look[nm] for es in refs.values() for _,nm in es});retail=struct.unpack_from('>75I',rom,0x208F58)
 cases=[g.Case(*v) for v in itertools.product(((0,0,0),(0x3f800000,0xc0200000,0x40400000),(0x7fc01234,0x80000000,0x7f800000)),(-1,0,1,10),(0,6,12),(0,255,0x78),(0,),(0,1))]
 reports={}
 for label,start in (('first',0x15029564),('second',0x15029B78)):
  words=struct.unpack_from('>4I',rom,start-0x15000000+0x2D4B0);assert words[0]==0x0d476eaa;count=0
  for c in cases:
   expected,values,args=g.reference(c)
   for ws in (retail,candidate):
    m=Caller(ws,c);m.entered=False;m.r[29]=g.STACK-0x100;m.r[4]=g.POINT;m.r[5]=c.count&0xffffffff;m.r[6]=c.selector;m.r[7]=c.mode
    code=dict(zip(range(start,start+16,4),words));code.update(zip(range(g.ENTRY,g.ENTRY+4*len(ws),4),ws));code[END]=0;m.code=WindowCode(code,m);m.code.ends=(END,);m.entry=start
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('caller boundary not reached')
    assert m.entered and m.target_args==(g.POINT,c.count&0xffffffff,c.selector,c.mode,0) and END in m.visits and m.r[2]==1,(label,c,'caller outcome')
    assert g.public(m.memory)==expected and m.packet=={k:v for k,(_,v) in values.items()} and m.call_args==args,(label,c,'packet or memory')
   count+=1
  reports[label]=count
 report=dict(cases=reports,caller='func_150265CC call windows',helper='modeled',full_parent_qualified=False,source_installed=False);(g.out/'caller_151DBAA8_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
