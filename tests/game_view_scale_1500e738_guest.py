from pathlib import Path
import struct
from tools.tests.game_script_sorted_insert_oracle import Oracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.experiments import game_view_scale_1500e738_match as screen
root,out=screen.ROOT,screen.OUT;ENTRY=0x1500E738
STATE,MODE=0x80082FA0,0x8008FD8C
FIELDS=(0x800DCA20,0x800DCA24,0x800DCA28,0x800DCA2C)
class View(Oracle):
 def __init__(self,words,m,entry):super().__init__(words,m,0,0,entry)
 def record_call(self,t):raise AssertionError(('unexpected call',hex(t)))
 def execute(self,word):
  if word>>26==32:
   rs,rt=(word>>21)&31,(word>>16)&31;imm=word&65535;imm=imm if imm<32768 else imm-65536
   self.dispatched_word=word;self.own_instruction=True
   try:v=self.get((self.r[rs]+imm)&0xFFFFFFFF,1)
   finally:self.own_instruction=False
   self.r[rt]=v if v<128 else (v-256)&0xFFFFFFFF;self.r[0]=0
  else:super().execute(word)
def fixture(state,mode,table,address):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-128,128)}
 for p in (STATE-4,MODE-4,*[v-4 for v in FIELDS]):
  for i in range(12):m[p+i]=0xA5
 put(m,STATE,state);put(m,MODE,mode,1)
 for i,b in enumerate(table):m[address+i]=b
 return m
def expected(state,mode):
 a,b=(0xA5,0xA5A5A5A5)
 if state==0:a,b=0,0x3F800000
 elif state==1:a,b=1,0x3F000000
 elif state in (2,3):a,b=2,0x3E800000
 signed=mode if mode<128 else mode-256
 if signed==2:c,d=1,0x3F000000
 elif signed in (3,4):c,d=2,0x3E800000
 elif 5<=signed<=8:c,d=3,0x3E000000
 elif 9<=signed<=16:c,d=4,0x3D800000
 else:c,d=0,0x3F800000
 return a,b,c,d
def run():
 obj=out/'variant-case1_default.o';_,fs,_=parse_object(obj);pos=fs['func_1500E738']['value'];candidate=sections(out/'variant-case1_default.elf');base=candidate['.text'][0]+pos
 raw=list(struct.unpack('>86I',candidate['.text'][1][pos:pos+344]));rbase,rtable=candidate['.rodata']
 retail=list(struct.unpack_from('>86I',(root/'conker/conker.us.bin').read_bytes(),0x3BBE8));gbase,gdata=sections(root/'conker/build/conker.us.elf')['.game_data'];table=gdata[0x800961D0-gbase:0x800961D0-gbase+64]
 count=0;seen=set()
 for state in (0,1,2,3,4,0xFFFFFFFF,0x80000000,0x7FFFFFFF):
  for mode in range(256):
   want=expected(state,mode)
   for words,entry,address,data in ((retail,ENTRY,0x800961D0,table),(raw,base,rbase,rtable)):
    m=fixture(state,mode,data,address);model=View(words,m,entry).run()
    got=(read(model.memory,FIELDS[0],1),read(model.memory,FIELDS[1]),read(model.memory,FIELDS[2],1),read(model.memory,FIELDS[3]))
    assert got==want,(state,mode,hex(entry),got,want)
    for p in (STATE,MODE):assert read(model.memory,p,4 if p==STATE else 1)==read(m,p,4 if p==STATE else 1)
    if entry==ENTRY:seen.update(p-ENTRY for p in model.visits)
   count+=1
 print(count,'input pairs per retail and raw body; visited',len(seen),'of 86 words',flush=True)
 return dict(cases=count,visited=len(seen),missing=[hex(i) for i in range(0,344,4) if i not in seen])
if __name__=='__main__':print(run())
