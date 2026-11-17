"""Independent original assembly, all-word guards, complete owner padders/rebases."""
from tools.experiments import game_region_emitter_151a5660_recovery as m
from pathlib import Path
import csv,hashlib,io,json,struct,subprocess,sys
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_actor_classifier_candidates import sections
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
R=m.ROOT;O=m.OUT;F=m.FROZEN;N=m.NAME;OWNER='generated_1D2B10';SIZE=m.SIZE
def assemble(text,label):
 label='v2-'+label
 p=O/(label+'.s');obj=p.with_suffix('.o');assert not p.exists();p.write_text(text)
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(p)],cwd=R/'conker',capture_output=True,text=True)
 assert q.returncode==0 and not q.stderr,q.stderr;return obj
def normalize(raw,refs):
 assert hashlib.sha256(raw).hexdigest()==m.PIN['raw_sha256']
 assert refs=={int(k):[tuple(v)for v in values]for k,values in m.PIN['refs'].items()}
 result=bytearray(raw);rows=m.PIN['guard_rows'];assert len(rows)==47
 for row in rows:
  off=int(row['offset'],0);assert off not in refs and struct.unpack_from('>I',result,off)[0]==int(row['expected'],0)
  assert row['omit']=='false'and not row['insert_after']and not row['insert_after_relocations']
  struct.pack_into('>I',result,off,int(row['replacement'],0))
 assert hashlib.sha256(result).hexdigest()==m.PIN['normalized_sha256']
 return bytes(result),dict(refs)
