"""Scoped abstract proof for arbitrary FP values with disabled FP traps.

Each FP operator has opaque value/exception/predicate functions. Sticky flags
combine by bitwise OR (represented as a set); Cause is replaced per FP operation.
This permits checking independent compare/subtract scheduling only at actual
provider and return boundaries. It is not an IEEE emulator, SMT proof, enabled
exception/fault-prefix proof, or proof of all raw scratch registers.
"""
from pathlib import Path
import hashlib,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_timed_phase_update_15108658_match as p
o=p.OUT
from tools.tests import game_radial_angle_150c16c0_symbolic as core
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=0x15108658;POINT=0x30000;SCRATCH=0x50000;RNG=0x150ada68;DELTA,EDGE,RATE=0x800be9a4,0x800a2460,0x800a2464
symbols=dict(func_150ADA68=RNG,D_800BE9A4=DELTA,D_800A2460=EDGE,D_800A2464=RATE)
RM=('initial-rounding-mode',);initial=lambda n:('initial-float-bits',n)
sub=lambda a,b:('sub.s',a,b,RM)
provider_rate=core.join([('provider-public-byte',1,RATE+i)for i in range(4)])
KEYS=[('lt',initial('remaining'),initial('edge')),('lt',sub(initial('total'),initial('remaining')),initial('edge')),('lt',initial('remaining'),initial('transition')),('lt',sub(initial('total'),initial('remaining')),initial('transition')),('eq',0,initial('cooldown')),('lt',initial('cooldown'),initial('limit')),('lt',sub(0x41300000,initial('cooldown')),initial('limit')),('lt',sub(initial('cooldown'),initial('delta')),0),('lt',sub(initial('remaining'),initial('delta')),0),('lt',('provider-float-result',1),provider_rate)]
class Machine(core.Machine):
 def __init__(self,words,decisions):
  super().__init__(words);self.code=dict(zip(range(ENTRY,ENTRY+len(words)*4,4),words));self.r[4:6]=[POINT,SCRATCH];self.decisions=decisions;self.condition=False;self.rm=RM;self.sticky=frozenset({('initial-sticky-flags',)});self.cause=('initial-Cause',);self.fp_arithmetic=[];self.public_writes=[];self.provider_states=[];self.predicate_keys=[]
  self.public_addresses=set(range(POINT-8,POINT+204))|set(range(SCRATCH-8,SCRATCH+24))|set(range(DELTA,DELTA+4))|set(range(EDGE,EDGE+4))|set(range(RATE,RATE+4))
  for a in self.public_addresses:self.mem[a]=('initial-public-byte',a)
  for at,name in[(0xa8,'remaining'),(0xac,'total'),(0xb0,'transition'),(0xb4,'edge'),(0xb8,'cooldown')]:self.store(POINT+at,4,initial(name),False)
  for at,name in[(DELTA,'delta'),(EDGE,'limit'),(RATE,'rate')]:self.store(at,4,initial(name),False)
 def store(self,a,n,v,record=True):
  super().store(a,n,v,record)
  if record and not core.STACK-256<=a<core.STACK+128:self.public_writes.append((a,n,core.mask(v,(1<<(8*n))-1)))
 def execute(self,pc):
  w=self.code[pc];op,fmt,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in(1,50,60):
   self.visits.append(pc);a,b=self.f[fs],self.f[rt]
   if fn==1:
    value=('sub.s',a,b,self.rm);self.f[fd]=value;self.fp_arithmetic.append(value);flags=('sub-exceptions',a,b,self.rm)
   else:
    key=('eq'if fn==50 else'lt',a,b);self.predicate_keys.append(key);self.condition=bool(self.decisions>>KEYS.index(key)&1)if key in KEYS else False;flags=('compare-exceptions',*key)
   self.sticky|={flags};self.cause=flags
  else:super().execute(pc)
 def public(self):return tuple((a,self.mem.get(a,('absent',a)))for a in sorted(self.public_addresses))
 def private(self):return tuple((a,self.mem.get(a,('initial-private-byte',a)))for a in range(core.STACK-256,core.STACK+128))
 def fp_state(self):return self.rm,self.sticky,self.cause,self.condition
 def call(self,target):
  assert target==RNG;self.provider_states.append((target,(),self.public(),self.private(),self.fp_state(),tuple(self.r[i]for i in(*range(16,24),28,29,30,31)),tuple(self.f[20:])));self.calls.append(target);self.epoch+=1
  for a in self.public_addresses:self.mem[a]=('provider-public-byte',self.epoch,a)
  for i in(1,2,3,*range(4,16),24,25):self.r[i]=('provider-GPR',self.epoch,i)
  for i in range(20):self.f[i]=('provider-FPR',self.epoch,i)
  self.r[2]=('provider-result',self.epoch);self.f[0]=('provider-float-result',self.epoch);self.rm=('provider-rounding-mode',self.epoch);self.sticky=frozenset({('provider-sticky-flags',self.epoch)});self.cause=('provider-Cause',self.epoch);self.condition=False;self.lo=self.hi=('provider-HILO',self.epoch)
  for i in range(4):self.store(self.r[29]+4*i,4,('provider-home',self.epoch,i),False)
 def run(self):
  pc=ENTRY
  for _ in range(200):
   if pc==core.RETURN:break
   w=self.code[pc];op,rs,rt,fn=w>>26,w>>21&31,w>>16&31,w&63
   if op==3:self.visits.append(pc);self.r[31]=pc+8;self.execute(pc+4);self.call(((pc+4)&0xf0000000)|((w&0x3ffffff)<<2));pc+=8
   elif op in(4,5,20,21)or op==17 and rs==8:
    if op==17:taken=self.condition==bool(rt&1);likely=bool(rt&2)
    else:
     a,b=self.r[rs],self.r[rt];assert isinstance(a,int)and isinstance(b,int),(hex(pc),a,b);taken=(a==b)if op in(4,20)else(a!=b);likely=op in(20,21)
    self.visits.append(pc)
    if taken or not likely:self.execute(pc+4)
    pc=pc+4+(((w&65535)^32768)-32768)*4 if taken else pc+8
   elif op==0 and fn==8:target=self.r[rs];self.visits.append(pc);self.execute(pc+4);pc=target
   else:self.execute(pc);pc+=4
  else:raise AssertionError('Unbounded symbolic path')
  assert self.r[29]==core.STACK and all(self.r[i]==self.before[i]for i in(*range(16,24),28,30,31))and self.f[20:]==self.before_f[20:]
  return self
