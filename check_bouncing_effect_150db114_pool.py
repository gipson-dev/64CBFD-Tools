"""Verify the compact owner before binding its float pool to retail data."""
import argparse,hashlib,json,struct
from pathlib import Path
try:
 from .pad_generated_object import ELF_HEADER,SECTION_HEADER,parse_object,read_c_string
except ImportError:
 try:from pad_generated_object import ELF_HEADER,SECTION_HEADER,parse_object,read_c_string
 except ImportError:
  import sys
  sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
  from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,parse_object,read_c_string
NAME='func_150DB114'
def verify(path):
 path=Path(path);data=path.read_bytes();h=ELF_HEADER.unpack_from(data)
 if h[0][:6]!=b'\x7fELF\x01\x02' or h[1]!=1 or h[2]!=8:raise ValueError('Expected big-endian MIPS ELF32 relocatable object')
 hs=[SECTION_HEADER.unpack_from(data,h[6]+i*h[11])for i in range(h[12])];ns=hs[h[13]];names=data[ns[4]:ns[4]+ns[5]];rs=[(i,s)for i,s in enumerate(hs)if read_c_string(names,s[0])=='.rodata']
 if len(rs)!=1:raise ValueError('Expected one literal section')
 index,s=rs[0]
 if s[1]!=1 or s[2]!=2 or s[5]!=16:raise ValueError('Expected allocated non-writable 16-byte compiler pool')
 if data[s[4]:s[4]+16]!=bytes.fromhex('3F99999A3F4CCCCD3F4CCCCD00000000'):raise ValueError('Literal values, order or alignment changed')
 if any(x[1]in(4,9)and x[7]==index and x[5]for x in hs):raise ValueError('Literal pool cannot own relocations')
 if any(x[2]&2 and x[5] and read_c_string(names,x[0])not in('.text','.rodata','.reginfo')for x in hs):raise ValueError('Unexpected allocated owner data')
 mf=Path(__file__).parent/'experiments/game_bouncing_effect_150db114_manifest.json';m=json.loads(mf.read_bytes());text,functions,refs=parse_object(path)
 if NAME not in functions:raise ValueError('Missing bouncing effect body')
 f=functions[NAME];a=f['value'];body=text[a:a+f['size']]
 if len(body)!=452 or hashlib.sha256(body).hexdigest()!=m['raw_body_sha256']:raise ValueError('Compiler body changed; requalify pool binding')
 actual={str(i-a):[list(x)for x in v]for i,v in refs.items()if a<=i<a+f['size']}
 if actual!=m['raw_relocations']:raise ValueError('Literal binding/addends changed')
 if any(n=='.rodata'for i,v in refs.items()if not a<=i<a+f['size']for k,n in v):raise ValueError('Another function owns a pool reference')
 return dict(function=NAME,verified=True,body_words=113,literal_bytes=12,discarded_alignment_bytes=4,retail_symbols=['D_800A0BE4','D_800A0BE8','D_800A0BEC'],independent_HI_LO_pairs=True)
def bind_assembly(path):
 """Give each verified compiler literal its actual independent retail symbol.

 Relocation addends are transferred to symbols before padding. Keeping three
 symbols also preserves distinct MIPS HI/LO pairs at signed-low carry seams.
 No register, opcode, branch or non-relocation operand is replaced.
 """
 verify(path);text,functions,relocations=parse_object(path);f=functions[NAME];base=f['value'];refs={a:list(v)for a,v in relocations.items()};body=bytearray(text)
 for off,name in((4,'D_800A0BE4'),(8,'D_800A0BE4'),(0x28,'D_800A0BEC'),(0xD8,'D_800A0BEC'),(0xC4,'D_800A0BE8'),(0xD4,'D_800A0BE8')):
  a=base+off;values=refs[a]
  if len(values)!=1 or values[0][1]!='.rodata':raise ValueError('Unqualified literal binding')
  kind,_=values[0];refs[a]=[(kind,name)]
  if kind=='R_MIPS_LO16':struct.pack_into('>I',body,a,struct.unpack_from('>I',body,a)[0]&0xFFFF0000)
 starts={v['value']:n for n,v in functions.items()};ends={v['value']+v['size']:n for n,v in functions.items()};out=['.set noat','.set noreorder','.set gp=64','.text']
 for a in range(0,len(body),4):
  if a in ends:out.append('.size '+ends[a]+',.-'+ends[a])
  if a in starts:out.extend(['.globl '+starts[a],'.type '+starts[a]+',@function',starts[a]+':'])
  for kind,name in refs.get(a,()):out.append('.reloc ., '+kind+', '+name)
  out.append('.word 0x'+body[a:a+4].hex())
 if len(body)in ends:out.append('.size '+ends[len(body)]+',.-'+ends[len(body)])
 return '\n'.join(out)+'\n'
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('object',type=Path);p.add_argument('--bind-assembly',type=Path);a=p.parse_args()
 try:
  q=verify(a.object)
  if a.bind_assembly:a.bind_assembly.write_text(bind_assembly(a.object))
 except (ValueError,OSError)as e:p.exit(1,'Bouncing effect literal binding rejected: '+str(e)+'\n')
 print(json.dumps(q));return q
if __name__=='__main__':main()
