"""Compare both real padders and independent original assembly under four links."""
from pathlib import Path
import csv,hashlib,io,json,struct,subprocess,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments import game_actor_accumulator_151ab9c8_recovery as source
R,P,F,N,SIZE=source.ROOT,source.OUT,source.FROZEN,source.NAME,source.SIZE
OWNER="generated_1D6E80"
def assemble(text,label):
 src=P/(label+'.s');obj=src.with_suffix('.o');assert not src.exists();src.write_text(text)
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=R/'conker',capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stderr;return obj
def main():
 source.check_inputs()
 fragment=(F/'conker/asm/1D6E80.s').read_text().split('glabel '+N+'\n',1)[1].split('endlabel '+N,1)[0]
 reference=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\nglabel '+N+'\n'+fragment+'\n.size '+N+',.-'+N+'\n','actor-accumulator-original')
 raw,refs=payload(P/'v28.o',N);normal,nrefs=payload(reference,N);assert len(raw)==len(normal)==SIZE
 syms={r[1]:r[2][1]for r in symbol_rows((R/'conker/build/conker.us.elf').read_bytes())};assert struct.pack('>227I',*bound_blob(normal,nrefs,syms))==(P/'retail.bin').read_bytes()
 old=(F/'conker/retail_word_patches.us.csv').read_bytes();assert(R/'conker/retail_word_patches.us.csv').read_bytes()in(old,(source.ADOPTION/'proposed-guards.csv').read_bytes())if source.installed()else(R/'conker/retail_word_patches.us.csv').read_bytes()==old
 fields=next(csv.reader(io.StringIO(old.decode())));rows=[]
 rel=lambda values:'|'.join('%s:%s'%v for v in values)or'-'
 for off in range(0,SIZE,4):
  a,b=struct.unpack_from('>I',raw,off)[0],struct.unpack_from('>I',normal,off)[0]
  if a==b and refs.get(off,[])==nrefs.get(off,[]):continue
  row={k:''for k in fields};row.update(filename=OWNER,function=N,offset='0x%03X'%off,expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=rel(refs.get(off,[])),replacement_relocations=rel(nrefs.get(off,[])),note='Normalize proved actor accumulator allocation and loop scheduling',omit='false');rows.append(row)
 assert rows==source.PIN['guard_rows']
 assert all(r['function']!=N for r in csv.DictReader(io.StringIO(old.decode())))
 def emit_rows(values):
  stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=fields,lineterminator='\n').writerows(values);return old+stream.getvalue().encode()
 proposed=P/'proposed-guards.csv';assert not proposed.exists();proposed.write_bytes(emit_rows(rows))
 plan=dict(raw_sha256=hashlib.sha256(raw).hexdigest(),normalized_sha256=hashlib.sha256(normal).hexdigest(),refs={str(k):v for k,v in refs.items()},normalized_refs={str(k):v for k,v in nrefs.items()},guard_rows=rows,source_label='v28')
 (P/'proposed-match-manifest.json').write_text(json.dumps(plan,indent=2)+'\n')
 def normalize(candidate,bindings):
  assert hashlib.sha256(candidate).hexdigest()==plan['raw_sha256']and bindings==refs
  output=bytearray();rr={};by_offset={int(r['offset'],0):r for r in rows}
  for off in range(0,len(candidate),4):
   word=struct.unpack_from('>I',candidate,off)[0];pairs=bindings.get(off,[]);row=by_offset.get(off)
   if row:
    assert word==int(row['expected'],0)and pairs==pg.parse_relocation_spec(row['expected_relocations']);word=int(row['replacement'],0);pairs=pg.parse_relocation_spec(row['replacement_relocations'])
   if pairs:rr[off]=pairs
   output+=struct.pack('>I',word)
  assert bytes(output)==normal and rr==nrefs;return bytes(output),rr
 assert normalize(raw,refs)==(normal,nrefs)
 emitters=(lambda guards:pg.emit_padded_assembly(P/'v28.o',F/'conker/asm/1D6E80.s',filename=OWNER,word_patches_path=guards),lambda guards:pc.emit_padded_assembly(P/'v28.o',F/'conker/retail_layout.us.txt',OWNER,word_patches_path=guards))
 objects=[]
 for label,emit in zip(('strict','layout'),emitters):
  obj=assemble(emit(proposed),'actor-accumulator-padded-'+label);objects.append(obj);assert payload(obj,N)==(normal,nrefs)
  baseline=F/'conker/build/src/game/generated_1D6E80.c.o';assert same_functions(baseline,obj,(N,))==40 and normalized_pools(baseline)==normalized_pools(obj)
 assert same_functions(*objects)==41
 corruptions=0
 for i in range(227):
  bad=bytearray(raw);bad[i*4+3]^=1
  try:normalize(bytes(bad),refs)
  except AssertionError:corruptions+=1
  else:raise AssertionError(('raw corruption',i))
 for off,pairs in refs.items():
  try:normalize(raw,{**refs,off:[(kind,name+'_wrong')for kind,name in pairs]})
  except AssertionError:corruptions+=1
  else:raise AssertionError(('binding corruption',off))
 negatives=0;badfile=P/'corrupt-actor-accumulator-guard.csv'
 for i in range(len(rows)):
  if i%25==0:print(json.dumps(dict(stale_guard_row=i,total=len(rows))),flush=True)
  for field in('expected','expected_relocations'):
   bad=[dict(row)for row in rows];bad[i][field]='0x%08X'%(int(bad[i][field],0)^1)if field=='expected'else('R_MIPS_32:wrong'if bad[i][field]=='-'else bad[i][field]+'_wrong');badfile.write_bytes(emit_rows(bad))
   for emit in emitters:
    try:emit(badfile)
    except ValueError:negatives+=1
    else:raise AssertionError(('stale guard',i,field))
 layouts=[]
 for i,start in enumerate((0x151AB9C8,0x151B8000,0x151C8004,0x151DFFF0)):
  moved=dict(syms)
  for name,values in {'D_800BE9A4':(0x800BE9A4,0x800B7FFC,0x800C8000,0x800DFFF8),'D_800A9018':(0x800A9018,0x800A7FFC,0x800B8000,0x800CFFF8),'D_800A901C':(0x800A901C,0x800DFFFC,0x800E8000,0x800F7FFC)}.items():moved[name]=values[i]
  outputs=[]
  for j,obj in enumerate([*objects,reference]):
   offset=pg.parse_object(obj)[1][N]['value'];script=P/('actor-accumulator-link-%d-%d.ld'%(i,j));elf=script.with_suffix('.elf');binary=script.with_suffix('.bin');assert not script.exists()
   names=[line.split()[-1]for line in subprocess.check_output(['mips-linux-gnu-nm','-u',str(obj)],text=True).splitlines()]
   script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(start-offset)+'\n'.join('%s = 0x%X;'%(name,moved[name])for name in names))
   q=subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',N,'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   subprocess.run(['mips-linux-gnu-objcopy','-O','binary','-j','.text',str(elf),str(binary)],capture_output=True,check=True);outputs.append(binary.read_bytes()[offset:offset+SIZE])
  assert outputs[0]==outputs[1]==outputs[2]==struct.pack('>227I',*bound_blob(normal,nrefs,moved));layouts.append(dict(code_start=hex(start),gnu_links=3))
 report=dict(body_words=227,retail_words=227,frame=280,guard_words=len(rows),original_bindings=len(nrefs),raw_and_binding_corruptions=corruptions,stale_CSV_controls=negatives,padders=2,owner_functions=41,neighbors_preserved=40,pools_unchanged=True,layouts=layouts,gnu_links=12,insertions=0,omissions=0,source_installed=source.installed(),c_match_credit=0)
 source.check_inputs()
 (P/'object-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
