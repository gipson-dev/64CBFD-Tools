"""Record query with explicit vector forwarding and bounded private-frame proof."""
from pathlib import Path
from collections import Counter
import csv,hashlib,io,json,os,struct,subprocess,sys
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();TOOLROOT=Path(__file__).resolve().parents[1];MANIFEST=json.loads(Path(__file__).with_name('game_resource_record_query_150eb484_manifest.json').read_bytes());OUT=ROOT/MANIFEST['build'];FUNCTION=MANIFEST['function'];ENTRY=0x150eb484;ROM=0x118934;WORDS=100;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
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
 live=installed();allowed={'conker/Makefile':MANIFEST['selected_Makefile_sha256'],MANIFEST['source']:MANIFEST['selected_sha256'],'conker/retail_word_patches.us.csv':MANIFEST['selected_guards_sha256'],MANIFEST['object']:MANIFEST.get('padded_sha256'),MANIFEST['gate_source']:MANIFEST['selected_gate_sha256'],MANIFEST['gate_object']:MANIFEST['gate_padded_sha256'],'conker/build/conker.us.elf':MANIFEST.get('predicted_ELF_sha256')}
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
 prepare();r=ROOT;o=OUT;b=o/"baseline"
 full=(b/MANIFEST['asm']).read_text();original='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+FUNCTION+'\n'+full.split('glabel '+FUNCTION+'\n',1)[1].split('endlabel '+FUNCTION,1)[0]+'endlabel '+FUNCTION+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n';(o/'func_150EB484-original.s').write_text(original);assemble(original,o/'original-target.o')
 for wrapper,owner in [('func_150EB430','1188E0'),('func_150A34B0','CDE80')]:
  full=(b/('conker/asm/'+owner+'.s')).read_text();text='.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+wrapper+'\n'+full.split('glabel '+wrapper+'\n',1)[1].split('endlabel '+wrapper,1)[0]+'endlabel '+wrapper+'\n.size '+wrapper+',.-'+wrapper+'\n';assemble(text,o/(wrapper+'-original.o'))
 source=MANIFEST['selected_source'];(o/'selected-owner.c').write_text(source);(o/'selected-gate-owner.c').write_text(MANIFEST['selected_gate_source']);(o/'selected-Makefile').write_text(MANIFEST['selected_Makefile_text'])
 obj,diag=compile_owner(r,o,source,'selected-owner');assert not diag
 assert normalize(*payload(obj,FUNCTION))==payload(o/'original-target.o',FUNCTION)
 raw,refs=payload(obj,'func_150EB484');truth,tr=payload(o/'original-target.o','func_150EB484');assert len(raw)==len(truth)==400
 a,z=struct.unpack('>100I',raw),struct.unpack('>100I',truth);pins=[i for i in range(100)if a[i]!=z[i]or refs.get(4*i,[])!=tr.get(4*i,[])];assert len(pins)==23
 enc=lambda v:';'.join(k+':'+n for k,n in v)or'-';stream=io.StringIO();writer=csv.writer(stream,lineterminator='\n')
 for i in pins:writer.writerow(['generated_1188E0','func_150EB484',hex(4*i),'0x%08X'%a[i],'0x%08X'%z[i],enc(refs.get(4*i,[])),enc(tr.get(4*i,[])),'Normalize private 72 to 80 byte frame saved register allocation and independent scheduling','','','false'])
 addition=stream.getvalue();lines=(b/'conker/retail_word_patches.us.csv').read_text().splitlines(keepends=True);retired=[s for s in lines if s.split(',')[1:2]==['func_150EB430']];assert len(retired)==4
 assert not any('func_150EB484,'in s for s in lines)
 (o/'retired-guards.csv').write_text(''.join(retired));(o/'guard-additions.csv').write_text(addition);(o/'selected-guards.csv').write_text(''.join(s for s in lines if s not in retired)+addition)
 assemble(assembly(truth,tr,'func_150EB484'),o/'normalized-target.o');where=o/'qualified-owner';where.mkdir(exist_ok=True);reports=[]
 for owner,selected,changed in [('1188E0',source,('func_150EB430','func_150EB484','func_150EBC80')),('CDE80',(o/'selected-gate-owner.c').read_text(),('func_150A34B0','func_150A3504'))]:
  old,bd=compile_owner(r,o,(b/('conker/src/game/generated_'+owner+'.c')).read_text(),'selected-before-'+owner);new,ad=compile_owner(r,o,selected,'selected-'+owner);assert not bd and not ad
  neighbors=same_functions(old,new,changed);assert normalized_pools(old)==normalized_pools(new);retail=b/('conker/asm/'+owner+'.s');filename='generated_'+owner;outputs=[]
  for label,emit in [('generic',lambda f,g:restore_labels(pc.emit_padded_assembly(f,b/'conker/retail_layout.us.txt',filename,word_patches_path=g),retail)),('generated',lambda f,g:pg.emit_padded_assembly(f,retail,filename=filename,word_patches_path=g))]:
   before=where/(owner+'-'+label+'-before.o');assemble(emit(old,b/'conker/retail_word_patches.us.csv'),before);assert before.read_bytes()==(b/('conker/build/src/game/'+filename+'.c.o')).read_bytes()
   out=where/(owner+'-'+label+'.o');assemble(emit(new,o/'selected-guards.csv'),out);assert same_functions(before,out,changed)==neighbors and normalized_pools(before)==normalized_pools(out);outputs.append(out)
  assert outputs[0].read_bytes()==outputs[1].read_bytes()
  for fn in changed:
   if fn in ('func_150EB430','func_150A34B0'):assert payload(new,fn)==payload(o/(fn+'-original.o'),fn)
   if fn=='func_150EB484':assert payload(outputs[0],fn)==(truth,tr)
  reports.append(dict(owner=owner,raw_neighbors=neighbors,padded_neighbors=neighbors,raw_and_padded_pools_unchanged=True,both_complete_padders_equal=True,changed_functions=list(changed),padded_sha256=sha(outputs[0])))
 q=dict(words=100,raw_frame=72,normalized_frame=80,guards=23,direct_words=77,retired_wrapper_guards=4,owners=reports,source_installed=installed(),matching_credit=0)
 (o/'objects.json').write_text(json.dumps(q,indent=2)+'\n');(o/'word-differences.json').write_text(json.dumps([dict(offset=hex(i*4),raw=hex(a[i]),retail=hex(z[i]),raw_refs=refs.get(4*i,[]),retail_refs=tr.get(4*i,[]))for i in pins],indent=2)+'\n');print(json.dumps(q),flush=True)
 return q
if __name__=="__main__":objects()
