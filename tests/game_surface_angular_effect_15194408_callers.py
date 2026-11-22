"""Execute the real two-actor call windows; bound the providers explicitly."""
from pathlib import Path
from dataclasses import replace
import csv,itertools,json,struct,sys
from tools.experiments import game_surface_angular_effect_15194408_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_surface_angular_effect_15194408_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes()

def census():
 calls=[];pointers=[]
 for i in range(0,len(rom)-3,4):
  w=struct.unpack_from('>I',rom,i)[0]
  if w>>26 in(2,3)and(w&0x3FFFFFF)<<2==g.ENTRY&0xFFFFFFF:
   assert 0x2D4B0<=i<0x2288C0;calls.append(0x15000000+i-0x2D4B0)
 from tools.experiments.game_actor_classifier_candidates import sections
 for name,(address,data)in sections(out/'baseline/conker/build/conker.us.elf').items():
  if not address or name.startswith(('.mdebug','.symtab','.strtab')):continue
  for at in range(0,len(data)-3,4):
   if struct.unpack_from('>I',data,at)[0]==g.ENTRY:pointers.append((name,address+at))
 assert calls==[0x15074FBC,0x151945B4]and not pointers,(calls,pointers)
 providers=[]
 for row in csv.reader((root/'conker/retail_layout.us.txt').read_text().splitlines()):
  if len(row)<5 or row[2]not in('func_1504715C','func_151AE7B0','func_15153F18','func_15074F48','func_15194588'):continue
  a,b=[int(v,16)for v in row[3:5]];at=elf_slot_offset(elf,a,b-a)
  providers.append(dict(name=row[2],words=(b-a)//4,current_equals_original=elf[at:at+b-a]==rom[a-0x15000000+0x2D4B0:b-0x15000000+0x2D4B0]))
 assert len(providers)==5 and all(v['current_equals_original']for v in providers),providers
 r=dict(direct_calls=calls,aligned_loaded_pointer_literals=pointers,providers=providers,computed_references_not_excluded=True)
 (out/'caller-census.json').write_text(json.dumps(r,indent=2)+'\n');return r

def main():
 evidence=census();streams=g.programs();count=0;controls=[]
 for entry,end,home,delay in((0x15074FB8,0x15074FC4,32,0xE4A6003C),(0x151945B0,0x151945BC,24,0x8FA5001C)):
  words=list(struct.unpack_from('>3I',rom,entry-0x15000000+0x2D4B0));assert words[2]==delay
  assert elf[elf_slot_offset(elf,entry,12):elf_slot_offset(elf,entry,12)+12]==struct.pack('>3I',*words)
  for kind,mode,phase in itertools.product((0,1,4,5,255),(0,3,7),(0,8)):
   c=g.Case(kind=kind,mode=mode,phase=phase);observed=[]
   for ws in streams:
    connected=dict(zip(range(g.ENTRY,g.ENTRY+384,4),ws));connected[end]=0
    m=g.Oracle(words,c,entry=entry,connected=connected)
    frame=g.STACK+phase;m.code=WindowCode(m.code,m);m.code.ends=(end,)
    # The real window's stack frame belongs to the caller. Target SP is this
    # frame; tests use that actual home when describing nested target locals.
    m.target_home=frame;m.r[4]=g.OTHER;m.r[5]=g.ACTOR;m.f[0]=g.bits(2.);m.f[4]=g.bits(3.)
    g.put(m.memory,frame+home,g.OTHER);g.put(m.memory,frame+home+4,g.ACTOR)
    m.initial=dict(m.memory)
    try:m.run();raise AssertionError('missing original continuation')
    except WindowBoundary:pass
    assert m.calls[0]==(g.ENTRY,(g.OTHER,g.ACTOR)),m.calls
    if kind<5:
     assert [t for t,_ in m.calls]==[g.ENTRY,g.ATTACH,g.SURFACE,g.SUBMIT]
     assert m.calls[1][1]==(g.ACTOR,0x3F19999A,90,255,1)
    else:assert len(m.calls)==1
    if entry==0x15074FB8:assert g.read(m.memory,g.ACTOR+0x3C)==g.bits(6.)
    assert m.r[29]==frame and m.r[16:24]==m.before[16:24]and m.f[20:]==m.before_f[20:]
    observed.append(g.state(m))
   assert observed[0]==observed[1]==observed[2];count+=1
  # Omitting either real delay must be detected, using poisoned A1/output.
  negative=list(words);negative[2]=0;c=g.Case()
  connected=dict(zip(range(g.ENTRY,g.ENTRY+384,4),streams[0]));connected[end]=0
  m=g.Oracle(negative,c,entry=entry,connected=connected)
  frame=g.STACK;m.r[4]=g.OTHER;m.r[5]=g.OTHER if entry==0x151945B0 else g.ACTOR
  m.f[0]=g.bits(2.);m.f[4]=g.bits(3.);g.put(m.memory,frame+home,g.OTHER);g.put(m.memory,frame+home+4,g.ACTOR)
  if entry==0x15074FB8:g.put(m.memory,g.ACTOR+0x3C,0xDEADBEEF)
  m.code=WindowCode(m.code,m);m.code.ends=(end,)
  try:m.run()
  except WindowBoundary:pass
  if entry==0x15074FB8:assert g.read(m.memory,g.ACTOR+0x3C)!=g.bits(6.)
  else:assert m.calls[0]!=(g.ENTRY,(g.OTHER,g.ACTOR))
  controls.append(hex(entry)+'-missing-delay')
 r=dict(cases_per_stream=count,streams=3,original_windows=2,executed_caller_words=6,full_parent_execution=False,
  parent_complete_words_statically_exact=True,two_actor_pointer_ABI=True,effective_controls=controls,source_installed=packet.installed(),matching_credit=0)
 (out/'callers.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
if __name__=='__main__':main()
