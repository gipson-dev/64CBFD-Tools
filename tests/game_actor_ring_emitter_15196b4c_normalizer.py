"""Closed source-derived operation projection, independently transfer-proved.

The source emits all arithmetic, public accesses and calls. Operand/index rows
reallocate registers/private homes and schedule these source operations. The
independent whole-body relation checks the complete values, calls, read epochs,
saved frame and normal-execution FCSR rather than assuming this correspondence.
The four allocation-surplus operations are two NOPs, one quiet repeated ordinary
RAM read, and one private spill after reallocation. They are not declared dead
instructions of the unchanged raw stream; the whole storage relation qualifies
their simultaneous removal and rewiring. No fault-prefix equality for raw C.
"""
from pathlib import Path
from collections import Counter
import hashlib,json,struct
from tools.experiments import game_actor_ring_emitter_15196b4c_match as p
PIN=json.loads((p.TOOLROOT/'experiments/game_actor_ring_emitter_15196b4c_projection.json').read_text())
from tools.experiments.game_curve_emitter_151a11e4_match import fields as basefields
def fields(w):
 if w>>26 in(20,21):return[(21,'g'),(16,'g')]
 if w>>26==0 and w&63==9:return[(21,'g'),(11,'g')]
 return basefields(w)
def branch(w):return w>>26 in(4,5,6,7,20,21)or w>>26==17 and w>>21&31==8
def private(w):return w>>26 in(9,35,43,49,53,57,61)and w>>21&31==29
def mask(w):return sum(31<<s for s,k in fields(w)if k=='f'or w>>s&31 not in(0,29,31))|(65535 if private(w)or branch(w)else 0)
def key(w,refs):
 roles=tuple((s,'zero'if w>>s&31==0 else'sp'if w>>s&31==29 else'ra'if w>>s&31==31 else'variable')for s,k in fields(w)if k=='g')
 return(w&~mask(w),tuple(refs),roles)
def normalize(data,refs):
 expected={int(k):[tuple(v)for v in rows]for k,rows in PIN['bindings'].items()}
 if hashlib.sha256(data).hexdigest()!=PIN['raw_sha256']or refs!=expected:raise ValueError('Emitter source words or relocation bindings changed')
 source=struct.unpack('>387I',data);out=[];bindings={};used=[]
 for row in PIN['rows']:
  i=row['source'];w=source[i];bits=row['operands'];assert bits&~mask(w)==0
  v=(w&~mask(w))|bits
  if 'old_private_offset'in row:assert private(w)and ((w&65535)^32768)-32768==row['old_private_offset']
  if 'target'in row:
   assert branch(w)and 0<=row['target']<383
   delta=row['target']-len(out)-1;assert -32768<=delta<32768;v=(v&0xffff0000)|(delta&65535)
  assert key(w,refs.get(4*i,()))==key(v,refs.get(4*i,()))
  if 4*i in refs:bindings[4*len(out)]=refs[4*i]
  used.append(i);out.append(v)
 omitted=PIN['omitted'];assert len(out)==383 and len(used)==len(set(used))and sorted(used+omitted)==list(range(387))
 assert [source[i]for i in omitted]==[int(w,16)for w in PIN['omitted_words']]
 assert sum(source[i]==0 for i in omitted)==2 and Counter(source[i]>>26 for i in omitted if source[i])=={49:1,57:1}
 return struct.pack('>383I',*out),bindings
