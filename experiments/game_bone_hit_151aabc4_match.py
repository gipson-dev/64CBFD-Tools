"""Both real owner padders, relocation-aware guards and independent GNU links."""
from pathlib import Path
import csv,hashlib,io,json,struct,subprocess,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments import game_bone_hit_151aabc4_recovery as source
R,P,F,N,SIZE=source.ROOT,source.OUT,source.FROZEN,source.NAME,source.SIZE
OWNER="generated_1D6E80"
def assemble(text,label):
 src=P/(label+'.s');obj=src.with_suffix('.o');assert not src.exists();src.write_text(text)
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=R/'conker',capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stderr;return obj
def main():
 source.check_inputs()
 fragment=(F/'conker/asm/1D6E80.s').read_text().split('glabel '+N+'\n',1)[1].split('endlabel '+N,1)[0]
 reference=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+N+'\n'+fragment+'\n.size '+N+',.-'+N+'\n','bone-original-reference')
 raw,refs=payload(P/'v13.o',N);normal,nrefs=payload(reference,N);assert len(raw)==len(normal)==SIZE
 syms={r[1]:r[2][1]for r in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())};assert struct.pack('>126I',*bound_blob(normal,nrefs,syms))==(P/'retail.bin').read_bytes()
 old=(F/'conker/retail_word_patches.us.csv').read_bytes();assert(R/'conker/retail_word_patches.us.csv').read_bytes()in(old,(source.ADOPTION/'proposed-guards.csv').read_bytes())if source.installed()else(R/'conker/retail_word_patches.us.csv').read_bytes()==old
 fields=next(csv.reader(io.StringIO(old.decode())));rows=[];rel=lambda v:';'.join(k+':'+n for k,n in v)or'-'
 for off in range(0,SIZE,4):
  a,b=struct.unpack_from('>I',raw,off)[0],struct.unpack_from('>I',normal,off)[0]
  if a==b and refs.get(off,[])==nrefs.get(off,[]):continue
  row={k:''for k in fields};row.update(filename=OWNER,function=N,offset='0x%03X'%off,expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=rel(refs.get(off,[])),replacement_relocations=rel(nrefs.get(off,[])),note='Normalize proved private bone-hit descriptor initialization schedule',omit='false');rows.append(row)
 assert rows==source.PIN['guard_rows']
 assert all(r['function']!=N for r in csv.DictReader(io.StringIO(old.decode())))
 def emit_rows(values):
  stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=fields,lineterminator='\n').writerows(values);return old+stream.getvalue().encode()
 proposed=P/'proposed-guards.csv';assert not proposed.exists();proposed.write_bytes(emit_rows(rows))
 plan=dict(raw_sha256=hashlib.sha256(raw).hexdigest(),normalized_sha256=hashlib.sha256(normal).hexdigest(),refs={str(k):v for k,v in refs.items()},normalized_refs={str(k):v for k,v in nrefs.items()},guard_rows=rows,source_label='v13')
 (P/'proposed-match-manifest.json').write_text(json.dumps(plan,indent=2)+'\n')
 def normalize(candidate,bindings):
  assert hashlib.sha256(candidate).hexdigest()==plan['raw_sha256']and bindings==refs
  output=bytearray(candidate);rr={k:list(v)for k,v in bindings.items()}
  for row in rows:
   off=int(row['offset'],0);assert struct.unpack_from('>I',output,off)[0]==int(row['expected'],0)
   assert rr.get(off,[])==pg.parse_relocation_spec(row['expected_relocations'])
   struct.pack_into('>I',output,off,int(row['replacement'],0));new=pg.parse_relocation_spec(row['replacement_relocations'])
   if new:rr[off]=new
   else:rr.pop(off,None)
  assert bytes(output)==normal and rr==nrefs;return bytes(output),rr
 assert normalize(raw,refs)==(normal,nrefs)
 emitters=(lambda guards:pg.emit_padded_assembly(P/'v13.o',F/'conker/asm/1D6E80.s',filename=OWNER,word_patches_path=guards),lambda guards:pc.emit_padded_assembly(P/'v13.o',F/'conker/retail_layout.us.txt',OWNER,word_patches_path=guards))
 objects=[]
 for label,emit in zip(('strict','layout'),emitters):
  obj=assemble(emit(proposed),'bone-padded-'+label);objects.append(obj);assert payload(obj,N)==(normal,nrefs)
  baseline=F/'conker/build/src/game/generated_1D6E80.c.o';assert same_functions(baseline,obj,(N,))==40 and normalized_pools(baseline)==normalized_pools(obj)
 assert same_functions(*objects)==41
 corruptions=0
 for i in range(126):
  bad=bytearray(raw);bad[i*4+3]^=1
  try:normalize(bytes(bad),refs)
  except AssertionError:corruptions+=1
  else:raise AssertionError(('raw corruption',i))
 for off,pairs in refs.items():
  try:normalize(raw,{**refs,off:[(kind,name+'_wrong')for kind,name in pairs]})
  except AssertionError:corruptions+=1
  else:raise AssertionError(('binding corruption',off))
 negatives=0;badfile=P/'corrupt-bone-guard.csv'
 for i in range(len(rows)):
  for field in('expected','expected_relocations'):
   bad=[dict(row)for row in rows];bad[i][field]='0x%08X'%(int(bad[i][field],0)^1)if field=='expected'else('R_MIPS_32:wrong'if bad[i][field]=='-'else bad[i][field]+'_wrong')
   badfile.write_bytes(emit_rows(bad))
   for emit in emitters:
    try:emit(badfile)
    except ValueError:negatives+=1
    else:raise AssertionError(('stale guard',i,field))
 layouts=[]
 for i,start in enumerate((0x151AABC4,0x151B8000,0x151C8004,0x151DFFF0)):
  moved=dict(syms);base=(0x800A8FCC,0x800A7FFC,0x800A8000,0x800AFFF0)[i]
  for n in range(5):moved['D_%08X'%(0x800A8FCC+n*4)]=base+n*4
  moved['D_800A8F70']=(0x800A8F70,0x800B7FFF,0x800C8000,0x800DFFFE)[i];outputs=[]
  for j,obj in enumerate([*objects,reference]):
   offset=pg.parse_object(obj)[1][N]['value'];script=P/('bone-link-%d-%d.ld'%(i,j));elf=script.with_suffix('.elf');binary=script.with_suffix('.bin');assert not script.exists()
   names=[line.split()[-1]for line in subprocess.check_output(['mips-linux-gnu-nm','-u',str(obj)],text=True).splitlines()]
   script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(start-offset)+'\n'.join('%s = 0x%X;'%(name,moved[name])for name in names))
   q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',N,'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True);outputs.append(binary.read_bytes()[offset:offset+SIZE])
  assert outputs[0]==outputs[1]==outputs[2]==struct.pack('>126I',*bound_blob(normal,nrefs,moved))
  layouts.append(dict(code_start=hex(start),coefficient_base=hex(base),bone_table=hex(moved['D_800A8F70']),gnu_links=3))
 assert corruptions==126+len(refs)and negatives==len(rows)*4
 report=dict(body_words=126,frame=200,guard_words=len(rows),original_bindings=len(refs),raw_and_binding_corruptions=corruptions,stale_CSV_controls=negatives,padders=2,owner_functions=41,neighbors_preserved=40,pools_unchanged=True,layouts=layouts,gnu_links=12,insertions=0,omissions=0,source_installed=source.installed(),c_match_credit=0)
 source.check_inputs()
 (P/'object-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
