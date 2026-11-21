from pathlib import Path
import json,struct,subprocess,sys
from tools.experiments import game_owner_two_effect_1514f194_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_owner_two_effect_1514f194_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions,load_symbol_addrs
from tools.pad_generated_object import parse_object
from tools.experiments.alternative_source_draft_word_screen import emit_function
ENTRY=g.ENTRY
def caller_checks():
 census=json.loads((out/'caller-census.json').read_text());assert [r['entry']for r in census['direct_original_calls']]==[0x1514DBA0,0x1514F118]and not census['aligned_loaded_pointer_literals']
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();streams=g.programs();reports=[];controls=[]
 expected_wrapper=[0x27BDFFE8,0xAFBF0014,0x0D453C65,0,0x8FBF0014,0x27BD0018,0x03E00008,0]
 for entry in(0x1514DB98,0x1514F110):
  wrapper=list(struct.unpack_from('>8I',rom,entry-0x15000000+0x2D4B0));assert wrapper==expected_wrapper
  at=elf_slot_offset(elf,entry,32);assert elf[at:at+32]==struct.pack('>8I',*wrapper)
  class Connected(g.Machine):
   def __init__(self,words,c,m,opening=wrapper):
    self.c=c;self.observations=[];self.factories=0;self.target_entries=[]
    code=dict(zip(range(ENTRY,ENTRY+g.SIZE,4),words))
    FactoryOracle.__init__(self,opening,m,c,entry=entry,s=g.SYMS,arguments=(g.owner(c),),connected=code)
   def record_call(self,t):
    if t==ENTRY:self.target_entries.append(tuple(self.arguments(1)));self.events.append(('TARGET',t,self.target_entries[-1]))
    else:super().record_call(t)
  cases=[c for c in g.corpus()if c.gate in(0,1,255)and c.mutation_step in(0,1,2,3)and c.alias<3]
  for c in cases:
   initial=g.fixture(c);expected=g.reference(initial,c);states=[]
   for words in streams:
    m=Connected(words,c,dict(initial)).run()
    assert(g.public(m.memory),m.calls,m.observations)==expected,c
    assert m.target_entries==[(g.owner(c),)]and m.r[29]==g.STACK+c.phase
    for reg in(*range(16,24),30):assert m.r[reg]==m.before[reg]
    states.append(g.state(m))
   assert states[0]==states[1]==states[2]
  c=g.Case();initial=g.fixture(c);expected=g.reference(initial,c)
  for label,index,value in(('skipped-target',2,0),('wrong-owner-delay',3,0x24840004)):
   altered=list(wrapper);altered[index]=value;m=Connected(streams[0],c,dict(initial),altered).run()
   assert(g.public(m.memory),m.calls,m.observations)!=expected or m.target_entries!=[(g.owner(c),)],label
   controls.append((hex(entry),label))
  reports.append({'entry':hex(entry),'complete_wrapper_words':8,'cases_per_stream':len(cases),'current_equals_original':True})
 r={'wrappers':reports,'streams':3,'effective_controls':controls,'complete_wrapper_execution':True,
 'scope':'Both original/current complete 8-word wrappers, target and bounded helper contracts. Wider callers, helper implementation and gameplay are not claimed.',
 'source_installed':packet.installed(),'matching_credit':0}
 (out/'caller-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
def links():
 where=out/'links';where.mkdir(exist_ok=True);reports=[]
 files={'raw':out/'qualified-source/candidate.o','retail':out/'image-qualification/retail.o','padded':out/'image-qualification/qualified-owner/generated_179F30.c.o'}
 parsed=parse_object(files['raw']);assembly,missing=emit_function(parsed[0],parsed[1]['func_1514F194'],parsed[2],'func_1514F194',g.SYMS);assert not missing,missing
 isolated=where/'raw-target.o';asm=where/'raw-target.s';asm.write_text(assembly)
 subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(isolated),str(asm)],capture_output=True,check=True)
 assert payload(isolated,'func_1514F194')==payload(files['raw'],'func_1514F194');files['raw']=isolated
 anchored=load_symbol_addrs(str(root/'conker/symbol_addrs.us.txt'));anchored.update({n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n})
 for code_delta,data_delta in((0,0),(0x10010,0x18020)):
  bind={n:a+(data_delta if a&0x80000000 else code_delta)for n,a in g.SYMS.items()};expected=bound_blob(*payload(files['retail'],'func_1514F194'),bind)
  for label,obj in files.items():
   prefix=where/(label+'-'+str(code_delta));script=prefix.with_suffix('.ld');elf=prefix.with_suffix('.elf');base=(0x1514CA80 if label=='padded'else ENTRY)+code_delta
   script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x81000000 : { *(.rodata*) } .bss : { *(.bss*) } }\n'%base)
   definitions={}
   for line in subprocess.check_output(['mips-linux-gnu-nm','-u',str(obj)],text=True).splitlines():
    n=line.split()[-1]
    if n in bind:definitions[n]=bind[n]
    elif n in anchored:definitions[n]=anchored[n]+(data_delta if anchored[n]&0x80000000 else code_delta)
    elif n.startswith(('D_','func_')):
     a=int(n.split('_')[1],16);definitions[n]=a+(data_delta if a&0x80000000 else code_delta)
    else:raise AssertionError(('unqualified undefined',n))
   q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_1514F194',*['--defsym=%s=0x%X'%v for v in definitions.items()],'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   syms={n:r[1]for _,n,r,_ in symbol_rows(elf.read_bytes())if n};assert syms['func_1514F194']==ENTRY+code_delta
   if label=='padded':assert syms['func_1514EC1C']==g.ATTACH+code_delta
   functions,_,_=load_elf_functions(elf,'mips-linux-gnu-objdump');assert tuple(functions['func_1514F194'][:93])==tuple(expected),(label,code_delta)
   reports.append({'stream':label,'code_delta':code_delta,'data_delta':data_delta,'words':93,'GNU_equals_independent_binding':True})
 kinds={k for rows in payload(files['raw'],'func_1514F194')[1].values()for k,n in rows};assert kinds=={'R_MIPS_26','R_MIPS_HI16','R_MIPS_LO16'}
 r={'links':reports,'target_relocation_kinds':sorted(kinds),'HI16_LO16_carry_exercised':True,'raw_scope':'Exact isolated target and all code/data bindings. Padded-owner internal attach helper is verified at its rebased address.','source_installed':packet.installed(),'matching_credit':0}
 (out/'GNU-links.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':caller_checks();links()
