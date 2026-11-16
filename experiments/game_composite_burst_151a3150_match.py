"""Operation-conserving 17-word allocator/schedule projection and real padders."""
from pathlib import Path
from collections import defaultdict,deque
import csv,hashlib,io,json,struct,subprocess,sys
from tools.experiments.game_curve_emitter_151a11e4_match import fields as common_fields
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments import game_composite_burst_151a3150_recovery as m
o,r,NAME=m.OUT,m.ROOT,m.NAME
def fields(w):return[(21,'g'),(16,'g')]if w>>26 in(20,21,22,23)else common_fields(w)
def mask(w):return sum(31<<shift for shift,kind in fields(w)if kind=='f'or w>>shift&31 not in(0,29,31))
def branch(w):return w>>26 in(4,5,6,7,20,21,22,23)or w>>26==17 and w>>21&31==8
def key(w,refs):
 roles=tuple((shift,'zero'if w>>shift&31==0 else'sp'if w>>shift&31==29 else'ra'if w>>shift&31==31 else'variable')for shift,kind in fields(w)if kind=='g')
 return(w&~(mask(w)|(65535 if branch(w)else 0)),tuple(refs),roles)
def assemble(text,label):
 p=o/(label+'.s');obj=p.with_suffix('.o');p.write_text(text)
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(p)],cwd=r/'conker',capture_output=True,text=True)
 assert q.returncode==0 and not q.stderr,q.stderr;return obj

def normalize(raw,refs):
 pin=m.PIN['schedule'];assert hashlib.sha256(raw).hexdigest()==pin['raw_sha256']
 assert {str(k):v for k,v in refs.items()}=={k:[tuple(v)for v in rs]for k,rs in pin['raw_refs'].items()}
 src=struct.unpack('>142I',raw);words=[];bindings={};used=[]
 for row in pin['order']:
  at=len(words)*4;source=row['source'];w=src[source//4];bits=row['operands'];assert bits&~mask(w)==0
  v=(w&~mask(w))|bits
  if 'target'in row:
   assert branch(w);d=row['target']-(at+4);assert d%4==0;v=(v&0xffff0000)|((d//4)&65535)
  assert key(w,refs.get(source,[]))==key(v,refs.get(source,[]))
  if source in refs:bindings[at]=refs[source]
  words.append(v);used.append(source)
 assert sorted(used)==list(range(0,568,4))and bindings==refs
 return struct.pack('>142I',*words),bindings

def guard_bytes(old,rows,header):
 stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n'if b'\r\n'in old else'\n').writerows(rows)
 return old+stream.getvalue().encode()

def main():
 from unittest.mock import patch
 m.check_inputs();raw,refs=payload(o/'qualified.o',NAME);normal,nrefs=normalize(raw,refs)
 assert bound_blob(normal,nrefs,m.symbols())==m.retail()
 a,b=struct.unpack('>142I',raw),struct.unpack('>142I',normal)
 old=(m.FROZEN/'conker/retail_word_patches.us.csv').read_bytes();header=next(csv.reader(io.StringIO(old.decode())))
 assert not any(row['function']==NAME for row in csv.DictReader(io.StringIO(old.decode())))
 rows=[]
 for i,(x,y)in enumerate(zip(a,b)):
  if x==y:continue
  assert 4*i not in refs
  rows.append(dict(filename='generated_1CC440',function=NAME,offset=hex(4*i),expected='0x%08X'%x,replacement='0x%08X'%y,expected_relocations='-',replacement_relocations='-',note='Preserve proved composite-burst integer allocator and packet-store schedule',insert_after='',insert_after_relocations='',omit='false'))
 assert len(rows)==17
 guards=o/'proposed-guards.csv';guards.write_bytes(guard_bytes(old,rows,header))
 emitters=lambda p:(lambda:pc.emit_padded_assembly(o/'qualified.o',r/'conker/retail_layout.us.txt','generated_1CC440',word_patches_path=p),lambda:pg.emit_padded_assembly(o/'qualified.o',r/'conker/asm/1CC440.s',filename='generated_1CC440',word_patches_path=p))
 for label,emit in zip(('layout','strict'),emitters(guards)):
  obj=assemble(emit(),label+'-fitted');assert payload(obj,NAME)==(normal,nrefs)
  assert same_functions(m.FROZEN/'conker/build/src/game/generated_1CC440.c.o',obj,(NAME,))==38
  assert normalized_pools(obj)==normalized_pools(m.FROZEN/'conker/build/src/game/generated_1CC440.c.o')
 corruptions=0
 for i in range(142):
  bad=bytearray(raw);bad[4*i+3]^=1
  try:normalize(bytes(bad),refs)
  except AssertionError:corruptions+=1
  else:raise AssertionError(('raw corruption accepted',i))
 for at,rs in refs.items():
  try:normalize(raw,{**refs,at:[(kind,name+'_wrong')for kind,name in rs]})
  except AssertionError:corruptions+=1
  else:raise AssertionError(('binding corruption accepted',at))
 stale=o/'stale-guards.csv';stale_count=0
 for index,field in((0,'expected'),(16,'expected'),(7,'expected'),(10,'expected'),(12,'expected_relocations')):
  changed=[dict(row)for row in rows];changed[index][field]='0x%08X'%(int(changed[index][field],0)^1)if field=='expected'else'R_MIPS_HI16:D_wrong'
  stale.write_bytes(guard_bytes(old,changed,header))
  for emit in emitters(stale):
   try:emit()
   except ValueError:stale_count+=1
   else:raise AssertionError(('stale guard accepted',index,field))
 from tools.tests import game_composite_burst_151a3150_proof as proof
 rebases=[]
 for delta in(0x17000,0x29004,0x3F100):
  moved={n:v+delta for n,v in m.symbols().items()};x,y=bound_blob(raw,refs,moved),bound_blob(normal,nrefs,moved)
  with patch.object(proof,'SUBMIT',moved['func_15152B38']):assert proof.prove(x,y)['whole_function']and proof.prove(y,y)['whole_function']
  rebases.append(moved)
 report=dict(raw_words=142,normalized_words=142,frame=144,source_operations_retained=142,guards=17,insertions=0,omissions=0,raw_and_binding_corruptions=corruptions,real_CSV_negatives=stale_count,independent_rebases=rebases,whole_owner_padders=2,neighbors_unchanged=38,pools_unchanged=True,source_installed=m.installed(),c_match_credit=0)
 (o/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');m.check_inputs();return report
if __name__=='__main__':print(json.dumps(main()),flush=True)
