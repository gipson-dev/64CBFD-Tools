"""Texture halfword/remainder proof, retaining ordered FP/public writes."""
from pathlib import Path
import json
from tools.tests import game_side_ring_renderer_1519fe6c_seed_proof as seed
from tools.tests import game_side_ring_renderer_1519fe6c_opening_proof as opening
from tools.tests import game_record_initializer_150169a0_proof as e
from tools.tests import game_side_ring_renderer_1519fe6c_oracle as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms

def bounds(v):
 if isinstance(v,int):return e.signed(v),e.signed(v)
 if e.tagged(v,'LOAD'):return 0,(1<<(8*v[2]))-1
 if e.tagged(v,'AND') and isinstance(v[2],int) and v[2]<0x80000000:return 0,v[2]
 if e.tagged(v,'SEXT'):return -(1<<(v[1]-1)),(1<<(v[1]-1))-1
 if e.tagged(v,'LINEAR'):
  low=high=e.signed(v[1])
  for value,k in v[2]:
   assert 0<k<0x80000000;a,b=bounds(value);low+=a*k;high+=b*k
  assert -0x80000000<=low<=high<0x80000000;return low,high
 raise AssertionError(('no texture interval',v))

def mask(v,bits):
 if isinstance(v,int):return v&((1<<bits)-1)
 if e.tagged(v,'SEXT') and bits<=v[1]:return mask(v[2],bits)
 try:low,high=bounds(v)
 except AssertionError:pass
 else:
  if 0<=low<=high<(1<<bits):return v
 return e.bitop('AND',v,(1<<bits)-1)

def sext(v,bits):
 if isinstance(v,int):return ((v&((1<<bits)-1))^(1<<(bits-1)))-(1<<(bits-1))&e.U32
 if e.tagged(v,'AND') and v[2]==(1<<bits)-1:v=v[1]
 try:low,high=bounds(v)
 except AssertionError:pass
 else:
  if -(1<<(bits-1))<=low<=high<(1<<(bits-1)):return v
 return ('SEXT',bits,mask(v,bits))

def canonical(v):
 if e.tagged(v,'SEXT'):return sext(canonical(v[2]),v[1])
 if e.tagged(v,'AND') and v[2] in(255,65535):return mask(canonical(v[1]),8 if v[2]==255 else 16)
 return v

def disjoint(a,n,b,m):
 delta=e.add(a,e.scale(b,-1))
 return isinstance(delta,int) and all((delta+i-j)&e.U32 for i in range(n) for j in range(m))

class State(seed.State):
 def __init__(self,side):
  super().__init__(side);self.phase='texture';self.r[16]=('OUTPUT',);self.cache={}
  self.r[10 if side=='raw'else 9]=('PACKET',)
  self.r[7 if side=='raw'else 8]=('INDEX',)
  self.r[4 if side=='raw'else 10]=('PREVIOUS_TAG',);self.r[9 if side=='raw'else 7]=('TAG',)
  self.r[5]=mask(('PREVIOUS_ALPHA',),8) if side=='raw'else ('PREVIOUS_ALPHA',)
  self.r[11]=mask(('ALPHA',),8) if side=='raw'else ('ALPHA',);self.r[3]=2
  for off,name in((-36,'PX'),(-32,'PY'),(-28,'PZ'),(-24,'X'),(-20,'Y'),(-16,'Z')):self.store(('STACK',off),4,(name,))
  self.store(('STACK',-40 if side=='raw'else -76),4,('PREVIOUS_WIDTH',))
  for reg,name in((2,'DZ'),(6,'NEG_DZ'),(12,'DX'),(14,'INV'),(16,'CURRENT_WIDTH'),(18,'ONE'),(20,'DX'),(22,'DZ')):self.f[reg]=(name,)
  self.fcsr=('FCSR','texture');self.private_writes=[]
 def load(self,address,size,pool):
  if e.tagged(address,'STACK'):
   if size==2:
    values=[self.mem.get(address[1]+i,('PRIVATE_BYTE',address[1]+i)) for i in range(2)]
    if all(isinstance(v,int) for v in values):return values[0]*256+values[1]
    if all(e.tagged(v,'BYTE') for v in values) and [v[2] for v in values]==[8,0] and values[0][1]==values[1][1]:return mask(values[0][1],16)
    return ('HALF',tuple(values))
   return super().load(address,size,pool)
  e.plain(address);key=(address,size)
  if key not in self.cache:self.cache[key]=('LOAD',address,size,self.epoch)
  v=self.cache[key];self.trace.append(('READ',address,size,v));return v
 def store(self,address,size,value):
  if e.tagged(address,'STACK'):return super().store(address,size,value)
  value=mask(value,8*size);self.trace.append(('WRITE',address,size,value));self.epoch+=1
  self.cache={key:v for key,v in self.cache.items() if disjoint(key[0],key[1],address,size)}
  self.cache[address,size]=value

