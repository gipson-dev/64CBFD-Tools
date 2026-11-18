"""Inductive complete burst relation with literal identities and a closed byte-home map."""
from pathlib import Path
from collections import Counter
from copy import deepcopy
import json,struct
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments import game_burst_emitter_150b82d0_match as source
e=g.e;p=source.OUT;f=source.FROZEN;ENTRY,LOOP,POOL=0x150B82D0,0xA4,0x80400000
RNG,REAL,DIRECTION,SUBMIT=0x150ADA20,0x150ADA68,0x15143794,0x1518A3C0
LITERALS=(0xC4C44000,0x45444000,0x3C23D70A,0x4498A000,0x44E1C000,0x3A83126F,0x441E4000,0x3F7149E8)
VECTOR_BASES=(-16,-28,-40,-52)
def pairs(refs,words):
 pending=None;result=[]
 for at,rows in sorted(refs.items()):
  if rows[0][1]!='.rodata':continue
  assert len(rows)==1;kind=rows[0][0]
  if kind=='R_MIPS_HI16':assert pending is None;pending=at//4
  else:
   assert kind=='R_MIPS_LO16'and pending is not None
   lo=at//4;offset=words[lo]&65535;assert offset in range(40,72,4)
   assert words[pending]>>26==15 and words[pending]>>16&31==1 and words[lo]>>26==49 and words[lo]>>21&31==1
   assert words[pending]&65535==0 and 1<=lo-pending<=2
   result.append((pending,lo,offset));pending=None
 assert pending is None and len(result)==8 and{v[2]for v in result}==set(range(40,72,4));return result
PAIRS=[tuple(v) for v in source.PIN['literal_pairs']]
def derive(words,refs=None):
 assert len(words)==188;result=words[:];bindings={k:list(v)for k,v in(refs or{}).items()}
 for hi,lo,offset in PAIRS:
  identity=(offset-40)//4;address=0x8009FD68+4*identity;name='D_%08X'%address
  if refs is None:
   assert((words[hi]&65535)<<16)+(((words[lo]&65535)^32768)-32768)==POOL+offset
   result[hi]=(words[hi]&0xffff0000)|((address+32768)>>16&65535);result[lo]=(words[lo]&0xffff0000)|(address&65535)
  else:
   assert refs[4*hi]==[('R_MIPS_HI16','.rodata')]and refs[4*lo]==[('R_MIPS_LO16','.rodata')]
   result[lo]&=0xffff0000;bindings[4*hi]=[('R_MIPS_HI16',name)];bindings[4*lo]=[('R_MIPS_LO16',name)]
 homes=[]
 assert words[0]==0x27BDFF18 and words[-1]==0x27BD00E8
 result[0]+=8;result[-1]-=8
 for i,w in enumerate(words):
  op=w>>26;off=w&65535
  if op in(9,35,43,49,57)and w>>21&31==29 and not(op==9 and w>>16&31==29):
   if 0xb8<=off<0xe8:result[i]-=12;homes.append(i)
   elif 0xe8<=off<0x100:result[i]-=8;homes.append(i)
 for i in range(125,167):
  w=result[i];op,fmt=w>>26,w>>21&31
  shifts=(16,)if op in(49,57)else(11,)if op==17 and fmt in(0,4)else(11,6)if op==17 and fmt==16 and w&63 in(6,7,13)else(16,11,6)if op==17 and fmt==16 else()
  for shift in shifts:
   reg=w>>shift&31
   if reg in(20,22):w=(w&~(31<<shift))|((42-reg)<<shift)
  result[i]=w
 assert len(homes)==22,(len(homes),homes)
 return result if refs is None else(result,bindings)
def canonical(off,raw):
 if raw and -232<=off<-60:return off+8
 if raw and -60<=off<-52:raise AssertionError(('unused source-only gap accessed',off))
 if raw and -52<=off<-48:return off+48
 if raw and -48<=off<0:return off-4
 return off
