from pathlib import Path
from dataclasses import replace
import json,struct,subprocess,sys
from tools.experiments import game_timed_effect_update_15188b74_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_timed_effect_update_15188b74_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions,load_symbol_addrs
from tools.pad_generated_object import parse_object
from tools.experiments.alternative_source_draft_word_screen import emit_function
ENTRY=g.ENTRY
def caller_checks():
 census=json.loads((out/'caller-census.json').read_text());assert len(census['direct_original_calls'])==2 and not census['aligned_loaded_pointer_literals']
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();streams=g.programs();reports=[];rejected=[]
 for start,list_,delay in((0x150192CC,0,0x00002025),(0x1501931C,1,0x24040001)):
  end=start+8;window=list(struct.unpack_from('>2I',rom,start-0x15000000+0x2D4B0));assert window==[0x0D4622DD,delay]
  at=elf_slot_offset(elf,start,8);current_equal=elf[at:at+8]==struct.pack('>2I',*window)
  class Connected(g.Machine):
   def __init__(self,words,c,m,opening=window):
    self.c=c;code=dict(zip(range(ENTRY,ENTRY+g.SIZE,4),words));code[end]=0
    FactoryOracle.__init__(self,opening,m,c,entry=start,s=g.SYMS,arguments=(7,),connected=code)
    self.before=self.r[:];self.code=WindowCode(self.code,self);self.code.ends=(end,)
   def record_call(self,t):
    if t==ENTRY:
     a=tuple(self.arguments(1));self.calls.append((t,a));self.events.append(('CALL',t,a))
    else:super().record_call(t)
  cases=[replace(c,list=list_)for c in g.corpus()if c.opacity in(0,1,8,240,255)and c.delta in(0,1,2)]
  for c in cases:
   initial=g.fixture(c);expected,calls=g.reference(initial,c);expected_calls=[(ENTRY,(list_,))]+calls;states=[]
   for w in streams:
    m=Connected(w,c,dict(initial))
    try:m.run();raise AssertionError('missing caller boundary')
    except WindowBoundary:pass
    assert(g.public(m.memory),m.calls)==(expected,expected_calls),c
    assert m.r[29]==g.STACK+c.phase
    for reg in range(16,24):assert m.r[reg]==m.before[reg]
    states.append(g.state(m))
   assert states[0]==states[1]==states[2]
  c=g.Case(list=list_,count=1,timer=2);initial=g.fixture(c);expected,calls=g.reference(initial,c);expected_calls=[(ENTRY,(list_,))]+calls
  for label,index,value in(('skipped-target',0,0),('wrong-list-delay',1,0x24040000 if list_ else 0x24040001)):
   changed=list(window);changed[index]=value;m=Connected(streams[0],c,dict(initial),changed)
   try:m.run();raise AssertionError('missing caller boundary')
   except WindowBoundary:pass
   assert(g.public(m.memory),m.calls)!=(expected,expected_calls),label;rejected.append((hex(start),label))
  reports.append({'window':hex(start),'words':2,'list_argument':list_,'cases_per_stream':len(cases),'current_window_equals_original':current_equal})
 r={'parent':'func_15019130','windows':reports,'streams':3,'effective_controls':rejected,'whole_caller_claim':False,
 'scope':'Both original call windows and their current linked bytes, delay-slot list arguments 0/1, complete target and bounded callback contracts. No full caller or gameplay claim.',
 'source_installed':packet.installed(),'matching_credit':0}
 (out/'caller-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
def links():
 where=out/'links';where.mkdir(exist_ok=True);reports=[]
 files={'raw':out/'qualified-source/candidate.o','retail':out/'image-qualification/retail.o','padded':out/'image-qualification/qualified-owner/generated_1B5CC0.c.o'}
 parsed=parse_object(files['raw']);assembly,missing=emit_function(parsed[0],parsed[1]['func_15188B74'],parsed[2],'func_15188B74',g.SYMS);assert not missing,missing
 isolated=where/'raw-target.o';asm=where/'raw-target.s';asm.write_text(assembly)
 subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(isolated),str(asm)],capture_output=True,check=True)
 assert payload(isolated,'func_15188B74')==payload(files['raw'],'func_15188B74');files['raw']=isolated
 anchored=load_symbol_addrs(str(root/'conker/symbol_addrs.us.txt'));anchored.update({n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n})
 for code_delta,data_delta in((0,0),(0x10010,0x18020)):
  bind={n:a+(data_delta if a&0x80000000 else code_delta)for n,a in g.SYMS.items()};expected=bound_blob(*payload(files['retail'],'func_15188B74'),bind)
  for label,obj in files.items():
   prefix=where/(label+'-'+str(code_delta));script=prefix.with_suffix('.ld');elf=prefix.with_suffix('.elf');base=(0x15188810 if label=='padded'else ENTRY)+code_delta
   script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x81000000 : { *(.rodata*) } .bss : { *(.bss*) } }\n'%base)
   definitions={}
   for line in subprocess.check_output(['mips-linux-gnu-nm','-u',str(obj)],text=True).splitlines():
    n=line.split()[-1]
    if n in bind:definitions[n]=bind[n]
    elif n in anchored:definitions[n]=anchored[n]+(data_delta if anchored[n]&0x80000000 else code_delta)
    elif n.startswith(('D_','func_')):
     a=int(n.split('_')[1],16);definitions[n]=a+(data_delta if a&0x80000000 else code_delta)
    else:raise AssertionError(('unqualified undefined',n))
   q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_15188B74',*['--defsym=%s=0x%X'%v for v in definitions.items()],'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   syms={n:r[1]for _,n,r,_ in symbol_rows(elf.read_bytes())if n};assert syms['func_15188B74']==ENTRY+code_delta
   functions,_,_=load_elf_functions(elf,'mips-linux-gnu-objdump');assert tuple(functions['func_15188B74'][:99])==tuple(expected),(label,code_delta)
   reports.append({'stream':label,'code_delta':code_delta,'data_delta':data_delta,'words':99,'GNU_equals_independent_binding':True})
 kinds={k for rows in payload(files['raw'],'func_15188B74')[1].values()for k,n in rows};assert kinds=={'R_MIPS_26','R_MIPS_HI16','R_MIPS_LO16'}
 r={'links':reports,'target_relocation_kinds':sorted(kinds),'HI16_LO16_carry_exercised':True,'raw_scope':'Exact isolated target and all its data/code bindings; unused raw-owner data is outside this scope.','source_installed':packet.installed(),'matching_credit':0}
 (out/'GNU-links.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':
 caller_checks();links()
