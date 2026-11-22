"""Original first-pool-actor origin and direct JAL/delay interface."""
from pathlib import Path
import itertools,json,struct,sys
from tools.experiments import game_paired_actor_initializer_151951e0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_paired_actor_initializer_151951e0_guest as g
import csv
from tools.experiments.game_actor_classifier_candidates import sections
def census():
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();entry=0x151951E0;calls=[];pointers=[]
 for i in range(0,len(rom)-3,4):
  w=struct.unpack_from('>I',rom,i)[0]
  if w>>26 in(2,3)and(w&0x3FFFFFF)<<2==entry&0xFFFFFFF:
   assert 0x2D4B0<=i<0x2288C0;calls.append(0x15000000+i-0x2D4B0)
 for name,(address,data)in sections(out/'baseline/conker/build/conker.us.elf').items():
  if not address or name.startswith(('.mdebug','.symtab','.strtab')):continue
  for at in range(0,len(data)-3,4):
   if struct.unpack_from('>I',data,at)[0]==entry:pointers.append(dict(section=name,address=address+at))
 providers=[]
 for row in csv.reader((root/'conker/retail_layout.us.txt').read_text().splitlines()):
  if len(row)<5 or row[2]not in('func_1507CD64','func_15194AB4','func_150ADA20','func_1505ED34','func_150838EC','func_150D10E4'):continue
  a,b=[int(v,16)for v in row[3:5]];at=elf_slot_offset(elf,a,b-a)
  providers.append(dict(name=row[2],words=(b-a)//4,current_equals_original=elf[at:at+b-a]==rom[a-0x15000000+0x2D4B0:b-0x15000000+0x2D4B0]))
 r=dict(direct_calls=calls,aligned_loaded_pointer_literals=pointers,providers=providers,computed_references_not_excluded=True)
 (out/'caller-census.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r

from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
POOL=0x800CC2D0
def main():
 r=census();assert r['direct_calls']==[0x150D0FD8]and not r['aligned_loaded_pointer_literals']
 assert all(v['current_equals_original']for v in r['providers'])
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes()
 parent=0x150D0E90;size=0x254;at=elf_slot_offset(elf,parent,size);current=elf[at:at+size]
 assert current==struct.pack('>3I',0x00001025,0x03E00008,0)+bytes(size-12)
 def words(a,n):
  blob=rom[a-0x15000000+0x2D4B0:a-0x15000000+0x2D4B0+4*n];return list(struct.unpack('>%dI'%n,blob))
 prefix=words(0x150D0E9C,9);end=0x150D0EC0
 m=g.Oracle(prefix,g.Case(),entry=0x150D0E9C,connected={end:0});m.code=WindowCode(m.code,m);m.code.ends=(end,)
 try:m.run();raise AssertionError('missing prefix boundary')
 except WindowBoundary:pass
 assert m.r[17]==POOL
 # The intervening parent instructions and ABI-compliant callees retain S1.
 middle=words(0x150D0EC0,(0x150D0FD8-0x150D0EC0)//4)
 for w in middle:
  op,rt,rd,fn=w>>26,w>>16&31,w>>11&31,w&63
  dest=rd if op==0 and fn not in(8,9,24,25,26,27)else rt if op in(9,10,11,12,13,14,15,32,33,35,36,37)else None
  assert dest!=17
 window=words(0x150D0FD8,2);assert window==[0x0D465478,0x02202025]
 continuation=words(0x150D0FE0,7);assert all(not((w>>21&31)==2 or(w>>16&31)==2)for w in continuation)
 streams=g.programs();count=0
 for mode,phase,alias,value in itertools.product((0,1,2,4,8,15),(0,8),(0,1),(0,0xFFFFFFFF)):
  c=g.Case(mode=mode,phase=phase,alias=alias,values=(value,)*5);seen=[]
  for ws in streams:
   end=0x150D0FE0;code=dict(zip(range(g.ENTRY,g.ENTRY+840,4),ws));code[end]=0
   m=g.Oracle(window,c,entry=0x150D0FD8,connected=code);m.r[17]=g.ACTOR;m.before=m.r[:]
   m.code=WindowCode(m.code,m);m.code.ends=(end,)
   try:m.run();raise AssertionError('missing caller continuation')
   except WindowBoundary:pass
   assert m.calls[0]==(g.ENTRY,(g.ACTOR,)) and len(m.calls)==12
   assert m.r[29]==g.STACK+phase and m.r[16:24]==m.before[16:24]
   seen.append(g.final_state(m))
  assert seen[0]==seen[1]==seen[2];count+=1
 bad=list(window);bad[1]=0;end=0x150D0FE0;code=dict(zip(range(g.ENTRY,g.ENTRY+840,4),streams[1]));code[end]=0
 m=g.Oracle(bad,g.Case(),entry=0x150D0FD8,connected=code);m.r[4]=0xBAD0BAD0;m.r[17]=g.ACTOR;m.before=m.r[:]
 try:m.run()
 except AssertionError as e:assert 'unmapped store' in str(e),str(e)
 else:raise AssertionError('missing-delay accepted')
 report=dict(cases_per_stream=count,streams=3,original_origin_words=9,original_call_words=2,original_continuation_words=7,current_parent_is_zero_stub=True,original_caller_only=True,actual_actor_origin=POOL,one_pointer_ABI=True,return_ignored_by_continuation=True,effective_control='missing actor delay move',full_parent_execution=False,source_installed=packet.installed(),matching_credit=0)
 (out/'callers.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report
if __name__=='__main__':main()
