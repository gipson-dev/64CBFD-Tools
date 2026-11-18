"""Connect the original radial call window to the complete trail callback."""
import itertools,json,struct
from tools.tests import game_snapshot_trail_151b0050_oracle as o
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
START,END,STOP=0x1514C3C4,0x1514C404,0x1514C42C

def run(programs):
 rom=(o.source.FROZEN/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>I',rom,0x22F514)[0]==o.ENTRY
 parent=list(struct.unpack_from('>16I',rom,0x179874));count=0
 class Connected(o.Oracle):
  def __init__(self,c,words):
   code={o.ENTRY+4*i:w for i,w in enumerate(words)};super().__init__(parent,o.fixture(c),c,entry=START,connected=code);self.called=[]
  def record_call(self,target):
   if target==o.ENTRY:self.called.append(tuple(self.arguments(15)))
   else:super().record_call(target)
 def machine(c,body):
  m=Connected(c,body);m.r[2]=o.ENTRY;m.r[4]=1;m.r[5]=7;m.r[7]=o.o.bits(-2.5-c.seed);m.r[18]=c.pitch;m.r[20]=c.heading;m.r[22]=9;m.r[23]=10;m.r[30]=c.channel
  for reg,value in((2,3.75+c.seed),(6,1.25+c.seed),(8,0.),(22,2.),(24,-2.5-c.seed),(26,0.),(28,3.75+c.seed),(30,4.)):m.f[reg]=o.o.bits(value)
  m.code[END]=0;m.code[STOP]=0;m.code=WindowCode(m.code,m);m.code.ends=(END,STOP)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('caller did not stop at window boundary')
  return m
 for pitch,mutation,phase,pattern in itertools.product((0,1,127,128,255),(0,1,2,4),(0,8),(0,2)):
  c=o.Case(seed=pitch%4,pitch=pitch,heading=8,channel=0xABCDEF80,mutation=mutation,phase=phase,pattern=pattern,duration=0xFFFFFFFF,color=0x80000000,request=1)
  expected,calls,packets=o.reference(o.fixture(c),c)
  for words in programs:
   m=machine(c,words);assert len(m.called)==1 and m.called[0][0:5]==o.args(c)[0:5]and m.called[0][8:10]==(pitch,8)and m.called[0][14]==c.channel
   assert o.o.public(m.memory)==o.o.public(expected)and m.service.calls==calls and m.service.packets==packets
   assert m.r[2]==1 and END in m.visits and STOP not in m.visits
  count+=1
 bad=programs[0][:];assert bad[-5]==0x24020001;bad[-5]=0x24020000
 m=machine(o.Case(pitch=1,heading=8,channel=0x80),bad);assert STOP in m.visits and END not in m.visits and m.r[2]==0
 report=dict(cases_per_stream=count,streams=len(programs),original_window_words=16,table_index=21,return_zero_control_stops_loop=True,full_parent_qualified=False)
 return report
