"""Original decode-result dispatch/case/shared-return with complete child attached."""
from pathlib import Path
from dataclasses import dataclass,replace
from functools import lru_cache
import hashlib,itertools,json,struct,sys
sys.path.insert(0,str(Path.cwd()));pass
from tools.tests import game_owner_position_preset_150f802c_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments import game_owner_position_preset_150f802c_match as p
r,o=p.ROOT,p.OUT;PARENT,START,RETURN=0x150265cc,0x15027550,0x15029ba4;COMMAND=0x32000;TABLE=0x800c3958;JUMP=0x80096c00;BANKS=tuple(0x400000+0x1000*i for i in range(4));FRAME=0x750
@dataclass(frozen=True)
class Case(g.Case):
 record:int=1
 bank:int=1
 subcommand:int=10
 decoded:int=0x12348001
 timestamp:int=0
def parent_home(c):return g.STACK+c.phase
def parent_sp(c):return parent_home(c)-FRAME
def source_point(c):return BANKS[c.bank]+68*c.record
@lru_cache(maxsize=1)
def jump_bytes():
 elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();rom=(r/'conker/conker.us.bin').read_bytes();start,base,_,_=g.load_game_data_layout(r/'conker');at=elf_slot_offset(elf,JUMP,104);blob=elf[at:at+104];assert blob==rom[start+JUMP-base:start+JUMP-base+104];return blob
def fixture(c):
 m=g.fixture(c)
 for i,v in enumerate(jump_bytes()):m[JUMP+i]=v
 for bank in range(4):
  g.put(m,TABLE+4*bank,BANKS[bank])
  for record in range(8):
   p=BANKS[bank]+68*record
   for i in range(68):m[p+i]=(i*19+record*31+bank*53+c.seed*7)&255
   for i in range(6):g.put(m,p+4*i,g.bits(float(bank*100+record*10+i+.25)))
 m.update({COMMAND+i:(i*23+c.seed*7+0x31)&255 for i in range(16)});m[COMMAND]=5;g.put(m,COMMAND+2,0x65,2);m[COMMAND+4]=0;m[COMMAND+5]=c.subcommand&255
 sp=parent_sp(c);g.put(m,sp+0x754,c.record);g.put(m,sp+0x75c,c.timestamp);g.put(m,sp+0x760,c.bank);g.put(m,sp+0x770,c.slot)
 return m
