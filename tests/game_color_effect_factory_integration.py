"""Sole retail callsite census and bounded original ABI window for func_15152874."""
from dataclasses import dataclass
import json,struct
from tools.tests.game_payload_effect_factory_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

TARGET=0x15152874;PARENT=0x150CD7F8;PARENT_END=0x150CDB6C;WINDOW=0x150CDAEC;END=0x150CDAFC
@dataclass(frozen=True)
class Case:
 mode:int=0;extra:int=0;phase:int=0;seed:int=0
class Caller(FactoryOracle):
 def record_call(self,target):
  assert target==TARGET,hex(target);args=tuple(self.arguments(3));self.calls.append((target,args));self.events.append(('CALL',target,args))
 def hook(self,target):
  assert target==TARGET
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.r[2]=0x87654321
def reads_register(word,reg):
 op=word>>26;rs=word>>21&31;rt=word>>16&31;fn=word&63
 if op==0:
  if fn in(0,2,3):return rt==reg
  if fn in(8,9,17,19):return rs==reg
  return rs==reg or rt==reg
 if op in(2,3,15):return False
 if op in(4,5,6,7,20,21,22,23):return rs==reg or (op in(4,5,20,21)and rt==reg)
 if op in(40,41,42,43,46,47,56,57,61):return rs==reg or rt==reg
 return rs==reg
def qualify(root,output):
 rom=(root/'conker/conker.us.bin').read_bytes();base=0x2D4B0
 words=struct.unpack_from('>4I',rom,WINDOW-0x15000000+base);assert words==(0x92460001,0x9245000C,0x0D454A1D,0x27A400A0)
 raw=[struct.unpack_from('>I',rom,i)[0]for i in range(0,len(rom)-3,4)];jal=0x0D454A1D;jump=0x09544A1D
 jal_rom=[4*i for i,w in enumerate(raw)if w==jal];jump_rom=[4*i for i,w in enumerate(raw)if w==jump];pointer_rom=[4*i for i,w in enumerate(raw)if w==TARGET]
 assert jal_rom==[0xFAFA4]and not jump_rom and not pointer_rom
 cases=0
 for mode in range(256):
  c=Case(mode=mode,extra=(mode*197+37)&255,phase=(mode&1)*8,seed=mode&3);home=STACK+c.phase;owner=0x30000
  memory={home+i:(i*17+mode*13+165)&255 for i in range(-512,512)}
  for i in range(32):memory[owner+i]=(i*29+mode*11+90)&255
  memory[owner+1]=c.extra;memory[owner+0xC]=c.mode
  m=Caller(words,memory,c,entry=WINDOW,arguments=(0,0,0));m.r[18]=owner;m.before=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(END,)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('Caller window did not reach boundary')
  assert m.calls==[(TARGET,(home+0xA0,c.mode,c.extra))];assert m.r[29]==home;cases+=1
 after=struct.unpack_from('>%dI'%((PARENT_END-END)//4),rom,END-0x15000000+base)
 assert not any(reads_register(w,2)for w in after),'callee return consumed after call'
 descriptor_writes=[]
 parent=struct.unpack_from('>%dI'%((PARENT_END-PARENT)//4),rom,PARENT-0x15000000+base)
 for i,w in enumerate(parent):
  op=w>>26;rs=w>>21&31;off=((w&65535)^32768)-32768
  if rs==29 and op in(40,41,43,57,61) and 0xA0<=off<0xEC:descriptor_writes.append((PARENT+4*i,op,off))
 assert descriptor_writes and min(x[2]for x in descriptor_writes)==0xA0 and max(x[2]for x in descriptor_writes)>=0xE4
 report=dict(success=True,original_callers=1,aligned_ROM_JALs=[hex(x)for x in jal_rom],aligned_ROM_Js=[],aligned_ROM_pointer_literals=[],parent='func_150CD7F8',parent_words=len(parent),bounded_original_window_words=4,cases=cases,executions=cases,arguments=dict(input='SP+0xA0',mode='LBU owner+0x0C',extra='LBU owner+0x01'),all256_mode_bytes=True,all256_extra_bytes=True,JAL_delay_sets_input_pointer=True,descriptor_write_sites=len(descriptor_writes),descriptor_write_offset_span=[hex(min(x[2]for x in descriptor_writes)),hex(max(x[2]for x in descriptor_writes))],return_not_consumed_before_parent_return=True,full_parent_execution_claimed=False,parent_C_placeholder_uncredited=True)
 (output/'private-caller-v1.json').write_text(json.dumps(report,indent=2)+'\n');return report
