"""Proved allocator/CFG projection with copies, short reload and RA coalescing.

Every real source operation is retained except the path-exclusive duplicate
saved-RA load. Independent whole-function transfer checks qualify the common
epilogue, branch annulment and narrow-value identities. CSV rows are emission
carriers, not per-row semantic instruction origins.
"""
from pathlib import Path
from collections import Counter
from unittest.mock import patch
import csv,hashlib,io,json,struct,subprocess,sys
from tools.experiments import game_spawn_curve_151a1998_recovery as m
from tools.experiments.game_curve_emitter_151a11e4_match import fields,mask,key,branch
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
o,r,NAME=m.OUT,m.ROOT,m.NAME

def assemble(text,label):
 p=o/(label+'.s');obj=p.with_suffix('.o');p.write_text(text)
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(p)],cwd=r/'conker',capture_output=True,text=True)
 assert q.returncode==0 and not q.stderr,q.stderr
 return obj

def projection(raw,refs,pin):
 assert hashlib.sha256(raw).hexdigest()==pin['raw_sha256']
 assert {str(k):v for k,v in refs.items()}=={k:[tuple(v)for v in rs]for k,rs in pin['raw_refs'].items()}
 src=struct.unpack('>293I',raw);omitted=pin['omitted'];omit=omitted['offset'];other=omitted['coalesced_restore']
 assert(omit,other)==(0xA8,0x450)and src[omit//4]==src[other//4]==0x8FBF006C and omit not in refs and other not in refs
 assert src[0xA4//4]&0xffff0000==0x45020000
 out=[];bindings={};used=[];copies=Counter();forms=0
 for row in pin['order']:
  at=4*len(out);kind=row['kind']
  if kind=='instruction':
   source=row['source'];assert source!=omit;w=src[source//4];original=w;bits=row['operands'];assert bits&~mask(w)==0
   if 'branch_form'in row:
    assert row['branch_form']=='likely-to-ordinary'and source==0xA4 and w&0xffff0000==0x45020000
    w^=0x20000;forms+=1
   value=(w&~mask(w))|bits
   if 'target'in row:
    assert branch(w);delta=row['target']-(at+4);assert delta%4==0;value=(value&0xffff0000)|((delta//4)&65535)
   assert key(w,refs.get(source,[]))==key(value,refs.get(source,[]))
   if source in refs:bindings[at]=refs[source]
   out.append(value);used.append(source)
  elif kind=='gpr-copy':
   a,b=row['source_register'],row['destination'];assert a not in(0,29,31)and b not in(0,29,31)
   out.append((a<<21)|(b<<11)|37);copies[kind]+=1
  else:
   assert kind=='short-reload'and row['base']==29 and row['offset']==0xAA and row['producer']==at-4
   producer=out[-1];assert producer>>26==41 and producer>>21&31==29 and producer&65535==0xAA
   out.append((33<<26)|(29<<21)|(row['destination']<<16)|0xAA);copies[kind]+=1
 assert sorted(used)==[at for at in range(0,1172,4)if at!=omit]
 assert copies==dict({'gpr-copy':2,'short-reload':1})and forms==1 and len(out)==295
 fp=lambda ws:[(w>>21&31,w&63)for w in ws if w>>26==17 and w>>21&31 in(16,20)and w&63!=6]
 assert fp(src)==fp(out)and len(fp(src))==22
 assert {str(k):v for k,v in bindings.items()}=={k:[tuple(v)for v in rs]for k,rs in m.PIN['normal_refs'].items()}
 return struct.pack('>295I',*out),bindings

def normalize(raw,refs):return projection(raw,refs,m.PIN['schedule'])

def guard_bytes(before,rows,header):
 stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n'if b'\r\n'in before else'\n').writerows(rows)
 return before+stream.getvalue().encode()

def make_rows(raw,refs,normal,nrefs):
 a,b=struct.unpack('>293I',raw),struct.unpack('>295I',normal);insert={0x10C,0x11C,0x2DC};omit=0xA8
 slots=iter(at for at in range(0,1180,4)if at not in insert);rows=[]
 spec=lambda rs:';'.join(kind+':'+name for kind,name in rs)or'-'
 for i,w in enumerate(a):
  raw_at=4*i
  if raw_at==omit:
   rows.append(dict(filename='generated_1CC440',function=NAME,offset=hex(raw_at),expected='0x%08X'%w,replacement='0x%08X'%w,expected_relocations='-',replacement_relocations='-',note='Coalesce proved branch-only saved-RA restore with the common epilogue',insert_after='',insert_after_relocations='',omit='true'));continue
  at=next(slots);added=at+4 in insert
  rows.append(dict(filename='generated_1CC440',function=NAME,offset=hex(raw_at),expected='0x%08X'%w,replacement='0x%08X'%b[at//4],expected_relocations=spec(refs.get(raw_at,[])),replacement_relocations=spec(nrefs.get(at,[])),note='Preserve proved emitter CFG allocator schedule and short-width identities',insert_after='0x%08X'%b[at//4+1]if added else'',insert_after_relocations=spec(nrefs.get(at+4,[]))if added else'',omit='false'))
 assert next(slots,None)is None
 return rows

def main():
 m.check_inputs();raw,refs=payload(o/'qualified.o',NAME);normal,nrefs=normalize(raw,refs)
 assert bound_blob(normal,nrefs,m.symbols())==m.retail()
 old=(m.FROZEN/'conker/retail_word_patches.us.csv').read_bytes();header=next(csv.reader(io.StringIO(old.decode())))
 assert not any(row['function']==NAME for row in csv.DictReader(io.StringIO(old.decode())))
 rows=make_rows(raw,refs,normal,nrefs);guards=o/'proposed-guards.csv';guards.write_bytes(guard_bytes(old,rows,header))
 emitters=lambda path:(lambda:pc.emit_padded_assembly(o/'qualified.o',r/'conker/retail_layout.us.txt','generated_1CC440',word_patches_path=path),lambda:pg.emit_padded_assembly(o/'qualified.o',r/'conker/asm/1CC440.s',filename='generated_1CC440',word_patches_path=path))
 padded=[]
 for label,emitter in zip(('layout','strict'),emitters(guards)):
  obj=assemble(emitter(),label+'-fitted');assert payload(obj,NAME)==(normal,nrefs)
  assert same_functions(m.FROZEN/'conker/build/src/game/generated_1CC440.c.o',obj,(NAME,))==38
  assert normalized_pools(obj)==normalized_pools(m.FROZEN/'conker/build/src/game/generated_1CC440.c.o');padded.append(obj)
 negatives=0
 for i in range(293):
  wrong=bytearray(raw);wrong[4*i+3]^=1
  try:normalize(bytes(wrong),refs)
  except AssertionError:negatives+=1
  else:raise AssertionError(('raw corruption accepted',i))
 for at,rs in refs.items():
  try:normalize(raw,{**refs,at:[(kind,name+'_wrong')for kind,name in rs]})
  except AssertionError:negatives+=1
  else:raise AssertionError(('binding corruption accepted',at))
 call=next(at for at,rs in refs.items()if rs==[('R_MIPS_26','func_15167D84')]);stale=o/'stale-guards.csv';stale_count=0
 for index,field in((0,'expected'),(292,'expected'),(0xA8//4,'expected'),(call//4,'expected'),(call//4,'expected_relocations')):
  changed=[dict(row)for row in rows];changed[index][field]='0x%08X'%(int(changed[index][field],0)^1)if field=='expected'else changed[index][field]+'_wrong';stale.write_bytes(guard_bytes(old,changed,header))
  for emitter in emitters(stale):
   try:emitter()
   except ValueError:stale_count+=1
   else:raise AssertionError(('stale CSV accepted',index,field))
 from tools.tests import game_spawn_curve_151a1998_proof as proof
 rebases=[]
 for delta in(0x17000,0x29004,0x3F100):
  moved={name:value+delta for name,value in m.symbols().items()}
  x,y=bound_blob(raw,refs,moved),bound_blob(normal,nrefs,moved)
  with patch.multiple(proof,TABLE=moved['D_80090B60'],RNG=moved['func_150ADA20'],REAL=moved['func_150ADA68'],TRIG=moved['func_151423D8'],SUBMIT=moved['func_15167D84'],COPY=moved['memcpy']):
   assert proof.prove(x,y)['whole_function']
   assert proof.prove(y,y,raw_state_register=16,raw_loop_start=0x104)['whole_function']
  rebases.append(moved)
 m.check_inputs();report=dict(raw_words=293,normalized_words=295,frame=240,source_operations_retained=292,
  omissions=1,coalesced_return_restore=True,likely_to_ordinary_branch=1,gpr_copies=2,redundant_short_reload=1,
  CSV_guards=293,CSV_insertions=3,CSV_rows_are_carriers=True,ordered_FP_operations=22,whole_owner_padders=2,neighbors_unchanged=38,
  raw_and_binding_corruptions=negatives,real_CSV_negatives=stale_count,independent_rebases=rebases,source_installed=m.installed(),c_match_credit=0)
 (o/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':print(json.dumps(main()),flush=True)
