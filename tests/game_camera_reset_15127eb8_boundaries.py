"""Compare both padders, rebased links and bounded access cuts."""
import csv,io,json,re,struct,subprocess,sys
from tools.experiments import game_camera_reset_15127eb8_match as p
from tools.tests import game_camera_reset_15127eb8_oracle as g
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
 selected=p.out/'independent-selected.o';raw,refs=p.payload(selected);text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+p.NAME+'\n.type '+p.NAME+',@function\n'+p.NAME+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(4*i,[]):text+='.reloc ., '+kind+', '+name+'\n'
  text+='.word 0x%08X\n'%w
 obj=assemble(text+'.size '+p.NAME+',.-'+p.NAME+'\n','target-raw');assert p.payload(obj)==(raw,refs)
 lines=(p.root/'conker/retail_layout.us.txt').read_text().splitlines();selected=[l for l in lines[1:]if l.split(',')[1:3]==['game_14FF90',p.NAME]];assert len(selected)==1;layout=p.out/'target-layout.csv';layout.write_text(lines[0]+'\n'+selected[0]+'\n')
 fields=next(csv.reader(io.StringIO((p.root/'conker/retail_word_patches.us.csv').read_text())));guard=p.out/'empty-guards.csv';stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=fields).writeheader();guard.write_text(stream.getvalue())
 asm=p.out/'original-target.s';full=(p.root/'conker/asm/nonmatchings/game_14FF90/func_15127EB8.s').read_text();start=full.index('glabel '+p.NAME+'\n');end=full.index('endlabel '+p.NAME,start)+len('endlabel '+p.NAME);asm.write_text(full[start:end]+'\n')
 a=assemble(pad_c_object.emit_padded_assembly(obj,layout,'game_14FF90',word_patches_path=guard),'target-generic');b=assemble(pad_generated_object.emit_padded_assembly(obj,asm,filename='game_14FF90',word_patches_path=guard),'target-generated');local=re.sub(r'(?m)^  jlabel (\S+)',r'  \1:',asm.read_text());original=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+local+'\n.size '+p.NAME+',.-'+p.NAME+'\n','original-reference');assert p.payload(a)==p.payload(b)==p.payload(original)==p.payload(obj)
 names={name for es in refs.values()for _,name in es};symbols={name:int(name.split('_')[1],16) for name in names};truth=struct.unpack('>77I',(p.out/'original-function.bin').read_bytes());programs=[words(v,symbols)for v in (obj,a,b,original)];assert all(tuple(v)==truth for v in programs)
 links=0
 for low in (0,0x7ffc,0x8000,0xfffc):
  syms={name:(value&0xffff0000)|low for name,value in symbols.items()}
  for i,path in enumerate((obj,a,b,original)):
   expected=words(path,syms);script=p.out/('link-%X-%d.ld'%(low,i));script.write_text('SECTIONS { .text 0x15127EB8 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf');v=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',p.NAME,*['--defsym=%s=0x%X'%item for item in syms.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert v.returncode==0,v.stderr;binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True);assert expected==list(struct.unpack_from('>77I',binary.read_bytes()));links+=1
 cuts=0
 for c in (g.Case(0,0,0),g.Case(1,1,1),g.Case(2,2,6),g.Case(3,3,15)):
  full=g.Oracle(programs[0],c);full.run();checks=range(full.all_accesses)
  for cut in checks:
   models=[]
   for ws in programs:
    m=g.Oracle(ws,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError(('Missing access cut',cut))
    models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]);cuts+=1
 result=dict(body_words=77,raw_generic_generated_original_bindings_equal=True,guards=0,GNU_rebased_links=links,access_cut_quads=cuts,hardware_or_C_fault_not_qualified=True,source_installed=False);(p.out/'boundaries.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
