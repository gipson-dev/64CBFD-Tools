"""Six-copy operation projection and two real padders; not an installation."""
from pathlib import Path
from collections import Counter,defaultdict,deque
import csv,hashlib,io,json,struct,subprocess,sys
from tools.experiments import game_curve_emitter_151a11e4_recovery as m
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
o,r,NAME=m.OUT,m.ROOT,m.NAME

def fields(w):
 op,fmt,fn=w>>26,w>>21&31,w&63
 if w==0:return[]
 if op==0:
  if fn==8:return[(21,'g')]
  if fn==13:return[]
  if fn in(0,2,3):return[(16,'g'),(11,'g')]
  if fn in(16,18):return[(11,'g')]
  if fn in(25,26,27):return[(21,'g'),(16,'g')]
  assert fn in(33,35,36,37);return[(21,'g'),(16,'g'),(11,'g')]
 if op==17:
  if fmt in(0,4):return[(16,'g'),(11,'f')]
  if fmt==8:return[]
  assert fmt in(16,20)
  return[(11,'f'),(6,'f')]+([(16,'f')]if fmt==16 and fn in(0,1,2,3,60)else[])if fn!=60 else[(11,'f'),(16,'f')]
 if op==3:return[]
 if op==15:return[(16,'g')]
 if op in(6,7):return[(21,'g')]
 if op in(49,53,57,61):return[(21,'g'),(16,'f')]
 assert op in(4,5,9,12,13,32,33,35,36,37,40,41,43),hex(w)
 return[(21,'g'),(16,'g')]

def mask(w):return sum(31<<shift for shift,kind in fields(w)if kind=='f'or w>>shift&31 not in(0,29,31))
def branch(w):return w>>26 in(4,5,6,7)or w>>26==17 and w>>21&31==8
def key(w,refs):
 roles=tuple((shift,'zero'if w>>shift&31==0 else'sp'if w>>shift&31==29 else'ra'if w>>shift&31==31 else'variable')for shift,kind in fields(w)if kind=='g')
 return(w&~(mask(w)|(65535 if branch(w)else 0)),tuple(refs),roles)

def assemble(text,label):
 p=o/(label+'.s');obj=p.with_suffix('.o');p.write_text(text)
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(p)],cwd=r/'conker',capture_output=True,text=True)
 assert q.returncode==0 and not q.stderr,q.stderr;return obj

