"""Direct point spray C; sealed float pool, both padders and owner neighbors."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads(Path(__file__).with_name('game_point_spray_150c71c0_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.check_point_spray_150c71c0_pool import verify
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows,elf_slot_offset
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
ENTRY=0x150c71c0;ROM=0xf4670;WORDS=99
def installed():return sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
_CHECKED=False
def prepare():
 global _CHECKED
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],'conker/Makefile':MANIFEST['selected_Makefile_sha256'],MANIFEST['object']:MANIFEST.get('padded_sha256'),'conker/build/conker.us.elf':MANIFEST.get('predicted_ELF_sha256')}
 for n,d in MANIFEST['inputs'].items():
  if not _CHECKED:
   f=OUT/'baseline'/n
   if f.is_file():assert sha(f)==d,('Frozen',n)
  if not _CHECKED or n in allowed:assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase',n)
 _CHECKED=True;return live
def normalize(data,refs):
 assert data.hex()==MANIFEST['raw_hex'];assert refs=={int(k):[tuple(v)for v in a]for k,a in MANIFEST['raw_relocations'].items()}
 return data,{k:[(kind,'D_800A0494'if n=='.rodata'else n)for kind,n in a]for k,a in refs.items()}
def assemble(text,path):
 f=path.with_suffix('.s');f.write_bytes(text.encode());q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(path),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
def assembly(data,refs,name=FUNCTION):
 text='.set noat\n.set noreorder\n.text\n.globl '+name+'\n.type '+name+',@function\n'+name+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',data)):
  for kind,n in refs.get(i*4,[]):text+=f'.reloc ., {kind}, {n}\n'
  text+=f'.word 0x{w:08X}\n'
 return text+'.size '+name+',.-'+name+'\n'
def objects():
 prepare();w=OUT/'selected-final';w.mkdir(exist_ok=True);b=OUT/'baseline';source=MANIFEST['source'];fn=FUNCTION;guards=b/'conker/retail_word_patches.us.csv';assert guards.read_bytes()==(ROOT/'conker/retail_word_patches.us.csv').read_bytes()
 old,bd=compile_owner(ROOT,w,(b/source).read_text(),'owner-before');obj,ad=compile_owner(ROOT,w,MANIFEST['selected_source'],'owner-candidate');assert diagnostic_rows(bd)==diagnostic_rows(ad);assert same_functions(old,obj,(fn,))==1;pool=verify(obj)
 full=(b/MANIFEST['asm']).read_text();original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+fn+full.split('glabel '+fn,1)[1].split('endlabel '+fn,1)[0]+'endlabel '+fn+'\n.size '+fn+',.-'+fn+'\n';assemble(original,OUT/'original-target.o');truth=payload(OUT/'original-target.o',fn);assert normalize(*payload(obj,fn))==truth
 syms={n:v[1]for _,n,v,_ in symbol_rows((b/'conker/build/conker.us.elf').read_bytes())if n};at=elf_slot_offset((b/'conker/build/conker.us.elf').read_bytes(),0x800a0494,4);assert(b/'conker/build/conker.us.elf').read_bytes()[at:at+4]==bytes.fromhex('3ed0624e');assert(ROOT/'conker/conker.us.bin').read_bytes()[0x244f54:0x244f58]==bytes.fromhex('3ed0624e')
 (w/'selected-owner.c').write_bytes(MANIFEST['selected_source'].encode());(OUT/'selected-Makefile').write_bytes(MANIFEST['selected_Makefile'].encode());where=OUT/'qualified-owner';where.mkdir(exist_ok=True);outputs=[]
 for label,emitter in [('generic',lambda raw:pc.emit_padded_assembly(raw,b/'conker/retail_layout.us.txt',MANIFEST['filename'],rodata_symbol='D_800A0494',word_patches_path=guards)),('generated',lambda raw:pg.emit_padded_assembly(raw,b/MANIFEST['asm'],filename=MANIFEST['filename'],rodata_symbol='D_800A0494',word_patches_path=guards))]:
  before=where/(label+'-before.o');assemble(emitter(old),before);assert before.read_bytes()==(b/MANIFEST['object']).read_bytes()
  out=where/(label+'.o');assemble(emitter(obj),out);assert payload(out,fn)==truth;assert same_functions(b/MANIFEST['object'],out,(fn,))==1;assert normalized_pools(out)==normalized_pools(b/MANIFEST['object']);outputs.append(out)
  text,functions,_=pg.parse_object(out);f=functions[fn];assert f['size']==396 and text[f['value']+396:f['value']+400]==bytes(4)
 assert outputs[0].read_bytes()==outputs[1].read_bytes();q=dict(words=99,retail_slot_words=100,retail_padding_bytes=4,frame=96,guards=0,raw_normalized_bindings_equal_original=True,padded_sha256=sha(outputs[0]),neighbors=1,both_padders_equal=True,literal_pool=pool,source_installed=installed(),matching_credit=0);(OUT/'objects.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
if __name__=='__main__':objects()
