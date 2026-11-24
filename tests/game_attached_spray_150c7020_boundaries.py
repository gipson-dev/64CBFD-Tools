"""Unguarded word visibility, slot limits and independent GNU relocation links."""
from unittest.mock import patch
import json,struct,subprocess
from tools.experiments import game_attached_spray_150c7020_match as p
from tools.tests import game_attached_spray_150c7020_guest as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_classifier_candidates import sections
def main():
 data,refs=p.normalize(*payload(p.OUT/'selected-final/owner-candidate.o',p.FUNCTION));truth=payload(p.OUT/'original-target.o',p.FUNCTION);assert(data,refs)==truth;w=p.OUT/'boundaries';w.mkdir(exist_ok=True);standalone=w/'raw.o';p.assemble(p.assembly(data,refs),standalone)
 lines=(p.OUT/'baseline/conker/retail_layout.us.txt').read_text().splitlines();rows=[v for v in lines if v.split(',')[1:3]==['generated_F44D0',p.FUNCTION]];assert len(rows)==1;layout=w/'layout.csv';layout.write_text(lines[0]+'\n'+rows[0]+'\n');guards=p.OUT/'baseline/conker/retail_word_patches.us.csv'
 emitters=[lambda f:p.pc.emit_padded_assembly(f,layout,'generated_F44D0',word_patches_path=guards),lambda f:p.pg.emit_padded_assembly(f,p.OUT/'original-target.s',filename='generated_F44D0',word_patches_path=guards)];outputs=[];visible=0
 for i,emit in enumerate(emitters):
  path=w/f'padded-{i}.o';p.assemble(emit(standalone),path);assert payload(path,p.FUNCTION)==truth;outputs.append(path)
 for at in range(0,416,4):
  changed=bytearray(data);changed[at+3]^=4;path=w/'changed.o';p.assemble(p.assembly(changed,refs),path)
  for i,emit in enumerate(emitters):
   out=w/f'visible-{i}.o';p.assemble(emit(path),out);assert payload(out,p.FUNCTION)!=truth;visible+=1
 over=w/'oversize.o';p.assemble(p.assembly(data+bytes(4),refs),over);oversize=[]
 for emit in emitters:
  try:text=emit(over)
  except ValueError:oversize.append('rejected')
  else:assert '__retail_overflow_'+p.FUNCTION in text;oversize.append('visible overflow')
 names={n for a in refs.values()for _,n in a};calls={n for a in refs.values()for k,n in a if k=='R_MIPS_26'};links=runs=0
 for group,(entry,low)in enumerate([(g.ENTRY,0),(0x250c7020,0x7ff8),(0x350c7020,0x8000),(0x450c7020,0xfff8)]):
  symbols={n:(entry&0xf0000000)+0x00210000+0x20000*i+low for i,n in enumerate(sorted(calls))};symbols.update({n:0x80100000+0x20000*i+low for i,n in enumerate(sorted(names-calls))});programs=[]
  for i,path in enumerate([standalone,*outputs,p.OUT/'original-target.o']):
   script=w/f'{group}-{i}.ld';script.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',p.FUNCTION,*[f'--defsym={n}=0x{a:X}'for n,a in symbols.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert q.returncode==0,q.stderr;body=sections(elf)['.text'][1];assert not any(body[416:]);words=list(struct.unpack_from('>104I',body));assert words==g.bound_blob(*payload(path,p.FUNCTION),symbols);programs.append(words);links+=1
  assert all(v==programs[0]for v in programs)
  with patch.multiple(g,ENTRY=entry,CONSTANT=symbols['D_800A0490'],RNG=symbols['func_150ADA20'],PREPARE=symbols['func_1516962C'],SUBMIT=symbols['func_15134DAC']):
   for c in[g.Case(),g.Case(mode=15,phase=8,lifetime=-32768)]:
    models=[g.check(words,c,entry=entry)for words in programs];assert all(g.state(m)==g.state(models[0])for m in models[1:]);runs+=len(models)
 q=dict(unguarded_corruptions_visible=visible,body_words=104,bindings=9,oversized=oversize,GNU_links=links,guest_rebase_runs=runs,HI_carry_negative_LO_and_JAL_regions_verified=True,source_installed=p.installed(),matching_credit=0);(p.OUT/'boundaries.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
