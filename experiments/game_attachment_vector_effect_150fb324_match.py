"""Paired attachment effects with qualified private homes and argument schedule."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_attachment_vector_effect_150fb324_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x150FB324;ROM=0x1287D4;WORDS=101
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
 data=bytes.fromhex(MANIFEST['preset_hex']);rom=(ROOT/'conker/conker.us.bin').read_bytes();at=MANIFEST['preset_ROM'];assert len(data)==48 and rom[at:at+48]==data
 target=OUT/'table-presets.bin'
 if target.exists():assert target.read_bytes()==data
 else:target.write_bytes(data)
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['object']:MANIFEST['padded_sha256'],'conker/build/conker.us.elf':MANIFEST['predicted_ELF_sha256'],'conker/retail_word_patches.us.csv':MANIFEST['guards_sha256']}
 for n,d in MANIFEST['inputs'].items():
  if not _CHECKED and(OUT/'baseline'/n).is_file():assert sha(OUT/'baseline'/n)==d,('Frozen',n)
  if not _CHECKED or n in allowed:assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase',n)
 assert sha(ROOT/'conker/retail_word_patches.us.csv')==(MANIFEST['guards_sha256'] if live else MANIFEST['inputs']['conker/retail_word_patches.us.csv']);_CHECKED=True;return live



fn=FUNCTION;owner=MANIFEST['filename']

def assemble(s,path):
 f=path.with_suffix('.s');f.write_text(s);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr

def derive(raw,refs,truth,tr):
 a=list(struct.unpack('>100I',raw));z=list(struct.unpack('>101I',truth));assert a[0]==z[0]==0x27BDFF60 and len(refs)==len(tr)==11
 assert a[2:5]==[0xAFA400A0,0xAFA500A4,0xAFA600A8] and a[0xB4//4:0xC4//4]==[0x8FAD00A0,0x8DAE01D4,0x51C00031,0x8FBF0024]
 # This extra retail read repeats the stable incoming owner home before any
 # call or home write. Fault behavior is qualified separately, never erased.
 assert not any(w>>26==3 or (w>>26 in(40,41,43,57)and w>>21&31==29 and 0xA0<=(w&65535)<0xA4)for w in a[5:0xC4//4])
 homes={0x44:0x78,0x48:0x74,**{i:i-8 for i in range(0x4C,0x7C,4)}};assert set(homes)==set(homes.values())
 v=a[:];v.insert(0xC4//4,0x8FA900A0)
 for i,w in enumerate(v):
  off=i*4;new=w
  if off==0xBC:new=(w&~65535)|((w&65535)+1)
  if w>>21&31==29 and w>>26 in(9,35,43,49,57)and w&65535 in homes:new=(new&~65535)|homes[w&65535]
  # Consumed attachment base is the same stable home value now read toT1.
  if off==0xE0:assert w==0x8DA601D4;new=(new&~(31<<21))|(9<<21)
  cycle={9:11,11:12,12:10,10:9}if 0x11C<=off<=0x150 else{10:13,13:10}if 0x15C<=off<=0x174 else{}
  fields=(21,16,11)if w>>26==0 else(21,16)if w>>26 in(9,35,36,43)else()
  for shift in fields:
   reg=w>>shift&31
   if reg in cycle:new=(new&~(31<<shift))|(cycle[reg]<<shift)
  v[i]=new
 # This is an instruction permutation: each instruction occurs exactly once.
 # The three SUB.S operands/order remain literal. Only private stores and
 # loads of already homed incoming values move around those SUB.S operations.
 permutation={0x11C:0x138,0x120:0x120,0x124:0x12C,0x128:0x13C,0x12C:0x140,0x130:0x130,0x134:0x11C,0x138:0x124,0x13C:0x128,0x140:0x134}
 assert set(permutation)==set(permutation.values());normal=v[:]
 def footprint(w):
  op,rs,rt,rd=w>>26,w>>21&31,w>>16&31,w>>11&31
  if op==9:return {('r',rs)}, {('r',rt)}, set(),set()
  if op in(35,36):assert rs==29;return {('r',29)},{('r',rt)},set(range(w&65535,(w&65535)+(1 if op==36 else 4))),set()
  if op in(43,57):assert rs==29;return {('r',29),('f'if op==57 else'r',rt)},set(),set(),set(range(w&65535,(w&65535)+4))
  assert op==17 and rs==16 and w&63==1
  return {('f',rd),('f',rt),('csr',0)},{('f',w>>6&31),('csr',0)},set(),set()
 reversed_pairs=0;destination={fr:at for at,fr in permutation.items()}
 for left in sorted(permutation):
  for right in sorted(permutation):
   if left>=right or destination[left]<destination[right]:continue
   reads,writes,mr,mw=footprint(v[left//4]);rr,rw,rm,rwm=footprint(v[right//4]);assert not(writes&(rr|rw)or rw&reads or mw&(rm|rwm)or rwm&mr),(hex(left),hex(right))
   reversed_pairs+=1
 for at,fr in permutation.items():normal[at//4]=v[fr//4]
 assert normal==z,[(hex(i*4),hex(x),hex(y))for i,(x,y)in enumerate(zip(normal,z))if x!=y]
 assert [w for w in a if w>>26==17]==[w for w in normal if w>>26==17]
 assert {off+(4 if off>=0xC4 else 0):values for off,values in refs.items()}==tr
 rows=[]
 for i,w in enumerate(a):
  at=i*4+(4 if i*4>=0xC4 else 0);new=normal[at//4];inserted=normal[0xC4//4]if i*4==0xC0 else None
  if new!=w or inserted is not None:rows.append(dict(offset=i*4,expected=w,replacement=new,insert_after=inserted))
 proof=dict(raw_words=100,normalized_words=101,frame=160,home_bijection=homes,insertion_offset=0xC4,inserted_owner_home_read=0x8FA900A0,branch_delta=1,argument_cycles=[dict(region=[0x11C,0x150],cycle={9:11,11:12,12:10,10:9}),dict(region=[0x15C,0x174],cycle={10:13,13:10})],normalized_offset_to_prepermutation_offset=permutation,reversed_instruction_pairs_proved_independent=reversed_pairs,independence_includes_GPR_FPR_FCSR_and_byte_memory_footprints=True,all_COP1_words_and_order_literal=True,no_semantic_memory_access_added_except_duplicated_owner_home_read=True,raw_full_fault_identity_not_claimed=True,semantic_qualification_complete=False)
 return rows,proof

def objects():
 full=(b/MANIFEST['asm']).read_text();original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+fn+'\n'+full.split('glabel '+fn+'\n',1)[1].split('endlabel '+fn,1)[0]+'endlabel '+fn+'\n.size '+fn+',.-'+fn+'\n';(o/'original-target.s').write_text(original);assemble(original,o/'original-target.o')
 prepare();source=MANIFEST['selected_source']
 (o/'semantic-source.c').write_text(source);(o/'selected-owner.c').write_text(source);(o/'selected-Makefile').write_bytes((b/'conker/Makefile').read_bytes())
 before,diag=compile_owner(r,o,(b/'conker/src/game/generated_126F60.c').read_text(),'before-owner');assert not diag
 selected,diag=compile_owner(r,o,source,'selected-owner');assert not diag;assert same_functions(before,selected,(fn,))==17 and normalized_pools(before)==normalized_pools(selected)
 raw,refs=payload(selected,fn);truth,tr=payload(o/'original-target.o',fn);rows,proof=derive(raw,refs,truth,tr)
 prefix=(b/'conker/retail_word_patches.us.csv').read_bytes();assert fn not in prefix.decode();fields=next(csv.reader(io.StringIO(prefix.decode())));buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in prefix[:300]else'\n');spec=lambda x:';'.join(k+':'+n for k,n in x)or'-'
 for row in rows:
  off=row['offset'];out=dict.fromkeys(fields,'');out.update(filename=owner,function=fn,offset=hex(off),expected=hex(row['expected']),replacement=hex(row['replacement']),expected_relocations=spec(refs.get(off,[])),replacement_relocations=spec(refs.get(off,[])),note='Derived attachment-effect private home bijection, stable owner-home reload, closed GPR roles and independent argument schedule; COP1 order literal',omit='false')
  if row['insert_after']is not None:out.update(insert_after=hex(row['insert_after']),insert_after_relocations='-')
  writer.writerow(out)
 (o/'guard-additions.csv').write_bytes(buf.getvalue().encode());(o/'selected-guards.csv').write_bytes(prefix+buf.getvalue().encode());assemble(assembly(truth,tr,fn),o/'normalized-target.o')
 where=o/'qualified-owner';where.mkdir(exist_ok=True);outputs=[]
 for mode,obj in [('before',before),('selected',selected)]:
  guards=b/'conker/retail_word_patches.us.csv'if mode=='before'else o/'selected-guards.csv'
  for kind in('generic','generated'):
   text=restore_labels(pc.emit_padded_assembly(obj,b/'conker/retail_layout.us.txt',owner,word_patches_path=guards),b/'conker/asm/126F60.s')if kind=='generic'else pg.emit_padded_assembly(obj,b/'conker/asm/126F60.s',filename=owner,word_patches_path=guards);path=where/(mode+'-'+kind+'.o');assemble(text,path)
   if mode=='before':assert path.read_bytes()==(b/'conker/build/src/game/generated_126F60.c.o').read_bytes()
   else:assert payload(path,fn)==(truth,tr)and same_functions(where/('before-'+kind+'.o'),path,(fn,))==17;outputs.append(path)
 assert outputs[0].read_bytes()==outputs[1].read_bytes();syms={n:int(n.split('_',1)[1],16)for v in tr.values()for _,n in v};assert struct.pack('>101I',*bound_blob(truth,tr,syms))==(r/'conker/conker.us.bin').read_bytes()[0x1287D4:0x128968]
 q=dict(words=100,normalized_words=101,retail_slot_words=103,frame=160,guards=len(rows),insertions=1,omissions=0,raw_binding_positions=11,normalized_byte_exact=True,raw_byte_exact=False,raw_neighbors=17,both_complete_padders_equal=True,both_before_objects_equal_frozen=True,source_sha256=sha(o/'selected-owner.c'),padded_sha256=sha(outputs[0]),structural_derivation=proof,semantic_qualification_complete=False,source_installed=installed(),matching_credit=0);(o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=="__main__":objects()
