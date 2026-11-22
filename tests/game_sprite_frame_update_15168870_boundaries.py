"""Both isolated production padders, exact comparison controls and symbol rebases."""
from pathlib import Path
import csv,json,struct,subprocess,sys
from tools.experiments import game_sprite_frame_update_15168870_match as packet
root,out=packet.ROOT,packet.OUT
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
NAME='func_15168870'
def main():
 where=out/'boundaries';where.mkdir(exist_ok=True);raw,refs=payload(out/'frames-mod32/candidate.o',NAME)
 def assemble(text,label):
  p=where/(label+'.s');p.write_text(text);obj=p.with_suffix('.o')
  q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(p)],capture_output=True,text=True);assert q.returncode==0,q.stderr;return obj
 def text(data,relocs):
  result='.set noat\n.set noreorder\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
  for i,(w,)in enumerate(struct.iter_unpack('>I',data)):
   for kind,name in relocs.get(4*i,[]):result+=f'.reloc ., {kind}, {name}\n'
   result+=f'.word 0x{w:08X}\n'
  return result+'.size '+NAME+',.-'+NAME+'\n'
 target=assemble(text(raw,refs),'raw');lines=(root/'conker/retail_layout.us.txt').read_text().splitlines();rows=[line for line in lines[1:]if line.split(',')[1:3]==['game_1944C0',NAME]];assert len(rows)==1
 layout=where/'layout.csv';layout.write_text(lines[0]+'\n'+rows[0]+'\n');original=root/'conker/asm/nonmatchings/game_1944C0/func_15168870.s'
 assert not any(r['filename']=='game_1944C0'and r['function']==NAME for r in csv.DictReader((root/'conker/retail_word_patches.us.csv').open()))
 guards=where/'empty-target-guards.csv';guards.write_text((root/'conker/retail_word_patches.us.csv').read_text().splitlines()[0]+'\n')
 emitters=[lambda obj:pc.emit_padded_assembly(obj,layout,'game_1944C0',word_patches_path=guards),lambda obj:pg.emit_padded_assembly(obj,original,filename='game_1944C0',word_patches_path=guards)]
 outputs=[assemble(emit(target),label)for label,emit in zip(('generic','generated'),emitters)]
 assert all(payload(obj,NAME)==(raw,refs)for obj in outputs)
 controls=0
 for label,data,relocs in(('word',bytes([raw[0]^1])+raw[1:],refs),('relocation',raw,{k:([(kind,'D_800BAD00')for kind,_ in value]if k==12 else value)for k,value in refs.items()})):
  assert(data,relocs)!=(raw,refs);bad=assemble(text(data,relocs),'bad-'+label)
  for i,emit in enumerate(emitters):
   try:result=payload(assemble(emit(bad),f'bad-{label}-{i}'),NAME);assert result==(raw,refs)
   except(ValueError,AssertionError):controls+=1
   else:raise AssertionError('Ineffective direct-word/relocation comparison control')
 links=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  symbols=dict(D_800BE9E4=0x80300000+low,D_8008CA4C=0x80400000+low,D_8008C9C8=0x80500000+low,func_1516972C=0x15300000);streams=[]
  for i,obj in enumerate([*outputs,out/'original-target.o']):
   script=where/f'{low:X}-{i}.ld';script.write_text('SECTIONS { .text 0x15168870 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf')
   q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*['--defsym=%s=0x%X'%p for p in symbols.items()],'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   section=sections(elf)['.text'][1];code=section[:444];assert not any(section[444:]);assert list(struct.unpack('>111I',code))==bound_blob(raw,refs,symbols)
   syms=[r for _,n,r,_ in symbol_rows(elf.read_bytes())if n==NAME];assert len(syms)==1 and syms[0][1:3]==(0x15168870,444);streams.append(code);links+=1
  assert len(set(streams))==1
 r=dict(both_padders_exact=True,target_guards=0,GNU_links=links,HI16_carry_boundaries=4,effective_comparison_controls=controls,
  limits='With no target guards, malformed code or relocations are detected by exact output comparison; guard rejection is not claimed.',source_installed=packet.installed(),matching_credit=0)
 (out/'boundaries.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
