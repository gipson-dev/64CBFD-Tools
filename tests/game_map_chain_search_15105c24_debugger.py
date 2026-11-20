"""Close the unpadded debugger's array metadata dependency without image exclusions."""
from pathlib import Path
import hashlib,json,shutil,struct
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.tests.game_owner_pool import normalized_pools
OBJECT='conker/build/src/debugger_258ED0.c.o'
OLD='6015a738e26aa68ab8aacaefce0f66de5b99aba40e55f6ce710778e855186406'
NEW='483b5099e8d671e2f9401d453e84a1fd73472237f40d96b79b6ad1b5e0a958c0'
sha=lambda b:hashlib.sha256(b).hexdigest()
def verify(root,base):
 before=base/OBJECT;after=root/OBJECT
 if sha(before.read_bytes())!=OLD or sha(after.read_bytes())!=NEW:raise ValueError('Debugger array-metadata object fingerprint changed')
 a,b=sections(before),sections(after)
 assert a.keys()==b.keys()and{n for n in a if a[n]!=b[n]}=={'.mdebug','.symtab'}
 rows=[v for v in symbol_rows(before.read_bytes())if v[1]=='D_800A5770'];assert len(rows)==1 and rows[0][2][1:]==(0,4,16,0,0)
 ar,br=a['.symtab'][1],b['.symtab'][1];expected=bytearray(ar)
 # The symbol table itself is unchanged except sizeof(s32[2]) for this extern.
 index=rows[0][0]
 # symbol_rows gives the file offset, while sections exposes the symbol bytes.
 from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,read_c_string
 data=before.read_bytes();header=ELF_HEADER.unpack_from(data);sh=[SECTION_HEADER.unpack_from(data,header[6]+i*header[11])for i in range(header[12])];names=sh[header[13]];strings=data[names[4]:names[4]+names[5]]
 symtab=next(v for v in sh if read_c_string(strings,v[0])=='.symtab');struct.pack_into('>I',expected,index-symtab[4]+8,8);assert bytes(expected)==br
 assert len(b['.mdebug'][1])-len(a['.mdebug'][1])==20
 assert same_functions(before,after)==1 and normalized_pools(before)==normalized_pools(after)
 return dict(object=OBJECT,before_sha256=OLD,after_sha256=NEW,functions_unchanged=1,changed_sections=['.mdebug','.symtab'],debug_bytes_before=len(a['.mdebug'][1]),debug_bytes_after=len(b['.mdebug'][1]),extern_size=[4,8],all_other_sections_and_relocations_identical=True,linked_image_exclusions=0)
def reproduce(root,out,spec):
 work=out/'debugger-header-pair';work.mkdir(exist_ok=True);source=(root/'conker/src/debugger_258ED0.c').read_text();objects=[];diags=[]
 for new in(False,True):
  for name in('variables.h','functions.h'):(work/name).write_text(spec['new_files'if new else'old_files']['conker/include/'+name])
  obj,diag=compile_owner(root,work,source,'debugger-canonical');copy=work/('after.o'if new else'before.o');shutil.copyfile(obj,copy);objects.append(copy);diags.append(diag)
 a,b=map(sections,objects);assert a.keys()==b.keys()and{n for n in a if a[n]!=b[n]}=={'.mdebug','.symtab'}
 assert len(b['.mdebug'][1])-len(a['.mdebug'][1])==20 and diags[0]==diags[1]
 assert same_functions(*objects)==1 and normalized_pools(objects[0])==normalized_pools(objects[1])
 # Both independent source compiles agree with the actual production function
 # bodies/bindings, rather than treating .mdebug as an exemption from code checks.
 assert same_functions(objects[0],root/OBJECT)==same_functions(objects[1],root/OBJECT)==1
 return dict(original_source_unchanged=True,old_and_new_headers_compiled=True,independent_functions_each=1,debug_growth=20,only_changes=['.mdebug','.symtab'],diagnostics_unchanged=True)
