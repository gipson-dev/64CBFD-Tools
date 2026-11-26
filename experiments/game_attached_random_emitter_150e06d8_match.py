"""Attachment-point emitter: preserved FP order, frame bijection and saved-home stutter."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_attached_random_emitter_150e06d8_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x150E06D8;ROM=0x10DB88;WORDS=101
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


def plain_compile(root,out,text,name,flags):
 assert 'GLOBAL_ASM'not in text;src=out/(name+'.c');obj=out/(name+'.o');src.write_text(text);includes=['.','include','include/2.0L','include/2.0L/PR','include/libc','src/libultra/os','src/libultra/audio','src/libultra/io'];command=[str(root/'ido/ido5.3_recomp/cc'),'-c','-32','-G','0','-Xfullwarn','-Xcpluscomm','-signed','-nostdinc','-non_shared','-Wab,-r4300_mul','-D_LANGUAGE_C','-D_FINALROM','-DF3DEX_GBI_2','-D_MIPS_SZLONG=32','-woff','649,838',*[v for path in includes for v in('-I',path)],*flags,'-mips2','-o32','-o',obj.relative_to(root/'conker').as_posix(),src.relative_to(root/'conker').as_posix()];q=subprocess.run(command,cwd=root/'conker',capture_output=True,text=True);diag=q.stdout+q.stderr;(out/(name+'-diagnostics.txt')).write_text(diag);assert q.returncode==0,diag;return obj,diag
def assemble(s,path):
 f=path.with_suffix('.s');f.write_text(s);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr

def derive(raw,refs,truth,tr):
 a=list(struct.unpack('>100I',raw));z=list(struct.unpack('>101I',truth));assert a[0]==z[0]==0x27BDFF90 and len(refs)==len(tr)==17
 assert a[8:12]==z[8:12]and a[12]&65535==83 and z[12]&65535==84
 # The prologue stores incoming owner A0 atSP+70, then reads it at18. No
 # instruction before the inserted read changes that home or invokes a call.
 assert a[2]==0xAFA40070 and a[6]==0x8FAE0070
 assert not any((w>>26 in(40,41,43,57)and w>>21&31==29 and(w&65535)<=0x70<(w&65535)+4)or w>>26==3 for w in a[3:14])
 homes={0x44:0x60,0x48:0x4C,0x4C:0x48,0x50:0x44,0x54:0x50,0x58:0x54,0x5C:0x58,0x60:0x5C};assert set(homes)==set(homes.values());regs={11:12,12:13,13:14,14:11};normalized=[];rows=[]
 for i,word in enumerate(a):
  off=i*4;at=off+(4 if off>=0x38 else 0);new=word
  if off==0x30:new=(word&~65535)|((word&65535)+1)
  if 0x40<=at<=0x70 or 0xD4<=at<=0x168:
   op=word>>26
   fields=(21,16,11)if op==0 else(16,)if op==15 else(21,16)if op in(9,35,36,43)else(21,)if op==57 else()
   if op==0:assert word&63 in(0,16,27,33,35),hex(word)
   for shift in fields:
    reg=word>>shift&31
    if reg in regs:new=(new&~(31<<shift))|(regs[reg]<<shift)
  if word>>26 in(9,35,43,57)and word>>21&31==29 and word&65535 in homes:new=(new&~65535)|homes[word&65535]
  normalized.append(new)
  inserted=None
  if off==0x34:inserted=0x8FAB0070;normalized.append(inserted)
  if new!=word or inserted is not None:rows.append(dict(offset=off,expected=word,replacement=new,insert_after=inserted))
 assert normalized==z,[(hex(i*4),hex(x),hex(y))for i,(x,y)in enumerate(zip(normalized,z))if x!=y]
 nr={k+(4 if k>=0x38 else 0):v for k,v in refs.items()};assert nr==tr
 assert[w for w in a if w>>26==17]==[w for w in z if w>>26==17]
 proof=dict(raw_words=100,normalized_words=101,frame=112,inserted_home_load_offset=0x38,inserted_home_load=0x8FAB0070,branch_delta=1,home_map=homes,GPR_cycle=regs,GPR_cycle_regions=[[0x40,0x70],[0xD4,0x168]],all_COP1_words_and_order_literal=True,all_original_call_bindings_retained_and_shifted=True,raw_private_fault_identity_not_claimed=True,raw_frame_bijection_and_extra_load_fault_relation_still_require_qualification=True,no_new_semantic_memory_access_except_duplicated_saved_owner_home=True)
 return rows,proof

def objects():
 fn=FUNCTION
 tables=(ROOT/'conker/conker.us.bin').read_bytes()[0x245A30:0x245A60];assert hashlib.sha256(tables).hexdigest()=='25684396db9786f0c69c58a9897401cc4e48a3d6777283f82f9cd3562745671a';(o/'table-presets.bin').write_bytes(tables)
 full=(b/MANIFEST['asm']).read_text();original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+fn+'\n'+full.split('glabel '+fn+'\n',1)[1].split('endlabel '+fn,1)[0]+'endlabel '+fn+'\n.size '+fn+',.-'+fn+'\n';(o/'original-target.s').write_text(original);assemble(original,o/'original-target.o')
 prepare();source=MANIFEST['selected_source'];(o/'selected-owner.c').write_text(source);(o/'semantic-source.c').write_text(source);(o/'selected-Makefile').write_bytes((b/'conker/Makefile').read_bytes());old=(b/'conker/src/game/generated_10CD70.c').read_text();objects={}
 for key,text in [('before-base',old),('before-motion','#define RETAIL_FUNC_150DFCA8 1\n'+old),('selected-base',source),('selected-motion','#define RETAIL_FUNC_150DFCA8 1\n'+source)]:
  obj,diag=plain_compile(r,o,text,key,('-O2','-g3'));assert not diag;objects[key]=obj
 assert same_functions(objects['before-base'],objects['selected-base'],(fn,))==12 and normalized_pools(objects['before-base'])==normalized_pools(objects['selected-base'])
 assert same_functions(objects['before-motion'],objects['selected-motion'],(fn,))==12 and normalized_pools(objects['before-motion'])==normalized_pools(objects['selected-motion'])
 raw,refs=payload(objects['selected-base'],fn);truth,tr=payload(o/'original-target.o',fn);rows,proof=derive(raw,refs,truth,tr);prefix=(b/'conker/retail_word_patches.us.csv').read_bytes();assert fn not in prefix.decode();fields=next(csv.reader(io.StringIO(prefix.decode())));buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in prefix[:300]else'\n');spec=lambda x:';'.join(k+':'+n for k,n in x)or'-'
 for row in rows:
  off=row['offset'];out=dict.fromkeys(fields,'');out.update(filename='generated_10CD70',function=fn,offset=hex(off),expected=hex(row['expected']),replacement=hex(row['replacement']),expected_relocations=spec(refs.get(off,[])),replacement_relocations=spec(refs.get(off,[])),note='Derived private-home bijection and closed GPR roles; restore duplicated incoming-owner load and retarget branch; COP1 sequence unchanged',omit='false')
  if row['insert_after']is not None:out.update(insert_after=hex(row['insert_after']),insert_after_relocations='-')
  writer.writerow(out)
 additions=buf.getvalue().encode();(o/'guard-additions.csv').write_bytes(additions);(o/'selected-guards.csv').write_bytes(prefix+additions);assemble(assembly(truth,tr,fn),o/'normalized-target.o');where=o/'qualified-owner';where.mkdir(exist_ok=True);outputs=[]
 for mode in('before','selected'):
  base=objects[mode+'-base'];motion=objects[mode+'-motion'];guards=b/'conker/retail_word_patches.us.csv'if mode=='before'else o/'selected-guards.csv';kw=dict(function_objects={'func_150DFCA8':motion},word_patches_path=guards,rodata_symbol='D_800A0FD0')
  for kind in('generic','generated'):
   text=restore_labels(pc.emit_padded_assembly(base,b/'conker/retail_layout.us.txt','generated_10CD70',**kw),b/'conker/asm/10CD70.s')if kind=='generic'else pg.emit_padded_assembly(base,b/'conker/asm/10CD70.s',filename='generated_10CD70',**kw);path=where/(mode+'-'+kind+'.o');assemble(text,path)
   if mode=='before':assert path.read_bytes()==(b/'conker/build/src/game/generated_10CD70.c.o').read_bytes()
   else:
    assert payload(path,fn)==(truth,tr);assert same_functions(where/('before-'+kind+'.o'),path,(fn,))==12;outputs.append(path)
 assert outputs[0].read_bytes()==outputs[1].read_bytes();syms={n:int(n.split('_',1)[1],16)for v in tr.values()for _,n in v};assert struct.pack('>101I',*bound_blob(truth,tr,syms))==(r/'conker/conker.us.bin').read_bytes()[0x10DB88:0x10DD1C]
 q=dict(words=100,normalized_words=101,retail_slot_words=102,frame=112,guards=len(rows),insertions=1,omissions=0,raw_binding_positions=17,normalized_byte_exact=True,raw_byte_exact=False,raw_and_both_profile_neighbors=12,both_complete_mixed_owner_padders_equal=True,both_before_objects_equal_frozen=True,source_sha256=sha(o/'selected-owner.c'),padded_sha256=sha(outputs[0]),structural_derivation=proof,semantic_qualification_complete=False,source_installed=installed(),matching_credit=0);(o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=="__main__":objects()
