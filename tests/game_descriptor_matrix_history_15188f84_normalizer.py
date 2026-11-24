"""Pin a closed S2/S3 lifetime swap and three commutative operands."""
import hashlib,json,struct
RAW='810ec836e85bec4ed2598fa4be8ce9bd396133e6ed508f785cf75fb9684a57c3'
REFS='9080413d5fc5b9a11215fe263570dc8b0c60cd52eb65d37a2e74090ae1ae5dd8'
def normalize(data,refs):
 if hashlib.sha256(data).hexdigest()!=RAW:raise ValueError('Descriptor history instructions changed')
 if hashlib.sha256(json.dumps(refs,sort_keys=True).encode()).hexdigest()!=REFS:raise ValueError('Descriptor history bindings changed')
 words=list(struct.unpack('>101I',data))
 for i in range(4,92):
  if i==8:continue
  w=words[i];op=w>>26
  fields=(21,16,11)if op==0 else(21,16)if op in(1,4,5,6,7,9,12,13,14,15,20,21,22,23,35,36,37,40,41,43)else()
  for shift in fields:
   reg=(w>>shift)&31
   if reg in(18,19):w=(w&~(31<<shift))|((37-reg)<<shift)
  words[i]=w
 words[1],words[8]=words[8],words[1]
 for i in(40,80,81):
  w=words[i];rs=w>>21&31;rt=w>>16&31;words[i]=(w&~((31<<21)|(31<<16)))|(rs<<16)|(rt<<21)
 return struct.pack('>101I',*words),refs
