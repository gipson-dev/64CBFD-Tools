"""Pristine entry census and bounded execution of both descriptor-building windows."""
from dataclasses import replace
import hashlib,json,struct
from tools.experiments import game_ring_effect_150c88d0_match as p
from tools.tests import game_ring_effect_150c88d0_guest as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

def stop(m,pc):
 m.code[pc]=0;m.code=WindowCode(m.code,m);m.code.ends=(pc,)
 try:m.run();raise AssertionError('Missing caller boundary')
 except WindowBoundary:return m

def main():
 rom=(p.ROOT/'conker/conker.us.bin').read_bytes();jal=0x0c000000|((g.ENTRY>>2)&0x3ffffff);sites=[];pointers=[]
 for i,(word,)in enumerate(struct.iter_unpack('>I',rom[:len(rom)//4*4])):
  if word==jal:sites.append(i*4)
  if word==g.ENTRY:pointers.append(i*4)
 assert sites==[0xf79a0,0xf9a00]and not pointers,(sites,pointers)
 before=(p.OUT/'baseline/conker/build/conker.us.elf').read_bytes();routes=[(0x150ca450,0xf7900,0x150ca4f0,0xe4),(0x150cc4ac,0xf995c,0x150cc550,0x70)];cases=0;control=False
 for ws in g.streams():
  connected=dict(zip(range(g.ENTRY,g.ENTRY+408,4),ws))
  for entry,offset,callpc,home in routes:
   words=list(struct.unpack_from('>'+str((callpc+8-entry)//4)+'I',rom,offset));assert words[0]==0x27a40000|home and words[-2]==jal
   for mode in(0,1,2,4,8,15):
    for phase,outcome in[(0,1),(8,1),(0,0)]:
     c=g.Case(mode=mode,phase=phase,outcome=outcome,descriptor=g.STACK+phase+home,priority=255,extra=0,group=1);memory=g.fixture(c)
     for at in(0x800a05a4,0x800a05a8,0x800a06c8):
      pos=p.elf_slot_offset(before,at,4);g.put(memory,at,int.from_bytes(before[pos:pos+4],'big'))
     def model(w):
      m=g.Oracle(w,c,entry=entry,memory=dict(memory),arguments=());m.f[0]=g.bits(24.);return m
     prefix=stop(model(words),callpc);prefix.execute(words[-1]);effective=replace(c,fcsr=prefix.fcsr);wanted,calls,obs,fcsr,value=g.reference(prefix.memory,effective)
     m=model(words);m.code.update(connected);stop(m,callpc+8)
     assert m.calls==[(g.ENTRY,(c.descriptor,0,255,1)),*calls],('calls',m.calls,calls)
     assert m.observations==obs,('observations',[(i,a[2],b[2])for i,(a,b)in enumerate(zip(m.observations,obs))if a!=b])
     assert(m.fcsr,m.r[2])==(fcsr,value),('return',m.fcsr,fcsr,m.r[2],value)
     assert g.public(m.memory,c)==g.public(wanted,c),('memory',[(hex(a),v,wanted.get(a))for a,v in g.public(m.memory,c).items()if wanted.get(a)!=v][:10])
     assert m.r[29]==g.STACK+phase;cases+=1
     if not control:
      bad=list(words);bad[-7]=0x240600fe;poison=model(bad);poison.code.update(connected);stop(poison,callpc+8);assert poison.calls[0][1][2]==254 and poison.calls!=m.calls;control=True
 # Pin the immediate continuations; complete parent behavior is outside this gate.
 first=list(struct.unpack_from('>5I',rom,0xf79a8));assert first==[0x93ab0127,0x8fac0168,0x51600107,0x8fbf0044,0x958d007a]
 assert struct.unpack_from('>I',rom,0xf9a08)[0]==0x0d42b688
 q=dict(pristine_ROM_sha256=hashlib.sha256(rom).hexdigest(),entire_pristine_aligned_ROM_scanned=True,entry_JALs=[hex(n)for n in sites],entry_pointers=pointers,unknown_additional_entry_callers=0,actual_caller_cases=cases,streams=4,caller_routes=2,complete_descriptor_argument_windows=True,return_observed_at_boundary=True,effective_wrong_priority_control=control,helpers_internals_contracted=True,helper_matching_credit=0,source_installed=p.installed(),matching_credit=0);(p.OUT/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
