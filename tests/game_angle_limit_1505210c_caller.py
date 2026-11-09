"""Actual original caller window and exact remaining trampoline forwarding."""
import json,struct,sys
from dataclasses import replace
from pathlib import Path
from tools.experiments.game_angle_limit_1505210c_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_angle_limit_1505210c_oracle as guest
from tools.experiments import game_angle_limit_1505210c_match as qualify
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.match_progress import load_elf_functions
WINDOWS=((0x1504B7D0,0x1504B7F4,0x4C,0x48,0x48,180.,True),(0x150512E8,0x15051310,0x6C,0x68,0x40,50.,False),(0x15051D9C,0x15051DD0,0x94,0x90,0x90,50.,True))
class CallerOracle(guest.Oracle):
 def record_call(self,t):
  if t==guest.ENTRY:
   assert tuple(self.arguments(5))==guest.args(self.case);self.root_calls+=1;return
  super().record_call(t)
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();jal=(0x0C000000|((guest.ENTRY>>2)&0x3FFFFFF)).to_bytes(4,'big');calls=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal];ptrs=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==guest.ENTRY.to_bytes(4,'big')];assert calls==[0x78C98,0x7E7B8,0x7F274]and not ptrs,(calls,ptrs)
 before=(out/'frozen'/qualify.ELF).read_bytes();functions,_,_=load_elf_functions(str(out/'frozen'/qualify.ELF),'mips-linux-gnu-objdump');jal_word=int.from_bytes(jal,'big');assert not[(n,i)for n,ws in functions.items()for i,w in enumerate(ws)if w==jal_word]
 sizes={n:r[2]for _,n,r,_ in symbol_rows(before)};missing={n:dict(symbol_bytes=sizes[n],padded_disassembly_words=len(functions[n]))for n in('func_1504B0FC','func_150511E8','func_15051558')};assert all(v['symbol_bytes']<=12 for v in missing.values()),missing
 bodies=(guest.words(out/'qualified-owner.o'),guest.words(out/'qualified-padded/game_77AD0.c.o'),list(struct.unpack_from('>85I',rom,qualify.ROM)));count=0;seen=set()
 for window_index,(entry,stop,xoff,zoff,outoff,limit,stored)in enumerate(WINDOWS):
  start=entry-0x15000000+0x2D4B0;length=stop-entry;window=list(struct.unpack_from('>%dI'%(length//4),rom,start));at=elf_slot_offset(before,entry,length);assert before[at:at+length]==bytes(length),'A previously absent caller window changed'
  for base in guest.cases():
   if base.effects&4 or base.output!=guest.OUTPUT:continue
   c=replace(base,limit=guest.bits(limit),output=guest.STACK+base.phase+outoff);results=[]
   for ws in bodies:
    connected=dict(zip(range(guest.ENTRY,guest.ENTRY+340,4),ws));connected[stop]=0;m=CallerOracle(window,guest.fixture(c),c,entry=entry,connected=connected);m.root_calls=0;m.r[16]=guest.ACTOR;m.f[16]=0;home=guest.STACK+c.phase;guest.put(m.memory,home+xoff,c.x);guest.put(m.memory,home+zoff,c.z)
    if window_index==2:guest.put(m.memory,home+0x88,guest.bits(-1.))
    m.initial=dict(m.memory);m.code=WindowCode(m.code,m);m.code.ends=(stop,);saved=m.r[:];saved_f=m.f[:]
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller boundary not reached')
    want,expected,obs,value=guest.reference(m.initial,c)
    if stored:guest.put(want,home+xoff,value)
    assert m.root_calls==1 and len(m.calls)==4 and m.observations==obs
    for a,b in zip(m.calls,expected):assert a[0]==b[0]and all(guest.same(x,y)for x,y in zip(a[1],b[1]))
    assert guest.same(m.f[0],value)
    for p in(c.output,home+xoff):assert guest.same(guest.read(m.memory,p),guest.read(want,p));guest.put(m.memory,p,guest.read(want,p))
    assert guest.public(m.memory)==guest.public(want)and all(m.memory[p]==want[p]for p in m.initial if home<=p<home+512)
    assert m.r[16:24]==saved[16:24]and m.r[29]==saved[29]and m.f[20:]==saved_f[20:];seen.update(m.visits&set(range(entry,stop,4)));results.append((m.memory,m.calls,m.f))
   assert results[0]==results[1]==results[2];count+=1
 # Exercise the third caller's real branch-likely rejection and its delay load.
 entry,stop,xoff,zoff,outoff,limit,stored=WINDOWS[2];start=entry-0x15000000+0x2D4B0;window=list(struct.unpack_from('>13I',rom,start))
 for phase in(0,8):
  c=replace(guest.Case(),phase=phase);m=CallerOracle(window,guest.fixture(c),c,entry=entry,connected={0x15051EB4:0});m.root_calls=0;m.r[16]=guest.ACTOR;m.f[16]=0;guest.put(m.memory,guest.STACK+phase+0x88,guest.bits(1.));initial=dict(m.memory);m.code=WindowCode(m.code,m);m.code.ends=(0x15051EB4,)
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('Caller rejection not reached')
  assert m.memory==initial and not m.calls and m.root_calls==0;seen.update(m.visits&set(range(entry,stop,4)))
 assert len(seen)==32
 trampolines=0;images=(before,(out/'qualified-image.elf').read_bytes())
 for data,stop in zip(images,(0x15F001B4,0x15F00050)):
  entry=0x150768DC;at=elf_slot_offset(data,entry,8);ws=list(struct.unpack_from('>2I',data,at));assert ws==[0x08000000|((stop>>2)&0x3FFFFFF),0]
  c=guest.Case();m=guest.Oracle(ws,guest.fixture(c),c,entry=entry,connected={stop:0});m.code=WindowCode(m.code,m);m.code.ends=(stop,);saved=(m.r[:],m.f[:],dict(m.memory))
  try:m.run()
  except WindowBoundary:pass
  else:raise AssertionError('Trampoline destination not reached')
  assert(m.r,m.f,m.memory)==saved and not m.calls;trampolines+=1
 image=before;helper=elf_slot_offset(image,0x8009F710,4);assert struct.unpack_from('>I',image,helper)[0]==0x3FC90FDB
 for entry,size in((0x150AD780,12),(0x150AD78C,272),(0x150AD89C,8),(0x150484A0,320)):
  at=elf_slot_offset(image,entry,size);offset=entry-0x15000000+0x2D4B0;assert image[at:at+size]==rom[offset:offset+size],('Unchanged helper is not retail exact',hex(entry))
 report=dict(cases=count,bodies=3,original_windows=3,original_window_words=[9,10,13],original_window_visited=32,retail_ROM_JALs=[hex(x)for x in calls],aligned_literal_pointers=0,current_linked_JALs=0,current_stub_callers_words=missing,output_aliases_original_input=True,primary_return_stores_checked=True,third_caller_branch_rejections=2,trampoline_forwardings=trampolines,trig_quarter_shift_verified=True,helper_bodies_verified_retail=True,helper_algorithms_bounded=True,full_parent_or_hardware_claimed=False)
 (out/'caller.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
