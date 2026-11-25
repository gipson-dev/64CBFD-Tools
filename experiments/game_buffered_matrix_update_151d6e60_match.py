"""Direct buffered matrix update and complete owner integrity."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_buffered_matrix_update_151d6e60_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x151d6e60;ROM=0x204310;WORDS=104
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
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['object']:MANIFEST['padded_sha256'],'conker/build/conker.us.elf':MANIFEST['predicted_ELF_sha256']}
 for n,d in MANIFEST['inputs'].items():
  if not _CHECKED and(OUT/'baseline'/n).is_file():assert sha(OUT/'baseline'/n)==d,('Frozen',n)
  if not _CHECKED or n in allowed:assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase',n)
 assert sha(ROOT/'conker/retail_word_patches.us.csv')==MANIFEST['guards_sha256'];_CHECKED=True;return live

def assemble(text,path):
 src=path.with_suffix('.s');src.write_text(text);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(src)],capture_output=True,text=True);assert q.returncode==0,q.stderr

def objects():
 prepare();fn=FUNCTION
 full=(b/MANIFEST['asm']).read_text();original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+fn+'\n'+full.split('glabel '+fn+'\n',1)[1].split('endlabel '+fn,1)[0]+'endlabel '+fn+'\n.size '+fn+',.-'+fn+'\n';(o/'original-target.s').write_text(original)
 source=MANIFEST['selected_source']
 (o/'selected-owner.c').write_text(source);(o/'selected-Makefile').write_bytes((b/'conker/Makefile').read_bytes());(o/'selected-guards.csv').write_bytes((b/'conker/retail_word_patches.us.csv').read_bytes())
 old,bd=compile_owner(r,o,(b/'conker/src/game/generated_203E20.c').read_text(),'selected-before');new,nd=compile_owner(r,o,source,'selected-owner');assert not bd and not nd
 assemble((o/'original-target.s').read_text(),o/'original-target.o');truth=payload(o/'original-target.o',fn);assert payload(new,fn)==truth and len(truth[0])==416;assert same_functions(old,new,(fn,))==6 and normalized_pools(old)==normalized_pools(new)
 assemble(assembly(*truth,fn),o/'normalized-target.o');retail=b/'conker/asm/203E20.s';filename='generated_203E20';where=o/'qualified-owner';where.mkdir(exist_ok=True);outs=[]
 for label,emit in [('generic',lambda f:restore_labels(pc.emit_padded_assembly(f,b/'conker/retail_layout.us.txt',filename,word_patches_path=b/'conker/retail_word_patches.us.csv'),retail)),('generated',lambda f:pg.emit_padded_assembly(f,retail,filename=filename,word_patches_path=b/'conker/retail_word_patches.us.csv'))]:
  before=where/(label+'-before.o');assemble(emit(old),before);assert before.read_bytes()==(b/'conker/build/src/game/generated_203E20.c.o').read_bytes()
  out=where/(label+'.o');assemble(emit(new),out);assert payload(out,fn)==truth and same_functions(before,out,(fn,))==6 and normalized_pools(before)==normalized_pools(out);outs.append(out)
 assert outs[0].read_bytes()==outs[1].read_bytes();_,_,_,labels=pg.parse_retail_slice(retail)
 q=dict(words=104,frame=32,raw_byte_exact=True,direct_words=104,guards=0,insertions=0,omissions=0,retail_padding_words=0,neighbors=6,raw_and_padded_pools_unchanged=True,both_complete_padders_equal=True,exported_retail_jump_labels_retained=sum(len(v)for v in labels.values()),selected_source_sha256=sha(o/'selected-owner.c'),padded_sha256=sha(outs[0]),guard_manifest_unchanged=True,normal_IDO_O2_g3_mips2_o32_profile=True,source_installed=installed(),matching_credit=0)
 (o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=="__main__":objects()
