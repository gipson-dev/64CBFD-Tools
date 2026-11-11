"""Independent padding, rebased helpers, corruption rejection and access cuts."""
import csv,io,json,re,struct,subprocess,sys
from tools.experiments import game_sequence_direction_1501fe68_match as p
from tools.tests import game_sequence_direction_1501fe68_oracle as g
from tools.experiments import game_sequence_direction_1501fe68_match as n
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def assemble(text,label):
 path=p.out/(label+'.s');path.write_text(text);obj=path.with_suffix('.o');r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=p.root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,(label,r.stdout,r.stderr);return obj
def independent():
 raw,refs=p.payload(p.out/'selected.o',p.NAME);normal,rs=n.normalize(raw,refs);text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+p.NAME+'\n.type '+p.NAME+',@function\n'+p.NAME+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(4*i,[]):text+='.reloc ., '+kind+', '+name+'\n'
  text+='.word 0x%08X\n'%w
 obj=assemble(text+'.size '+p.NAME+',.-'+p.NAME+'\n','target-raw');lines=(p.root/'conker/retail_layout.us.txt').read_text(encoding='utf-8').splitlines();selected=[l for l in lines[1:]if l.split(',')[1:3]==['generated_49D30',p.NAME]];assert len(selected)==1;layout=p.out/'target-layout.csv';layout.write_text(lines[0]+'\n'+selected[0]+'\n');asm=p.out/'original-target.s';full=(p.root/'conker/asm/49D30.s').read_text(encoding='utf-8');start=full.index('glabel '+p.NAME+'\n');end=full.index('endlabel '+p.NAME,start)+len('endlabel '+p.NAME);asm.write_text(full[start:end]+'\n');guard=p.out/'target-guards.csv'
 fields=next(csv.reader(io.StringIO((p.root/'conker/retail_word_patches.us.csv').read_text(encoding='utf-8'))));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(n.rows(raw,refs));guard.write_text(stream.getvalue())
 a=assemble(pad_c_object.emit_padded_assembly(obj,layout,'generated_49D30',word_patches_path=guard),'target-generic');b=assemble(pad_generated_object.emit_padded_assembly(obj,asm,filename='generated_49D30',word_patches_path=guard),'target-generated');local=re.sub(r'(?m)^  jlabel (\S+)',r'  \1:',asm.read_text(encoding='utf-8'));original=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+local+'\n.size '+p.NAME+',.-'+p.NAME+'\n','original-reference');assert p.payload(a,p.NAME)==p.payload(b,p.NAME)==(normal,rs);assert g.words(original)==g.words(a)
 failures=0
 for i in range(384):
  wrong=bytearray(raw);wrong[i]^=1
  try:n.normalize(bytes(wrong),refs)
  except ValueError:failures+=1
  else:raise AssertionError(i)
 for at,es in refs.items():
  for change in(0,1):
   wrong=dict(refs);wrong[at]=[(kind+'_stale'if change else kind,name if change else name+'_stale')for kind,name in es]
   try:n.normalize(raw,wrong)
   except ValueError:failures+=1
   else:raise AssertionError(at)
 rows=n.rows(raw,refs);rejections=0
 for i in range(len(rows)):
  altered=[dict(row)for row in rows];altered[i]['expected']='0x%08X'%(int(altered[i]['expected'],16)^1);stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(altered);bad=p.out/'target-bad-guard.csv';bad.write_text(stream.getvalue())
  try:pad_c_object.emit_padded_assembly(obj,layout,'generated_49D30',word_patches_path=bad)
  except (ValueError,AssertionError):rejections+=1
  else:raise AssertionError(('Guard corruption accepted',i))
 return dict(raw_generic_generated_original_equal_after_closed_recipe=True,byte_and_binding_corruptions=failures,individual_guard_corruptions=rejections,guards=8,body_words=96)
def rebases():
 links=runs=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s={name:(0x15200000 if name.startswith('func_')else 0x80400000)+i*0x10000+low for i,name in enumerate(g.NAMES)};programs=[]
  for i,path in enumerate((p.out/'target-raw.o',p.out/'target-generic.o',p.out/'target-generated.o',p.out/'original-reference.o')):
   ws=g.words(path,s);script=p.out/('rebase-%X-%d.ld'%(low,i));script.write_text('SECTIONS { .text 0x1501FE68 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf');subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',p.NAME,*['--defsym=%s=0x%X'%item for item in s.items()],'-o',str(elf),str(path)],capture_output=True,check=True);binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True);assert ws==list(struct.unpack_from('>96I',binary.read_bytes()));links+=1;programs.append(ws)
   for c in(g.Case(count=0,alias=5,invalid=1),g.Case(count=1,alias=5,invalid=1),g.Case(count=2,flag=0),g.Case(count=2,flag=1,mutation=31)):g.run(ws,c,s);runs+=1
  assert programs[1]==programs[2]==programs[3]
 return dict(GNU_linker_comparisons=links,executions=runs,independent_symbol_sets=4)
def faults():
 raw=g.words(p.out/'selected.o');normal=g.words(p.out/'target-generic.o');truth=struct.unpack_from('>96I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM);triples=0
 cases=(g.Case(count=0,alias=5,invalid=1),g.Case(count=1,alias=5,invalid=1),g.Case(count=2,flag=0),g.Case(count=2,flag=1),g.Case(count=3,flag=1,mutation=15,alias=1),g.Case(count=2,flag=0,mutation=31,alias=4))
 for c in cases:
  whole=g.run(truth,c)
  for cut in range(whole.all_accesses):
   models=[]
   for ws in(raw,normal,truth):
    m=g.Oracle(ws,g.fixture(c),c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Access cut not reached')
    models.append(m)
   a,b,d=models;assert g.public(a.memory)==g.public(d.memory);assert(b.memory,b.r,b.f,b.trace,b.calls,b.current_pc,b.delay_of)==(d.memory,d.r,d.f,d.trace,d.calls,d.current_pc,d.delay_of);triples+=1
 return dict(literal_access_cut_triples=triples,raw_private_stack_or_portable_C_faults_not_claimed=True)
def main():
 r=dict(padders=independent(),rebases=rebases(),faults=faults());(p.out/'boundaries.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