class State(g.State):
 def __init__(self,raw,literals=LITERALS,remap=True):
  super().__init__('common');self.raw=raw;self.frame_bytes=232 if raw else 224;self.remap=raw and remap;self.literals=literals;self.mem={off:('PRIVATE_ENTRY',off)for off in range(-224,24)};self.exposed=set()
  self.r[4:8]=[('ARG',i)for i in range(4)];self.store(('STACK',16),4,('ARG',4));self.store(('STACK',20),4,('ARG',5))
 def address(self,v):return('STACK',canonical(v[1],self.remap))if e.tagged(v,'STACK')else v
 def at(self,off,size):
  physical=off
  if self.remap:
   if off<-52:physical=off-8
   elif off<-4:physical=off+4
   elif off<0:physical=off-48
  return self.load(('STACK',physical),size)
 def load(self,address,size,pool=b''):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0 and -self.frame_bytes<=off and off+size<=24
   return g.join([self.mem[canonical(off+i,self.remap)]for i in range(size)])
  if isinstance(address,int):
   start=POOL+40 if self.raw else 0x8009FD68
   if start<=address<start+32:
    assert size==4 and(address-start)%4==0;index=(address-start)//4;self.trace.append(('LITERAL',index,self.literals[index]));return self.literals[index]
  return super().load(address,size,pool)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0 and -self.frame_bytes<=off and off+size<=24
   for i in range(size):self.mem[canonical(off+i,self.remap)]=g.byte(value,8*(size-i-1))
  else:super().store(address,size,value)
 def value(self,v):
  if e.tagged(v,'STACK'):return self.address(v)
  return tuple(self.value(item)for item in v)if isinstance(v,tuple)else v
 def frame(self):return tuple(self.value(self.mem[i])for i in range(-224,24))
class Program(g.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
 def call(self,s,target):
  n={RNG:0,REAL:0,DIRECTION:4,SUBMIT:13}[target];assert s.r[29]==('STACK',-s.frame_bytes)
  args=tuple(s.r[4:4+min(n,4)])+tuple(s.load(('STACK',-s.frame_bytes+16+4*i),4)for i in range(max(0,n-4)))
  passed=tuple(s.address(v)for v in args);ordinal=sum(s.calls.values());s.calls[target]+=1;observed=()
  if target==DIRECTION:
   out=passed[3];assert out in(('STACK',-16),('STACK',-40));s.exposed.add(out[1]);observed=tuple(s.mem[out[1]+i]for i in range(12))
  elif target==SUBMIT:
   assert tuple(passed[i]for i in(0,1,3,4))==tuple(('STACK',v)for v in VECTOR_BASES)
   assert passed[7]==passed[12]==1 and passed[9:12]==(0,0,255)
   s.exposed.update(VECTOR_BASES);observed=tuple(tuple(s.mem[base+i]for i in range(12))for base in VECTOR_BASES)
  s.trace.append(('CALL',target,passed,observed,s.fcsr));s.trace.append(('FRAME',s.frame()));s.epoch+=1
  for base in s.exposed:
   for i in range(12):s.mem[base+i]=('PROVIDER_BYTE',ordinal,base+i)
  for i in range(max(4,n)):s.store(('STACK',-s.frame_bytes+4*i),4,('CALL_HOME',ordinal,i))
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  s.r[2]=('RESULT',target,ordinal)
  if target==REAL:s.f[0]=('FLOAT_RESULT',ordinal)
  s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal)
def invariant(s):
 assert s.r[19]==('ARG',0)and s.r[22]==61
 assert tuple(s.address(s.r[i])for i in(20,23,21,30))==tuple(('STACK',v)for v in VECTOR_BASES)
 assert(s.f[24],s.f[26],s.f[28],s.f[30])==(0x43B40000,LITERALS[2],LITERALS[1],LITERALS[0])
 for reg in range(16,24):assert s.at(-224+0x70+4*(reg-16),4)==('ENTRY',reg)
 assert s.at(-80,4)==('ENTRY',30)and s.at(-76,4)==('RETURN',)
 for reg in range(20,32):assert s.at(-224+0x40+4*(reg-20),4)==('ENTRY_FP',reg)
 for i in(1,2,3):assert s.at(4*i,4)==('ARG',i)
def observe(s,end):
 if end=='return':
  assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
  assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
 else:assert s.r[29]==('STACK',-s.frame_bytes);invariant(s)
 return(s.trace,s.read_set,s.divisors,s.frame(),s.fcsr,tuple(s.address(v)for v in s.r[2:]),tuple((i,s.f[i])for i in range(20,32)if end=='return'or i not in(20,22)),s.exposed)
