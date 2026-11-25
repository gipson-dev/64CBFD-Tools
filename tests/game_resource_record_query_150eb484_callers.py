"""Pin data/call census and execute original ABI forwarding and bounded parent."""
from pathlib import Path
from dataclasses import replace
import hashlib,itertools,json,re,struct,sys
sys.path.insert(0,str(Path.cwd()));from tools.experiments import game_resource_record_query_150eb484_match as packet
o=packet.OUT;sys.path.insert(0,str(o))
from tools.tests import game_resource_record_query_150eb484_guest as g
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
r=packet.ROOT;rom=(r/'conker/conker.us.bin').read_bytes();b=o/'baseline'
def pin():
 table=rom[0x22d560:0x22d594];assert len(table)==52 and struct.unpack('>13I',table)==(*g.tables,0x437f0000)
 for elf in (b/'conker/build/conker.us.elf',r/'conker/build/conker.us.elf'):
  blob=elf.read_bytes();at=elf_slot_offset(blob,0x80088aa0,52);assert blob[at:at+52]==table
 owner=(b/'conker/asm/AEB40.s').read_text();part=owner.split('glabel func_15081E78\n',1)[1].split('endlabel func_15081E78',1)[0];rows=re.findall(r'/\* ([0-9A-F]+) ([0-9A-F]+) ([0-9A-F]{8}) \*/',part);blob=bytes.fromhex(''.join(w for _,_,w in rows));assert blob==rom[0xaf328:0xaf328+len(blob)]
 (o/'original-parent.s').write_text(part);literal={}
 for fn in ('func_150EB430','func_150EB484','func_150A34B0','func_150A3504','func_150EBC80'):
  val=int(fn[5:],16);literal[fn]=[hex(i*4)for i,(w,)in enumerate(struct.iter_unpack('>I',rom))if w==val]
 q=dict(table_ASM_ROM_frozen_live_ELF_equal=True,table_bytes=52,secondary_end_is_float_scalar_at_AB0_plus_32=True,aligned_literal_pointer_patterns_ROM=literal,parent='func_15081E78',parent_words=len(rows),parent_ROM='AF328..AFA70',parent_sha256=hashlib.sha256(blob).hexdigest(),target_parent_call='15081FEC',parent_three_stack_vector_arguments=['SP+374','SP+368','SP+380'],return_overwritten_by_minus_one_at='15081FF8',wrapper_return_kept_void=True,no_other_aligned_JAL_callers=True,source_installed=packet.installed(),matching_credit=0)
 (o/'census.json').write_text(json.dumps(q,indent=2)+'\n');return {int(va,16):int(w,16)for _,va,w in rows},q
class Gate(g.Machine):
 def __init__(self,words,c,disabled,flags):
  super().__init__(words,c,entry=0x150a34b0,arguments=(g.A,*g.args(c)));self.memory[g.A+20]=disabled;self.memory[g.A+21]=flags
 def record_call(self,t):
  assert t==0x150a3504;self.calls.append((t,tuple(self.arguments(4))))
 def hook(self,t):
  a=self.calls[-1][1]
  for i in range(3):g.put(self.memory,a[3]+4*i,0x41000000+i*0x800000)
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
  self.r[2]=self.c.result
class Sum(g.Machine):
 def __init__(self,words,c):super().__init__(words,c,entry=0x150eb430)
 def record_call(self,t):
  assert t==g.ENTRY;a=tuple(self.arguments(3));self.calls.append((t,a));self.observations.append((g.vector(self.memory,a[0]),g.vector(self.memory,a[1]),a[2]));assert a==(g.args(self.c)[0],g.STACK+self.c.phase-12,g.args(self.c)[2])
 def hook(self,t):
  for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
  for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
  self.r[2]=0xfedcba98
