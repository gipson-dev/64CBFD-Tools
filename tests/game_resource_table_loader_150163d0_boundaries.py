import csv,io,json,re,struct,subprocess,sys
from pathlib import Path
from tools.experiments import game_resource_table_loader_150163d0_match as p
out=p.out;root=p.root
from tools.pad_generated_object import parse_object
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
def main():
 NAME='func_150163D0';OWNER='generated_43880'
 pin=p.PIN
 def payload(path):
  text,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];return text[a:a+n],{i-a:v for i,v in rs.items() if a<=i<a+n}
 raw,refs=payload(out/'independent-selected.o');truth,truthrefs=payload(out/'original_150163D0.o');assert len(raw)==len(truth)==300 and len(pin['rows'])==52
 spec=lambda x:';'.join(kind+':'+name for kind,name in x) if x else '-'
 fields=next(csv.reader(io.StringIO((root/'conker/retail_word_patches.us.csv').read_text())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writeheader()
 for row in pin['rows']:writer.writerow(dict(filename=OWNER,function=NAME,offset='0x%X'%(4*row['index']),expected='0x'+row['expected'],replacement='0x'+row['replacement'],expected_relocations=spec(row['expected_relocations']),replacement_relocations=spec(row['replacement_relocations']),note='Normalize resource table loader control flow and register allocation',insert_after='',insert_after_relocations='',omit='false'))
 guard=out/'target_150163D0_guards.csv';guard.write_text(stream.getvalue());lines=(root/'conker/retail_layout.us.txt').read_text().splitlines();entries=[line for line in lines[1:] if line.split(',')[1:3]==[OWNER,NAME]];assert len(entries)==1;layout=out/'target_150163D0_layout.csv';layout.write_text(lines[0]+'\n'+entries[0]+'\n')
 def assemble(s,label):
  p=out/(label+'.s');p.write_text(s);o=p.with_suffix('.o');v=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o),str(p)],cwd=root/'conker',capture_output=True,text=True);assert v.returncode==0 and not v.stderr,(v.stdout,v.stderr);return o
 obj=out/'independent-selected.o';asm=out/'original_150163D0_target.s';whole=(out/'frozen/conker/asm/43880.s').read_text();start='glabel '+NAME+'\n';end='endlabel '+NAME;asm.write_text(start+whole.split(start,1)[1].split(end,1)[0]+end+'\n')
 a=assemble(pad_c_object.emit_padded_assembly(obj,layout,OWNER,word_patches_path=guard),'padded_150163D0_generic');b=assemble(pad_generated_object.emit_padded_assembly(obj,asm,filename=OWNER,word_patches_path=guard),'padded_150163D0_generated')
 av,ar=payload(a);bv,br=payload(b);assert(av,ar)==(bv,br),(len(av),len(bv));assert av[:300]==truth and ar==truthrefs and av[300:]==b'\0'*(len(av)-300)
 lookup={v[1]:v[2][1]for v in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};symbols={nm:lookup.get(nm,int(nm[2:],16)if nm.startswith('D_')else 0)for es in refs.values()for _,nm in es};words=bound_blob(av,ar,symbols);retail=struct.unpack_from('>76I',(root/'conker/conker.us.bin').read_bytes(),0x43880);assert tuple(words)==retail[:len(words)] and all(v==0 for v in retail[len(words):]);atext,afs,_=parse_object(a);btext,bfs,_=parse_object(b);assert atext[:304]==btext[:304] and atext[300:304]==b'\0'*4
 return dict(body_words=len(av)//4,slot_words=76,alignment_nops=1,guard_rows=52,dual_padder_matches_retail=True,source_installed=False)
