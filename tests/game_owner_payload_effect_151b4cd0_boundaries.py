"""Independent padders, GNU relocations and literal retail access-cut states."""
import csv,hashlib,json,re,struct,subprocess,sys
from tools.experiments import game_owner_payload_effect_151b4cd0_match as p
from tools.tests import game_owner_payload_effect_151b4cd0_oracle as g
SHA='c3f01171ee87995283456007e0f57acf3699c57b0a4a7952740dd4ec50289fc2'
REFS={36: [('R_MIPS_26', 'func_15134070')], 72: [('R_MIPS_HI16', 'D_800A3FE6')], 80: [('R_MIPS_LO16', 'D_800A3FE6')], 112: [('R_MIPS_26', 'func_1516962C')], 160: [('R_MIPS_HI16', 'D_800AA3D0')], 168: [('R_MIPS_LO16', 'D_800AA3D0')], 212: [('R_MIPS_26', 'func_150ADA20')], 232: [('R_MIPS_HI16', 'D_800A3FE6')], 248: [('R_MIPS_LO16', 'D_800A3FE6')], 320: [('R_MIPS_26', 'func_1513418C')], 348: [('R_MIPS_26', 'memcpy')]}
def checked(raw,refs):
 if hashlib.sha256(raw).hexdigest()!=SHA or refs!=REFS:raise ValueError('Changed viewport words or bindings')
 return raw,refs

from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def assemble(text,label):
 path=p.out/(label+'.s');path.write_text(text);obj=path.with_suffix('.o');r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=p.root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,(label,r.stdout,r.stderr);return obj
def independent():
 raw,refs=p.payload(p.out/'selected.o');normal,nrefs=checked(raw,refs);text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+p.NAME+'\n.type '+p.NAME+',@function\n'+p.NAME+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(4*i,[]):text+='.reloc ., '+kind+', '+name+'\n'
  text+='.word 0x%08X\n'%w
 obj=assemble(text+'.size '+p.NAME+',.-'+p.NAME+'\n','target-raw');lines=(p.root/'conker/retail_layout.us.txt').read_text(encoding='utf-8').splitlines();selected=[l for l in lines[1:]if l.split(',')[1:3]==['generated_1E2180',p.NAME]];assert len(selected)==1;layout=p.out/'target-layout.csv';layout.write_text(lines[0]+'\n'+selected[0]+'\n');guard=p.out/'proposed-guards.csv';asm=p.out/'original-target.s'
 guard=p.out/'target-guards.csv';guard.write_text((p.root/'conker/retail_word_patches.us.csv').read_text(encoding='utf-8').splitlines()[0]+'\n')
 a=assemble(pad_c_object.emit_padded_assembly(obj,layout,'generated_1E2180',word_patches_path=guard),'target-generic');b=assemble(pad_generated_object.emit_padded_assembly(obj,asm,filename='generated_1E2180',word_patches_path=guard),'target-generated');local=re.sub(r'(?m)^  jlabel (\S+)',r'  \1:',asm.read_text(encoding='utf-8'));original=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+local+'\n.size '+p.NAME+',.-'+p.NAME+'\n','original-reference');assert p.payload(a)==p.payload(b)==(normal,nrefs);assert g.words(original)==g.words(a)
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
 return dict(raw_normalization_generic_generated_original_bound_equal=True,word_and_binding_corruptions=failures,guards=0)
def rebases():
 runs=links=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s=g.symbols()
  for i,name in enumerate(s):s[name]=(0x15200000 if (name.startswith('func_')or name=='memcpy')else 0x80400000)+0x10000*i+low
  programs=[]
  for i,path in enumerate((p.out/'target-raw.o',p.out/'target-generic.o',p.out/'target-generated.o',p.out/'original-reference.o')):
   ws=g.words(path,s);script=p.out/('rebase-%X-%d.ld'%(low,i));script.write_text('SECTIONS { .text 0x151B4CD0 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf');subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',p.NAME,*['--defsym=%s=0x%X'%item for item in s.items()],'-o',str(elf),str(path)],capture_output=True,check=True);binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True);assert ws==list(struct.unpack_from('>95I',binary.read_bytes()));links+=1;programs.append(ws)
   for c in(g.Case(owner=0),g.Case(kind=99),g.Case(class_byte=2),g.Case(mutation=15)):g.run(ws,c,s);runs+=1
  assert all(w==programs[1]for w in programs[1:])
 return dict(executions=runs,GNU_linker_comparisons=links,independent_symbol_sets=4)
def faults():
 programs=(g.words(p.out/'selected.o'),struct.unpack_from('>95I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM));pairs=0
 for c in(g.Case(owner=0),g.Case(kind=99),g.Case(class_byte=2),g.Case(outcome=0),g.Case(mutation=15),g.Case(mutation=63,alias=3)):
  whole=g.run(programs[0],c)
  for cut in range(whole.all_accesses):
   models=[]
   for ws in programs:
    m=g.Oracle(ws,g.fixture(c),c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Cut not reached')
    models.append(m)
   a,b=models;assert(a.memory,a.r,a.f,a.trace,a.calls,a.current_pc,a.delay_of)==(b.memory,b.r,b.f,b.trace,b.calls,b.current_pc,b.delay_of);pairs+=1
 return dict(exact_normalized_retail_access_cut_pairs=pairs,portable_C_fault_semantics_qualified=False,raw_intermediate_register_or_FCSR_equivalence_claimed=False)
def main():
 report=dict(padders=independent(),rebases=rebases(),faults=faults());(p.out/'boundaries.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
