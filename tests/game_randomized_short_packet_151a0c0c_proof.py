"""Whole straight-line/three-way CFG transfer, independent of normalization.

Mapped ordinary RAM, stable unpassed argument/private homes, no public alias of
private frame/code/literals. Opaque o32 helpers may mutate public RAM and FCSR,
clobber every caller register and their own argument homes. The final helper sees
all56 escaped packet bytes and may mutate them. Exact FP opcode/operand/status
sequence is retained; no raw fault-PC, hardware or portable-undefined-input claim.
"""
from copy import deepcopy
from pathlib import Path
import hashlib,json,struct
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests import game_side_ring_renderer_1519fe6c_opening_proof as opening
from tools.tests import game_side_ring_renderer_1519fe6c_texture_proof as texture
from tools.tests.game_side_ring_emitter_1519f7f0_transition_proof import byte,word
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.tests.game_side_ring_renderer_1519fe6c_coverage import static
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_randomized_short_packet_151a0c0c_match as m
r,o,ENTRY,POOL=m.ROOT,m.OUT,m.ENTRY,0x80400000
RNG,FLOAT,SINE,SUBMIT=0x150ADA20,0x150ADA68,0x151423D8,0x15167D84
PRIVATE=(*range(4,12),26,27,43,51,54,55)
class State(opening.State):
 def __init__(self,side,literals):
  super().__init__(side,'random-packet');self.literals=literals;self.fcsr=('ENTRY_FCSR',)
  self.r=[('UNDEFINED_GPR',side,i)for i in range(32)];self.r[0]=0;self.r[29]=('STACK',0);self.r[31]=('RETURN',)
  self.f=[('UNDEFINED_FPR',side,i)for i in range(32)]
  for i in(*range(16,24),28,30):self.r[i]=('ENTRY',i)
  for i in range(20,32):self.f[i]=('ENTRY_FP',i)
  for i in range(4):self.r[4+i]=('ARG',i)
  for i in range(4,15):self.store(('STACK',4*i),4,('ARG',i))
  self.private_writes=[]
 def load(self,address,size,pool):
  if e.tagged(address,'STACK'):
   if size==2:
    values=[self.mem.get(address[1]+i,('PRIVATE_BYTE',address[1]+i))for i in range(2)]
    if all(isinstance(v,int)for v in values):return values[0]*256+values[1]
    if all(e.tagged(v,'BYTE')for v in values)and[v[2]for v in values]==[8,0]and values[0][1]==values[1][1]:return texture.mask(values[0][1],16)
    return ('HALF',tuple(values))
   return super().load(address,size,pool)
  if isinstance(address,int)and address in self.literals:
   assert size==4;return self.literals[address]
  e.plain(address);assert not e.has_tag(address,'UNDEFINED_GPR'),('undefined public address',address)
  self.trace.append(('READ',address,size,self.epoch));return('LOAD',address,size,self.epoch)
class Program(opening.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
 def instruction(self,pc):self.seen.add(pc);return super().instruction(pc)
 def step(self,s,w):
  op,fmt,fn=w>>26,w>>21&31,w&63
  if op==17 and fmt==4:s.f[w>>11&31]=s.r[w>>16&31]
  elif op==17 and fmt==16:
   fs,ft,fd=w>>11&31,w>>16&31,w>>6&31
   if fn==6:s.f[fd]=s.f[fs]
   else:
    assert fn in(0,1,2,3,7,13),('unsupported random-packet FP',hex(w))
    args=(s.f[fs],s.f[ft])if fn in(0,1,2,3)else(s.f[fs],)
    assert not any(e.has_tag(v,'UNDEFINED_FPR')for v in args),('undefined FP input',args)
    observation=(fn,args,s.fcsr);s.trace.append(('FP',observation));s.f[fd]=self.terms.term('FP_VALUE',*observation);s.fcsr=self.terms.term('FP_STATUS',*observation)
  else:super().step(s,w)
 def call(self,s,target):
  assert target in(RNG,FLOAT,SINE,SUBMIT),('unclassified provider',target)
  assert s.r[29]==('STACK',-128)
  n={RNG:0,FLOAT:0,SINE:1,SUBMIT:6}[target]
  args=tuple(s.r[4:4+min(n,4)])+tuple(s.load(('STACK',-112+4*i),4,b'')for i in range(max(0,n-4)))
  assert not any(e.has_tag(a,'UNDEFINED_GPR')for a in args),('undefined call input',target,args)
  ordinal=s.calls[target];s.calls[target]+=1
  if target==SUBMIT:
   assert args[0]==('STACK',-56),('exposed packet home',args[0])
   packet=tuple(s.load(('STACK',-56+i),1,b'')for i in range(56))
   for i in PRIVATE:assert packet[i]==('PRIVATE_BYTE',-56+i),('unwritten packet byte changed',i,packet[i])
   s.trace.append(('SUBMIT',target,args,packet,s.fcsr))
   for i in range(56):s.mem[-56+i]=('ESCAPED_AFTER',target,ordinal,i)
  else:
   for a in args:e.plain(a)
   s.trace.append(('CALL',target,args,s.fcsr))
  s.epoch+=1
  for i in(1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',target,ordinal,i)
  for i in range(20):s.f[i]=('CALLER_FP',target,ordinal,i)
  for i in range(4):s.store(('STACK',-128+4*i),4,('CALL_HOME',target,ordinal,i))
  s.r[2]=('RESULT',target,ordinal);s.f[0]=('FP_RESULT',target,ordinal);s.r[31]=('CALL_RETURN',target,ordinal)
  s.hi=('CALL_HI',target,ordinal);s.lo=('CALL_LO',target,ordinal);s.fcsr=('CALL_FCSR',target,ordinal)
  assert s.load(('STACK',-100),4,b'')==('RETURN',),('saved return custody',target)
def observable(s):
 assert s.r[2]==1 and s.r[29]==('STACK',0) and s.r[31]==('RETURN',)
 assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))
 assert s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
 assert s.calls=={RNG:4,SINE:4,FLOAT:1,SUBMIT:1}
 for off,size in s.private_writes:
  assert (-128<=off and off+size<=0)or(off in(0,4,8,12)and size==4),('private write escape',off,size)
 effects=[];reads=[];fp=[]
 for event in s.trace:
  if event[0]=='READ':reads.append(event)
  elif event[0]=='FP':fp.append(event)
  else:
   assert event[0]in('CALL','SUBMIT');effects.append((tuple(sorted(reads,key=repr)),tuple(fp),event));reads=[];fp=[]
 assert not reads and not fp
 return effects,s.fcsr,s.r[2],tuple(s.f[20:])
