import difflib,inspect,json,struct,subprocess,sys
from pathlib import Path
from tools.experiments import game_actor_colored_dispatch_match as p
out=p.out;root=p.root
from tools.experiments import game_remaining_donor_candidates as c
from tools.experiments.game_actor_state_tick_integration import symbol_rows,same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.pad_generated_object import parse_object
code=inspect.getsource(c.compile_owner);old="str(root / 'tools/asm-processor/asm_processor.py'), *flags,";new="str(root / 'tools/asm-processor/asm_processor.py'), *[f for f in flags if not f.startswith(('-Wo,','-D'))],";assert old in code;scope=dict(c.compile_owner.__globals__);exec(code.replace(old,new),scope);compile_owner=scope['compile_owner']
def main():
 p.freeze();source=p.MANIFEST['selected'];name='func_151026BC';helper='func_15100600'
 compile_owner(root,out,(out/'frozen/conker/src/game/generated_12DAB0.c').read_text(),'before')
 (out/'mixed_source.c').write_text(source);primary,diag=compile_owner(root,out,source,'mixed-primary',('-O2','-g3','-DCBFD_COLORED_PRIMARY'));override,diag2=compile_owner(root,out,source,'mixed-target',('-O2','-g3','-Wo,-no_const_in_reg'))
 assert not diag and not diag2
 assert same_functions(out/'before.o',primary)==23
 text,fs,rs=parse_object(override);a,n=fs[name]['value'],fs[name]['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};elf=(root/'conker/build/conker.us.elf').read_bytes();look={v[1]:v[2][1]for v in symbol_rows(elf)};look['.rodata']=0x800a2298;words=bound_blob(text[a:a+n],refs,{nm:look[nm]for es in refs.values()for _,nm in es});truth=struct.unpack_from('>75I',(root/'conker/conker.us.bin').read_bytes(),0x12fb6c);assert tuple(words)==truth
 table=sections(override)['.rodata'][1];offsets=struct.unpack_from('>41I',table);retail_table=struct.unpack_from('>41I',elf,0x242b20+0x800a2298-0x80082b20);assert tuple(0x151026bc+(v-a)for v in offsets)==retail_table
 def assemble(text,label):
  p=out/(label+'.s');p.write_text(text);o=p.with_suffix('.o');r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o),str(p)],cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr);return o
 guards=root/'conker/retail_word_patches.us.csv';over={name:override};asm=root/'conker/asm/12DAB0.s';layout=root/'conker/retail_layout.us.txt';anchor='jtbl_800A2298_game'
 gen=assemble(pad_generated_object.emit_padded_assembly(primary,asm,function_objects=over,word_patches_path=guards,filename='generated_12DAB0',rodata_symbol=anchor),'mixed-generated')
 generic=assemble(pad_c_object.emit_padded_assembly(primary,layout,'generated_12DAB0',function_objects=over,word_patches_path=guards,rodata_symbol=anchor),'mixed-generic')
 assert same_functions(root/'conker/build/src/game/generated_12DAB0.c.o',gen,(name,))==22
 def payload(path):
  t,f,r=parse_object(path);a,n=f[name]['value'],f[name]['size'];return t[a:a+n],{i-a:v for i,v in r.items()if a<=i<a+n}
 assert payload(gen)==payload(generic)
 body,refs=payload(gen);bound=bound_blob(body,refs,{nm:look[nm]for es in refs.values()for _,nm in es});assert tuple(bound)==truth
 report=dict(words=n//4,bound_differences=0,table_entries=41,primary_owner_functions_unchanged=23,padded_owner_neighbors_unchanged=22,dual_padder_target_agrees=True,helper_stub_unchanged=True,profile='target-only no_const_in_reg',source_installed=False)
 (out/'mixed.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
