"""Compare both padders, independent links and bounded memory access cuts."""
import csv,io,json,re,struct,subprocess,sys
from tools.experiments import game_actor_control_150f43f0_match as p
from tools.tests import game_actor_control_150f43f0_oracle as g
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def assemble(text,label):
 path=p.out/(label+'.s');path.write_text(text);obj=path.with_suffix('.o');v=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=p.root/'conker',capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(v.stdout,v.stderr);return obj
def words(obj,s):
 raw,refs=p.payload(obj);return p.bound_blob(raw,refs,s)
def state(m):return(m.memory,m.r,m.f,m.calls,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)
def main():
 selected_obj=p.out/'independent-selected.o';raw,refs=p.payload(selected_obj);text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+p.NAME+'\n.type '+p.NAME+',@function\n'+p.NAME+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(4*i,[]):text+='.reloc ., '+kind+', '+name+'\n'
  text+='.word 0x%08X\n'%w
 obj=assemble(text+'.size '+p.NAME+',.-'+p.NAME+'\n','target-raw');assert p.payload(obj)==(raw,refs)
 lines=(p.root/'conker/retail_layout.us.txt').read_text(encoding='utf-8').splitlines();selected=[l for l in lines[1:]if l.split(',')[1:3]==['generated_11FF10',p.NAME]];assert len(selected)==1;layout=p.out/'target-layout.csv';layout.write_text(lines[0]+'\n'+selected[0]+'\n')
 fields=next(csv.reader(io.StringIO((p.root/'conker/retail_word_patches.us.csv').read_text(encoding='utf-8'))));guard=p.out/'empty-guards.csv';stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=fields).writeheader();guard.write_text(stream.getvalue())
 asm=p.out/'original-target.s';full=(p.root/'conker/asm/11FF10.s').read_text(encoding='utf-8');start=full.index('glabel '+p.NAME+'\n');end=full.index('endlabel '+p.NAME,start)+len('endlabel '+p.NAME);asm.write_text(full[start:end]+'\n');a=assemble(pad_c_object.emit_padded_assembly(obj,layout,'generated_11FF10',word_patches_path=guard),'target-generic');b=assemble(pad_generated_object.emit_padded_assembly(obj,asm,filename='generated_11FF10',word_patches_path=guard),'target-generated');local=re.sub(r'(?m)^  jlabel (\S+)',r'  \1:',asm.read_text(encoding='utf-8'));original=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+local+'\n.size '+p.NAME+',.-'+p.NAME+'\n','original-reference');assert p.payload(a)==p.payload(b)==p.payload(original)==p.payload(obj)
 assert words(obj,{'func_1509BFB0':g.AUDIO,'func_1509BE40':g.INPUT,'func_15123934':g.GATE,'func_151239CC':g.EXIT,'func_15124B18':g.START})==list(struct.unpack_from('>96I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM)[:94])
 links=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s=dict(func_1509BFB0=0x15210000+low,func_1509BE40=0x15230000+low,func_15123934=0x15250000+low,func_151239CC=0x15270000+low,func_15124B18=0x15290000+low)
  for i,path in enumerate((obj,a,b,original)):
   expected=words(path,s);script=p.out/('link-%X-%d.ld'%(low,i));script.write_text('SECTIONS { .text 0x150F43F0 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf');v=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',p.NAME,*['--defsym=%s=0x%X'%item for item in s.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert v.returncode==0,v.stderr;binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True);assert expected==list(struct.unpack_from('>94I',binary.read_bytes()));links+=1
 truth=struct.unpack_from('>96I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM);programs=[words(v,{'func_1509BFB0':g.AUDIO,'func_1509BE40':g.INPUT,'func_15123934':g.GATE,'func_151239CC':g.EXIT,'func_15124B18':g.START})for v in (obj,a,b,original)];assert all(tuple(v)==truth[:94] for v in programs) and truth[94:]==(0,0)
 triples=0
 for c in (g.Case(kind=0),g.Case(state=0x100),g.Case(held=1),g.Case(gate=0),g.Case(mutation=31),g.Case(kind=0,state=8,mutation=31)):
  full=g.Oracle(programs[0],c);full.run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    m=g.Oracle(ws,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError(('Missing access cut',cut))
    models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);triples+=1
 assert truth[94:]==(0,0)
 r=dict(body_words=94,slot_words=96,zero_padding_words=2,raw_generic_generated_original_bindings_equal=True,guards=0,GNU_rebased_links=links,access_cut_quads=triples,all_body_words_reachable=True,hardware_or_C_fault_not_qualified=True,source_installed=False);(p.out/'boundaries.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
