"""Both padders, all switch destinations, GNU rebases and exact access-cut states."""
import csv,hashlib,json,re,struct,subprocess,sys
from tools.experiments import game_event_dispatch_1509d780_match as p
from tools.tests import game_event_dispatch_1509d780_oracle as g
from tools.experiments import game_event_dispatch_1509d780_match as q
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,read_c_string
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
SHA='0bbcf5457f7ff0d71971b08734cf0eba9bb02ceeb96271d66c3e12a16ee43f98'
REFS={28:[('R_MIPS_HI16','.rodata')],36:[('R_MIPS_LO16','.rodata')],48:[('R_MIPS_26','func_150EB8C4')],64:[('R_MIPS_26','func_150F9720')],88:[('R_MIPS_26','func_151616D0')],112:[('R_MIPS_26','func_1505EEF4')],128:[('R_MIPS_26','func_150F6DB0')],152:[('R_MIPS_26','func_151616D0')],168:[('R_MIPS_26','func_151CD394')],184:[('R_MIPS_HI16','D_800D9920')],192:[('R_MIPS_LO16','D_800D9920')],196:[('R_MIPS_26','func_150E35DC')],212:[('R_MIPS_26','func_150B3DD0')],236:[('R_MIPS_26','func_1505EEF4')],260:[('R_MIPS_26','func_150C5C9C')],276:[('R_MIPS_26','func_150C522C')],292:[('R_MIPS_26','func_151D2718')],316:[('R_MIPS_26','func_151616D0')],340:[('R_MIPS_26','func_151616D0')],356:[('R_MIPS_26','func_151616D0')]}
def checked(raw,refs):
 if hashlib.sha256(raw).hexdigest()!=SHA or refs!=REFS:raise ValueError('Changed command-dispatch words or bindings')
 return raw,refs
def assemble(text,label):
 path=p.out/(label+'.s');path.write_text(text);obj=path.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=p.root/'conker',capture_output=True,check=True);return obj
def independent():
 raw,refs=checked(*p.payload(p.out/'selected.o'));text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+p.NAME+'\n.type '+p.NAME+',@function\n'+p.NAME+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(4*i,[]):text+='.reloc ., '+kind+', '+('jtbl_8009F1AC_game'if name=='.rodata'else name)+'\n'
  text+='.word 0x%08X\n'%w
 obj=assemble(text+'.size '+p.NAME+',.-'+p.NAME+'\n','target-raw');lines=(p.root/'conker/retail_layout.us.txt').read_text(encoding='utf-8').splitlines();selected=[l for l in lines[1:]if l.split(',')[1:3]==['generated_C9EC0',p.NAME]];assert len(selected)==1;layout=p.out/'target-layout.csv';layout.write_text(lines[0]+'\n'+selected[0]+'\n')
 guard=p.out/'empty-guards.csv';fields=next(csv.reader((p.root/'conker/retail_word_patches.us.csv').open()));guard.write_text(','.join(fields)+'\n');asm=p.out/'original-target.s';a=assemble(pad_c_object.emit_padded_assembly(obj,layout,'generated_C9EC0',word_patches_path=guard),'target-generic');b=assemble(pad_generated_object.emit_padded_assembly(obj,asm,filename='generated_C9EC0',word_patches_path=guard),'target-generated');local=re.sub(r'(?m)^  jlabel (\S+)',r'  \1:',asm.read_text(encoding='utf-8'));original=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+local+'\n.size '+p.NAME+',.-'+p.NAME+'\n','original-reference')
 assert p.payload(a)==p.payload(b)==p.payload(obj);assert g.words(original)==g.words(a)
 failures=0
 for i in range(95):
  wrong=bytearray(raw);wrong[4*i+3]^=1
  try:checked(bytes(wrong),refs)
  except ValueError:failures+=1
  else:raise AssertionError(i)
 for at,es in refs.items():
  wrong=dict(refs);wrong[at]=[(kind,name+'_stale')for kind,name in es]
  try:checked(raw,wrong)
  except ValueError:failures+=1
  else:raise AssertionError(at)
 data=(p.out/'selected.o').read_bytes();header=ELF_HEADER.unpack_from(data);hs=[SECTION_HEADER.unpack_from(data,header[6]+i*header[11])for i in range(header[12])];sh=hs[header[13]];names=data[sh[4]:sh[4]+sh[5]];ro=next(h for h in hs if read_c_string(names,h[0])=='.rodata');pool_failures=0
 for i in range(40):
  wrong=bytearray(data);wrong[ro[4]+4*i+3]^=1;file=p.out/'wrong-pool.o';file.write_bytes(wrong)
  try:q.check_pool(p.out/'independent-before.o',file)
  except(AssertionError,ValueError):pool_failures+=1
  else:raise AssertionError(('accepted wrong pool entry',i))
 return dict(raw_generic_generated_original_bound_equal=True,word_and_binding_corruptions=failures,pool_entry_corruptions=pool_failures,guards=0)
def rebases():
 runs=links=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s=g.symbols();s.update({k:0x80400000+low for k in('.rodata','jtbl_8009F1AC_game','jtbl_8009F1AC')});s['D_800D9920']=0x80500000+(low^0x8000)
  for i,a in enumerate(g.COUNTS):s['func_%08X'%a]=0x15200000+0x10000*i+low
  programs=[]
  for i,path in enumerate((p.out/'target-raw.o',p.out/'target-generic.o',p.out/'target-generated.o',p.out/'original-reference.o')):
   ws=g.words(path,s);script=p.out/('rebase-%X-%d.ld'%(low,i));script.write_text('SECTIONS { .text 0x1509D780 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf');subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',p.NAME,*['--defsym=%s=0x%X'%item for item in s.items()if item[0]!='.rodata'],'-o',str(elf),str(path)],capture_output=True,check=True);binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True);assert ws==list(struct.unpack_from('>95I',binary.read_bytes()));links+=1;programs.append(ws)
   for c in(g.Case(command=2),g.Case(command=9,mutation=7),g.Case(command=19),g.Case(command=22),g.Case(command=39)):
    m=g.Oracle(ws,g.fixture(c,s),c,s=s);m.run();g.check(m,c,s);runs+=1
  assert all(w==programs[0]for w in programs)
 return dict(executions=runs,GNU_linker_comparisons=links,independent_symbol_sets=4)
def faults():
 programs=(g.words(p.out/'selected.o'),struct.unpack_from('>95I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM));pairs=0
 for c in(g.Case(command=1),g.Case(command=2),g.Case(command=9,found=0),g.Case(command=36,mutation=7),g.Case(command=19),g.Case(command=22,mutation=7),g.Case(command=39)):
  whole=g.Oracle(programs[0],g.fixture(c),c);whole.run()
  for cut in range(whole.all_accesses):
   models=[]
   for ws in programs:
    m=g.Oracle(ws,g.fixture(c),c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Cut not reached')
    models.append(m)
   a,b=models;assert(a.memory,a.r,a.f,a.trace,a.calls,a.current_pc,a.delay_of)==(b.memory,b.r,b.f,b.trace,b.calls,b.current_pc,b.delay_of);pairs+=1
 return dict(exact_access_cut_pairs=pairs,portable_C_fault_semantics_qualified=False)
def main():
 result=dict(padders=independent(),rebases=rebases(),faults=faults());(p.out/'boundaries.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
