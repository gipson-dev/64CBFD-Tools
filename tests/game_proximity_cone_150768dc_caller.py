"""Complete original script dispatcher with the protected 4B callback and bounded providers."""
import itertools,json,struct,sys
from pathlib import Path
from tools.experiments.game_proximity_cone_150768dc_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_proximity_cone_150768dc_oracle as guest
from tools.experiments import game_proximity_cone_150768dc_match as qualify
from tools.match_progress import load_elf_functions
PARENT=0x1507BC14;ROM=0xA90C4;WORDS=103;TABLE=0x80086730;SCRIPT=guest.SCRIPT;LOOKUP=0x1507BB28;DELTA=0x800CC264

def reference(initial,c,stop):
 m=dict(initial);calls=[];obs=[];a=guest.SYMS['D_800CC2D0']+c.own*812;p=guest.read(m,a+536);timer=guest.read(m,a+540,2);roots=0
 if timer and p:
  if timer!=25500:timer=(timer-((guest.read(m,DELTA,2)^32768)-32768))&65535;guest.put(m,a+540,timer,2)
  if timer>=50000 or timer==0:
   timer=0;guest.put(m,a+540,0,2);flags=guest.read(m,a+244)
   if flags&0x400:timer=20000;guest.put(m,a+540,timer,2);guest.put(m,a+244,(flags&~0x400)|4)
  else:return m,calls,obs,roots
 if not p:
  calls.append((LOOKUP,(0,m[a+562])));p=SCRIPT;guest.put(m,a+536,p);timer=0;guest.put(m,a+540,0,2)
 if timer:return m,calls,obs,roots
 while m[p]>=247:p+=1;guest.put(m,a+536,p)
 assert m[p]==0x4B
 for i,name in enumerate(('D_800D1890','D_800D1891','D_800D1892','D_800D1893')):m[guest.SYMS[name]]=m[p+1+i]
 m,cs,obs=guest.reference(m,c);calls+=cs;roots=1;p=guest.read(m,a+536)+5;guest.put(m,a+536,p);assert m[p]==0
 for i,name in enumerate(('D_800D1890','D_800D1891','D_800D1892','D_800D1893')):m[guest.SYMS[name]]=m[p+1+i]
 calls.append((stop,()));guest.put(m,a+540,1,2);p+=5;guest.put(m,a+536,p);return m,calls,obs,roots

class CallerOracle(guest.Oracle):
 def record_call(self,t):
  if t==guest.ENTRY:self.root_calls+=1;assert self.r[29]==guest.STACK+self.case.phase;return
  if t==LOOKUP:
   self.parent_lookup=not guest.ENTRY<=self.r[31]<guest.ENTRY+640
   if self.parent_lookup:self.calls.append((t,tuple(self.arguments(2))));return
  if t==self.stop:self.calls.append((t,()));return
  return super().record_call(t)
 def hook(self,t):
  if t not in(LOOKUP,self.stop)or t==LOOKUP and not self.parent_lookup:return super().hook(t)
  if t==self.stop:self.put(self.actor+540,1,2)
  for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=SCRIPT if t==LOOKUP else 0xDEADBEEF;self.hi,self.lo=0xA5000010,0xA5000011

