"""Direct emission, both padders, relocation integrity and memory-cut states."""
import csv,hashlib,json,struct,subprocess,sys
from tools.experiments import game_slot_sector_search_1505dda8_match as p
from tools.tests import game_slot_sector_search_1505dda8_oracle as g
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.tests.game_actor_audio_handle_15060778_controls import reachable
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
SHA='2cf85beab984bd928109f18e69537a656b5abee363fc8f83e79973b972cfc2e8'
REFS={72:[('R_MIPS_HI16','D_80082FA0')],76:[('R_MIPS_LO16','D_80082FA0')],96:[('R_MIPS_HI16','D_800CC2D0')],104:[('R_MIPS_LO16','D_800CC2D0')],180:[('R_MIPS_26','func_1505DF10')],272:[('R_MIPS_HI16','D_80082FA0')],276:[('R_MIPS_LO16','D_80082FA0')]}
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
 guard=p.out/'empty-guards.csv';fields=next(csv.reader((p.root/'conker/retail_word_patches.us.csv').open()));guard.write_text(','.join(fields)+'\n');asm=p.root/'conker/asm/nonmatchings/game_83300/func_1505DDA8.s'
 a=assemble(pad_c_object.emit_padded_assembly(obj,layout,'game_83300',word_patches_path=guard),'target-generic');b=assemble(pad_generated_object.emit_padded_assembly(obj,asm,filename='game_83300',word_patches_path=guard),'target-generated')
 original=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm.read_text()+'\n.size '+p.NAME+',.-'+p.NAME+'\n','original-reference')
 assert p.payload(a)==p.payload(b)==p.payload(original)==(raw,refs)
 failures=0
 for i in range(90):
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
  symbols={'D_80082FA0':0x80300000+(low^0x8000),'D_800CC2D0':0x80400000+low,'func_1505DF10':0x15200000+low}
  for path in(p.out/'selected.o',p.out/'target-generic.o',p.out/'original-reference.o'):
   ws=g.words(path,symbols)
   for c in(g.Case(),g.Case(mutation=4,match=-1,new_limit=0),g.Case(alias=0),g.Case(alias=3,mutation=3)):
    m=g.Oracle(ws,g.fixture(c,symbols),c,entry=g.ENTRY+0x40000,s=symbols);m.run();g.check(m,c,symbols);runs+=1
 return dict(executions=runs,independent_symbol_sets=4,raw_padded_original=True)

def faults():
 programs=(g.words(p.out/'selected.o'),struct.unpack_from('>90I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM));pairs=0
 for c in(g.Case(),g.Case(limit=-1),g.Case(alias=0),g.Case(mutation=15,match=-1),g.Case(mutation=16),g.Case(state=0x80000000)):
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
def cfg(ws):
 # Width is masked into saved S2 at entry and copied to V0 immediately before
 # BGEZ. The intervening helper preserves S2 under the O32 ABI.
 assert ws[6]==0x30D2FFFF and ws[54]==0x02401025 and ws[55]==0x03284823 and ws[56]==0x04410003
 def writes(w):
  op=w>>26
  if op==0:return(w>>11)&31 if w&63 not in(8,24,25,26,27)else None
  if op in(1,2,3,4,5,6,7,17,20,21,22,23,40,41,42,43,46,49,53,57,61):return None
  return(w>>16)&31
 assert all(writes(w)!=18 for w in ws[7:54]);assert ws[45]>>26==3
 reduced=list(ws);reduced[56]=0x10000003
 result=reachable(reduced,p.ENTRY);assert result['unreachable']==[58,59]and result['reachable_words']==88
 result['unsigned_width_branch_proof']=dict(mask_word=6,copy_word=54,branch_word=56,saved_register=18,helper_ABI_preserves_width=True);return result
def main():
 ws=g.words(p.out/'selected.o');result=dict(CFG=cfg(ws),padders=independent(),rebases=rebases(),faults=faults());(p.out/'boundaries.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
