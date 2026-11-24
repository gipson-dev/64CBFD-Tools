"""Randomized event spray; the existing five-word helper ABI remains unchanged."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads(Path(__file__).with_name('game_random_spray_150c2558_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
def installed():return sha(ROOT/MANIFEST['source'])==MANIFEST['selected_sha256']
_CHECKED=False
def prepare():
 global _CHECKED
 live=installed();allowed={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['helper_source']:MANIFEST['helper_sha256'],MANIFEST['object']:MANIFEST.get('padded_sha256'),MANIFEST['helper_object']:MANIFEST.get('helper_padded_sha256'),'conker/build/conker.us.elf':MANIFEST.get('predicted_ELF_sha256'),'conker/retail_word_patches.us.csv':MANIFEST.get('selected_guards_sha256')}
 for n,d in MANIFEST['inputs'].items():
  if not _CHECKED:
   f=OUT/'baseline'/n
   if f.is_file():assert sha(f)==d,('Frozen',n)
  if not _CHECKED or n in allowed:assert sha(ROOT/n)==(allowed.get(n,d)if live else d),('Phase',n)
 _CHECKED=True
 return live
def normalize(data,refs):
 assert data.hex()==MANIFEST['raw_hex'];assert refs=={int(k):[tuple(v)for v in a]for k,a in MANIFEST['refs'].items()}
 words=list(struct.unpack('>106I',data));v=words[:];words[38:47]=[v[46],v[38],v[40],v[41],v[39],*v[42:46]];return struct.pack('>106I',*words),refs
def proof(raw,truth):
 a,b=[list(struct.unpack('>106I',x[0]))for x in(raw,truth)];assert raw[1]==truth[1]and a[:38]==b[:38]and a[47:]==b[47:]
 def evaluate(words):
  regs=[('R',i)for i in range(32)];regs[0]=0;memory={};trace=[]
  for w in words:
   op,rs,rt=w>>26,w>>21&31,w>>16&31;imm=w&65535
   if op==15:assert rs==0;regs[rt]=imm<<16
   elif op==9:
    n=(imm^32768)-32768;regs[rt]=n&0xffffffff if rs==0 else('ADD32',regs[rs],n)
   else:
    assert rs==29 and(op,imm)in[(40,80),(41,64)];width=1 if op==40 else 2;value=('LOW'+str(width*8),regs[rt]);memory[imm]=value;trace.append((imm,width,value))
  return regs,memory,trace
 assert evaluate(a[38:47])==evaluate(b[38:47]);assert a[46]==0x3c014230 and a[47]==0x44819000
 assert not any(raw[1].get(i*4)for i in range(38,47));assert a[0]==0x27bdff60
 for i,w in enumerate(a):
  assert w>>26 not in(1,2,4,5,6,7,20,21,22,23)
  if w>>26==3:assert i+1 not in range(38,47)and i+2 not in range(38,47)
 return dict(words=106,unchanged_words=99,closed_block_words=9,changed_guard_words=7,arbitrary_register_and_private_byte_join=True,two_identical_private_store_traces=True,FPU_and_conversion_prefix_unchanged=True,arbitrary_FCSR_behavior_preserved_compositionally=True,raw_fault_prefix_identity_claim=False)
def assemble(text,path):
 f=path.with_suffix('.s');f.write_bytes(text.encode());q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(path),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
def assembly(data,refs,name=FUNCTION):
 text='.set noat\n.set noreorder\n.text\n.globl '+name+'\n.type '+name+',@function\n'+name+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',data)):
  for kind,n in refs.get(i*4,[]):text+=f'.reloc ., {kind}, {n}\n'
  text+=f'.word 0x{w:08X}\n'
 return text+'.size '+name+',.-'+name+'\n'
def objects():
 prepare();w=OUT/'selected-final';w.mkdir(exist_ok=True);b=OUT/'baseline';records={}
 # The ordinary owner has no complete original ASM slice. Give the second
 # padder the same frozen slot geometry; this is not an independent layout.
 rows=pc.load_layout(b/'conker/retail_layout.us.txt','game_EF410');retail=''
 for row in rows:
  retail+=f"glabel {row['name']}\n/* 0 {row['address']:08X} 00000000 */ nop\n"
 retail+=f"/* 0 {rows[-1]['end']-4:08X} 00000000 */ nop\n";(OUT/'retail-owner.s').write_bytes(retail.encode())
 original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+(b/MANIFEST['asm']).read_text()+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n';assemble(original,OUT/'original-target.o');truth=payload(OUT/'original-target.o',FUNCTION)
 for label,source,text,fn,filename,asm,pool,count in [('owner',MANIFEST['source'],MANIFEST['selected_source'],FUNCTION,'game_EF410',OUT/'retail-owner.s','D_800A02C0',17)]:
  old,bd=compile_owner(ROOT,w,(b/source).read_text(),label+'-before');obj,ad=compile_owner(ROOT,w,text,label+'-candidate');assert same_functions(old,obj,(fn,))==count;assert diagnostic_rows(bd)==diagnostic_rows(ad)
  (w/('selected-'+label+'.c')).write_bytes(text.encode())
  if label=='owner':
   raw=payload(obj,fn);assert normalize(*raw)==truth;relation=proof(raw,truth);head=(b/'conker/retail_word_patches.us.csv').read_bytes();buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=next(csv.reader(io.StringIO(head.decode()))),lineterminator='\n');x=struct.unpack('>106I',raw[0]);y=struct.unpack('>106I',truth[0])
   for i in (38,39,42,43,44,45,46):writer.writerow(dict(filename=filename,function=fn,offset=hex(i*4),expected=hex(x[i]),replacement=hex(y[i]),expected_relocations='-',replacement_relocations='-',note='Normalize proved closed constant-load scheduling block for randomized spray descriptor',insert_after='',insert_after_relocations='',omit='false'))
   suffix=buf.getvalue().encode();(OUT/'guard-suffix.csv').write_bytes(suffix);(OUT/'private-guards.csv').write_bytes(head+suffix)
   if 'selected_guards_sha256'in MANIFEST:assert sha(OUT/'private-guards.csv')==MANIFEST['selected_guards_sha256']
  else:assert payload(obj,fn)==(bytes.fromhex(MANIFEST['helper_hex']),{})
  guard=OUT/'private-guards.csv';where=OUT/('qualified-'+label);where.mkdir(exist_ok=True);out=[]
  for kind,s in [('generic',pc.emit_padded_assembly(obj,b/'conker/retail_layout.us.txt',filename,rodata_symbol=pool,word_patches_path=guard)),('generated',pg.emit_padded_assembly(obj,asm,filename=filename,rodata_symbol=pool,word_patches_path=guard))]:
   p=where/(kind+'.o');assemble(s,p);assert same_functions(b/('conker/build/'+source.removeprefix('conker/')+'.o'),p,(fn,))==count;assert normalized_pools(p)==normalized_pools(b/('conker/build/'+source.removeprefix('conker/')+'.o'));assert payload(p,fn)==(truth if label=='owner'else payload(obj,fn));out.append(p)
  assert pg.parse_object(out[0])==pg.parse_object(out[1]);records[label]=dict(neighbors=count,padded_sha256=sha(out[0]),raw_words=len(payload(obj,fn)[0])//4,both_padders_equal=True)
 q=dict(records=records,relation=relation,source_installed=installed(),matching_credit=0);(OUT/'objects.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
if __name__=='__main__':objects()
