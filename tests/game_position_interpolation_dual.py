from pathlib import Path
import sys,struct,json,subprocess
from tools.experiments import game_position_interpolation_match as source
root=source.root;p=source.out
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import same_functions

def main():
 name='func_150BE2E8';owner='generated_EB340';target=p/'make-shadow/src/game/generated_EB340.c.o';primary=Path(str(target)+'.compact');override=Path(str(target)+'.float.compact');guards=p/'proposed-guards.csv';layout=root/'conker/retail_layout.us.txt';asm=root/'conker/asm/EB340.s'
 def assemble(text,label):
  src=p/(label+'.s');src.write_text(text);out=src.with_suffix('.o');proc=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out),str(src)],cwd=root/'conker',capture_output=True,text=True);assert proc.returncode==0,(proc.stdout,proc.stderr);return out
 kwargs=dict(function_objects={name:override},word_patches_path=guards,filename=owner)
 gen=assemble(pad_generated_object.emit_padded_assembly(primary,asm,**kwargs),'dual-generated')
 generic=assemble(pad_c_object.emit_padded_assembly(primary,layout,owner,function_objects={name:override},word_patches_path=guards),'dual-generic')
 def payload(path):
  text,fs,rs=parse_object(path);a,n=fs[name]['value'],fs[name]['size'];return text[a:a+n],{i-a:v for i,v in rs.items() if a<=i<a+n}
 assert payload(target)==payload(gen)==payload(generic);assert same_functions(p/'frozen/conker/build/src/game/generated_EB340.c.o',gen,(name,))==7
 whole=asm.read_text();body='glabel '+name+'\n'+whole.split('glabel '+name+'\n',1)[1].split('endlabel '+name,1)[0]+'endlabel '+name+'\n';original=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+body+'.size '+name+',.-'+name+'\n','isolated-retail')
 paths=[original]
 for i,path in enumerate((gen,generic)):
  raw,refs=payload(path);text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+name+'\n.type '+name+',@function\n'+name+':\n'
  for j,(word,) in enumerate(struct.iter_unpack('>I',raw)):
   for kind,symbol in refs.get(4*j,[]):text+='.reloc ., '+kind+', '+symbol+'\n'
   text+=f'.word 0x{word:08X}\n'
  paths.append(assemble(text+'.size '+name+',.-'+name+'\n',f'isolated-{i}'))
 links=0
 for low in (0,0x7ffc,0x8000,0xfffc):
  variants=[];syms={'D_800A0068':0x80010000|low,'D_800BE9E4':0x80020000|low}
  for i,path in enumerate(paths):
   script=p/f'rebase-{i}-{low:04x}.ld';script.write_text(f'SECTIONS {{ .text 0x150BE2E8 : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf');proc=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',name,*[f'--defsym={k}=0x{v:X}' for k,v in syms.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert proc.returncode==0,proc.stderr
   binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True);variants.append(struct.unpack_from('>84I',binary.read_bytes()));links+=1
  assert variants[0]==variants[1]==variants[2],hex(low)
 report=dict(dual_padders=True,unchanged_owner_neighbors=7,rebases=4,gnu_links=links,guards=10,source_installed=(__import__('hashlib').sha256((root/'conker/src/game/generated_EB340.c').read_bytes()).hexdigest()==source.MANIFEST['installed']['conker/src/game/generated_EB340.c']));(p/'dual-qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__ == "__main__":main()
