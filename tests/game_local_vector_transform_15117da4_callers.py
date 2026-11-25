"""Three original bounded caller windows, connected leaf, and separate original epilogue.

The parent dispatch/other cases between these windows are preconditions, not
claimed runtime coverage of the full 652-word function.
"""
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
import hashlib,itertools,json,math,re,struct,sys
sys.path.insert(0,str(Path.cwd()));pass
from tools.tests import game_local_vector_transform_15117da4_guest as g
from tools.experiments import game_local_vector_transform_15117da4_match as p
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
o=p.OUT;r=p.ROOT;PARENT=0x15117f3c;EPILOGUE=0x15118958;ACTOR=0x70000;PAYLOAD=0x71000
WINDOWS=[(0x1511815c,0x151181fc,(0x1511821c,)),(0x15118678,0x1511869c,(0x1511877c,)),(0x1511877c,0x151187b0,(0x151188d8,0x151188dc))]
class TrackedParentCode(WindowCode):
 def __getitem__(self,pc):
  value=super().__getitem__(pc)
  if PARENT<=pc<PARENT+2608:self.owner.executed_parent.add(pc)
  return value
class Connected(g.Machine):
 def __init__(self,leaf,c,index,present,source_state,words,changed=None):
  memory=g.fixture(c);self.parent_case=c;self.window=index;self.present=present;self.source_state=source_state;self.frame=g.STACK+c.phase-168;self.child_args=[];self.child_expectation=None;self.child_return=None
  for base,n in((ACTOR,0x340),(PAYLOAD,0xa0)):memory.update({base+i:(i*23+c.seed+0x33)&255 for i in range(n)})
  for i,v in enumerate((1.,2.,3.)):g.put(memory,g.POINT+44+4*i,g.bits(v))
  g.put(memory,g.POINT+124,source_state)
  connected=dict(zip(range(PARENT,PARENT+4*len(words),4),words));connected.update(zip(range(g.ENTRY,g.ENTRY+4*len(leaf),4),leaf))
  if changed:connected[changed[0]]=changed[1]
  super().__init__(words[:4],c,entry=PARENT,memory=memory,arguments=(g.POINT,),connected=connected);self.executed_parent=set();self.code=TrackedParentCode(self.code,self);self.code.ends=(PARENT+16,)
  try:self.run();raise AssertionError('Missing prologue boundary')
  except WindowBoundary:pass
  assert self.r[29]==self.frame and self.r[16]==g.POINT and g.read(self.memory,self.frame+32)==self.before[16]and g.read(self.memory,self.frame+36)==self.before[31]
  self.c=replace(c,phase=c.phase-168);self.original_fcsr=c.fcsr;self.entry=WINDOWS[index][0];self.code.ends=WINDOWS[index][2];self.r[14]=ACTOR if present else 0;self.r[8]=3;self.r[9]=1;self.r[10]=8;self.r[11]=c.seed&3;self.r[12]=4;self.r[3]=1208;self.f[12]=g.bits(40.);self.f[14:15]=[c.values[0]];self.f[16]=c.values[1];self.f[18]=c.values[2];self.f[2]=g.bits(.5)
  for off,v in[(0x60,c.values[2]),(0x64,c.values[1]),(0x68,c.values[0]),(0x70,ACTOR if present else 0),(0x40,3),(0x48,1),(0x4c,c.seed&3)]:g.put(self.memory,self.frame+off,v)
  g.put(self.memory,ACTOR+0x31c,PAYLOAD if source_state!=2 or index!=2 else 0)
 def record_call(self,t):
  if t!=g.ENTRY:return super().record_call(t)
  args=tuple(map(g.u32,self.arguments(5)));self.child_args.append(args);c=replace(self.c,values=args[1:4],fcsr=self.fcsr,home_mutation=False);self.child_case=c;self.child_start=dict(self.memory)
  with patch.object(g,'destination',lambda _:args[4]):self.child_expectation=g.reference(self.memory,c)
  self.saved_child_registers=self.r[:]
 def hook(self,t):
  with patch.object(g,'destination',lambda _:self.child_args[-1][4]):super().hook(t)
 def execute(self,w):
  # The two observed consumers truncate finite outputs before their SH stores.
  if w>>26==17 and w>>21&31==16 and w&63==13:
   value=g.floating(self.f[w>>11&31]);assert math.isfinite(value)and-2147483648<=value<2147483648;self.f[w>>6&31]=g.u32(math.trunc(value));return
  super().execute(w)
 def run_window(self):
  try:self.run();raise AssertionError('Missing caller boundary')
  except WindowBoundary:pass
  self.window_memory=dict(self.memory);self.window_registers=self.r[:];self.window_fcsr=self.fcsr
  # This is a separate bounded epilogue execution, not an invented parent edge.
  self.entry=EPILOGUE;self.code.ends=();self.run();self.window_visits=set(self.executed_parent);return self
