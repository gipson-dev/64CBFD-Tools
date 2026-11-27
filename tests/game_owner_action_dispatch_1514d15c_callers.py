"""Pinned original538-word caller and its exact four-word target/next-service window."""
from tools.experiments import game_owner_action_dispatch_1514d15c_match as target_packet
from pathlib import Path
from dataclasses import replace
import hashlib,itertools,json,re,struct,sys
sys.path.insert(0,str(target_packet.ROOT));o=target_packet.OUT;pass
from tools.tests import game_owner_action_dispatch_1514d15c_guest as g
from tools.tests import game_owner_action_dispatch_1514d15c_classifier_abi as abi
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
PARENT=0x15082A44;WINDOW=0x15083208;NEXT=0x150849A0;END=0x15083218
class Caller(g.Machine):
 def __init__(self,window,words,c):
  self.entries=[];super().__init__(window,c,entry=WINDOW,arguments=(0,0,0,0),connected=dict(zip(range(g.ENTRY,g.ENTRY+436,4),words)))
  self.r[16]=g.owner(c);self.before=self.r[:];self.code=WindowCode(self.code,self);self.code.ends=(END,)
 def record_call(self,t):
  if t in(g.ENTRY,NEXT):
   a=tuple(map(g.u32,self.arguments(1)));self.calls.append((t,a));self.events.append(('CALL',t,a))
   if t==g.ENTRY:self.entries.append(a)
  else:super().record_call(t)
 def hook(self,t):
  if t!=NEXT:return super().hook(t)
  g.put(self.memory,g.MARK+16,0xCAFEBABE);value=0x12340000+self.c.seed
  for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
  self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011;self.r[2]=g.u32(value)

def run(window,words,c):
 m=Caller(window,words,c)
 try:m.run();raise AssertionError('Original window did not stop at83218')
 except WindowBoundary:pass
 return m

def interface():
 r=g.r;rom=(r/'conker/conker.us.bin').read_bytes();elf=(o/'baseline/conker/build/conker.us.elf').read_bytes();asm=(o/'baseline/conker/asm/AEB40.s').read_text();body=asm.split('glabel func_15082A44\n',1)[1].split('endlabel func_15082A44',1)[0];rows=re.findall(r'/\*\s*([0-9A-F]+)\s+([0-9A-F]+)\s+([0-9A-F]{8})\s*\*/',body);blob=bytes.fromhex(''.join(v[2]for v in rows));assert len(blob)==538*4 and blob==rom[0xAFEF4:0xB075C];assert abi.at(elf,PARENT,12)==bytes.fromhex('0000102503e0000800000000')
 assert's32 func_15082A44() {\n    return 0;\n}'in(o/'baseline/conker/src/game/generated_AEB40.c').read_text()
 window=struct.unpack_from('>4I',rom,0xB06B8);assert window==(0x0D453457,0x02002025,0x0D421268,0x02002025)
 literal=[];direct=[];class_calls=[]
 for off in range(0,len(rom)-3,4):
  w=struct.unpack_from('>I',rom,off)[0]
  if w==g.ENTRY:literal.append(hex(off))
  if w>>26 in(2,3)and w&0x3FFFFFF==g.ENTRY>>2&0x3FFFFFF:direct.append(hex(off))
  if w>>26 in(2,3)and w&0x3FFFFFF==g.CLASSIFY>>2&0x3FFFFFF:class_calls.append(hex(off))
 assert not literal and direct==['0xb06b8']and class_calls==['0x17a6c8'],(literal,direct,class_calls)
 table=abi.at(elf,g.TABLE,58*4);assert table==rom[0x22F530:0x22F618]and abi.at(elf,g.TABLE+23*4,4)==table[92:96];assert g.TABLE+58*4==0x8008AB58
 q=dict(function='func_1514D15C',ABI='s32 (u8 *)',parent='func_15082A44',original_parent_words_pinned=538,parent_ASM_ROM_sha256=hashlib.sha256(blob).hexdigest(),production_parent_remains12byte_stub=True,original_call_window_words=4,window_entry=hex(WINDOW),window_end=hex(END),passed_owner_from_S0_in_delay=True,target_return_ignored_and_next_service_receives_same_owner=True,aligned_ROM_literals=literal,aligned_direct_call_patterns=direct,classifier_aligned_direct_call_patterns=class_calls,callback_table_entries=58,pre_callback_aliases_table_index23=True,full_callback_table_ELF_ROM_exact=True,callback_table_sha256=hashlib.sha256(table).hexdigest(),complete_parent_execution_not_claimed=True,source_installed=target_packet.installed(),matching_credit=0)
 (o/'interface-qualified.json').write_text(json.dumps(q,indent=2)+'\n');return window,q

def main():
 window,iface=interface();ws=g.streams();programs=[ws[i]for i in(0,1,3)];count=0
 for index,gate,flags,effects,mode,phase in itertools.product((-2,0,3),(0,1),(0,3,7),(0,2),(0,15),(0,8)):
  c=g.Case(index=index,gate=gate,flags=flags,effects=effects,mode=mode,phase=phase,seed=flags);initial=g.fixture(c);memory,calls,result=g.reference(initial,c);g.put(memory,g.MARK+16,0xCAFEBABE);expected_calls=[(g.ENTRY,(g.owner(c),)),*calls,(NEXT,(g.owner(c),))];models=[]
  for words in programs:
   m=run(window,words,c);assert(g.public(m.memory,c),m.calls,m.entries,m.r[2])==(memory,expected_calls,[(g.owner(c),)],0x12340000+c.seed);models.append(m)
  assert all(g.state(m)==g.state(models[0])for m in models[1:]);count+=1
 c=g.Case();base=run(window,programs[0],c);controls=[]
 for name,where,value in(('skipped-target',0,0),('wrong-owner-delay',1,0x26040004)):
  bad=list(window);bad[where]=value;m=run(bad,programs[0],c);assert m.entries!=[(g.owner(c),)]or(g.public(m.memory,c),m.calls)!=(g.public(base.memory,c),base.calls),name;controls.append(dict(name=name,comparison_rejected=True))
 poisons=[]
 for value in(0x24020000,0x2402FFFF):
  bad=list(programs[0]);bad[0x19C//4]=value;m=run(window,bad,c);assert(g.public(m.memory,c),m.calls,m.r[2])==(g.public(base.memory,c),base.calls,base.r[2]);poisons.append(hex(value))
 q=dict(static_interface=iface,original_parent_words_pinned=538,original_parent_words_executed=4,exact_original_call_window=True,complete_parent_execution_not_claimed=True,cases_per_stream=count,streams=3,connected_target_invocations_per_stream=count,all_literal_full_private_states_equal=True,independent_target_reference_public_effects_calls_and_next_result_equal=True,effective_controls=controls,ignored_target_return_poisons=poisons,other_services_opaque=True,source_installed=target_packet.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
