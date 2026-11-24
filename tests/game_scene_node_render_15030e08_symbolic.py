"""Independent entry/one-iteration bisimulation; no projection map is imported."""
from pathlib import Path
import json,struct,sys
from tools.experiments import game_scene_node_render_15030e08_match as p
r,o=p.ROOT,p.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
MASK=0xffffffff
class NeedChoice(Exception):pass
def addr(kind,offset=0):return('address',kind,offset)
def add(a,b):
 if isinstance(a,int)and isinstance(b,int):return(a+b)&MASK
 if b==0:return a
 if a==0:return b
 if isinstance(a,tuple)and a[0]=='address'and isinstance(b,int):return addr(a[1],a[2]+b)
 return('add32',a,b)
def low5(v):
 if isinstance(v,int):return v&31
 if v[0]=='and32'and v[2]==31:return low5(v[1])
 return('low5',v)
def band(a,b):
 if isinstance(a,int)and isinstance(b,int):return a&b
 return('and32',a,b)
def equal(a,b):
 if a==b:return True
 if isinstance(a,int)and isinstance(b,int):return a==b
 return('equal32',*sorted((a,b),key=repr))
class State:
 def __init__(self,data,refs,choices,iteration=False,side=0):
  self.words=tuple(w[0]for w in struct.iter_unpack('>I',data));self.refs=refs;self.choices=choices;self.pc=21 if iteration else 0;self.iteration=iteration;self.side=side;self.steps=[];self.events=[];self.calls=0;self.memory=('arbitrary-loop-public-memory',)if iteration else('initial-public-memory',);self.private={}
  self.r=[('original-register',i)for i in range(32)];self.r[0]=0;self.r[4]=('argument',0);self.r[5]=('argument',1);self.r[6]=('argument',2);self.r[29]=addr('stack');self.r[31]=('original-return',);self.before=self.r[:]
  if iteration:
   # This is the entry-established frame and the arbitrary live loop invariant.
   self.r[29]=addr('stack',-72)
   for reg,offset in((22,56),(21,52),(19,44),(31,68),(30,64),(23,60),(20,48),(18,40),(17,36),(16,32)):self.write(add(self.r[29],offset),4,self.before[reg])
   self.r[16]=('nonzero-loop-node',);self.r[22]=('loop-cursor',);self.r[19]=('argument',1);self.r[21]=('argument',2);self.r[20]=1;self.r[23]=2;self.r[30]=7;self.r[14]=self.read(add(self.r[16],3),1,False)
  for reg in(1,2,3,*range(4,16),24,25):
   if not iteration and reg in(4,5,6)or iteration and reg==14:continue
   self.r[reg]=('independent-dead-register',side,reg)
  if iteration:
   self.r[17]=('independent-dead-role',side,17);self.r[18]=('independent-dead-role',side,18);self.r[31]=('independent-dead-link',side)
 def read(self,p,n,record=True):
  if isinstance(p,tuple)and p[0]=='address'and p[1]=='stack':
   values=[self.private.get(add(p,i),('initial-private-byte',p[2]+i))for i in range(n)]
   if all(isinstance(v,int)for v in values):return int.from_bytes(bytes(values),'big')
   if all(isinstance(v,tuple)and v[0]=='private-byte'and v[2:]==(i,n)for i,v in enumerate(values))and all(v[1]==values[0][1]for v in values):return values[0][1]
   return('private-bytes',tuple(values))
  value=('public-read',self.memory,p,n)
  if record:self.events.append(('read',p,n,value))
  return value
 def write(self,p,n,v):
  assert p[0]=='address'and p[1]=='stack','Target unexpectedly wrote public RAM'
  for i in range(n):self.private[add(p,i)]=(v>>(8*(n-1-i)))&255 if isinstance(v,int)else('private-byte',v,i,n)
 def location(self,i,rs,imm):
  refs=self.refs.get(4*i)
  if refs:assert len(refs)==1 and refs[0][0]=='R_MIPS_LO16'and self.r[rs]==('symbol-high',refs[0][1])and imm==0;return addr('global:'+refs[0][1])
  return add(self.r[rs],imm)
 def ins(self,i):
  self.steps.append(i);w=self.words[i];op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;fn=w&63;imm=((w&65535)^32768)-32768
  if w==0:return
  if op==0:
   if fn==37:assert self.r[rt]==0;self.r[rd]=self.r[rs]
   elif fn==4:
    value,count=self.r[rt],low5(self.r[rs]);self.r[rd]=(value<<count)&MASK if isinstance(value,int)and isinstance(count,int)else('shl32',value,count)
   elif fn==36:self.r[rd]=band(self.r[rs],self.r[rt])
   else:raise AssertionError(('R instruction',i,hex(w)))
  elif op==9:self.r[rt]=add(self.r[rs],imm)
  elif op==12:self.r[rt]=band(self.r[rs],w&65535)
  elif op in(10,11):
   value=self.r[rs]
   if isinstance(value,int):self.r[rt]=int(((value^0x80000000)-0x80000000 if op==10 else value)<(imm if op==10 else imm&MASK))
   else:self.r[rt]=('signed-lt'if op==10 else'unsigned-lt',value,imm)
  elif op==15:
   refs=self.refs.get(4*i);assert refs and len(refs)==1 and refs[0][0]=='R_MIPS_HI16'and imm==0;self.r[rt]=('symbol-high',refs[0][1])
  elif op in(35,36):self.r[rt]=self.read(self.location(i,rs,imm),4 if op==35 else 1)
  elif op==43:self.write(self.location(i,rs,imm),4,self.r[rt])
  else:raise AssertionError(('Instruction',i,hex(w)))
  self.r[0]=0
 def arguments(self,n):return tuple(self.r[4+i]if i<4 else self.read(add(self.r[29],4*i),4)for i in range(n))
 def call(self,name):
  arity={'func_15083E90':1,'func_1506196C':2,'func_150311C4':5};a=self.arguments(arity[name]);self.calls+=1;self.events.append(('call',name,a,self.memory));self.memory=('arbitrary-provider-public-memory',self.calls)
  for i in range(max(4,len(a))):self.write(add(self.r[29],4*i),4,('independent-clobbered-outgoing-home',self.side,self.calls,i))
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=('independent-provider-register',self.side,self.calls,reg)
  self.r[2]=('provider-return',name,self.calls)
 def run(self):
  while True:
   assert len(self.steps)<220
   if self.pc==21 and(not self.iteration or self.steps):return'loop'
   i=self.pc;w=self.words[i];op=w>>26;rs=w>>21&31;rt=w>>16&31
   if w==0x03e00008:
    assert self.r[31]==self.before[31];self.steps.append(i);self.ins(i+1);assert self.r[16:24]==self.before[16:24]and self.r[28:]==self.before[28:];return'return'
   if op==3:
    refs=self.refs.get(4*i);assert refs and len(refs)==1 and refs[0][0]=='R_MIPS_26';self.r[31]=('linked-return',i+2);self.steps.append(i);self.ins(i+1);self.call(refs[0][1]);self.pc=i+2;continue
   if op in(4,5,20,21):
    key=equal(self.r[rs],self.r[rt])
    if isinstance(key,bool):eq=key
    elif key in self.choices:eq=self.choices[key]
    else:raise NeedChoice(key)
    taken=eq if op in(4,20)else not eq;self.events.append(('branch',key,eq));self.steps.append(i)
    if taken or op not in(20,21):self.ins(i+1)
    self.pc=i+1+(((w&65535)^32768)-32768)if taken else i+2
   else:self.ins(i);self.pc=i+1
 def signature(self,end):
  live=tuple(self.r[i]for i in(16,19,20,21,22,23,30,14))if end=='loop'else(self.r[2],*self.r[16:24],*self.r[28:])
  frame=tuple(sorted(((p,v)for p,v in self.private.items()if -40<=p[2]<0),key=repr))
  return end,tuple(self.events),self.memory,frame,live
