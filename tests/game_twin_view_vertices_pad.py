import csv,io,json,struct,subprocess,sys
from pathlib import Path
from tools.experiments import game_twin_view_vertices_match as p
out=p.out;root=p.root
from tools.tests import game_twin_view_vertices_guest as g
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
def payload(path,name):
 text,fs,rs=parse_object(path);a,n=fs[name]['value'],fs[name]['size'];return text[a:a+n],{i-a:v for i,v in rs.items() if a<=i<a+n}
def assemble(text,label):
 src=out/(label+'.s');src.write_text(text);obj=src.with_suffix('.o');r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr);return obj
def main():
 lookup={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};rom=(root/'conker/conker.us.bin').read_bytes();reports=[]
 lines=(root/'conker/retail_layout.us.txt').read_text().splitlines();fields=next(csv.reader(io.StringIO((root/'conker/retail_word_patches.us.csv').read_text())))
 for target,owner,index in g.TARGETS:
  name='func_'+target;asm_path=(out/'frozen/conker/asm/1D92F0.s') if owner.startswith('generated_') else (out/'frozen/conker/asm/nonmatchings/game_2062D0/func_151DAE28.s');whole=asm_path.read_text();start='glabel '+name+'\n';end='endlabel '+name;assembly=start+whole.split(start,1)[1].split(end,1)[0]+end+'\n';asm=out/('original_'+target+'_target.s');asm.write_text(assembly)
  original=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+assembly+'.size '+name+',.-'+name+'\n','original_'+target)
  raw,refs=payload(out/('variant_'+target+'.o'),name);truth,truthrefs=payload(original,name);assert len(raw)==len(truth)==476 and (raw,refs)==(truth,truthrefs)
  guard=out/('target_'+target+'_guards.csv');stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=fields,lineterminator='\n').writeheader();guard.write_text(stream.getvalue());entries=[line for line in lines[1:] if line.split(',')[1:3]==[owner,name]];assert len(entries)==1;layout=out/('target_'+target+'_layout.csv');layout.write_text(lines[0]+'\n'+entries[0]+'\n')
  src='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+name+'\n.type '+name+',@function\n'+name+':\n'
  for i,(word,) in enumerate(struct.iter_unpack('>I',raw)):
   for kind,symbol in refs.get(4*i,[]):src+='.reloc ., '+kind+', '+symbol+'\n'
   src+='.word 0x%08X\n'%word
  obj=assemble(src+'.size '+name+',.-'+name+'\n','target_'+target+'_raw');assert payload(obj,name)==(raw,refs)
  a=assemble(pad_c_object.emit_padded_assembly(obj,layout,owner,word_patches_path=guard),'padded_'+target+'_generic');b=assemble(pad_generated_object.emit_padded_assembly(obj,asm,filename=owner,word_patches_path=guard),'padded_'+target+'_generated');assert payload(a,name)==payload(b,name)==(truth,truthrefs)
  words=bound_blob(truth,truthrefs,{nm:lookup[nm]for es in truthrefs.values()for _,nm in es});offset=int(target,16)-0x15000000+0x2d4b0;assert struct.pack('>119I',*words)==rom[offset:offset+476]
  reports.append(dict(target=target,raw_words=119,guard_rows=0,dual_padder_matches_retail=True))
 report=dict(targets=reports,source_installed=False);(out/'pad_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
