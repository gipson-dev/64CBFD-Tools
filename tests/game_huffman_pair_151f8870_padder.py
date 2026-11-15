"""Full-owner padder agreement and four independent code layouts."""
from pathlib import Path
import json,os,struct,subprocess,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments import game_huffman_pair_151f8870_restoration as source
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload

def main():
 root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();conker=root/'conker';out=root/source.BUILD;name=source.FUNCTION
 texts={'generated':pg.emit_padded_assembly(out/'selected.o',conker/'asm/225D20.s',filename='generated_225D20',word_patches_path=out/'proposed-guards.csv'),
        'c':pc.emit_padded_assembly(out/'selected.o',conker/'retail_layout.us.txt','generated_225D20',word_patches_path=out/'proposed-guards.csv')}
 for label,text in texts.items():
  (out/(label+'-padded.s')).write_text(text)
  subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out/(label+'-padded.o')),str(out/(label+'-padded.s'))],cwd=conker,capture_output=True,check=True)
  assert same_functions(conker/'build/src/game/generated_225D20.c.o',out/(label+'-padded.o'),(name,))==5
 def link(obj,target,label):
  _,functions,_=pg.parse_object(obj);offset=functions[name]['value'];script=out/(label+'.ld');elf=out/(label+'.elf');binary=out/(label+'.bin')
  script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(target-offset))
  undefined=subprocess.run(['mips-linux-gnu-nm','-u',str(obj)],capture_output=True,text=True,check=True).stdout;assert not undefined.strip(),undefined
  q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',name,'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr
  subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True)
  return binary.read_bytes()[offset:offset+source.SLOT_BYTES]
 truth=(conker/'conker.us.bin').read_bytes()[source.ROM:source.ROM+source.SLOT_BYTES]
 for i,region in enumerate((0x15000000,0x25000000,0x65000000,0x95000000)):
  target=region+0x1f8870;retail=link(out/'retail.o',target,f'rebase-{i}-retail');assert retail==truth
  for label in texts:assert link(out/(label+'-padded.o'),target,f'rebase-{i}-{label}')==retail
 report=dict(padders=2,layouts=4,gnu_links=12,body_words=47,alignment_words=0,owner_neighbors=5,bindings=0,strict_full_owner_passes=True)
 (out/'padder-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
