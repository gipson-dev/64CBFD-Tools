"""Complete-owner padders, original bindings and independent GNU rebases."""
import csv,io,json,struct,subprocess,sys
from tools.experiments import game_radial_effect_150c29f0_match as s
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc

def main():
 root,out=s.ROOT,s.OUT;conker=root/'conker';guards=(conker/'retail_word_patches.us.csv').read_bytes()
 old=(out/'production-baseline/conker/retail_word_patches.us.csv').read_bytes();new=(out/'proposed-guards.csv').read_bytes()
 assert guards in (old,new) and new.startswith(old)
 rows_old=list(csv.DictReader(io.StringIO(old.decode())));rows_new=list(csv.DictReader(io.StringIO(new.decode())))
 assert rows_new[:len(rows_old)]==rows_old and len(rows_new)==len(rows_old)+11
 assert {r['function'] for r in rows_new[len(rows_old):]}=={s.NAME}
 rows=[r for r in csv.DictReader(io.StringIO((conker/'retail_layout.us.txt').read_text())) if r['filename']=='game_EF410']
 original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'
 rom=(conker/'conker.us.bin').read_bytes()
 for row in rows:
  path=conker/'asm/nonmatchings/game_EF410'/(row['function']+'.s')
  if path.exists():original+=path.read_text()+'\n'
  else:
   original+='glabel '+row['function']+'\n'
   for at in range(int(row['address'],16),int(row['end'],16),4):
    off=at-0x15000000+0x2d4b0;word=struct.unpack_from('>I',rom,off)[0]
    original+='/* %X %08X %08X */ .word 0x%08X\n'%(off,at,word,word)
 whole=out/'original-owner.s';whole.write_text(original)
 target=(conker/'asm/nonmatchings/game_EF410'/f'{s.NAME}.s').read_text()
 texts=dict(generated=pg.emit_padded_assembly(out/'recovered.o',whole,filename='game_EF410',word_patches_path=out/'proposed-guards.csv'),c=pc.emit_padded_assembly(out/'recovered.o',conker/'retail_layout.us.txt','game_EF410',word_patches_path=out/'proposed-guards.csv'),retail='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+target+'\n.size '+s.NAME+',.-'+s.NAME+'\n')
 for name,text in texts.items():
  (out/(name+'-padded.s')).write_text(text)
  q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out/(name+'-padded.o')),str(out/(name+'-padded.s'))],cwd=conker,capture_output=True,text=True)
  assert q.returncode==0,q.stderr
  assert payload(out/(name+'-padded.o'),s.NAME)==s.normalize(*payload(out/'recovered.o',s.NAME))
 assert same_functions(out/'generated-padded.o',out/'c-padded.o')==18
 assert normalized_pools(out/'generated-padded.o')==normalized_pools(out/'c-padded.o')
 assert same_functions(out/'production-baseline/conker/build/src/game_EF410.c.o',out/'c-padded.o',(s.NAME,))==17
 lookup={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())}
 def link(obj,region,label):
  _,functions,_=pg.parse_object(obj);offset=functions[s.NAME]['value'];script,elf,binary=[out/(label+ext) for ext in ('.ld','.elf','.bin')]
  target=region+(s.ENTRY-0x15000000);script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(target-offset))
  undefined=subprocess.check_output(['mips-linux-gnu-nm','-u',str(obj)],text=True)
  symbols={name:lookup[name] for line in undefined.splitlines() if (name:=line.split()[-1])}
  symbols={n:(region+v-0x15000000 if 0x15000000<=v<0x15200000 else v) for n,v in symbols.items()}
  data_base=(0x800a02a0,0x800a7ff0,0x800a8000,0x800afff0)[(0x15000000,0x25000000,0x65000000,0x95000000).index(region)]
  for i in range(8):
   n='D_%08X'%(0x800a02a0+4*i)
   if n in symbols:symbols[n]=data_base+4*i
  q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',s.NAME,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(obj)],capture_output=True,text=True)
  assert q.returncode==0,q.stderr
  subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True)
  return binary.read_bytes()[offset:offset+s.SIZE]
 for i,region in enumerate((0x15000000,0x25000000,0x65000000,0x95000000)):
  outputs=[link(out/(name+'-padded.o'),region,f'rebase-{i}-{name}') for name in texts]
  assert len(outputs[0])==s.SIZE and outputs[0]==outputs[1]==outputs[2]
  if i==0:assert outputs[0]==(conker/'conker.us.bin').read_bytes()[s.ROM:s.ROM+s.SIZE]
 rejected=0
 for row_index in range(len(rows_old),len(rows_new)):
  corrupt=[dict(r) for r in rows_new];corrupt[row_index]['expected']='0x%08X'%(int(corrupt[row_index]['expected'],16)^1);stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(rows_new[0]),lineterminator='\n');writer.writeheader();writer.writerows(corrupt);bad=out/'corrupt-guard.csv';bad.write_text(stream.getvalue())
  for emitter in (lambda:pg.emit_padded_assembly(out/'recovered.o',whole,filename='game_EF410',word_patches_path=bad),lambda:pc.emit_padded_assembly(out/'recovered.o',conker/'retail_layout.us.txt','game_EF410',word_patches_path=bad)):
   try:emitter()
   except ValueError:rejected+=1
   else:raise AssertionError('Changed expected-word guard accepted')
 assert rejected==22
 report=dict(padders=2,full_owner=True,owner_functions=18,neighbors=17,body_words=132,alignment_words=0,layouts=4,gnu_links=12,guards=11,guard_manifest_append_only=True,corrupted_guards_rejected=rejected)
 (out/'padder-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
