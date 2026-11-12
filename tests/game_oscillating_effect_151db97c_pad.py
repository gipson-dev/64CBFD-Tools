import csv,io,json,struct,subprocess,sys
from pathlib import Path
from tools.experiments import game_oscillating_effect_151db97c_match as p
out=p.out;root=p.root
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
def main():
 NAME='func_151DB97C';OWNER='game_2062D0';pin=p.PIN
 def payload(path):
  text,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return text[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
 raw,refs=payload(out/'independent-selected.o');truth,truthrefs=payload(out/'original_151DB97C.o');assert len(raw)==300 and len(truth)==300 and len(pin['rows'])==0
 spec=lambda x:';'.join(kind+':'+name for kind,name in x)if x else '-'
 fields=next(csv.reader(io.StringIO((root/'conker/retail_word_patches.us.csv').read_text())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writeheader()
 for row in pin['rows']:writer.writerow(dict(filename=OWNER,function=NAME,offset='0x%X'%(4*row['index']),expected='0x'+row['expected'],replacement='0x'+row['replacement'],expected_relocations=spec(row['expected_relocations']),replacement_relocations=spec(row['replacement_relocations']),note='Normalize registered update walker register allocation and control flow',insert_after=('0x'+row['insert_after']if row['insert_after']else ''),insert_after_relocations=(spec(row['insert_after_relocations'])if row['insert_after']else ''),omit='false'))
 guard=out/'target_151DB97C_guards.csv';guard.write_text(stream.getvalue());lines=(root/'conker/retail_layout.us.txt').read_text().splitlines();entries=[line for line in lines[1:]if line.split(',')[1:3]==[OWNER,NAME]];assert len(entries)==1;layout=out/'target_151DB97C_layout.csv';layout.write_text(lines[0]+'\n'+entries[0]+'\n')
 def assemble(s,label):
  p=out/(label+'.s');p.write_text(s);o=p.with_suffix('.o');v=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o),str(p)],cwd=root/'conker',capture_output=True,text=True);assert v.returncode==0 and not v.stderr,(v.stdout,v.stderr);return o
 src='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for i,(word,)in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(4*i,[]):src+='.reloc ., '+kind+', '+name+'\n'
  src+='.word 0x%08X\n'%word
 obj=assemble(src+'.size '+NAME+',.-'+NAME+'\n','target_151DB97C_raw');assert payload(obj)==(raw,refs)
 whole=(out/'frozen/conker/asm/nonmatchings/game_2062D0/func_151DB97C.s').read_text();start='glabel '+NAME+'\n';end='endlabel '+NAME;asm=out/'original_151DB97C_target.s';asm.write_text(start+whole.split(start,1)[1].split(end,1)[0]+end+'\n')
 a=assemble(pad_c_object.emit_padded_assembly(obj,layout,OWNER,word_patches_path=guard),'padded_151DB97C_generic');b=assemble(pad_generated_object.emit_padded_assembly(obj,asm,filename=OWNER,word_patches_path=guard),'padded_151DB97C_generated');assert payload(a)==payload(b)==(truth,truthrefs)
 lookup={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};symbols={nm:lookup[nm]for es in truthrefs.values()for _,nm in es};assert tuple(bound_blob(truth,truthrefs,symbols))==struct.unpack_from('>75I',(root/'conker/conker.us.bin').read_bytes(),0x208e2c)
 report=dict(raw_words=75,retail_words=75,guard_rows=0,inserted_words=0,dual_padder_matches_retail=True,source_installed=False);(out/'pad_151DB97C_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
