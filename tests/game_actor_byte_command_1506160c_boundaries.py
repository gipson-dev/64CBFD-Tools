"""Direct target equality through both padders and sixteen independent GNU links."""
from pathlib import Path
import csv,json,struct,subprocess,sys
from tools.experiments import game_actor_byte_command_1506160c_match as packet
root,out=packet.ROOT,packet.OUT
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_path_heading_turn_roles import bound_blob
NAME='func_1506160C'
def main():
 def assemble(text,name):
  p=out/(name+'.s');p.write_text(text);obj=p.with_suffix('.o')
  q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(p)],capture_output=True,text=True)
  assert q.returncode==0 and not q.stdout and not q.stderr,(q.stdout,q.stderr);return obj
 raw,refs=payload(out/'high-mask/candidate.o',NAME)
 text='.set noat\n.set noreorder\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  for k,n in refs.get(4*i,[]):text+=f'.reloc ., {k}, {n}\n'
  text+=f'.word 0x{w:08X}\n'
 target=assemble(text+'.size '+NAME+',.-'+NAME+'\n','isolated-target')
 lines=(root/'conker/retail_layout.us.txt').read_text().splitlines();selected=[v for v in lines[1:]if v.split(',')[1:3]==['game_83300',NAME]];assert len(selected)==1
 layout=out/'target-layout.csv';layout.write_text(lines[0]+'\n'+selected[0]+'\n')
 guards=out/'empty-target-guards.csv';guards.write_bytes((out/'baseline/conker/retail_word_patches.us.csv').read_bytes().splitlines(keepends=True)[0])
 original_path=root/'conker/asm/nonmatchings/game_83300/func_1506160C.s'
 generic=assemble(pc.emit_padded_assembly(target,layout,'game_83300',word_patches_path=guards),'target-generic')
 generated=assemble(pg.emit_padded_assembly(target,original_path,filename='game_83300',word_patches_path=guards),'target-generated')
 original=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+original_path.read_text()+'\n.size '+NAME+',.-'+NAME+'\n','original-target')
 assert payload(target,NAME)==payload(generic,NAME)==payload(generated,NAME)==payload(original,NAME)
 links=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  symbols={'D_800DBFF4':0x80100000+low};streams=[]
  for label,path in(('raw',target),('generic',generic),('generated',generated),('retail',original)):
   script=out/f'link-{low:X}-{label}.ld';script.write_text('SECTIONS { .text 0x1506160C : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf')
   q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,'--defsym=D_800DBFF4=0x%X'%symbols['D_800DBFF4'],'-o',str(elf),str(path)],capture_output=True,text=True)
   assert q.returncode==0,q.stderr;code=sections(elf)['.text'][1];assert len(code)==432
   assert list(struct.unpack('>108I',code))==bound_blob(*payload(path,NAME),symbols);streams.append(code);links+=1
  assert len(set(streams))==1
 r=dict(raw_generic_generated_original_equal=True,GNU_links=links,rebases=4,body_words=108,frame=0,guards=0,insertions=0,omissions=0,
  trailing_padding_bytes=0,relocation_sites=len(refs),HI16_carry_boundaries=True,source_installed=packet.installed(),matching_credit=0)
 (out/'boundaries.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
