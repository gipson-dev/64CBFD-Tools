import csv,io,json,re,struct,subprocess,sys
from tools.experiments import game_effect_state_callback_150bf0f4_match as p
n=p
from tools.tests import game_effect_state_callback_150bf0f4_oracle as g
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def assemble(text,label):
 path=p.out/(label+'.s');path.write_text(text);obj=path.with_suffix('.o');v=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=p.root/'conker',capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(v.stdout,v.stderr);return obj
def words(obj,syms):raw,refs=p.payload(obj);return p.bound_blob(raw,refs,syms)
def state(m):return(m.memory,m.r,m.f,m.calls,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)
def main():
 raw,refs=p.payload(p.out/'independent-selected.o');expected,nrefs=n.normalize(raw,refs);text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+p.NAME+'\n.type '+p.NAME+',@function\n'+p.NAME+':\n'
 for i,(word,) in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(4*i,[]):text+='.reloc ., '+kind+', '+name+'\n'
  text+='.word 0x%08X\n'%word
 obj=assemble(text+'.size '+p.NAME+',.-'+p.NAME+'\n','target-raw');assert p.payload(obj)==(raw,refs)
 lines=(p.root/'conker/retail_layout.us.txt').read_text().splitlines();entries=[line for line in lines[1:] if line.split(',')[1:3]==['generated_EC420',p.NAME]];assert len(entries)==1
 layout=p.out/'target-layout.csv';layout.write_text(lines[0]+'\n'+entries[0]+'\n');fields=next(csv.reader(io.StringIO((p.root/'conker/retail_word_patches.us.csv').read_text())));stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(n.rows(raw,refs));guard=p.out/'target-guards.csv';guard.write_text(stream.getvalue())
 asm=p.out/'original-target.s';whole=(p.out/'frozen/conker/asm/EC420.s').read_text();target='glabel '+p.NAME+'\n';ending='endlabel '+p.NAME;asm.write_text(target+whole.split(target,1)[1].split(ending,1)[0]+ending+'\n')
 a=assemble(pad_c_object.emit_padded_assembly(obj,layout,'generated_EC420',word_patches_path=guard),'target-generic')
 b=assemble(pad_generated_object.emit_padded_assembly(obj,asm,filename='generated_EC420',word_patches_path=guard),'target-generated')
 local=re.sub(r'(?m)^  jlabel (\S+)',r'  \1:',asm.read_text());original=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+local+'\n.size '+p.NAME+',.-'+p.NAME+'\n','original-reference')
 assert p.payload(a)==p.payload(b)==p.payload(original)==(expected,nrefs)
 lookup={v[1]:v[2][1] for v in p.symbol_rows((p.out/'frozen/conker/build/conker.us.elf').read_bytes())};symbols={name:lookup[name] for entries in refs.values() for _,name in entries};truth=struct.unpack_from('>74I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM);programs=[words(v,symbols) for v in (a,b,original)];assert all(tuple(v)==truth for v in programs)
 links=0
 for low in (0,0x7ffc,0x8000,0xfffc):
  syms={name:(value&0xffff0000)|low for name,value in symbols.items()}
  for i,path in enumerate((a,b,original)):
   expected_words=words(path,syms);script=p.out/('rebase-%X-%d.ld'%(low,i));script.write_text('SECTIONS { .text 0x150BF0F4 : SUBALIGN(4) { *(.text) } }\n');linked=script.with_suffix('.elf');v=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',p.NAME,*['--defsym=%s=0x%X'%item for item in syms.items()],'-o',str(linked),str(path)],capture_output=True,text=True);assert v.returncode==0,v.stderr
   binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(linked),str(binary)],capture_output=True,check=True);assert expected_words==list(struct.unpack_from('>74I',binary.read_bytes()));links+=1
 cuts=0
 for c in (g.Case(1,1,7,1,12,3,-2,-1,2,3,126),g.Case(0,7,4,4,1,3,-2,-1,2,3,0,1)):
  full=g.Oracle(programs[0],c);full.run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    machine=g.Oracle(ws,c);machine.cut=cut
    try:machine.run()
    except AccessBoundary:pass
    else:raise AssertionError(('Missing access cut',cut))
    models.append(machine)
   assert all(state(m)==state(models[0]) for m in models[1:]);cuts+=1
 report=dict(body_words=74,generic_generated_original_bindings_equal=True,guards=28,GNU_rebased_links=links,access_cut_triples=cuts,hardware_or_C_fault_not_qualified=True,source_installed=False)
 (p.out/'boundaries-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
