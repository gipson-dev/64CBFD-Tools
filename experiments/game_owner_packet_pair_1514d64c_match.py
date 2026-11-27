"""Closed compiler frame, COP1-role and disjoint-store normalization proof."""
from pathlib import Path
from tools.experiments import game_owner_packet_pair_1514d64c_packet as target_packet
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
R=target_packet.ROOT;O=target_packet.OUT;B=O/'baseline';FN='func_1514D64C';OWNER='generated_179F30'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def assemble(text,path):
 src=path.with_suffix('.s');src.write_text(text)
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(R/'conker/include'),'-o',str(path),str(src)],capture_output=True,text=True);assert q.returncode==0,q.stderr
def main():
 target_packet.prepare()
 full=(B/'conker/asm/179F30.s').read_text();body=full.split('glabel '+FN+'\n',1)[1].split('endlabel '+FN,1)[0]
 assemble('.include \"macro.inc\"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+FN+'\n'+body+'endlabel '+FN+'\n.size '+FN+',.-'+FN+'\n',O/'original-target.o')
 selected=target_packet.MANIFEST['selected_source'];before,bd=compile_owner(R,O,(B/'conker/src/game/generated_179F30.c').read_text(),'before-owner');obj,ad=compile_owner(R,O,selected,'selected-owner')
 (O/'selected-source.c').write_text(selected)
 assert diagnostic_rows(bd)==diagnostic_rows(ad) and sum(diagnostic_rows(ad).values())==4
 assert same_functions(before,obj,(FN,))==77 and normalized_pools(before)==normalized_pools(obj)
 raw,rr=payload(obj,FN);retail,tr=payload(O/'original-target.o',FN)
 assert len(raw)==len(retail)==800 and rr==tr and len(rr)==13
 words=list(struct.unpack('>200I',raw));truth=list(struct.unpack('>200I',retail));normalized=words[:]
 # Only an unused eight-byte high tail is removed. All emitted stack offsets,
 # saved roles and escaping packet extents fit the original 296-byte frame.
 assert words[3]==0x27bdfed0 and words[0x314//4]==0x27bd0130
 normalized[3]=0x27bdfed8;normalized[0x314//4]=0x27bd0128
 assert words[4]==truth[4]==0xafb00048 and words[8]==truth[8]==0xafbf004c
 footprint=[]
 for i,w in enumerate(words):
  op=w>>26;rs=w>>21&31
  if rs==29 and op in (32,33,35,36,37,40,41,43,49,57):
   width={32:1,36:1,40:1,33:2,37:2,41:2}.get(op,4);off=w&65535
   assert 0<=off and off+width<=296,(i,off,width)
   footprint.append((i*4,off,width))
 assert (0x54+32,0x74+88,0xcc+92)==(0x74,0xcc,296)
 assert 0xcc+0x58+1<=296 # actual helper writes subtype byte 88
 # Complete phase-two FPR bijection. There is no COP1 arithmetic, conversion,
 # compare or FCSR access: MTC1/LWC1/SWC1 transfer raw bits, including sNaNs.
 rename={14:2,16:12,2:14,12:16};renamed=[]
 for i,w in enumerate(words):
  op=w>>26
  if op==17:assert w>>21&31==4,('non-MTC1 COP1',i,w)
  if 0x160<=i*4<0x29c:
   shift=11 if op==17 else 16 if op in (49,57) else None
   if shift is not None:
    reg=w>>shift&31;target=rename.get(reg,reg)
    if reg!=target:normalized[i]=(w&~(31<<shift))|(target<<shift);renamed.append(i*4)
 # Each permutation consists solely of nonoverlapping SP-relative stores;
 # base/source registers are unchanged inside the block and no call intervenes.
 blocks=[(0x74,0x80),(0x80,0x90),(0xf8,0x100),(0x100,0x108),
 (0x10c,0x11c),(0x1bc,0x1c8),(0x1c8,0x1d8),(0x240,0x248),
 (0x248,0x258),(0x27c,0x284)]
 permutations=[]
 for lo,hi in blocks:
  a=normalized[lo//4:hi//4];b=truth[lo//4:hi//4];assert Counter(a)==Counter(b),(hex(lo),a,b)
  used=set()
  for w in a:
   op=w>>26;assert op in (40,41,43,57) and w>>21&31==29
   width={40:1,41:2,43:4,57:4}[op];off=w&65535;span=set(range(off,off+width));assert not used&span;used|=span
  normalized[lo//4:hi//4]=b;permutations.append(dict(start=hex(lo),end=hex(hi),stores=len(a),disjoint_bytes=len(used)))
 assert normalized==truth,[(hex(i*4),hex(a),hex(b)) for i,(a,b) in enumerate(zip(normalized,truth)) if a!=b]
 base=(B/'conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(base.decode())));stream=io.StringIO(newline='');writer=csv.writer(stream,lineterminator='\n');rows=[]
 for i,(a,b) in enumerate(zip(words,truth)):
  if a==b:continue
  off=i*4;refs=rr.get(off,[]);assert len(refs)<=1;tag=refs[0][0]+':'+refs[0][1] if refs else '-'
  reason='Remove unused compiler frame tail; all packet extents and saved roles remain within retail frame' if off in (0xc,0x314) else 'Normalize closed phase-two COP1 bit-transfer register roles' if off in renamed else 'Normalize independent nonoverlapping packet initialization stores'
  row=[OWNER,FN,f'0x{off:03X}',f'0x{a:08X}',f'0x{b:08X}',tag,tag,reason,'','','false'];assert len(row)==len(fields);writer.writerow(row);rows.append(row)
 assert len(rows)==44
 suffix=stream.getvalue().encode();(O/'guard-additions.csv').write_bytes(suffix);(O/'selected-guards.csv').write_bytes(base+suffix)
 assemble(assembly(retail,tr,FN),O/'normalized-target.o')
 where=O/'qualified-owner';where.mkdir(exist_ok=True);outputs=[]
 for mode,path in [('before',before),('selected',obj)]:
  guard=B/'conker/retail_word_patches.us.csv' if mode=='before' else O/'selected-guards.csv'
  for kind in ('generic','generated'):
   text=restore_labels(pc.emit_padded_assembly(path,B/'conker/retail_layout.us.txt',OWNER,word_patches_path=guard,rodata_symbol='jtbl_800A5E20'),B/'conker/asm/179F30.s') if kind=='generic' else pg.emit_padded_assembly(path,B/'conker/asm/179F30.s',filename=OWNER,word_patches_path=guard,rodata_symbol='jtbl_800A5E20')
   target=where/(mode+'-'+kind+'.o');assemble(text,target)
   if mode=='before':assert target.read_bytes()==(B/'conker/build/src/game/generated_179F30.c.o').read_bytes()
   else:
    assert payload(target,FN)==(retail,tr) and same_functions(where/('before-'+kind+'.o'),target,(FN,))==77
    assert normalized_pools(target)==normalized_pools(where/('before-'+kind+'.o'));outputs.append(target)
 assert outputs[0].read_bytes()==outputs[1].read_bytes()
 report=dict(words=200,raw_frame=304,retail_frame=296,raw_differences=44,guards=44,frame_guards=2,renamed_COP1_words=len(renamed),disjoint_store_permutations=permutations,all_200_words_accounted=True,all_13_bindings_unchanged=True,no_COP1_arithmetic_conversion_compare_or_FCSR_instruction=True,all_emitted_SP_accesses_within_retail_frame=True,SP_accesses=footprint,helper_source_byte_88_in_bounds=True,raw_neighbors=77,normalized_neighbors=77,pools_unchanged=True,both_complete_padders_equal=True,both_before_objects_equal_frozen=True,selected_source_sha256=sha(O/'selected-source.c'),padded_sha256=sha(outputs[0]),selected_guards_sha256=sha(O/'selected-guards.csv'),existing_diagnostics=4,new_diagnostics=0,source_installed=target_packet.installed(),matching_credit=0,raw_literal_private_fault_parity_claimed=False,frame_derivation='eight unused high bytes removed; exact live offsets unchanged',goal_status='active')
 (O/'objects.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ('SP_accesses','disjoint_store_permutations')}),flush=True)
 return report
if __name__=='__main__':main()
