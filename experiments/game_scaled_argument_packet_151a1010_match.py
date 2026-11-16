"""Source-operation scheduling, five proved short copies and exact object gates."""
from pathlib import Path
from unittest.mock import patch
import csv,hashlib,io,json,struct,subprocess,sys
from tools.experiments import game_scaled_argument_packet_151a1010_recovery as m
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
ROOT,OUT,FROZEN,NAME=m.ROOT,m.OUT,m.FROZEN,m.NAME
SOURCE,ENTRY,ROM,SIZE=m.SOURCE,m.ENTRY,m.ROM,444
PIN=m.PIN['schedule']

def fields(w):
 op,fmt,fn=w>>26,w>>21&31,w&63
 if op==0:shifts=(21,)if fn==8 else(16,11)if fn in(0,2,3)else(21,16,11)if fn==37 else None
 elif op==17:shifts=(16,)if fmt in(0,4)else()
 elif op==3:shifts=()
 elif op in(6,7,49,57):shifts=(21,)
 elif op==15:shifts=(16,)
 else:shifts=(21,16)if op in(9,35,36,43)else None
 assert shifts is not None,hex(w)
 return sum(31<<s for s in shifts if w>>s&31 not in(0,29,31))

def key(w,refs):
 mask=fields(w)
 if w>>26 in(6,7):mask|=65535
 if refs:mask|=0x3ffffff if w>>26==3 else 65535
 return w&~mask,tuple(refs)

def writes(w):
 op,fmt,fn=w>>26,w>>21&31,w&63
 if op==0:return(w>>11&31,)if fn in(0,2,3,37)else()
 if op in(9,15,35,36)or op==17 and fmt==0:return(w>>16&31,)
 return()

