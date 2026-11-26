"""Display sprite opacity, phase, motion and origin wrap with derived guards."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_display_sprite_update_151797b0_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x151797B0;ROM=0x1A6C60;WORDS=194
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
 assert len(raw)==len(truth)==776 and refs==retail_refs and len(refs)==18
 a=list(struct.unpack('>194I',raw));z=list(struct.unpack('>194I',truth));assert a[1]==z[1]==0x27BDFFC8
 diff=[i*4 for i,(x,y)in enumerate(zip(a,z))if x!=y];assert diff==[0x120,0x128,0x130,0x144,0x14C,0x150,0x1E4,0x22C,0x274],diff
 def immediate(op,rs,rt,imm):return(op<<26)|(rs<<21)|(rt<<16)|imm
 def shift(rt,rd):return(rt<<16)|(rd<<11)|(8<<6)|3
 normal=a[:]
 for load,shr,mask,raw_temp,retail_temp in((0x120,0x128,0x130,9,10),(0x144,0x14C,0x150,15,14)):
  assert a[load//4]==immediate(37,5,2,0xAE)and z[load//4]==immediate(37,5,4,0xAE)
  assert a[shr//4]==shift(2,raw_temp)and z[shr//4]==shift(4,retail_temp)
  assert a[mask//4]==immediate(12,raw_temp,4,255)and z[mask//4]==immediate(12,retail_temp,4,255)
  # LHU -> SRA8 -> ANDI255 maps every possible phase halfword to the
  # same zero-extended byte ABI argument, including the first JAL delay slot.
  def argument(sequence,phase):
   regs=[0xA5000000+i for i in range(32)];regs[0]=0
   for word in sequence:
    op,rs,rt,rd,amount,fun=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63
    if op==37:assert rs==5 and word&65535==0xAE;regs[rt]=phase
    elif op==0 and fun==3:regs[rd]=((((regs[rt]^0x80000000)-0x80000000)>>amount)&0xFFFFFFFF)
    elif op==12:regs[rt]=regs[rs]&(word&65535)
    else:raise AssertionError(hex(word))
   return regs
  for phase in range(65536):
   ar=argument([a[at//4]for at in(load,shr,mask)],phase);zr=argument([z[at//4]for at in(load,shr,mask)],phase);assert ar[4]==zr[4]==phase//256 and ar[raw_temp]==zr[retail_temp]
  for at in(load,shr,mask):normal[at//4]=z[at//4]
 for at in(0x1E4,0x22C,0x274):
  w=a[at//4];assert w>>26==0 and w&63==0x21;rs,rt=w>>21&31,w>>16&31;swapped=(w&~((31<<21)|(31<<16)))|(rt<<21)|(rs<<16);assert swapped==z[at//4];normal[at//4]=swapped
 assert normal==z and all(a[i]==z[i]for i,w in enumerate(a)if w>>26==17)
 assert[(i,w)for i,w in enumerate(a)if w>>26 in(1,2,3,4,5,6,7,20,21,22,23)]==[(i,w)for i,w in enumerate(z)if w>>26 in(1,2,3,4,5,6,7,20,21,22,23)]
 assert all(at not in refs for at in diff)
 proof=dict(byte_argument_blocks=[[0x120,0x128,0x130],[0x144,0x14C,0x150]],phase_domain_halfwords=65536,actual_helper_prototypes_unsigned8=True,same_masked_byte_at_each_call=True,raw_argument_register_roles_differ=True,integer_addu_operand_swaps=[0x1E4,0x22C,0x274],all_FP_words_positions_and_operand_order_identical=True,all_memory_addresses_order_widths_immediates_and_bindings_identical=True,all_calls_branches_and_private_frame_identical=True,raw_full_private_fault_GPR_identity_not_claimed=True,normalized_literal_fault_identity_required=True,no_FP_rewrites_or_instruction_motion=True)
 return diff,proof

def objects():
 prepare();fn=FUNCTION
 full=(b/MANIFEST['asm']).read_text();original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+fn+'\n'+full.split('glabel '+fn+'\n',1)[1].split('endlabel '+fn,1)[0]+'endlabel '+fn+'\n.size '+fn+',.-'+fn+'\n';(o/'original-target.s').write_text(original)
 source=MANIFEST['selected_source'];(o/'selected-owner.c').write_text(source);(o/'selected-Makefile').write_bytes((b/'conker/Makefile').read_bytes());old,diag=compile_owner(r,o,(b/'conker/src/game/generated_1A6360.c').read_text(),'selected-before');warning_signature(diag);new,diag=compile_owner(r,o,source,'selected-owner');warning_signature(diag)
 assemble((o/'original-target.s').read_text(),o/'original-target.o');truth,refs=payload(o/'original-target.o',fn);raw,rr=payload(new,fn);diff,proof=derive(raw,rr,truth,refs);assert same_functions(old,new,(fn,))==8 and normalized_pools(old)==normalized_pools(new)
 symbols={name:int(name.split('_',1)[1],16)for entries in refs.values()for _,name in entries};assert struct.pack('>194I',*bound_blob(truth,refs,symbols))==(r/'conker/conker.us.bin').read_bytes()[0x1A6C60:0x1A6F68]
 guards=(b/'conker/retail_word_patches.us.csv').read_bytes();assert fn not in guards.decode();fields=next(csv.reader(io.StringIO(guards.decode())));buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\n')
 for off in diff:
  assert off not in rr
  row=dict.fromkeys(fields,'');row.update(filename='generated_1A6360',function=fn,offset=f'0x{off:03X}',expected='0x'+raw[off:off+4].hex().upper(),replacement='0x'+truth[off:off+4].hex().upper(),expected_relocations='-',replacement_relocations='-',note='Normalize two equivalent byte argument preparations and three commutative integer additions; no FP or memory order changes',omit='false');writer.writerow(row)
 add=buf.getvalue().encode();add=add.replace(b'\n',b'\r\n')if b'\r\n'in guards[:500]else add;(o/'guard-additions.csv').write_bytes(add);(o/'selected-guards.csv').write_bytes(guards+add);assemble(assembly(truth,refs,fn),o/'normalized-target.o')
 where=o/'qualified-owner';where.mkdir(exist_ok=True);retail=b/'conker/asm/1A6360.s';outs=[]
 for label,emit in [('generic',lambda obj,patches:restore_labels(pc.emit_padded_assembly(obj,b/'conker/retail_layout.us.txt','generated_1A6360',word_patches_path=patches),retail)),('generated',lambda obj,patches:pg.emit_padded_assembly(obj,retail,filename='generated_1A6360',word_patches_path=patches))]:
  before=where/(label+'-before.o');assemble(emit(old,b/'conker/retail_word_patches.us.csv'),before);assert before.read_bytes()==(b/'conker/build/src/game/generated_1A6360.c.o').read_bytes();after=where/(label+'.o');assemble(emit(new,o/'selected-guards.csv'),after);assert payload(after,fn)==(truth,refs)and same_functions(before,after,(fn,))==8 and normalized_pools(before)==normalized_pools(after);outs.append(after)
 assert outs[0].read_bytes()==outs[1].read_bytes();parsed=pg.parse_retail_slice(retail)
 q=dict(words=194,retail_slot_words=194,frame=56,raw_byte_exact=False,normalized_byte_exact=True,raw_direct_words=185,guards=9,raw_binding_positions=18,guarded_relocations=0,insertions=0,omissions=0,retail_padding_words=0,neighbors=8,raw_and_padded_pools_unchanged=True,both_complete_padders_equal=True,exported_retail_jump_labels_retained=sum(len(v)for v in parsed[3].values()),complete_owner_layout_functions=9,selected_source_sha256=sha(o/'selected-owner.c'),raw_SHA256=hashlib.sha256(raw).hexdigest(),padded_sha256=sha(outs[0]),normal_IDO_O2_g3_mips2_o32_profile=True,unchanged_existing_diagnostics=[],new_compiler_diagnostics=0,old_guard_prefix_unchanged=True,captured_origins_and_distance_speed_lifetimes_restore_original_frame=True,structural_rewrite=proof,source_installed=installed(),matching_credit=0);(o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=="__main__":objects()
