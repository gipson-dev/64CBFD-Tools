"""Trail fade tick and complete owner integrity."""
from pathlib import Path
import csv,hashlib,io,itertools,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_trail_fade_tick_151b6420_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x151b6420;ROM=0x1e38d0;WORDS=109
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

def remap(w,p):
 op=w>>26
 if op in (49,57):return (w&~(31<<16))|(p.get(w>>16&31,w>>16&31)<<16)
 if op==17:
  fmt=w>>21&31
  if fmt in (0,4):return(w&~(31<<11))|(p.get(w>>11&31,w>>11&31)<<11)
  if fmt==16:
   fields=[11]
   if w&63 in(0,1,2,3,50,60,62):fields.append(16)
   if w&63<48:fields.append(6)
   for shift in fields:w=(w&~(31<<shift))|(p.get(w>>shift&31,w>>shift&31)<<shift)
 return w

def objects():
 prepare();fn=FUNCTION
 full=(b/MANIFEST['asm']).read_text();original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+fn+'\n'+full.split('glabel '+fn+'\n',1)[1].split('endlabel '+fn,1)[0]+'endlabel '+fn+'\n.size '+fn+',.-'+fn+'\n';(o/'original-target.s').write_text(original)
 source=MANIFEST['selected_source'];(o/'selected-owner.c').write_text(source);(o/'selected-Makefile').write_bytes((b/'conker/Makefile').read_bytes())
 old,diag=compile_owner(r,o,(b/'conker/src/game/generated_1E37D0.c').read_text(),'selected-before');assert not diag;new,diag=compile_owner(r,o,source,'selected-owner');assert not diag
 assemble((o/'original-target.s').read_text(),o/'original-target.o');truth,refs=payload(o/'original-target.o',fn);raw,rr=payload(new,fn);assert len(raw)==len(truth)==436 and rr==refs and len(refs)==4
 words=lambda d:[int.from_bytes(d[i:i+4],'big')for i in range(0,len(d),4)];a,z=words(raw),words(truth);solutions=[]
 for v in itertools.permutations((2,4,6,14,18)):
  p=dict(zip((2,4,6,14,18),v))
  if[remap(w,p)if 0xe4<=4*i<=0x120 else w for i,w in enumerate(a)]==z:solutions.append(p)
 assert len(solutions)==1,solutions;p=solutions[0];diff=[i*4 for i,(x,y)in enumerate(zip(a,z))if x!=y];assert diff==[0xf0,0x114,0x118,0x11c,0x120]
 assert same_functions(old,new,(fn,))==16 and normalized_pools(old)==normalized_pools(new)
 full=(b/'conker/retail_word_patches.us.csv').read_bytes();assert fn not in full.decode();reader=csv.DictReader(io.StringIO(full.decode()));fields=reader.fieldnames;rows=[]
 for at in diff:
  row=dict.fromkeys(fields,'');rel='R_MIPS_LO16:D_800AA470'if at==0xf0 else'-';row.update(filename='generated_1E37D0',function=fn,offset=f'0x{at:03X}',expected=f'0x{a[at//4]:08X}',replacement=f'0x{z[at//4]:08X}',expected_relocations=rel,replacement_relocations=rel,note='Normalize closed volatile floating-register allocation in trail fade calculation',omit='false');rows.append(row)
 buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\n');writer.writerows(rows);add=buf.getvalue().encode();add=add.replace(b'\n',b'\r\n')if b'\r\n'in full[:500]else add;(o/'guard-additions.csv').write_bytes(add);(o/'selected-guards.csv').write_bytes(full+add)
 assemble(assembly(truth,refs,fn),o/'normalized-target.o');where=o/'qualified-owner';where.mkdir(exist_ok=True);retail=b/'conker/asm/1E37D0.s';outs=[]
 for label,emit in [('generic',lambda obj,guards:restore_labels(pc.emit_padded_assembly(obj,b/'conker/retail_layout.us.txt','generated_1E37D0',word_patches_path=guards),retail)),('generated',lambda obj,guards:pg.emit_padded_assembly(obj,retail,filename='generated_1E37D0',word_patches_path=guards))]:
  before=where/(label+'-before.o');assemble(emit(old,b/'conker/retail_word_patches.us.csv'),before);assert before.read_bytes()==(b/'conker/build/src/game/generated_1E37D0.c.o').read_bytes();after=where/(label+'.o');assemble(emit(new,o/'selected-guards.csv'),after);assert payload(after,fn)==(truth,refs)and same_functions(before,after,(fn,))==16 and normalized_pools(before)==normalized_pools(after);outs.append(after)
 assert outs[0].read_bytes()==outs[1].read_bytes();_,_,_,labels=pg.parse_retail_slice(retail)
 q=dict(words=109,frame=0,raw_byte_exact=False,normalized_byte_exact=True,raw_direct_words=104,guards=5,guarded_relocations=1,raw_binding_positions=4,insertions=0,omissions=0,retail_padding_words=0,neighbors=16,raw_and_padded_pools_unchanged=True,both_complete_padders_equal=True,exported_retail_jump_labels_retained=sum(len(v)for v in labels.values()),FP_permutation_raw_to_retail=p,permutation_region=[0xe4,0x120],permutation_proves_every_word_and_relocation=True,raw_dead_volatile_FP_literal_identity_not_claimed=True,selected_source_sha256=sha(o/'selected-owner.c'),raw_SHA256=hashlib.sha256(raw).hexdigest(),padded_sha256=sha(outs[0]),normal_IDO_O2_g3_mips2_o32_profile=True,old_guard_prefix_unchanged=True,source_installed=installed(),matching_credit=0)
 (o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=="__main__":objects()
