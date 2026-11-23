"""Derived role/slot allocation, ABI argument-home lifetime and branch schedule."""
import hashlib,json,struct
RAW='546054121161f9657a0130668abcb782e3dde0c2e9289e2079b215a5cf3cf915'
BINDINGS='73b39b560c653372cf70ff49bc62c52c066b0cbd2b2107c493b8f4cafcce9051'
ORDER=[*range(15),17,16,15,*range(18,22),'state-load',*range(23,34),38,35,36,34,37,*range(39,79),84,*range(79,84),85,86,87,'primary-zero',*range(88,108),'secondary-zero',*range(108,131),'state-store',*range(131,147)]
EXTRA={'state-load':0x8FB60070,'primary-zero':0x00001025,'secondary-zero':0x00001025,'state-store':0xAFB60070}
def normalize(data,refs):
 if hashlib.sha256(data).hexdigest()!=RAW or hashlib.sha256(json.dumps(refs,sort_keys=True).encode()).hexdigest()!=BINDINGS:raise ValueError('Layout slot source words or bindings changed')
 ws=[w[0]for w in struct.iter_unpack('>I',data)];positions={old:i for i,old in enumerate(ORDER)};assert len(ws)==147 and len(ORDER)==150 and set(x for x in ORDER if isinstance(x,int))==set(range(147))-{22}
 out=[];bindings={};roles={17:16,18:17,19:18,20:19,21:20,22:21}
 for old in ORDER:
  at=len(out)
  if isinstance(old,str):out.append(EXTRA[old]);continue
  w=ws[old];op=w>>26
  if old in(3,9):
   reg,offset=(20,0x28)if old==3 else(21,0x2C);w=(w&0xFC00FFFF)|(29<<21)|(reg<<16);w=(w&0xFFFF0000)|offset
  elif old==4:w=(w&~(31<<11))|(20<<11)
  elif old==15:w=(w&~(31<<11))|(16<<11)
  elif old==17:w=(w&~(31<<11))|(21<<11)
  elif 20<=old<=134 and op not in(2,3):
   fields=(21,16,11)if op==0 else(21,16)
   for shift in fields:
    reg=w>>shift&31;replacement=roles.get(reg,2 if reg==16 and 87<=old<=125 else reg)
    if old in(61,74)and shift==11:replacement=22
    w=(w&~(31<<shift))|(replacement<<shift)
  if op in(4,5,20,21):
   target=old+1+(((ws[old]&65535)^32768)-32768)
   if old==21:w=(w&0x03FFFFFF)|(5<<26);target=24
   elif old==33:target=34
   elif old==80:target=85
   elif old==85:target='secondary-zero'
   w=(w&0xFFFF0000)|((positions[target]-at-1)&65535)
  if old*4 in refs:bindings[at*4]=refs[old*4]
  out.append(w)
 return struct.pack('>150I',*out),bindings
