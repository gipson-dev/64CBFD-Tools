"""Direct display sprite slot, palette snapshot and exact original frame."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_display_sprite_slot_15179600_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x15179600;ROM=0x1A6AB0;WORDS=108
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

def warning_signature(text):assert not text,text;return []

def derive(raw,refs,truth,retail_refs):
 assert len(raw)==len(truth)==432 and refs==retail_refs and len(refs)==14
 a=list(struct.unpack('>108I',raw));z=list(struct.unpack('>108I',truth));assert a[0]==z[0]==0x27BDFF08
 mapping={10:15,15:25,25:10,11:24,24:9,9:11};assert set(mapping)==set(mapping.values())
 # The only changed instruction fields implement two closed three-register
 # cycles. Every mapped role is defined before use and ends before a call;
 # no mapped register supplies a memory base or an ABI argument.
 normal=a[:];defined=set();definitions=[];reads=[]
 for off in range(0x114,0x168,4):
  w=a[off//4];op,rs,rt=w>>26,w>>21&31,w>>16&31;read_regs=[];write_regs=[];positions=[]
  if op in(35,33):read_regs=[rs];write_regs=[rt];positions=[(21,rs),(16,rt)]
  elif op in(9,13):read_regs=[rs];write_regs=[rt];positions=[(21,rs),(16,rt)]
  elif op in(40,41,43):read_regs=[rs,rt];positions=[(21,rs),(16,rt)]
  elif w==0x00003025:read_regs=[0];write_regs=[6]
  else:raise AssertionError((hex(off),hex(w)))
  if op in(35,33,40,41,43):assert rs not in mapping
  for register in read_regs:
   if register in mapping:assert register in defined,(off,register);reads.append((off,register))
  for register in write_regs:
   if register in mapping:defined.add(register);definitions.append((off,register));assert register not in range(4,8)
  for shift,register in positions:
   if register in mapping:w=(w&~(31<<shift))|(mapping[register]<<shift)
  normal[off//4]=w
 assert defined==set(mapping)and len(definitions)==len(reads)==6
 assert a[0x168//4]>>26==3 and refs[0x168]==[('R_MIPS_26','func_15168800')]
 assert normal==z
 diff=[i*4 for i,(x,y)in enumerate(zip(a,z))if x!=y];assert diff==[0x114,0x118,0x124,0x128,0x12C,0x130,0x13C,0x140,0x144,0x148,0x15C,0x160],diff
 proof=dict(cycles=[[10,15,25],[11,24,9]],mapping_raw_to_retail=mapping,interval=['0x114','0x168'],each_role_defined_once_before_use=True,all_roles_end_before_factory_call=True,only_caller_saved_non_argument_GPRs=True,no_memory_bases_renamed=True,all_opcodes_immediates_bindings_control_FP_and_instruction_order_unchanged=True,all_memory_accesses_and_private_frame_identity=True,raw_full_private_fault_GPR_identity_not_claimed=True,normalized_literal_fault_identity_required=True)
 return diff,proof

def objects():
 prepare();fn=FUNCTION
 full=(b/MANIFEST['asm']).read_text();original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+fn+'\n'+full.split('glabel '+fn+'\n',1)[1].split('endlabel '+fn,1)[0]+'endlabel '+fn+'\n.size '+fn+',.-'+fn+'\n';(o/'original-target.s').write_text(original)
 source=MANIFEST['selected_source'];(o/'selected-owner.c').write_text(source);(o/'selected-Makefile').write_bytes((b/'conker/Makefile').read_bytes());old,diag=compile_owner(r,o,(b/'conker/src/game/generated_1A6360.c').read_text(),'selected-before');warning_signature(diag);new,diag=compile_owner(r,o,source,'selected-owner');warning_signature(diag)
 assemble((o/'original-target.s').read_text(),o/'original-target.o');truth,refs=payload(o/'original-target.o',fn);raw,rr=payload(new,fn);diff,proof=derive(raw,rr,truth,refs);assert same_functions(old,new,(fn,))==8 and normalized_pools(old)==normalized_pools(new)
 symbols={name:int(name.split('_',1)[1],16)for entries in refs.values()for _,name in entries};assert struct.pack('>108I',*bound_blob(truth,refs,symbols))==(r/'conker/conker.us.bin').read_bytes()[0x1A6AB0:0x1A6C60]
 guards=(b/'conker/retail_word_patches.us.csv').read_bytes();assert fn not in guards.decode();fields=next(csv.reader(io.StringIO(guards.decode())));buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\n')
 for off in diff:
  assert off not in rr
  row=dict.fromkeys(fields,'');row.update(filename='generated_1A6360',function=fn,offset=f'0x{off:03X}',expected='0x'+raw[off:off+4].hex().upper(),replacement='0x'+truth[off:off+4].hex().upper(),expected_relocations='-',replacement_relocations='-',note='Normalize two closed caller-saved GPR cycles with definition before use; no opcode address or schedule changes',omit='false');writer.writerow(row)
 add=buf.getvalue().encode();add=add.replace(b'\n',b'\r\n')if b'\r\n'in guards[:500]else add;(o/'guard-additions.csv').write_bytes(add);(o/'selected-guards.csv').write_bytes(guards+add);assemble(assembly(truth,refs,fn),o/'normalized-target.o')
 where=o/'qualified-owner';where.mkdir(exist_ok=True);retail=b/'conker/asm/1A6360.s';outs=[]
 for label,emit in [('generic',lambda obj,patches:restore_labels(pc.emit_padded_assembly(obj,b/'conker/retail_layout.us.txt','generated_1A6360',word_patches_path=patches),retail)),('generated',lambda obj,patches:pg.emit_padded_assembly(obj,retail,filename='generated_1A6360',word_patches_path=patches))]:
  before=where/(label+'-before.o');assemble(emit(old,b/'conker/retail_word_patches.us.csv'),before);assert before.read_bytes()==(b/'conker/build/src/game/generated_1A6360.c.o').read_bytes();after=where/(label+'.o');assemble(emit(new,o/'selected-guards.csv'),after);assert payload(after,fn)==(truth,refs)and same_functions(before,after,(fn,))==8 and normalized_pools(before)==normalized_pools(after);outs.append(after)
 assert outs[0].read_bytes()==outs[1].read_bytes();parsed=pg.parse_retail_slice(retail)
 q=dict(words=108,retail_slot_words=108,frame=248,raw_byte_exact=False,normalized_byte_exact=True,raw_direct_words=96,guards=12,raw_binding_positions=14,guarded_relocations=0,insertions=0,omissions=0,retail_padding_words=0,neighbors=8,raw_and_padded_pools_unchanged=True,both_complete_padders_equal=True,exported_retail_jump_labels_retained=sum(len(v)for v in parsed[3].values()),complete_owner_layout_functions=9,selected_source_sha256=sha(o/'selected-owner.c'),raw_SHA256=hashlib.sha256(raw).hexdigest(),padded_sha256=sha(outs[0]),normal_IDO_O2_g3_mips2_o32_profile=True,unchanged_existing_diagnostics=[],new_compiler_diagnostics=0,old_guard_prefix_unchanged=True,meaningful_random_draw_capture_restores_original_frame=True,structural_rewrite=proof,source_installed=installed(),matching_credit=0);(o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=="__main__":objects()
