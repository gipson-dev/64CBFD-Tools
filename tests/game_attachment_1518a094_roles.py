"""Pin and classify changed words and exhaust the reordered callback gate."""
import json,struct
from tools.experiments import game_attachment_1518a094_match as p
from tools.experiments import game_attachment_1518a094_match as n
def main():
 raw,refs=p.payload(p.out/"independent-selected.o");normal,nrefs=n.normalize(raw,refs);a=struct.unpack(">96I",raw);b=struct.unpack(">96I",normal);diff={i for i,(x,y)in enumerate(zip(a,b))if x!=y}
 stack={10,11,33,35,37,58,63};dispatch_temps={29,30};gate={36,38,39,40,41,42,44};matrix_temps={46,47,48,49,50,51,55,56,59,60,62};output_temps={64,65,69,71,72,74};flags_and_return={75,77,78,79,80,82,83,85,87};groups=(stack,dispatch_temps,gate,matrix_temps,output_temps,flags_and_return);assert sum(map(len,groups))==len(set().union(*groups))==42 and set().union(*groups)==diff
 # Stack slots are inside both 0x50 frames and disjoint from saved registers,
 # outgoing arguments, and each other. Callbacks see only the single-byte pointer.
 rawslots=((0x10,0x1c),(0x28,0x30),(0x34,0x38),(0x43,0x44),(0x44,0x48));retailslots=((0x10,0x1c),(0x28,0x30),(0x3c,0x40),(0x44,0x48),(0x4b,0x4c))
 for slots in (rawslots,retailslots):
  assert all(0<=s<e<=0x50 for s,e in slots)
  for i,(s,e) in enumerate(slots):assert all(e<=t or u<=s for t,u in slots[i+1:])
 # Verify the exact register roles and store/reordering words before interpreting.
 assert [a[i] for i in (29,30,46,49,55,56)]==[0x00064080,0x0328c821,0x8c4401d4,0x10800021,0x000a5980,0x008b2021]
 assert [b[i] for i in (29,30,46,49,55,56)]==[0x00064880,0x0329c821,0x8c4801d4,0x11000021,0x000b6180,0x010c2021]
 assert [a[i] for i in (75,76,77,78,79,80,81,82)]==[0x8e190058,0x2401fffb,0x24020001,0x37290002,0xae090058,0x01215824,0x10000009,0xae0b0058]
 assert [b[i] for i in (75,76,77,78,79,80,81,82)]==[0x8e0a0058,0x2401fffb,0x354b0002,0xae0b0058,0x01616824,0xae0d0058,0x10000009,0x24020001]
 def gate_run(ws,result,enabled):
  # Starting immediately after jalr: test actual branch words and delay slots.
  regs=[0]*32;regs[2]=result;regs[3]=0x40000;regs[29]=0x100000;pc=36;reads=[];steps=0
  def execute(w):
   op=w>>26;rs=(w>>21)&31;rt=(w>>16)&31;imm=w&65535;imm=imm-65536 if imm&32768 else imm
   if w==0:return
   if op==0 and w&63==0x25:regs[(w>>11)&31]=(regs[rs]|regs[rt])&0xffffffff
   elif op==9:regs[rt]=(regs[rs]+imm)&0xffffffff
   elif op==0x23:
    if rs==29 and rt==3:regs[3]=0x40000
    elif rs==3 and rt==2:regs[2]=0x50000;reads.append("resource")
    else:raise AssertionError(hex(w))
   elif op==0x24 and rs==29:regs[rt]=enabled;reads.append("enabled")
   else:raise AssertionError(hex(w))
  while pc not in (46,91):
   steps+=1;assert steps<20,(pc,result,enabled);w=ws[pc];op=w>>26;rs=w>>21&31;rt=w>>16&31;imm=w&65535;imm=imm-65536 if imm&32768 else imm
   if op in(4,5,20,21):
    take=(regs[rs]==regs[rt]);take=not take if op in (5,21)else take;likely=op in(20,21)
    if take or not likely:execute(ws[pc+1])
    pc=pc+1+imm if take else pc+2
   else:execute(w);pc+=1
  return pc,regs[2],reads
 count=0
 for result in (0,1,0x80000000,0xffffffff):
  for enabled in range(256):
   x=gate_run(a,result,enabled);y=gate_run(b,result,enabled);assert x==y,(result,enabled,x,y);expected=(91,0,[])if not result else (46,0x50000,["enabled","resource"])if enabled else (91,1,["enabled"]);assert x==expected,(result,enabled,x,expected);count+=1
 report=dict(guard_words=len(diff),groups={"stack_slots":len(stack),"dispatcher_temporaries":len(dispatch_temps),"callback_gate":len(gate),"matrix_temporaries":len(matrix_temps),"output_temporaries":len(output_temps),"flag_and_return_schedule":len(flags_and_return)},gate_cases=count,stack_slots_disjoint=True,register_roles_checked=True,callback_alias_and_hardware_not_qualified=True,source_installed=False)
 (p.out/"roles.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report),flush=True);return report
