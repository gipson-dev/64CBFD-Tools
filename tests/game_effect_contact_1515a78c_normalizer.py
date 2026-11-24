"""Pinned source-derived pointer/home/register schedule; independent proof."""
import hashlib,json,struct
def normalize(data,refs):
 pins={'raw_sha256': 'd256d622d17510efcedc4c73bab4830375705620af744d68183149a470ffb455', 'bindings_sha256': '992cb5549229e6e274d4de303e5434e5032a3a041e61cebf9217f7e54af20662', 'source_sha256': '36139aea0837249cd5be08e295bc6be30d5824c645b55154e9a11ab7d954efce'}
 if hashlib.sha256(data).hexdigest()!=pins['raw_sha256'] or hashlib.sha256(json.dumps(refs,sort_keys=True).encode()).hexdigest()!=pins['bindings_sha256']:raise ValueError('Effect contact source or bindings changed')
 words=list(struct.unpack('>98I',data));order=list(range(22))+[('pointer',81),23,22]+list(range(24,30))+[('pointer-save',83)]+list(range(30,77))+[('pointer-reload',92)]+list(range(77,98));positions={v:i for i,v in enumerate(order)if isinstance(v,int)};out=[];bindings={};entries=[]
 def field(w,shift,v):return(w&~(31<<shift))|(v<<shift)
 for source in order:
  i=len(out)
  if isinstance(source,tuple):
   tag,src=source;w=words[src]
   if tag=='pointer':assert w==0x27a80040;w=field(field(w,21,16),16,24);w=(w&0xffff0000)|0xa8
   elif tag=='pointer-save':assert w==0xafa80010;w=field(w,16,24);w=(w&0xffff0000)|0x34
   else:assert w==0x8fa20030;w=field(w,16,10);w=(w&0xffff0000)|0x34
   entries.append(dict(output=i,derived_from=src,role=tag))
  else:
   src=source;w=words[src];op=w>>26;imm=w&65535
   if src in(6,48,50,57,59,60):assert imm==79;w=(w&0xffff0000)|75
   if src in(25,27,31,38,40,52,58,81):assert imm in(64,68,72);w=(w&0xffff0000)|(imm-4)
   if src==32:assert w==0xc60000c8;w=field(w,21,24);w=(w&0xffff0000)|32
   if src==33:assert w==0x460a0032;w=field(field(w,11,10),16,0)
   if src in(48,57,60):w=field(w,16,8)
   if src==61:assert words[src]==0x1700001e;w=field(w,21,8);w=(w&0x03ffffff)|(21<<26)
   if src in(62,70,74,92):assert words[src] in(0xafb80030,0x8fa20030);w=(36<<26)|(29<<21)|(2<<16)|75
   if src==71:w=field(w,16,9)
   if src==73:w=field(w,21,9)
   if src==79:assert w==0xc60600a8;w=field(w,21,10);w&=0xffff0000
   if src in(81,83):w=field(w,16,11)
   if src in(84,87):w=field(w,16,12)
   if src in(88,91):w=field(w,16,13)
   branch=op in(4,5,6,7,20,21,22,23) or(op==17 and words[src]>>21&31==8)
   if branch:
    target=93 if src==61 else src+1+((imm^32768)-32768);w=(w&0xffff0000)|((positions[target]-i-1)&65535)
   if 4*src in refs:bindings[4*i]=refs[4*src]
   entries.append(dict(output=i,derived_from=src,role='source'))
  out.append(w)
 return struct.pack('>101I',*out),bindings
