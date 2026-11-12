import csv,io,json,struct,subprocess,sys
from pathlib import Path
from tools.experiments import game_spawn_scene_transition_match as p
out=p.out;root=p.root
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
NAME='func_1507DFE4';OWNER='game_A9D90'
def payload(path):
 text,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return text[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
def assemble(text,label):
 src=out/(label+'.s');src.write_text(text);obj=src.with_suffix('.o');r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr);return obj
def main():
 whole=(root/'conker/asm/nonmatchings/game_A9D90/func_1507DFE4.s').read_text();start='glabel '+NAME+'\n';end='endlabel '+NAME;assembly=start+whole.split(start,1)[1].split(end,1)[0]+end+'\n';asm=out/'original_target.s';asm.write_text(assembly)
 original=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+assembly+'.size '+NAME+',.-'+NAME+'\n','original')
 raw,refs=payload(out/'candidate.o');truth,truthrefs=payload(original);assert len(raw)==len(truth)==304 and (raw,refs)==(truth,truthrefs)
 fields=next(csv.reader(io.StringIO((root/'conker/retail_word_patches.us.csv').read_text())));guard=out/'guards.csv';stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=fields,lineterminator='\n').writeheader();guard.write_text(stream.getvalue());lines=(root/'conker/retail_layout.us.txt').read_text().splitlines();entries=[line for line in lines[1:]if line.split(',')[1:3]==[OWNER,NAME]];assert len(entries)==1;layout=out/'layout.csv';layout.write_text(lines[0]+'\n'+entries[0]+'\n')
 src='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for i,(word,) in enumerate(struct.iter_unpack('>I',raw)):
  for kind,symbol in refs.get(4*i,[]):src+='.reloc ., '+kind+', '+symbol+'\n'
  src+=f'.word 0x{word:08X}\n'
 obj=assemble(src+'.size '+NAME+',.-'+NAME+'\n','raw');assert payload(obj)==(raw,refs)
 a=assemble(pad_c_object.emit_padded_assembly(obj,layout,OWNER,word_patches_path=guard),'generic');b=assemble(pad_generated_object.emit_padded_assembly(obj,asm,filename=OWNER,word_patches_path=guard),'generated');assert payload(a)==payload(b)==(truth,truthrefs)
 lookup={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};words=bound_blob(truth,truthrefs,{nm:lookup[nm]for es in truthrefs.values()for _,nm in es});assert struct.pack('>76I',*words)==(root/'conker/conker.us.bin').read_bytes()[0xab494:0xab5c4]
 report=dict(raw_words=76,guard_rows=0,dual_padder_matches_retail=True,source_installed=False);(out/'pad_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
