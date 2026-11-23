"""Qualify four local ORI/copy coalescences independently of retail scheduling.

This intermediate is private; it does not write production guards or source.
"""
from pathlib import Path
import hashlib,json,struct,sys

PAIRS=((189,193,24),(217,218,12),(240,241,14),(262,263,25))
def registers(w):
 op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;fn=w&63
 if not w:return set(),set()
 if op==0:
  if fn in(0,2,3):return{rt}-{0},{rd}-{0}
  if fn in(33,35,36,37,38,42,43):return{rs,rt}-{0},{rd}-{0}
  if fn==8:return{rs},set()
  raise AssertionError(('Unhandled ALU register effects',hex(w)))
 if op==3:return{4,5,6,7,29},{31}
 if op==2:return set(),set()
 if op==1:return{rs},set()
 if op in(4,5,6,7,20,21,22,23):return{rs,rt}-{0},set()
 if op==17:
  if rs==4:return{rt},set()
  if rs==0:return set(),{rt}
  return set(),set()
 if op==15:return set(),{rt}
 if op in(9,10,11,12,13,14,0x20,0x21,0x23,0x24,0x25):return{rs}-{0},{rt}-{0}
 if op in(0x28,0x29,0x2B):return{rs,rt}-{0},set()
 if op==0x31:return{rs}-{0},set()
 if op==0x39:return{rs}-{0},set()
 raise AssertionError(('Unhandled register effects',hex(w)))
def branch(w):return w>>26 in(1,4,5,6,7,20,21,22,23)or w>>26==17 and w>>21&31==8
def control(w):return branch(w)or w>>26 in(2,3)or w>>26==0 and w&63 in(8,9)
def transform(raw,refs):
 assert hashlib.sha256(raw).hexdigest()=='8160dc7ead367f9cef2e0af47b7aa43ad74852b7aaffc078b06643b00d6bc4b6'
 a=list(struct.unpack('>341I',raw));proof=[]
 for definition,copy,temp in PAIRS:
  w=a[definition];assert w>>26==13 and w&65535==0x2CA0 and w>>16&31==temp and w>>21&31==5
  assert a[copy]==(temp<<21|5<<11|37)and not control(a[copy-1])
  for i in range(definition+1,copy):
   reads,writes=registers(a[i]);assert not control(a[i])and 5 not in reads|writes and temp not in writes,(copy,i)
  # The temporary is a caller-clobbered register. No use escapes before the
  # next call, including its executed delay instruction; A1 supplies the mode.
  call=next(i for i in range(copy+1,len(a))if a[i]>>26==3)
  assert temp in(*range(1,16),24,25)
  for i in range(copy+1,call+2):
   reads,writes=registers(a[i]);assert temp not in reads,(copy,i)
   if i<call:assert not control(a[i]),(copy,i)
  proof.append(dict(ori_index=definition,copy_index=copy,temporary=temp,next_call=call,old_A1_not_used_between=True,temporary_has_no_escaping_use=True))
 omitted={v[1]for v in PAIRS};order=[i for i in range(len(a))if i not in omitted];where={i:j for j,i in enumerate(order)}
 assert len(order)==337 and a[0]==0x27BDFF58
 defs={d for d,c,t in PAIRS};out=[];newrefs={};branches=[]
 for j,i in enumerate(order):
  w=a[i]
  if i in defs:w=(w&~(31<<16))|5<<16
  if branch(w):
   dst=i+1+(((w&65535)^32768)-32768);assert dst in where,(i,dst)
   delta=where[dst]-j-1;assert -32768<=delta<=32767;w=(w&0xFFFF0000)|(delta&65535)
   branches.append(dict(origin=i,target=dst,new_origin=j,new_target=where[dst]))
  assert w>>26!=2,'Unexpected internal absolute jump'
  out.append(w)
  if 4*i in refs:newrefs[4*j]=refs[4*i]
 assert all(4*i not in refs for i in omitted)
 return struct.pack('>337I',*out),newrefs,order,proof,branches
