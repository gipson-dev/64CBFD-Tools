"""Both padders, exact extents, MIPS26 rebases and effective binary controls."""
from pathlib import Path
import itertools,json,struct,subprocess,sys
from tools.experiments import game_effect_preset_150c04c0_match as packet
r,o=packet.ROOT,packet.OUT
from tools.tests import game_effect_preset_150c04c0_guest as g
from tools.experiments.game_effect_preset_150c04c0_objects import assemble
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_actor_state_tick_integration import symbol_rows
NAME='func_150C04C0'
def assembly(data,refs):
 text='.set noat\n.set noreorder\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for i,(word,)in enumerate(struct.iter_unpack('>I',data)):
  for kind,name in refs.get(i*4,[]):text+=f'.reloc ., {kind}, {name}\n'
  text+=f'.word 0x{word:08X}\n'
 return text+'.size '+NAME+',.-'+NAME+'\n'
def main():
 data,refs=payload(o/'selected-final/candidate.o',NAME);truth=payload(o/'original-target.o',NAME);assert(data,refs)==truth and len(data)==392
 where=o/'boundaries';where.mkdir(exist_ok=True);target=where/'raw.o';assemble(assembly(data,refs),target)
 rows=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();selected=[line for line in rows if line.split(',')[1:3]==['generated_EC420',NAME]];assert len(selected)==1
 layout=where/'layout.csv';layout.write_text(rows[0]+'\n'+selected[0]+'\n')
 emitters=[lambda p:pc.emit_padded_assembly(p,layout,'generated_EC420',word_patches_path=None),lambda p:pg.emit_padded_assembly(p,o/'original-target.s',filename='generated_EC420',word_patches_path=None)]
 outputs=[]
 for i,emit in enumerate(emitters):
  p=where/f'padded-{i}.o';assemble(emit(target),p);assert payload(p,NAME)==truth;outputs.append(p)
 controls=0
 for label in('word','binding'):
  bad=bytearray(data);br={i:list(v)for i,v in refs.items()}
  if label=='word':bad[0]^=1
  else:
   at=next(i for i,v in br.items()if('R_MIPS_26','func_15150400')in v);br[at]=[('R_MIPS_26','func_15150404')]
  p=where/(label+'.o');assemble(assembly(bad,br),p)
  for i,emit in enumerate(emitters):
   candidate=where/f'{label}-{i}.o';assemble(emit(p),candidate);assert payload(candidate,NAME)!=truth;controls+=1
 oversized=where/'oversized.o';assemble(assembly(data+struct.pack('>I',0x24420001),refs),oversized);rejected=0
 for i,emit in enumerate(emitters):
  try:text=emit(oversized)
  except ValueError:
   assert i==1;rejected+=1;continue
  assert i==0;p=where/f'oversized-padded-{i}.o';assemble(text,p)
  assert '__retail_overflow_'+NAME in text and payload(p,NAME)!=truth
  rejected+=1
 links=0;runs=0
 for number,(entry,callee,shift)in enumerate(((g.ENTRY,g.FACTORY,0),(g.ENTRY+0x10000,0x150016C0,0x8000),(g.ENTRY-0x10000,0x15FF8000,-0x1000),(0x250C04C0,0x25008000,0x10000000))):
  syms={name:(value+shift)&0xFFFFFFFF for name,value in g.S.items()if name in {n for entries in refs.values()for _,n in entries}and name!='func_15150400'};syms['func_15150400']=callee
  blobs=[]
  for i,p in enumerate([*outputs,o/'original-target.o']):
   script=where/f'{number}-{i}.ld';script.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf')
   q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*[f'--defsym={n}=0x{v:X}'for n,v in syms.items()],'-o',str(elf),str(p)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   text=sections(elf)['.text'][1];assert not any(text[392:]);blobs.append(text[:392]);assert list(struct.unpack('>98I',text[:392]))==g.bound_blob(*payload(p,NAME),syms);defs=[v for _,n,v,_ in symbol_rows(elf.read_bytes())if n==NAME];assert len(defs)==1 and defs[0][1:3]==(entry,392);links+=1
  assert len(set(blobs))==1
  for c in [g.replace(seed,phase=phase)for seed in list(g.cases())[::32]for phase in (0,8)]:
   initial=g.fixture(c,syms)
   for blob in blobs:
    m=g.Oracle(struct.unpack('>98I',blob),initial,c,entry=entry,s=syms).run();g.check(m,initial,c,syms);runs+=1
 report=dict(both_padders_byte_exact=True,guards=0,insertions=0,omissions=0,effective_wrong_word_or_binding_controls=controls,oversized_body_comparison_rejections=rejected,GNU_links=links,independent_code_callee_and_HI16_LO16_data_bindings=4,guest_rebase_runs=runs,source_installed=packet.installed(),matching_credit=0)
 (o/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
