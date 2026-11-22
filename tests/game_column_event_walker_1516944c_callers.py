"""Actual complete packet wrapper, all-byte ABI and retail direct-call census."""
from pathlib import Path
from dataclasses import replace
import csv,itertools,json,struct,sys
from tools.experiments import game_column_event_walker_1516944c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_column_event_walker_1516944c_guest as p
g=p.g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
WRAPPER=0x1516962C;ACTOR=0x60000
class CallerOracle(p.Oracle):
 def record_call(self,t):
  if t==p.ENTRY:
   assert tuple(self.arguments(3))==p.arguments(self.case,self.syms),'Caller arguments differ'
   packet=g.STACK+self.case.phase+24
   assert g.read(self.memory,packet)==ACTOR and self.memory[packet+4]==0xF7 and bytes(self.memory[packet+i]for i in(5,6,7))==self.packet_tail,'Packet or delay-slot tag differs'
   self.root_calls+=1;self.root_initial=dict(self.memory);return
  super().record_call(t)
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();before=(out/'baseline/conker/build/conker.us.elf').read_bytes();after=(out/'image-qualification/linked.elf').read_bytes()
 at=elf_slot_offset(before,WRAPPER,60);truth=rom[0x196ADC:0x196B18];assert before[at:at+60]==after[at:at+60]==truth
 caller=list(struct.unpack('>15I',truth));jal=0x0C000000|(p.ENTRY>>2&0x3FFFFFF);jump=0x08000000|(p.ENTRY>>2&0x3FFFFFF)
 direct=[];pointers=[];jumps=[]
 for i,(w,)in enumerate(struct.iter_unpack('>I',rom)):
  if w==jal:direct.append(4*i)
  if w==p.ENTRY:pointers.append(4*i)
  if w==jump:jumps.append(4*i)
 rows=list(csv.DictReader((root/'conker/progress.csv').open()));sites=[]
 for offset in direct:
  va=0x15000000+offset-0x2D4B0;sites.append(dict(ROM='0x%X'%offset,VA='0x%X'%va,owners=[r['function']for r in rows if r['section']=='game'and int(r['offset'])<=va<int(r['offset'])+int(r['length'])]))
 paths=[out/'assign-1/candidate.o',out/'qualified-owner/game_1944C0.c.o',out/'original-target.o'];helpers=p.helper_code();count=0;visits=set()
 original_payload=g.payload
 def packet_payload(c,s=g.SYMS):return g.STACK+c.phase+24 if c.payload_kind==5 else original_payload(c,s)
 g.payload=packet_payload
 try:
  def machine(ws,c,broken=None):
   memory=p.fixture(c);memory[ACTOR+0x3B]=0xF7;words=list(caller)
   if broken=='tag':words[10]=0
   if broken=='byte':words[2]=0x00C07025
   connected=dict(zip(range(p.ENTRY,p.ENTRY+4*len(ws),4),ws))
   if c.real_helpers:connected.update(helpers)
   m=CallerOracle.__new__(CallerOracle);FactoryOracle.__init__(m,words,memory,replace(c,phase=c.phase&8),entry=WRAPPER,s=p.SYMS,connected=connected,arguments=(g.u32(c.first),ACTOR,0xABCD0000|(c.opcode&255)))
   m.case=c;m.target_home=g.STACK+c.phase;m.r[29]=m.target_home+32;m.ws=ws;m.initial=dict(m.memory);m.before=m.r[:];m.before_f=m.f[:];m.observations=[];m.state=dict(fired=False);m.bound_helpers=connected;m.root_calls=0;m.root_initial=None;m.packet_tail=bytes(m.memory[m.target_home+24+i]for i in(5,6,7));return m
  cases=[replace(p.Case(),first=col,opcode=op,pattern=pattern,mode=mode,phase=phase,tag=tag,real_helpers=real,payload_kind=5)for col,op,pattern,mode,phase,tag,real in itertools.product((2,103),(15,16),range(3),(0,15,16,32,128),(0,8),(0,0x39),(False,True))]
  cases +=[replace(p.Case(),opcode=op,payload_kind=5)for op in range(256)]
  for path in paths:
   ws=p.words(path)
   for c in cases:
    m=machine(ws,c);m.run();assert m.root_calls==1
    want,calls,obs=p.reference(m.root_initial,c)
    assert(g.public(m.memory),m.calls,m.observations)==(g.public(want),calls,obs),c
    assert all(m.memory[a]==want[a]for a in m.root_initial if m.target_home<=a<m.target_home+96),('Caller homes',c)
    assert m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]
    assert g.read(m.memory,m.target_home+40)==0xABCD0000|(c.opcode&255)
    visits.update(m.visits);count+=1
  for broken in('tag','byte'):
   m=machine(p.words(paths[0]),cases[0],broken)
   try:m.run()
   except AssertionError:pass
   else:raise AssertionError('Ineffective caller '+broken+' control')
 finally:g.payload=original_payload
 assert {WRAPPER+4*i for i in range(15)}<=visits
 r=dict(cases_per_stream=len(cases),streams=3,executions=count,complete_original_current_caller_words=15,caller_frame=32,
  packet_pointer_delay_slot_tag_and_tail_preserved=True,all_256_opcode_bytes=True,high_caller_input_bits_narrowed=True,effective_caller_controls=['missing-delay-slot-tag','missing-byte-narrowing'],
  direct_JAL_sites=sites,aligned_pointer_literals=['0x%X'%i for i in pointers],direct_jumps=['0x%X'%i for i in jumps],
  other_full_parents_not_executed=True,source_installed=packet.installed(),matching_credit=0)
 (out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
