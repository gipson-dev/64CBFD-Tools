"""Scoped symbolic o32 trace for this fixed-one-iteration callback only."""
from pathlib import Path
import hashlib,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_radial_angle_150c16c0_match as p
o=p.OUT;ENTRY=0x150c16c0;STACK=0x40000;RETURN=0x7fff0000
RNG,ANGLE,FRNG,FACTORY=0x150ada20,0x151423d8,0x150ada68,0x15147da0
u=lambda x:x&0xffffffff
def add(a,b):
 if isinstance(a,int)and isinstance(b,int):return u(a+b)
 terms=[];constant=0
 for v in(a,b):
  for w in(v[1:]if isinstance(v,tuple)and v[0]=='add'else(v,)):
   if isinstance(w,int):constant=u(constant+w)
   else:terms.append(w)
 if constant:terms.append(constant)
 return 0 if not terms else terms[0]if len(terms)==1 else('add',*sorted(terms,key=repr))
def mask(x,n):
 if isinstance(x,int):return x&n
 if n==0:return 0
 if isinstance(x,tuple)and x[0]=='and':return mask(x[1],x[2]&n)
 if isinstance(x,tuple)and x[0]=='sx16'and n<=65535:return mask(x[1],n)
 if isinstance(x,tuple)and x[0]=='add'and n<=65535:x=('add',*[v[1]if isinstance(v,tuple)and v[0]=='sx16'else v for v in x[1:]])
 return x if n==0xffffffff else('and',x,n)
def shift(x,n,right=False):
 if n==0:return x
 if isinstance(x,int):return u(((x^0x80000000)-0x80000000)>>n)if right else u(x<<n)
 if right and isinstance(x,tuple)and x[0]=='shl'and x[2]==n==16:return('sx16',x[1])
 return('sar'if right else'shl',x,n)
def byte(x,at):return(x>>(8*at))&255 if isinstance(x,int)else('byte',x,at)
def join(v):
 if all(isinstance(x,int)for x in v):return int.from_bytes(bytes(v),'big')
 n=len(v)
 if all(isinstance(x,tuple)and x[0]=='byte'and x[1]==v[0][1]and x[2]==n-1-i for i,x in enumerate(v)):return mask(v[0][1],(1<<(8*n))-1)
 return('bytes',*v)
