"""Both full-owner padders, independent data/code rebases and exact guards."""
import json,struct,subprocess,sys
from tools.experiments import game_view_reset_15017640_match as s
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_view_reset_15017640_prefix_proof import certify
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc

def main():
 root,out=s.ROOT,s.OUT;conker=root/'conker';rom=(conker/'conker.us.bin').read_bytes()
 # The non-generated owner has no flat assembly file. Independently reconstruct
 # its complete layout fixture from both original ROM slots, then verify that
 # parse_retail_slice agrees with the production CSV layout.
 fixture='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'
 for name,start,end in (('func_150175E0',0x150175e0,0x15017640),(s.NAME,s.ENTRY,0x15017790)):
  fixture+='glabel '+name+'\n'
  for pc0 in range(start,end,4):
   at=pc0-0x15000000+0x2d4b0;w=struct.unpack_from('>I',rom,at)[0]
   fixture+='/* %X %08X %08X */ .word 0x%08X\n'%(at,pc0,w,w)
  fixture+='endlabel '+name+'\n'
 path=out/'retail-owner-layout.s';path.write_text(fixture)
 a,z,functions,_=pg.parse_retail_slice(path);assert(a,z,functions)==(0x150175e0,0x15017790,{'func_150175E0':0x150175e0,s.NAME:s.ENTRY})
 texts={'generated':pg.emit_padded_assembly(out/'qualified.o',path,filename=s.OWNER,word_patches_path=out/'proposed-guards.csv'),'c':pc.emit_padded_assembly(out/'qualified.o',conker/'retail_layout.us.txt',s.OWNER,word_patches_path=out/'proposed-guards.csv')}
 for name,text in texts.items():
  (out/(name+'-padded.s')).write_text(text)
  q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(out/(name+'-padded.o')),str(out/(name+'-padded.s'))],cwd=conker,capture_output=True,text=True);assert q.returncode==0,q.stderr
  assert same_functions(out/'guarded.o',out/(name+'-padded.o'))==2 and normalized_pools(out/'guarded.o')==normalized_pools(out/(name+'-padded.o'))
 symbols=s.draft.symbols(root)
 def link(obj,cd,dd,label):
  _,functions,_=pg.parse_object(obj);offset=functions[s.NAME]['value'];script,elf,binary=[out/(label+suffix) for suffix in ('.ld','.elf','.bin')]
  script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(s.ENTRY+cd-offset))
  undefined=subprocess.check_output(['mips-linux-gnu-nm','-u',str(obj)],text=True).splitlines();defs={}
  for row in undefined:
   name=row.split()[-1];v=int(name.split('_')[1],16) if name.startswith(('func_','D_')) else symbols[name];defs[name]=(v+(cd if name.startswith('func_') or name in s.SDK else dd))&0xffffffff
  q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',s.NAME,*['--defsym=%s=0x%X'%x for x in defs.items()],'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr
  subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True)
  return binary.read_bytes()[offset:offset+s.SLOT_SIZE]
 raw,refs=payload(out/'qualified.o',s.NAME);normal,nrefs=s.normalize(raw,refs)
 for i,(cd,dd) in enumerate(((0,0),(0x10000000,0x12348000),(0x50000000,0x23457ffc),(0x80000000,0x34568000))):
  retail=link(out/'retail.o',cd,dd,f'rebase-{i}-retail')
  if not i:assert retail==rom[s.ROM:s.ROM+s.SLOT_SIZE]
  for label in texts:assert link(out/(label+'-padded.o'),cd,dd,f'rebase-{i}-{label}')==retail
  rebased={name:(value+(cd if name in s.SDK or name.startswith('func_') else dd))&0xffffffff for name,value in symbols.items()}
  certify(bound_blob(normal,nrefs,rebased),bound_blob(raw,refs,rebased),(0x800d2438+dd)&0xffffffff,(0x100226f0+cd)&0xffffffff,s.ENTRY+cd)
 report=dict(padders=2,full_owner=True,owner_functions=2,body_words=82,alignment_words=2,layouts=4,gnu_links=12,proof_layouts=4,aliases_keep_original_storage_layout=True)
 (out/'padder-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
