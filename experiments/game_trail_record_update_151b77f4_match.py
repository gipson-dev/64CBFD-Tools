"""Guarded trail record update and complete owner integrity."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_trail_record_update_151b77f4_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x151b77f4;ROM=0x1e4ca4;WORDS=105
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
 source=MANIFEST['selected_source']
 (o/'selected-owner.c').write_text(source);(o/'selected-Makefile').write_bytes((b/'conker/Makefile').read_bytes());old,diag=compile_owner(r,o,(b/'conker/src/game/generated_1E37D0.c').read_text(),'selected-before');assert not diag;new,diag=compile_owner(r,o,source,'selected-owner');assert not diag
 assemble((o/'original-target.s').read_text(),o/'original-target.o');truth,refs=payload(o/'original-target.o',fn);raw,rrefs=payload(new,fn);assert len(raw)==len(truth)==420 and refs==rrefs and raw[:4]==truth[:4]==bytes.fromhex('27bdffb8')
 differences=[at for at in range(0,420,4)if raw[at:at+4]!=truth[at:at+4]];assert differences==[0xec,0xf0,0xf4,0xf8,0x100,0x104,0x108,0x10c,0x110,0x114,0x118]
 assert same_functions(old,new,(fn,))==16 and normalized_pools(old)==normalized_pools(new)
 for callback in('func_151B7678','func_151B76CC'):assert payload(new,callback)==payload(old,callback)
 full_bytes=(b/'conker/retail_word_patches.us.csv').read_bytes();full=full_bytes.decode();assert fn not in full;reader=csv.DictReader(io.StringIO(full));fields=reader.fieldnames;rows=[]
 for at in differences:
  row=dict.fromkeys(fields,'');row.update(filename='generated_1E37D0',function=fn,offset=f'0x{at:03X}',expected=f'0x{int.from_bytes(raw[at:at+4],"big"):08X}',replacement=f'0x{int.from_bytes(truth[at:at+4],"big"):08X}',expected_relocations='-',replacement_relocations='-',note='Normalize independent post-length private loads and record-address scheduling',omit='false');rows.append(row)
 # Use the actual manifest column names rather than silently dropping fields.
 assert {'filename','function','offset','expected','replacement'}<=set(fields),fields
 buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\n');writer.writerows(rows);add=buf.getvalue().encode();nl=b'\r\n'if b'\r\n'in full_bytes[:500]else b'\n';add=add.replace(b'\n',nl);assert full_bytes.endswith(b'\n');(o/'selected-guards.csv').write_bytes(full_bytes+add);(o/'guard-additions.csv').write_bytes(add)
 assemble(assembly(truth,refs,fn),o/'normalized-target.o');where=o/'qualified-owner';where.mkdir(exist_ok=True);retail=b/'conker/asm/1E37D0.s';filename='generated_1E37D0';outs=[]
 for label,emit in(('generic',lambda obj,guards:restore_labels(pc.emit_padded_assembly(obj,b/'conker/retail_layout.us.txt',filename,word_patches_path=guards),retail)),('generated',lambda obj,guards:pg.emit_padded_assembly(obj,retail,filename=filename,word_patches_path=guards))):
  before=where/(label+'-before.o');assemble(emit(old,b/'conker/retail_word_patches.us.csv'),before);assert before.read_bytes()==(b/'conker/build/src/game/generated_1E37D0.c.o').read_bytes()
  after=where/(label+'.o');assemble(emit(new,o/'selected-guards.csv'),after);assert payload(after,fn)==(truth,refs)and same_functions(before,after,(fn,))==16 and normalized_pools(before)==normalized_pools(after);outs.append(after)
 assert outs[0].read_bytes()==outs[1].read_bytes();_,_,_,labels=pg.parse_retail_slice(retail)
 q=dict(words=105,frame=72,raw_byte_exact=False,normalized_byte_exact=True,raw_direct_words=94,guards=11,guarded_relocations=0,insertions=0,omissions=0,retail_padding_words=0,neighbors=16,both_callback_bodies_and_bindings_unchanged=True,common_callback_C_type='s32(void *,void *)',raw_and_padded_pools_unchanged=True,both_complete_padders_equal=True,exported_retail_jump_labels_retained=sum(len(v)for v in labels.values()),selected_source_sha256=sha(o/'selected-owner.c'),raw_SHA256=hashlib.sha256(raw).hexdigest(),padded_sha256=sha(outs[0]),old_guard_prefix_unchanged=True,normal_IDO_O2_g3_mips2_o32_profile=True,source_installed=installed(),matching_credit=0);(o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=="__main__":objects()
