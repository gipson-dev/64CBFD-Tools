"""Both production padders, rebases and fail-closed changed-caller guards."""
from pathlib import Path
import csv,io,json,struct,subprocess,sys
from tools.experiments import game_column_event_walker_1516944c_match as packet
root,out=packet.ROOT,packet.OUT
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import symbol_rows

def main():
 where=out/'caller-boundaries';where.mkdir(exist_ok=True)
 def assemble(text,name):
  p=where/(name+'.s');p.write_text(text);obj=p.with_suffix('.o')
  q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(p)],capture_output=True,text=True)
  assert q.returncode==0 and not q.stdout and not q.stderr,(q.stdout,q.stderr)
  return obj
 with(out/'private-word-patches.csv').open(newline='')as f:
  reader=csv.DictReader(f);fields=reader.fieldnames;allrows=list(reader)
 links=controls=0;reports=[]
 for owner,name,rawpath,entry,words in [('game_1944C0','func_1516944C','assign-1/candidate.o',0x1516944C,105)]:
  raw,refs=payload(out/rawpath,name)
  text='.set noat\n.set noreorder\n.text\n.globl '+name+'\n.type '+name+',@function\n'+name+':\n'
  for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
   for k,n in refs.get(4*i,[]):text+=f'.reloc ., {k}, {n}\n'
   text+=f'.word 0x{w:08X}\n'
  target=assemble(text+'.size '+name+',.-'+name+'\n',name+'-raw')
  rows=[r for r in allrows if r['function']==name and r['filename']==owner];assert len(rows)==18
  def write_guards(rows,label):
   p=where/(name+'-'+label+'.csv')
   with p.open('w',newline='')as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
   return p
  guards=write_guards(rows,'guards')
  lines=(root/'conker/retail_layout.us.txt').read_text().splitlines();selected=[v for v in lines[1:]if v.split(',')[1:3]==[owner,name]];assert len(selected)==1
  layout=where/(name+'-layout.csv');layout.write_text(lines[0]+'\n'+selected[0]+'\n')
  original_path=root/f'conker/asm/nonmatchings/{owner}/{name}.s'
  emitters=[lambda g:pc.emit_padded_assembly(target,layout,owner,word_patches_path=g),lambda g:pg.emit_padded_assembly(target,original_path,filename=owner,word_patches_path=g)]
  generic,generated=[assemble(emit(guards),name+'-'+label)for label,emit in zip(('generic','generated'),emitters)]
  original=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+original_path.read_text()+'\n.size '+name+',.-'+name+'\n',name+'-retail')
  assert payload(generic,name)==payload(generated,name)==payload(original,name)
  for kind in ('word','relocation'):
   bad=[dict(r)for r in rows];idx=next(i for i,r in enumerate(bad)if r['expected_relocations']!='-')
   if kind=='word':bad[idx]['expected']='0x%08X'%(int(bad[idx]['expected'],0)^1)
   else:bad[idx]['expected_relocations']='R_MIPS_HI16:D_800BAD00'
   malformed=write_guards(bad,kind+'-control')
   for emit in emitters:
    try:emit(malformed)
    except (ValueError,AssertionError):controls+=1
    else:raise AssertionError('Ineffective '+kind+' guard control for '+name)
  names=sorted({n for v in refs.values()for k,n in v})
  for low in(0,0x7FFC,0x8000,0xFFFC):
   symbols={'func_1516968C':0x15310000,'D_8008B4A8':0x80300000+low,'D_800DCE50':0x80400000+low,'D_800DD190':0x80400340+low,'D_800DD198':0x80400348+low}
   streams=[]
   for label,path in(('generic',generic),('generated',generated),('retail',original)):
    script=where/f'{name}-{low:X}-{label}.ld';script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);elf=script.with_suffix('.elf')
    q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',name,*['--defsym=%s=0x%X'%p for p in symbols.items()],'-o',str(elf),str(path)],capture_output=True,text=True)
    assert q.returncode==0,q.stderr
    section=sections(elf)['.text'][1];code=section[:4*words]
    syms=[r for _,n,r,_ in symbol_rows(elf.read_bytes())if n==name];assert len(syms)==1 and syms[0][1:3]==(entry,4*words)
    assert section[:len(code)]==code and not any(section[len(code):])
    assert list(struct.unpack('>%dI'%words,code))==bound_blob(*payload(path,name),symbols)
    streams.append(code);links+=1
   assert len(set(streams))==1
  reports.append(dict(function=name,raw_words=len(raw)//4,retail_words=words,guards=18,omissions=sum(r['omit']=='true'for r in rows),both_padders_exact=True))
 r=dict(callers=reports,GNU_links=links,effective_malformed_controls=controls,HI16_carry_boundaries=4)
 (out/'caller-boundaries.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
