"""Strict paired symbolic effects before the snapshot loop; no whole-body claim."""
from pathlib import Path
import copy,hashlib,json,struct
from tools.tests import game_strip_update_151ad174_private_oracle as o
STOP=142;MASK=0xffffffff
def norm(op,*args):
 if op in('add','and','or','mul'):
  if op=='add':
   values=[];constant=0
   for a in args:
    for b in(a[1:]if isinstance(a,tuple)and a[0]=='add'else(a,)):
     if isinstance(b,int):constant=(constant+b)&MASK
     else:values.append(b)
   values.sort(key=repr)
   if constant:values.append(constant)
   return 0 if not values else values[0]if len(values)==1 else('add',*values)
  if all(isinstance(v,int)for v in args):
   a,b=args;return {'and':lambda:a&b,'or':lambda:a|b,'mul':lambda:a*b}[op]()&MASK
  if op=='or'and 0 in args:return args[1]if args[0]==0 else args[0]
  args=tuple(sorted(args,key=repr))
 if op=='sub':
  a,b=args
  if a==b:return 0
  if isinstance(b,int):return norm('add',a,(-b)&MASK)
 if op in('sll','sra')and all(isinstance(v,int)for v in args):
  a,n=args;return((a<<n)if op=='sll'else((a-0x100000000 if a&0x80000000 else a)>>n))&MASK
 return(op,*args)
def initial():
 return dict(r=[0]+[('r',i)for i in range(1,32)],f=[('f',i)for i in range(32)],hi=('hi',),lo=('lo',),cc=('cc',),csr=('csr',))
