"""Pointer quad vertices, retained template attributes and complete owner integrity."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_pointer_quad_vertices_150db714_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x150db714;ROM=0x108BC4;WORDS=178
r=ROOT;o=OUT;b=o/'baseline';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_local_vector_transform_15117da4_match import restore_labels,assembly as _assembly
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import check_bouncing_effect_150db114_pool as old_pool
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

def written(w):
 op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;f=w&63
 if not w:return None
 if op==0:return rd if f in(0,2,3,4,6,7,0x10,0x12,0x20,0x21,0x22,0x23,0x24,0x25,0x26,0x27,0x2A,0x2B)else None
 if op in(8,9,10,11,12,13,14,15,0x20,0x21,0x22,0x23,0x24,0x25,0x26):return rt
 if op==17 and rs==0:return rt
 return 31 if op==3 else None

def derive(raw,refs,truth,retail_refs):
 assert len(raw)==len(truth)==712 and refs==retail_refs and len(refs)==7
 a=list(struct.unpack('>178I',raw));z=list(struct.unpack('>178I',truth));assert a[0]==z[0]==0x27BDFFA8;assert a[0xF4//4]==z[0xD4//4]==0x26030110
 assert all(written(w)not in(3,16)for i,w in enumerate(a[0xD4//4:-4])if 4*i+0xD4!=0xF4)
 assert all(written(w)!=16 for w in a[0xD4//4:-4]);assert all(w>>26!=3 for w in a[0xD4//4:])
 # In the moved block, every instruction except the ADDIU is independent of V1.
 block=a[0xD4//4:0xF4//4];assert len(block)==8
 for w in block:
  op=w>>26;rs=w>>21&31;assert written(w)!=3;assert op in(35,49,17)
  if op in(35,49):assert rs in(16,29,11,12)and rs!=3
 promoted=[];normal=a[:]
 for i,w in enumerate(a):
  if w>>26==35 and w>>21&31==16 and(w&65535)in(0x110,0x118,0x11C):
   normal[i]=(w&~((31<<21)|65535))|(3<<21)|((w&65535)-0x110);promoted.append(4*i)
 assert len(promoted)==13,promoted
 # Modular address identity for every folded load, without pointer alias assumptions.
 for off in promoted:
  old=a[off//4];new=normal[off//4];assert(old&65535)==0x110+(new&65535);assert(old>>16&31)==(new>>16&31)and old>>26==new>>26==35
 normal[0xD4//4:0xF8//4]=[a[0xF4//4],*normal[0xD4//4:0xF4//4]]
 # The chosen Y-expression forms already retain the retail pointer-read order.
 # Do not commute these loads: doing so fails complete-word identity.
 assert normal==z,[(hex(4*i),hex(x),hex(y))for i,(x,y)in enumerate(zip(normal,z))if x!=y]
 # Contrary to the advisory's dead-register claim, raw V1 remains live at the end.
 v1_reads=[4*i for i,w in enumerate(a)if w>>26 in(35,49,57)and w>>21&31==3];assert 0x260 in v1_reads and 0x264 in v1_reads
 diff=[4*i for i,(x,y)in enumerate(zip(a,z))if x!=y];assert len(diff)==20 and not set(diff)&set(refs)
 return diff,dict(invariant_address_promotion=True,modular_O32_address_identities=len(promoted),base_init_moved_over_eight_independent_instructions=True,pointer_read_swap=False,all_memory_access_order_preserved=True,FP_opcode_operands_and_logical_order_unchanged=True,raw_V1_live_read_offsets=v1_reads,pointer_source_aliases_not_excluded=True,raw_private_fault_GPR_and_EPC_identity_not_claimed=True)

def objects():
 prepare();fn=FUNCTION
 full=(b/MANIFEST['asm']).read_text();original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+fn+'\n'+full.split('glabel '+fn+'\n',1)[1].split('endlabel '+fn,1)[0]+'endlabel '+fn+'\n.size '+fn+',.-'+fn+'\n';(o/'original-target.s').write_text(original)
 source=MANIFEST['selected_source'];(o/'selected-owner.c').write_text(source);(o/'selected-Makefile').write_bytes((b/'conker/Makefile').read_bytes());old,diag=compile_owner(r,o,(b/'conker/src/game/generated_108320.c').read_text(),'selected-before');assert not diag;new,diag=compile_owner(r,o,source,'selected-owner');assert not diag
 assemble((o/'original-target.s').read_text(),o/'original-target.o');truth,refs=payload(o/'original-target.o',fn);raw,rr=payload(new,fn);diff,proof=derive(raw,rr,truth,refs);assert same_functions(old,new,(fn,))==5 and normalized_pools(old)==normalized_pools(new)
 guards=(b/'conker/retail_word_patches.us.csv').read_bytes();assert fn not in guards.decode();fields=next(csv.reader(io.StringIO(guards.decode())));buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\n')
 for off in diff:
  row=dict.fromkeys(fields,'');row.update(filename='generated_108320',function=fn,offset=f'0x{off:03X}',expected='0x'+raw[off:off+4].hex().upper(),replacement='0x'+truth[off:off+4].hex().upper(),expected_relocations='-',replacement_relocations='-',note='Normalize live-source address promotion and independent address-init schedule',omit='false');writer.writerow(row)
 add=buf.getvalue().encode();add=add.replace(b'\n',b'\r\n')if b'\r\n'in guards[:500]else add;(o/'guard-additions.csv').write_bytes(add);(o/'selected-guards.csv').write_bytes(guards+add);assemble(assembly(truth,refs,fn),o/'normalized-target.o')
 boundold=o/'bound-before.o';boundnew=o/'bound-owner.o';assemble(old_pool.bind_assembly(old),boundold);assemble(old_pool.bind_assembly(new),boundnew);where=o/'qualified-owner';where.mkdir(exist_ok=True);retail=b/'conker/asm/108320.s';outs=[]
 for label,emit in [('generic',lambda obj,patches:restore_labels(pc.emit_padded_assembly(obj,b/'conker/retail_layout.us.txt','generated_108320',word_patches_path=patches),retail)),('generated',lambda obj,patches:pg.emit_padded_assembly(obj,retail,filename='generated_108320',word_patches_path=patches))]:
  before=where/(label+'-before.o');assemble(emit(boundold,b/'conker/retail_word_patches.us.csv'),before);assert before.read_bytes()==(b/'conker/build/src/game/generated_108320.c.o').read_bytes();after=where/(label+'.o');assemble(emit(boundnew,o/'selected-guards.csv'),after);assert payload(after,fn)==(truth,refs)and same_functions(before,after,(fn,))==5 and normalized_pools(before)==normalized_pools(after);outs.append(after)
 assert outs[0].read_bytes()==outs[1].read_bytes();q=dict(words=178,retail_slot_words=179,frame=88,raw_byte_exact=False,normalized_byte_exact=True,raw_direct_words=158,guards=20,guarded_relocations=0,raw_binding_positions=7,insertions=0,omissions=0,retail_padding_words=1,neighbors=5,raw_and_padded_pools_unchanged=True,both_complete_padders_equal=True,selected_source_sha256=sha(o/'selected-owner.c'),raw_SHA256=hashlib.sha256(raw).hexdigest(),padded_sha256=sha(outs[0]),normal_IDO_O2_g3_mips2_o32_profile=True,old_guard_prefix_unchanged=True,structural_rewrite=proof,source_installed=installed(),matching_credit=0);(o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=="__main__":objects()
