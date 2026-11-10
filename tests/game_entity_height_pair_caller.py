"""All three complete retail callers; preparation and first spatial query are bounded providers."""
import itertools,json,struct,sys
from pathlib import Path
from tools.experiments.game_entity_height_pair_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_entity_height_pair_oracle as guest
from tools.experiments import game_entity_height_pair_match as qualify
from tools.match_progress import load_elf_functions
PREP=0x15045714;DEST=0x98100;BASE=guest.OUTPUT-40
CALLERS=((0x150461D0,0x73680,164,54,0,0x15045880),(0x15046460,0x73910,166,56,1,0x15045AE4),(0x15045780,0x72C30,32,26,1,None))
def packet(m,height):
 b=bytearray(guest.data(m,DEST,36));struct.pack_into('>I',b,0,height)
 for i in range(9):struct.pack_into('>H',b,4+i*2,(-(i+1)*1234)&65535)
 struct.pack_into('>I',b,24,0x1234ABCD);b[28]|=1;b[29]=90;return bytes(b)
def visible(m):return{p:v for p,v in m.items()if not guest.STACK-768<=p<guest.STACK+768 and not guest.OUTPUT-256<=p<guest.OUTPUT+256}
class CallerOracle(guest.Oracle):
 def record_call(self,t):
  if t==guest.ENTRIES[self.case.kind]:
   assert tuple(self.arguments(4))==(guest.POS,self.case.threshold,guest.INPUT,guest.OUTPUT);self.root_calls+=1;self.root_initial=dict(self.memory);self.root_call_index=len(self.calls);self.target_home=self.r[29];assert self.target_home==BASE;return
  if t==PREP:
   a=tuple(self.arguments(4));assert a==(guest.POS,0x2345,BASE+(28 if self.first is None else 116),guest.INPUT),a;self.calls.append((t,a));return
  if t==self.first:
   a=tuple(self.arguments(4));assert a==(guest.POS,self.case.threshold,BASE+116,guest.OUTPUT+36),a;self.calls.append((t,a));return
  return super().record_call(t)
 def hook(self,t):
  if t not in(PREP,self.first):return super().hook(t)
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
  if t==PREP:self.put(guest.INPUT,self.case.input_word,4);self.put(BASE+(28 if self.first is None else 116),0x2345ABCD,4);self.r[2]=0
  else:self.memory.update({guest.OUTPUT+36+i:v for i,v in enumerate(self.first_payload)});self.r[2]=self.first_return
