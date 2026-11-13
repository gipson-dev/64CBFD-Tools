"""Recreate the script-query list callback match and its historical baseline."""
import csv,hashlib,inspect,io,json,os,shutil,struct,subprocess,sys
from pathlib import Path
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments import game_remaining_donor_candidates as donor
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-query-list-1509dbbc-screen'
MANIFEST=json.loads(Path(__file__).with_name('game_query_list_1509dbbc_manifest.json').read_text())
sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
FIXTURES=('guest','connected','faults','native','rebase')
def apply(text,changes,reverse=False):
 lines=text.splitlines(keepends=True)
 for item in reversed(changes):
  old,new=('new','old') if reverse else ('old','new');at=item['new_at' if reverse else 'old_at'];before=item[old].splitlines(keepends=True)
  if lines[at:at+len(before)]!=before:raise ValueError('patch context changed')
  lines[at:at+len(before)]=item[new].splitlines(keepends=True)
 return ''.join(lines)
def history(text,prefix):
 before,after=MANIFEST[prefix+'_before_sha256'],MANIFEST[prefix+'_after_sha256']
 if sha(text)==before:return text
 if sha(text)!=after:raise ValueError(prefix+' fingerprint changed')
 result=apply(text,MANIFEST['guard_changes' if prefix=='guards' else prefix+'_changes'],True)
 if sha(result)!=before:raise ValueError(prefix+' historical reconstruction failed')
 return result
def historical_source(text):return history(text,'source')
def historical_guards(text):return history(text,'guards')
def assemble(text,label):
 src=OUT/(label+'.s');obj=OUT/(label+'.o');src.write_text(text)
 r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=ROOT/'conker',capture_output=True,text=True)
 if r.returncode:raise ValueError(r.stderr)
 return obj
def prepare():
 OUT.mkdir(parents=True,exist_ok=True);rom=(ROOT/'conker/conker.us.bin').read_bytes()
 if hashlib.sha256(rom).hexdigest()!=MANIFEST['rom_sha256'] or hashlib.sha256((ROOT/'conker/retail_layout.us.txt').read_bytes()).hexdigest()!=MANIFEST['layout_sha256']:raise ValueError('retail image or layout changed')
 source=historical_source((ROOT/MANIFEST['source_path']).read_text());selected=apply(source,MANIFEST['source_changes']);assert sha(selected)==MANIFEST['source_after_sha256']
 oldguards=historical_guards((ROOT/'conker/retail_word_patches.us.csv').read_text());newguards=apply(oldguards,MANIFEST['guard_changes']);assert sha(newguards)==MANIFEST['guards_after_sha256'];guard=OUT/'private-guards.csv';guard.write_text(newguards)
 code=inspect.getsource(donor.compile_owner);old="str(root / 'tools/asm-processor/asm_processor.py'), *flags,";new="str(root / 'tools/asm-processor/asm_processor.py'), *flags[:2],";assert old in code;scope=dict(donor.compile_owner.__globals__);exec(code.replace(old,new),scope);compile_profile=scope['compile_owner'];flags=('-O2','-g3','-Wo,-loopunroll,0')
 before,bd=compile_profile(ROOT,OUT,source,'before',flags);after,ad=compile_profile(ROOT,OUT,selected,'selected2',flags);same_functions(before,after,('func_1509DBBC',))
 if normalized_pools(before)!=normalized_pools(after) or diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('owner pools or diagnostics changed')
 shutil.copyfile(after,OUT/'typedshape06.o')
 name='func_1509DBBC';assembly=(ROOT/'conker/asm/C9EC0.s').read_text();a=assembly.index('glabel '+name);b=assembly.index('endlabel '+name,a)+len('endlabel '+name)
 retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+assembly[a:b]+'\n.size '+name+',.-'+name+'\n','retail')
 gen=assemble(pg.emit_padded_assembly(after,ROOT/'conker/asm/C9EC0.s',filename='generated_C9EC0',word_patches_path=guard,rodata_symbol='jtbl_8009F1AC_game'),'generated')
 generic=assemble(pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt','generated_C9EC0',word_patches_path=guard,rodata_symbol='jtbl_8009F1AC_game'),'generic')
 if payload(gen,name)!=payload(retail,name) or payload(generic,name)!=payload(retail,name):raise ValueError('retail body or relocations differ')
 data,refs=payload(retail,name);lookup={v[1]:v[2][1] for v in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())};words=bound_blob(data,refs,{n:lookup[n] for rows in refs.values() for _,n in rows})
 if struct.pack('>84I',*words)!=rom[0xcb06c:0xcb06c+336]:raise ValueError('assembled code differs from retail image')
 for name in FIXTURES:shutil.copyfile(Path(__file__).resolve().parents[1]/'tests'/('game_query_list_1509dbbc_'+name+'.py'),OUT/(name+'.py'))
 print('owner, 18 neighbors and both object padders qualified')
 return source,selected
