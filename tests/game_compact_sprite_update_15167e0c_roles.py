"""Symbolic fixed-point stores, load-order dependency and byte-home liveness."""
from pathlib import Path
import json,struct,sys
from tools.experiments import game_compact_sprite_update_15167e0c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_compact_sprite_update_15167e0c_match import normalize
def expr(op,*args):
 if op in('add32','mul32','mulhi32','or32'):args=tuple(sorted(args,key=repr))
 return(op,*args)
def symbolic(words):
 r=[('incoming',i)for i in range(32)];r[0]=('zero',);memory={};writes=[];ticks=[];lo=hi=None;branch=None
 def load(offset,size):
  key=(offset,size)
  return expr('signed16'if size==2 else'unsigned8',memory.get(key,('initial-record-bytes',offset,size)))
 for i in range(48,90):
  w=words[i];op,rs,rt,rd,shift,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;imm=w&65535
  if op in(33,36):assert rs==4;r[rt]=load(imm,2 if op==33 else 1)
  elif op==35:
   assert rs==8 and imm==0;ticks.append(len(writes));r[rt]=('live-tick-after-public-stores',len(writes))
  elif op in(40,41):
   assert rs==4;size=1 if op==40 else 2;key=(imm,size)
   # Distinct record fields cannot overlap after the schedule permutation.
   assert all(at==imm and n==size or at+n<=imm or imm+size<=at for at,n in memory)
   value=expr('low8'if size==1 else'low16',r[rt]);memory[key]=value;writes.append((imm,size,value))
  elif op==0:
   if fn==33:r[rd]=expr('add32',r[rs],r[rt])
   elif fn==37:r[rd]=expr('or32',r[rs],r[rt])
   elif fn==0:r[rd]=expr('shift-left32',r[rt],shift)
   elif fn==3:r[rd]=expr('arithmetic-right32',r[rt],shift)
   elif fn==25:lo=expr('mul32',r[rs],r[rt]);hi=expr('mulhi32',r[rs],r[rt])
   elif fn==18:assert lo is not None;r[rd]=lo
   else:raise AssertionError(('Unqualified block instruction',i,hex(w)))
  elif op==4:
   assert i==88 and rt==0;branch=(r[rs],i+1+(((imm^32768)-32768)))
  else:raise AssertionError(('Unqualified block opcode',i,hex(w)))
 return dict(writes=writes,tick_read_store_positions=ticks,retained_registers=[r[i]for i in(4,6,7,8,29,31)],lo=lo,hi=hi,branch=branch)
def main():
 raw,refs=payload(out/'selected/candidate.o','func_15167E0C');fixed,nrefs,order=normalize(raw,refs);a=struct.unpack('>195I',raw);b=struct.unpack('>195I',fixed)
 assert(fixed,nrefs)==payload(out/'original-target.o','func_15167E0C')and refs==nrefs
 assert order[:62]==list(range(62))and order[83:]==list(range(83,195))and sorted(order)==list(range(195))
 assert all(a[i]==b[i]for i in range(48)if i not in(40,44))and a[90:]==b[90:]
 source,target=symbolic(a),symbolic(b);assert source==target
 assert [v[:2]for v in source['writes']]==[(0x30,2),(0x22,2),(0x2E,1),(0x20,2),(0x2C,1),(0x24,2),(0x2D,1)]
 assert source['tick_read_store_positions']==[1,3,5]
 assert a[40]==0xA3A7001F and a[44]==0x93A7001F and b[40]==0xA3A7001B and b[44]==0x93A7001B
 for home in(27,31):assert 16<=home<32 and not 20<=home<24
 # Flag load44 has only the dispatched-call path as predecessor. Both skip
 # branches bypass it: selector sentinel32 ->45; null callback36 ->46.
 target_of=lambda i:i+1+(((a[i]&65535)^32768)-32768)
 assert target_of(32)==45 and target_of(36)==46
 assert a[39]==b[39]==0x0060F809 and a[38]==b[38]==0xAFA40020 and a[43]==b[43]==0x8FA40020
 assert a[0]==b[0]==0x27BDFFE0 and a[1]==b[1]==0xAFBF0014
 r=dict(all_195_source_origins_bijective=True,named_relocations_unchanged=True,symbolic_motion_stores_and_low32_products_equal=True,ordered_public_store_offsets=[hex(v[0])for v in source['writes']],
  tick_load_after_store_counts=[1,3,5],retained_speed_pointer_flag_SP_RA_and_HI_LO_equal=True,completion_byte_home_before=31,completion_byte_home_after=27,completion_byte_store_dominates_reload=True,
  no_frame_scaffolding=True,no_inserted_or_omitted_words=True,frame=32,source_installed=packet.installed(),matching_credit=0,
  limits='Bitvector expression and byte/halfword dependency proof for the motion block; live tick reads retain their store boundaries. Caller-owned argument homes may change; the private completion byte remains outside the callee argument area.')
 (out/'roles.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
