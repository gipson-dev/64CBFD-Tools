"""Pinned shift-mask and temporary-register normalization, independently proved."""
import hashlib,json,struct
def normalize(data,refs):
 pins={'raw_sha256': 'b35a3250a0a6f1418bd5b59ce17c859f4d58d39de6f71ccdd9822b0c86eae6a9', 'bindings_sha256': 'a2d88387ed5df426ce5ec7d5feca4231b200e7d15a1016d2f18b44c547a42fd1', 'selected_source_sha256': 'a1c2efd39b065d52fc352d45cf62212b9306290f82be977c6760207d841d85fd'}
 if hashlib.sha256(data).hexdigest()!=pins['raw_sha256']or hashlib.sha256(json.dumps(refs,sort_keys=True).encode()).hexdigest()!=pins['bindings_sha256']:raise ValueError('Scene render source words or bindings changed')
 words=list(struct.unpack('>100I',data));assert words[31]==0x3278001f and words[36]==0x03191804
 order=[i for i in range(100)if i!=31];positions={src:dst for dst,src in enumerate(order)};out=[];bindings={}
 for src in order:
  dst=len(out);w=words[src];op=w>>26;rs=w>>21&31;rt=w>>16&31;fn=w&63;imm=w&65535
  reg={8:25,9:8,10:9,11:10,12:11,13:12,14:13,15:14,25:24 if src<=36 else 15}if 34<=src<=73 else{}
  fields=(21,16,11)if op==0 and w else(16,)if op==15 else(21,16)if op!=3 and w else()
  for shift in fields:
   v=w>>shift&31;w=(w&~(31<<shift))|(reg.get(v,v)<<shift)
  if src==36:w=(w&~(31<<21))|(19<<21) # SLLV already masks the original view to five bits.
  if op in(4,5,6,7,20,21,22,23):
   target=src+1+((imm^32768)-32768);assert target!=31;w=(w&0xffff0000)|((positions[target]-dst-1)&65535)
  if src*4 in refs:bindings[dst*4]=refs[src*4]
  out.append(w)
 return struct.pack('>99I',*out),bindings
