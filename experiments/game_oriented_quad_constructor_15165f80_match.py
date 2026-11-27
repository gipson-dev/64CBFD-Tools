"""Two-quad constructor with two closed GPR swaps and byte-fixed caller owners."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_oriented_quad_constructor_15165f80_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x15165F80;ROM=0x193430;WORDS=102
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
 allowed.update({n:v['selected_sha256']for n,v in MANIFEST['dependent_sources'].items()})
 for n,d in MANIFEST['inputs'].items():
  if not _CHECKED and(OUT/'baseline'/n).is_file():assert sha(OUT/'baseline'/n)==d,('Frozen',n)
  if not _CHECKED or n in allowed:assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase',n)
 assert sha(ROOT/'conker/retail_word_patches.us.csv')==(MANIFEST['guards_sha256'] if live else MANIFEST['inputs']['conker/retail_word_patches.us.csv']);_CHECKED=True;return live



import shlex
fn=FUNCTION;owner=MANIFEST['filename']

def prototypes():
 where=o/'caller-prototypes';where.mkdir(exist_ok=True);reports=[]
 for name in('105760','E7970','E8090'):
  filename='generated_'+name;source='src/game/'+filename+'.c';old=(b/'conker'/source).read_text();decl='s32 func_15165F80(s32, s32, s32, s32, s32, s32, s32, u8, s32);';assert old.count(decl)==1;new=old.replace(decl,decl.replace('s32 func_','void func_',1));before,diag=compile_owner(r,where,old,name+'-before');assert not diag;after,diag=compile_owner(r,where,new,name+'-selected');assert not diag;count=len(pg.parse_object(before)[1]);assert same_functions(before,after,())==count and normalized_pools(before)==normalized_pools(after)
  for mode,obj in(('before',before),('selected',after)):
   for kind in('generic','generated'):
    text=restore_labels(pc.emit_padded_assembly(obj,b/'conker/retail_layout.us.txt',filename,word_patches_path=b/'conker/retail_word_patches.us.csv'),b/'conker/asm'/(name+'.s'))if kind=='generic'else pg.emit_padded_assembly(obj,b/'conker/asm'/(name+'.s'),filename=filename,word_patches_path=b/'conker/retail_word_patches.us.csv');asm=where/(name+'-'+mode+'-'+kind+'.s');out=asm.with_suffix('.o');asm.write_text(text);p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(out),str(asm)],capture_output=True,text=True);assert p.returncode==0,p.stderr;assert out.read_bytes()==(b/'conker/build'/ (source+'.o')).read_bytes()
  c=r/'conker';shadow=where/('Make-'+name);target=shadow/(source+'.o');target.parent.mkdir(parents=True,exist_ok=True);p=subprocess.run(['make','-f','Makefile','-n','-B','-o','Makefile','BUILD_DIR='+shadow.relative_to(c).as_posix(),target.relative_to(c).as_posix()],cwd=c,capture_output=True,text=True);assert p.returncode==0,p.stderr;commands=[]
  for line in p.stdout.replace('\\\n','').splitlines():
   args=shlex.split(line)
   if not args or args[0]=='rm':continue
   assert args[0]in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'),args
   args=[str(TOOLROOT/a.removeprefix('../tools/'))if a.startswith('../tools/')else(where/(name+'-selected.c')).relative_to(c).as_posix()if a==source else(b/'conker/retail_word_patches.us.csv').relative_to(c).as_posix()if a=='retail_word_patches.us.csv'else a for a in args];q=subprocess.run(args,cwd=c,capture_output=True,text=True);assert q.returncode==0 and not(q.stdout or q.stderr),(args,q.stdout,q.stderr);commands.append(args)
  assert len(commands)==3 and target.read_bytes()==(b/'conker/build'/(source+'.o')).read_bytes();reports.append(dict(source='conker/'+source,functions=count,all_raw_functions_bindings_pools_fixed=True,both_before_and_after_complete_padders_equal_frozen=True,actual_Make_commands=3,whole_object_unchanged=True,object_sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
 q=dict(owners=reports,prototypes_corrected_to_void=3,all_dependent_objects_byte_identical=True,source_installed=installed(),matching_credit=0);(o/'prototypes.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
def assemble(s,path):
 f=path.with_suffix('.s');f.write_text(s);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(r/'conker/include'),'-o',str(path),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr

def derive(raw,refs,truth,tr):
 a=list(struct.unpack('>102I',raw));z=list(struct.unpack('>102I',truth));assert a[0]==z[0]==0x27BDFFC8 and refs==tr and len(refs)==6;rows=[];normalized=[]
 for i,word in enumerate(a):
  off=i*4;new=word;cycle={4:5,5:4}if 0x54<=off<=0x88 else{2:3,3:2}if 0x108<=off<=0x140 else{}
  if cycle:
   op=word>>26;fields=(21,16,11)if op==0 else(21,16)if op in(5,9,40,41)else();assert op in(0,5,9,40,41),hex(word)
   for shift in fields:
    reg=word>>shift&31
    if reg in cycle:new=(new&~(31<<shift))|(cycle[reg]<<shift)
  normalized.append(new)
  if new!=word:rows.append(dict(offset=off,expected=word,replacement=new))
 assert normalized==z and len(rows)==15,[(hex(i*4),hex(x),hex(y))for i,(x,y)in enumerate(zip(normalized,z))if x!=y];assert[w for w in a if w>>26==17]==[w for w in z if w>>26==17]
 return rows

def objects():
 prepare()
 full=(b/MANIFEST['asm']).read_text();original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+fn+'\n'+full.split('glabel '+fn+'\n',1)[1].split('endlabel '+fn,1)[0]+'endlabel '+fn+'\n.size '+fn+',.-'+fn+'\n';(o/'original-target.s').write_text(original);assemble(original,o/'original-target.o');prototypes()
 prepare();source=MANIFEST['selected_source'];(o/'selected-owner.c').write_text(source);(o/'semantic-source.c').write_text(source);(o/'selected-Makefile').write_bytes((b/'conker/Makefile').read_bytes());old=(b/'conker/src/game/generated_193430.c').read_text();before,diag=compile_owner(r,o,old,'before-owner');assert not diag;selected,diag=compile_owner(r,o,source,'selected-owner');assert not diag;assert same_functions(before,selected,(fn,))==4 and normalized_pools(before)==normalized_pools(selected)
 raw,refs=payload(selected,fn);truth,tr=payload(o/'original-target.o',fn);rows=derive(raw,refs,truth,tr);prefix=(b/'conker/retail_word_patches.us.csv').read_bytes();assert fn not in prefix.decode();fields=next(csv.reader(io.StringIO(prefix.decode())));buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in prefix[:300]else'\n')
 for row in rows:
  off=row['offset'];assert off not in refs;out=dict.fromkeys(fields,'');out.update(filename=owner,function=fn,offset=hex(off),expected=hex(row['expected']),replacement=hex(row['replacement']),expected_relocations='-',replacement_relocations='-',note='Normalize two closed quad-loop GPR swaps; all FP words, stack accesses and instruction order unchanged',omit='false');writer.writerow(out)
 additions=buf.getvalue().encode();(o/'guard-additions.csv').write_bytes(additions);(o/'selected-guards.csv').write_bytes(prefix+additions);assemble(assembly(truth,tr,fn),o/'normalized-target.o');where=o/'qualified-owner';where.mkdir(exist_ok=True);outputs=[]
 for mode,obj in[('before',before),('selected',selected)]:
  guards=b/'conker/retail_word_patches.us.csv'if mode=='before'else o/'selected-guards.csv'
  for kind in('generic','generated'):
   text=restore_labels(pc.emit_padded_assembly(obj,b/'conker/retail_layout.us.txt',owner,word_patches_path=guards),b/'conker/asm/193430.s')if kind=='generic'else pg.emit_padded_assembly(obj,b/'conker/asm/193430.s',filename=owner,word_patches_path=guards);path=where/(mode+'-'+kind+'.o');assemble(text,path)
   if mode=='before':assert path.read_bytes()==(b/'conker/build/src/game/generated_193430.c.o').read_bytes()
   else:assert payload(path,fn)==(truth,tr)and same_functions(where/('before-'+kind+'.o'),path,(fn,))==4;outputs.append(path)
 assert outputs[0].read_bytes()==outputs[1].read_bytes();syms={n:int(n.split('_',1)[1],16)if n.startswith(('D_','func_'))else{'sinf':0x15047D60,'cosf':0x15047C00}[n]for v in tr.values()for _,n in v};assert struct.pack('>102I',*bound_blob(truth,tr,syms))==(r/'conker/conker.us.bin').read_bytes()[0x193430:0x1935C8]
 q=dict(words=102,normalized_words=102,retail_slot_words=102,frame=56,guards=15,insertions=0,omissions=0,raw_binding_positions=6,normalized_byte_exact=True,raw_byte_exact=False,raw_direct_words=87,raw_neighbors=4,both_complete_padders_equal=True,both_before_objects_equal_frozen=True,all_FP_words_and_order_literal=True,all_stack_access_instructions_literal=True,GPR_swaps=[dict(region=[0x54,0x88],registers=[4,5]),dict(region=[0x108,0x140],registers=[2,3])],source_sha256=sha(o/'selected-owner.c'),padded_sha256=sha(outputs[0]),semantic_qualification_complete=False,source_installed=installed(),matching_credit=0);(o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=="__main__":objects()
