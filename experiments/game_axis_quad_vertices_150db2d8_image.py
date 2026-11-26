"""Independent old C plus original ASM full-ELF prediction, without exclusions."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
sys.path.insert(0,str(Path.cwd()))
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_local_vector_transform_15117da4_match import restore_labels,assembly
from tools.experiments.game_resource_record_query_150eb484_image import predict_metadata
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.check_game_data_layout import audit_layout
from tools.experiments import game_axis_quad_vertices_150db2d8_match as target_packet
r=target_packet.ROOT;o=target_packet.OUT;b=o/'baseline';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def assemble(text,path):
 f=path.with_suffix('.s');f.write_text(text);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
def link(where,obj,label):
 text=(b/'conker/build/conker.ld').read_text();source='build/src/game/generated_108320.c.o';assert text.count(source)==1;text=text.replace(source,obj.relative_to(r/'conker').as_posix());script=where/(label+'.ld');script.write_text(text);elf=where/(label+'.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',script.relative_to(r/'conker').as_posix(),*['-T'+n for n in ('undefined_syms.us.txt','undefined_funcs.us.txt','undefined_syms_auto.txt','undefined_funcs_auto.txt')],'--no-check-sections','--no-warn-mismatch','-o',elf.relative_to(r/'conker').as_posix()],cwd=r/'conker',capture_output=True,text=True);assert q.returncode==0,q.stderr;return elf
def main():
 target_packet.prepare()
 where=o/'image-qualification';where.mkdir(exist_ok=True);old,diag=compile_owner(r,where,(b/'conker/src/game/generated_108320.c').read_text(),'reference-before');assert not diag
 from tools import check_bouncing_effect_150db114_pool as pool
 boundold=where/'reference-before.bound.o';assemble(pool.bind_assembly(old),boundold)
 text=restore_labels(pc.emit_padded_assembly(boundold,b/'conker/retail_layout.us.txt','generated_108320',word_patches_path=b/'conker/retail_word_patches.us.csv'),b/'conker/asm/108320.s');before_obj=where/'reference-before.padded.o';assemble(text,before_obj);assert before_obj.read_bytes()==(b/'conker/build/src/game/generated_108320.c.o').read_bytes()
 fn='func_150DB2D8';lo=text.index('.globl '+fn+'\n');hi=text.index('.globl ',lo+1);assert text[lo:hi].count('.globl ')==1 and '.space 0x234, 0'in text[lo:hi]
 truth,refs=payload(o/'original-target.o',fn);assert len(truth)==576;replacement=assembly(truth,refs,fn);replacement=replacement[replacement.index('.globl '):]+'\n';reference_obj=where/'reference-after.o';assemble(text[:lo]+replacement+text[hi:],reference_obj);assert same_functions(before_obj,reference_obj,(fn,))==5 and normalized_pools(before_obj)==normalized_pools(reference_obj)
 reference=link(where,reference_obj,'reference');before=(b/'conker/build/conker.us.elf').read_bytes();wanted=bytearray(before);at=elf_slot_offset(wanted,0x150db2d8,576);wanted[at:at+576]=(r/'conker/conker.us.bin').read_bytes()[0x108788:0x1089c8];rows=[(pos,v)for pos,name,v,_ in symbol_rows(wanted)if name==fn];assert len(rows)==1;position,row=rows[0];assert row[1:3]==(0x150db2d8,12);struct.pack_into('>I',wanted,position+8,576)
 predicted,moved=predict_metadata(bytes(wanted),reference.read_bytes());prediction=where/'predicted.elf';prediction.write_bytes(predicted);actual=link(where,o/'make-owner/src/game/generated_108320.c.o','linked');assert actual.read_bytes()==predicted
 q=dict(reference_uses_frozen_before_C_and_original_ASM_only=True,metadata_permuted_records=moved,predicted_ELF_sha256=sha(prediction),changed_bytes=sum(a!=z for a,z in zip(before,predicted)),exclusions=0,protected_data_audit=audit_layout(actual,r/'conker'),strict_predicted_ELF_equal=True,neighbors=5,source_installed=target_packet.installed(),matching_credit=0);(o/'image-qualification.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k!='metadata_permuted_records'}),flush=True);return q
if __name__=='__main__':main()
