"""Independent before-C plus literal ASM full-image predictor; zero exclusions."""
from pathlib import Path
import json,struct,sys,hashlib,subprocess
from collections import Counter,defaultdict,deque
sys.path.insert(0,str(Path.cwd()))
from tools.experiments import game_resource_record_query_150eb484_match as packet
r=packet.ROOT;o=packet.OUT;b=o/"baseline"
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

from tools import pad_c_object as pc
from tools.experiments.game_local_vector_transform_15117da4_match import restore_labels,assembly
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.check_game_data_layout import audit_layout
from tools.tests.game_owner_pool import normalized_pools
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def predict_metadata(wanted,reference):
 expected=bytearray(wanted);h,ref_h=headers(expected),headers(reference)
 assert h==ref_h and expected[:52]==reference[:52]and len(expected)==len(reference),'ELF geometry changed'
 oldrows,newrows=symbol_rows(expected),symbol_rows(reference)
 assert Counter(token(n,v)for _,n,v,_ in oldrows)==Counter(token(n,v)for _,n,v,_ in newrows),'Unexpected named definition change'
 records=defaultdict(deque)
 for _,name,row,_ in oldrows:records[token(name,row)].append(row)
 pool=bytearray(h['.strtab'][5]);covered=bytearray(len(pool));covered[0]=1
 for position,name,row,_ in newrows:
  assert h['.symtab'][4]<=position<h['.symtab'][4]+h['.symtab'][5]and(position-h['.symtab'][4])%16==0
  old=records[token(name,row)].popleft();struct.pack_into('>IIIBBH',expected,position,row[0],*old[1:]);encoded=name.encode()+b'\0';start=row[0];assert start+len(encoded)<=len(pool)
  for i,value in enumerate(encoded):
   at=start+i;assert not covered[at]or pool[at]==value;pool[at]=value;covered[at]=1
 assert not any(records.values())and all(covered)
 expected[h['.strtab'][4]:h['.strtab'][4]+len(pool)]=pool
 assert expected==reference,'Independent baseline/reference reconstruction differs'
 return bytes(expected),[dict(index=i,before=a[1],after=z[1])for i,(a,z)in enumerate(zip(oldrows,newrows))if a[1]!=z[1]]
def main():
 packet.prepare()
 where=o/'image-qualification';where.mkdir(exist_ok=True);objects={};reports=[];patches=[]
 target,tr=payload(o/'original-target.o','func_150EB484');assert len(target)==400
 literal=[('1188E0','func_150EB484','func_150EB614',0x150eb484,400,target,tr),('1188E0','func_150EBC80',None,0x150ebc80,576,struct.pack('>6I',0xafa40000,0xafa50004,0xafa60008,0x00001025,0x03e00008,0),{}),('CDE80','func_150A3504',None,0x150a3504,1388,struct.pack('>7I',0xafa40000,0xafa50004,0xafa60008,0xafa7000c,0x00001025,0x03e00008,0),{})]
 for owner in ('1188E0','CDE80'):
  source='conker/src/game/generated_'+owner+'.c';objpath='conker/build/src/game/generated_'+owner+'.c.o';raw,diag=compile_owner(r,where,(b/source).read_text(),'reference-before-'+owner);assert not diag
  text=restore_labels(pc.emit_padded_assembly(raw,b/'conker/retail_layout.us.txt','generated_'+owner,word_patches_path=b/'conker/retail_word_patches.us.csv'),b/('conker/asm/'+owner+'.s'))
  old=where/('reference-before-'+owner+'.padded.o');assemble(text,old);assert old.read_bytes()==(b/objpath).read_bytes();changed=[]
  for own,fn,nextfn,va,slot,data,refs in literal:
   if own!=owner:continue
   lo=text.index('.globl '+fn+'\n');hi=text.index('.globl '+nextfn+'\n',lo+1)if nextfn else text.index('.section ',lo+1)if '.section 'in text[lo+1:]else len(text)
   fragment=text[lo:hi];assert fragment.count('.globl ')==1,fn
   replacement=assembly(data,refs,fn);replacement=replacement[replacement.index('.globl '):]+'\n'
   if slot>len(data):replacement+=f'.space 0x{slot-len(data):X}, 0\n\n'
   text=text[:lo]+replacement+text[hi:];patches.append((fn,va,slot,data));changed.append(fn)
  out=where/('reference-after-'+owner+'.o');assemble(text,out);neighbors=same_functions(old,out,changed);assert normalized_pools(old)==normalized_pools(out)
  actual=o/('make-owner/src/game/generated_'+owner+'.c.o');assert same_functions(out,actual,())==neighbors+len(changed)and normalized_pools(out)==normalized_pools(actual)
  objects[objpath]=out;reports.append(dict(owner=owner,unchanged_functions=neighbors,explicit_replacement_functions=changed))
 reference=link(where,objects,'reference');before=(b/'conker/build/conker.us.elf').read_bytes();wanted=bytearray(before)
 for fn,va,slot,data in patches:
  # Target gets original executable bytes; stubs get only explicit argument homes.
  if fn=='func_150EB484':data=(r/'conker/conker.us.bin').read_bytes()[0x118934:0x118ac4]
  at=elf_slot_offset(wanted,va,slot);wanted[at:at+slot]=data+bytes(slot-len(data));syms=[(p,v)for p,n,v,_ in symbol_rows(wanted)if n==fn];assert len(syms)==1;p,v=syms[0];assert v[1:3]==(va,12);struct.pack_into('>I',wanted,p+8,len(data))
 predicted,moved=predict_metadata(bytes(wanted),reference.read_bytes());(where/'predicted.elf').write_bytes(predicted)
 actual=link(where,{p:o/('make-owner/'+p.removeprefix('conker/build/'))for p in objects},'linked');assert actual.read_bytes()==predicted
 q=dict(reference_from_frozen_before_C_and_original_target_ASM=True,typed_stub_argument_homes_explicitly_predicted=True,owners=reports,metadata_permuted_records=moved,predicted_ELF_sha256=sha(where/'predicted.elf'),changed_bytes=sum(a!=z for a,z in zip(before,predicted)),exclusions=0,protected_data_audit=audit_layout(actual,r/'conker'),strict_predicted_ELF_equal=True,source_installed=packet.installed(),matching_credit=0)
 (o/'image-qualification.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k!='metadata_permuted_records'}),flush=True);return q
if __name__=='__main__':main()