class Machine:
 def __init__(self,words):
  self.code=dict(zip(range(ENTRY,ENTRY+len(words)*4,4),words));self.r=[('r',i)for i in range(32)];self.r[0]=0;self.r[29]=STACK;self.r[31]=RETURN;self.f=[('f',i)for i in range(32)];self.before=self.r[:];self.before_f=self.f[:];self.mem={};self.pairs={};self.events=[];self.calls=[];self.branches=[];self.visits=[];self.epoch=0;self.lo=self.hi=None
  for i in range(4):self.r[4+i]=('arg',i)
  for i in range(4,15):self.store(STACK+4*i,4,('arg',i),False)
 def store(self,a,n,v,record=True):
  assert isinstance(a,int)
  assert not any(a<base+8 and base<a+n for base in self.pairs),'Unsupported partial FP-pair overwrite'
  if record:self.events.append(('W',a,n,v))
  for i in range(n):self.mem[a+i]=byte(v,n-1-i)
 def load(self,a,n):
  assert isinstance(a,int);v=join([self.mem.get(a+i,('memory-byte',self.epoch,a+i))for i in range(n)]);self.events.append(('R',a,n,v));return v
 def execute(self,pc):
  w=self.code[pc];self.visits.append(pc);op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;imm=((w&65535)^32768)-32768
  if w==0:return
  if op==0:
   if fn==0:self.r[rd]=shift(self.r[rt],sa)
   elif fn==3:self.r[rd]=shift(self.r[rt],sa,True)
   elif fn==0x21:self.r[rd]=add(self.r[rs],self.r[rt])
   elif fn==0x25:
    a,b=self.r[rs],self.r[rt];assert a==0 or b==0 or isinstance(a,int)and isinstance(b,int);self.r[rd]=b if a==0 else a if b==0 else a|b
   elif fn==0x1b:
    divisor=self.r[rt];assert isinstance(divisor,int)and divisor!=0;self.hi=('umod',self.r[rs],divisor);self.lo=('udiv',self.r[rs],divisor)
   elif fn==0x10:self.r[rd]=self.hi
   elif fn==0x12:self.r[rd]=self.lo
   else:raise AssertionError(('SPECIAL',hex(pc),hex(w)))
  elif op==9:self.r[rt]=add(self.r[rs],u(imm))
  elif op==12:self.r[rt]=mask(self.r[rs],w&65535)
  elif op==13:
   assert isinstance(self.r[rs],int);self.r[rt]=self.r[rs]|(w&65535)
  elif op==15:self.r[rt]=(w&65535)<<16
  elif op in(35,36,49):
   a=add(self.r[rs],u(imm));v=self.load(a,1 if op==36 else 4)
   if op==49:self.f[rt]=v
   else:self.r[rt]=v
  elif op in(40,41,43,57):self.store(add(self.r[rs],u(imm)),{40:1,41:2,43:4,57:4}[op],self.f[rt]if op==57 else self.r[rt])
  elif op==61:
   a=add(self.r[rs],u(imm));v=('fp-pair',self.f[rt],self.f[rt+1]);self.pairs[a]=v;self.events.append(('W',a,8,v))
  elif op==53:
   a=add(self.r[rs],u(imm));v=self.pairs[a];self.events.append(('R',a,8,v));self.f[rt],self.f[rt+1]=v[1:]
  elif op==17:
   if rs==4:self.f[rd]=self.r[rt]
   elif rs==16:
    fd=w>>6&31
    if fn==6:self.f[fd]=self.f[rd]
    elif fn==7:self.f[fd]=('fneg',self.f[rd]);self.events.append(('FP',self.f[fd]))
    elif fn in(0,2):v=('fadd'if fn==0 else'fmul',self.f[rd],self.f[rt]);self.f[fd]=v;self.events.append(('FP',v))
    else:raise AssertionError(('COP1',hex(pc),hex(w)))
   else:raise AssertionError(('COP1FMT',hex(pc),hex(w)))
  else:raise AssertionError(('OP',hex(pc),hex(w)))
  self.r[0]=0
 def call(self,target):
  n=0 if target in(RNG,FRNG)else 1 if target==ANGLE else 15 if target==FACTORY else None;assert n is not None
  args=tuple(self.r[4+i]if i<4 else self.load(self.r[29]+4*i,4)for i in range(n));self.calls.append((target,args));self.events.append(('CALL',target,args));self.epoch+=1
  for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=('call-clobber',self.epoch,'r',reg)
  for reg in range(20):self.f[reg]=('call-clobber',self.epoch,'f',reg)
  self.r[2]=('call-result',self.epoch);self.f[0]=('call-float-result',self.epoch)
  self.mem={a:v for a,v in self.mem.items()if STACK-296<=a<STACK}
  if target==FACTORY:
   for at,n in((args[0],28),(args[1],32),(args[11],32)):
    assert isinstance(at,int)and STACK-296<=at and at+n<=STACK
    assert not any(at<base+8 and base<at+n for base in self.pairs)
    for i in range(n):self.mem.pop(at+i,None)
  for i in range(4):self.store(self.r[29]+4*i,4,('outgoing-home',self.epoch,i),False)
 def run(self):
  pc=ENTRY
  for steps in range(400):
   if pc==RETURN:break
   w=self.code[pc];op,rs,rt,fn=w>>26,w>>21&31,w>>16&31,w&63
   if op==3:
    self.visits.append(pc);self.r[31]=pc+8;self.execute(pc+4);self.call(((pc+4)&0xf0000000)|((w&0x3ffffff)<<2));pc+=8
   elif op in(4,5):
    a,b=self.r[rs],self.r[rt];assert isinstance(a,int)and isinstance(b,int),(pc,a,b);taken=(a==b)if op==4 else(a!=b);self.branches.append((op,taken));self.visits.append(pc);self.execute(pc+4);pc=pc+4+((((w&65535)^32768)-32768)*4)if taken else pc+8
   elif op==0 and fn==8:
    target=self.r[rs];assert isinstance(target,int);self.visits.append(pc);self.execute(pc+4);pc=target
   else:self.execute(pc);pc+=4
  else:raise AssertionError('Unbounded symbolic execution')
  assert self.r[2]==1 and self.r[29]==STACK and all(self.r[i]==self.before[i]for i in(*range(16,24),28,30,31))and self.f[20:]==self.before_f[20:];return self
