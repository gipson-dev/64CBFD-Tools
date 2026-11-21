from pathlib import Path
import json,struct,subprocess,sys
from tools.experiments import game_camera_origin_shift_15097798_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_camera_origin_shift_15097798_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions,load_symbol_addrs
from tools.pad_generated_object import parse_object
from tools.experiments.alternative_source_draft_word_screen import emit_function
ENTRY=g.ENTRY
NEXT,CALLER=0x15125A6C,0x70000
def caller_checks():
 census=json.loads((out/'caller-census.json').read_text());assert [r['entry']for r in census['direct_original_calls']]==[0x15122E74]and not census['aligned_loaded_pointer_literals']
 start=0x15122E74;end=start+16;rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes()
 opening=list(struct.unpack_from('>4I',rom,start-0x15000000+0x2D4B0));assert opening==[0x0D425DE6,0x9204023D,0x0D44969B,0x02002025]
 at=elf_slot_offset(elf,start,16);current_equal=elf[at:at+16]==struct.pack('>4I',*opening);streams=g.programs()
 def fixture(c):
  m=g.fixture(c);m.update({CALLER+i:0x35 for i in range(0x300)});m[CALLER+0x23D]=c.view;m[CALLER+0x23E]=(c.view+1)&255;return m
 class Connected(g.Machine):
  def __init__(self,words,c,m,window=opening):
   self.c=c;self.sqrt_visits=set();self.target_entries=[]
   code=dict(zip(range(ENTRY,ENTRY+g.SIZE,4),words));code[end]=0
   FactoryOracle.__init__(self,window,m,c,entry=start,s=g.SYMS,arguments=(0x12345678,),connected=code)
   self.r[16]=CALLER;self.r[17]=g.OTHER;self.before=self.r[:];self.code=WindowCode(self.code,self);self.code.ends=(end,)
  def record_call(self,t):
   if t==ENTRY:self.target_entries.append(tuple(self.arguments(1)));self.events.append(('TARGET',t,self.target_entries[-1]))
   elif t==NEXT:
    a=tuple(self.arguments(1));self.calls.append((t,a));self.events.append(('CALL',t,a))
   else:super().record_call(t)
  def hook(self,t):
   if t!=NEXT:return super().hook(t)
   a=self.calls[-1][1][0];g.put(self.memory,a+0x18,0x12345678)
   for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
   for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
   self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
 cases=[c for c in g.corpus()if 0<=c.view<=255 and c.alias==0 and c.pattern in(0,1,3)and c.mutation in(0,1,2,4,7)]
 for c in cases:
  initial=fixture(c);expected,calls,coords=g.reference(initial,c);g.put(expected,CALLER+0x18,0x12345678);calls=calls+[(NEXT,(CALLER,))];states=[]
  for words in streams:
   m=Connected(words,c,dict(initial))
   try:m.run();raise AssertionError('missing caller boundary')
   except WindowBoundary:pass
   assert(g.public(m.memory),m.calls,g.coordinates(m.memory,g.selected(c)))==(expected,calls,coords),c
   assert m.target_entries==[(c.view,)]and m.r[29]==g.STACK+c.phase and m.r[16]==CALLER and m.r[17]==g.OTHER
   states.append(g.state(m))
  assert states[0]==states[1]==states[2]
 controls=[];c=g.Case();initial=fixture(c);expected,calls,coords=g.reference(initial,c);g.put(expected,CALLER+0x18,0x12345678);calls=calls+[(NEXT,(CALLER,))]
 for label,index,value in(('skipped-target',0,0),('wrong-view-byte',1,0x9204023E),('wrong-next-delay',3,0x02202025)):
  altered=list(opening);altered[index]=value;m=Connected(streams[0],c,dict(initial),altered)
  try:m.run();raise AssertionError('missing caller boundary')
  except WindowBoundary:pass
  assert(g.public(m.memory),m.calls,g.coordinates(m.memory,g.selected(c)))!=(expected,calls,coords)or m.target_entries!=[(c.view,)],label
  controls.append(label)
 r={'parent':'func_15122C5C','original_window':hex(start),'window_words':4,'cases_per_stream':len(cases),'streams':3,'current_window_equals_original':current_equal,'effective_controls':controls,
 'scope':'Original ROM window, real LBU view delay and following S0 camera delay with bounded next-helper effect. Parent remains unfinished; no complete current-parent, next-helper, hardware or gameplay claim.','source_installed':packet.installed(),'matching_credit':0}
 (out/'caller-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
def links():
 where=out/'links';where.mkdir(exist_ok=True);reports=[]
 files={'raw':out/'qualified-source/candidate.o','retail':out/'image-qualification/retail.o','padded':out/'image-qualification/qualified-owner/generated_C3E20.c.o'}
 parsed=parse_object(files['raw']);assembly,missing=emit_function(parsed[0],parsed[1]['func_15097798'],parsed[2],'func_15097798',g.SYMS);assert not missing,missing
 isolated=where/'raw-target.o';asm=where/'raw-target.s';asm.write_text(assembly)
 subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(isolated),str(asm)],capture_output=True,check=True)
 assert payload(isolated,'func_15097798')==payload(files['raw'],'func_15097798');files['raw']=isolated
 anchored=load_symbol_addrs(str(root/'conker/symbol_addrs.us.txt'));anchored.update({n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n})
 for code_delta,data_delta in((0,0),(0x10010,0x18020)):
  bind={n:a+(data_delta if a&0x80000000 else code_delta)for n,a in g.SYMS.items()};expected=bound_blob(*payload(files['retail'],'func_15097798'),bind)
  for label,obj in files.items():
   prefix=where/(label+'-'+str(code_delta));script=prefix.with_suffix('.ld');elf=prefix.with_suffix('.elf');base=(0x15096970 if label=='padded'else ENTRY)+code_delta
   script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x81000000 : { *(.rodata*) } .bss : { *(.bss*) } }\n'%base)
   definitions={}
   for line in subprocess.check_output(['mips-linux-gnu-nm','-u',str(obj)],text=True).splitlines():
    n=line.split()[-1]
    if n in bind:definitions[n]=bind[n]
    elif n in anchored:definitions[n]=anchored[n]+(data_delta if anchored[n]&0x80000000 else code_delta)
    elif n.startswith(('D_','func_')):
     a=int(n.split('_')[1],16);definitions[n]=a+(data_delta if a&0x80000000 else code_delta)
    else:raise AssertionError(('unqualified undefined',n))
   q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_15097798',*['--defsym=%s=0x%X'%v for v in definitions.items()],'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   syms={n:r[1]for _,n,r,_ in symbol_rows(elf.read_bytes())if n};assert syms['func_15097798']==ENTRY+code_delta
   functions,_,_=load_elf_functions(elf,'mips-linux-gnu-objdump');assert tuple(functions['func_15097798'][:93])==tuple(expected),(label,code_delta)
   reports.append({'stream':label,'code_delta':code_delta,'data_delta':data_delta,'words':93,'GNU_equals_independent_binding':True})
 kinds={k for rows in payload(files['raw'],'func_15097798')[1].values()for k,n in rows};assert kinds=={'R_MIPS_26','R_MIPS_HI16','R_MIPS_LO16'}
 r={'links':reports,'target_relocation_kinds':sorted(kinds),'HI16_LO16_carry_exercised':True,'raw_scope':'Exact isolated target and all code/data bindings. All target code/data bindings are checked; unrelated raw-owner data is outside this scope.','source_installed':packet.installed(),'matching_credit':0}
 (out/'GNU-links.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))

if __name__=='__main__':caller_checks();links()
