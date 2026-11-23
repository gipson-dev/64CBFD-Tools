"""Both production padders, fail-closed bindings and independent GNU carry links."""
from pathlib import Path
import csv,json,struct,subprocess,sys
from tools.experiments import game_compact_sprite_renderer_15168118_match as packet
root,out=packet.ROOT,packet.OUT
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
NAME='func_15168118'
def main():
 where=out/'boundaries';where.mkdir(exist_ok=True);raw,refs=payload(out/'selected-v2/candidate.o',NAME)
 def assemble(text,label):
  p=where/(label+'.s');p.write_text(text);obj=p.with_suffix('.o');q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(p)],capture_output=True,text=True);assert q.returncode==0,q.stderr;return obj
 text='.set noat\n.set noreorder\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  for k,n in refs.get(4*i,[]):text+=f'.reloc ., {k}, {n}\n'
  text+=f'.word 0x{w:08X}\n'
 target=assemble(text+'.size '+NAME+',.-'+NAME+'\n','raw')
 with(out/'private-word-patches.csv').open(newline='')as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=[r for r in reader if r['function']==NAME and r['filename']=='game_1944C0']
 assert len(rows)==201 and sum(r['omit']=='true'for r in rows)==4 and not any(r['insert_after']for r in rows)
 def guards(data,label):
  p=where/(label+'.csv')
  with p.open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(data)
  return p
 guard=guards(rows,'guards');lines=(root/'conker/retail_layout.us.txt').read_text().splitlines();line=[v for v in lines[1:]if v.split(',')[1:3]==['game_1944C0',NAME]];assert len(line)==1
 layout=where/'layout.csv';layout.write_text(lines[0]+'\n'+line[0]+'\n');original=root/'conker/asm/nonmatchings/game_1944C0/func_15168118.s'
 emitters=[lambda g:pc.emit_padded_assembly(target,layout,'game_1944C0',word_patches_path=g),lambda g:pg.emit_padded_assembly(target,original,filename='game_1944C0',word_patches_path=g)]
 outputs=[assemble(emit(guard),label)for label,emit in zip(('generic','generated'),emitters)];truth=payload(out/'original-target.o',NAME)
 assert payload(outputs[0],NAME)==payload(outputs[1],NAME)==truth
 rejections=comparisons=0
 for kind in('expected-word','unexpected-binding','omitted-copy-word','wrong-replacement'):
  bad=[dict(r)for r in rows];index=next(i for i,r in enumerate(bad)if (r['omit']=='true'if kind=='omitted-copy-word'else r['omit']=='false'and r['expected_relocations']=='-'))
  if kind=='unexpected-binding':bad[index]['expected_relocations']='R_MIPS_HI16:D_800BAD00'
  elif kind=='wrong-replacement':bad[index]['replacement']='0x%08X'%(int(bad[index]['replacement'],0)^1)
  else:bad[index]['expected']='0x%08X'%(int(bad[index]['expected'],0)^1)
  for i,emit in enumerate(emitters):
   if kind=='wrong-replacement':
    assert payload(assemble(emit(guards(bad,'bad-'+kind)),f'bad-output-{i}'),NAME)!=truth;comparisons+=1
   else:
    try:emit(guards(bad,'bad-'+kind))
    except(ValueError,AssertionError):rejections+=1
    else:raise AssertionError('Ineffective guard control: '+kind)
 names=sorted({n for pairs in truth[1].values()for _,n in pairs});links=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  symbols={n:(0x15300000+i*0x100 if n.startswith('func_')else 0x80300000+i*0x10000+low)for i,n in enumerate(names)};streams=[]
  for i,obj in enumerate([*outputs,out/'original-target.o']):
   script=where/f'{low:X}-{i}.ld';script.write_text('SECTIONS { .text 0x15168118 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf')
   q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*['--defsym=%s=0x%X'%p for p in symbols.items()],'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   section=sections(elf)['.text'][1];code=section[:1348];assert not any(section[1348:]);assert list(struct.unpack('>337I',code))==bound_blob(*payload(obj,NAME),symbols)
   syms=[r for _,n,r,_ in symbol_rows(elf.read_bytes())if n==NAME];assert len(syms)==1 and syms[0][1:3]==(0x15168118,1348);streams.append(code);links+=1
  assert len(set(streams))==1
 report=dict(both_padders_exact=True,target_guards=201,omissions=4,insertions=0,GNU_links=links,HI16_carry_boundaries=4,effective_guard_rejections=rejections,effective_output_comparisons=comparisons,named_relocations_all_retained=True,source_installed=packet.installed(),matching_credit=0)
 (out/'boundaries.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
