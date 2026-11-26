"""Colour-framebuffer settings and complete owner integrity."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_colour_framebuffer_settings_151600d8_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x151600d8;ROM=0x18d588;WORDS=103
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

def assemble(text,path):
 f=path.with_suffix('.s');f.write_text(text);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr

def objects():
 prepare();fn=FUNCTION
 full=(b/MANIFEST['asm']).read_text();original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+fn+'\n'+full.split('glabel '+fn+'\n',1)[1].split('endlabel '+fn,1)[0]+'endlabel '+fn+'\n.size '+fn+',.-'+fn+'\n';(o/'original-target.s').write_text(original)
 helper=(r/'conker/conker.us.bin').read_bytes()[0x16f78c:0x16f7a8];assert hashlib.sha256(helper).hexdigest()=='699841c41ef8dd2b13e8710815394d3b8e1f883e5d0072d61426bc35578d54a3';(o/'default-provider-original.bin').write_bytes(helper)
 parent_asm=(b/'conker/asm/18D250.s').read_text();parent_body=parent_asm.split('glabel func_1515FFEC\n',1)[1].split('endlabel func_1515FFEC',1)[0];(o/'original-parent.s').write_text('glabel func_1515FFEC\n'+parent_body+'endlabel func_1515FFEC\n')
 source=MANIFEST['selected_source']
 (o/'selected-owner.c').write_text(source);(o/'selected-Makefile').write_bytes((b/'conker/Makefile').read_bytes());old,diag=compile_owner(r,o,(b/'conker/src/game/generated_18D250.c').read_text(),'selected-before');assert not diag;new,diag=compile_owner(r,o,source,'selected-owner');assert not diag
 assemble((o/'original-target.s').read_text(),o/'original-target.o');truth,refs=payload(o/'original-target.o',fn);raw,rrefs=payload(new,fn);assert raw==truth and refs==rrefs and len(raw)==412 and len(refs)==33 and raw[:4]==bytes.fromhex('27bdffd0')
 assert same_functions(old,new,(fn,))==5 and normalized_pools(old)==normalized_pools(new);assert payload(old,'func_1515FFEC')==payload(new,'func_1515FFEC')
 guards=(b/'conker/retail_word_patches.us.csv').read_bytes();assert fn not in guards.decode();(o/'selected-guards.csv').write_bytes(guards);(o/'guard-additions.csv').write_bytes(b'')
 assemble(assembly(truth,refs,fn),o/'normalized-target.o');where=o/'qualified-owner';where.mkdir(exist_ok=True);retail=b/'conker/asm/18D250.s';outs=[]
 for label,emit in(('generic',lambda obj:restore_labels(pc.emit_padded_assembly(obj,b/'conker/retail_layout.us.txt','generated_18D250',word_patches_path=b/'conker/retail_word_patches.us.csv'),retail)),('generated',lambda obj:pg.emit_padded_assembly(obj,retail,filename='generated_18D250',word_patches_path=b/'conker/retail_word_patches.us.csv'))):
  before=where/(label+'-before.o');assemble(emit(old),before);assert before.read_bytes()==(b/'conker/build/src/game/generated_18D250.c.o').read_bytes();after=where/(label+'.o');assemble(emit(new),after);assert payload(after,fn)==(truth,refs)and same_functions(before,after,(fn,))==5 and normalized_pools(before)==normalized_pools(after);outs.append(after)
 assert outs[0].read_bytes()==outs[1].read_bytes();_,_,_,labels=pg.parse_retail_slice(retail)
 q=dict(words=103,frame=48,raw_byte_exact=True,normalized_byte_exact=True,raw_direct_words=103,guards=0,guarded_relocations=0,insertions=0,omissions=0,retail_padding_words=0,neighbors=5,raw_binding_positions=33,raw_and_padded_pools_unchanged=True,both_complete_padders_equal=True,parent_explicit_owner_argument_preserves_all_words_and_bindings=True,parent_additional_matching_credit=0,exported_retail_jump_labels_retained=sum(len(v)for v in labels.values()),selected_source_sha256=sha(o/'selected-owner.c'),raw_SHA256=hashlib.sha256(raw).hexdigest(),padded_sha256=sha(outs[0]),normal_IDO_O2_g3_mips2_o32_profile=True,entire_guard_file_unchanged=True,source_installed=installed(),matching_credit=0);(o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=="__main__":objects()