class Pair:
 def __init__(self,left,right):self.words=(left,right);self.completed=[];self.calls=0;self.branches=0
 def execute(self,pc,states,events):
  effects=[]
  for word,s in zip((self.words[0][pc],self.words[1][pc]),states):
   op,rs,rt,rd,sa,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63;u=word&65535;imm=u-65536 if u&32768 else u;r,f=s['r'],s['f'];effect=None
   def put(reg,value):
    if reg:r[reg]=value
   if word==0:pass
   elif op==15:put(rt,u<<16)
   elif op==9:put(rt,norm('add',r[rs],imm&MASK))
   elif op==12:put(rt,norm('and',r[rs],u))
   elif op==0:
    if fn in(33,35,37):put(rd,norm({33:'add',35:'sub',37:'or'}[fn],r[rs],r[rt]))
    elif fn in(0,3):put(rd,norm('sll'if fn==0 else'sra',r[rt],sa))
    elif fn==25:s['lo']=norm('mul',r[rs],r[rt]);s['hi']=('mulhi',*sorted((r[rs],r[rt]),key=repr))
    elif fn==18:put(rd,s['lo'])
    else:raise AssertionError(('unsupported R',pc,hex(word)))
   elif op in(32,33,35,36,37,49):
    address=norm('add',r[rs],imm&MASK);effect=('read',op,address);value=('memory',len(events),op)
    if op==49:f[rt]=value
    else:put(rt,value)
   elif op in(40,41,43,57,61):
    address=norm('add',r[rs],imm&MASK)
    if op==61:value=(f[rt+1],f[rt])
    else:value=f[rt]if op==57 else norm('and',r[rt],255 if op==40 else 65535)if op in(40,41)else r[rt]
    effect=('write',op,address,value)
   elif op==17:
    if rs==4:f[rd]=r[rt]
    elif rs==16:
     args=(f[rd],)+( (f[rt],)if fn in(0,1,2,3,50,60,62)else())
     if fn==6:f[sa]=f[rd]
     else:
      effect=('FP',rs,fn,*args);before=s['csr'];s['csr']=('csr',before,effect)
      if fn in(50,60,62):s['cc']=('predicate',before,effect)
      else:f[sa]=('FP-result',before,effect)
    else:raise AssertionError(('unsupported COP1',pc,hex(word)))
   elif op==3:put(31,o.ENTRY+pc*4+8)
   else:raise AssertionError(('unsupported',pc,hex(word)))
   effects.append(effect)
  assert effects[0]==effects[1],('effect mismatch',pc,effects)
  if effects[0]is not None:events.append(effects[0])
 def predicate(self,pc,s,word):
  op,rs,rt=word>>26,word>>21&31,word>>16&31;r=s['r']
  if op==17:return('FP-branch',word>>16&3,s['cc'])
  if op in(4,20):return('eq',r[rs],r[rt])
  if op in(5,21):return('ne',r[rs],r[rt])
  if op==1:return('gez',r[rs])if rt in(1,3)else('ltz',r[rs])
  if op in(6,22):return('lez',r[rs])
  if op in(7,23):return('gtz',r[rs])
  raise AssertionError(('unsupported branch',pc,hex(word)))
 def live(self,s):return tuple(s['r'][16:24])+tuple(s['r'][28:32])+tuple(s['f'][20:])+(s['csr'],s['cc'],s['hi'],s['lo'])
 def run(self):
  pending=[(0,(initial(),initial()),[],[])];visits=set()
  while pending:
   pc,states,events,path=pending.pop()
   while pc<STOP:
    assert pc>=0;visits.add(pc);a,b=self.words[0][pc],self.words[1][pc];op=a>>26;assert b>>26==op,('opcode',pc)
    branch=op in(1,4,6,7,20,22,23)or(op==17 and a>>21&31==8)
    if branch:
     assert a&65535==b&65535 and(a>>16&31==b>>16&31 if op in(1,17)else True),('branch shape',pc)
     left=self.predicate(pc,states[0],a);right=self.predicate(pc,states[1],b);assert left==right,('predicate',pc,left,right)
     target=pc+1+((a&65535)-65536 if a&32768 else a&65535);likely=op in(20,22,23)or(op==1 and a>>16&31 in(2,3))or(op==17 and a>>16&2)
     for take in(False,True):
      branch_states=copy.deepcopy(states);branch_events=events[:]
      if take or not likely:self.execute(pc+1,branch_states,branch_events);visits.add(pc+1)
      pending.append((target if take else pc+2,branch_states,branch_events,path+[(pc,take)]))
     self.branches+=1;break
    self.execute(pc,states,events)
    if op==3:
     assert a==b,('call target',pc);self.execute(pc+1,states,events);visits.add(pc+1)
     target=((o.ENTRY+pc*4+4)&0xf0000000)|((a&0x3ffffff)<<2);assert target in(o.SIN,o.COS),hex(target)
     assert states[0]['r'][4]==states[1]['r'][4],('call argument',pc)
     assert self.live(states[0])==self.live(states[1]),('ABI live state',pc)
     assert states[0]['f']==states[1]['f'],('all floating registers at call',pc)
     events.append(('call',target,states[0]['r'][4]));call=len(events)
     for s in states:
      for index in(1,2,3,*range(4,16),24,25):s['r'][index]=('call-clobber',call,'r',index)
      for index in range(20):s['f'][index]=('call-clobber',call,'f',index)
      s['hi']=('call-clobber',call,'hi');s['lo']=('call-clobber',call,'lo');s['csr']=('call-clobber',call,'csr');s['cc']=('call-clobber',call,'cc')
     self.calls+=1;pc+=2
    else:pc+=1
   else:
    assert pc==STOP,('prefix exits elsewhere',pc)
    assert self.live(states[0])==self.live(states[1]),('join live state',path)
    assert states[0]['f']==states[1]['f'],('all floating registers at join',path)
    assert states[0]['r'][8]==states[1]['r'][8],('join last count',path)
    self.completed.append(dict(path=path,effects=len(events),calls=sum(e[0]=='call'for e in events),sha256=hashlib.sha256(repr(events).encode()).hexdigest()))
  return dict(paths=len(self.completed),visited_words=len(visits),call_boundaries=self.calls,branches=self.branches,strict_ordered_memory_FP_effects=True,ABI_saved_registers_at_every_call_and_join=True,all_floating_registers_at_every_call_and_join=True,join_last_count=True,domain='Symbolic initial registers and arbitrary synchronized load/provider results; only the first142word prefix. Caller temporaries may be renamed; no whole-function or literal full-register fault-state claim.',completed=self.completed)