def verify(m,c,index,present,state):
 expected_calls=1 if index==0 else int(present and(index==1 or state!=2));assert len(m.child_args)==expected_calls
 if not expected_calls:return
 args=m.child_args[0];values=c.values
 if index==0:values=tuple(g.arithmetic(v,g.bits(float(i+1)),2,c.fcsr&3)[0]for i,v in enumerate(values))
 assert args==(g.POINT,*values,m.frame+0x54),(index,'caller arguments',args,values)
 expected,calls,obs,fcsr=m.child_expectation;assert m.calls==calls and m.provider_observations==obs,(c,index,present,state,'provider comparison',m.calls==calls,[(i,a[1],b[1],sum(a[0].get(k)!=v for k,v in b[0].items()))for i,(a,b)in enumerate(zip(m.provider_observations,obs))if a!=b])
 # Independently check all12 output bytes and the two actual signed-half consumers.
 assert all(m.window_memory[m.frame+0x54+i]==expected[m.frame+0x54+i]for i in range(12))
 if index in(1,2):
  for i in range(3):assert g.read(m.window_memory,PAYLOAD+0x6c+2*i,2)==math.trunc(g.floating(g.read(expected,m.frame+0x54+4*i)))&65535
 assert all(m.r[i]==m.before[i]for i in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:]
def main():
 rom=(r/'conker/conker.us.bin').read_bytes();full=(o/'baseline/conker/asm/142560.s').read_text();fragment=full.split('glabel func_15117F3C',1)[1].split('endlabel func_15117F3C',1)[0];blob=bytes.fromhex(''.join(re.findall(r'/\* [0-9A-F]+ [0-9A-F]+ ([0-9A-F]{8}) \*/',fragment)));assert blob==rom[0x1453ec:0x145e1c]and len(blob)==652*4;words=list(struct.unpack('>652I',blob));programs=[g.bound_blob(*g.payload(o/f,'func_15117DA4'),g.symbols())for f in('original-target.o','selected-final/owner-candidate.o')];count=children=0;seen=set()
 corpus=[(g.Case(kind=k,category=cat,mode=mode,seed=seed,fcsr=rm,phase=8*(rm&1)),index,present,state)for index,k,cat,mode,seed,rm,present,state in itertools.product(range(3),(0x8005,0x8006),(0,53),(0,7),(0,3),range(4),(False,True),(0,2))]
 for c,index,present,state in corpus:
  models=[]
  for ws in programs:
   m=Connected(ws,c,index,present,state,words).run_window();verify(m,c,index,present,state);models.append(m)
  a,b=models;assert a.memory==b.memory and a.r==b.r and a.fcsr==b.fcsr and a.provider_frames==b.provider_frames and a.child_args==b.child_args;seen.update(a.window_visits);children+=len(a.child_args);count+=1
 controls=[]
 for name,at,word,index in [('output-storage',0x15118688,0x27af0058,1),('argument-order',0x1511867c,0x8fa50064,1)]:
  c=g.Case(kind=0x8005);m=Connected(programs[0],c,index,True,0,words,(at,word)).run_window()
  try:verify(m,c,index,True,0)
  except AssertionError:controls.append(dict(name=name,supported_complete_window_and_separate_epilogue=True,rejected=True))
  else:raise AssertionError('Ineffective caller control')
 q=dict(full_parent_words=652,full_parent_ASM_equal_ROM=True,parent_sha256=hashlib.sha256(blob).hexdigest(),complete_parent_runtime_qualified=False,parent_frame=168,three_actual_JAL_windows=True,cases_per_stream=count,streams=2,connected_children_per_stream=children,bounded_parent_words_visited=len(seen),original_four_word_prologue_and_separate_five_word_epilogue_executed=True,output_storage_bytes=12,output_at_parent_SP_plus_0x54=True,all_five_child_arguments_and_two_original_truncate_SH_consumers_checked=True,nonnull_null_and_missing_payload_gates=True,full_provider_frame_and_saved_register_and_bounded_parent_memory_equal=True,provider_internals_and_intervening_parent_dispatch_not_qualified=True,effective_controls=controls,parent_matching_credit=0,source_installed=p.installed(),matching_credit=0);(o/'callers.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=='__main__':main()
