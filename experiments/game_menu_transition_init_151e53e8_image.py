"""Independent before-owner/retail-ASM reference and literal full-ELF predictor.

The reference is built without the recovered parent C or its guards. Only
named metadata ordering comes from that reference link; every definition
and string value is reconstructed from the frozen baseline.
"""
from pathlib import Path
from collections import Counter,defaultdict,deque
import hashlib,json,struct,subprocess,sys
from tools.experiments import game_menu_transition_init_151e53e8_match as packet
r,o=packet.ROOT,packet.OUT
b=o/'baseline'
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.check_game_data_layout import audit_layout
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();NAME='func_151E53E8'
def assemble(text,path):
 src=path.with_suffix('.s');src.write_text(text);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(src)],capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
def link(where,obj,label):
 text=(b/'conker/build/conker.ld').read_text();old='build/src/game/generated_20AE20.c.o';assert text.count(old)==1;text=text.replace(old,obj.relative_to(r/'conker').as_posix());script=where/(label+'.ld');script.write_text(text);image=where/(label+'.elf')
 q=subprocess.run(['mips-linux-gnu-ld','-T',script.relative_to(r/'conker').as_posix(),*['-T'+n for n in('undefined_syms.us.txt','undefined_funcs.us.txt','undefined_syms_auto.txt','undefined_funcs_auto.txt')],'--no-check-sections','--no-warn-mismatch','-o',image.relative_to(r/'conker').as_posix()],cwd=r/'conker',capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr;return image
def headers(blob):
 at=struct.unpack_from('>I',blob,32)[0];size,count,names=struct.unpack_from('>HHH',blob,46);rows=[struct.unpack_from('>10I',blob,at+i*size)for i in range(count)];h=rows[names];pool=blob[h[4]:h[4]+h[5]]
 return {pool[h[0]:].split(b'\0',1)[0].decode():h for h in rows}
def token(name,row):return(name,*row[1:])
def predict(before,reference):
 expected=bytearray(before);at=elf_slot_offset(before,0x151E53E8,404);expected[at:at+404]=(r/'conker/conker.us.bin').read_bytes()[0x212898:0x212A2C]
 symbols=[(p,v)for p,n,v,_ in symbol_rows(expected)if n==NAME];assert len(symbols)==1;p,v=symbols[0];assert v[1:3]==(0x151E53E8,12);struct.pack_into('>I',expected,p+8,404)
 h,ref_h=headers(expected),headers(reference);assert h==ref_h and expected[:52]==reference[:52]and len(expected)==len(reference),'ELF geometry changed'
 oldrows=symbol_rows(expected);newrows=symbol_rows(reference);assert Counter(token(n,v)for _,n,v,_ in oldrows)==Counter(token(n,v)for _,n,v,_ in newrows),'Unexpected named definition change'
 records=defaultdict(deque)
 for _,name,row,_ in oldrows:records[token(name,row)].append(row)
 pool=bytearray(h['.strtab'][5]);covered=bytearray(len(pool));covered[0]=1;sym_start=h['.symtab'][4];strings_start=h['.strtab'][4]
 for index,(position,name,row,_)in enumerate(newrows):
  assert sym_start<=position<sym_start+h['.symtab'][5] and (position-sym_start)%16==0
  old=records[token(name,row)].popleft();struct.pack_into('>IIIBBH',expected,position,row[0],*old[1:]);encoded=name.encode()+b'\0';start=row[0];assert start+len(encoded)<=len(pool)
  for i,value in enumerate(encoded):
   at=start+i;assert not covered[at]or pool[at]==value,('Conflicting string reconstruction',name,at);pool[at]=value;covered[at]=1
 assert not any(records.values());assert all(covered),('Unreferenced string bytes',sum(not v for v in covered))
 expected[strings_start:strings_start+len(pool)]=pool
 assert expected==reference,'Independent baseline/reference reconstruction differs'
 oldnames=[n for _,n,_,_ in oldrows];newnames=[n for _,n,_,_ in newrows];moved=[dict(index=i,before=a,after=z)for i,(a,z)in enumerate(zip(oldnames,newnames))if a!=z]
 return bytes(expected),moved
def main():
 packet.prepare()
 where=o/'image-qualification';where.mkdir(exist_ok=True)
 old,_=compile_owner(r,where,(b/'conker/src/game/generated_20AE20.c').read_text(),'reference-before',('-O2','-g3'))
 text=pg.emit_padded_assembly(old,b/'conker/asm/20AE20.s',filename='generated_20AE20',rodata_symbol='jtbl_800AB994',word_patches_path=b/'conker/retail_word_patches.us.csv');before_obj=where/'reference-before-padded.o';assemble(text,before_obj)
 assert before_obj.read_bytes()==(b/'conker/build/src/game/generated_20AE20.c.o').read_bytes(),'Before assembly is not the frozen complete owner'
 data,refs=payload(o/'original-target.o',NAME);assert len(data)==404
 replacement='.globl '+NAME+'\n.type '+NAME+', @function\n'+NAME+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',data)):
  for kind,name in refs.get(4*i,[]):replacement+=f'.reloc ., {kind}, {name}\n'
  replacement+=f'.word 0x{w:08X}\n'
 replacement+='.size '+NAME+', . - '+NAME+'\n\n'
 lo=text.index('.globl '+NAME+'\n');hi=text.index('.globl func_151E557C\n',lo);assert '.space 0x188, 0'in text[lo:hi]
 reference_dir=where/'reference-src';reference_dir.mkdir(exist_ok=True);after_obj=reference_dir/'generated_20AE20.c.o';assemble(text[:lo]+replacement+text[hi:],after_obj);assert payload(after_obj,NAME)==(data,refs)and same_functions(before_obj,after_obj,(NAME,))==59
 reference=link(where,after_obj,'reference');before=(b/'conker/build/conker.us.elf').read_bytes();predicted,moved=predict(before,reference.read_bytes());prediction=where/'predicted.elf';prediction.write_bytes(predicted)
 report=dict(reference_before_owner_equals_frozen_object=True,reference_uses_only_frozen_before_C_and_original_target_ASM=True,all_59_reference_neighbors_fixed=True,named_definition_multiset_preserved_except_target_size=True,string_pool_completely_reconstructed=True,metadata_permuted_records=moved,predicted_ELF_sha256=sha(prediction),changed_bytes=sum(a!=z for a,z in zip(before,predicted)),exclusions=0,protected_data_audit=audit_layout(reference,r/'conker'),source_installed=packet.installed(),matching_credit=0)
 if '--predict-only'not in sys.argv:
  actual=link(where,o/'make-owner/src/game/generated_20AE20.c.o','linked');assert actual.read_bytes()==predicted,'Actual C full image differs from independent prediction'
  report.update(strict_predicted_ELF_equal=True,ELF_sha256=sha(actual))
 (o/('image-prediction.json'if '--predict-only'in sys.argv else'image-qualification.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='metadata_permuted_records'}),flush=True);return report
if __name__=='__main__':main()
