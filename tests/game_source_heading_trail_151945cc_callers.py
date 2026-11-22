"""Original registered two-actor/context dispatch through both actual JALR sites."""
from pathlib import Path
from dataclasses import replace
import itertools,json,struct,sys
from tools.experiments import game_source_heading_trail_151945cc_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_source_heading_trail_151945cc_guest as g
import csv
from tools.experiments.game_actor_classifier_candidates import sections
def census():
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();entry=0x151945CC;calls=[];pointers=[]
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
  if len(row)<5 or row[2]not in('func_1504715C','func_15134070','func_15153F18','func_151B4CD0'):continue
  a,b=[int(v,16)for v in row[3:5]];at=elf_slot_offset(elf,a,b-a)
  providers.append(dict(name=row[2],words=(b-a)//4,current_equals_original=elf[at:at+b-a]==rom[a-0x15000000+0x2D4B0:b-0x15000000+0x2D4B0]))
 r=dict(direct_calls=calls,aligned_loaded_pointer_literals=pointers,providers=providers,computed_references_not_excluded=True)
 (out/'caller-census.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r

from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
def main():
 evidence=census();assert evidence['direct_calls']==[]and evidence['aligned_loaded_pointer_literals']==[{'section':'.game_data','address':0x800866BC}]
 assert all(v['current_equals_original']for v in evidence['providers'])
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();streams=g.programs();count=0;controls=[]
 assert rom[0x22B17C:0x22B180]==struct.pack('>I',g.ENTRY)
 assert elf[elf_slot_offset(elf,0x80086694,160):elf_slot_offset(elf,0x80086694,160)+160]==rom[0x22B154:0x22B1F4]
 for entry,end,slot,load_source in((0x1505BD78,0x1505BD9C,0x67,True),(0x1505C6DC,0x1505C6FC,0x54,False)):
  n=(end-entry)//4;words=list(struct.unpack_from('>%dI'%n,rom,entry-0x15000000+0x2D4B0))
  at=elf_slot_offset(elf,entry,4*n);assert elf[at:at+4*n]==struct.pack('>%dI'%n,*words)
  for kind,category,mode,phase,alias in itertools.product((0,1,98,99),(1,2),(0,7),(0,8),(0,1)):
   c=g.Case(kind=kind,category=category,mode=mode,phase=phase,alias=alias);observed=[]
   for ws in streams:
    connected=dict(zip(range(g.ENTRY,g.ENTRY+456,4),ws));connected[end]=0
    m=g.Oracle(words,c,entry=entry,connected=connected);frame=g.STACK+phase;source=g.ACTOR if alias else g.SOURCE
    m.r[2]=10;m.r[16]=g.ACTOR;m.r[17]=source;m.r[9]=0x12345678;m.before=m.r[:]
    g.put(m.memory,frame+0x68,source)
    for i,b in enumerate(rom[0x22B154:0x22B1F4]):m.memory[0x80086694+i]=b
    m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run();raise AssertionError('missing caller continuation')
    except WindowBoundary:pass
    assert m.calls[0]==(g.ENTRY,(source,g.ACTOR,frame+slot)),m.calls[0]
    assert [t for t,_ in m.calls[1:3]]==[g.SURFACE,g.CLASSIFY]
    effective=category^3 if mode&4 and kind!=99 else category
    assert len(m.calls)==(3 if kind==99 or effective==2 else 5)
    if load_source:assert g.read(m.memory,frame+0x30)==0x12345678
    assert m.r[29]==frame and m.r[16:24]==m.before[16:24]
    observed.append(g.state(m))
   assert observed[0]==observed[1]==observed[2];count+=1
  # A poisoned third register makes omission of the context delay observable.
  changed=list(words);changed[-1]=0;connected=dict(zip(range(g.ENTRY,g.ENTRY+456,4),streams[1]));connected[end]=0
  m=g.Oracle(changed,g.Case(),entry=entry,connected=connected);m.r[2]=10;m.r[16]=g.ACTOR;m.r[17]=g.SOURCE;m.r[6]=0xBAD0BAD0;m.r[9]=0x12345678;m.before=m.r[:]
  g.put(m.memory,g.STACK+0x68,g.SOURCE)
  for i,b in enumerate(rom[0x22B154:0x22B1F4]):m.memory[0x80086694+i]=b
  m.code=WindowCode(m.code,m);m.code.ends=(end,)
  try:m.run()
  except WindowBoundary:pass
  if load_source:assert g.read(m.memory,g.STACK+0x30)!=0x12345678
  else:assert m.calls[0][1][2]!=g.STACK+slot
  controls.append(hex(entry)+'-missing-delay')
 r=dict(cases_per_stream=count,streams=3,registered_table_base=0x80086694,registered_index=10,entry_ROM=0x22B17C,
  original_caller_windows=2,executed_caller_words=17,current_windows_equal_original=True,
  source_actor_context_ABI=True,context_byte_pointer_unused=True,callback_return_ignored=True,
  effective_controls=controls,full_parent_execution=False,source_installed=packet.installed(),matching_credit=0)
 (out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
if __name__=='__main__':main()
