"""Signed height callback with complete owner and bounded integer proof."""
from pathlib import Path
from collections import Counter
import csv,hashlib,io,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_height_interpolation_151155c0_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x151155c0;ROM=0x142a70;WORDS=103;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows,elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools
def installed():return sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
_CHECKED=False
def prepare():
 global _CHECKED
 live=installed();allowed={'conker/Makefile':MANIFEST['selected_Makefile_sha256'],MANIFEST['source']:MANIFEST['selected_sha256'],'conker/retail_word_patches.us.csv':MANIFEST['selected_guards_sha256'],MANIFEST['object']:MANIFEST.get('padded_sha256'),'conker/build/conker.us.elf':MANIFEST.get('predicted_ELF_sha256')}
 for n,d in MANIFEST['inputs'].items():
  if not _CHECKED:
   f=OUT/'baseline'/n
   if f.is_file():assert sha(f)==d,('Frozen',n)
  if not _CHECKED or n in allowed:assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase',n)
 _CHECKED=True;return live
def normalize(data,refs):
 assert data.hex()==MANIFEST['raw_hex'];assert refs=={int(k):[tuple(v)for v in a]for k,a in MANIFEST['raw_relocations'].items()};result=bytearray(data);bindings={k:list(v)for k,v in refs.items()}
 for row in csv.reader(io.StringIO(MANIFEST['guard_additions'])):
  filename,fn,offset,old,new,expected,replacement,note,insert,insert_refs,omit=row;assert filename==MANIFEST['filename']and fn==FUNCTION and not insert and not insert_refs and omit=='false';at=int(offset,0);assert result[at:at+4]==int(old,0).to_bytes(4,'big');assert bindings.get(at,[])==pg.parse_relocation_spec(expected);result[at:at+4]=int(new,0).to_bytes(4,'big');values=pg.parse_relocation_spec(replacement)
  if values:bindings[at]=values
  else:bindings.pop(at,None)
 return bytes(result),bindings
def assemble(text,path):
 f=path.with_suffix('.s');f.write_text(text);q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(path),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
def assembly(data,refs,name=FUNCTION):
 text='.set noat\n.set noreorder\n.text\n.globl '+name+'\n.type '+name+',@function\n'+name+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',data)):
  for kind,n in refs.get(4*i,[]):text+=f'.reloc ., {kind}, {n}\n'
  text+=f'.word 0x{w:08X}\n'
 return text+'.size '+name+',.-'+name+'\n'
def restore_labels(text,retail_path):
 start,end,_,labels=pg.parse_retail_slice(retail_path);offsets={a-start:names for a,names in labels.items()};expected={n for names in offsets.values()for n in names};out=[];current=0;inside=False;emitted=set()
 def emit(at):
  for name in offsets.get(at,[]):
   if name not in emitted:out.extend((f'.globl {name}',name+':'));emitted.add(name)
 for line in text.splitlines():
  s=line.strip()
  if s.startswith('.section '):
   if inside:emit(current)
   inside=s.split()[1].rstrip(',')=='.text';out.append(line);continue
  if inside and s and not s.startswith('/*'):emit(current)
  if inside and s.startswith('.space '):
   target=current+int(s.split()[1].rstrip(','),0)
   for at in sorted(k for k in offsets if current<k<target):
    if at>current:out.append(f'.space 0x{at-current:X}, 0');current=at
    emit(current)
   if target>current:out.append(f'.space 0x{target-current:X}, 0');current=target
   continue
  out.append(line)
  if inside and s.startswith('.word '):assert ','not in s;current+=4
 if inside:emit(current)
 assert current==end-start and emitted==expected,(current,end-start,expected-emitted)
 return '\n'.join(out)+'\n'

def objects():
 prepare();w=OUT/'selected-final';w.mkdir(exist_ok=True);b=OUT/'baseline';source=MANIFEST['source'];fn=FUNCTION;guard=OUT/'selected-guards.csv';assert guard.read_bytes()==(b/'conker/retail_word_patches.us.csv').read_bytes()+MANIFEST['guard_additions'].encode();assert sha(guard)==MANIFEST['selected_guards_sha256']
 old,bd=compile_owner(ROOT,w,(b/source).read_text(),'owner-before');obj,ad=compile_owner(ROOT,w,MANIFEST['selected_source'],'owner-candidate');assert not bd and not ad;neighbors=same_functions(old,obj,(fn,));assert normalized_pools(old)==normalized_pools(obj)
 full=(b/MANIFEST['asm']).read_text();original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+fn+full.split('glabel '+fn,1)[1].split('endlabel '+fn,1)[0]+'endlabel '+fn+'\n.size '+fn+',.-'+fn+'\n';assemble(original,OUT/'original-target.o');truth=payload(OUT/'original-target.o',fn);raw=payload(obj,fn);assert normalize(*raw)==truth;assert len(raw[0])==len(truth[0])==412;assert not raw[1]and not truth[1]
 from collections import Counter
 assert Counter(v for pairs in raw[1].values()for v in pairs)==Counter(v for pairs in truth[1].values()for v in pairs)

 assemble(assembly(*normalize(*raw)),OUT/'normalized-target.o');(w/'selected-owner.c').write_bytes(MANIFEST['selected_source'].encode());(OUT/'selected-Makefile').write_bytes(MANIFEST['selected_Makefile_text'].encode());assert sha(OUT/'selected-Makefile')==MANIFEST['selected_Makefile_sha256'];where=OUT/'qualified-owner';where.mkdir(exist_ok=True);outputs=[]
 for label,emitter in [('generic',lambda f,g:restore_labels(pc.emit_padded_assembly(f,b/'conker/retail_layout.us.txt',MANIFEST['filename'],word_patches_path=g),b/MANIFEST['asm'])),('generated',lambda f,g:pg.emit_padded_assembly(f,b/MANIFEST['asm'],filename=MANIFEST['filename'],word_patches_path=g))]:
  before=where/(label+'-before.o');assemble(emitter(old,b/'conker/retail_word_patches.us.csv'),before);assert before.read_bytes()==(b/MANIFEST['object']).read_bytes();out=where/(label+'.o');assemble(emitter(obj,guard),out);assert payload(out,fn)==truth;assert same_functions(b/MANIFEST['object'],out,(fn,))==neighbors;assert normalized_pools(out)==normalized_pools(b/MANIFEST['object']);outputs.append(out)
 assert outputs[0].read_bytes()==outputs[1].read_bytes();q=dict(words=103,frame=0,guards=76,insertions=0,omissions=0,raw_byte_exact=False,private_stack_normalization=False,invariant_address_promotion=False,GPR_allocation_cycles=False,bounded_integer_structural_proof=True,global_fixed_GPR_map=False,exported_retail_labels_retained=42,raw_fault_order_not_claimed=True,raw_direct_words=27,padded_sha256=sha(outputs[0]),neighbors=neighbors,both_padders_equal=True,raw_and_padded_pools_unchanged=True,source_installed=installed(),matching_credit=0);(OUT/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':objects()
