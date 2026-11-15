"""Both complete-owner padders and four GNU links of the direct C body."""
import csv,io,json,subprocess,sys
from tools.experiments import game_quaternion_matrix_1504a140_recovery as s
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc

def main():
 root,out=s.ROOT,s.OUT;conker=root/'conker';guards=(conker/'retail_word_patches.us.csv').read_bytes();(out/'proposed-guards.csv').write_bytes(guards)
 assert guards==(out/'production-baseline/conker/retail_word_patches.us.csv').read_bytes()
 assert not [r for r in csv.DictReader(io.StringIO(guards.decode())) if r['function']==s.NAME]
 texts={'generated':pg.emit_padded_assembly(out/'recovered.o',conker/'asm/770F0.s',filename='generated_770F0',word_patches_path=out/'proposed-guards.csv'),'c':pc.emit_padded_assembly(out/'recovered.o',conker/'retail_layout.us.txt','generated_770F0',word_patches_path=out/'proposed-guards.csv')}
 fragment=(conker/'asm/770F0.s').read_text();a=fragment.index('glabel '+s.NAME+'\n');z=fragment.index('endlabel '+s.NAME,a)+len('endlabel '+s.NAME)
 texts['retail']='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment[a:z]+'\n.size '+s.NAME+',.-'+s.NAME+'\n'
 for name,text in texts.items():
  (out/(name+'-padded.s')).write_text(text)
  q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out/(name+'-padded.o')),str(out/(name+'-padded.s'))],cwd=conker,capture_output=True,text=True);assert q.returncode==0,q.stderr
  assert payload(out/(name+'-padded.o'),s.NAME)==payload(out/'recovered.o',s.NAME)
 assert same_functions(out/'generated-padded.o',out/'c-padded.o')==4
 assert normalized_pools(out/'generated-padded.o')==normalized_pools(out/'c-padded.o')
 assert same_functions(out/'production-baseline/conker/build/src/game/generated_770F0.c.o',out/'generated-padded.o',(s.NAME,))==3
 def link(obj,target,label):
  _,functions,_=pg.parse_object(obj);offset=functions[s.NAME]['value'];script,elf,binary=[out/(label+ext) for ext in ('.ld','.elf','.bin')]
  script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(target-offset))
  undefined=subprocess.check_output(['mips-linux-gnu-nm','-u',str(obj)],text=True);assert not undefined.strip(),undefined
  q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',s.NAME,'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr
  subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True)
  return binary.read_bytes()[offset:offset+s.SLOT_SIZE]
 truth=(conker/'conker.us.bin').read_bytes()[s.ROM:s.ROM+s.SLOT_SIZE]
 for i,region in enumerate((0x15000000,0x25000000,0x65000000,0x95000000)):
  for name in texts:assert link(out/(name+'-padded.o'),region+0x4a140,f'rebase-{i}-{name}')==truth
 report=dict(padders=2,full_owner=True,owner_functions=4,neighbors=3,body_words=89,alignment_words=3,layouts=4,gnu_links=12,guards=0,bindings=0,guard_manifest_unchanged=True)
 (out/'padder-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
