"""Semantic ring constructor, bounded header-schedule normalization and owner audit."""
from pathlib import Path
from collections import Counter
import csv,hashlib,io,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_ring_effect_150c88d0_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x150c88d0;ROM=0xf5d80;WORDS=102;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
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
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],'conker/retail_word_patches.us.csv':MANIFEST['selected_guards_sha256'],MANIFEST['object']:MANIFEST.get('padded_sha256'),'conker/build/conker.us.elf':MANIFEST.get('predicted_ELF_sha256')}
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
def tokens(data,refs):
 result=[]
 for i,(w,)in enumerate(struct.iter_unpack('>I',data)):
  if i==16:assert w in(0x01d27821,0x024e7821);w=0x024e7821
  v=('branch',w>>16,i+1+((w&65535)^32768)-32768)if w>>26 in(4,5,6,7,20,21,22,23)else('word',w)
  result.append((v,tuple(refs.get(4*i,[]))))
 return Counter(result)
def objects():
 prepare();w=OUT/'selected-final';w.mkdir(exist_ok=True);b=OUT/'baseline';source=MANIFEST['source'];fn=FUNCTION;guard=OUT/'selected-guards.csv';assert guard.read_bytes()==(b/'conker/retail_word_patches.us.csv').read_bytes()+MANIFEST['guard_additions'].encode();assert sha(guard)==MANIFEST['selected_guards_sha256']
 old,bd=compile_owner(ROOT,w,(b/source).read_text(),'owner-before');obj,ad=compile_owner(ROOT,w,MANIFEST['selected_source'],'owner-candidate');assert not bd and not ad;neighbors=same_functions(old,obj,(fn,));assert normalized_pools(old)==normalized_pools(obj)
 full=(b/MANIFEST['asm']).read_text();original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+fn+full.split('glabel '+fn,1)[1].split('endlabel '+fn,1)[0]+'endlabel '+fn+'\n.size '+fn+',.-'+fn+'\n';assemble(original,OUT/'original-target.o');truth=payload(OUT/'original-target.o',fn);raw=payload(obj,fn);assert normalize(*raw)==truth;assert tokens(*raw)==tokens(*truth);assert int.from_bytes(raw[0][:4],'big')==0x27bdffc8
 assemble(assembly(*normalize(*raw)),OUT/'normalized-target.o');(w/'selected-owner.c').write_bytes(MANIFEST['selected_source'].encode());(OUT/'selected-Makefile').write_bytes((b/'conker/Makefile').read_bytes());where=OUT/'qualified-owner';where.mkdir(exist_ok=True);outputs=[]
 for label,emitter in [('generic',lambda f,g:pc.emit_padded_assembly(f,b/'conker/retail_layout.us.txt',MANIFEST['filename'],word_patches_path=g)),('generated',lambda f,g:pg.emit_padded_assembly(f,b/MANIFEST['asm'],filename=MANIFEST['filename'],word_patches_path=g))]:
  before=where/(label+'-before.o');assemble(emitter(old,b/'conker/retail_word_patches.us.csv'),before);assert before.read_bytes()==(b/MANIFEST['object']).read_bytes();out=where/(label+'.o');assemble(emitter(obj,guard),out);assert payload(out,fn)==truth;assert same_functions(b/MANIFEST['object'],out,(fn,))==neighbors;assert normalized_pools(out)==normalized_pools(b/MANIFEST['object']);outputs.append(out)
 assert outputs[0].read_bytes()==outputs[1].read_bytes();q=dict(words=102,frame=56,guards=22,insertions=0,omissions=0,instruction_multiset_preserved=True,raw_direct_words=80,padded_sha256=sha(outputs[0]),neighbors=neighbors,both_padders_equal=True,no_pool_change=True,source_installed=installed(),matching_credit=0);(OUT/'objects.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':objects()
