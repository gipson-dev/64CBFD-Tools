"""Qualify the retail effect factory wrapper's previously discarded C return."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import parse_object
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-effect-factory-return-151303bc-match'
MANIFEST=json.loads(Path(__file__).with_name('game_effect_factory_return_151303bc_manifest.json').read_text())
NAME=MANIFEST['name'];sha=lambda b:hashlib.sha256(b).hexdigest()
def payload(path):
 t,fs,refs=parse_object(path);f=fs[NAME];a=f['value'];return t[a:a+f['size']],{i-a:v for i,v in refs.items()if a<=i<a+f['size']}
def assemble(text,label):
 src=OUT/(label+'.s');obj=src.with_suffix('.o');src.write_text(text)
 r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=ROOT/'conker',capture_output=True,text=True)
 if r.returncode:raise ValueError(r.stderr)
 return obj
def prepare():
 OUT.mkdir(parents=True,exist_ok=True)
 if sha((ROOT/'conker/conker.us.bin').read_bytes())!=MANIFEST['rom_sha256']:raise ValueError('Retail input changed')
 live=(ROOT/MANIFEST['source']).read_bytes();old=MANIFEST['old_source'].encode();new=MANIFEST['selected_source'].encode()
 if sha(old)!=MANIFEST['source_sha256'] or live not in (old,new):raise ValueError('Unknown owner source')
 before,bd=compile_owner(ROOT,OUT,old.decode(),'before');after,ad=compile_owner(ROOT,OUT,new.decode(),'after')
 if same_functions(before,after)!=31 or normalized_pools(before)!=normalized_pools(after):raise ValueError('Owner functions or pools changed')
 if diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Diagnostics changed')
 old_sections=sections(before);new_sections=sections(after)
 changed={k for k in old_sections.keys()|new_sections.keys() if old_sections.get(k)!=new_sections.get(k)}
 if changed!={'.mdebug'}:raise ValueError(('Unexpected sections changed',changed))
 asm=(ROOT/MANIFEST['assembly']).read_text();start='glabel '+NAME+'\n';end='endlabel '+NAME;frag=start+asm.split(start,1)[1].split(end,1)[0]+end
 retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+frag+'\n.size '+NAME+',.-'+NAME+'\n','retail')
 if payload(after)!=payload(before) or payload(after)!=payload(retail) or len(payload(retail)[0])!=48:raise ValueError('Factory wrapper changed')
 one=assemble(pg.emit_padded_assembly(after,ROOT/MANIFEST['assembly'],filename=MANIFEST['owner'],word_patches_path=ROOT/'conker/retail_word_patches.us.csv'),'generated')
 two=assemble(pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',MANIFEST['owner'],word_patches_path=ROOT/'conker/retail_word_patches.us.csv'),'generic')
 if payload(one)!=payload(retail) or payload(two)!=payload(retail):raise ValueError('Padded wrapper differs')
 return dict(before=before,after=after,retail=retail,generated=one,generic=two,installed=live==new)