def paths(raw,retail,iteration):
 pending=[{}];completed=[];branches=set()
 while pending:
  choices=pending.pop();values=[];needs=[]
  for side,(data,refs)in enumerate((raw,retail)):
   model=State(data,refs,choices,iteration,side)
   try:end=model.run();needs.append(None);values.append(model.signature(end))
   except NeedChoice as e:needs.append(e.args[0]);values.append(None)
  if needs[0]is not None or needs[1]is not None:
   assert needs[0]==needs[1],('Branch predicates differ',iteration,needs);key=needs[0];assert key not in choices;branches.add(key)
   for answer in(False,True):pending.append(dict(choices,**{})|{key:answer})
  else:
   assert values[0]==values[1],('Loop relation differs',iteration,choices,values);completed.append(dict(end=values[0][0],calls=sum(e[0]=='call'for e in values[0][1])))
  assert len(pending)+len(completed)<512,'Unexpected path explosion'
 return dict(paths=len(completed),loop_cuts=sum(v['end']=='loop'for v in completed),returns=sum(v['end']=='return'for v in completed),call_counts=sorted(set(v['calls']for v in completed)),symbolic_branch_keys=len(branches))
def proof(raw,retail,write=True):
 assert len(raw[0])==400 and len(retail[0])==396;entry=paths(raw,retail,False);iteration=paths(raw,retail,True);assert entry['loop_cuts']and entry['returns']and iteration['loop_cuts']and iteration['returns']
 q=dict(entry=entry,arbitrary_loop_iteration=iteration,ordered_public_reads_calls_and_conditions_equal=True,loop_live_roles_and_saved_frame_equal=True,independent_initial_dead_roles_and_provider_register_home_clobbers=True,return_cursor_and_saved_registers_equal=True,view_shift_all_32_bit_words=True,next_link_snapshot_preserved_across_providers=True,arbitrary_compatible_provider_public_effects=True,projection_imported=False,source_installed=False,matching_credit=0,scope='Entry and one arbitrary nonzero-node iteration establish an inductive/coinductive relation for the whole loop, including termination or continued iteration. Ordinary mapped RAM, public node/actor aliases and compatible returning o32 providers; no private-frame or code-address reflection. Dead caller-saved temporaries and outgoing homes can differ independently. Raw full private/fault-state identity and helper implementations are not claimed.')
 if write:(o/'symbolic.json').write_bytes((json.dumps(q,indent=2)+'\n').encode())
 return q
if __name__=='__main__':print(json.dumps(proof(payload(o/'selected-final/candidate.o','func_15030E08'),payload(o/'original-target.o','func_15030E08'))),flush=True)
