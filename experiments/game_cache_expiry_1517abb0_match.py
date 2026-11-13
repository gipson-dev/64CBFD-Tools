"""Qualify the cache-expiry candidate against retail and owner objects."""
import csv,hashlib,io,json,os,struct,subprocess,sys
from pathlib import Path
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-cache-expiry-1517abb0-durable'
MANIFEST=json.loads(Path(__file__).with_name('game_cache_expiry_1517abb0_manifest.json').read_text())
NAME,OWNER='func_1517ABB0','generated_1A8060'
sha=lambda text:hashlib.sha256(text.encode()).hexdigest()

def apply(text,changes,reverse=False):
 lines=text.splitlines(keepends=True)
 for item in reversed(changes):
  old,new=('new','old') if reverse else ('old','new');at=item['new_at' if reverse else 'old_at'];expected=item[old].splitlines(keepends=True)
  if lines[at:at+len(expected)]!=expected:raise ValueError('Cache expiry candidate context changed')
  lines[at:at+len(expected)]=item[new].splitlines(keepends=True)
 return ''.join(lines)

def sources():
 result,states={},set()
 for name,spec in MANIFEST['paths'].items():
  current=(ROOT/spec['path']).read_text()
  if sha(current)==spec['before_sha256']:before,installed=current,False
  elif sha(current)==spec['after_sha256']:before,installed=apply(current,spec['changes'],True),True
  else:raise ValueError('Unknown cache expiry input: '+spec['path'])
  after=apply(before,spec['changes'])
  if sha(before)!=spec['before_sha256'] or sha(after)!=spec['after_sha256']:raise ValueError('Cache expiry reconstruction failed')
  result[name]=(before,after);states.add(installed)
 if len(states)!=1:raise ValueError('Partial cache expiry installation')
 return result,states.pop()

def assemble(text,label):
 asm=OUT/(label+'.s');obj=asm.with_suffix('.o');asm.write_text(text)
 result=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(asm)],cwd=ROOT/'conker',capture_output=True,text=True)
 if result.returncode:raise ValueError(result.stderr)
 return obj

def prepare():
 OUT.mkdir(parents=True,exist_ok=True)
 for key,path in (('rom','conker/conker.us.bin'),('layout','conker/retail_layout.us.txt'),('assembly','conker/asm/1A8060.s')):
  if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=MANIFEST[key+'_sha256']:raise ValueError('Cache expiry input changed: '+path)
 texts,installed=sources();before,bd=compile_owner(ROOT,OUT,texts['source'][0],'before');after,ad=compile_owner(ROOT,OUT,texts['source'][1],'variant-split')
 if same_functions(before,after,(NAME,))!=1 or normalized_pools(before)!=normalized_pools(after) or diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Cache expiry neighbor, pools or diagnostics changed')
 asm=(ROOT/'conker/asm/1A8060.s').read_text();start=asm.index('glabel '+NAME);end=asm.index('endlabel '+NAME,start)+len('endlabel '+NAME)
 retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[start:end]+'\n.size '+NAME+',.-'+NAME+'\n','retail')
 raw,refs=payload(after,NAME);truth,truth_refs=payload(retail,NAME)
 if len(raw)!=336 or len(truth)!=336 or refs!=truth_refs:raise ValueError('Cache expiry extent or bindings changed')
 guards=OUT/'proposed-guards.csv';guards.write_text(texts['guards'][1]);rows=[r for r in csv.DictReader(io.StringIO(texts['guards'][1])) if r['function']==NAME]
 if rows!=MANIFEST['guard_rows'] or len(rows)!=16:raise ValueError('Cache expiry guard rows changed')
 objects=[]
 for label,emitted in (('padded',pg.emit_padded_assembly(after,ROOT/'conker/asm/1A8060.s',filename=OWNER,word_patches_path=guards)),('generic',pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',OWNER,word_patches_path=guards))):
  obj=assemble(emitted,label)
  if payload(obj,NAME)!=(truth,truth_refs) or same_functions(ROOT/'conker/build/src/game/generated_1A8060.c.o',obj,(NAME,))!=1:raise ValueError('Cache expiry padded body or neighbor changed')
  objects.append(obj)
 addresses={row[1]:row[2][1] for row in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())}
 words=bound_blob(truth,truth_refs,{s:addresses[s] for v in truth_refs.values() for _,s in v})
 if struct.pack('>84I',*words)!=(ROOT/'conker/conker.us.bin').read_bytes()[0x1A8060:0x1A81B0]:raise ValueError('Cache expiry retail ROM changed')
 link_owner(ROOT,OUT,after,OWNER)
 print('Cache expiry: 84 retail words, 16 guards, one unchanged neighbor',flush=True)
 return texts,installed

if __name__=='__main__':prepare()
