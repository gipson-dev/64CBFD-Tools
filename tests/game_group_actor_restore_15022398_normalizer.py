"""Pinned four-access permutation of an unexposed private table-pointer word."""
import hashlib,json,struct
def normalize(data,refs):
 if hashlib.sha256(data).hexdigest()!='970f61a8c0462bb04c8124501c599d4b1a9610748e4225c4bf25ce613c2beb19':raise ValueError('Group actor restore source words changed')
 if hashlib.sha256(json.dumps(refs,sort_keys=True).encode()).hexdigest()!='0481b54ff57df652108dac18860e799a27d50079f5c237a841a68702119be303':raise ValueError('Group actor restore bindings changed')
 words=list(struct.unpack('>100I',data))
 for i in(24,30,34,37):
  if words[i]>>26 not in(35,43)or words[i]>>21&31!=29 or words[i]&65535!=40:raise ValueError('Table pointer home changed')
  words[i]=(words[i]&0xffff0000)|44
 return struct.pack('>100I',*words),refs
