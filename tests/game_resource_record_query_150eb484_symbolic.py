"""Exact changed-region observer proof and explicit private-frame bijection.

Provider results/effects are opaque tokens. The loop induction is finite (0..4).
Provider stack introspection, asynchronous observers, hardware and raw faults
are outside this proof. No pointer to this function's frame escapes to a call.
"""
from pathlib import Path
import json,struct,sys
sys.path.insert(0,str(Path.cwd()));from tools.experiments import game_resource_record_query_150eb484_match as packet
o=packet.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
def add(a,b):
 if isinstance(a,int)and isinstance(b,int):return(a+b)&0xffffffff
 if a==0:return b
 if b==0:return a
 return ('add',*sorted((a,b),key=repr))
def region(raw,refs,hit,i):
 words=struct.unpack('>100I',raw);regs=['r'+str(n)for n in range(32)];regs[0]=0;regs[2]=('hit',)if hit else 0;regs[16]='cursor';regs[17]=i;regs[18]='saved-index';regs[19]='saved-byte-offset';regs[21]='global-address';regs[29]='private-SP'
 memory={add('private-SP',68):'context','global-address':('base',0)};calls=[];writes=[];pc=0x88;steps=0
 def execute(at):
  w=words[at//4];op=w>>26;rs,rt,rd=w>>21&31,w>>16&31,w>>11&31;imm=((w&65535)^32768)-32768
  if w==0:return
  if op==9:regs[rt]=add(regs[rs],imm)
  elif op==0 and w&63==37:
   assert regs[rt]==0 or regs[rs]==0;regs[rd]=regs[rs]if regs[rt]==0 else regs[rt]
  elif op==0 and w&63==33:regs[rd]=add(regs[rs],regs[rt])
  elif op==35:regs[rt]=memory[add(regs[rs],imm)]
  elif op==43:
   address=add(regs[rs],imm);memory[address]=regs[rt];writes.append((address,regs[rt]))
  elif op==10:
   assert isinstance(regs[rs],int);regs[rt]=int(regs[rs]<imm)
  else:raise AssertionError(('unexpected straight instruction',hex(at),hex(w)))
  regs[0]=0
 while pc not in (0x60,0xd0,0x160):
  steps+=1;assert steps<40,(pc,steps);w=words[pc//4];op=w>>26;rs,rt=w>>21&31,w>>16&31
  if op==3:
   execute(pc+4);bindings=refs[pc];assert len(bindings)==1 and bindings[0][0]=='R_MIPS_26';name=bindings[0][1];count={'func_150A2864':2,'func_150EBC80':3}[name];calls.append((name,tuple(regs[4:4+count]),tuple(writes)))
   # An opaque status provider can change both the base and selected field.
   memory['global-address']=('base',len(calls));memory[add('context',744)]=('provider-selected',len(calls))
   for n in (1,2,3,*range(4,16),24,25,31):regs[n]=('clobber',len(calls),n)
   pc+=8
  elif op in (4,5):
   equal=regs[rs]==regs[rt];take=equal if op==4 else not equal;offset=((w&65535)^32768)-32768;execute(pc+4);pc=pc+4+offset*4 if take else pc+8
  else:execute(pc);pc+=4
 return dict(end=pc,loop_registers=regs[16:24],result=regs[2]if pc==0x160 else None,calls=calls,writes=writes,base=memory['global-address'])
def main():
 raw,refs=payload(o/'selected-1188E0.o','func_150EB484');truth,tr=payload(o/'original-target.o','func_150EB484');a,z=struct.unpack('>100I',raw),struct.unpack('>100I',truth)
 pins={i*4 for i in range(100)if a[i]!=z[i]or refs.get(4*i,[])!=tr.get(4*i,[])}
 assert pins=={0,0x50,0x54,*range(0x88,0xcc,4),0xd8,0xdc,0x18c}
 assert a[0]==0x27bdffb8 and z[0]==0x27bdffb0 and a[-1]==0x27bd0048 and z[-1]==0x27bd0050
 # Independent address materializations commute with distinct destinations.
 for x,y in ((0x50,0x54),(0xd8,0xdc)):
  assert a[x//4]==z[y//4]and a[y//4]==z[x//4]
  assert refs[x]==tr[y]and refs[y]==tr[x]
  assert a[x//4]>>26==9 and a[y//4]>>26==9
  assert a[x//4]>>21&31==a[x//4]>>16&31 and a[y//4]>>21&31==a[y//4]>>16&31
  assert a[x//4]>>16&31!=a[y//4]>>16&31
 rows=[]
 for hit in (False,True):
  for i in range(4):
   before,after=region(raw,refs,hit,i),region(truth,tr,hit,i);assert before==after,(hit,i,before,after);rows.append(dict(hit=hit,loop_index=i,exit=hex(before['end']),provider_calls=len(before['calls'])))
 sp=[]
 for i,w in enumerate(a):
  op=w>>26;rs,rt,rd=w>>21&31,w>>16&31,w>>11&31
  if rs!=29:continue
  if op in (35,43):offset=((w&65535)^32768)-32768;assert 0<=offset<=68 and offset%4==0;sp.append(offset)
  else:assert op==9 and rt==29 and i in (0,99),'private frame pointer escapes'
 assert set(sp)=={24,28,32,36,40,44,48,52,56,60,68}
 q=dict(exact_changed_region_cases=8,opaque_provider_effects_and_arguments_and_writes_equal=True,loop_induction_values=[0,1,2,3,4],independent_address_materialization_pairs=2,private_frame_translation_bytes=8,active_stack_offsets=sorted(set(sp)),raw_active_frame_bytes=72,retail_frame_bytes=80,private_pointer_not_passed_to_provider=True,non_escaping_active_stack_bijection=True,unused_retail_frame_tail_bytes=8,rows=rows,stack_introspection_async_hardware_and_raw_faults_not_qualified=True,source_installed=packet.installed(),matching_credit=0)
 (o/'symbolic.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=='__main__':main()
