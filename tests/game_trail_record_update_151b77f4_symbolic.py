"""Check the closed integer scheduling window with arbitrary aliased memory."""
from pathlib import Path
import hashlib,json,struct,sys
sys.path.insert(0,str(Path.cwd()))
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments import game_trail_record_update_151b77f4_match as target_packet
o=target_packet.OUT;fn='func_151B77F4';START,END=0xec,0x11c
def const(v):return('constant',v&0xffffffff)
def add(a,b):
 if a==const(0):return b
 if b==const(0):return a
 if a[0]==b[0]=='constant':return const(a[1]+b[1])
 return('add32',a,b)
def execute(words):
 regs=[('register',i)for i in range(32)];regs[0]=const(0);memory=('initial_memory',)
 for word in words:
  op,rs,rt,rd,sa,fun=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63;immediate=((word&65535)^32768)-32768
  if op in(32,35,36,43):
   address=add(regs[rs],const(immediate))
   if op==43:memory=('store32be',memory,address,regs[rt])
   elif op==35:regs[rt]=('load32be',memory,address)
   else:
    value=('load8',memory,address);regs[rt]=('sign8',value)if op==32 else value
  elif op==9:regs[rt]=add(regs[rs],const(immediate))
  elif op==0 and fun==0:regs[rd]=('shift_left32',regs[rt],sa)
  elif op==0 and fun==33:regs[rd]=add(regs[rs],regs[rt])
  else:raise AssertionError(('unsupported instruction',hex(word)))
  regs[0]=const(0)
 return tuple(regs),memory
def evaluate(expr,registers,memory):
 tag=expr[0]
 if tag=='constant':return expr[1]
 if tag=='register':return registers[expr[1]]
 if tag=='initial_memory':return memory
 if tag=='add32':return(evaluate(expr[1],registers,memory)+evaluate(expr[2],registers,memory))&0xffffffff
 if tag=='shift_left32':return(evaluate(expr[1],registers,memory)<<expr[2])&0xffffffff
 if tag=='sign8':return((evaluate(expr[1],registers,memory)^128)-128)&0xffffffff
 if tag in('load8','load32be'):
  m=evaluate(expr[1],registers,memory);address=evaluate(expr[2],registers,memory);return int.from_bytes(bytes(m.get((address+i)&0xffffffff,0)for i in range(1 if tag=='load8'else 4)),'big')
 if tag=='store32be':
  m=dict(evaluate(expr[1],registers,memory));address=evaluate(expr[2],registers,memory);value=evaluate(expr[3],registers,memory)
  for i in range(4):m[(address+i)&0xffffffff]=(value>>(24-8*i))&255
  return m
 raise AssertionError(tag)
def concrete(state,head):
 regs=[0xa5000000+i for i in range(32)];regs[0]=0;regs[29]=0x1000;m={}
 def put(a,v,n=4):
  for i in range(n):m[a+i]=(v>>(8*(n-i-1)))&255
 put(0x101c,0x30010);put(0x1048,0x30000);put(0x1040,0x30014);put(0x3002e,head,1);put(0x30010,0x11111111);put(0x30014,0x22222222)
 return tuple(evaluate(v,regs,m)for v in state[0]),evaluate(state[1],regs,m)
def main():
 raw,refs=payload(o/'selected-owner.o',fn);truth,trefs=payload(o/'original-target.o',fn);assert refs==trefs and len(raw)==len(truth)==420
 assert raw[:START]==truth[:START]and raw[END:]==truth[END:];a=list(struct.unpack('>12I',raw[START:END]));b=list(struct.unpack('>12I',truth[START:END]));left,right=execute(a),execute(b);assert left==right
 controls=[]
 for name,old,new in(('unsigned-head',0x80cd002e,0x90cd002e),('wrong-record-stride',0x000d7080,0x000d70c0),('wrong-position-home',0x8fa5001c,0x8fa50018),('wrong-opacity',0x240a00ff,0x240a00fe),('wrong-record-store',0xac410000,0xac410004)):
  wrong=list(b);assert wrong.count(old)==1,name;wrong[wrong.index(old)]=new;state=execute(wrong);assert state!=right;witnesses=[head for head in(0,127,255)if concrete(state,head)!=concrete(right,head)];assert witnesses,name;controls.append(dict(name=name,complete_supported_execution=True,symbolic_inequality_and_concrete_witness=True,witness_head=witnesses[0]))
 wrong=list(b);wrong[9],wrong[10]=wrong[10],wrong[9];state=execute(wrong);assert state!=right and concrete(state,0)!=concrete(right,0);controls.append(dict(name='position-reload-before-overlapping-store',complete_supported_execution=True,symbolic_inequality_and_concrete_witness=True,witness_head=0))
 q=dict(window=[hex(START),hex(END)],window_words=12,guard_words=11,all32_GPRs_and_entire_functional_memory_identical=True,arbitrary_initial_registers_and_byte_memory=True,no_nonalias_assumptions=True,all_memory_aliases_including_saved_pointer_and_position_overlap=True,integer_operations_modulo32=True,FPR_HILO_FCSR_unchanged_by_supported_integer_opcode_set=True,all_words_and_bindings_outside_window_identical=True,source_frame=72,retail_frame=72,no_private_frame_mapping=True,nonfaulting_ordinary_RAM_domain_only=True,raw_fault_prefix_order_not_claimed=True,proof_is_structural_expression_identity_not_SMT_or_hardware=True,effective_controls=controls,raw_SHA256=hashlib.sha256(raw).hexdigest(),retail_object_SHA256=hashlib.sha256((o/'original-target.o').read_bytes()).hexdigest(),source_installed=target_packet.installed(),matching_credit=0);(o/'symbolic.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
