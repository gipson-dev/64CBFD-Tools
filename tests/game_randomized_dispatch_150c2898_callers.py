"""Authentic table-selected caller window and mixed float/stack ABI."""
from dataclasses import replace
import csv,io,itertools,json,struct
from tools.experiments import game_randomized_dispatch_150c2898_recovery as s
from tools.tests import game_randomized_dispatch_150c2898_oracle as g
from tools.tests.game_animation_timeline_oracle import bits
from tools.tests.test_game_point_transform_match import put
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
START,END,TABLE=0x15134b78,0x15134bf4,0x80089afc
class Caller(g.Oracle):
 def record_call(self,t):
  if t==s.ENTRY:
   self.indirect_called=True
   assert (self.f[12],self.f[14],self.r[6],self.r[7],*self.arguments(7)[4:])==(*self.case.position,*self.case.vector,g.OWNER)
  else:super().record_call(t)

def main():
 rom=(s.ROOT/'conker/conker.us.bin').read_bytes();window=list(struct.unpack_from('>31I',rom,0x162028));assert window[-2:]==[0x0320f809,0]
 assert struct.unpack_from('>I',rom,0x22e5d4)[0]==s.ENTRY
 programs=s.programs();count=0
 def run(words,phase=0,mutation=0,slot=6,changed=None):
  c=g.Case(position=(bits(1.5),bits(.25),bits(5.5)),vector=(bits(2.),bits(-3.),bits(4.)),phase=phase,mutation=mutation)
  initial=g.fixture(c);home=g.STACK+phase;initial[g.OWNER+0x27]=slot
  for i,v in enumerate((1.,2.,3.)):put(initial,home+0x90+4*i,bits(v))
  put(initial,home+0x8c,bits(4.));put(initial,g.OWNER+0x1c,bits(2.))
  for i in range(8):put(initial,TABLE+4*i,struct.unpack_from('>I',rom,0x22e5bc+4*i)[0])
  caller=window[:]
  if changed is not None:caller[changed]^=4
  code=dict(zip(range(s.ENTRY,s.ENTRY+s.SIZE,4),words));code[END]=0
  m=Caller(caller,initial,c,entry=START,connected=code);m.r[16]=g.OWNER;m.r[17]=TABLE
  for reg,val in ((0,.125),(20,.25),(22,4.),(24,.5),(26,.75),(28,2.),(30,-3.)):m.f[reg]=bits(val)
  m.before=m.r[:];m.before_f=m.f[:];m.saved_f=m.f[20:].copy();m.indirect_called=False;m.code=WindowCode(m.code,m);m.code.ends=(END,)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('Missing original caller continuation')
  assert m.indirect_called;g.verify(m,initial,c)
 for phase,mutation in itertools.product((0,8),(0,1)):
  for words in programs:run(words,phase,mutation)
  count+=1
 controls=0
 for kw in (dict(slot=5),dict(changed=4)):
  try:run(programs[0],**kw)
  except (AssertionError,KeyError):controls+=1
  else:raise AssertionError('Incorrect caller/table control accepted')
 rows=list(csv.DictReader(io.StringIO((s.ROOT/'conker/retail_layout.us.txt').read_text())));end=max(int(r['end'],16) for r in rows if r['section']=='game')
 jal=0x0c000000|((s.ENTRY>>2)&0x3ffffff)
 calls=[i for i in range(0x2d4b0,0x2d4b0+end-0x15000000,4) if struct.unpack_from('>I',rom,i)[0]==jal]
 pointers=[i for i in range(0,len(rom)-3,4) if struct.unpack_from('>I',rom,i)[0]==s.ENTRY]
 assert not calls and pointers==[0x22e5d4]
 report=dict(caller_words=31,caller_cases=count,streams=2,table='D_80089AFC[6]',table_pointer_rom='0x22E5D4',indirect_jalr_va='0x15134BEC',negative_controls=controls,direct_jal_count=0,aligned_literal_pointers=len(pointers),complete_parent_not_claimed=True)
 (s.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