def original_words(rom):return list(struct.unpack_from('>3451I',rom,0x53a7c))
class Connected(g.Machine):
 def __init__(self,words,c,rom,parent_override=None):
  self.parent_case=c;self.children=[];self.pending=False
  parent=original_words(rom)if parent_override is None else parent_override;code=dict(zip(range(PARENT,PARENT+4*len(parent),4),parent));code.update(zip(range(g.ENTRY,g.ENTRY+400,4),words));dispatch=parent[(START-PARENT)//4:(0x15027584-PARENT)//4]
  super().__init__(dispatch,c,entry=START,memory=fixture(c),args=(COMMAND,c.record,0,c.timestamp),connected=code)
  self.r[29]=parent_sp(c);self.r[16]=COMMAND;self.r[2]=g.u32(c.decoded)
  self.before[29]=parent_home(c);g.put(self.memory,parent_sp(c)+0xd0,self.before[16]);g.put(self.memory,parent_sp(c)+0xd4,self.before[31]);self.initial=dict(self.memory)
 def close_child(self):
  self.children.append(dict(case=self.c,initial=self.child_initial,final=dict(self.memory),calls=self.calls[self.child_calls:],observations=self.observations[self.child_obs:],fcsr=self.fcsr));self.pending=False;self.c=self.parent_case;self.provider_count=0
 def execute(self,w):
  if self.pending and self.current_pc==0x15027800:self.close_child()
  super().execute(w)
 def record_call(self,t):
  if t==g.ENTRY:
   args=tuple(map(g.u32,self.arguments(4)));self.calls.append((t,args));self.events.append(('CALL',t,args));assert not self.pending
   self.c=replace(self.parent_case,point=args[0],parameter=args[1],slot=args[2],context=args[3],phase=self.r[29]-g.STACK,rm=self.fcsr);self.child_initial=dict(self.memory);self.child_calls=len(self.calls);self.child_obs=len(self.observations);self.provider_count=0;self.pending=True;return
  super().record_call(t)
def verify(m,c):
 assert not m.pending;sp=parent_sp(c);expected=dict(m.initial);diff=g.u32(c.decoded-c.timestamp);g.put(expected,sp+0x660,diff);inside=c.subcommand==10;assert len(m.children)==int(inside)
 expected_calls=[]
 if inside:
  parameter=g.u32(((diff&65535)^32768)-32768);args=(source_point(c),parameter,c.slot&255,1);child=m.children[0];cc=child['case'];assert g.arguments(cc)==args,(c,'caller args',g.arguments(cc),args)
  assert g.public(child['initial'],c)==g.public(expected,c),'Caller child public prestate'
  end,calls,obs,fcsr,value=g.reference(child['initial'],cc);assert child['calls']==calls and child['observations']==obs and child['fcsr']==fcsr
  assert g.public(child['final'],cc)==g.public(end,cc)and g.data(child['final'],g.packet(cc),144)==g.data(end,g.packet(cc),144)
  expected_calls=[(g.ENTRY,args),*calls];expected=end
 else:fcsr=c.rm
 assert m.calls==expected_calls,(c,'calls');assert g.public(m.memory,c)==g.public(expected,c),(c,'public');assert m.r[2]==1 and m.r[29]==parent_home(c)and m.r[16:24]==m.before[16:24]and m.r[28:]==m.before[28:]and m.f[20:]==m.before_f[20:]and m.fcsr==fcsr
 assert g.read(m.memory,sp+0x660)==diff
 return inside
def main():
 rom=(r/'conker/conker.us.bin').read_bytes();inventory=json.loads((o/'caller-inventory.json').read_bytes());assert inventory['complete_ASM_words_equal_pristine_ROM']and inventory['target_subcommand']==10
 corpus=[Case(slot=i,record=i%8,bank=i&1,decoded=(0x8000,0x7fff,0,0x80000000,0xffffffff)[i%5],timestamp=g.u32(i*0x87654321),outcome=i&1,mutation=i%8,rm=i%4,phase=(i&1)*8,seed=i&15)for i in range(256)]
 corpus +=[Case(slot=slot,record=record,bank=bank,decoded=decoded,timestamp=timestamp,outcome=outcome,mutation=mutation,rm=rm)for slot,record,bank,decoded,timestamp,outcome,mutation,rm in itertools.product((0,255),(0,7),(0,1),(0x8000,0x7fff),(0,0xffffffff),(0,1),(0,7),(0,3))]
 corpus +=[Case(subcommand=v,slot=slot,phase=phase)for v,slot,phase in itertools.product((0,27,127,128,255),(0,255),(0,8))]
 seen=set();children=0;retail=g.programs();assert all(w==retail[0]for w in retail);programs=[retail[0],g.raw_program()]
 for c in corpus:
  models=[]
  for words in programs:
   m=Connected(words,c,rom).run();verify(m,c);models.append(m)
  a=models[0];assert all((a.memory,a.r,a.f,a.fcsr,a.hi,a.lo,a.calls,a.observations,a.frames)==(b.memory,b.r,b.f,b.fcsr,b.hi,b.lo,b.calls,b.observations,b.frames)for b in models[1:]);children+=len(a.children);seen|={p for p in a.visits if PARENT<=p<0x15029bb8}
 expected=set(range(0x15027550,0x15027584,4))|set(range(0x150277c4,0x15027804,4))|set(range(0x15029ba0,0x15029bb8,4));assert seen==expected,(len(seen),sorted(expected-seen),sorted(seen-expected))
 controls=[];c=Case(record=1,bank=1,decoded=0x8001,timestamp=1,slot=0x123400ff,mutation=7)
 for name,find,change in [('record-stride',lambda w:w==0x01ee7821,lambda w:0x01e07825),('table-index-scale',lambda w:w==0x000fc080,lambda w:w+64),('parameter-high-half',lambda w:w==0x87a50662,lambda w:w-2),('slot-other-byte',lambda w:w==0x93a60773,lambda w:w-1)]:
  parent=original_words(rom);positions=[i for i,w in enumerate(parent)if 0x150277c4<=PARENT+4*i<0x15027804 and find(w)];assert len(positions)==1,name;at=positions[0];parent[at]=change(parent[at]);m=Connected(programs[0],c,rom,parent).run();assert m.r[2]==1 and m.r[29]==parent_home(c)and len(m.children)==1
  try:verify(m,c)
  except AssertionError:controls.append(dict(name=name,supported_complete_bounded_execution=True,rejected=True))
  else:raise AssertionError('Ineffective bounded caller control')
 q=dict(original_parent_words=3451,parent_frame=FRAME,whole_original_parent_ASM_and_literal_call_census_audited=True,complete_parent_runtime_coverage=False,bounded_entry=hex(START),bounded_entry_precondition='type5/opcode65/state0 path after func15023BB0 returns; savedS0/RA and incoming homes are valid',bounded_parent_words_visited=len(seen),bounded_cases_per_stream=len(corpus),streams=len(programs),connected_children_per_stream=children,table_entries=26,target_table_index=9,target_subcommand=10,table_pinned_ROM_and_frozen_ELF=True,decoder_return_minus_timestamp_word_and_signed_low_half_checked=True,independent_table_and_record_indices=True,source_record_stride=68,source_first_six_float_bytes=24,unknown_assembly_record_C_effective_type_not_claimed=True,invalid_subcommand_paths_return1=True,child_return_overwritten_with1=True,full_shared_parent_return_and_saved_register_restore=True,effective_controls=controls,prefix_decoder_and_unrelated_cases_are_preconditions_not_runtime_results=True,parent_C_remains_unmatched_stub_and_uncredited=True,source_installed=p.installed(),matching_credit=0)
 (o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=='__main__':main()