def main():
 global BASE
 rom=(root/'conker/conker.us.bin').read_bytes();before=(out/'frozen'/qualify.ELF).read_bytes();after=(out/'qualified-image.elf').read_bytes();functions,_,_=load_elf_functions(str(out/'frozen'/qualify.ELF),'mips-linux-gnu-objdump');census={};runs=roots=0;coverage={};oldinput=guest.INPUT
 try:
  for kind,f in enumerate(guest.FUNCTIONS):
   entry=guest.ENTRIES[kind];jal=0x0C000000|((entry>>2)&0x3FFFFFF);j=0x08000000|((entry>>2)&0x3FFFFFF);calls=[i for i in range(0,len(rom)-3,4)if int.from_bytes(rom[i:i+4],'big')==jal];expected=[r+wi*4 for _,r,_,wi,k,_ in CALLERS if k==kind];assert sorted(calls)==sorted(expected);assert not any(int.from_bytes(rom[i:i+4],'big')in(entry,j)for i in range(0,len(rom)-3,4));linked=[(n,i)for n,ws in functions.items()for i,w in enumerate(ws)if w==jal];assert sorted(linked)==sorted(('func_%08X'%a,wi)for a,_,_,wi,k,_ in CALLERS if k==kind);census[f]=dict(ROM_JALs=calls,linked_JALs=linked,aligned_pointers=0,direct_jumps=0)
  for addr,romat,n,wi,kind,first in CALLERS:
   BASE=guest.OUTPUT-(40 if first else 128)
   raw=rom[romat:romat+n*4];at=qualify.elf_slot_offset(before,addr,n*4);assert before[at:at+n*4]==after[at:at+n*4]==raw;ws=list(struct.unpack('>'+str(n)+'I',raw));bodies=[guest.words(out/'selected.o',kind),guest.words(out/'qualified-padded/generated_71820.c.o',kind),guest.words(out/(guest.FUNCTIONS[kind]+'-retail.o'),kind)];seen=set();guest.INPUT=BASE+(112 if first else 24)
   for threshold,first_return,height,mutation,count in itertools.product((0,0x40000000,0x40A00000),(0,1,255,256),(0,0x40000000,0x40C00000),(0,3,12),(0,4)):
    if first is None and(first_return or height):continue
    c=guest.replace(guest.Case(),kind=kind,threshold=threshold,mutation=mutation,count=count)
    for target in bodies:
     initial=guest.fixture(c);initial.update({guest.OUTPUT+i:(i*13+5)&255 for i in range(-256,256)if guest.OUTPUT+i not in initial});initial.update({DEST+i:initial.get(DEST+i,(i*29+91)&255)for i in range(-16,52)});original=guest.data(initial,DEST if first else guest.OUTPUT,36);first_payload=packet(initial,height);connected=dict(zip(range(guest.ENTRIES[kind],guest.ENTRIES[kind]+580,4),target));m=CallerOracle(ws,initial,c,entry=addr,connected=connected);m.root_calls=0;m.first=first;m.first_return=first_return;m.first_payload=first_payload;m.r[29]=BASE+(120 if first else 32);m.r[4]=guest.POS;m.r[5]=0xABC12345;m.r[6]=threshold;m.r[7]=DEST if first else guest.OUTPUT;saved=m.r[:];saved_f=m.f[:];m.before=saved[:];m.run();early=guest.floating(threshold)<guest.floating(c.position[1])if kind==0 else guest.floating(c.position[1])<guest.floating(threshold)
     if early:
      assert not m.root_calls and not m.calls;want=dict(initial);p=bytearray(original);p[28]&=253
      if first and kind:p[29]=0;p[32:36]=bytes(4)
      want.update({(DEST if first else guest.OUTPUT)+i:v for i,v in enumerate(p)});result=0
     else:
      assert m.root_calls==1;want,cs,obs,second=guest.reference(m.root_initial,c,home=BASE);assert m.calls[m.root_call_index:]==cs and m.observations==obs;second_payload=guest.data(want,guest.OUTPUT,36);roots+=1
      if first:
       a=bool(first_return&255)
       if a and second or not a and not second:
        x=guest.floating(height);y=guest.floating(int.from_bytes(second_payload[:4],'big'));chosen=first_payload if(x<y if not kind else y<x)else second_payload;result=int(a and second)
       else:chosen=first_payload if a else second_payload;result=1
       if not result:p=bytearray(chosen);p[28]&=253;chosen=bytes(p)
       want.update({DEST+i:v for i,v in enumerate(chosen)});assert guest.data(m.memory,guest.OUTPUT+36,36)==first_payload
      else:result=second
      assert guest.data(m.memory,guest.OUTPUT,36)==second_payload
     assert(visible(m.memory),guest.data(m.memory,DEST if first else guest.OUTPUT,36),m.r[2]&0xFFFFFFFF)==(visible(want),guest.data(want,DEST if first else guest.OUTPUT,36),result),(hex(addr),c,first_return,height,[(hex(p),v,visible(want).get(p))for p,v in visible(m.memory).items()if visible(want).get(p)!=v][:12],guest.data(m.memory,DEST if first else guest.OUTPUT,36).hex(),guest.data(want,DEST if first else guest.OUTPUT,36).hex(),m.r[2],result)
     assert m.r[16:24]==saved[16:24]and m.r[28:]==saved[28:]and m.f[20:]==saved_f[20:];seen.update(m.visits&set(range(addr,addr+n*4,4)));runs+=1
   missing=sorted((p-addr)//4 for p in set(range(addr,addr+n*4,4))-seen);assert missing==([]if first else[19]);coverage[hex(addr)]=dict(words=n,visited=n-len(missing),unvisited=missing)
 finally:guest.INPUT=oldinput
 report=dict(executions=runs,target_invocations=roots,census=census,complete_callers=coverage,retained_assembly_wrapper=True,mixed_pointer_float_pointer_pointer_ABI=True,first_return_narrowed_to_byte=True,packet_copy_and_selection=True,preparation_and_other_spatial_query_are_bounded_providers=True,hardware_qualified=False);(out/'caller.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
