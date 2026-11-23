"""Literal independent full image: original update ASM and ABI-only frozen C.

All five changed function windows and declared sizes are reconstructed; there
are no dependent-object, code, data, metadata or symbol/string exclusions.
"""
from pathlib import Path
from collections import Counter,defaultdict,deque
import hashlib,json,struct,subprocess,sys
from tools.experiments import game_actor_effect_update_15196748_match as packet
from tools.experiments import game_actor_effect_update_15196748_abi as abi
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.check_game_data_layout import audit_layout
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
r,o=packet.ROOT,packet.OUT;b=o/'baseline';NAME=packet.FUNCTION;sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def assemble(text,path):
 src=path.with_suffix('.s');src.write_text(text);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(src)],capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
def link(where,obj,label):
 text=(b/'conker/build/conker.ld').read_text();old='build/src/game/generated_1C2C60.c.o';assert text.count(old)==1;text=text.replace(old,obj.relative_to(r/'conker').as_posix());script=where/(label+'.ld');script.write_text(text);image=where/(label+'.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',script.relative_to(r/'conker').as_posix(),*['-T'+n for n in('undefined_syms.us.txt','undefined_funcs.us.txt','undefined_syms_auto.txt','undefined_funcs_auto.txt')],'--no-check-sections','--no-warn-mismatch','-o',image.relative_to(r/'conker').as_posix()],cwd=r/'conker',capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr;return image
def headers(blob):
 at=struct.unpack_from('>I',blob,32)[0];size,count,names=struct.unpack_from('>HHH',blob,46);rows=[struct.unpack_from('>10I',blob,at+i*size)for i in range(count)];h=rows[names];pool=blob[h[4]:h[4]+h[5]];return{pool[h[0]:].split(b'\0',1)[0].decode():h for h in rows}
def token(name,row):return(name,*row[1:])
def predict(before,reference):
 expected=bytearray(before);windows={NAME:dict(entry=0x15196748,bytes=1028,code=(r/'conker/conker.us.bin').read_bytes()[0x1C3BF8:0x1C3FFC])}
 for name,slot in packet.MANIFEST['helper_slots'].items():
  data,refs=payload(o/'ABI-qualified/candidate.o',name);assert not refs and len(data)==16;windows[name]=dict(**slot,code=data)
 for name,row in windows.items():
  at=elf_slot_offset(before,row['entry'],row['bytes']);old,refs=payload(o/'selected-final/before.o',name);assert not refs and len(old)==12;assert before[at:at+row['bytes']]==old+bytes(row['bytes']-12),(name,'unexpected old slot')
  expected[at:at+row['bytes']]=row['code']+bytes(row['bytes']-len(row['code']));symbols=[(p,v)for p,n,v,_ in symbol_rows(expected)if n==name];assert len(symbols)==1;p,v=symbols[0];assert v[1:3]==(row['entry'],12);struct.pack_into('>I',expected,p+8,len(row['code']))
 h,rh=headers(expected),headers(reference);assert h==rh and expected[:52]==reference[:52]and len(expected)==len(reference),'ELF geometry changed';oldrows=symbol_rows(expected);newrows=symbol_rows(reference);assert Counter(token(n,v)for _,n,v,_ in oldrows)==Counter(token(n,v)for _,n,v,_ in newrows),'Unexpected named definition change'
 records=defaultdict(deque)
 for _,name,row,_ in oldrows:records[token(name,row)].append(row)
 pool=bytearray(h['.strtab'][5]);covered=bytearray(len(pool));covered[0]=1;sym_start=h['.symtab'][4];strings_start=h['.strtab'][4]
 for position,name,row,_ in newrows:
  assert sym_start<=position<sym_start+h['.symtab'][5]and(position-sym_start)%16==0;old=records[token(name,row)].popleft();struct.pack_into('>IIIBBH',expected,position,row[0],*old[1:]);encoded=name.encode()+b'\0';start=row[0];assert start+len(encoded)<=len(pool)
  for i,value in enumerate(encoded):
   at=start+i;assert not covered[at]or pool[at]==value,('conflicting string',name,at);pool[at]=value;covered[at]=1
 assert not any(records.values())and all(covered);expected[strings_start:strings_start+len(pool)]=pool;assert expected==reference,'Independent reference reconstruction differs'
 moved=[dict(index=i,before=a[1],after=z[1])for i,(a,z)in enumerate(zip(oldrows,newrows))if a[1]!=z[1]];return bytes(expected),moved
def main():
 packet.prepare();where=o/'image-qualification';where.mkdir(exist_ok=True);old,_=compile_owner(r,where,packet.MANIFEST['old_source'],'reference-before',('-O2','-g3'));oldtext=pc.emit_padded_assembly(old,b/'conker/retail_layout.us.txt','generated_1C2C60',word_patches_path=b/'conker/retail_word_patches.us.csv');before_obj=where/'reference-before-padded.o';assemble(oldtext,before_obj);assert before_obj.read_bytes()==(b/'conker/build/src/game/generated_1C2C60.c.o').read_bytes()
 abi_raw,_=compile_owner(r,where,abi.recover(packet.MANIFEST['old_source']),'reference-ABI-only',('-O2','-g3'));assert same_functions(old,abi_raw,packet.MANIFEST['helper_names'])==65
 text=pc.emit_padded_assembly(abi_raw,b/'conker/retail_layout.us.txt','generated_1C2C60',word_patches_path=b/'conker/retail_word_patches.us.csv');abi_obj=where/'reference-ABI-padded.o';assemble(text,abi_obj)
 data,refs=payload(o/'original-target.o',NAME);assert len(data)==1028;replacement='.globl '+NAME+'\n.type '+NAME+', @function\n'+NAME+':\n'
 for i,(word,)in enumerate(struct.iter_unpack('>I',data)):
  for kind,name in refs.get(4*i,[]):replacement+=f'.reloc ., {kind}, {name}\n'
  replacement+=f'.word 0x{word:08X}\n'
 replacement+='.size '+NAME+', . - '+NAME+'\n\n';lo=text.index('.globl '+NAME+'\n');hi=text.index('.globl ',lo+8);after_obj=where/'reference-owner.o';assemble(text[:lo]+replacement+text[hi:],after_obj);assert payload(after_obj,NAME)==(data,refs)and same_functions(abi_obj,after_obj,(NAME,))==68
 reference=link(where,after_obj,'reference');before=(b/'conker/build/conker.us.elf').read_bytes();predicted,moved=predict(before,reference.read_bytes());prediction=where/'predicted.elf';prediction.write_bytes(predicted)
 report=dict(reference_before_owner_equals_frozen_object=True,reference_uses_only_original_update_ASM_and_frozen_ABI_only_C=True,other_64_neighbors_fixed=True,ABI_only_stubs=4,named_definition_multiset_preserved_except_five_sizes=True,string_pool_completely_reconstructed=True,metadata_permuted_records=moved,predicted_ELF_sha256=sha(prediction),changed_bytes=sum(a!=z for a,z in zip(before,predicted)),exclusions=0,protected_data_audit=audit_layout(reference,r/'conker'),source_installed=packet.installed(),matching_credit=0)
 if '--predict-only'not in sys.argv:
  actual=link(where,o/'make-owner/src/game/generated_1C2C60.c.o','linked');assert actual.read_bytes()==predicted;report.update(strict_predicted_ELF_equal=True,ELF_sha256=sha(actual))
 (o/('image-prediction.json'if '--predict-only'in sys.argv else'image-qualification.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='metadata_permuted_records'}),flush=True);return report