def project(raw,refs,pin):
 if hashlib.sha256(raw).hexdigest()!=pin['raw_sha256']or{str(k):v for k,v in refs.items()}!={k:[tuple(v)for v in rows]for k,rows in pin['raw_refs'].items()}:raise ValueError('Compiler words or bindings changed')
 words=list(struct.unpack('>106I',raw));out=[];bindings={};sources=[];copies=[]
 for row in pin['order']:
  at=row['source'];w=words[at//4]
  if row['kind']=='instruction':
   mask=fields(w);assert row['operands']&~mask==0;changed=(w&~mask)|row['operands']
   if 'target'in row:
    assert w>>26 in(6,7);delta=row['target']-(4*len(out)+4);assert delta%4==0;changed=(changed&0xffff0000)|((delta//4)&65535)
   assert key(w,refs.get(at,[]))==key(changed,refs.get(at,[]));w=changed;sources.append(at)
   if at in refs:bindings[4*len(out)]=refs[at]
  else:
   assert row['kind']=='short-view-copy';producer=row['producer']//4;assert 0<=producer<len(out)
   origin=out[producer];assert origin>>26==0 and origin&63==3 and origin>>6&31==16
   assert pin['order'][producer]['kind']=='instruction'and pin['order'][producer]['source']==at
   assert words[at//4]>>26==0 and words[at//4]&63==3 and words[at//4]>>6&31==16
   src=origin>>11&31;dest=row['destination'];assert src not in(0,29,31)and dest not in(0,29,31)
   assert all(src not in writes(v)for v in out[producer+1:]),('short view killed before copy',src,producer,len(out))
   w=(src<<21)|(dest<<11)|37;copies.append(4*len(out))
  out.append(w)
 assert sorted(sources)==list(range(0,424,4))and copies==pin['copy_offsets']and len(copies)==5 and len(out)==111
 fp=lambda values:[w for w in values if w>>26==17 and w>>21&31==16]
 assert fp(words)==fp(out)and len(fp(words))==17,'FP operations or register operands changed'
 return struct.pack('>111I',*out),bindings

def normalize(raw,refs):
 normal,bindings=project(raw,refs,PIN)
 assert hashlib.sha256(normal).hexdigest()==PIN['normal_sha256']
 assert {str(k):v for k,v in bindings.items()}=={k:[tuple(v)for v in rows]for k,rows in PIN['normal_refs'].items()}
 return normal,bindings

def assemble(label,text):
 path=OUT/(label+'.s');obj=path.with_suffix('.o');path.write_text(text)
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=ROOT/'conker',capture_output=True,text=True);assert q.returncode==0 and not q.stderr,q.stderr;return obj

def main():
 m.check_inputs();raw,refs=payload(OUT/'qualified.o',NAME);normal,nrefs=normalize(raw,refs);symbols={'D_800A8D28':m.CONST,'func_151A11CC':m.CALLEE};truth=m.retail();assert bound_blob(normal,nrefs,symbols)==truth
 from tools.tests import game_scaled_argument_packet_151a1010_proof as core
 from tools.tests import game_scaled_argument_packet_151a1010_frame_proof as proof
 assert proof.prove(bound_blob(raw,refs,symbols),truth)['whole_private_word_image_at_call_and_return']
 negative=0
 for i in range(106):
  changed=bytearray(raw);changed[4*i+3]^=1
  try:normalize(bytes(changed),refs)
  except ValueError:negative+=1
  else:raise AssertionError(('changed source word accepted',i))
 for at,rows in refs.items():
  try:normalize(raw,{**refs,at:[(kind,name+'_bad')for kind,name in rows]})
  except ValueError:negative+=1
  else:raise AssertionError(('changed source binding accepted',at))
 before=(FROZEN/'conker/retail_word_patches.us.csv').read_bytes();header=next(csv.reader(io.StringIO(before.decode())));assert not any(row['function']==NAME for row in csv.DictReader(io.StringIO(before.decode())))
 original=struct.unpack('>106I',raw);wanted=struct.unpack('>111I',normal);slots=[i for i,row in enumerate(PIN['order'])if row['kind']=='instruction'];assert len(slots)==106
 reloc=lambda rows:';'.join(kind+':'+name for kind,name in rows)or'-';rows=[]
 for i,w in enumerate(original):
  at=4*i;target=slots[i];insert=target+1<len(wanted)and PIN['order'][target+1]['kind']=='short-view-copy'
  rows.append(dict(filename='generated_1CC440',function=NAME,offset='0x%X'%at,expected='0x%08X'%w,replacement='0x%08X'%wanted[target],expected_relocations=reloc(refs.get(at,[])),replacement_relocations=reloc(nrefs.get(4*target,[])),note='Preserve proved scaled packet short views and compiler schedule; five short-result copies',insert_after='0x%08X'%wanted[target+1]if insert else'',insert_after_relocations='-'if insert else'',omit='false'))
 def csv_bytes(items):
  stream=io.StringIO(newline='');csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n'if b'\r\n'in before else'\n').writerows(items);return before+stream.getvalue().encode()
 guards=OUT/'proposed-guards.csv';guards.write_bytes(csv_bytes(rows));padded=[]
 for label,text in(('layout',pc.emit_padded_assembly(OUT/'qualified.o',ROOT/'conker/retail_layout.us.txt','generated_1CC440',word_patches_path=guards)),('strict',pg.emit_padded_assembly(OUT/'qualified.o',ROOT/'conker/asm/1CC440.s',filename='generated_1CC440',word_patches_path=guards))):
  obj=assemble(label,text);assert payload(obj,NAME)==(normal,nrefs)
  assert same_functions(FROZEN/'conker/build/src/game/generated_1CC440.c.o',obj,(NAME,))==38
  assert normalized_pools(obj)==normalized_pools(FROZEN/'conker/build/src/game/generated_1CC440.c.o');padded.append(obj)
 stale=OUT/'stale-guards.csv';padder_stale=0
 controls=[(i,'expected')for i in sorted({0,105,*[at//4 for at in refs]})]+[(at//4,'expected_relocations')for at in refs]
 for index,field in controls:
  changed=[dict(row)for row in rows];changed[index][field]='0x%08X'%(int(changed[index][field],0)^1)if field=='expected'else changed[index][field].replace('func_','wrong_').replace('D_','wrong_');stale.write_bytes(csv_bytes(changed))
  for emitter in(lambda:pc.emit_padded_assembly(OUT/'qualified.o',ROOT/'conker/retail_layout.us.txt','generated_1CC440',word_patches_path=stale),lambda:pg.emit_padded_assembly(OUT/'qualified.o',ROOT/'conker/asm/1CC440.s',filename='generated_1CC440',word_patches_path=stale)):
   try:emitter()
   except (ValueError,AssertionError)as error:assert str(error);padder_stale+=1
   else:raise AssertionError(('stale CSV accepted',index,field))
 rebases=[]
 for ordinal,constant in enumerate((m.CONST,0x800afffc,0x80117ffc)):
  moved={'D_800A8D28':constant,'func_151A11CC':m.CALLEE+(ordinal+1)*0x10000};a,b=bound_blob(raw,refs,moved),bound_blob(normal,nrefs,moved)
  for obj in padded:assert bound_blob(*payload(obj,NAME),moved)==b
  with patch.multiple(core,CONST=constant,CALLEE=moved['func_151A11CC']):assert proof.prove(a,b)['whole_private_word_image_at_call_and_return']
  rebases.append(moved)
 m.check_inputs();report=dict(raw_words=106,normalized_words=111,frame=120,word_guards=106,inserted_words=5,omitted_words=0,all_source_operations_retained_once=True,FP_words_unchanged=17,short_copy_offsets=PIN['copy_offsets'],corruption_controls=negative,padder_stale_controls=padder_stale,padders=2,independent_rebases=rebases,neighbors_unchanged=38,pools_unchanged=True,source_installed=m.installed(),c_match_credit=0)
 (OUT/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