def programs(label='qualified'):
 raw,refs=payload(o/(label+'.o'),'func_151A0C0C');symbols={name:int(name.split('_',1)[1],16)for rows in refs.values()for kind,name in rows if name.startswith(('func_','D_'))};symbols['.rodata']=POOL
 candidate=bound_blob(raw,refs,symbols);pool=sections(o/(label+'.o'))['.rodata'][1]
 literals={POOL+i:struct.unpack_from('>I',pool,i)[0]for i in range(0,len(pool),4)}
 literals.update({0x800A8D14:0x43FB8000,0x800A8D18:0x44484000})
 retail=list(struct.unpack_from('>141I',(r/'conker/conker.us.bin').read_bytes(),0x1CE0BC));return candidate,retail,literals,{0x800A8D14:0x43FB8000,0x800A8D18:0x44484000}
def prove(raw,retail,raw_literals,retail_literals):
 results={};seen={};terms=Terms()
 for side,words,literals in(('raw',raw,raw_literals),('retail',retail,retail_literals)):
  program=Program(words,terms);paths=program.paths(0,{-4:'return'},State(side,literals));results[side]={key:observable(s)for key,s in paths.items()};seen[side]=program.seen
 assert results['raw'].keys()==results['retail'].keys(),('path predicates',list(results['raw']),list(results['retail']))
 for key in results['raw']:
  a,b=results['raw'][key],results['retail'][key]
  if a!=b:
   differing=[(i,x,y)for i,(x,y)in enumerate(zip(a[0],b[0]))if x!=y]
   raise AssertionError(('whole-function transfer',key,repr(differing)[:3500]))
 for side,words in(('raw',raw),('retail',retail)):assert seen[side]==static(words),('incomplete CFG',side,static(words)-seen[side])
 return dict(symbolic_paths=len(results['raw']),raw_reachable_words=len(seen['raw']),retail_reachable_words=len(seen['retail']),ordered_FP_FCSR=True,all56_packet_bytes=True,unwritten14_bytes_preserved=True,arbitrary_o32_clobbers_and_public_mutation=True,saved_ABI_and_return_custody=True,whole_function=True,c_match_credit=0)
def main():
 values=programs();raw,retail,a,b=values;report=prove(*values)
 alternative=raw[:]
 for i,w in enumerate(alternative):
  op,fn,fmt=w>>26,w&63,w>>21&31
  if op==0:fields=(11,)if fn in(16,18)else(21,)if fn==8 else(16,11)if fn in(0,2,3)else(21,16,11)
  elif op==17:fields=(16,)if fmt in(0,4)else()
  elif op==3:fields=()
  elif op==15:fields=(16,)
  elif op in(49,53,57,61):fields=(21,)
  else:fields=(21,16)
  for shift in fields:
   reg=w>>shift&31
   if reg in(12,13):w=(w&~(31<<shift))|((25-reg)<<shift)
  alternative[i]=w
 assert alternative!=raw and prove(alternative,retail,a,b)==report
 def unique(predicate):
  matches=[i for i,w in enumerate(raw)if predicate(w)];assert len(matches)==1,matches;return matches[0]
 controls=[
  ('unsigned-angle-divisor',unique(lambda w:w==0x2401000F),lambda w:w+1),
  ('packet-magnitude',unique(lambda w:w>>26==9 and w>>21&31==0 and w&65535==200),lambda w:w+1),
  ('speed-literal',0x84//4,lambda w:w+4),
  ('input-x-coordinate',0x11C//4,lambda w:w+4),
  ('direction-store-width',0xC4//4,lambda w:(w&0x03FFFFFF)|(40<<26)),
  ('angle-private-home',0x30//4,lambda w:w-2),
  ('saved-return-home',1,lambda w:w+4),
  ('unwritten-byte-initialization',0x1C//4,lambda w:0xA3A00073),
 ]
 negatives=[]
 for label,index,change in controls:
  bad=raw[:];bad[index]=change(bad[index]);assert bad!=raw
  try:prove(bad,retail,a,b)
  except AssertionError as error:
   reason=str(error);assert not any(v in reason for v in('unsupported','unbounded proof','escaped code')),('invalid proof control',label,reason)
   negatives.append(dict(name=label,rejected=reason[:250]))
  else:raise AssertionError(('ineffective proof control',label))
 report['independent_register_allocation_positive_control']=True;report['effective_controls']=negatives
 (o/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
