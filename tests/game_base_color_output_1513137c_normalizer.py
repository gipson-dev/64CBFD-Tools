"""Bind the verified private eight-entry table to protected retail data."""
import hashlib,json,struct
RAW='45fa937ad1df5b6378007fba529811c57562285fdd2dff8fd75ef8ae85b65e5f'
BINDINGS='0de3ec4d2c382d8fa53b7da58813ea24d729a28c4f37b0ec23b93c42938d909b'
def normalize(data,refs):
 assert len(data)==408 and hashlib.sha256(data).hexdigest()==RAW
 assert hashlib.sha256(json.dumps(refs,sort_keys=True).encode()).hexdigest()==BINDINGS
 words=list(struct.unpack('>102I',data));assert words[8]==0x3c010000 and words[10]==0x8c2f0024;words[10]=0x8c2f0000
 return struct.pack('>102I',*words),{32:[('R_MIPS_HI16','jtbl_800A3800')],40:[('R_MIPS_LO16','jtbl_800A3800')]}
