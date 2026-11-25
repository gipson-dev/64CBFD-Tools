"""Independent before-owner/retail-ASM reference and literal full-ELF predictor.

The reference is built without the recovered parent C or its guards. Only
named metadata ordering comes from that reference link; every definition
and string value is reconstructed from the frozen baseline.
"""
from pathlib import Path
from collections import Counter,defaultdict,deque
import hashlib,json,re,struct,subprocess,sys
from tools.experiments import game_local_vector_transform_15117da4_match as packet
r,o=packet.ROOT,packet.OUT
b=o/'baseline'
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.check_game_data_layout import audit_layout
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();NAME='func_15117DA4'
def assemble(text,path):
 src=path.with_suffix('.s');src.write_text(text);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(src)],capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
def link(where,objects,label):
 text=(b/'conker/build/conker.ld').read_text()
 for source,obj in objects.items():
  old=source.removeprefix('conker/');assert text.count(old)==1;text=text.replace(old,obj.relative_to(r/'conker').as_posix())
 script=where/(label+'.ld');script.write_text(text);image=where/(label+'.elf')
 q=subprocess.run(['mips-linux-gnu-ld','-T',script.relative_to(r/'conker').as_posix(),*['-T'+n for n in('undefined_syms.us.txt','undefined_funcs.us.txt','undefined_syms_auto.txt','undefined_funcs_auto.txt')],'--no-check-sections','--no-warn-mismatch','-o',image.relative_to(r/'conker').as_posix()],cwd=r/'conker',capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr;return image
def headers(blob):
 at=struct.unpack_from('>I',blob,32)[0];size,count,names=struct.unpack_from('>HHH',blob,46);rows=[struct.unpack_from('>10I',blob,at+i*size)for i in range(count)];h=rows[names];pool=blob[h[4]:h[4]+h[5]]
 return {pool[h[0]:].split(b'\0',1)[0].decode():h for h in rows}
def token(name,row):return(name,*row[1:])
def predict(before,reference):
 expected=bytearray(before)
 for name,va,data in [(NAME,0x15117da4,(r/'conker/conker.us.bin').read_bytes()[0x145254:0x1453ec])]:
  at=elf_slot_offset(before,va,len(data));expected[at:at+len(data)]=data
  syms=[(p,v)for p,n,v,_ in symbol_rows(expected)if n==name];assert len(syms)==1;p,v=syms[0];assert v[1:3]==(va,12);struct.pack_into('>I',expected,p+8,408)
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
 packet.prepare();where=o/'image-qualification';where.mkdir(exist_ok=True);objects={};reports={}
 for label,source,filename,asm,pool,fn,nextfn,bytesize,neighbors in [('owner',packet.MANIFEST['source'],'generated_142560',b/'conker/asm/142560.s',None,NAME,'func_15117F3C',408,json.loads((o/'objects.json').read_text())['neighbors'])]:
  raw,_=compile_owner(r,where,(b/source).read_text(),'reference-'+label)
  text=packet.restore_labels(pc.emit_padded_assembly(raw,b/'conker/retail_layout.us.txt',filename,rodata_symbol=pool,word_patches_path=b/'conker/retail_word_patches.us.csv'),asm);before_obj=where/('reference-before-'+label+'.o');assemble(text,before_obj);objpath='conker/build/'+source.removeprefix('conker/')+'.o';assert before_obj.read_bytes()==(b/objpath).read_bytes()
  lo=text.index('.globl '+fn+'\n');hi=text.index('.globl '+nextfn+'\n',lo+1)if nextfn else len(text)
  data,refs=payload(o/'original-target.o',fn);assert len(data)==408
  # Preserve the original slot end while replacing exactly the one body.
  fragment=text[lo:hi];assert '.globl 'not in fragment[len('.globl '+fn+'\n'):]
  assert '.space 0x%X, 0'%(bytesize-12)in fragment
  replacement=packet.assembly(data,refs,fn);replacement=replacement[replacement.index('.globl '):]+'\n'
  if bytesize>len(data):replacement+=f'.space 0x{bytesize-len(data):X}, 0\n\n'
  obj=where/('reference-after-'+label+'.o');assemble(text[:lo]+replacement+text[hi:],obj);assert payload(obj,fn)==(data,refs);assert same_functions(before_obj,obj,(fn,))==neighbors;objects[objpath]=obj;reports[label]=dict(neighbors=neighbors,explicit_body_bytes=len(data))
 reference=link(where,objects,'reference');before=(b/'conker/build/conker.us.elf').read_bytes();predicted,moved=predict(before,reference.read_bytes());prediction=where/'predicted.elf';prediction.write_bytes(predicted)
 actual=link(where,{packet.MANIFEST['object']:o/'make-owner/src/game/generated_142560.c.o'},'linked');assert actual.read_bytes()==predicted
 report=dict(reference_uses_frozen_before_C_and_original_target_ASM=True,owner_reports=reports,metadata_permuted_records=moved,predicted_ELF_sha256=sha(prediction),changed_bytes=sum(a!=z for a,z in zip(before,predicted)),exclusions=0,original_body_words=102,retail_slot_words=102,owner_padding_words=0,owner_padding_unchanged=True,protected_data_audit=audit_layout(actual,r/'conker'),strict_predicted_ELF_equal=True,source_installed=packet.installed(),matching_credit=0)
 (o/'image-qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='metadata_permuted_records'}),flush=True);return report
if __name__=='__main__':main()
