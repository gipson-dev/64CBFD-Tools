"""Pristine entry census and execution of both original direct caller routes."""
from dataclasses import replace
import hashlib,json,struct
from tools.experiments import game_attached_spray_150c7020_match as p
from tools.tests import game_attached_spray_150c7020_guest as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_point_transform_match import put
NEXT=0x15194408;END=0x15029ba4
class Caller(g.Oracle):
 def record_call(self,t):
  if t!=NEXT:return super().record_call(t)
  a=tuple(map(g.u32,self.arguments(2)));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  if t!=NEXT:return super().hook(t)
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xa5000000+reg
def main():
 rom=(p.ROOT/'conker/conker.us.bin').read_bytes();jal=0x0c000000|((g.ENTRY>>2)&0x3ffffff);sites=[];pointers=[]
 for i,(word,)in enumerate(struct.iter_unpack('>I',rom[:len(rom)//4*4])):
  if word==jal:sites.append(i*4)
  if word==g.ENTRY:pointers.append(i*4)
 assert sites==[0x5587c,0x1c1a58]and not pointers,(sites,pointers)
 cases=0
 for ws in g.streams():
  code=dict(zip(range(g.ENTRY,g.ENTRY+416,4),ws))
  for tag,life,mode in [(i,(0,1,-1,-32768,32767)[i%5],i%8)for i in range(32)]:
   for route in range(2):
    c=g.Case(tag=tag,lifetime=500 if route==0 else life,mode=mode,ignored2=255,ignored3=1)
    memory=g.fixture(c);wanted,calls,obs=g.reference(memory,c)
    if route==0:
     words=list(struct.unpack_from('>17I',rom,0x1c1a38));entry=0x15194588;args=(c.owner,0x87654321,0xabcdef01)
     m=Caller(words,c,entry=entry,memory=memory,arguments=args,connected=code);m.r[29]+=24;m.before=m.r[:];m.run();assert m.r[29]==g.STACK+24
     target=(g.ENTRY,(c.owner,500,255,1));expected=[target,*calls,(NEXT,(c.owner,args[1]))]
    else:
     words=list(struct.unpack_from('>8I',rom,0x5586c));entry=0x150283bc;put(memory,g.STACK+0x773,255,1)
     m=Caller(words,c,entry=entry,memory=memory,connected={**code,END:0});m.r[3]=g.u32(life);m.code=WindowCode(m.code,m);m.code.ends=(END,)
     try:m.run();raise AssertionError('Missing caller boundary')
     except WindowBoundary:pass
     assert m.r[2]==1 and m.r[29]==g.STACK
     target=(g.ENTRY,(c.owner,g.u32(g.half(life)),255,1));expected=[target,*calls]
    assert(g.public(m.memory,c),m.calls,m.observations)==(g.public(wanted,c),expected,obs),(route,c,m.calls,expected)
    cases+=1
 # A poisoned argument register is an effective caller-interface negative control.
 bad=list(struct.unpack_from('>8I',rom,0x5586c));bad[3]=0x24040000
 c=g.Case();memory=g.fixture(c);put(memory,g.STACK+0x773,255,1);m=Caller(bad,c,entry=0x150283bc,memory=memory,connected={**code,END:0});m.r[3]=1;m.code=WindowCode(m.code,m);m.code.ends=(END,)
 try:m.run();raise AssertionError('Missing caller boundary')
 except WindowBoundary:pass
 assert m.calls[0][1][0]==0 and not m.observations
 helpers={}
 for name,va,offset,count in [('prepare',0x1516962c,0x196adc,15),('submit',0x15134dac,0x16225c,39)]:
  data=rom[offset:offset+4*count];before=(p.OUT/'baseline/conker/build/conker.us.elf').read_bytes();at=p.elf_slot_offset(before,va,len(data));live=before[at:at+len(data)];assert live==data,(name,'Helper body differs');symbol=next(row for _,label,row,_ in p.symbol_rows(before)if label=='func_%08X'%va);assert symbol[2]==count*4;helpers[name]=dict(original_words=count,original_sha256=hashlib.sha256(data).hexdigest(),baseline_slot_sha256=hashlib.sha256(live).hexdigest(),baseline_slot_is_retail=True,symbol_extent_checked=True,pristine_interface_inspected=True,internals_contracted=True)
 q=dict(pristine_ROM_sha256=hashlib.sha256(rom).hexdigest(),entire_pristine_aligned_ROM_scanned=True,entry_JALs=[hex(n)for n in sites],entry_pointers=pointers,unknown_additional_entry_callers=0,actual_caller_cases=cases,streams=4,caller_routes=2,ignored_return_verified=True,signed16_lifetime=True,effective_wrong_A0_control=True,helpers=helpers,helper_matching_credit=0,source_installed=p.installed(),matching_credit=0);(p.OUT/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
