from pathlib import Path
from dataclasses import replace
import itertools,json,re,struct,subprocess,sys
from tools.experiments import game_camera_query_1509759c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_camera_query_1509759c_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions,load_symbol_addrs
from tools.pad_generated_object import parse_object
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
ENTRY=g.ENTRY
CALLER,COUNT,PARAMETERS,DISPATCH=0x1509BE40,0x800D3840,0x800D2F60,0x80088498

def caller_checks():
 census=json.loads((out/'caller-census.json').read_text());assert not census['direct_original_calls']
 assert[(r['section'],r['address'])for r in census['aligned_loaded_pointer_literals']]==[('.game_data',DISPATCH+8*4)]
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();original=rom[0xC92F0:0xC9460];assert len(original)==92*4
 at=elf_slot_offset(elf,CALLER,len(original));assert elf[at:at+len(original)]==original
 caller_words=list(struct.unpack('>92I',original));streams=g.programs()
 class Connected(g.Machine):
  def __init__(self,words,c,m,count,caller=caller_words):
   self.c=c;self.sqrt_visits=set();self.trunc_visits=set();self.target_entries=[]
   code=dict(zip(range(ENTRY,ENTRY+g.SIZE,4),words));code.update(g.helper_code())
   args=(count,0x9000|c.view,c.command,c.key,*[0x12340000+i for i in range(1,count)])
   FactoryOracle.__init__(self,caller,m,c,entry=CALLER,s=g.SYMS,arguments=args,connected=code)
  def record_call(self,t):
   if t==ENTRY:self.target_entries.append(tuple(self.arguments(3)));self.events.append(('TARGET',t,self.target_entries[-1]))
   else:super().record_call(t)
 def initial(c):
  m=g.fixture(c);g.put(m,COUNT,0x12345678)
  for i in range(20):g.put(m,DISPATCH+4*i,0)
  g.put(m,DISPATCH+8*4,ENTRY);return m
 def expected(c,n,m):
  m=dict(m);g.put(m,PARAMETERS,c.view);g.put(m,PARAMETERS+4,c.command)
  for i in range(n):g.put(m,PARAMETERS+8+4*i,c.key if i==0 else 0x12340000+i)
  g.put(m,COUNT,n+2);result,calls,answer=g.reference(m,replace(c,phase=c.phase-48));result[COUNT]=0x12;result[COUNT+1]=0x34;result[COUNT+2]=0x56;result[COUNT+3]=0x78
  return result,calls,answer
 covered=set();counted=0
 cases=[]
 for n,command,pattern,view,mutation,phase in itertools.product((0,1,3,4,5,8),(29,30,31,32,33,34),(0,1,3),(0,3),(0,7,16,32,63),(0,8)):
  if n==0 and command in(29,32,33):continue
  cases.append((n,g.Case(view=view,command=command,pattern=pattern,mutation=mutation,phase=phase,params=PARAMETERS)))
 for n,c in cases:
  memory=initial(c);wanted=expected(c,n,memory);states=[]
  for words in streams:
   m=Connected(words,c,dict(memory),n).run();assert(g.public(m.memory),m.calls,m.r[2])==wanted,('caller',n,c,m.calls,wanted[1])
   assert m.target_entries==[(c.view,c.command,PARAMETERS)];states.append(g.state(m));covered|={p for p in m.visits if CALLER<=p<CALLER+368}
  assert states[0]==states[1]==states[2];counted+=1
 assert covered==set(range(CALLER,CALLER+368,4)),sorted(set(range(CALLER,CALLER+368,4))-covered)
 controls=[];c=g.Case(params=PARAMETERS);n=1;memory=initial(c);wanted=expected(c,n,memory)
 for label,address,replacement in(('skipped-query',0x1509BF90,0),('wrong-command-home',0x1509BF8C,0x8FA50034),('wrong-count-restore',0x1509BFA4,0xAC223840)):
  changed=caller_words[:];index=(address-CALLER)//4;assert changed[index]!=replacement;changed[index]=replacement
  m=Connected(streams[0],c,dict(memory),n,changed).run();assert(g.public(m.memory),m.calls,m.r[2])!=wanted,label;controls.append(label)
 r={'caller':'func_1509BE40','words':92,'current_complete_caller_equals_original':True,'dispatch_table':'0x80088498','provider_index':8,'provider_word':'0x800884B8','cases_per_stream':counted,'streams':3,'covered_caller_words':len(covered),'effective_controls':controls,
  'scope':'Complete original/current script-query caller connected through its actual indexed JALR, target and original delta/dot. Lookup and sin/cos remain explicit bounded contracts; no full script-engine/gameplay/hardware claim.','source_installed':packet.installed(),'matching_credit':0}
 (out/'caller-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)

def links():
 where=out/'links';where.mkdir(exist_ok=True);reports=[]
 files={'raw':out/'qualified-source/candidate.o','retail':out/'image-qualification/retail.o','padded':out/'image-qualification/qualified-owner/generated_C3E20.c.o'}
 raw_owner=files['raw'];parsed=parse_object(raw_owner)
 refs={at:[(kind,'jtbl_8009DF38_game'if name=='.rodata'else name)for kind,name in rows]for at,rows in parsed[2].items()}
 assembly,missing=emit_function(parsed[0],parsed[1]['func_1509759C'],refs,'func_1509759C',g.SYMS);assert not missing,missing
 isolated=where/'raw-target.o';asm=where/'raw-target.s';asm.write_text(assembly)
 subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(isolated),str(asm)],capture_output=True,check=True)
 blob,original_refs=payload(raw_owner,'func_1509759C');normalized={at:[(kind,'jtbl_8009DF38_game'if name=='.rodata'else name)for kind,name in rows]for at,rows in original_refs.items()}
 assert payload(isolated,'func_1509759C')==(blob,normalized);files['raw']=isolated
 anchored=load_symbol_addrs(str(root/'conker/symbol_addrs.us.txt'));anchored.update({n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n})
 for code_delta,data_delta in((0,0),(0x10010,0x18020)):
  bind={n:a+(data_delta if a&0x80000000 else code_delta)for n,a in g.SYMS.items()};expected=bound_blob(*payload(files['retail'],'func_1509759C'),bind)
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
   q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_1509759C',*['--defsym=%s=0x%X'%v for v in definitions.items()],'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   syms={n:r[1]for _,n,r,_ in symbol_rows(elf.read_bytes())if n};assert syms['func_1509759C']==ENTRY+code_delta
   functions,_,_=load_elf_functions(elf,'mips-linux-gnu-objdump');assert tuple(functions['func_1509759C'][:127])==tuple(expected),(label,code_delta)
   reports.append({'stream':label,'code_delta':code_delta,'data_delta':data_delta,'words':127,'GNU_equals_independent_binding':True})
  # Also link the untouched raw owner with its actual R_MIPS_32 table records.
  script=where/('raw-owner-'+str(code_delta)+'.ld');elf=script.with_suffix('.elf')
  base=ENTRY-parsed[1]['func_1509759C']['value']+code_delta
  script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x%X : SUBALIGN(4) { *(.rodata*) } .bss : { *(.bss*) } }\n'%(base,g.TABLE+data_delta))
  definitions={};unused=[];relocations=subprocess.check_output(['mips-linux-gnu-readelf','-Wr',str(raw_owner)],text=True)
  for line in subprocess.check_output(['mips-linux-gnu-nm','-u',str(raw_owner)],text=True).splitlines():
   n=line.split()[-1];a=g.SYMS.get(n,anchored.get(n))
   if a is None:
    assert not re.search(r'\b'+re.escape(n)+r'\b',relocations),('unbound relocation',n);unused.append(n);continue
   definitions[n]=a+(data_delta if a&0x80000000 else code_delta)
  q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_1509759C',*['--defsym=%s=0x%X'%v for v in definitions.items()],'-o',str(elf),str(raw_owner)],capture_output=True,text=True);assert q.returncode==0,q.stderr
  functions,_,_=load_elf_functions(elf,'mips-linux-gnu-objdump');assert tuple(functions['func_1509759C'][:127])==tuple(expected)
  table=sections(elf)['.rodata'];assert table[0]==g.TABLE+data_delta and tuple(struct.unpack_from('>5I',table[1]))==tuple(v+code_delta for v in g.TABLE_WORDS)
  assert table[1][20:]==bytes(12)
  reports.append({'stream':'complete-raw-owner-and-table','code_delta':code_delta,'data_delta':data_delta,'words':127,'table_R_MIPS_32_targets':5,'unreferenced_SDK_declarations':unused,'GNU_equals_independent_binding':True})
 kinds={k for rows in payload(files['raw'],'func_1509759C')[1].values()for k,n in rows};assert kinds=={'R_MIPS_26','R_MIPS_HI16','R_MIPS_LO16'}
 r={'links':reports,'target_relocation_kinds':sorted(kinds),'HI16_LO16_carry_exercised':True,'raw_scope':'Exact isolated target and complete raw-owner table links at both bases. All five R_MIPS_32 table targets are independently checked; the immutable production table is also checked by the image gate. Unrelated raw-owner function addresses are outside this compact-owner link scope.','source_installed':packet.installed(),'matching_credit':0}
 (out/'GNU-links.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='links':links()
 else:caller_checks();links()
