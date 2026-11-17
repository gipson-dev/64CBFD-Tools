"""Complete retail draw caller and selector; literal registered descriptors."""
from pathlib import Path
from collections import Counter
from dataclasses import replace,asdict
import hashlib,importlib.util,itertools,json,struct,sys
from tools.tests import game_strip_draw_151ad92c_private_oracle as o
from tools.experiments import game_strip_draw_151ad92c_private_recovery as source
p=source.OUT
CALLER,SELECTOR=0x151674F8,0x15168F84
TABLE,HEADS,DEPTH,NEXT=[o.SYMS[n]for n in('D_8008B4A8','D_800DCE50','D_800DD190','D_800DD198')]
BASES,BUDGET,MARK=[o.SYMS[n]for n in('D_800BE9C8','D_800BEBA4','D_8003C8E0')]
rom=(source.FROZEN/'conker/conker.us.bin').read_bytes()
def retail(entry,size):
 offset=entry-0x15000000+0x2D4B0
 return list(struct.unpack_from('>%dI'%(size//4),rom,offset))
caller=retail(CALLER,1392);selector=retail(SELECTOR,188)
table=o.data[TABLE-o.data_at:TABLE-o.data_at+101*52]
assert len(caller)==348 and len(selector)==47 and len(table)==5252
for category in(47,78):
 assert struct.unpack_from('>I',table,category*52+8)[0]==o.ENTRY
 assert table[category*52+48]==1
 assert all(struct.unpack_from('>I',table,category*52+offset)[0]==0 for offset in(16,20,32,36))

def fixture(c,category,row,depth,budget,layer):
 m=o.fixture(c)
 m.update({TABLE+i:value for i,value in enumerate(table)})
 m.update({HEADS+i:0 for i in range(0x440)})
 for address,size in((BASES,8),(BUDGET,4),(MARK,4),(o.SYMS['D_800D2DAB'],1)):
  m.update({address+i:0xA5 for i in range(size)})
 o.o.put(m,HEADS+row*0x1A0+category*4,o.RECORD)
 o.o.put(m,o.RECORD+8,0);m[o.RECORD]=category;m[o.RECORD+1]=row
 o.o.put(m,DEPTH,0xA55A5AA5);m[DEPTH]=depth
 o.o.put(m,BASES,o.OUTPUT);o.o.put(m,BASES+4,o.OUTPUT)
 o.o.put(m,BUDGET,budget)
 if layer!=1:m[TABLE+category*52+48]=layer
 return m

class Caller(o.Oracle):
 def __init__(self,callback,m,c,category,row,original=caller):
  self.fp=[];self.loads=Counter();self.boundaries=[];self.invocations=[];self.selector_calls=[]
  connected={o.ENTRY+i*4:w for i,w in enumerate(callback)}
  connected.update({SELECTOR+i*4:w for i,w in enumerate(selector)})
  group=0 if category==47 else 1
  o.FactoryOracle.__init__(self,original,m,c,entry=CALLER,s={},arguments=(o.OUTPUT,group,c.viewport,row),connected=connected)
  self.service=o.Service(self.memory,c)
  self.saved_g=tuple(self.r[16:24])+(self.r[28],self.r[29],self.r[30]);self.saved_fp=tuple(self.f[20:])
 def record_call(self,target):
  if target==SELECTOR:
   self.selector_calls.append(tuple(self.arguments(3)))
  elif target==o.ENTRY:
   args=tuple(self.arguments(3));view=o.u32(((self.case.viewport&65535)^32768)-32768)
   assert args==(o.OUTPUT+16,o.RECORD,view),('callback ABI',args)
   self.invocations.append(args);self.target_home=self.r[29]
  else:super().record_call(target)
 def hook(self,target):
  assert target==o.SUBMIT,('unexpected provider',hex(target))
  # The caller narrows its third argument to signed16 before the callback.
  original=self.case
  self.case=replace(original,viewport=o.u32(((original.viewport&65535)^32768)-32768))
  try:super().hook(target)
  finally:self.case=original

def one(words,c,category,row,depth,budget=4096,layer=1,original=caller):
 initial=fixture(c,category,row,depth,budget,layer)
 machine=Caller(words,initial,c,category,row,original).run()
 assert len(machine.selector_calls)==1 and len(machine.invocations)==1
 assert machine.memory[DEPTH]==depth
 assert o.o.read(machine.memory,NEXT+4*(depth+1))==0
 expected,calls,answer=o.reference(initial,c,o.OUTPUT+16)
 assert machine.service.calls==calls
 overflow=layer==1 and (answer-o.OUTPUT)//8>budget
 final=o.OUTPUT+16 if overflow else answer
 # Compare every vertex/buffer byte and every emitted callback command against
 # the independent model. The caller appends its final geometry-mode command.
 for base,size in((o.RECORD,128),(o.POINTS,480),(o.VERTICES,2560),(o.OTHER_VERTICES,2560),(o.TABLE,672)):
  assert bytes(machine.memory[base+i]for i in range(size))==bytes(expected[base+i]for i in range(size)),('model region',hex(base))
 for address in(o.OUTPUT,o.OTHER_OUTPUT):
  for i in range(4096):
   at=address+i
   if o.OUTPUT<=at<o.OUTPUT+16 or final<=at<final+8:continue
   assert machine.memory[at]==expected[at],('command bytes',hex(at),machine.memory[at],expected[at])
 assert o.o.read(machine.memory,o.OUTPUT)==0xDA380003
 assert o.o.read(machine.memory,o.OUTPUT+4)==o.SYMS['D_80089470']
 assert o.o.read(machine.memory,o.OUTPUT+8)==0xD9FDFFFF and o.o.read(machine.memory,o.OUTPUT+12)==0
 assert o.o.read(machine.memory,final)==0xD9FFFFFF and o.o.read(machine.memory,final+4)==1
 # Layer1 budget failure restores the list pointer captured before this class.
 expected_return=o.OUTPUT+8 if overflow else answer+8
 assert machine.r[2]==expected_return,('caller return',hex(machine.r[2]),hex(expected_return))
 return machine

def main():
 source.check_inputs()
 label='selected'
 raw,refs=o.o.payload(p/'owner.o','func_151AD92C')
 programs={'retail':retail(o.ENTRY,1856),'raw':o.o.bound_blob(raw,refs,o.SYMS)}
 seen={k:set()for k in programs};cases=0
 for seed,category,row,depth,budget in itertools.product(range(4),(47,78),(0,1),(0,3),(0,4096)):
  c=o.Case(seed=seed,count=(0,1,3,20)[seed],bank=seed&1,texture=54+(seed>>1&1),pattern=seed,phase=(seed&1)*8,viewport=(0,0xABCD8000,0x12347FFF,0xFFFFFFFF)[seed],mutation=seed*5)
  left=None
  for name,words in programs.items():
   machine=one(words,c,category,row,depth,budget)
   seen[name].update(machine.visits)
   if left is None:left=machine
   else:
    assert o.o.public(machine.memory)==o.o.public(left.memory)
    assert machine.r[2]==left.r[2]and machine.service.calls==left.service.calls
  cases+=1
 # Same full caller, deliberately altered descriptor flag: extra ABI branch
 # coverage, separate from the literal layer1 production descriptors.
 extra=0
 for layer in(0,2):
  for category in(47,78):
   c=o.Case(count=3,pattern=2,viewport=0xFFFF)
   left=one(programs['retail'],c,category,0,0,layer=layer)
   right=one(programs['raw'],c,category,0,0,layer=layer)
   assert o.o.public(left.memory)==o.o.public(right.memory)and left.r[2]==right.r[2]
   seen['retail'].update(left.visits);seen['raw'].update(right.visits);extra+=1
 controls=[]
 # Wrong record pointer in a genuine JALR delay boundary must be detected.
 bad=caller[:];site=(0x151677F4-CALLER)//4;assert bad[site]==0x02002825;bad[site]=0x26050004
 try:one(programs['retail'],o.Case(count=2),47,0,0,original=bad)
 except AssertionError as error:assert error.args[0][0]=='callback ABI';controls.append('wrong callback record pointer')
 else:raise AssertionError('bad caller ABI accepted')
 report=dict(label=label,literal_descriptor_cases_per_stream=cases,additional_layer_cases_per_stream=extra,streams=list(programs),caller_words=348,selector_words=47,caller_coverage={k:len({a for a in v if CALLER<=a<CALLER+1392})for k,v in seen.items()},selector_coverage={k:len({a for a in v if SELECTOR<=a<SELECTOR+188})for k,v in seen.items()},registered_classes=[47,78],literal_layer=1,budget_rollback=True,three_word_abi_and_signed_viewport=True,public_ram_calls_and_return=True,effective_controls=controls,source_installed=False,c_match_credit=0)
 with(p/'caller-report.json').open('x')as stream:json.dump(report,stream,indent=2);stream.write('\n')
 source.check_inputs()
 print(json.dumps(report),flush=True)
if __name__=='__main__':main()