def observe(m):return m.public(),m.public_writes,m.private(),m.provider_states,m.r[2],tuple(m.r[i]for i in(*range(16,24),28,29,30,31)),tuple(m.f[20:]),m.fp_state(),m.lo,m.hi,m.fp_arithmetic
def main():
 raw,rr=payload(o/'selected-final/owner-candidate.o','func_15108658');truth,tr=payload(o/'original-target.o','func_15108658');ws=bound_blob(raw,rr,symbols);retail=bound_blob(truth,tr,symbols);assert len(ws)==len(retail)==105;paths=set();seen=set();original_seen=set()
 for decisions in range(1<<len(KEYS)):
  a,b=Machine(ws,decisions).run(),Machine(retail,decisions).run();assert observe(a)==observe(b),('observer mismatch',decisions)
  paths.add(tuple(b.predicate_keys));seen.update(a.visits);original_seen.update(b.visits)
 controls=[]
 bad36=bound_blob(bytes.fromhex(p.MANIFEST['short_circuit_control_hex']),{int(k):[tuple(v)for v in rows]for k,rows in p.MANIFEST['short_circuit_control_relocations'].items()},symbols)
 modifications=[('short-circuited-cooldown-subtraction',bad36)]
 bad=ws[:];bad=[0x24020002 if w==0x24020001 else w for w in bad];modifications.append(('wrong-active-return',bad))
 bad=ws[:];i=next(i for i,w in enumerate(bad)if w==0x2418ffff);bad[i]=0x2418fffe;modifications.append(('wrong-display-state',bad))
 bad=ws[:];i=max(i for i,w in enumerate(bad)if w==0x3c014130);bad[i]=0x3c014140;modifications.append(('wrong-cooldown-reset',bad))
 for name,bad in modifications:
  rejected=0;first=None
  for decisions in range(1<<len(KEYS)):
   a,b=Machine(bad,decisions).run(),Machine(retail,decisions).run()
   if observe(a)!=observe(b):rejected+=1;first=decisions if first is None else first
  assert rejected,name;controls.append(dict(name=name,all1024_executions_complete=True,rejected_cases=rejected,first_decisions=first))
 q=dict(raw_sha256=hashlib.sha256(raw).hexdigest(),words=105,frame=40,predicate_assignments=1<<len(KEYS),independent_predicate_keys=len(KEYS),distinct_predicate_paths=len(paths),retail_executed_words=len(original_seen),raw_executed_words=len(seen),arbitrary_initial_record_float_bits_and_provider_public_byte_epochs=True,ordered_arithmetic_operators_and_operands_preserved=True,compare_subtract_interleaving_may_differ=True,sticky_exceptions_OR_and_last_Cause_and_condition_equal_at_observers=True,provider_ABI_saved_state_and_complete_private_frame_equal=True,public_RAM_and_ordered_writes_and_integer_return_equal=True,no_commutative_arithmetic_operand_rewrite_or_private_frame_map=True,FP_traps_disabled_and_existing_predicate_exception_functions_assumed=True,not_IEEE_or_SMT_or_fault_prefix_or_raw_scratch_register_proof=True,effective_controls=controls,source_installed=p.installed(),matching_credit=0)
 (o/'symbolic.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=='__main__':main()
