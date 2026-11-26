"""Seed sprite growth, fall and complete owner integrity."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_seed_sprite_tick_151934b4_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x151934b4;ROM=0x1c0964;WORDS=106
r=ROOT;o=OUT;b=o/'baseline';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_local_vector_transform_15117da4_match import restore_labels,assembly as _assembly
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
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

def assemble(s,path):
 f=path.with_suffix('.s');f.write_text(s);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr

def objects():
 prepare();fn=FUNCTION
 full=(b/MANIFEST['asm']).read_text();original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+fn+'\n'+full.split('glabel '+fn+'\n',1)[1].split('endlabel '+fn,1)[0]+'endlabel '+fn+'\n.size '+fn+',.-'+fn+'\n';(o/'original-target.s').write_text(original)
 source=MANIFEST['selected_source'];(o/'selected-owner.c').write_text(source);(o/'selected-Makefile').write_bytes((b/'conker/Makefile').read_bytes());old,diag=compile_owner(r,o,(b/'conker/src/game/generated_1C0840.c').read_text(),'selected-before');assert not diag;new,diag=compile_owner(r,o,source,'selected-owner');assert not diag
 assemble((o/'original-target.s').read_text(),o/'original-target.o');truth,refs=payload(o/'original-target.o',fn);raw,rr=payload(new,fn);assert raw==truth and rr==refs and len(raw)==424 and len(refs)==5 and raw[:4]==bytes.fromhex('27bdffb8')
 assert same_functions(old,new,(fn,))==1 and normalized_pools(old)==normalized_pools(new)
 guards=(b/'conker/retail_word_patches.us.csv').read_bytes();assert fn not in guards.decode();(o/'selected-guards.csv').write_bytes(guards);(o/'guard-additions.csv').write_bytes(b'')
 assemble(assembly(truth,refs,fn),o/'normalized-target.o');where=o/'qualified-owner';where.mkdir(exist_ok=True);retail=b/'conker/asm/1C0840.s';outs=[]
 for label,emit in [('generic',lambda obj:restore_labels(pc.emit_padded_assembly(obj,b/'conker/retail_layout.us.txt','generated_1C0840',word_patches_path=b/'conker/retail_word_patches.us.csv'),retail)),('generated',lambda obj:pg.emit_padded_assembly(obj,retail,filename='generated_1C0840',word_patches_path=b/'conker/retail_word_patches.us.csv'))]:
  before=where/(label+'-before.o');assemble(emit(old),before);assert before.read_bytes()==(b/'conker/build/src/game/generated_1C0840.c.o').read_bytes();after=where/(label+'.o');assemble(emit(new),after);assert payload(after,fn)==(truth,refs)and same_functions(before,after,(fn,))==1 and normalized_pools(before)==normalized_pools(after);outs.append(after)
 assert outs[0].read_bytes()==outs[1].read_bytes();_,_,_,labels=pg.parse_retail_slice(retail)
 q=dict(words=106,retail_slot_words=107,frame=72,raw_byte_exact=True,normalized_byte_exact=True,raw_direct_words=106,guards=0,guarded_relocations=0,raw_binding_positions=5,insertions=0,omissions=0,retail_padding_words=1,neighbors=1,raw_and_padded_pools_unchanged=True,both_complete_padders_equal=True,exported_retail_jump_labels_retained=sum(len(v)for v in labels.values()),selected_source_sha256=sha(o/'selected-owner.c'),raw_SHA256=hashlib.sha256(raw).hexdigest(),padded_sha256=sha(outs[0]),normal_IDO_O2_g3_mips2_o32_profile=True,entire_guard_file_unchanged=True,source_installed=installed(),matching_credit=0);(o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=="__main__":objects()
