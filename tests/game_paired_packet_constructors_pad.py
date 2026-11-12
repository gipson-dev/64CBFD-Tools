import csv,io,json,struct,subprocess,sys
from pathlib import Path
from tools.experiments import game_paired_packet_constructors_match as p
out=p.out;root=p.root
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
def assemble(s,label):
 p=out/(label+'.s');p.write_text(s);o=p.with_suffix('.o')
 v=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o),str(p)],cwd=root/'conker',capture_output=True,text=True)
 assert v.returncode==0 and not v.stderr,(v.stdout,v.stderr)
 return o
def payload(path,name):
 text,fs,rs=parse_object(path);a,n=fs[name]['value'],fs[name]['size'];return text[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
def main():
 look={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};rom=(root/'conker/conker.us.bin').read_bytes();reports=[]
 for name,offset in (('func_1514E00C',0x17b4bc),('func_1514E194',0x17b644)):
  raw,refs=payload(out/'paired.o',name);whole=(root/'conker/asm/179F30.s').read_text();start='glabel '+name+'\n';end='endlabel '+name
  target=start+whole.split(start,1)[1].split(end,1)[0]+end+'\n';asm=out/(name+'_retail_target.s');asm.write_text(target)
  original=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+target+'\n.size '+name+',.-'+name+'\n',name+'_retail')
  truth,truthrefs=payload(original,name);assert len(raw)==len(truth)==392 and refs==truthrefs
  delta=[(i,a,b)for i,((a,),(b,)) in enumerate(zip(struct.iter_unpack('>I',raw),struct.iter_unpack('>I',truth))) if a!=b];assert len(delta)==11 and all(4*i not in refs for i,_,_ in delta)
  fields=next(csv.reader(io.StringIO((root/'conker/retail_word_patches.us.csv').read_text())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writeheader()
  for i,a,b in delta:writer.writerow(dict(filename='generated_179F30',function=name,offset=f'0x{i*4:X}',expected=f'0x{a:08X}',replacement=f'0x{b:08X}',expected_relocations='-',replacement_relocations='-',note='Normalize independent packet initialization store order',omit='false'))
  guard=out/(name+'_guards.csv');guard.write_text(stream.getvalue());lines=(root/'conker/retail_layout.us.txt').read_text().splitlines();entry=[line for line in lines[1:]if line.split(',')[1:3]==['generated_179F30',name]];assert len(entry)==1
  layout=out/(name+'_layout.csv');layout.write_text(lines[0]+'\n'+entry[0]+'\n')
  src='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+name+'\n.type '+name+',@function\n'+name+':\n'
  for i,(word,)in enumerate(struct.iter_unpack('>I',raw)):
   for kind,symbol in refs.get(4*i,[]):src+='.reloc ., '+kind+', '+symbol+'\n'
   src+=f'.word 0x{word:08X}\n'
  obj=assemble(src+'.size '+name+',.-'+name+'\n',name+'_raw');assert payload(obj,name)==(raw,refs)
  padded1=assemble(pad_c_object.emit_padded_assembly(obj,layout,'generated_179F30',word_patches_path=guard),name+'_generic')
  padded2=assemble(pad_generated_object.emit_padded_assembly(obj,asm,filename='generated_179F30',word_patches_path=guard),name+'_generated')
  assert payload(padded1,name)==payload(padded2,name)==(truth,truthrefs)
  symbols={nm:look[nm]for es in truthrefs.values()for _,nm in es};assert tuple(bound_blob(truth,truthrefs,symbols))==struct.unpack_from('>98I',rom,offset)
  reports.append(dict(target=name,words=98,guards=11,relocations_unchanged=True,dual_pad_matches_retail=True))
 report=dict(targets=reports,source_installed=False);(out/'pad_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