PARENT,WINDOW,END,EPILOGUE,ACTOR=0x15081e78,0x15081f60,0x15081ffc,0x150825ac,0x70000
class Connected(g.Machine):
 def __init__(self,leaf,c,parent):
  memory=g.fixture(c);memory.update({g.STACK+c.phase+i:(i*17+165)&255 for i in range(-1200,-512)})
  memory.update({ACTOR+i:0x5a for i in range(128)})
  for off,v in ((8,0x41200000),(12,0x41a00000),(16,0x41f00000),(56,0x3f800000),(60,0x40000000),(64,0x40800000)):g.put(memory,ACTOR+off,v)
  super().__init__(leaf,c,arguments=(g.CTX,ACTOR,2),memory=memory);self.parent_frame=g.STACK+c.phase-944;self.child_args=[];self.code.update(parent);self.code=WindowCode(self.code,self);self.entry=PARENT;self.code.ends=(PARENT+24,)
  try:self.run();raise AssertionError('Missing prologue boundary')
  except WindowBoundary:pass
  assert self.r[29]==self.parent_frame;self.entry=WINDOW;self.code.ends=(END,)
 def record_call(self,t):
  if t==g.ENTRY:
   a=tuple(self.arguments(3));self.child_args.append(a);self.child_initial=dict(self.memory);self.expected=g.reference(self.memory,self.c,a)
  else:super().record_call(t)
 def finish(self):
  try:self.run();raise AssertionError('Missing parent window boundary')
  except WindowBoundary:pass
  assert self.child_args==[(self.parent_frame+0x374,self.parent_frame+0x368,self.parent_frame+0x380)]
  wanted,answer,calls,obs=self.expected
  external=lambda m:{a:v for a,v in m.items()if not self.parent_frame-80<=a<self.parent_frame}
  assert external(self.memory)==external(wanted)and self.calls==calls and self.observations==obs
  assert self.r[2]==0xffffffff,'caller must overwrite target return'
  self.window_memory=dict(self.memory);self.entry=EPILOGUE;self.code.ends=();self.run();return self
def main():
 parent,census=pin();gate_raw=g.bound_blob(*g.payload(o/'selected-CDE80.o','func_150A34B0'),dict(func_150A3504=0x150a3504));gate_truth=g.bound_blob(*g.payload(o/'func_150A34B0-original.o','func_150A34B0'),dict(func_150A3504=0x150a3504));assert gate_raw==gate_truth;gate_count=0
 for disabled,flags,result in itertools.product((0,1,2,255),range(256),(1,0x80000000)):
  c=g.Case(result=result);models=[Gate(w,c,disabled,flags).run()for w in (gate_truth,gate_raw)];a,z=models;assert g.state(a)==g.state(z);allowed=disabled!=1 and flags&3==0;assert a.r[2]==(result if allowed else 0)and a.calls==([(0x150a3504,(g.A,*g.args(c)))]if allowed else []);gate_count+=1
 sums=[g.bound_blob(*g.payload(o/f,'func_150EB430'),dict(func_150EB484=g.ENTRY))for f in ('func_150EB430-original.o','selected-1188E0.o')];assert sums[0]==sums[1];sum_count=0
 for alias,phase in itertools.product(range(5),(0,8)):
  c=g.Case(alias=alias,phase=phase);models=[Sum(w,c).run()for w in sums];a,z=models;assert g.state(a)==g.state(z);assert a.observations==[((0x3f800000,0x40000000,0x40800000),(0x40000000,0x40800000,0x41000000),g.args(c)[2])];sum_count+=1
 leaves=[g.bound_blob(*g.payload(o/f,'func_150EB484'),g.symbols)for f in ('original-target.o','selected-1188E0.o')];count=0
 for ctx,hit,mutation,phase in itertools.product((0,1),(-1,0,3,4,11),range(8),(0,8)):
  c=g.Case(context=ctx,hit=hit,mutation=mutation,phase=phase);a,z=[Connected(w,c,parent).finish()for w in leaves];external=lambda m:{p:v for p,v in m.memory.items()if not m.parent_frame-80<=p<m.parent_frame};assert external(a)==external(z)and a.calls==z.calls and a.observations==z.observations;count+=1
 q=dict(gate_cases_per_stream=gate_count,gate_streams=2,all_disabled_and_flag_byte_values=True,sum_cases_per_stream=sum_count,sum_complete_21_word_original_and_C=True,parent_cases_per_stream=count,parent_streams=2,bounded_parent_prologue_words=6,bounded_parent_window='15081F60..15081FFC',separate_original_epilogue_words=5,parent_return_overwrite_and_three_stack_vector_arguments=True,parent_full_body_only_pinned_not_qualified=True,raw_child_private_stack_excluded_with_explicit_80_byte_scope=True,geometry_and_effect_provider_contracts_only=True,source_installed=packet.installed(),matching_credit=0)
 (o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(dict(census=census,**q)),flush=True)
 return q
if __name__=='__main__':main()
