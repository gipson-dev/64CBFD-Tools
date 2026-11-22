"""Both real padders; closed row-end carry relation and malformed guard controls."""
from pathlib import Path
import csv,json,struct,subprocess,sys
from tools.experiments import game_view_trig_render_walker_15167310_match as packet
root,out=packet.ROOT,packet.OUT
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows
NAME='func_15167310'
def main():
 where=out/'boundaries';where.mkdir(exist_ok=True);raw,refs=payload(out/'selected/candidate.o',NAME)
 def assemble(text,label):
  p=where/(label+'.s');p.write_text(text);obj=p.with_suffix('.o');q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(p)],capture_output=True,text=True);assert q.returncode==0,q.stderr;return obj
 text='.set noat\n.set noreorder\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  for k,n in refs.get(4*i,[]):text+=f'.reloc ., {k}, {n}\n'
  text+=f'.word 0x{w:08X}\n'
 target=assemble(text+'.size '+NAME+',.-'+NAME+'\n','raw')
 with(out/'private-word-patches.csv').open(newline='')as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=[r for r in reader if r['function']==NAME and r['filename']=='game_1944C0']
 assert len(rows)==45
 def guards(data,label):
  p=where/(label+'.csv')
  with p.open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(data)
  return p
 guard=guards(rows,'guards');lines=(root/'conker/retail_layout.us.txt').read_text().splitlines();line=[v for v in lines[1:]if v.split(',')[1:3]==['game_1944C0',NAME]];assert len(line)==1
 layout=where/'layout.csv';layout.write_text(lines[0]+'\n'+line[0]+'\n');original=root/'conker/asm/nonmatchings/game_1944C0/func_15167310.s'
 emitters=[lambda g:pc.emit_padded_assembly(target,layout,'game_1944C0',word_patches_path=g),lambda g:pg.emit_padded_assembly(target,original,filename='game_1944C0',word_patches_path=g)]
 outputs=[assemble(emit(guard),label)for label,emit in zip(('generic','generated'),emitters)]
 assert payload(outputs[0],NAME)==payload(outputs[1],NAME)==payload(out/'original-target.o',NAME)
 controls=0
 for kind in('word','relocation','omission-word','insertion-word'):
  bad=[dict(r)for r in rows]
  index=next(i for i,r in enumerate(bad)if r['omit']=='true')if kind=='omission-word'else next(i for i,r in enumerate(bad)if r['insert_after'])if kind=='insertion-word'else next(i for i,r in enumerate(bad)if r['expected_relocations']!='-')
  if kind=='relocation':bad[index]['expected_relocations']='R_MIPS_HI16:D_800BAD00'
  else:bad[index]['expected']='0x%08X'%(int(bad[index]['expected'],0)^1)
  for emit in emitters:
   try:emit(guards(bad,'bad-'+kind))
   except(ValueError,AssertionError):controls+=1
   else:raise AssertionError('Ineffective guard '+kind)
 links=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  names=sorted({n for v in payload(out/'original-target.o',NAME)[1].values()for k,n in v})
  symbols={n:0x80300000+i*0x10000+low for i,n in enumerate(names)};symbols.update(sinf=0x15047D60,cosf=0x15047C00);symbols['D_800DD190']=symbols['D_800DCE50']+0x340;streams=[]
  for i,obj in enumerate([*outputs,out/'original-target.o']):
   script=where/f'{low:X}-{i}.ld';script.write_text('SECTIONS { .text 0x15167310 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf')
   q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*['--defsym=%s=0x%X'%p for p in symbols.items()],'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   section=sections(elf)['.text'][1];code=section[:488];assert not any(section[488:]);assert list(struct.unpack('>122I',code))==bound_blob(*payload(obj,NAME),symbols)
   syms=[r for _,n,r,_ in symbol_rows(elf.read_bytes())if n==NAME];assert len(syms)==1 and syms[0][1:3]==(0x15167310,488);streams.append(code);links+=1
  assert len(set(streams))==1
 r=dict(both_padders_exact=True,target_guards=45,omissions=3,insertions=1,GNU_links=links,HI16_carry_boundaries=4,effective_malformed_controls=controls,
  row_end_relation='D_800DD190 == D_800DCE50 + 0x340 required by retail fold',source_installed=packet.installed(),matching_credit=0)
 (out/'boundaries.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
