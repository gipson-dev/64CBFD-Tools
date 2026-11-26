"""Direct random sprite scatter, palette snapshot and exact original frame."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_random_sprite_scatter_15179b14_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x15179b14;ROM=0x1A6FC4;WORDS=103
r=ROOT;o=OUT;b=o/'baseline';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_local_vector_transform_15117da4_match import restore_labels,assembly as _assembly
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_actor_transform_position_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
def assembly(data,refs,name=FUNCTION):return _assembly(data,refs,name)
def installed():return sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
_CHECKED=False
def prepare():
 global _CHECKED
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['object']:MANIFEST['padded_sha256'],'conker/build/conker.us.elf':MANIFEST['predicted_ELF_sha256'],'conker/retail_word_patches.us.csv':MANIFEST['guards_sha256']}
 for n,d in MANIFEST['inputs'].items():
  if not _CHECKED and(OUT/'baseline'/n).is_file():assert sha(OUT/'baseline'/n)==d,('Frozen',n)
  if not _CHECKED or n in allowed:assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase',n)
 assert sha(ROOT/'conker/retail_word_patches.us.csv')==(MANIFEST['guards_sha256'] if live else MANIFEST['inputs']['conker/retail_word_patches.us.csv']);_CHECKED=True;return live

def assemble(text,path):
 f=path.with_suffix('.s');f.write_text(text);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr

def warning_signature(text):
 assert not text,text;return []

def objects():
 prepare();fn=FUNCTION
 full=(b/MANIFEST['asm']).read_text();original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+fn+'\n'+full.split('glabel '+fn+'\n',1)[1].split('endlabel '+fn,1)[0]+'endlabel '+fn+'\n.size '+fn+',.-'+fn+'\n';(o/'original-target.s').write_text(original)
 source=MANIFEST['selected_source'];(o/'selected-owner.c').write_text(source);(o/'selected-Makefile').write_bytes((b/'conker/Makefile').read_bytes());old,diag=compile_owner(r,o,(b/'conker/src/game/generated_1A6360.c').read_text(),'selected-before');warnings=warning_signature(diag);new,diag=compile_owner(r,o,source,'selected-owner');assert warning_signature(diag)==warnings
 assemble((o/'original-target.s').read_text(),o/'original-target.o');truth,tr=payload(o/'original-target.o',fn);raw,refs=payload(new,fn);assert(raw,refs)==(truth,tr)and len(raw)==412 and len(refs)==9 and int.from_bytes(raw[:4],'big')==0x27BDFEF0;assert same_functions(old,new,(fn,))==8 and normalized_pools(old)==normalized_pools(new)
 symbols={name:int(name.split('_',1)[1],16)for entries in refs.values()for kind,name in entries};assert struct.pack('>103I',*bound_blob(raw,refs,symbols))==(r/'conker/conker.us.bin').read_bytes()[0x1A6FC4:0x1A7160]
 guards=(b/'conker/retail_word_patches.us.csv').read_bytes();assert fn not in guards.decode();(o/'guard-additions.csv').write_bytes(b'');(o/'selected-guards.csv').write_bytes(guards);assemble(assembly(truth,tr,fn),o/'normalized-target.o')
 retail=b/'conker/asm/1A6360.s';parsed=pg.parse_retail_slice(retail);assert len(parsed[2])==9
 where=o/'qualified-owner';where.mkdir(exist_ok=True);outs=[]
 for label,emit in [('generic',lambda obj:restore_labels(pc.emit_padded_assembly(obj,b/'conker/retail_layout.us.txt','generated_1A6360',word_patches_path=o/'selected-guards.csv'),retail)),('generated',lambda obj:pg.emit_padded_assembly(obj,retail,filename='generated_1A6360',word_patches_path=o/'selected-guards.csv'))]:
  before=where/(label+'-before.o');assemble(emit(old),before);assert before.read_bytes()==(b/'conker/build/src/game/generated_1A6360.c.o').read_bytes();after=where/(label+'.o');assemble(emit(new),after);assert payload(after,fn)==(truth,tr)and same_functions(before,after,(fn,))==8 and normalized_pools(before)==normalized_pools(after);outs.append(after)
 assert outs[0].read_bytes()==outs[1].read_bytes();q=dict(words=103,retail_slot_words=103,frame=272,raw_byte_exact=True,normalized_byte_exact=True,raw_direct_words=103,guards=0,raw_binding_positions=9,insertions=0,omissions=0,retail_padding_words=0,neighbors=8,raw_and_padded_pools_unchanged=True,both_complete_padders_equal=True,exported_retail_jump_labels_retained=sum(len(v)for v in parsed[3].values()),complete_owner_layout_functions=9,selected_source_sha256=sha(o/'selected-owner.c'),raw_SHA256=hashlib.sha256(raw).hexdigest(),padded_sha256=sha(outs[0]),normal_IDO_O2_g3_mips2_o32_profile=True,unchanged_existing_diagnostics=warnings,new_compiler_diagnostics=0,whole_guard_CSV_unchanged=True,captured_signed_origins_promoted_to_s32_working_values=True,source_installed=installed(),matching_credit=0);(o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=="__main__":objects()
