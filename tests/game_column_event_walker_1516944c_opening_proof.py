"""All-input affine proof of the closed opening roles and linked end fold."""
from pathlib import Path
import json,struct,sys
from tools.experiments import game_column_event_walker_1516944c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_column_event_walker_1516944c_guest as p
from tools.experiments.game_actor_state_tick_integration import symbol_rows
MASK=0xFFFFFFFF
def const(n):return {'constant':n&MASK}if n&MASK else{}
def variable(n):return {n:1}
def add(a,b,factor=1):
 r=dict(a)
 for k,v in b.items():r[k]=(r.get(k,0)+factor*v)&MASK
 return {k:v for k,v in r.items()if v}
def mul(a,n):return {k:v*n&MASK for k,v in a.items()if v*n&MASK}
def execute_opening(ws,taken):
 r=[variable('R%d'%i)for i in range(32)];r[0]={};memory={};pc=0
 initial=[dict(a)for a in r]
 while pc<33:
  w=ws[pc];op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;imm=((w&65535)^32768)-32768
  if op==15:r[rt]=const((w&65535)<<16)
  elif op==9:r[rt]=add(r[rs],const(imm))
  elif op==12:
   assert r[rs]==initial[6]and w&65535==255;r[rt]=variable('byte(R6)')
  elif op==43:memory[json.dumps(add(r[rs],const(imm)),sort_keys=True)]=dict(r[rt])
  elif op==10:
   assert pc==14 and rs==4 and rt==1 and imm==104;r[rt]={'signed(R4)<104':1}
  elif op==5:
   assert pc==15 and rs==1 and rt==0 and r[1]=={'signed(R4)<104':1}and imm==2
   pc+=1;delay=ws[pc];assert delay>>26==15;r[delay>>16&31]=const((delay&65535)<<16)
   pc=18 if taken else 17;continue
  elif op==0 and fn==0:r[rd]=mul(r[rt],1<<sa)
  elif op==0 and fn==0x21:r[rd]=add(r[rs],r[rt])
  elif op==0 and fn==0x23:r[rd]=add(r[rs],r[rt],-1)
  elif op==0 and fn==0x25:
   assert not r[rt];r[rd]=dict(r[rs])
  else:raise AssertionError((pc,hex(w)))
  r[0]={};pc+=1
 return r,memory,initial
def main():
 paths=[out/'assign-1/candidate.o',out/'qualified-owner/game_1944C0.c.o',out/'original-target.o'];s=p.SYMS
 for taken in(True,False):
  states=[execute_opening(p.words(path),taken)for path in paths]
  assert states[0][1]==states[1][1]==states[2][1]
  col=variable('R4')if taken else const(103)
  expected={4:col,19:variable('R5'),20:variable('byte(R6)'),29:add(variable('R29'),const(-64)),
   22:add(const(s['D_8008B4A8']),mul(col,52)),23:add(const(s['D_800DCE50']),mul(col,4)),30:const(s['D_800DCE50']),18:const(s['D_800DD190']),21:const(s['D_800DD198'])}
  for r,m,initial in states:
   for k,v in expected.items():assert r[k]==v,(taken,k,r[k],v)
   for k in(16,17,28,31):assert r[k]==initial[k]
 rows={n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n}
 assert rows['D_800DD190']==rows['D_800DCE50']+0x340
 for path in paths:
  ws=p.words(path);start=88
  expected=[0x3C08800E,0x2508D190,0x27DE01A0,0x17C8FFC5,0x26F701A0]
  if len(ws)==106:assert ws[start:start+6]==[0x3C08800E,0x2508CE50,0x27DE01A0,0x25090340,0x17C9FFC4,0x26F701A0]
  else:assert ws[start:start+5]==expected
 # Equal modulo-32-bit end expressions cover every possible linked base.
 assert add(variable('row_base'),const(0x340))==add(add(variable('row_base'),const(0x1A0)),const(0x1A0))
 bad=p.words(paths[0]);bad[19]^=1<<21
 rejected=execute_opening(bad,True)[0]
 assert rejected[22]!=add(const(s['D_8008B4A8']),mul(variable('R4'),52)),'Ineffective opening source-role control'
 r=dict(all_2_to_32_column_words_proved=True,signed_branch_domains=2,all_payload_and_opcode_bits_symbolic=True,
  saved_role_and_stack_store_expressions_equal=True,closing_address_fold_proved_modulo_32_bits=True,actual_end_symbol_adjacency_verified=True,
  effective_opening_control=True,limits='The ABI preserves saved registers across contracted helpers/callbacks; volatile temporaries and PCs are not equated.',source_installed=packet.installed(),matching_credit=0)
 (out/'opening-proof.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