def projection(raw,refs,pin):
 assert hashlib.sha256(raw).hexdigest()==pin['raw_sha256']
 assert {str(k):v for k,v in refs.items()}=={k:[tuple(v)for v in rs]for k,rs in pin['refs'].items()}
 src=struct.unpack('>344I',raw);out=[];bindings={};used=[];copies=Counter()
 for row in pin['order']:
  kind=row['kind']
  if kind=='instruction':
   at=row['source'];w=src[at//4];bits=row['operands'];assert bits&~mask(w)==0
   v=(w&~mask(w))|bits
   if 'target'in row:
    assert branch(w);delta=row['target']-(4*len(out)+4);assert delta%4==0;v=(v&0xffff0000)|((delta//4)&65535)
   assert key(w,refs.get(at,[]))==key(v,refs.get(at,[]))
   if at in refs:bindings[4*len(out)]=refs[at]
   out.append(v);used.append(at)
  elif kind=='gpr-copy':
   a,b=row['source_register'],row['destination'];assert a not in(0,29,31)and b not in(0,29,31)
   out.append((a<<21)|(b<<11)|37);copies[kind]+=1
  elif kind=='fpr-copy':
   a,b=row['source_register'],row['destination'];assert 0<=a<32 and 0<=b<32
   out.append((17<<26)|(16<<21)|(a<<11)|(b<<6)|6);copies[kind]+=1
  else:
   assert kind=='literal-copy';p=row['producer']//4;assert 0<=p<len(out)and out[p]>>26==15
   # Repeating the same LUI is idempotent; the independent whole-function
   # relation also checks every downstream use and provider boundary.
   out.append(out[p]);copies[kind]+=1
 assert sorted(used)==list(range(0,1376,4))and copies==dict({'gpr-copy':4,'fpr-copy':1,'literal-copy':1})and len(out)==350
 fp=lambda ws:[(w>>21&31,w&63)for w in ws if w>>26==17 and w>>21&31 in(16,20)and w&63!=6]
 assert fp(src)==fp(out)and len(fp(src))==39
 return struct.pack('>350I',*out),bindings


def normalize(raw,refs):return projection(raw,refs,m.PIN['schedule'])
def guard_bytes(before,rows,header):
 stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n'if b'\r\n'in before else'\n').writerows(rows)
 return before+stream.getvalue().encode()
def main():
 m.check_inputs();raw,refs=payload(o/'qualified.o',NAME);normal,nrefs=normalize(raw,refs);a=struct.unpack('>344I',raw);b=struct.unpack('>350I',normal)
 assert bound_blob(normal,nrefs,m.symbols())==m.retail()
 insert={0x118,0x124,0x134,0x13c,0x444,0x510};slots=[at for at in range(0,1400,4)if at not in insert];assert len(slots)==344 and all(x-4 not in insert for x in insert)
 old=(m.FROZEN/'conker/retail_word_patches.us.csv').read_bytes();header=next(csv.reader(io.StringIO(old.decode())));assert not any(row['function']==NAME for row in csv.DictReader(io.StringIO(old.decode())))
 spec=lambda rs:';'.join(kind+':'+n for kind,n in rs)or'-';rows=[]
 for i,w in enumerate(a):
  at=slots[i];added=at+4 in insert
  rows.append(dict(filename='generated_1CC440',function=NAME,offset='0x%X'%(4*i),expected='0x%08X'%w,replacement='0x%08X'%b[at//4],expected_relocations=spec(refs.get(4*i,[])),replacement_relocations=spec(nrefs.get(at,[])),note='Preserve proved emitter operation schedule and six redundant copies',insert_after='0x%08X'%b[at//4+1]if added else'',insert_after_relocations='-'if added else'',omit='false'))
 guards=o/'proposed-guards.csv';guards.write_bytes(guard_bytes(old,rows,header));padded=[]
 for label,text in(('layout',pc.emit_padded_assembly(o/'qualified.o',r/'conker/retail_layout.us.txt','generated_1CC440',word_patches_path=guards)),('strict',pg.emit_padded_assembly(o/'qualified.o',r/'conker/asm/1CC440.s',filename='generated_1CC440',word_patches_path=guards))):
  obj=assemble(text,label+'-fitted');assert payload(obj,NAME)==(normal,nrefs)
  assert same_functions(m.FROZEN/'conker/build/src/game/generated_1CC440.c.o',obj,(NAME,))==38
  assert normalized_pools(obj)==normalized_pools(m.FROZEN/'conker/build/src/game/generated_1CC440.c.o');padded.append(obj)
 negatives=0
 for i in range(344):
  wrong=bytearray(raw);wrong[4*i+3]^=1
  try:normalize(bytes(wrong),refs)
  except AssertionError:negatives+=1
  else:raise AssertionError(('raw corruption accepted',i))
 for at,rs in refs.items():
  try:normalize(raw,{**refs,at:[(kind,n+'_wrong')for kind,n in rs]})
  except AssertionError:negatives+=1
  else:raise AssertionError(('binding corruption accepted',at))
 call=next(at for at,rs in refs.items()if rs==[('R_MIPS_26','func_15167D84')]);stale=o/'stale-guards.csv';stale_count=0
 for index,field in((0,'expected'),(343,'expected'),(call//4,'expected'),(call//4,'expected_relocations')):
  altered=[dict(row)for row in rows];altered[index][field]='0x%08X'%(int(altered[index][field],0)^1)if field=='expected'else altered[index][field]+'_wrong';stale.write_bytes(guard_bytes(old,altered,header))
  for emitter in(lambda:pc.emit_padded_assembly(o/'qualified.o',r/'conker/retail_layout.us.txt','generated_1CC440',word_patches_path=stale),lambda:pg.emit_padded_assembly(o/'qualified.o',r/'conker/asm/1CC440.s',filename='generated_1CC440',word_patches_path=stale)):
   try:emitter()
   except (ValueError,AssertionError)as error:assert str(error);stale_count+=1
   else:raise AssertionError(('stale guard accepted',index,field))
 from unittest.mock import patch
 from tools.tests import game_curve_emitter_151a11e4_proof as proof
 rebases=[]
 for i,table in enumerate((0x80090b60,0x800b7ffc,0x800dfffc)):
  moved=m.symbols();moved.update(D_80090B60=table,D_80090D34=(0x80090d34,0x80117ffc,0x8012fffc)[i],D_800BE9A4=(0x800be9a4,0x80127ffc,0x80137ffc)[i])
  for n in('func_150ADA20','func_150ADA68','func_151423D8','func_15167D84','memcpy'):moved[n]+=(i+1)*0x10000
  x,y=bound_blob(raw,refs,moved),bound_blob(normal,nrefs,moved)
  for obj in padded:assert bound_blob(*payload(obj,NAME),moved)==y
  with patch.multiple(proof,TABLE=table,RNG=moved['func_150ADA20'],REAL=moved['func_150ADA68'],TRIG=moved['func_151423D8'],SUBMIT=moved['func_15167D84'],COPY=moved['memcpy']):assert proof.prove(x,y)['whole_function']
  rebases.append(moved)
 m.check_inputs();report=dict(raw_words=344,normalized_words=350,frame=272,source_operations_retained=344,logical_copies=dict(gpr=4,fpr=1,literal=1),CSV_guards=344,CSV_insertions=6,CSV_carrier_insertions_match_logical_copy_locations=False,omissions=0,ordered_FP_operations=39,whole_owner_padders=2,neighbors_unchanged=38,raw_and_binding_corruptions=negatives,real_CSV_negatives=stale_count,independent_rebases=rebases,source_installed=m.installed(),c_match_credit=0)
 (o/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':print(json.dumps(main()),flush=True)
