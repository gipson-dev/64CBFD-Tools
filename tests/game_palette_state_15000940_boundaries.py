"""Independent padders, real split-relocation links, aliases and access cuts."""
import json,struct,subprocess,re
from tools.experiments import game_palette_state_15000940_match as p
from tools.tests import game_palette_state_15000940_oracle as g
from tools.experiments import game_palette_state_15000940_match as n
from tools import pad_generated_object
import sys
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def assemble(text,label):
 path=p.out/(label+'.s');path.write_text(text);obj=path.with_suffix('.o');r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=p.root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,(label,r.stdout,r.stderr);return obj
def independent():
 raw,refs=p.payload(p.out/'selected.o');normal,rs=n.normalize(raw,refs);text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+p.NAME+'\n.type '+p.NAME+',@function\n'+p.NAME+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(4*i,[]):text+='.reloc ., '+kind+', '+name+'\n'
  text+='.word 0x%08X\n'%w
 obj=assemble(text+'.size '+p.NAME+',.-'+p.NAME+'\n','target-raw');lines=(p.root/'conker/retail_layout.us.txt').read_text(encoding='utf-8').splitlines();selected=[l for l in lines[1:]if l.split(',')[1:3]==['game_2DDF0',p.NAME]];assert len(selected)==1;layout=p.out/'target-layout.csv';layout.write_text(lines[0]+'\n'+selected[0]+'\n');asm=p.out/'original-target.s';guard=p.out/'target-guards.csv'
 import csv,io
 stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=lines_guard_fields());writer.writeheader();writer.writerows(n.rows(raw,refs));guard.write_text(stream.getvalue())
 a=assemble(pad_c_object.emit_padded_assembly(obj,layout,'game_2DDF0',word_patches_path=guard),'target-generic');b=assemble(pad_generated_object.emit_padded_assembly(obj,asm,filename='game_2DDF0',word_patches_path=guard),'target-generated');local=re.sub(r'(?m)^  jlabel (\S+)',r'  \1:',asm.read_text(encoding='utf-8'));original=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+local+'\n.size '+p.NAME+',.-'+p.NAME+'\n','original-reference');assert p.payload(a)==p.payload(b)==(normal,rs);assert g.words(original)==g.words(a)
 failures=0
 for i in range(380):
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
 return dict(raw_generic_generated_original_equal_after_closed_recipe=True,byte_and_binding_corruptions=failures,guards=len(n.rows(raw,refs)),body_words=95,retail_slot_words=96)
def lines_guard_fields():
 import csv,io
 return next(csv.reader(io.StringIO((p.root/'conker/retail_word_patches.us.csv').read_text(encoding='utf-8'))))
def rebases():
 links=runs=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s={name:0x80400000+i*0x10000+low for i,name in enumerate(g.NAMES)};s['D_800D9EB7']=s['D_800D9EB4']+3;s['D_800D9EC4']=s['D_800D9EB8']+12
  programs=[]
  for i,path in enumerate((p.out/'target-raw.o',p.out/'target-generic.o',p.out/'target-generated.o',p.out/'original-reference.o')):
   ws=g.words(path,s);script=p.out/('rebase-%X-%d.ld'%(low,i));script.write_text('SECTIONS { .text 0x15000940 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf');subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',p.NAME,*['--defsym=%s=0x%X'%item for item in s.items()],'-o',str(elf),str(path)],capture_output=True,check=True);binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True);assert ws==list(struct.unpack_from('>95I',binary.read_bytes()));links+=1;programs.append(ws)
   for c in(g.Case(index=0),g.Case(index=6),g.Case(index=7),g.Case(index=255,generic=1)):g.run(ws,c,s);runs+=1
  assert programs[1]==programs[2]==programs[3]
 return dict(GNU_linker_comparisons=links,executions=runs,independent_symbol_sets=4,fixed_array_end_relations_retained=True)
def faults():
 raw=g.words(p.out/'selected.o');normal=g.words(p.out/'target-generic.o');truth=struct.unpack_from('>95I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM);pairs=0;aliases=0
 for c in(g.Case(index=0),g.Case(index=6),g.Case(index=255,generic=1)):
  whole=g.run(truth,c)
  for cut in range(whole.all_accesses):
   models=[]
   for ws in(raw,normal,truth):
    m=g.Oracle(ws,g.fixture(c),c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Cut not reached')
    models.append(m)
   a,b,d=models;assert(a.memory,a.trace)==(d.memory,d.trace);assert(b.memory,b.r,b.f,b.trace,b.current_pc,b.delay_of)==(d.memory,d.r,d.f,d.trace,d.current_pc,d.delay_of);pairs+=1
 for name,dest in(('D_800A2CE8','D_800D9E88'),('D_800A2CEC','D_800D9E70'),('D_800A2D04','D_800D9EB4'),('D_800D9E98','D_800D9E88'),('D_800D9EA8','D_800D9EB8')):
  s=g.symbols();s[name]=s[dest]
  for c in(g.Case(index=0),g.Case(index=6),g.Case(index=7)):
   a,b,d=[g.run(g.words(path,s),c,s)for path in(p.out/'target-raw.o',p.out/'target-generic.o',p.out/'original-reference.o')];assert(a.memory,a.trace)==(d.memory,d.trace);assert(b.memory,b.r,b.f,b.trace)==(d.memory,d.r,d.f,d.trace);aliases+=1
 return dict(literal_access_cut_triples=pairs,guest_alias_triples=aliases,raw_private_registers_or_portable_C_faults_not_claimed=True)
def main():
 r=dict(padders=independent(),rebases=rebases(),faults=faults());(p.out/'boundaries.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
