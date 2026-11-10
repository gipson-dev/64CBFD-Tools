"""Direct emission, both padders, relocation integrity and memory-cut states."""
import csv,hashlib,json,struct,subprocess,sys
from tools.experiments import game_paired_float_approach_1505a250_match as p
from tools.tests import game_paired_float_approach_1505a250_oracle as g
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.tests.game_actor_audio_handle_15060778_controls import reachable
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
SHA='8e12fbdcf9b2df5b3d7ab2bbdf679bfd309c69f8ecb416f6d05ea242b48d3782'
REFS={76:[('R_MIPS_HI16','D_800D1550')],80:[('R_MIPS_LO16','D_800D1550')]}
def checked(raw,refs):
 if hashlib.sha256(raw).hexdigest()!=SHA or refs!=REFS:raise ValueError('Changed direct float-pair words or bindings')
 return raw,refs
def assemble(text,label):
 path=p.out/(label+'.s');path.write_text(text);obj=path.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=p.root/'conker',capture_output=True,check=True);return obj
def independent():
 raw,refs=checked(*p.payload(p.out/'selected.o'));text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+p.NAME+'\n.type '+p.NAME+',@function\n'+p.NAME+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(i*4,[]):text+='.reloc ., '+kind+', '+name+'\n'
  text+='.word 0x%08X\n'%w
 obj=assemble(text+'.size '+p.NAME+',.-'+p.NAME+'\n','target-raw');lines=(p.root/'conker/retail_layout.us.txt').read_text().splitlines();selected=[l for l in lines[1:]if l.split(',')[1:3]==['game_83300',p.NAME]];assert len(selected)==1;layout=p.out/'target-layout.csv';layout.write_text(lines[0]+'\n'+selected[0]+'\n')
 guard=p.out/'empty-guards.csv';fields=next(csv.reader((p.root/'conker/retail_word_patches.us.csv').open()));guard.write_text(','.join(fields)+'\n');asm=p.root/'conker/asm/nonmatchings/game_83300/func_1505A250.s'
 a=assemble(pad_c_object.emit_padded_assembly(obj,layout,'game_83300',word_patches_path=guard),'target-generic');b=assemble(pad_generated_object.emit_padded_assembly(obj,asm,filename='game_83300',word_patches_path=guard),'target-generated')
 original=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm.read_text()+'\n.size '+p.NAME+',.-'+p.NAME+'\n','original-reference')
 assert p.payload(a)==p.payload(b)==p.payload(original)==(raw,refs)
 failures=0
 for i in range(86):
  wrong=bytearray(raw);wrong[4*i+3]^=1
  try:checked(bytes(wrong),refs)
  except ValueError:failures+=1
  else:raise AssertionError(i)
 for offset,entries in refs.items():
  wrong=dict(refs);wrong[offset]=[(kind,name+'_stale')for kind,name in entries]
  try:checked(raw,wrong)
  except ValueError:failures+=1
  else:raise AssertionError(offset)
 return dict(direct_raw_generic_generated_original_equal=True,word_and_binding_corruptions=failures,guards=0)
def rebases():
 runs=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  address=0x80300000+low
  for path in(p.out/'selected.o',p.out/'target-generic.o',p.out/'original-reference.o'):
   ws=g.words(path,address)
   for c in(g.Case(),g.Case(alias=1),g.Case(alias=2),g.Case(alias=3)):
    m=g.Oracle(ws,g.fixture(c,address),c,entry=g.ENTRY+0x4000,s=address);m.run();g.check(m,c,address);runs+=1
 return dict(executions=runs,independent_symbol_sets=4,raw_padded_original=True)
def faults():
 programs=(g.words(p.out/'selected.o'),struct.unpack_from('>86I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM));pairs=0
 for c in(g.Case(),g.Case(x=0,z=0),g.Case(alias=1),g.Case(alias=2),g.Case(alias=4),g.Case(alias=5)):
  whole=g.Oracle(programs[0],g.fixture(c),c);whole.run()
  for cut in range(whole.all_accesses):
   models=[]
   for ws in programs:
    m=g.Oracle(ws,g.fixture(c),c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Guest cut not reached')
    models.append(m)
   a,b=models;assert(a.memory,a.r,a.f,a.trace,a.current_pc,a.delay_of)==(b.memory,b.r,b.f,b.trace,b.current_pc,b.delay_of),(c,cut);pairs+=1
 return dict(exact_access_cut_pairs=pairs,portable_C_fault_semantics_qualified=False)
def main():
 ws=g.words(p.out/'selected.o');cfg=reachable(ws,p.ENTRY);assert cfg['unreachable']==[75]and cfg['reachable_words']==85
 result=dict(CFG=cfg,padders=independent(),rebases=rebases(),faults=faults());(p.out/'boundaries.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
