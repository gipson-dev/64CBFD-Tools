"""Both direct padders and sixteen independent GNU relocation links."""
from pathlib import Path
import csv,json,struct,subprocess,sys
from tools.experiments import game_view_color_script_150d08c0_match as packet
root,out=packet.ROOT,packet.OUT
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_classifier_candidates import sections
NAME='func_150D08C0'

def assemble(text,name):
 p=out/(name+'.s');p.write_text(text);obj=p.with_suffix('.o')
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(p)],cwd=root/'conker',capture_output=True,text=True)
 assert q.returncode==0 and not q.stdout and not q.stderr,(q.stdout,q.stderr);return obj

def main():
 raw,refs=payload(out/'qualified-source/candidate.o',NAME)
 text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(4*i,[]):text+='.reloc ., '+kind+', '+name+'\n'
  text+='.word 0x%08X\n'%w
 text+='.size '+NAME+',.-'+NAME+'\n';target=assemble(text,'target-raw');assert payload(target,NAME)==(raw,refs)
 lines=(root/'conker/retail_layout.us.txt').read_text().splitlines();rows=[v for v in lines[1:]if v.split(',')[1:3]==['generated_FDD70',NAME]];assert len(rows)==1
 layout=out/'target-layout.csv';layout.write_text(lines[0]+'\n'+rows[0]+'\n')
 full=(root/'conker/asm/FDD70.s').read_text();body='glabel '+NAME+full.split('glabel '+NAME,1)[1].split('endlabel '+NAME,1)[0]+'endlabel '+NAME
 asm=out/'original-target.s';asm.write_text(body+'\n');guards=out/'baseline/conker/retail_word_patches.us.csv'
 assert not any(r['function']==NAME for r in csv.DictReader(guards.open()))
 generic=assemble(pc.emit_padded_assembly(target,layout,'generated_FDD70',word_patches_path=guards),'target-generic')
 generated=assemble(pg.emit_padded_assembly(target,asm,filename='generated_FDD70',word_patches_path=guards),'target-generated')
 original=out/'image-qualification/retail.o'
 assert payload(target,NAME)==payload(generic,NAME)==payload(generated,NAME)==payload(original,NAME)
 paths=(target,generic,generated,original);links=0
 names={n for values in refs.values()for _,n in values};calls={n for values in refs.values()for k,n in values if k=='R_MIPS_26'}
 for low in(0,0x7FF8,0x8000,0xFFF8):
  symbols={n:0x15210000+0x20000*i+low for i,n in enumerate(sorted(calls))}
  symbols.update({n:0x80100000+0x20000*i+low for i,n in enumerate(sorted(names-calls))})
  streams=[]
  for i,p in enumerate(paths):
   expected=bound_blob(*payload(p,NAME),symbols);streams.append(expected)
   script=out/('bind-%X-%d.ld'%(low,i));script.write_text('SECTIONS { .text 0x150D08C0 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf')
   q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(p)],capture_output=True,text=True)
   assert q.returncode==0,q.stderr
   linked=sections(elf)['.text'][1];assert len(linked)in(1488,1488)and not any(linked[1488:])
   assert list(struct.unpack_from('>372I',linked))==expected;links+=1
  assert streams[0]==streams[1]==streams[2]==streams[3]
 r=dict(GNU_rebased_links=links,guards=0,raw_generic_generated_original_equal=True,
        retail_slot_tail_padding_bytes=0,relocation_sites_covered=len(refs),HI16_carry_boundaries=True,body_bytes=1488,possible_GNU_alignment_bytes=0,
        guard_manifest_unchanged=True,source_installed=packet.installed(),matching_credit=0)
 (out/'boundaries.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
