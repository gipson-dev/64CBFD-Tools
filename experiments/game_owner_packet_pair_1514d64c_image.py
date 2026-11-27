"""Independent old-C plus full original packet callback ASM ELF prediction."""
from pathlib import Path
from tools.experiments import game_owner_packet_pair_1514d64c_packet as target_packet
import hashlib,json,re,struct,subprocess,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_local_vector_transform_15117da4_match import restore_labels
from tools.experiments.game_resource_record_query_150eb484_image import predict_metadata
compile_owner=target_packet.compile_owner
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_actor_transform_position_match import diagnostic_rows
from tools.check_game_data_layout import audit_layout
r=target_packet.ROOT;o=target_packet.OUT;b=o/'baseline';fn='func_1514D64C';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def assemble(text,path):
 p=path.with_suffix('.s');p.write_text(text);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(p)],capture_output=True,text=True);assert q.returncode==0,q.stderr
def link(where,obj,label):
 text=(b/'conker/build/conker.ld').read_text();source='build/src/game/generated_179F30.c.o';assert text.count(source)==1;text=text.replace(source,obj.relative_to(r/'conker').as_posix());script=where/(label+'.ld');script.write_text(text);elf=where/(label+'.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',script.relative_to(r/'conker').as_posix(),*['-T'+n for n in ('undefined_syms.us.txt','undefined_funcs.us.txt','undefined_syms_auto.txt','undefined_funcs_auto.txt')],'--no-check-sections','--no-warn-mismatch','-o',elf.relative_to(r/'conker').as_posix()],cwd=r/'conker',capture_output=True,text=True);assert q.returncode==0,q.stderr;return elf
def main():
 target_packet.prepare()
 where=o/'image-qualification';where.mkdir(exist_ok=True);old,diag=compile_owner(r,where,(b/'conker/src/game/generated_179F30.c').read_text(),'reference-before');assert diagnostic_rows(diag)==diagnostic_rows((o/'before-owner-diagnostics.txt').read_text())
 text=restore_labels(pc.emit_padded_assembly(old,b/'conker/retail_layout.us.txt','generated_179F30',word_patches_path=b/'conker/retail_word_patches.us.csv',rodata_symbol='jtbl_800A5E20'),b/'conker/asm/179F30.s');oldobj=where/'reference-before.padded.o';assemble(text,oldobj);assert oldobj.read_bytes()==(b/'conker/build/src/game/generated_179F30.c.o').read_bytes()
 lo=text.index('.globl '+fn+'\n');hi=text.index('.globl func_1514D96C\n',lo+1)
 full=(b/'conker/asm/179F30.s').read_text();body=full.split('glabel '+fn+'\n',1)[1].split('endlabel '+fn,1)[0]
 body=re.sub(r'^([ \t]*)jlabel[ \t]+([^ \t\r\n]+)[ \t]*$',r'\1.globl \2\n\1\2:',body,flags=re.M)
 # Export the same original internal labels as the frozen padded owner.
 # No candidate body, guard list or compact table is used in this reference.
 replacement='.globl '+fn+'\n.type '+fn+',@function\n'+fn+':\n'+body+'.size '+fn+',.-'+fn+'\n'
 reference_obj=where/'reference-after.o';assemble(text[:lo]+replacement+text[hi:],reference_obj);assert same_functions(oldobj,reference_obj,(fn,))==77 and normalized_pools(oldobj)==normalized_pools(reference_obj)
 reference=link(where,reference_obj,'reference');before=(b/'conker/build/conker.us.elf').read_bytes();wanted=bytearray(before);start=elf_slot_offset(wanted,0x1514D64C,800);wanted[start:start+800]=(r/'conker/conker.us.bin').read_bytes()[0x17AAFC:0x17AE1C];rows=[(pos,v)for pos,name,v,_ in symbol_rows(wanted)if name==fn];assert len(rows)==1;position,row=rows[0];assert row[1:3]==(0x1514D64C,12);struct.pack_into('>I',wanted,position+8,800)
 predicted,moved=predict_metadata(bytes(wanted),reference.read_bytes());prediction=where/'predicted.elf';prediction.write_bytes(predicted);actual=link(where,o/'make-owner/src/game/generated_179F30.c.o','linked');assert actual.read_bytes()==predicted
 q=dict(reference_uses_frozen_before_C_and_original_ASM_only=True,metadata_permuted_records=moved,predicted_ELF_sha256=sha(prediction),changed_bytes=sum(a!=b for a,b in zip(before,predicted)),exclusions=0,protected_data_audit=audit_layout(actual,r/'conker'),strict_predicted_ELF_equal=True,neighbors=77,existing_neighbor_pool_binding_preserved=True,source_installed=target_packet.installed(),matching_credit=0);(o/'private-image.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k!='metadata_permuted_records'}),flush=True);return q
if __name__=='__main__':main()
