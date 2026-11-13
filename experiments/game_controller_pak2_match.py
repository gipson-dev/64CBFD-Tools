from pathlib import Path
import hashlib,json,struct,subprocess,sys,os
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-controller-pak2-durable';out.mkdir(parents=True,exist_ok=True)
manifest=json.loads(Path(__file__).with_name('game_controller_pak2_manifest.json').read_text())
for p,h in manifest['inputs'].items():
 assert hashlib.sha256((root/p).read_bytes()).hexdigest()==h,p
states=set()
for key,record in manifest['paths'].items():
 current=(root/record['path']).read_text();actual=hashlib.sha256(current.encode()).hexdigest()
 assert actual in (record['before_sha256'],record['after_sha256']),record['path']
 assert hashlib.sha256(record['before'].encode()).hexdigest()==record['before_sha256'] and hashlib.sha256(record['after'].encode()).hexdigest()==record['after_sha256']
 states.add(actual==record['after_sha256'])
assert len(states)==1
installed=states.pop()
targets={'read':(('__osContRamRead2',0x21f530,580),('__osPackRamReadData2',0x21f774,360)),'write':(('__osContRamWrite2',0x21f8e0,560),('__osPackRamWriteData2',0x21fb10,380))}
(out/'proposed.Makefile').write_text(manifest['paths']['make']['after']);(out/'proposed-guards.csv').write_bytes((root/'conker/retail_word_patches.us.csv').read_bytes())
def assemble(text,label):
 asm=out/(label+'.s');obj=asm.with_suffix('.o');asm.write_text(text)
 p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj.relative_to(root/'conker')),str(asm.relative_to(root/'conker'))],cwd=root/'conker',capture_output=True,text=True);assert p.returncode==0,p.stderr
 return obj
addresses={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};rom=(root/'conker/conker.us.bin').read_bytes();report={}
for kind,specs in targets.items():
 owner='generated_contram'+kind+'2';before=manifest['paths'][kind]['before'];source=manifest['paths'][kind]['after']
 (out/(owner+'-selected.c')).write_text(source)
 old,bd=compile_owner(root,out,before,owner+'-before');obj,diag=compile_owner(root,out,source,owner+'-after',flags=('-O1',));assert not diag and normalized_pools(old)==normalized_pools(obj)
 asm=(root/('conker/asm/libultra/io/contram'+kind+'2.s')).read_text()
 objects=[]
 for label,text in (('generated',pg.emit_padded_assembly(obj,root/('conker/asm/libultra/io/contram'+kind+'2.s'),filename=owner,word_patches_path=out/'proposed-guards.csv')),('generic',pc.emit_padded_assembly(obj,root/'conker/retail_layout.us.txt',owner,word_patches_path=out/'proposed-guards.csv'))):objects.append(assemble(text,owner+'-'+label))
 for name,offset,size in specs:
  a=asm.index('glabel '+name);b=asm.index('endlabel '+name,a)+len('endlabel '+name);retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[a:b]+'\n.size '+name+',.-'+name+'\n',name+'-retail')
  expected=rom[offset:offset+size]
  for p in (retail,obj,*objects):
   raw,refs=payload(p,name);assert len(raw)==size,(name,p,len(raw),size)
   words=bound_blob(raw,refs,{sym:addresses[sym] for group in refs.values() for _,sym in group});assert struct.pack('>%dI'%(size//4),*words)==expected,(name,p)
  report[name]={'words':size//4,'sha256':hashlib.sha256(expected).hexdigest(),'zero_guards':True}
print(json.dumps(report,indent=2),flush=True);(out/'preparation.json').write_text(json.dumps(report,indent=2)+'\n')
