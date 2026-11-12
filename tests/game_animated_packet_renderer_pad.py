import csv,io,json,struct,subprocess,sys
from pathlib import Path
from tools.experiments import game_animated_packet_renderer_match as p
out=p.out;root=p.root
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
NAME='func_15167C58';OWNER='game_1944C0'
def payload(path):
 text,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return text[a:a+n],{i-a:v for i,v in rs.items()if a<=i<a+n}
def assemble(s,label):
 p=out/(label+'.s');p.write_text(s);o=p.with_suffix('.o');r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o),str(p)],cwd=root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr);return o
def main():
 pin=json.loads((out/'normalization_screen.json').read_text());raw,refs=payload(out/'candidate.o');truth,truthrefs=payload(out/'original.o');assert len(raw)==len(truth)==300 and len(pin['rows'])==42
 fields=next(csv.reader(io.StringIO((root/'conker/retail_word_patches.us.csv').read_text())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writeheader();spec=lambda x:';'.join(kind+':'+name for kind,name in x)if x else '-'
 for row in pin['rows']:writer.writerow(dict(filename=OWNER,function=NAME,offset='0x%X'%(4*row['index']),expected='0x'+row['expected'],replacement='0x'+row['replacement'],expected_relocations=spec(row['expected_relocations']),replacement_relocations=spec(row['replacement_relocations']),note='Normalize animation renderer register allocation and table-read schedule',omit='false'))
 guard=out/'guards.csv';guard.write_text(stream.getvalue());lines=(root/'conker/retail_layout.us.txt').read_text().splitlines();entries=[line for line in lines[1:]if line.split(',')[1:3]==[OWNER,NAME]];assert len(entries)==1;layout=out/'layout.csv';layout.write_text(lines[0]+'\n'+entries[0]+'\n')
 src='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for i,(word,)in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(4*i,[]):src+='.reloc ., '+kind+', '+name+'\n'
  src+=f'.word 0x{word:08X}\n'
 obj=assemble(src+'.size '+NAME+',.-'+NAME+'\n','raw');assert payload(obj)==(raw,refs)
 a=assemble(pad_c_object.emit_padded_assembly(obj,layout,OWNER,word_patches_path=guard),'generic');b=assemble(pad_generated_object.emit_padded_assembly(obj,out/'original_target.s',filename=OWNER,word_patches_path=guard),'generated');assert payload(a)==payload(b)==(truth,truthrefs)
 lookup={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};words=bound_blob(truth,truthrefs,{nm:lookup[nm]for es in truthrefs.values()for _,nm in es});assert struct.pack('>75I',*words)==(root/'conker/conker.us.bin').read_bytes()[0x195108:0x195234]
 report=dict(raw_words=75,guard_rows=42,insertions=0,dual_padder_matches_retail=True,source_installed=False);(out/'pad_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
