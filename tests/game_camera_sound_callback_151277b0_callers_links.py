from pathlib import Path
from dataclasses import replace
import itertools,json,struct,subprocess,sys
from tools.experiments import game_camera_sound_callback_151277b0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_camera_sound_callback_151277b0_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions,load_symbol_addrs
from tools.pad_generated_object import parse_object
from tools.experiments.alternative_source_draft_word_screen import emit_function
START,END,DELETED,DELETE,COUNT=0x10011848,0x100118A8,0x10011B60,0x1000FE88,0x72000
def caller_checks():
 rom=(root/'conker/conker.us.bin').read_bytes();opening=struct.unpack_from('>24I',rom,0x11848)
 original=(out/'baseline/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(original,START,96);assert original[at:at+96]==rom[0x11848:0x118A8]
 assert opening[13:16]==(0x0040F809,0x03D92021,0x10400006)
 class Connected(g.Machine):
  def __init__(self,words,c,m,window=opening):
   self.c=c;code=dict(zip(range(g.ENTRY,g.ENTRY+496,4),words));code[END]=code[DELETED]=0
   FactoryOracle.__init__(self,window,m,c,entry=START,s=g.SYMS,arguments=(0xDEADC0DE,),connected=code)
   for register,value in((16,g.SLOT),(17,c.flags),(22,2),(23,COUNT),(30,0x60)):
    self.r[register]=value;self.before[register]=value
   self.visited_words=set();self.code=WindowCode(self.code,self);self.code.ends=(END,DELETED)
  def record_call(self,t):
   if t in(g.ENTRY,DELETE):
    a=tuple(self.arguments(7 if t==g.ENTRY else 3));self.calls.append((t,a));self.events.append(('CALL',t,a))
   else:super().record_call(t)
  def hook(self,t):
   if t==DELETE:
    assert self.calls[-1][1]==(g.SLOT-0x60,2,COUNT),self.calls[-1]
    g.put(self.memory,COUNT,2);g.put(self.memory,g.MARK+4,0xD311E7ED)
    for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xB9000000+r
   else:super().hook(t)
 count=0;returns=set()
 cases=[g.Case(phase=phase,mode=mode,state=state,counter=counter,delta=101,handle=handle,mutation=mutation,flags=0x12,state_pointer=g.STACK+phase+0xA6)
  for phase,mode,state,counter,handle,mutation in itertools.product((0,8),(0,2),(0,0x622,0x61C,0x61D),(0,10),(0,7),(0,1))]
 def execute(words,c,window=opening):
  m=g.fixture(c);home=g.STACK+c.phase;g.put(m,g.SLOT+0x14,g.ENTRY);g.put(m,home+0xC8,g.SLOT-0x60);g.put(m,COUNT,3)
  expected,calls,answer=g.reference(m,c,True);actual_args=(g.SLOT,home+0xB0,home+0xB4,home+0xBC,home+0xA8,home+0xA0,home+0xA6)
  if answer:g.put(expected,COUNT,2);g.put(expected,g.MARK+4,0xD311E7ED)
  machine=Connected(words,c,m,window)
  try:machine.run();raise AssertionError('missing caller boundary')
  except WindowBoundary:pass
  expected_calls=[(g.ENTRY,actual_args)]+calls+([(DELETE,(g.SLOT-0x60,2,COUNT))]if answer else[])
  assert(g.public(machine.memory,c),machine.calls)==(g.public(expected,c),expected_calls),c
  assert machine.r[29]==home
  assert g.read(machine.memory,home+0xA6,2)==g.read(expected,c.state_pointer,2),('caller sound ID',c)
  for offset in(0xA0,0xA8,0xB0,0xB4,0xBC):
   assert g.read(machine.memory,home+offset)==g.read(expected,home+offset),('unused caller mix local',offset,c)
  return machine,answer
 for c in cases:
  states=[]
  for words in g.programs():
   m,answer=execute(words,c);returns.add(answer);states.append((m.memory,m.trace,m.calls,m.current_pc,m.delay_of))
  assert states[0]==states[1]==states[2],c;count+=1
 assert returns=={0,1};rejected=[]
 for name,index,word in(('lost-seventh-argument',10,0),('lost-delay-record',14,0),('ignored-return',15,0x10000006)):
  window=list(opening);window[index]=word;failed=False
  for c in(cases[0],next(c for c in cases if c.mode==2)):
   try:execute(g.programs()[0],c,window)
   except(AssertionError,KeyError):failed=True
  assert failed,name;rejected.append(name)
 r={'caller':'func_10011624','window':hex(START),'window_words':24,'cases_per_stream':count,'streams':3,
  'seventh_argument':'caller SP+0xA6 sound ID, passed at SP+0x18','return_values_consumed':[0,1],
  'effective_controls':rejected,'delete_provider_bounded':True,'whole_caller_claim':False,'source_installed':packet.installed(),'matching_credit':0}
 (out/'caller-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
def links():
 where=out/'links';where.mkdir(exist_ok=True);reports=[]
 files={'raw':out/'qualified-source/candidate.o','retail':out/'image-qualification/retail.o','padded':out/'image-qualification/qualified-owner/game_14FF90.c.o'}
 parsed=parse_object(files['raw']);assembly,missing=emit_function(parsed[0],parsed[1]['func_151277B0'],parsed[2],'func_151277B0',g.SYMS);assert not missing,missing
 isolated=where/'raw-target.o';asm=where/'raw-target.s';asm.write_text(assembly)
 subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(isolated),str(asm)],capture_output=True,check=True)
 assert payload(isolated,'func_151277B0')==payload(files['raw'],'func_151277B0');files['raw']=isolated
 for code_delta,data_delta in((0,0),(0x10010,0x18020)):
  bind={name:address+(data_delta if address&0x80000000 else code_delta)for name,address in g.SYMS.items()}
  for label,obj in files.items():
   expected=bound_blob(*payload(files['raw'if label=='raw'else'retail'],'func_151277B0'),bind)
   prefix=where/(label+'-'+str(code_delta));script=prefix.with_suffix('.ld');elf=prefix.with_suffix('.elf')
   script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x81000000 : { *(.rodata*) } .bss : { *(.bss*) } }\n'%(0x15122C5C+code_delta))
   undefined=subprocess.check_output(['mips-linux-gnu-nm','-u',str(obj)],text=True).splitlines();definitions={}
   anchored=load_symbol_addrs(str(root/'conker/symbol_addrs.us.txt'));anchored.update({n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n})
   for line in undefined:
    n=line.split()[-1]
    if n in bind:definitions[n]=bind[n]
    elif n in anchored:definitions[n]=anchored[n]+(data_delta if anchored[n]&0x80000000 else code_delta)
    elif n.startswith(('D_','func_')):
     value=int(n.split('_')[1],16);definitions[n]=value+(data_delta if value&0x80000000 else code_delta)
    else:raise AssertionError(('unqualified undefined symbol',n))
   q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_151277B0',*['--defsym=%s=0x%X'%v for v in definitions.items()],'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   functions,_,_=load_elf_functions(elf,'mips-linux-gnu-objdump');assert tuple(functions['func_151277B0'][:124])==tuple(expected),(label,code_delta)
   reports.append({'stream':label,'code_delta':code_delta,'data_delta':data_delta,'words':124,'GNU_equals_independent_binding':True})
 r={'links':reports,'HI16_LO16_carry_exercised':True,'raw_scope':'Exact isolated raw payload and bindings; raw code intentionally differs in GPR allocation, qualified separately by symbolic proof.',
  'source_installed':packet.installed(),'matching_credit':0}
 (out/'GNU-links.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':caller_checks();links()
