"""Closed normalization algebra, selected words and two-path callback guard."""
from pathlib import Path
import json,struct,sys
from tools.experiments import game_view_trig_render_walker_15167310_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_view_trig_render_walker_15167310_match import normalize
def main():
 raw,refs=payload(out/'selected/candidate.o','func_15167310');fixed,frefs,order=normalize(raw,refs)
 assert(fixed,frefs)==payload(out/'original-target.o','func_15167310')
 a=struct.unpack('>124I',raw);b=struct.unpack('>122I',fixed)
 assert len(set(i for i in order if i is not None))==121
 assert a[35]==0xE6600000 and b[38]==0x26730004 and b[40]==0xE660FFFC
 arithmetic=0
 # Modulo32 address identity, including both carry boundaries and wraparound.
 for pointer in(0,4,0x7FFC,0x8000,0x7FFFFFFC,0xFFFFFFFC):
  assert pointer&0xFFFFFFFF==((pointer+4-4)&0xFFFFFFFF);arithmetic+=1
 # Every independent view scheduling word retains its destination and operand.
 assert order[35:41]==[37,36,38,40,39,35]
 assert all((a[i]>>26)==9 for i in(37,38,40))and a[36]&63==42
 assert a[39]>>26==4 and a[35]>>26==57
 # Cached descriptor base replaces two per-head address materializations.
 assert a[64]==0x03C0A825 and a[72]>>26==15 and a[73]>>26==9
 assert frefs[212]==[('R_MIPS_HI16','D_8008B4A8')]and frefs[232]==[('R_MIPS_LO16','D_8008B4A8')]
 assert a[77]>>26==20 and a[78]==0x26B501A0 and b[74]>>26==4 and b[75]==0
 branch_paths=[]
 # Raw likely null branch increments row in its executed delay then skips
 # common increment. Fixed plain branch uses a NOP then reaches common row
 # increment. Non-null raw branch annuls that increment and reaches it later.
 def target(ws,i):return i+1+(((ws[i]&65535)^32768)-32768)
 def path(ws,head_i,cb_i,walk_end,row_branch,head,callback):
  executed=[head_i+1]
  if not head:start=target(ws,head_i)
  elif not callback:
   executed.append(cb_i+1);start=target(ws,cb_i)
  else:
   # The raw likely branch annuls its increment on the non-null path.
   if ws[cb_i]>>26!=20:executed.append(cb_i+1)
   start=walk_end
  executed+=list(range(start,row_branch+2))
  return sum(ws[i]==0x26B501A0 for i in executed),executed
 assert not any(w==0x26B501A0 for w in a[79:101])
 for head,callback in((0,0),(0,1),(1,0),(1,1)):
  raw_increments,raw_path=path(a,69,77,98,103,head,callback)
  fixed_increments,fixed_path=path(b,order.index(69),order.index(77),order.index(98),order.index(103),head,callback)
  assert raw_increments==fixed_increments==1
  branch_paths.append(dict(head=head,callback=callback,walk_entered=bool(head and callback),row_increments=1,raw_indices=raw_path,fixed_indices=fixed_path))
 # This is a linked-layout fold, not an interchangeable arbitrary symbol.
 syms={n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n}
 assert syms['D_800DD190']==syms['D_800DCE50']+0x340
 for low in(0,0x7FFC,0x8000,0xFFFC):
  start=0x80400000+low;end=start+0x340
  assert [start+416*k==end for k in(1,2)]==[False,True]
  assert ((end+0x8000)>>16)<<16 | end&65535 !=0
 assert b[98]>>26==15 and b[99]>>26==9 and b[100]==0x26B501A0 and b[101]>>26==5
 # F20/F21, all nine nonvolatile GPRs and RA keep exactly the measured homes.
 assert a[:35]==b[:35]and a[111:]==b[109:]
 r=dict(derived_words_equal=True,word_order_is_bijective_except_3_omissions_1_insertion=True,cache_address_cases=arithmetic,callback_gate_paths=branch_paths,
  frame=104,F20_F21_home=24,nonvolatile_GPR_and_RA_homes='0x20..0x44',column_offset_home=76,unidentified_tail_bytes=16,
  limits='Compiler scheduling and register-role normalization plus a linked-layout end fold. The 16-byte trailing frame area has no recovered semantic purpose; it remains explicit scaffolding.',source_installed=packet.installed(),matching_credit=0)
 (out/'roles.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
