"""Independent padders, alias-carry relocation checks and exact memory-access cuts."""
import csv,hashlib,json,struct,subprocess,sys
from tools.experiments import game_slot_allocation_1505ed34_match as p
from tools.tests import game_slot_allocation_1505ed34_oracle as g
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
SHA='7c935f52cc45b0ac9c592bb9d583f86a1230b3ca5a938b7933e1fd17b9bdccdb'
REFS={4:[('R_MIPS_HI16','D_800CC2D0')],8:[('R_MIPS_LO16','D_800CC2D0')],16:[('R_MIPS_HI16','D_800CC2D0')],20:[('R_MIPS_LO16','D_800CC2D0')],96:[('R_MIPS_HI16','D_800CC2D0')],100:[('R_MIPS_LO16','D_800CC2D0')],180:[('R_MIPS_26','func_15060F28')],188:[('R_MIPS_HI16','D_800CC2D0')],192:[('R_MIPS_LO16','D_800CC2D0')],216:[('R_MIPS_HI16','D_800CC2D0')],220:[('R_MIPS_LO16','D_800CC2D0')],296:[('R_MIPS_26','func_15060F28')],340:[('R_MIPS_26','func_15060F28')],352:[('R_MIPS_26','func_1505F188')]}
def checked(raw,refs):
 if hashlib.sha256(raw).hexdigest()!=SHA or refs!=REFS:raise ValueError('Changed direct allocation words or bindings')
 return raw,refs
def assemble(text,label):
 path=p.out/(label+'.s');path.write_text(text);obj=path.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=p.root/'conker',capture_output=True,check=True);return obj
def independent():
 raw,refs=checked(*p.payload(p.out/'selected.o'));text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+p.NAME+'\n.type '+p.NAME+',@function\n'+p.NAME+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(4*i,[]):text+='.reloc ., '+kind+', '+name+'\n'
  text+='.word 0x%08X\n'%w
 obj=assemble(text+'.size '+p.NAME+',.-'+p.NAME+'\n','target-raw');lines=(p.root/'conker/retail_layout.us.txt').read_text(encoding='utf-8').splitlines();selected=[l for l in lines[1:]if l.split(',')[1:3]==['game_83300',p.NAME]];assert len(selected)==1;layout=p.out/'target-layout.csv';layout.write_text(lines[0]+'\n'+selected[0]+'\n')
 guard=p.out/'empty-guards.csv';fields=next(csv.reader((p.root/'conker/retail_word_patches.us.csv').open()));guard.write_text(','.join(fields)+'\n');asm=p.root/'conker/asm/nonmatchings/game_83300/func_1505ED34.s'
 a=assemble(pad_c_object.emit_padded_assembly(obj,layout,'game_83300',word_patches_path=guard),'target-generic');b=assemble(pad_generated_object.emit_padded_assembly(obj,asm,filename='game_83300',word_patches_path=guard),'target-generated');original=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm.read_text(encoding='utf-8')+'\n.size '+p.NAME+',.-'+p.NAME+'\n','original-reference')
 assert p.payload(a)==p.payload(b)==(raw,refs)
 assert g.words(original)==g.words(a)
 original_raw,original_refs=p.payload(original);assert original_refs[96]==[('R_MIPS_HI16','D_800CC4A4')]and original_refs[100]==[('R_MIPS_LO16','D_800CC4A4')]
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
 return dict(raw_generic_generated_equal=True,original_equal_after_field_alias_binding=True,field_alias_offset=0x1D4,word_and_binding_corruptions=failures,guards=0)
def linked_words(path,s,label):
 script=p.out/(label+'.ld');script.write_text('SECTIONS { .text 0x1505ED34 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf');subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',p.NAME,*['--defsym=%s=0x%X'%item for item in s.items()],'-o',str(elf),str(path)],capture_output=True,check=True);binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True);return list(struct.unpack_from('>95I',binary.read_bytes()))
def rebases():
 runs=0;links=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  s=dict(D_800CC2D0=0x80400000+low,D_800CC4A4=0x804001D4+low,func_15060F28=0x15200000+low,func_1505F188=0x15300000+(low^0x8000));programs=[]
  for i,path in enumerate((p.out/'target-raw.o',p.out/'target-generic.o',p.out/'target-generated.o',p.out/'original-reference.o')):
   ws=g.words(path,s);assert ws==linked_words(path,s,'rebase-%X-%d'%(low,i));links+=1;programs.append(ws)
   for c in(g.Case(empty=24),g.Case(clear=24,mutation=31),g.Case(recycle=24),g.Case()):
    m=g.Oracle(ws,g.fixture(c,s),c,s=s);m.run();g.check(m,c,s);runs+=1
  assert all(ws==programs[0]for ws in programs)
  bad=dict(s);bad['D_800CC4A4']+=4;assert g.words(p.out/'original-reference.o',bad)!=programs[0]
 return dict(executions=runs,GNU_linker_comparisons=links,independent_symbol_sets=4,field_alias_negative_controls=4)
def faults():
 programs=(g.words(p.out/'selected.o'),struct.unpack_from('>95I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM));pairs=0
 for c in(g.Case(empty=0),g.Case(empty=24),g.Case(clear=24,mutation=31),g.Case(recycle=24,mutation=31),g.Case(mutation=31),g.Case(reserved=0)):
  whole=g.Oracle(programs[0],g.fixture(c),c);whole.run()
  for cut in range(whole.all_accesses):
   models=[]
   for ws in programs:
    m=g.Oracle(ws,g.fixture(c),c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Guest cut not reached')
    models.append(m)
   a,b=models;assert(a.memory,a.r,a.f,a.trace,a.calls,a.current_pc,a.delay_of)==(b.memory,b.r,b.f,b.trace,b.calls,b.current_pc,b.delay_of),(c,cut);pairs+=1
 return dict(exact_access_cut_pairs=pairs,portable_C_fault_semantics_qualified=False)
def main():
 result=dict(padders=independent(),rebases=rebases(),faults=faults());(p.out/'boundaries.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