def main():
 dest=O/'guard-qualification.json';assert not dest.exists()
 m.check_inputs()
 raw,refs=payload(O/'qualified.o',N);compiled=m.PIN;assert hashlib.sha256(raw).hexdigest()==compiled['raw_sha256']
 reference=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+N+'\n'+(O/'retail.s').read_text()+'\n.size '+N+', .-'+N+'\n','region-original-reference')
 normal,nrefs=payload(reference,N);assert len(normal)==len(raw)==SIZE and nrefs==refs
 symbols={r[1]:r[2][1]for r in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())}
 assert struct.pack('>403I',*bound_blob(normal,nrefs,symbols))==(O/'retail.bin').read_bytes()
 old=(F/'conker/retail_word_patches.us.csv').read_bytes();assert(R/'conker/retail_word_patches.us.csv').read_bytes()in(old,(m.ADOPTION/'proposed-guards.csv').read_bytes())if m.installed()else(R/'conker/retail_word_patches.us.csv').read_bytes()==old
 header=next(csv.reader(io.StringIO(old.decode())));rows=[]
 for off in range(0,SIZE,4):
  a,b=struct.unpack_from('>I',raw,off)[0],struct.unpack_from('>I',normal,off)[0]
  if a==b:continue
  assert off not in refs and off not in nrefs
  row={k:''for k in header};row.update(filename=OWNER,function=N,offset='0x%03X'%off,expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',note='Normalize region-sampling register roles and independent schedule',omit='false')
  if off in(0x264,0x298):row['note']='Restore ordered region-offset multiply operands'
  elif 0x498<=off<0x4B8:row['note']='Normalize proved binary height-result test and branch-delay fallback'
  rows.append(row)
 assert len(rows)==47 and all(row['function']!=N for row in csv.DictReader(io.StringIO(old.decode())))
 stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=header,lineterminator='\n').writerows(rows)
 proposed=O/'proposed-guards.csv';assert not proposed.exists();proposed.write_bytes(old+stream.getvalue().encode())
 plan=dict(raw_sha256=hashlib.sha256(raw).hexdigest(),normalized_sha256=hashlib.sha256(normal).hexdigest(),refs={str(k):v for k,v in refs.items()},guard_rows=rows,source_label='v39')
 (O/'proposed-match-manifest.json').write_text(json.dumps(plan,indent=2)+'\n')
 def normalize(candidate,bindings):
  assert hashlib.sha256(candidate).hexdigest()==plan['raw_sha256']and bindings==refs
  result=bytearray(candidate)
  for row in rows:
   off=int(row['offset'],0);assert struct.unpack_from('>I',result,off)[0]==int(row['expected'],0)
   struct.pack_into('>I',result,off,int(row['replacement'],0))
  assert bytes(result)==normal;return bytes(result),dict(bindings)
 assert normalize(raw,refs)==(normal,nrefs)
 emitters=(lambda path:pg.emit_padded_assembly(O/'qualified.o',R/'conker/asm/1D2B10.s',filename=OWNER,word_patches_path=path),lambda path:pc.emit_padded_assembly(O/'qualified.o',R/'conker/retail_layout.us.txt',OWNER,word_patches_path=path))
 objects=[]
 for name,emit in zip(('strict','layout'),emitters):
  obj=assemble(emit(proposed),'region-'+name+'-padded');objects.append(obj);assert payload(obj,N)==(normal,nrefs)
  baseline=F/'conker/build/src/game/generated_1D2B10.c.o'
  assert same_functions(baseline,obj,(N,))==14 and normalized_pools(baseline)==normalized_pools(obj)
 assert same_functions(*objects)==15
 corruptions=0
 for i in range(403):
  bad=bytearray(raw);bad[4*i+3]^=1
  try:normalize(bytes(bad),refs)
  except AssertionError:corruptions+=1
  else:raise AssertionError(('raw corruption accepted',i))
 for at,pairs in refs.items():
  try:normalize(raw,{**refs,at:[(kind,name+'_wrong')for kind,name in pairs]})
  except AssertionError:corruptions+=1
  else:raise AssertionError(('binding corruption accepted',at))
 negatives=0;bad=O/'corrupt-region-guard.csv'
 for i in range(47):
  mutated=[dict(row)for row in rows];mutated[i]['expected']='0x%08X'%(int(mutated[i]['expected'],0)^1)
  stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=header,lineterminator='\n').writerows(mutated);bad.write_bytes(old+stream.getvalue().encode())
  for emit in emitters:
   try:emit(bad)
   except ValueError:negatives+=1
   else:raise AssertionError(('stale CSV guard accepted',i))
  if i%16==0:print(json.dumps(dict(guards_checked=i+1)),flush=True)
 layouts=[]
 for index,start in enumerate((0x151A5660,0x151B8000,0x151C8004,0x151DFFF0)):
  moved=dict(symbols);base=(0x800A8D80,0x800A7FF8,0x800A8000,0x800AFFF0)[index]
  for i in range(6):moved['D_%08X'%(0x800A8D80+4*i)]=base+4*i
  moved['D_800BE9A4']+=(index+1)*0x10104
  outputs=[]
  for j,obj in enumerate([*objects,reference]):
   _,functions,_=pg.parse_object(obj);offset=functions[N]['value'];script=O/('region-link-%d-%d.ld'%(index,j));elf=script.with_suffix('.elf');binary=script.with_suffix('.bin')
   names=[line.split()[-1]for line in subprocess.check_output(['mips-linux-gnu-nm','-u',str(obj)],text=True).splitlines()]
   script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(start-offset)+'\n'.join('%s = 0x%X;'%(name,moved[name])for name in names))
   q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',N,'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True)
   outputs.append(binary.read_bytes()[offset:offset+SIZE])
  assert outputs[0]==outputs[1]==outputs[2]==struct.pack('>403I',*bound_blob(normal,nrefs,moved))
  layouts.append(dict(code_start=hex(start),coefficient_base=hex(base),dt=hex(moved['D_800BE9A4']),gnu_links=3))
 assert negatives==94 and corruptions==439
 m.check_inputs()
 report=dict(guard_words=47,body_words=403,frame=264,insertions=0,omissions=0,original_bindings=36,raw_and_binding_corruptions=corruptions,stale_CSV_controls=negatives,padders=2,owner_functions=15,neighbors_preserved=14,pools_unchanged=True,layouts=layouts,gnu_links=12,source_installed=m.installed(),c_match_credit=0)
 dest.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
