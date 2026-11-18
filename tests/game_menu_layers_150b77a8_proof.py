"""Complete symbolic descriptor/frame/provider relation and independent schedule proof."""
from pathlib import Path
from copy import deepcopy
import json,struct
from tools.tests import game_owner_record_151b09bc_proof as parent
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
g=parent.g;e=g.e;ENTRY=0x150B77A8;FREE,CREATE=0x1516972C,0x15169968
from tools.experiments import game_menu_layers_150b77a8_match as source
p=source.OUT;f=source.FROZEN
class State(g.State):
 def __init__(self):
  super().__init__('common');self.mem={off:('PRIVATE_ENTRY',off)for off in range(-96,16)};self.retained=False
 def load(self,address,size,pool=b''):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0 and -96<=off and off+size<=16
   return g.join([self.mem[off+i]for i in range(size)])
  return super().load(address,size,pool)
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):
   off=address[1];assert size in(1,2,4)and off%size==0 and -96<=off and off+size<=16
   for i in range(size):self.mem[off+i]=g.byte(value,8*(size-i-1))
  else:super().store(address,size,value)
 def frame(self):return tuple(self.mem[i]for i in range(-96,16))
class Program(parent.Program):
 def __init__(self,words,terms):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
 def call(self,s,target):
  assert target in(FREE,CREATE)and s.r[29]==('STACK',-96)
  arg=s.r[4];ordinal=sum(s.calls.values());s.calls[target]+=1
  if target==CREATE:
   assert arg==('STACK',-60)
   observed=tuple(s.mem[i]for i in range(-60,0));s.retained=True
  else:e.plain(arg);observed=()
  s.trace.append(('CALL',target,arg,observed,s.fcsr));s.trace.append(('FRAME',s.frame()));s.epoch+=1
  if s.retained:
   for off in range(-60,0):s.mem[off]=('PROVIDER_BYTE',ordinal,off)
  for i in range(4):s.store(('STACK',-96+4*i),4,('CALL_HOME',ordinal,i))
  for reg in(1,2,3,*range(4,16),24,25):s.r[reg]=('CALLER',ordinal,reg)
  for reg in range(20):s.f[reg]=('CALLER_FP',ordinal,reg)
  s.r[2]=('RESULT',target,ordinal);s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal)
def programs():
 lookup={v[1]:v[2][1]for v in symbol_rows((f/'conker/build/conker.us.elf').read_bytes())}
 raw=bound_blob(*payload(p/'owner.o','func_150B77A8'),lookup);retail=list(struct.unpack('>93I',(p/'retail.bin').read_bytes()))
 return raw,retail
def derive(words,refs=None):
 assert len(words)==93
 if refs is None:assert words==source.PIN['bound_source_words']
 else:
  assert __import__('hashlib').sha256(struct.pack('>93I',*words)).hexdigest()==source.PIN['raw_sha256']
  assert refs=={int(k):[tuple(v)for v in values]for k,values in source.PIN['refs'].items()}
 order=list(range(93));order[16:22]=[21,16,17,18,19,20]
 result=[words[i]for i in order]
 if refs is None:return result
 return result,{4*i:refs[4*old]for i,old in enumerate(order)if 4*old in refs}
def schedule(words):
 block=words[16:22];assert block[-1]>>26==15 and block[-1]>>16&31==1
 writes=set();reads=set()
 for w in block[:-1]:
  assert w>>26==9
  reads.add(w>>21&31);writes.add(w>>16&31)
 assert 1 not in reads|writes and 29 not in writes and 31 not in writes
 # LUI's output is disjoint from all five ADDIU inputs/outputs. Moving it
 # earlier preserves every register bit and causes no memory, FP or call event.
 assert writes=={14,15,24,25,8}
 before=[('REGISTER',i)for i in range(32)];before[0]=0
 def run(order):
  registers=before[:]
  for index in order:
   w=block[index];op,rs,rt=w>>26,w>>21&31,w>>16&31;imm=((w&65535)^32768)-32768
   registers[rt]=(w&65535)<<16 if op==15 else e.add(registers[rs],imm)
  return registers
 assert run(range(6))==run((5,0,1,2,3,4))
 return dict(instructions=6,permutation=[5,0,1,2,3,4],all_GPR_bits_preserved=True,no_memory_FP_call_or_branch_operations=True)
def prove(raw,retail):
 assert derive(raw)==retail and all(raw[i]==retail[i]for i in range(93)if not 16<=i<22)
 local=schedule(raw);terms=Terms();answers=[];coverage=[]
 for words in(raw,retail):
  program=Program(words,terms);paths=program.paths(State());result={}
  for key,s in paths.items():
   assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',)
   assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))and s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
   result[key]=(s.trace,s.read_set,s.frame(),s.fcsr)
  answers.append(result);coverage.append(len(program.seen))
 assert answers[0]==answers[1]
 return dict(passes=True,paths=len(answers[0]),coverage=coverage,words=93,frame_bytes_compared=112,arbitrary_retained_descriptor_and_public_provider_mutations=True,ordered_public_effects_and_FCSR=True,schedule=local,c_match_credit=0)
def main(raw=None,retail=None):
 if raw is None:raw,retail=programs()
 report=prove(raw,retail);(p/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