def main():
 rom=(root/'conker/conker.us.bin').read_bytes();jal=0x0C000000|(guest.ENTRY>>2&0x3FFFFFF);jump=0x08000000|(guest.ENTRY>>2&0x3FFFFFF);census={n:[p for p in range(0,len(rom)-3,4)if int.from_bytes(rom[p:p+4],'big')==w]for n,w in(('JAL',jal),('J',jump),('pointer',guest.ENTRY))};assert census==dict(JAL=[],J=[],pointer=[0x22B31C])
 before=(out/'frozen'/qualify.ELF).read_bytes();after=(out/'qualified-image.elf').read_bytes();at=qualify.elf_slot_offset(before,TABLE,0x358);table=before[at:at+0x358];assert after[at:at+0x358]==table and struct.unpack_from('>I',table,0x4B*4)[0]==guest.ENTRY;stop=struct.unpack_from('>I',table)[0];assert stop not in(guest.ENTRY,LOOKUP,*guest.SYMS.values())
 functions,_,_=load_elf_functions(str(out/'frozen'/qualify.ELF),'mips-linux-gnu-objdump');assert not[(n,i)for n,w in functions.items()for i,v in enumerate(w)if v==jal]
 raw=rom[ROM:ROM+WORDS*4];offset=qualify.elf_slot_offset(before,PARENT,WORDS*4);assert before[offset:offset+WORDS*4]==after[offset:offset+WORDS*4]==raw;assert functions['func_1507BC14']==list(struct.unpack('>103I',raw));ws=list(struct.unpack('>103I',raw));configs=[]
 for effects,null,prefix in itertools.product((0,1,2,4,8,15),(0,1),(0,1)):configs.append((guest.replace(guest.Case(),effects=effects,phase=(len(configs)&1)*8),0,0,1,null,prefix))
 for c in(guest.replace(guest.Case(),candidates=()),guest.replace(guest.Case(),own=25,candidates=(0,24)),guest.replace(guest.Case(),script=0),guest.replace(guest.Case(),width=0)):
  configs.append((c,0,0,1,0,1))
 for timer,flags,delta in((3,0,1),(1,0,1),(1,0,2),(50001,0,1),(50001,0x400,1),(25500,0,1),(3,0,-1)):
  for null in(0,1):configs.append((guest.replace(guest.Case(),command=10,phase=(len(configs)&1)*8),timer,flags,delta,null,1))
 runs=roots=0;seen=set()
 for p in(out/'selected.o',out/'qualified-padded/game_A28B0.c.o',out/'retail-linked.o'):
  target=guest.words(p)
  for c,timer,flags,delta,null,prefix in configs:
   initial=guest.fixture(c);actor=guest.SYMS['D_800CC2D0']+c.own*812;initial.update({TABLE+i:v for i,v in enumerate(table)});initial.update({SCRIPT+i:0 for i in range(32)});packet=([255]if prefix else[])+[0x4B,c.command,c.cross,c.script,c.lookup,0,0,0,0,0];initial.update({SCRIPT+i:v for i,v in enumerate(packet)});initial.update({SCRIPT+40+i:0 for i in range(5)});guest.put(initial,actor+536,0 if null else SCRIPT);guest.put(initial,actor+540,timer,2);guest.put(initial,actor+244,0x81234000|flags);initial[actor+562]=0xAB;guest.put(initial,DELTA,delta,2)
   connected=dict(zip(range(guest.ENTRY,guest.ENTRY+len(target)*4,4),target));m=CallerOracle(ws,initial,c,entry=PARENT,connected=connected);m.stop=stop;m.actor=actor;m.root_calls=0;m.r[4]=actor;m.r[29]=guest.STACK+c.phase+48;saved=m.r[:];m.before=saved[:];saved_f=m.f[:];m.run();want,calls,obs,n=reference(initial,c,stop);assert m.root_calls==n and m.calls==calls and m.observations==obs,(c,timer,flags,delta,null,prefix,m.calls,calls);assert guest.public(m.memory)==guest.public(want),(c,timer,flags,delta,null,prefix);assert m.r[16:24]==saved[16:24]and m.r[28:]==saved[28:]and m.f[20:]==saved_f[20:];runs+=1;roots+=n;seen.update(m.visits&set(range(PARENT,PARENT+400,4)))
 missing=sorted((p-PARENT)//4 for p in set(range(PARENT,PARENT+400,4))-seen)
 report=dict(executions=runs,target_invocations=roots,ROM_census=census,protected_dispatch_table=hex(TABLE),dispatch_index=0x4B,dispatch_pointer=hex(TABLE+0x4B*4),complete_original_dispatcher=True,unchanged_byte_exact_C_dispatcher=True,dispatcher_body_words=100,dispatcher_slot_words=103,visited_body_words=len(seen),unvisited_body_words=missing,bounded_script_lookup=hex(LOOKUP),bounded_next_handler=hex(stop),script_decode_skip_advance_timer_flags_and_indirect_ABI=True,hardware_qualified=False);(out/'caller.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
