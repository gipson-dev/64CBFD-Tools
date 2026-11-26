"""Two-stage effect descriptors with checked byte masks and address scheduling."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_effect_transition_150db9e0_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x150db9e0;ROM=0x108E90;WORDS=160
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

def derive(raw,refs,truth,retail_refs):
 assert len(raw)==len(truth)==640 and len(refs)==len(retail_refs)==25;a=list(struct.unpack('>160I',raw));z=list(struct.unpack('>160I',truth));assert a[0]==z[0]==0x27BDFF30 and a[2]==z[2]==0x30D000FF
 # Both replacements read the same unmodified zero-extended S0, before any call.
 for offset in(0x20,0x2C):assert a[offset//4]==0x02003025 and z[offset//4]==0x320600FF
 # Check every instruction from the ANDI through each use is an identical
 # branch/delay or writes a register other than S0; no call can intervene.
 for i,w in enumerate(a[3:0x30//4],3):
  if w>>26==0:assert(w>>11&31)!=16
  elif w>>26 in(9,15,35):assert(w>>16&31)!=16
  else:assert w>>26 in(4,20,43)
  assert w>>26!=3
 expected=0x3C010000;assert a[0x74//4]==z[0x84//4]==expected and refs[0x74]==retail_refs[0x84]==[('R_MIPS_HI16','D_800A0C0C')]
 immediates=[0x240E0008,0x240F0008,0x2418FFB5,0x2419FFDA];assert a[0x78//4:0x88//4]==z[0x74//4:0x84//4]==immediates
 normal=a[:]
 for offset in(0x20,0x2C):normal[offset//4]=0x320600FF
 normal[0x74//4:0x88//4]=[*immediates,expected];nr=dict(refs);nr[0x84]=nr.pop(0x74);assert normal==z and nr==retail_refs
 diff=[4*i for i,(x,y)in enumerate(zip(a,z))if x!=y or refs.get(4*i)!=retail_refs.get(4*i)];assert diff==[0x20,0x2C,0x74,0x78,0x7C,0x80,0x84]
 return diff,dict(S0_zero_extended_before_both_masks=True,no_S0_write_or_call_before_masks=True,address_LUI_moved_over_four_independent_immediates=True,all_memory_access_and_FP_transfer_order_unchanged=True,no_FP_arithmetic_rewrites=True,private_frame_identity=True,raw_fault_full_private_identity_at_memory_access_cuts_claimed=True,asynchronous_interrupt_identity_not_claimed=True)

def objects():
 prepare();fn=FUNCTION
 full=(b/MANIFEST['asm']).read_text();original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+fn+'\n'+full.split('glabel '+fn+'\n',1)[1].split('endlabel '+fn,1)[0]+'endlabel '+fn+'\n.size '+fn+',.-'+fn+'\n';(o/'original-target.s').write_text(original)
 source=MANIFEST['selected_source'];(o/'selected-owner.c').write_text(source);(o/'selected-Makefile').write_bytes((b/'conker/Makefile').read_bytes());old,diag=compile_owner(r,o,(b/'conker/src/game/generated_108E90.c').read_text(),'selected-before');assert not diag;new,diag=compile_owner(r,o,source,'selected-owner');assert not diag
 assemble((o/'original-target.s').read_text(),o/'original-target.o');truth,refs=payload(o/'original-target.o',fn);raw,rr=payload(new,fn);diff,proof=derive(raw,rr,truth,refs);assert same_functions(old,new,(fn,))==11 and normalized_pools(old)==normalized_pools(new)
 guards=(b/'conker/retail_word_patches.us.csv').read_bytes();assert fn not in guards.decode();fields=next(csv.reader(io.StringIO(guards.decode())));buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\n')
 def reftext(entries):return ';'.join(kind+':'+name for kind,name in entries)if entries else'-'
 for off in diff:
  row=dict.fromkeys(fields,'');row.update(filename='generated_108E90',function=fn,offset=f'0x{off:03X}',expected='0x'+raw[off:off+4].hex().upper(),replacement='0x'+truth[off:off+4].hex().upper(),expected_relocations=reftext(rr.get(off)),replacement_relocations=reftext(refs.get(off)),note='Normalize proven redundant byte masks and independent scalar-address schedule',omit='false');writer.writerow(row)
 add=buf.getvalue().encode();add=add.replace(b'\n',b'\r\n')if b'\r\n'in guards[:500]else add;(o/'guard-additions.csv').write_bytes(add);(o/'selected-guards.csv').write_bytes(guards+add);assemble(assembly(truth,refs,fn),o/'normalized-target.o');where=o/'qualified-owner';where.mkdir(exist_ok=True);retail=b/'conker/asm/108E90.s';outs=[]
 for label,emit in [('generic',lambda obj,patches:restore_labels(pc.emit_padded_assembly(obj,b/'conker/retail_layout.us.txt','generated_108E90',word_patches_path=patches),retail)),('generated',lambda obj,patches:pg.emit_padded_assembly(obj,retail,filename='generated_108E90',word_patches_path=patches))]:
  before=where/(label+'-before.o');assemble(emit(old,b/'conker/retail_word_patches.us.csv'),before);assert before.read_bytes()==(b/'conker/build/src/game/generated_108E90.c.o').read_bytes();after=where/(label+'.o');assemble(emit(new,o/'selected-guards.csv'),after);assert payload(after,fn)==(truth,refs)and same_functions(before,after,(fn,))==11 and normalized_pools(before)==normalized_pools(after);outs.append(after)
 assert outs[0].read_bytes()==outs[1].read_bytes();q=dict(words=160,retail_slot_words=160,frame=208,raw_byte_exact=False,normalized_byte_exact=True,raw_direct_words=153,guards=7,guarded_raw_relocations=1,raw_binding_positions=25,insertions=0,omissions=0,retail_padding_words=0,neighbors=11,raw_and_padded_pools_unchanged=True,both_complete_padders_equal=True,selected_source_sha256=sha(o/'selected-owner.c'),raw_SHA256=hashlib.sha256(raw).hexdigest(),padded_sha256=sha(outs[0]),normal_IDO_O2_g3_mips2_o32_profile=True,old_guard_prefix_unchanged=True,structural_rewrite=proof,source_installed=installed(),matching_credit=0);(o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=="__main__":objects()
