"""Pristine callback pointer, type49 descriptor and original update-dispatch window."""
import hashlib,itertools,json,struct
from tools.experiments import game_ring_updater_150c8a68_match as p
from tools.tests import game_ring_updater_150c8a68_guest as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
TABLE=0x8008b4a8;SLOT=TABLE+49*52;NEST=0x800dd190;QUEUE=0x800dd198;WINDOW=0x15167164;END=0x15167190
class WrongRecord(Exception):pass
class Caller(g.Oracle):
 def record_call(self,t):
  if t==g.ENTRY and tuple(map(g.u32,self.arguments(1)))!=(g.OWNER,):raise WrongRecord()
  return super().record_call(t)
def run(m):
 m.code[END]=0;m.code=WindowCode(m.code,m);m.code.ends=(END,)
 try:m.run();raise AssertionError('Missing dispatch boundary')
 except WindowBoundary:return m
def main():
 rom=(p.ROOT/'conker/conker.us.bin').read_bytes();jal=0x0c000000|((g.ENTRY>>2)&0x3ffffff);sites=[];pointers=[]
 for i,(word,)in enumerate(struct.iter_unpack('>I',rom[:len(rom)//4*4])):
  if word==jal:sites.append(i*4)
  if word==g.ENTRY:pointers.append(i*4)
 assert not sites and pointers==[0x23095c],(sites,pointers)
 before=(p.OUT/'baseline/conker/build/conker.us.elf').read_bytes();at=p.elf_slot_offset(before,SLOT,4);assert SLOT==0x8008be9c and before[at:at+4]==g.ENTRY.to_bytes(4,'big')
 text=(p.OUT/'baseline/conker/asm/nonmatchings/game_1944C0/func_151670C0.s').read_text();assert '26520034'in text and '241E0065'in text and '24010002'in text
 words=list(struct.unpack_from('>11I',rom,0x194614));assert words==[0x8e590000,0x8e0d0008,0x02002025,0x0320f809,0xae2d0000,0x826e0000,0x000e7880,0x028f8821,0x8e300000,0x5600fff7,0x8e590000];cases=0
 for ws in g.streams():
  code=dict(zip(range(g.ENTRY,g.ENTRY+848,4),ws))
  for phase,level,life,mode in itertools.product((0,8),(1,2),(0,30),(0,7,24,31)):
   c=g.Case(phase=phase,life=life,mode=mode);memory=g.fixture(c);g.put(memory,g.OWNER+8,0);g.put(memory,SLOT,g.ENTRY);g.put(memory,NEST,level,1);g.put(memory,QUEUE+level*4,0x24681357)
   def model(selected):
    m=Caller(selected,c,entry=WINDOW,memory=dict(memory),arguments=(),connected=code);m.r[16]=g.OWNER;m.r[17]=QUEUE+level*4;m.r[18]=SLOT;m.r[19]=NEST;m.r[20]=QUEUE;m.before=m.r[:];return m
   expected=dict(memory);g.put(expected,QUEUE+level*4,0);wanted,calls,obs,fcsr=g.reference(expected,c);m=run(model(words))
   assert m.calls==[(g.ENTRY,(g.OWNER,)),*calls];assert g.public(m.memory,c)==g.public(wanted,c);assert m.observations==obs;assert m.fcsr==fcsr and m.r[16]==0 and m.r[29]==g.STACK+phase;cases+=1
 bad=list(words);bad[2]=0x00002025
 try:run(model(bad));raise AssertionError('Wrong A0 accepted')
 except WrongRecord:pass
 q=dict(pristine_ROM_sha256=hashlib.sha256(rom).hexdigest(),entire_pristine_aligned_ROM_scanned=True,entry_JALs=sites,entry_pointers=[hex(v)for v in pointers],qualified_entry_pointer=hex(SLOT),descriptor_type=49,descriptor_stride=52,actual_caller_cases=cases,streams=4,caller_routes=1,two_nesting_levels=True,prefetched_next_link_before_callback=True,return_value_ignored_by_dispatch_window=True,effective_wrong_A0_control=True,additional_static_entry_references=0,complete_parent_execution=False,helpers_internals_contracted=True,helper_matching_credit=0,source_installed=p.installed(),matching_credit=0);(p.OUT/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
