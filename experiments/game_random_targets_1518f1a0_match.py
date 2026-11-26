"""Direct random target callback, palette snapshot and exact original frame."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_random_targets_1518f1a0_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x1518f1a0;ROM=0x1BC650;WORDS=121
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

def warning_signature(text):
 import re
 lines=[line.strip()for line in text.splitlines()if line.strip()];assert len(lines)==12,text;calls=[]
 for i in range(0,len(lines),3):
  assert re.fullmatch(r'cfe: Warning 712: .+, line [0-9]+: illegal combination of pointer and integer',lines[i]),lines[i]
  assert re.fullmatch(r'[- ]+\^',lines[i+2]),lines[i+2];calls.append(lines[i+1])
 assert calls==['func_1518E4A0(arg0);']*2+['func_15190454(arg0);']*2,calls;return calls

def derive(raw,refs,truth,retail_refs):
 assert len(raw)==len(truth)==484 and len(refs)==len(retail_refs)==20;a=list(struct.unpack('>121I',raw));z=list(struct.unpack('>121I',truth));assert a[0]==z[0]==0x27BDFFE0
 diff=[4*i for i,(x,y)in enumerate(zip(a,z))if x!=y or refs.get(4*i)!=retail_refs.get(4*i)];assert diff==[0x30,0xA4,0xA8,0xAC,0xB0,0xB4,0xB8,0xBC,0xC0,0xC4,0xC8,0xCC,0xD8,0xDC],diff
 assert a[0x30//4]==a[0xA4//4]==z[0xAC//4]==0xC6200030
 assert z[0x30//4]==z[0xA4//4]==a[0xC0//4]==0x26300110
 assert a[0xA8//4]==0xC6280128 and z[0xA8//4]==0xC6080018
 assert a[0xBC//4]==0x862A012C and z[0xCC//4]==0x860A001C
 for at,raw_word,original_word in((0xD8,0xA62C012C,0xA60C001C),(0xDC,0x862D012C,0x860D001C)):assert a[at//4]==raw_word and z[at//4]==original_word
 expected=[0xC6200030,0xC6280128,0x3C010000,0xC4300000,0x46004281,0x3C0B0000,0x862A012C,0x26300110,0x46105482,0x46120100,0xE6240030]
 original=[0x26300110,0xC6080018,0xC6200030,0x3C010000,0xC4300000,0x46004281,0x3C0B0000,0x46105482,0x46120100,0xE6240030,0x860A001C]
 assert a[0xA4//4:0xD0//4]==expected and z[0xA4//4:0xD0//4]==original
 assert refs[0xAC]==retail_refs[0xB0]==[('R_MIPS_HI16','D_800A7B68')]and refs[0xB0]==retail_refs[0xB4]==[('R_MIPS_LO16','D_800A7B68')]and refs[0xB8]==retail_refs[0xBC]==[('R_MIPS_HI16','D_800BE9E4')]
 def control(words):return[(i,w)for i,w in enumerate(words)if w>>26 in(1,2,3,4,5,6,7,20,21,22,23)or(w>>26==0 and w&63 in(8,9))]
 assert control(a)==control(z)
 # Every COP1 arithmetic/conversion/transfer instruction and every opaque call
 # is unchanged and remains in the same relative order. Only RAM field reads
 # and a pure S0 address calculation move inside the no-call phase.
 assert[w for w in a if w>>26==17]==[w for w in z if w>>26==17]
 assert[(i,w,refs.get(4*i))for i,w in enumerate(a)if w>>26==3]==[(i,w,retail_refs.get(4*i))for i,w in enumerate(z)if w>>26==3]
 # The only advanced timer read cannot overlap the preceding split-value store
 # or target read for any common base; all are fields of a valid320byte object.
 fields=[set(range(at,at+n))for at,n in((0x30,4),(0x128,4),(0x12C,2))];assert all(not(fields[i]&fields[j])for i in range(3)for j in range(i+1,3))
 normal=a[:]
 for at in diff:normal[at//4]=z[at//4]
 nr=dict(refs)
 for at in diff:
  nr.pop(at,None)
  if at in retail_refs:nr[at]=retail_refs[at]
 assert normal==z and nr==retail_refs
 return diff,dict(all_FP_arithmetic_conversion_transfer_words_and_order_unchanged=True,all_call_and_control_words_and_positions_unchanged=True,same_record_disjoint_scalar_read_schedule=True,read_before_split_store_promoted_only_for_disjoint_timer_field=True,all_memory_writes_and_effective_addresses_preserved=True,S0_base_is_actor_plus110_and_no_observer_call_intervenes=True,private_frame_identity=True,raw_fault_access_order_identity_not_claimed=True,normalized_literal_fault_identity_required=True,no_FP_commutative_rewrites=True,no_new_loads_stores_calls_or_arithmetic=True)

def objects():
 prepare();fn=FUNCTION
 full=(b/MANIFEST['asm']).read_text();original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+fn+'\n'+full.split('glabel '+fn+'\n',1)[1].split('endlabel '+fn,1)[0]+'endlabel '+fn+'\n.size '+fn+',.-'+fn+'\n';(o/'original-target.s').write_text(original)
 source=MANIFEST['selected_source'];(o/'selected-owner.c').write_text(source);(o/'selected-Makefile').write_bytes((b/'conker/Makefile').read_bytes());old,diag=compile_owner(r,o,(b/'conker/src/game/generated_1BA1D0.c').read_text(),'selected-before');prior=warning_signature(diag);new,diag=compile_owner(r,o,source,'selected-owner');assert warning_signature(diag)==prior
 assemble((o/'original-target.s').read_text(),o/'original-target.o');truth,refs=payload(o/'original-target.o',fn);raw,rr=payload(new,fn);diff,proof=derive(raw,rr,truth,refs)
 assert same_functions(old,new,(fn,))==60 and normalized_pools(old)==normalized_pools(new)
 guards=(b/'conker/retail_word_patches.us.csv').read_bytes();assert fn not in guards.decode();fields=next(csv.reader(io.StringIO(guards.decode())));buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\n')
 def reftext(entries):return ';'.join(kind+':'+name for kind,name in entries)if entries else'-'
 for off in diff:
  row=dict.fromkeys(fields,'');row.update(filename='generated_1BA1D0',function=fn,offset=f'0x{off:03X}',expected='0x'+raw[off:off+4].hex().upper(),replacement='0x'+truth[off:off+4].hex().upper(),expected_relocations=reftext(rr.get(off)),replacement_relocations=reftext(refs.get(off)),note='Normalize same-record scalar read schedule and equivalent target-block addresses; no FP arithmetic rewrite',omit='false');writer.writerow(row)
 add=buf.getvalue().encode();add=add.replace(b'\n',b'\r\n')if b'\r\n'in guards[:500]else add;(o/'guard-additions.csv').write_bytes(add);(o/'selected-guards.csv').write_bytes(guards+add)
 assemble(assembly(truth,refs,fn),o/'normalized-target.o');where=o/'qualified-owner';where.mkdir(exist_ok=True);retail=b/'conker/asm/1BA1D0.s';outs=[]
 for label,emit in [('generic',lambda obj,patches:restore_labels(pc.emit_padded_assembly(obj,b/'conker/retail_layout.us.txt','generated_1BA1D0',word_patches_path=patches),retail)),('generated',lambda obj,patches:pg.emit_padded_assembly(obj,retail,filename='generated_1BA1D0',word_patches_path=patches))]:
  before=where/(label+'-before.o');assemble(emit(old,b/'conker/retail_word_patches.us.csv'),before);assert before.read_bytes()==(b/'conker/build/src/game/generated_1BA1D0.c.o').read_bytes();after=where/(label+'.o');assemble(emit(new,o/'selected-guards.csv'),after);assert payload(after,fn)==(truth,refs)and same_functions(before,after,(fn,))==60 and normalized_pools(before)==normalized_pools(after);outs.append(after)
 assert outs[0].read_bytes()==outs[1].read_bytes();_,_,_,labels=pg.parse_retail_slice(retail)
 q=dict(words=121,retail_slot_words=121,frame=32,raw_byte_exact=False,normalized_byte_exact=True,raw_direct_words=107,guards=14,guarded_raw_relocations=3,raw_binding_positions=20,insertions=0,omissions=0,retail_padding_words=0,neighbors=60,raw_and_padded_pools_unchanged=True,both_complete_padders_equal=True,exported_retail_jump_labels_retained=sum(len(v)for v in labels.values()),selected_source_sha256=sha(o/'selected-owner.c'),raw_SHA256=hashlib.sha256(raw).hexdigest(),padded_sha256=sha(outs[0]),normal_IDO_O2_g3_mips2_o32_profile=True,unchanged_existing_warning712_calls=prior,new_compiler_diagnostics=0,old_guard_prefix_unchanged=True,structural_rewrite=proof,source_installed=installed(),matching_credit=0);(o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=="__main__":objects()