def prove(raw,retail,raw_literals=LITERALS,retail_literals=LITERALS,remap=True):
 terms=Terms();programs=[Program(raw,terms),Program(retail,terms)];prefix=[];reports={}
 for side,program in enumerate(programs):prefix.append(program.paths(0,{LOOP:'loop',-4:'return'},State(side==0,raw_literals if side==0 else retail_literals,remap)))
 for phase in('prefix','first','steady'):
  answers=[]
  for side,program in enumerate(programs):
   if phase=='prefix':paths=prefix[side]
   else:
    starts=[deepcopy(s)for key,s in prefix[side].items()if key[0]=='loop'];assert len(starts)==1;s=starts[0]
    s.trace=[];s.read_set=Counter();s.divisors=set();s.steps=0
    if phase=='steady':
     s.facts={};s.r[18]=('REMAINING',);e.assume(s,g.predicate('SLT',0,s.r[18]),True)
     # All non-saved private bytes are arbitrary at the inductive cut. Keep
     # only the established saved GPR/FP/RA custody and incoming parameters.
     for off in range(-224,0):
      if not -160<=off<-72:s.mem[off]=('LOOP_ENTRY_BYTE',off)
     s.exposed=set(VECTOR_BASES)
     s.r[16],s.r[17]=('PREVIOUS_HEADING',),('PREVIOUS_PITCH',)
     s.f[20],s.f[22]=('PREVIOUS_SAMPLE',0),('PREVIOUS_SAMPLE',1)
    invariant(s)
    paths=program.paths(LOOP,{LOOP:'loop',-4:'return'},s)
   answers.append({key:observe(s,key[0])for key,s in paths.items()})
  assert answers[0].keys()==answers[1].keys(),('path keys',phase)
  for key in answers[0]:
   if answers[0][key]!=answers[1][key]:
    part=next(i for i,(x,y)in enumerate(zip(answers[0][key],answers[1][key]))if x!=y)
    if part==0:
     aa,bb=answers[0][key][part],answers[1][key][part];at=next(i for i,(x,y)in enumerate(zip(aa,bb))if x!=y)
     if aa[at][0]==bb[at][0]=='FRAME':
      off=next(i for i,(x,y)in enumerate(zip(aa[at][1],bb[at][1]))if x!=y)
      raise AssertionError(('frame event',phase,at,off-224,aa[at][1][off],bb[at][1][off]))
     raise AssertionError(('trace event',phase,at,repr(aa[at])[:1200],repr(bb[at])[:1200]))
    raise AssertionError(('relation',phase,key,part,repr(answers[0][key][part])[:1200],repr(answers[1][key][part])[:1200]))
  reports[phase]=len(answers[0])
 coverage=[]
 for program in programs:
  unseen=set(range(0,752,4))-program.seen;assert unseen=={0xE4}and program.words[0xE4//4]==0x0007000D
  coverage.append(dict(visited=len(program.seen),preserved_unreachable_break=0xE4))
 return dict(passes=True,phases=reports,coverage=coverage,private_incoming_bytes=248,closed_52_byte_rotation=True,source_frame_bytes=232,retail_frame_bytes=224,source_only_unused_gap_bytes=8,dead_sample_roles_excluded_only_at_loop_cut=True,all_four_exposed_vectors_and_provider_mutations=True,ordered_FP_FCSR=True,literal_identities=8,inductive_saved_roles_and_custody=True,positive_countdown_closure='positive signed n decrements to n-1; nonzero successor is positive',c_match_credit=0)
def programs():
 RAW,REFS=payload(p/'owner.o','func_150B82D0');assert pairs(REFS,list(struct.unpack('>188I',RAW)))==PAIRS
 lookup={v[1]:v[2][1]for v in symbol_rows((f/'conker/build/conker.us.elf').read_bytes())};lookup['.rodata']=POOL
 return bound_blob(RAW,REFS,lookup),list(struct.unpack('>188I',(p/'retail.bin').read_bytes()))
def main(raw=None,retail=None):
 if raw is None:raw,retail=programs()
 assert derive(raw)==retail
 source_pool=sections(p/'owner.o')['.rodata'][1];original_pool=(f/'conker/build/conker.us.elf').read_bytes()
 source_values=struct.unpack_from('>8I',source_pool,40);original_values=struct.unpack_from('>8I',original_pool,elf_slot_offset(original_pool,0x8009FD68,32))
 assert source_values==original_values==LITERALS and source_pool[72:]==bytes(8)
 report=prove(raw,retail,source_values,original_values);controls=[]
 def reject(label,words,values=source_values,remap=True):
  try:prove(words,retail,values,original_values,remap)
  except(AssertionError,KeyError,ValueError)as error:
   reason=str(error);assert not any(v in reason for v in('unsupported','unbounded proof','escaped code')),(label,reason)
   controls.append(label)
  else:raise AssertionError(('ineffective control',label))
 reject('disabled-private-home-map',raw,remap=False)
 for label,wanted,mask in(('count-divisor',0x2401001A,1),('pitch-divisor',0x2416003D,1),('heading-mask',0x305000FF,128),('duration-base',0x25CF004B,1),('loop-decrement',0x2652FFFF,1),('saved-return-home',0xAFBF0094,4),('acceleration-y-home',0xE7B200BC,4)):
  assert raw.count(wanted)==1,(label,hex(wanted));bad=raw[:];bad[bad.index(wanted)]^=mask;reject(label,bad)
 for index in range(8):
  bad=list(source_values);bad[index]^=1;reject('literal-bit-'+str(index),raw,tuple(bad))
 report.update(effective_negatives=controls,steady_all_non_saved_private_bytes_arbitrary=True,source_and_retail_literal_bits=list(source_values),raw_fault_register_identity_unclaimed=True)
 (p/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
