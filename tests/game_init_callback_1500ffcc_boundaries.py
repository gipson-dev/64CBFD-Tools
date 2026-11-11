"""Both padders, relocation pins, rebases and bounded access cuts."""
import csv,io,json,re,struct,subprocess,sys
from tools.experiments import game_init_callback_1500ffcc_match as p
from tools.tests import game_init_callback_1500ffcc_oracle as g
from tools.experiments import game_init_callback_1500ffcc_match as n
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def assemble(text,label):
 path=p.out/(label+'.s');path.write_text(text);obj=path.with_suffix('.o')
 v=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=p.root/'conker',capture_output=True,text=True)
 assert v.returncode==0 and not v.stdout and not v.stderr,(v.stdout,v.stderr);return obj
def words(obj,syms):
 raw,refs=p.payload(obj);return p.bound_blob(raw,refs,syms)
def main():
 asm=p.out/'original-target.s';full=(p.root/'conker/asm/3D2E0.s').read_text();start=full.index('glabel '+p.NAME+'\n');end=full.index('endlabel '+p.NAME,start)+len('endlabel '+p.NAME);asm.write_text(full[start:end]+'\n')
 raw,refs=p.payload(p.out/'independent-selected.o');normal,nrefs=n.normalize(raw,refs)
 text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+p.NAME+'\n.type '+p.NAME+',@function\n'+p.NAME+':\n'
 for i,(word,) in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(i*4,[]):text+='.reloc ., '+kind+', '+name+'\n'
  text+='.word 0x%08X\n'%word
 obj=assemble(text+'.size '+p.NAME+',.-'+p.NAME+'\n','target-raw');assert p.payload(obj)==(raw,refs)
 lines=(p.root/'conker/retail_layout.us.txt').read_text().splitlines();entries=[line for line in lines[1:] if line.split(',')[1:3]==['generated_3D2E0',p.NAME]];assert len(entries)==1
 layout=p.out/'target-layout.csv';layout.write_text(lines[0]+'\n'+entries[0]+'\n')
 fields=next(csv.reader(io.StringIO((p.root/'conker/retail_word_patches.us.csv').read_text())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(n.rows(raw,refs));guard=p.out/'target-guards.csv';guard.write_text(stream.getvalue())
 a=assemble(pad_c_object.emit_padded_assembly(obj,layout,'generated_3D2E0',word_patches_path=guard),'target-generic')
 b=assemble(pad_generated_object.emit_padded_assembly(obj,p.out/'original-target.s',filename='generated_3D2E0',word_patches_path=guard),'target-generated')
 local=re.sub(r'(?m)^  jlabel (\S+)',r'  \1:',asm.read_text());original=assemble('.include \"macro.inc\"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+local+'\n.size '+p.NAME+',.-'+p.NAME+'\n','original-reference');assert p.payload(a)==p.payload(b)==p.payload(original)==(normal,nrefs)
 failures=0
 for i in range(len(raw)):
  wrong=bytearray(raw);wrong[i]^=1
  try:n.normalize(bytes(wrong),refs)
  except ValueError:failures+=1
  else:raise AssertionError(i)
 for at,entries in refs.items():
  for change in (0,1):
   wrong=dict(refs);wrong[at]=[(kind+'_stale' if change else kind,name if change else name+'_stale') for kind,name in entries]
   try:n.normalize(raw,wrong)
   except ValueError:failures+=1
   else:raise AssertionError(at)
 guardfails=0
 for i in range(15):
  altered=[dict(row) for row in n.rows(raw,refs)];altered[i]['expected']='0x%08X'%(int(altered[i]['expected'],16)^1)
  stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(altered);bad=p.out/'bad-guard.csv';bad.write_text(stream.getvalue())
  try:pad_c_object.emit_padded_assembly(obj,layout,'generated_3D2E0',word_patches_path=bad)
  except (ValueError,AssertionError):guardfails+=1
  else:raise AssertionError(i)
 lookup={v[1]:v[2][1] for v in p.symbol_rows((p.out/'frozen/conker/build/conker.us.elf').read_bytes())}
 symbols={name:lookup[name] for entries in refs.values() for _,name in entries};links=0
 for low in (0,0x7ffc,0x8000,0xfffc):
  syms={name:(value&0xffff0000)|low for name,value in symbols.items()}
  for i,path in enumerate((obj,a,b,original)):
   expected=words(path,syms);script=p.out/('rebase-%X-%d.ld'%(low,i));script.write_text('SECTIONS { .text 0x1500FFCC : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf')
   v=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',p.NAME,*['--defsym=%s=0x%X'%item for item in syms.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert v.returncode==0,v.stderr
   binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True)
   assert expected==list(struct.unpack_from('>79I',binary.read_bytes()));links+=1
 programs=[words(v,symbols) for v in (obj,a,b,original)];assert programs[1]==programs[2]==programs[3]
 quads=0
 for c in (g.Case(0,0,0),g.Case(1,0,0),g.Case(0,1,1),g.Case(1,1,1)):
  full=g.Oracle(programs[3],c);full.run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    machine=g.Oracle(ws,c);machine.cut=cut
    try:machine.run()
    except AccessBoundary:pass
    else:raise AssertionError(('Missing access cut',cut))
    models.append(machine)
   x,y,z,w=models;assert g.public(x.memory)==g.public(w.memory)
   assert all((v.memory,v.r,v.f,v.calls,v.trace,v.current_pc,v.delay_of)==(w.memory,w.r,w.f,w.calls,w.trace,w.current_pc,w.delay_of) for v in (y,z));quads+=1
 result=dict(body_words=79,guards=15,generic_generated_original_equal=True,byte_and_binding_corruptions=failures,individual_guard_corruptions=guardfails,GNU_rebased_links=links,access_cut_quads=quads,raw_private_stack_or_portable_faults_not_qualified=True,source_installed=False)
 (p.out/'boundaries-screen.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
