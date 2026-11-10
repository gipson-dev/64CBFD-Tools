"""Both real padders, guarded zero/FP proof, rebases and retail access cuts."""
import csv,io,json,struct,subprocess,sys
from tools.experiments import game_actor_anchor_15060be0_match as p
from tools.tests import game_actor_anchor_15060be0_oracle as g
from tools.experiments import game_actor_anchor_15060be0_match as n
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.tests.game_actor_audio_handle_15060778_controls import reachable
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def assemble(text,label):
 path=p.out/(label+'.s');path.write_text(text);obj=path.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=p.root/'conker',capture_output=True,check=True);return obj
def guardfile(path,rows):
 fields=next(csv.reader((p.root/'conker/retail_word_patches.us.csv').open()));stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=fields);w.writeheader();w.writerows(rows);path.write_text(stream.getvalue());return path
def independent():
 raw,refs=p.payload(p.out/'selected.o');normal,nrefs=n.normalize(raw,refs);rows=n.rows(raw,refs);text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+p.NAME+'\n.type '+p.NAME+',@function\n'+p.NAME+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(i*4,[]):text+='.reloc ., '+kind+', '+name+'\n'
  text+='.word 0x%08X\n'%w
 obj=assemble(text+'.size '+p.NAME+',.-'+p.NAME+'\n','target-raw');lines=(p.root/'conker/retail_layout.us.txt').read_text().splitlines();selected=[l for l in lines[1:]if l.split(',')[1:3]==['game_83300',p.NAME]];assert len(selected)==1;layout=p.out/'target-layout.csv';layout.write_text(lines[0]+'\n'+selected[0]+'\n');guard=guardfile(p.out/'target-guards.csv',rows);asm=p.root/'conker/asm/nonmatchings/game_83300/func_15060BE0.s'
 a=assemble(pad_c_object.emit_padded_assembly(obj,layout,'game_83300',word_patches_path=guard),'target-generic');b=assemble(pad_generated_object.emit_padded_assembly(obj,asm,filename='game_83300',word_patches_path=guard),'target-generated');original=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm.read_text()+'\n.size '+p.NAME+',.-'+p.NAME+'\n','original-reference');assert p.payload(a)==p.payload(b)==p.payload(original)==(normal,nrefs)
 count=0
 for i in range(93):
  wrong=bytearray(raw);wrong[4*i+3]^=1
  try:n.normalize(bytes(wrong),refs)
  except ValueError:count+=1
  else:raise AssertionError(i)
 for at,vs in refs.items():
  wrong=dict(refs);wrong[at]=[(kind,name+'_stale')for kind,name in vs]
  try:n.normalize(raw,wrong)
  except ValueError:count+=1
  else:raise AssertionError(at)
 corrupt_rows=0
 for field in('expected','replacement','offset'):
  wrong=[dict(v)for v in rows];wrong[0][field]=hex(int(wrong[0][field],16)^4)
  try:n.checked_rows(wrong,raw,refs)
  except ValueError:corrupt_rows+=1
  else:raise AssertionError(field)
 wrong=[dict(v)for v in rows];wrong[0]['expected']=hex(int(wrong[0]['expected'],16)^1);stale=guardfile(p.out/'stale-guards.csv',wrong);rejected=0
 for emit in(lambda:pad_c_object.emit_padded_assembly(obj,layout,'game_83300',word_patches_path=stale),lambda:pad_generated_object.emit_padded_assembly(obj,asm,filename='game_83300',word_patches_path=stale)):
  try:emit()
  except(ValueError,AssertionError):rejected+=1
  else:raise AssertionError('Stale expected word accepted')
 return dict(raw_normalized_generic_generated_original_qualified=True,word_and_binding_corruptions=count,guard_record_corruptions=corrupt_rows,independent_stale_guard_rejections=rejected,guards=27)
def rebases():
 runs=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  syms={'D_800C3E90':0x80300000+low,'D_800D1C90':0x80400000+(low^0x8000)}
  for c in(g.Case(),g.Case(identity=255,sparse=True),g.Case(alias=2),g.Case(alias=4)):
   ms=[]
   for path in(p.out/'selected.o',p.out/'target-generic.o',p.out/'original-reference.o'):
    m=g.run(g.words(path,s=syms),c,syms,g.ENTRY+0x40000);ms.append(m);runs+=1
   a,b=ms[1:];assert(a.memory,a.r,a.f,a.trace,a.prefix)==(b.memory,b.r,b.f,b.trace,b.prefix)
 return dict(executions=runs,independent_symbol_sets=4,raw_padded_original=True)
def faults():
 programs=(g.words(p.out/'selected.o',True),struct.unpack_from('>93I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM));pairs=0
 for c in(g.Case(),g.Case(identity=255),g.Case(distance=0),g.Case(alias=2),g.Case(origin=(0x41240000,0x7F800000,0))):
  whole=g.run(programs[0],c)
  for cut in range(whole.all_accesses):
   models=[]
   for ws in programs:
    m=g.Oracle(ws,g.fixture(c),c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Guest access cut not reached')
    models.append(m)
   a,b=models;assert(a.memory,a.r,a.f,a.trace,a.current_pc,a.delay_of)==(b.memory,b.r,b.f,b.trace,b.current_pc,b.delay_of);pairs+=1
 return dict(exact_normalized_retail_access_cut_pairs=pairs,raw_instruction_fault_PC_identity_claimed=False,portable_C_fault_semantics_qualified=False)
def main():
 raw,refs=p.payload(p.out/'selected.o');normal,_=n.normalize(raw,refs);cfg=reachable(struct.unpack('>93I',normal),p.ENTRY);assert cfg['unreachable']==[53]and cfg['reachable_words']==92;result=dict(CFG=cfg,normalization_proof=n.proof(list(struct.unpack('>93I',raw))),padders=independent(),rebases=rebases(),faults=faults());(p.out/'boundaries.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True);return result
if __name__=='__main__':main()
