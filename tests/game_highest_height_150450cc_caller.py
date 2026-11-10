"""Complete retail-exact height combiner and its real mixed pointer/float call ABI."""
import itertools,json,struct,sys
from pathlib import Path
from tools.experiments.game_highest_height_150450cc_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_highest_height_150450cc_oracle as guest
from tools.experiments import game_highest_height_150450cc_match as qualify
from tools.match_progress import load_elf_functions
CALLER,FIRST=0x1504697C,0x15046460
BASE=guest.OUTPUT-40
def payload(m,at,height):
 b=bytearray(guest.data(m,at,36));struct.pack_into('>I',b,0,height)
 for i in range(9):struct.pack_into('>H',b,4+i*2,(-(i+1)*1234)&65535)
 struct.pack_into('>I',b,24,0x1234ABCD);b[28]|=1;b[29]=90;return bytes(b)
def visible(m):return{p:v for p,v in m.items()if not guest.STACK-512<=p<guest.STACK+512 and not guest.OUTPUT-256<=p<guest.OUTPUT+256}
class CallerOracle(guest.Oracle):
 def record_call(self,t):
  if t==guest.ENTRY:
   assert tuple(self.arguments(3))==(guest.pos(self.case),self.case.threshold,guest.OUTPUT);self.root_calls+=1;self.root_initial=dict(self.memory);self.root_call_index=len(self.calls);self.target_home=self.r[29];assert self.target_home==BASE;assert self.memory[BASE+39]==self.first_return&255;return
  if t==FIRST:
   a=tuple(self.arguments(4));assert a==(guest.pos(self.case),0x2345,self.case.threshold,guest.OUTPUT+36),a;self.calls.append((t,a));return
  return super().record_call(t)
 def hook(self,t):
  if t!=FIRST:return super().hook(t)
  self.memory.update({guest.OUTPUT+36+i:v for i,v in enumerate(self.first_payload)})
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=self.first_return
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();jal=0x0C000000|((guest.ENTRY>>2)&0x3FFFFFF);j=0x08000000|((guest.ENTRY>>2)&0x3FFFFFF)
 calls=[i for i in range(0,len(rom)-3,4)if int.from_bytes(rom[i:i+4],'big')==jal];ptrs=[i for i in range(0,len(rom)-3,4)if int.from_bytes(rom[i:i+4],'big')==guest.ENTRY];jumps=[i for i in range(0,len(rom)-3,4)if int.from_bytes(rom[i:i+4],'big')==j];assert calls==[0x73EF0]and not ptrs and not jumps
 before=(out/'frozen'/qualify.ELF).read_bytes();after=(out/'qualified-image.elf').read_bytes();functions,_,_=load_elf_functions(str(out/'frozen'/qualify.ELF),'mips-linux-gnu-objdump');linked=[(n,i)for n,ws in functions.items()for i,w in enumerate(ws)if w==jal];assert linked==[('func_1504697C',49)]
 raw=rom[0x73E2C:0x73E2C+644];at=qualify.elf_slot_offset(before,CALLER,644);assert before[at:at+644]==after[at:at+644]==raw;ws=list(struct.unpack('>161I',raw));bodies=(guest.words(out/'selected.o'),guest.words(out/'qualified-padded/generated_71820.c.o'),list(struct.unpack_from('>144I',rom,qualify.ROM)));seen=set();count=roots=0
 for threshold,first_return,first_height,mutation,n,real in itertools.product((0,0x40A00000,0x41A00000),(0,1,255,256),(0,0x40000000,0x40C00000),(0,1,15),(0,4),(False,True)):
  c=guest.replace(guest.Case(),threshold=threshold,mutation=mutation,count=n,real_context=real)
  for body in bodies:
   initial=guest.fixture(c);initial.update({guest.OUTPUT+i:(i*13+5)&255 for i in range(-256,256)if guest.OUTPUT+i not in initial});original=guest.data(initial,guest.ALTERNATE,36);first_payload=payload(initial,guest.ALTERNATE,first_height)
   connected=dict(zip(range(guest.ENTRY,guest.ENTRY+576,4),body))
   if real:connected.update(guest.original_context())
   m=CallerOracle(ws,initial,c,entry=CALLER,connected=connected);m.root_calls=0;m.first_return=first_return;m.first_payload=first_payload;m.r[29]=BASE+112;m.r[4]=guest.pos(c);m.r[5]=0xABC12345;m.r[6]=threshold;m.r[7]=guest.ALTERNATE;m.before=m.r[:];saved=m.r[:];saved_f=m.f[:];m.run()
   early=guest.floating(c.position[1])<guest.floating(threshold)
   if early:
    assert not m.root_calls and not m.calls;want=dict(initial);p=bytearray(original);p[28]&=253;want.update({guest.ALTERNATE+i:v for i,v in enumerate(p)});expected_return=0
   else:
    assert m.root_calls==1;want,root_calls,obs,second=guest.reference(m.root_initial,c,home=BASE);assert m.calls[m.root_call_index:]==root_calls and m.observations==obs
    assert m.calls[:m.root_call_index]==[(FIRST,(guest.pos(c),0x2345,threshold,guest.OUTPUT+36))]
    second_payload=guest.data(want,guest.OUTPUT,36);first=bool(first_return&255)
    if first and second:chosen=first_payload if guest.floating(int.from_bytes(second_payload[:4],'big'))<guest.floating(first_height)else second_payload;expected_return=1
    elif first:chosen=first_payload;expected_return=1
    elif second:chosen=second_payload;expected_return=1
    else:
     chosen=first_payload if guest.floating(int.from_bytes(second_payload[:4],'big'))<guest.floating(first_height)else second_payload;p=bytearray(chosen);p[28]&=253;chosen=bytes(p);expected_return=0
    want.update({guest.ALTERNATE+i:v for i,v in enumerate(chosen)});assert guest.data(m.memory,guest.OUTPUT,36)==second_payload;assert guest.data(m.memory,guest.OUTPUT+36,36)==first_payload;roots+=1
   assert(visible(m.memory),m.r[2]&0xFFFFFFFF)==(visible(want),expected_return),(c,first_return,first_height)
   assert m.r[16:24]==saved[16:24]and m.r[28:]==saved[28:]and m.f[20:]==saved_f[20:]
   seen.update(m.visits&set(range(CALLER,CALLER+644,4)));count+=1
 missing=sorted((p-CALLER)//4 for p in set(range(CALLER,CALLER+644,4))-seen);targets=set()
 for i,w in enumerate(ws):
  if w>>26 in(4,5,6,7,20,21,22,23)or w>>26==17 and w>>21&31==8:targets.add(i+1+((w&65535)^32768)-32768)
 assert missing==[76,140]and not targets.intersection(missing)and all(ws[i-2]>>16==0x1000 for i in missing)
 report=dict(executions=count,target_invocations=roots,bodies=3,retail_ROM_JALs=[hex(v)for v in calls],current_linked_JALs=len(linked),aligned_literal_pointers=0,direct_jumps=0,complete_original_C_caller=True,original_caller_words=161,visited_caller_words=len(seen),unreachable_caller_words=missing,mixed_pointer_float_pointer_ABI=True,first_query_result_narrowed_to_byte=True,comparison_and_packet_copies=True,first_spatial_query_is_bounded_provider=True,hardware_qualified=False)
 (out/'caller.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