def prefix_controls(truth,candidate):
 report=Pair(truth,candidate).run();controls=[]
 for name,index,mask in [('wrong-stack-store',14,4),('wrong-float-operand',43,1<<11),('wrong-call-argument',45,1<<21)]:
  bad=candidate[:];bad[index]^=mask
  try:Pair(truth,bad).run()
  except AssertionError:controls.append(name)
  else:raise AssertionError(('ineffective prefix negative',name))
 report.update(negative_controls=controls,source_installed=False,c_match_credit=0);return report

def fresh():
 left,right=initial(),initial();kept={0,8,*range(16,24),28,29,30,31}
 for index in range(1,32):
  if index not in kept:left['r'][index]=('dead-left',index);right['r'][index]=('dead-right',index)
 return left,right
def snapshot_check(truth,candidate):
 engine=Pair(truth,candidate);setup=fresh();events=[]
 for pc in(142,143,144):engine.execute(pc,setup,events)
 assert truth[145]>>26==candidate[145]>>26==6 and truth[145]&65535==candidate[145]&65535==29
 assert engine.predicate(145,setup[0],truth[145])==engine.predicate(145,setup[1],candidate[145])
 engine.execute(146,setup,events) # Ordinary blez executes the delay on both outcomes.
 empty=copy.deepcopy(setup);assert engine.live(empty[0])==engine.live(empty[1])and empty[0]['f']==empty[1]['f']
 engine.execute(147,setup,events)
 assert setup[0]['r'][5]==setup[1]['r'][5]==12
 assert setup[0]['r'][7]==setup[1]['r'][7]==0
 assert setup[0]['r'][10]==setup[1]['r'][9]and setup[0]['r'][6]==setup[1]['r'][6]
 # A generic row begins with only loop-live values related; dead temporaries
 # are deliberately different. This is independent of a finite row count.
 states=fresh()
 for side in states:
  side['r'][5]=12;side['r'][6]=('velocities-row',);side['r'][7]=('row-index',);side['r'][8]=('captured-count',)
 states[0]['r'][10]=('positions-row',);states[1]['r'][9]=('positions-row',)
 events=[]
 for pc in(148,149,150):engine.execute(pc,states,events)
 for component in range(3):
  for pc in range(151,169):engine.execute(pc,states,events)
  assert truth[169]>>26==candidate[169]>>26==5 and truth[169]&65535==candidate[169]&65535==0xffed
  condition=engine.predicate(169,states[0],truth[169]);assert condition==engine.predicate(169,states[1],candidate[169])
  assert condition==('ne',(component+1)*4,12),condition
  engine.execute(170,states,events)
 for pc in(171,172):engine.execute(pc,states,events)
 assert truth[173]>>26==candidate[173]>>26==5 and truth[173]&65535==candidate[173]&65535==0xffe6
 assert engine.predicate(173,states[0],truth[173])==engine.predicate(173,states[1],candidate[173])
 engine.execute(174,states,events)
 for index in(5,6,7,8):assert states[0]['r'][index]==states[1]['r'][index],('backedge live',index)
 assert states[0]['r'][10]==states[1]['r'][9],('positions-row backedge',states[0]['r'][10],states[1]['r'][9])
 assert engine.live(states[0])==engine.live(states[1])and states[0]['f']==states[1]['f']
 return dict(prefix_words=[142,175],generic_outer_row_inductive=True,inner_components_exactly_three=True,empty_path_checked=True,strict_ordered_memory_FP_effects=True,all_floating_and_ABI_saved_registers_at_exit=True,loop_live_relation_reestablished=True,row_effect_count=len(events),row_effects_sha256=hashlib.sha256(repr(events).encode()).hexdigest(),scope='Snapshot setup, empty branch and generic row only. Composition requires the qualified142word prefix; reverse-loop and audio remain outside this proof.')
def snapshot_controls(truth,candidate):
 report=snapshot_check(truth,candidate);controls=[]
 for name,index,mask in [('wrong-component-load',157,4),('wrong-row-stride',172,4),('wrong-component-bound',147,4)]:
  bad=candidate[:];bad[index]^=mask
  try:snapshot_check(truth,bad)
  except AssertionError:controls.append(name)
  else:raise AssertionError(('ineffective snapshot negative',name))
 report.update(negative_controls=controls,source_installed=False,c_match_credit=0);return report
