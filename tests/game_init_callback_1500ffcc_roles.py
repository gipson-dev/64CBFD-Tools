"""Private proof of the reordered stack and call-argument preparation."""
import json,struct
from tools.experiments import game_init_callback_1500ffcc_match as p
from tools.experiments import game_init_callback_1500ffcc_match as n
def main():
 raw,refs=p.payload(p.out/'independent-selected.o');normalized,_=n.normalize(raw,refs)
 a=struct.unpack('>79I',raw);b=struct.unpack('>79I',normalized)
 assert [i for i,(x,y) in enumerate(zip(a,b)) if x!=y]==list(range(51,65))+[66]
 assert a[50]==b[50]==0x44800000 and a[65]==b[65] and a[65]>>26==3
 def execute(words,sp,seed):
  regs=[(seed*0x10203+i*0x11111111)&0xffffffff for i in range(32)];regs[0]=0;regs[29]=sp;memory={};f0=0
  for i in range(51,67):
   word=words[i];op=word>>26;rs=(word>>21)&31;rt=(word>>16)&31;imm=((word&65535)^32768)-32768
   if op==9:regs[rt]=(regs[rs]+imm)&0xffffffff
   elif op in (0x2b,0x39):
    assert rs==29;memory[(regs[rs]+imm)&0xffffffff]=(f0 if op==0x39 else regs[rt])
   elif op==3:
    assert i==65;regs[31]=p.ENTRY+4*i+8
   else:raise AssertionError((i,hex(word)))
   regs[0]=0
  return regs,memory
 for sp in (0,0x40000,0x7ffffff0,0xfffffff0):
  for seed in range(5):
   ar,am=execute(a,sp,seed);br,bm=execute(b,sp,seed)
   assert ar==br and am==bm
   assert set(am)=={(sp+x)&0xffffffff for x in (0x10,0x14,0x18,0x1c,0x20,0x38,0x3c)}
 result=dict(guard_words=15,identical_registers_and_stack_at_call=True,disjoint_stack_slots=True,delay_slots_complete_before_call=True,scenarios=20,partial_fault_state_not_qualified=True,source_installed=False)
 (p.out/'roles-screen.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
