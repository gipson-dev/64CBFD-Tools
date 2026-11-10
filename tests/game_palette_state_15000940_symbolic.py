"""Affine, modulo-32-bit proof of all loop traces and public ABI boundaries.

Each load is an independent symbolic input. Equal ordered reads/writes imply
equal memory behavior even when modeled data addresses alias. Actual symbolic
HI/LO pairs use one address atom; separate GNU links check real split carries.
Stack-save forwarding assumes the normal disjoint stack/global object domain.
"""
import json,struct
from tools.experiments import game_palette_state_15000940_match as p
from tools.experiments import game_palette_state_15000940_match as n
MASK=0xFFFFFFFF
def vec(values):return tuple(sorted((k,v&MASK)for k,v in values.items()if v&MASK))
def atom(name):return((name,1),)
def val(i):return vec({'#':i})
def add(a,b,scale=1):
 d=dict(a)
 for k,v in b:d[k]=d.get(k,0)+scale*v
 return vec(d)
def mul(a,v):return vec({k:c*v for k,c in a})
def address(name):
 if name=='D_800D9EB7':return add(atom('ADDR:D_800D9EB4'),val(3))
 if name=='D_800D9EC4':return add(atom('ADDR:D_800D9EB8'),val(12))
 return atom('ADDR:'+name)
def signed16(v):return((v&65535)^32768)-32768
def execute(raw,refs):
 ws=struct.unpack('>95I',raw);r=[atom('INITIAL_R%d'%i)for i in range(32)];r[0]=val(0);initial=r[:];trace=[];memory={};pc=0;branches=[];visits=[]
 def one(i):
  w=ws[i];op,rs,rt,rd=w>>26,w>>21&31,w>>16&31,w>>11&31;imm=signed16(w);rel=refs.get(4*i,[]);visits.append(i)
  if op in(4,5):
   diff=add(r[rs],r[rt],-1);assert all(k=='#'for k,_ in diff),('Unresolved branch',i,diff)
   equal=not diff;take=equal if op==4 else not equal;branches.append((take,i+1+imm));return i+1+imm if take else i+2
  if op==0:
   fn=w&63
   if fn==8:assert rs==31;return 'return'
   if fn==0:r[rd]=mul(r[rt],1<<(w>>6&31))
   elif fn in(0x21,0x23):r[rd]=add(r[rs],r[rt],-1 if fn==0x23 else 1)
   elif fn==0x25:assert r[rt]==val(0);r[rd]=r[rs]
   else:raise AssertionError(('Unknown SPECIAL',i,hex(w)))
  elif op==15:
   if rel:assert len(rel)==1 and rel[0][0]=='R_MIPS_HI16';r[rt]=address(rel[0][1])
   else:r[rt]=val((w&65535)<<16)
  elif op==9:
   if rel:assert len(rel)==1 and rel[0][0]=='R_MIPS_LO16';imm=0
   r[rt]=add(r[rs],val(imm))
  elif op in(35,36,40,41,43):
   if rel:assert len(rel)==1 and rel[0][0]=='R_MIPS_LO16';imm=0
   at=add(r[rs],val(imm));width={35:4,36:1,40:1,41:2,43:4}[op]
   if op in(35,36):
    result=memory.get((at,width),atom('READ_%d_WIDTH_%d'%(len(trace),width)));trace.append(('R',at,width,result));r[rt]=result
   else:
    result=r[rt];trace.append(('W',at,width,result));memory[at,width]=result
  else:raise AssertionError(('Unknown opcode',i,hex(w)))
  r[0]=val(0);return None
 while True:
  assert len(visits)<1000
  target=one(pc)
  if target is not None:
   assert one(pc+1)is None
   if target=='return':break
   pc=target
  else:pc+=1
 assert r[16:24]==initial[16:24]and r[28:]==initial[28:],'Callee-save or SP/RA changed'
 return dict(trace=trace,branches=[v for v,_ in branches],registers=r,visits=visits)
def main():
 raw,refs=p.payload(p.out/'selected.o');normal,rs=n.normalize(raw,refs);a,b=execute(raw,refs),execute(normal,rs)
 assert a['trace']==b['trace'],'Symbolic ordered memory effects differ'
 assert a['branches']==b['branches']and len(a['branches'])==16
 assert len(a['trace'])==130
 assert set(a['visits'])==set(b['visits'])==set(range(95))
 r=dict(symbolic_ordered_memory_accesses=130,symbolic_branch_decisions=16,all_95_raw_and_normal_words_reachable=True,all_initial_registers_and_130_load_store_effects_symbolic=True,all_instructions_retained_once=sorted(n.ORDER)==list(range(95)),saved_GPRs_SP_RA_preserved=True,raw_V0_is_caller_scratch=True,HI_LO_atom_abstraction_requires_independent_GNU_links=True,no_portable_C_fault_claim=True)
 (p.out/'symbolic.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
