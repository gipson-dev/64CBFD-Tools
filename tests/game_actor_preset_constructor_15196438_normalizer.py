"""Closed preset-field schedule, temporary roles and unsigned-byte ABI word."""
import hashlib,json,struct
RAW='15ce0c6323a3c836ff2b656fbcbae1b9879cd91c5c65bd38aaa34532cac4b0cc'
BINDINGS='c25c2c974a4e0c17c37ee7fd8b5c1e71f27ee6144c30d2b278208d0e291d8d37'
ORDER=[*range(61),63,61,64,65,66,67,68,62,78,72,69,71,73,74,75,76,77,70,93,*range(79,93),*range(94,196)]
FIELD_ROLES={63:11,61:10,64:14,65:15,66:8,67:25,68:24,62:9,78:12,72:11,69:10,73:14,74:15,75:8,76:25,77:24,70:9,93:12}
def field(w,shift,value):return(w&~(31<<shift))|((value&31)<<shift)
def normalize(data,refs):
 if hashlib.sha256(data).hexdigest()!=RAW or hashlib.sha256(json.dumps(refs,sort_keys=True).encode()).hexdigest()!=BINDINGS:raise ValueError('Actor preset source words or bindings changed')
 ws=[v[0]for v in struct.iter_unpack('>I',data)];assert len(ws)==196 and sorted(ORDER)==list(range(196));out=[];bindings={}
 for old in ORDER:
  w=ws[old]
  if old in FIELD_ROLES:w=field(w,16,FIELD_ROLES[old])
  elif old==134:
   assert w==0x8FAB0100
   # A canonical unsigned-byte argument consumes only incoming argument2's
   # low byte. Retail also zero-extends the complete outgoing o32 word.
   w=((w&0x03FFFFFF)|(36<<26))+3
  elif old in(163,175):w=field(w,16,3)
  elif old==166:w=field(field(w,21,3),16,5)
  elif old==167:w=field(w,21,5)
  elif old==168:w=field(w,16,5)
  elif old==172:w=field(w,16,3)
  elif old in(177,180):w=field(w,21,3)
  if old*4 in refs:bindings[len(out)*4]=refs[old*4]
  out.append(w)
 return struct.pack('>196I',*out),bindings