class Program(seed.Program):
 def step(self,s,w):
  super().step(s,w)
  s.r=[canonical(v) for v in s.r]

def relation(s):
 opening.saved(s)
 assert all(size==2 and off in(-92,-90,-88) for off,size in s.private_writes),('texture private write escape',s.private_writes)
 # Stable ordinary RAM can be read redundantly. Values/addresses/widths must
 # agree as a set; writes and FP/FCSR instructions retain their exact order.
 accesses=set(event for event in s.trace if event[0]=='READ')
 effects=[event for event in s.trace if event[0]!='READ']
 byte=lambda v:mask(v,8)
 live=(s.r[16],s.r[17],s.r[7 if s.side=='raw'else 8],s.r[2],s.r[3],byte(s.r[5]),byte(s.r[11]),s.r[4 if s.side=='raw'else 10],s.r[9 if s.side=='raw'else 7],tuple(sext(s.load(('STACK',off),2,b''),16) for off in(-92,-90,-88)),tuple(s.f[i] for i in(2,6,12,14,16,18,20,22)),s.r[14 if s.side=='raw'else 25],s.load(('STACK',-4),4,b''),s.load(('STACK',-8),4,b''),s.r[18] if s.side=='raw'else s.r[12])
 return accesses,effects,s.fp,s.fcsr,live

def prove(raw,retail):
 terms=Terms();results={}
 for side,words,start,stop in(('raw',raw,0x430,0x4F0),('retail',retail,0x42C,0x4E8)):
  results[side]=Program(words,terms).paths(start,{stop:'vertices'},State(side))
 a,b=results['raw'],results['retail']
 assert a.keys()==b.keys(),('texture path predicates',len(a),len(b),next(iter(a.keys()-b.keys()),None),next(iter(b.keys()-a.keys()),None))
 for key in a:
  left,right=relation(a[key]),relation(b[key])
  assert left==right,('texture transfer',key,left,right)
 return dict(symbolic_paths=len(a),signed_halfword_endpoints=True,negative_C_remainder_1024=True,stable_ordinary_read_values_and_known_disjoint_halfword_write=True,ordered_public_writes_and_FP_FCSR=True,duplicate_mapped_ordinary_reads_may_differ=True,raw_access_timing_and_fault_state_claimed=False,vertices_proved=False,whole_function=False,c_match_credit=0)

def main():
 p=g.programs();raw,retail=p['candidate'],p['retail'];report=prove(raw,retail);controls=[]
 reused=raw[:];assert reused[0x460//4]==0x854E0046;reused[0x460//4]=0x03007025
 assert prove(reused,retail)==report
 report['redundant_ordinary_read_reuse_positive_control']=True
 alternative=raw[:]
 for pc in range(0x430,0x498,4):
  w=alternative[pc//4];op,fn,fmt=w>>26,w&63,w>>21&31
  if op==0:fields=(16,11) if fn in(0,2,3) else (21,16,11) if fn in(33,35,36,37,42,43) else (11,) if fn in(16,18) else (21,16) if fn==25 else ()
  elif op==17:fields=(16,) if fmt in(0,4) else ()
  elif op in(49,57,1):fields=(21,)
  elif op==15:fields=(16,)
  else:fields=(21,16)
  for shift in fields:
   reg=w>>shift&31
   if reg in(14,15):w=(w&~(31<<shift))|((29-reg)<<shift)
  alternative[pc//4]=w
 assert alternative!=raw and prove(alternative,retail)=={k:v for k,v in report.items() if k!='redundant_ordinary_read_reuse_positive_control'}
 report['independent_scratch_allocation_positive_control']=True
 for name,pc,change in(
  ('texture-first-field',0x430,lambda w:w+2),
  ('texture-extent-field',0x43C,lambda w:w+2),
  ('halfword-comparison-width',0x44C,lambda w:w^(4<<26)),
  ('remainder-mask',0x468,lambda w:w^0x400),
  ('negative-remainder-adjustment',0x474,lambda w:w^0x400),
  ('texture-public-write-field',0x484,lambda w:w+2),
  ('texture-public-write-width',0x484,lambda w:w^(1<<26)),
  ('texture-midpoint',0x4AC,lambda w:w^(1<<6)),
  ('mode-six-gate',0x4B8,lambda w:w+1),
  ('ordered-FP-multiply-operands',0x4A0,lambda w:w^((8^12)<<11)^((8^12)<<16))):
  wrong=raw[:];wrong[pc//4]=change(wrong[pc//4]);assert wrong!=raw
  try:prove(wrong,retail)
  except AssertionError as error:
   reason=str(error);assert not any(x in reason for x in('unsupported','unbounded seed proof','escaped code')),('invalid texture control',name,reason)
   controls.append(dict(name=name,rejected=reason[:180]))
  else:raise AssertionError(('ineffective texture control',name))
 report['effective_controls']=controls;out=g.O;(out/'texture-proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
