"""Prove the complete compiler difference is closed independent scheduling."""
from pathlib import Path
from tools.experiments import game_owner_effect_packet_1514e31c_packet as target_packet
from collections import Counter
import csv,hashlib,io,json,struct,subprocess,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_local_vector_transform_15117da4_match import restore_labels,assembly
compile_owner=target_packet.compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_actor_transform_position_match import diagnostic_rows
R=target_packet.ROOT;O=target_packet.OUT;B=O/'baseline';FN='func_1514E31C';OWNER='generated_179F30'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def assemble(text,path):
 src=path.with_suffix('.s');src.write_text(text);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(R/'conker/include'),'-o',str(path),str(src)],capture_output=True,text=True);assert q.returncode==0,q.stderr
def effects(w):
 op,rs,rt=w>>26,w>>21&31,w>>16&31;off=w&65535
 if op in (40,41,43,57):
  assert rs==29;n={40:1,41:2,43:4,57:4}[op]
  return set((('g',29),('f'if op==57 else'g',rt))),set(),set(),set(range(off,off+n))
 if op==35:
  assert rs==29 and off==304
  return {('g',29)},{('g',rt)},set(range(off,off+4)),set()
 if op==9:
  assert rs in(0,29)and rt in(5,6,7)
  return {('g',rs)},{('g',rt)},set(),set()
 raise AssertionError(('unexpected instruction in permutation',hex(w)))
def main():
 target_packet.prepare()
 full=(B/'conker/asm/179F30.s').read_text();body=full.split('glabel '+FN+'\n',1)[1].split('endlabel '+FN,1)[0]
 assemble('.include \"macro.inc\"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+FN+'\n'+body+'endlabel '+FN+'\n.size '+FN+',.-'+FN+'\n',O/'original-target.o')
 source=(O/'selected-source.c').read_text();before,bd=compile_owner(R,O,(B/'conker/src/game/generated_179F30.c').read_text(),'before-owner');obj,ad=compile_owner(R,O,source,'selected-owner')
 assert same_functions(before,obj,(FN,))==77 and normalized_pools(before)==normalized_pools(obj)and diagnostic_rows(bd)==diagnostic_rows(ad)and sum(diagnostic_rows(ad).values())==4
 raw,rr=payload(obj,FN);retail,tr=payload(O/'original-target.o',FN);assert len(raw)==len(retail)==492 and rr==tr and len(rr)==7
 words=list(struct.unpack('>123I',raw));truth=list(struct.unpack('>123I',retail));normalized=words[:]
 assert words[3]==truth[3]==0x27bdfed0 and words[6]==truth[6]==0xafbf0044 and words[7]==truth[7]==0xafa40130
 blocks=[(0x6c,0x78),(0x78,0x88),(0xf4,0x104),(0x108,0x118),(0x18c,0x1d4)];proofs=[]
 for lo,hi in blocks:
  a=words[lo//4:hi//4];b=truth[lo//4:hi//4];assert Counter(a)==Counter(b),(hex(lo),a,b)
  # Every pair in each block commutes, including both directions of register
  # and memory hazards. No arithmetic/FP/state/control transformation is used.
  for i,x in enumerate(a):
   xr,xw,xmr,xmw=effects(x)
   for y in a[i+1:]:
    yr,yw,ymr,ymw=effects(y)
    assert not(xw&(yr|yw)or yw&(xr|xw)or xmw&(ymr|ymw)or ymw&(xmr|xmw)),(hex(lo),hex(x),hex(y))
  normalized[lo//4:hi//4]=b;proofs.append(dict(start=hex(lo),end=hex(hi),words=len(a),pairwise_register_and_memory_independent=True))
 assert normalized==truth
 for w in words:
  if w>>26==17:assert w>>21&31==4 # MTC1 only, not FP arithmetic or FCSR
 base=(B/'conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(base.decode())));out=io.StringIO(newline='');writer=csv.writer(out,lineterminator='\n');rows=[]
 for i,(a,b)in enumerate(zip(words,truth)):
  if a==b:continue
  off=i*4;assert off not in rr
  row=[OWNER,FN,f'0x{off:03X}',f'0x{a:08X}',f'0x{b:08X}','-','-','Normalize pairwise independent packet vector and outgoing argument initialization','','','false'];assert len(row)==len(fields);rows.append(row);writer.writerow(row)
 assert len(rows)==32
 (O/'guard-additions.csv').write_bytes(out.getvalue().encode());(O/'selected-guards.csv').write_bytes(base+out.getvalue().encode());assemble(assembly(retail,tr,FN),O/'normalized-target.o')
 where=O/'qualified-owner';where.mkdir(exist_ok=True);outputs=[]
 for mode,path in [('before',before),('selected',obj)]:
  guard=B/'conker/retail_word_patches.us.csv'if mode=='before'else O/'selected-guards.csv'
  for kind in ('generic','generated'):
   text=restore_labels(pc.emit_padded_assembly(path,B/'conker/retail_layout.us.txt',OWNER,word_patches_path=guard,rodata_symbol='jtbl_800A5E20'),B/'conker/asm/179F30.s')if kind=='generic'else pg.emit_padded_assembly(path,B/'conker/asm/179F30.s',filename=OWNER,word_patches_path=guard,rodata_symbol='jtbl_800A5E20');target=where/(mode+'-'+kind+'.o');assemble(text,target)
   if mode=='before':assert target.read_bytes()==(B/'conker/build/src/game/generated_179F30.c.o').read_bytes()
   else:
    assert payload(target,FN)==(retail,tr)and same_functions(where/('before-'+kind+'.o'),target,(FN,))==77 and normalized_pools(target)==normalized_pools(where/('before-'+kind+'.o'));outputs.append(target)
 assert outputs[0].read_bytes()==outputs[1].read_bytes()
 q=dict(words=123,raw_frame=304,retail_frame=304,guards=32,independent_schedule_blocks=proofs,all_words_accounted=True,all_bindings_unchanged=True,binding_positions=7,no_register_frame_FP_or_value_rewrite=True,raw_neighbors=77,normalized_neighbors=77,pools_unchanged=True,both_complete_padders_equal=True,both_before_objects_equal_frozen=True,source_sha256=sha(O/'selected-source.c'),padded_sha256=sha(outputs[0]),guards_sha256=sha(O/'selected-guards.csv'),new_diagnostics=0,existing_diagnostics=4,source_installed=target_packet.installed(),matching_credit=0,goal_status='active')
 (O/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
