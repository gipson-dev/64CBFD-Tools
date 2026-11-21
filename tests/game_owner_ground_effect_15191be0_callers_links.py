from pathlib import Path
from dataclasses import replace
import itertools,json,struct,subprocess,sys
from tools.experiments import game_owner_ground_effect_15191be0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_owner_ground_effect_15191be0_guest as g
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.match_progress import load_elf_functions,load_symbol_addrs
from tools.pad_generated_object import parse_object
from tools.experiments.alternative_source_draft_word_screen import emit_function
ENTRY=g.ENTRY;CALLER=0x151925C4
def caller_checks():
 census=json.loads((out/'caller-census.json').read_text());assert [r['entry']for r in census['direct_original_calls']]==[0x1519275C]and not census['aligned_loaded_pointer_literals']
 rom=(root/'conker/conker.us.bin').read_bytes();elf=(out/'baseline/conker/build/conker.us.elf').read_bytes();streams=g.programs()
 opening=list(struct.unpack_from('>110I',rom,0x1BFA74));table={}
 for name,(address,data)in sections(out/'baseline/conker/build/conker.us.elf').items():
  if address<=0x800A8030 and address+len(data)>0x800A8160:table.update({p:data[p-address] for p in range(0x800A8030,0x800A8160)})
 assert table
 def arguments(m,kind,life,priority,context):
  if kind<17:
   label=g.read(m,0x800A811C+4*kind);index={0x1519264C:0,0x15192654:1,0x15192664:3,0x15192668:-1}[label]
  else:index={88:2,121:3}.get(kind,-1)
  if index<0:return None
  w=lambda p:g.read(m,p+4*index)
  return tuple(map(g.u32,(g.OWNER,0x800A8030+12*index,m[0x800A8060+index],w(0x800A8064),w(0x800A8074),g.s16(life),w(0x800A8084),w(0x800A8094),g.s16(g.read(m,0x800A80A4+2*index,2)),g.s16(g.read(m,0x800A80AC+2*index,2)),100,155,w(0x800A80B4),w(0x800A80C4),w(0x800A80D4),m[0x800A80E4+index],priority&255,context)))
 class Connected(g.Machine):
  def __init__(self,words,c,m,kind,life,priority,context,opening=opening):
   self.c=c;self.observations=[];self.expected=None;self.target_entries=[]
   self.expected_arguments=None if c.null else arguments(m,kind,life,priority,context)
   code=dict(zip(range(ENTRY,ENTRY+g.SIZE,4),words))
   FactoryOracle.__init__(self,opening,m,c,entry=CALLER,s=g.SYMS,arguments=(0 if c.null else g.OWNER,life,priority,context),connected=code)
   self.target_home=g.STACK+c.phase-80
  def record_call(self,t):
   if t==ENTRY:
    a=tuple(self.arguments(18));assert a==self.expected_arguments,('caller arguments',a,self.expected_arguments)
    self.target_entries.append(a);self.events.append(('TARGET',t,a));self.expected=g.reference(dict(self.memory),self.c,arguments=a,home=self.r[29])
   else:super().record_call(t)
 cases=0;coverage=set()
 for kind,setting,outcome,mutation,phase,null in itertools.product(range(256),(0,1),(0,1),(0,4),(0,8),(0,1)):
  c=g.Case(seed=kind,outcome=outcome,mutation=mutation,phase=phase,null=null);initial=g.fixture(c);initial.update(table);initial[g.OWNER+4]=kind
  life=(-1,0xABCD8001)[setting];priority=(0xABCDFF80,255)[setting];context=0x13579BDF;states=[]
  for words in streams:
   m=Connected(words,c,dict(initial),kind,life,priority,context).run()
   expected=m.expected if m.expected is not None else(g.public(initial),[],0,[])
   assert(g.public(m.memory),m.calls,m.r[2],m.observations)==expected,(kind,setting,outcome)
   assert len(m.target_entries)==int(m.expected_arguments is not None)
   assert m.r[29]==g.STACK+phase
   for reg in(*range(16,24),30):assert m.r[reg]==m.before[reg]
   coverage.update((p-CALLER)//4 for p in m.visits if CALLER<=p<CALLER+440);states.append(g.state(m))
  assert states[0]==states[1]==states[2];cases+=1
 controls=[]
 for label,index,value in (('skipped-target',(0x1519275C-CALLER)//4,0),('wrong-priority-delay',(0x15192760-CALLER)//4,0xAFA00040)):
  kind=88;c=g.Case();initial=g.fixture(c);initial.update(table);initial[g.OWNER+4]=kind;altered=list(opening);altered[index]=value
  try:
   m=Connected(streams[0],c,initial,kind,-1,255,0x13579BDF,altered).run()
   rejected=m.target_entries!=[m.expected_arguments]
  except AssertionError:rejected=True
  assert rejected,label;controls.append(label)
 at=elf_slot_offset(elf,CALLER,440)
 r={'complete_retail_caller_words':110,'cases_per_stream':cases,'streams':3,'covered_caller_words':len(coverage),'unvisited_caller_words':sorted(set(range(110))-coverage),'current_caller_equals_original':elf[at:at+440]==struct.pack('>110I',*opening),'all_18_arguments_checked_against_retail_tables':True,'effective_controls':controls,'scope':'Complete retail caller, all 256 type values and immutable GameData tables. The current caller is still an unchanged placeholder; this is original ABI evidence, not recovered caller credit. Surface/factory/copy use the separately stated contracts.','source_installed':packet.installed(),'matching_credit':0}
 (out/'caller-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
def links():
 where=out/'links';where.mkdir(exist_ok=True);reports=[]
 files={'raw':out/'qualified-source/candidate.o','retail':out/'image-qualification/retail.o','padded':out/'image-qualification/qualified-owner/generated_1BF090.c.o'}
 parsed=parse_object(files['raw']);assembly,missing=emit_function(parsed[0],parsed[1]['func_15191BE0'],parsed[2],'func_15191BE0',g.SYMS);assert not missing,missing
 isolated=where/'raw-target.o';asm=where/'raw-target.s';asm.write_text(assembly)
 subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(isolated),str(asm)],capture_output=True,check=True)
 assert payload(isolated,'func_15191BE0')==payload(files['raw'],'func_15191BE0');files['raw']=isolated
 anchored=load_symbol_addrs(str(root/'conker/symbol_addrs.us.txt'));anchored.update({n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n})
 for code_delta in(0,0x10010):
  bind={n:a+code_delta for n,a in g.SYMS.items()};expected=bound_blob(*payload(files['retail'],'func_15191BE0'),bind)
  for label,obj in files.items():
   prefix=where/(label+'-'+str(code_delta));script=prefix.with_suffix('.ld');elf=prefix.with_suffix('.elf')
   script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x81000000 : { *(.rodata*) } .bss : { *(.bss*) } }\n'%(ENTRY+code_delta))
   definitions={}
   for line in subprocess.check_output(['mips-linux-gnu-nm','-u',str(obj)],text=True).splitlines():
    n=line.split()[-1]
    if n in bind:definitions[n]=bind[n]
    elif n in anchored:definitions[n]=anchored[n]+(0x18020 if anchored[n]&0x80000000 else code_delta)
    else:raise AssertionError(('unqualified undefined',n))
   q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_15191BE0',*['--defsym=%s=0x%X'%v for v in definitions.items()],'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   syms={n:r[1]for _,n,r,_ in symbol_rows(elf.read_bytes())if n};assert syms['func_15191BE0']==ENTRY+code_delta
   functions,_,_=load_elf_functions(elf,'mips-linux-gnu-objdump');assert tuple(functions['func_15191BE0'][:93])==tuple(expected),(label,code_delta)
   reports.append({'stream':label,'code_delta':code_delta,'words':93,'GNU_equals_independent_binding':True})
 kinds={k for rows in payload(files['raw'],'func_15191BE0')[1].values()for k,n in rows};assert kinds=={'R_MIPS_26'}
 r={'links':reports,'target_relocation_kinds':sorted(kinds),'scope':'Three exact call bindings at two code bases. The target has no HI16/LO16 relocations.','source_installed':packet.installed(),'matching_credit':0}
 (out/'GNU-links.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
if __name__=='__main__':caller_checks();links()
