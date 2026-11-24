"""Pinned source-role normalization justified by independent functional-memory proof."""
import hashlib,json,struct
def normalize(data,refs):
 pins={'raw_sha256': 'e8cfd2280085a1018d52c99a4f9fefa9a5b74ffa9ed6be383827435a3f82dcab', 'bindings_sha256': '62711d8c5dec16a5c61f91f66f3b9fa79be358444773f2850e0f1ab69530a18e', 'selected_source_sha256': 'd40a735a196470f0099dd9a999642a11e60b31d0edc7d027ae3b627ee1e9221e'}
 if hashlib.sha256(data).hexdigest()!=pins['raw_sha256']or hashlib.sha256(json.dumps(refs,sort_keys=True).encode()).hexdigest()!=pins['bindings_sha256']:raise ValueError('State-motion source words or bindings changed')
 words=list(struct.unpack('>98I',data));assert words[4]==0x960e0076 and words[7]==0xa7ae0036 and words[34]==0x87ac0036 and words[52]==0x46006086
 order=[0,1,2,3,5,4,9,8,6,10,11,12,13,14,15,16,17,18,19,20,21,7,23,22,*range(24,68),71,76,78,79,81,83,68,69,80,72,73,74,75,70,77,82,*range(84,98)]
 assert len(order)==98 and sorted(order)==list(range(98));positions={src:dst for dst,src in enumerate(order)};out=[];bindings={}
 first={14:2,15:14,24:15,25:24,8:25,9:8,10:9,11:10}
 floating={0:2,2:0,4:18,6:4,8:6,10:8,12:0,14:12,16:2,18:16}
 overrides={66:{18:10},71:{4:16,18:10},76:{6:18,4:16},78:{6:18},79:{8:4},81:{10:6,8:4},83:{10:6},75:{18:8},77:{4:10,18:8},80:{6:16},82:{8:18,4:10,6:16},85:{8:18}}
 for src in order:
  dst=len(out);w=words[src];op=w>>26;rs=w>>21&31;rt=w>>16&31;fn=w&63;imm=w&65535
  gpr=first if src<34 else{12:2,13:11,3:13 if src<42 else 15,15:24,24:25}
  fp={}if src<34 else dict(floating)
  fp.update(overrides.get(src,{}))
  gf=();ff=()
  if op==0 and w:gf=(21,16,11)
  elif op==15:gf=(16,)
  elif op in(33,35,36,37,40,41,43,9,4,5,20,21):gf=(21,16)
  elif op in(49,57):gf=(21,);ff=(16,)
  elif op==17:
   if rs in(0,4):gf=(16,);ff=(11,)
   elif rs==20:assert fn==32;ff=(11,6)
   elif rs==16:ff=(16,11)if fn==60 else(11,6)if fn==6 else(16,11,6)
   else:assert rs==8
  for shift in gf:
   v=w>>shift&31;w=(w&~(31<<shift))|(gpr.get(v,v)<<shift)
  for shift in ff:
   v=w>>shift&31;w=(w&~(31<<shift))|(fp.get(v,v)<<shift)
  if src==4:w=(w&0x03ffffff)|(33<<26) # Same short bits; signed extension dies in SH.
  if src in(7,34):assert imm==54;w=(w&0xffff0000)|52
  if src==52:w=0 # Coalesced correction/clamped FP roles already share F0.
  if op in(4,5,20,21)or op==17 and rs==8:
   target=src+1+((imm^32768)-32768);w=(w&0xffff0000)|((positions[target]-dst-1)&65535)
  if src*4 in refs:bindings[dst*4]=refs[src*4]
  out.append(w)
 return struct.pack('>98I',*out),bindings
