"""Original two-level VM callback, register result publication and real actor lookup."""
import csv,itertools,json,struct
from dataclasses import replace
from tools.tests import game_event_dispatch_1509d780_oracle as g
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
VM,OUTER,OUTER_END,LOOP=0x150AE108,0x150ADFD8,0x150AE028,0x150ADBC4
COUNTER,RESULT,RESULTPTR,BUILTINS,CALLBACKS=0x800D3844,0x800D3848,0x800D384C,0x800886A4,0x8008845C
ACTORS=0x800CC2D0
def original(rom,start,size):return struct.unpack_from('>%dI'%(size//4),rom,start-0x15000000+0x2D4B0)
def memory_data(m,elf,va,size):
 at=elf_slot_offset(elf,va,size);m.update({va+i:b for i,b in enumerate(elf[at:at+size])})
def census():
 rom=(g.root/'conker/conker.us.bin').read_bytes();sites=[];pointers=[]
 for at in range(0,len(rom)-3,4):
  w=struct.unpack_from('>I',rom,at)[0]
  if w==g.ENTRY:pointers.append(hex(at))
  if w>>26 in(2,3)and(w&0x03FFFFFF)<<2==g.ENTRY&0x0FFFFFFF:sites.append(hex(at))
 assert sites==[]and pointers==['0x22cf50']
 return dict(direct_J_or_JAL_sites=sites,literal_pointers=pointers,callback_table=hex(CALLBACKS),callback_entry=13,callback_address='0x80088490',computed_indirect_calls_excluded=False)
class CallerOracle(g.Oracle):
 def record_call(self,t):
  if t==VM:args=(self.r[4],);self.calls.append((t,args));self.events.append(('CALL',t,args))
  else:super().record_call(t)
def run_vm(rom,elf,ws,c):
 command=g.u32(c.command)&0xFFFF0FFF;c=replace(c,command=command,packet_mode=0);memory=g.fixture(c);home=g.STACK+c.phase;packet=g.packet(c);g.put(memory,packet,command|0xE000)
 memory_data(memory,elf,BUILTINS,56);memory_data(memory,elf,CALLBACKS,60);assert g.read(memory,BUILTINS+4*4)==VM and g.read(memory,CALLBACKS+13*4)==g.ENTRY
 for address,value in((COUNTER,0x11223344),(RESULT,0x87654321),(RESULTPTR,0x12345678)):g.put(memory,address,value)
 code=dict(zip(range(g.ENTRY,g.ENTRY+380,4),ws));code.update(zip(range(VM,0x150AE194,4),original(rom,VM,0x8C)));code[LOOP]=0
 m=CallerOracle(original(rom,OUTER,OUTER_END-OUTER),memory,c,entry=OUTER,connected=code);m.r[21]=packet;m.r[10]=4;m.code=WindowCode(m.code,m);m.code.ends=(LOOP,);m.initial=dict(m.memory);m.before=m.r[:];m.before_f=m.f[:]
 expected=dict(m.initial);g.put(expected,COUNTER,0);expected,calls,value=g.reference(expected,c);g.put(expected,RESULT,value);g.put(expected,RESULTPTR,RESULT)
 try:m.run()
 except WindowBoundary:pass
 else:raise AssertionError('Missing VM loop continuation')
 assert m.calls==[(VM,(packet,)),(g.ENTRY,(command,packet))]+calls,(c,'VM-calls',m.calls,calls)
 assert g.public(m.memory)==g.public(expected),(c,'VM-public');assert m.r[2]==value and m.r[29]==home and m.r[31]==0x150AE004 and m.r[23]==0x150AE004,(c,'VM-return')
 assert m.r[16:23]==m.before[16:23]and m.r[28]==m.before[28]and m.r[30]==m.before[30]and m.f[20:]==m.before_f[20:],(c,'VM-preserved')
 return m
def run_lookup(rom,elf,ws,c,slot,state):
 memory=g.fixture(c)
 for i in range(26):
  actor=ACTORS+i*812;g.put(memory,actor,state if i==slot else 0);g.put(memory,actor+0x13F,c.word&255,1)
 code=dict(zip(range(g.LOOKUP,g.LOOKUP+220,4),original(rom,g.LOOKUP,220)));m=g.Oracle(ws,memory,c,connected=code);m.run();expected=dict(m.initial);key=g.read(expected,g.packet(c)+4)&4095;actor=ACTORS+slot*812 if slot<25 and state and key==(c.word&255)else 0
 calls=[(g.LOOKUP,(key,))];value=actor
 if actor:
  target=g.HELPERS[c.command];calls.append((target,(actor,)));value=g.effect(expected,c,target,(actor,),2)
 assert m.calls==calls,(c,slot,state,'lookup-calls');assert g.public(m.memory)==g.public(expected),(c,slot,state,'lookup-public');assert m.r[2]==value,(c,slot,state,'lookup-result')
 at=elf_slot_offset(elf,g.LOOKUP,220);assert elf[at:at+220]==rom[0x8C3A4:0x8C480]
 return m
def helper_abi():
 # This no-argument helper overwrites all argument registers before its first call.
 asm=(g.root/'conker/asm/1188E0.s').read_text(encoding='utf-8');body=asm.split('glabel func_150EB8C4\n',1)[1].split('endlabel func_150EB8C4',1)[0];prefix=body.split('jal ',1)[0]
 assert '$a0' in prefix and '$a1'in prefix and '$a2'in prefix and '$a3'in body.split('/* 118DD8',1)[0]
 return dict(original_no_argument_helper_entry_inspected=True,original_C_return_type_proven=False,explicit_C_result_branch='command9/null lookup only',portable_fallthrough_C_results_qualified=False)
def main():
 rom=(g.root/'conker/conker.us.bin').read_bytes();elf=(g.out/'frozen/conker/build/conker.us.elf').read_bytes();programs=(g.words(g.out/'selected.o'),original(rom,g.ENTRY,380));cs=[replace(g.Case(command=cmd,found=found,incoming=inc,mutation=mu),phase=(i&1)*8,seed=i%7)for i,(cmd,found,inc,mu)in enumerate(itertools.product(tuple(range(2,42))+(0,1,42,0x10009,0x80000000,0xFFFFFFFF),(0,1),(0,0xFFFFFFFF),(0,7)))];seen=set();pairs=0
 for c in cs:
  a,b=[run_vm(rom,elf,ws,c)for ws in programs];assert(a.memory,a.r,a.f,a.trace,a.calls)==(b.memory,b.r,b.f,b.trace,b.calls);pairs+=1;seen.update(pc for pc in a.visits if OUTER<=pc<OUTER_END or VM<=pc<0x150AE194)
 helper_seen=set();helper_pairs=0
 for cmd,key,slot,state in itertools.product((9,36),(0,255,256,4095),range(26),(0,1,0x80000000)):
  c=g.Case(command=cmd,word=key);a,b=[run_lookup(rom,elf,ws,c,slot,state)for ws in programs];assert(a.memory,a.r,a.f,a.trace,a.calls)==(b.memory,b.r,b.f,b.trace,b.calls);helper_pairs+=1;helper_seen.update(pc for pc in a.visits if g.LOOKUP<=pc<g.LOOKUP+220)
 result=dict(census=census(),ABI=helper_abi(),VM_pairs=pairs,VM_executions=2*pairs,VM_window_covered_words=len(seen),real_lookup_pairs=helper_pairs,real_lookup_executions=2*helper_pairs,real_lookup_covered_words=len(helper_seen),VM_result_publication_checked=True,original_handwritten_S7_convention_preserved=True,current_VM_C_stub_unchanged=True,full_VM_or_effect_helpers_qualified=False);(g.out/'callers.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