from unittest.mock import patch
def main():
 s=sys.modules[__name__];fn=p.FUNCTION
 raw,rr=s.payload(o/'selected-final/owner-candidate.o',fn);truth,tr=s.payload(o/'original-target.o',fn)
 base={name:int(name.split('_',1)[1],16)for refs in(rr,tr)for pairs in refs.values()for _,name in pairs}
 def compare(symbols,entry=s.ENTRY):
  with patch.multiple(s,ENTRY=entry,RNG=symbols['func_150ADA20'],ANGLE=symbols['func_151423D8'],FRNG=symbols['func_150ADA68'],FACTORY=symbols['func_15147DA0']):
   a=s.Machine(s.bound_blob(raw,rr,symbols)).run();b=s.Machine(s.bound_blob(truth,tr,symbols)).run();assert a.events==b.events and a.branches==b.branches;return a,b
 a,b=compare(base);valid=0
 for region,low in[(0x150c16c0,0),(0x250c16c0,0x7ff8),(0x350c16c0,0x8000),(0x450c16c0,0xfff8)]:
  calls=sorted(n for n in base if n.startswith('func_'));data=sorted(n for n in base if n.startswith('D_'));symbols={n:(region&0xf0000000)+0x210000+0x20000*i+low for i,n in enumerate(calls)};symbols.update({n:0x80100000+0x20000*i+low for i,n in enumerate(data)});compare(symbols,region);valid+=1
 ws=s.bound_blob(raw,rr,base);model=s.Machine(ws).run();reference=s.Machine(s.bound_blob(truth,tr,base)).run();controls=[]
 mutations=[('loop-count',next(i for i,w in enumerate(ws)if w==0x24110001),0x24110002),('slot-home',next(i for i,w in enumerate(ws)if w==0x93b40163),0x93b4015f),('payload-kind',next(i for i,w in enumerate(ws)if w==0x240d000a),0x240d000b),('factory-control',next(i for i,w in enumerate(ws)if w==0x24180005),0x24180004)]
 i=next(i for i,w in enumerate(ws)if w>>26==17 and w>>21&31==16 and w&63==2);mutations.append(('multiply-to-add',i,ws[i]&~63))
 for name,i,w in mutations:
  changed=ws[:];changed[i]=w;m=s.Machine(changed).run();assert m.events!=reference.events or m.branches!=reference.branches;controls.append(dict(name=name,supported_execution=True,rejected_by_trace_comparison=True))
 symbols=dict(base);symbols['D_800A01F4']=symbols['D_800A01F8'];m=s.Machine(s.bound_blob(raw,rr,symbols)).run();assert m.events!=reference.events;controls.append(dict(name='coefficient-binding',supported_execution=True,rejected_by_trace_comparison=True))
 q=dict(events=len(model.events),calls=len(model.calls),fixed_branch_outcomes=model.branches,raw_executed_words=len(set(model.visits)),retail_executed_words=len(set(reference.visits)),rebased_proofs=valid,effective_supported_trace_controls=controls,arbitrary_provider_results_and_public_memory_epochs=True,factory_may_overwrite_all_three_bounded_records=True,complete_saved_register_pair_and_return_check=True,source_installed=p.installed(),matching_credit=0)
 (o/'symbolic-controls.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q

if __name__=='__main__':main()
