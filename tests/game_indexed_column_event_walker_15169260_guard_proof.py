"""Symbolic opening/role proof, local branch shapes and live-reload controls."""
from pathlib import Path
from dataclasses import replace
import json,struct,sys
from tools.experiments import game_indexed_column_event_walker_15169260_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_indexed_column_event_walker_15169260_guest as p
from tools.experiments.game_actor_state_tick_integration import symbol_rows
MASK=0xFFFFFFFF
def const(n):return {'constant':n&MASK}if n&MASK else{}
def var(n):return {n:1}
def add(a,b):
 r=dict(a)
 for k,v in b.items():r[k]=(r.get(k,0)+v)&MASK
 return {k:v for k,v in r.items()if v}
def mul(a,n):return {k:v*n&MASK for k,v in a.items()if v*n&MASK}
def opening(ws,positive):
 r=[var('R%d'%i)for i in range(32)];r[0]={};initial=[dict(v)for v in r];memory={};pc=0;branch=None
 def step(w):
  op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;imm=((w&65535)^32768)-32768
  if op==15:r[rt]=const((w&65535)<<16)
  elif op==9:r[rt]=add(r[rs],const(imm))
  elif op==12:
   assert r[rs]==initial[7]and w&65535==255;r[rt]=var('byte(R7)')
  elif op in(35,43):
   key=json.dumps(add(r[rs],const(imm)),sort_keys=True)
   if op==43:memory[key]=dict(r[rt])
   else:r[rt]=dict(memory[key])
  elif op==0 and fn==0x25:
   assert not r[rt];r[rd]=dict(r[rs])
  else:raise AssertionError((pc,hex(w)))
  r[0]={}
 while pc<29:
  w=ws[pc]
  if w>>26==6:
   assert branch is None and r[w>>21&31]==initial[5];branch=pc
   step(ws[pc+1]);pc+=2
   if not positive:break
  else:step(w);pc+=1
 assert branch is not None
 return r,memory,initial
def main():
 paths=[out/'sdk-frame-last/candidate.o',out/'qualified-owner/game_1944C0.c.o',out/'original-target.o'];streams=[p.words(path)for path in paths]
 roles={18:20,19:18,20:19,22:23,23:30,30:22}
 for positive in(False,True):
  states=[opening(ws,positive)for ws in streams];assert states[0][1]==states[1][1]==states[2][1]
  for r,m,initial in states:
   assert r[29]==add(var('R29'),const(-88))
   assert m[json.dumps(add(var('R29'),const(4)),sort_keys=True)]==var('R5')
   assert m[json.dumps(add(var('R29'),const(12)),sort_keys=True)]==var('R7')
   assert m[json.dumps(add(var('R29'),const(-8)),sort_keys=True)]=={}
  if positive:
   raw=states[0][0];retail=states[2][0]
   for a,b in roles.items():assert raw[a]==retail[b],(a,b)
   for k in(16,17,21,28,29,31):assert raw[k]==retail[k]
   assert raw[30]==var('R4')and raw[19]==var('R6')and raw[20]==var('byte(R7)')and raw[23]==const(52)
   assert states[0][1][json.dumps(add(var('R29'),const(-24)),sort_keys=True)]==const(p.SYMS['D_800DCE50'])
 # The only nonconstant address expressions reordered around the callback gate.
 x=var('column');row=var('row');base=var('descriptor_base')
 assert add(row,mul(x,4))==add(mul(x,4),row)
 assert add(base,mul(x,52))==add(mul(x,52),base)
 # Both empty-node rewrites increment before joining the common signed reload.
 raw=streams[0];ret=streams[2]
 for branch,store,load in((43,42,44),(80,79,81)):
  assert raw[branch]>>26==20 and raw[store]>>26==40 and raw[load]>>26==32
 for branch,store in((45,46),(79,80)):
  assert ret[branch]>>26==4 and ret[store]>>26==40
 assert raw[36]>>26==4 and ret[40]>>26==20 and ret[41]>>26==32
 for depth in range(256):
  raised=(depth+1)&255
  assert (p.g.s8(raised)-1)&255==depth
 # Retained load has no ordinary CFG predecessor: prior branch is unconditional.
 assert ret[74]>>26==4 and ret[74]>>16&1023==0 and ret[75]>>26==40
 target=74+1+((ret[74]&65535)^32768)-32768;assert target==99 and ret[76]>>26==32
 rows={n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n}
 assert rows['D_800DD190']==rows['D_800DCE50']+0x340
 assert add(var('row_base'),const(0x340))==add(add(var('row_base'),const(0x1A0)),const(0x1A0))
 controls=[]
 for name,index,expected,new,c in(
  ('cached-count-home',108,0x8FAC005C,0x240C0002,replace(p.Case(),mode=32)),
  ('cached-current-entry',54,0x8FD90000,0x24190002,replace(p.Case(),pattern=1,mode=16))):
  assert raw[index]==expected,(name,index,hex(raw[index]));bad=list(raw);bad[index]=new
  m=p.Oracle(bad,p.fixture(c),c);m.run()
  try:p.check(m,c)
  except AssertionError:controls.append(name)
  else:raise AssertionError('Ineffective live reload control: '+name)
 r=dict(symbolic_all_input_opening=True,signed_count_domains=2,full_opcode_home_and_byte_role=True,closed_saved_role_map=roles,
  owned_frame_saved_store_values_equal=True,frame=88,row_SP_offset=64,counter_SP_offset=80,
  head_address_commutation_modulo_32_bits=True,empty_branch_store_and_unwind_shapes_verified=True,
  all_256_depth_increment_unwind_values=True,unreachable_retail_load=76,linked_row_end_adjacency=True,
  effective_live_reload_controls=controls,limits='Symbolic opening and local transformations complement the full-stream guest/native checks. Arbitrary provider internals, exception PCs, volatile register identity and cycle timing are not equated.',source_installed=packet.installed(),matching_credit=0)
 (out/'guard-proof.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
