"""Closed call-delay expansion and temporary register value proof."""
from pathlib import Path
import hashlib,json,struct
PIN=json.loads((Path(__file__).resolve().parents[1]/'experiments/game_actor_attached_emitter_150bb760_manifest.json').read_text())
def derive(raw,refs,truth,trefs):
 expected={int(k):[tuple(x)for x in v]for k,v in PIN['refs'].items()};retail={int(k):[tuple(x)for x in v]for k,v in PIN['retail_refs'].items()}
 assert hashlib.sha256(raw).hexdigest()==PIN['raw_sha256']and refs==expected
 assert hashlib.sha256(truth).hexdigest()==PIN['retail_unbound_sha256']and trefs==retail
 assert len(raw)==1016 and len(truth)==1020
 source=list(struct.unpack('>254I',raw));retail=list(struct.unpack('>255I',truth));assert source[0]==retail[0]==0x27bdff08
 at=0x154//4;assert source[at:at+2]==[0x0c000000,0xa3a900ec]and refs[0x154]==[('R_MIPS_26','func_150ADA20')]
 assert 0x158 not in refs
 # Exchange only the independent byte store and call, then restore retail's
 # empty call delay. Neither SP nor T1 is changed by the JAL instruction.
 def target(i):return i if i<at else at+1 if i==at else at if i==at+1 else i+1
 control=[]
 for i,w in enumerate(source):
  if w>>26 in(4,5,6,7,20,21,22,23):
   imm=w&65535;imm=imm-65536 if imm&32768 else imm;dest=i+1+imm;assert dest not in(at,at+1)
   control.append((i,dest,target(dest)-(target(i)+1)))
 out=source[:at]+[source[at+1],source[at],0]+source[at+2:]
 for i,dest,delta in control:out[target(i)]=(source[i]&~65535)|(delta&65535)
 moved={target(k//4)*4:list(v)for k,v in refs.items()};assert moved==trefs
 left=[('entry',i)for i in range(32)];right=list(left);gl=list(left);gr=list(left);rewritten=[];integer_words=[];commuted=[]
 allowed={8,9,10,11,12,13,14,15,24,25}
 def scalar(a,b,i,uses,defines,fields):
  mask=0
  for shift in fields:
   x,y=a>>shift&31,b>>shift&31
   if x!=y:assert x in allowed and y in allowed,('fixed GPR changed',i,x,y)
   mask|=31<<shift
  for shift in uses:assert gl[a>>shift&31]==gr[b>>shift&31],('integer producer',i,shift,gl[a>>shift&31],gr[b>>shift&31])
  for shift in defines:
   x,y=a>>shift&31,b>>shift&31
   if x or y:assert x and y;gl[x]=gr[y]=('integer',i)
  if any((a>>v&31)!=(b>>v&31)for v in fields):integer_words.append(i*4)
  return mask
 pending=None
 for i,(a,b)in enumerate(zip(out,retail)):
  # Calls consume arguments and clobber temporaries after their delay word.
  if pending is not None and i==pending+2:
   assert all(gl[k]==gr[k]for k in range(4,8)),('helper arguments',pending)
   for k in(1,2,3,*range(4,16),24,25):gl[k]=gr[k]=('integer call',pending,k)
   for k in range(20):left[k]=right[k]=('call',pending,k)
   pending=None
  op=a>>26;assert op==b>>26,(i,hex(a),hex(b))
  if op==3:
   assert a==b and moved.get(4*i)==trefs.get(4*i)
   gl[31]=gr[31]=('link',i)
   assert pending is None;pending=i
   continue
  if op==0x31:
   mask=(31<<16)|scalar(a,b,i,(21,),(),(21,));assert(a&~mask)==(b&~mask)
   x,y=a>>16&31,b>>16&31;assert x<20 and y<20;left[x]=right[y]=('load',i)
  elif op==0x39:
   mask=(31<<16)|scalar(a,b,i,(21,),(),(21,));assert(a&~mask)==(b&~mask)
   x,y=a>>16&31,b>>16&31;assert left[x]==right[y],('store value',i,left[x],right[y])
  elif op==17:
   fmt=a>>21&31;assert fmt==b>>21&31
   if fmt==4:
    mask=(31<<11)|scalar(a,b,i,(16,),(),(16,));assert(a&~mask)==(b&~mask)
    x,y=a>>11&31,b>>11&31;assert x<20 and y<20;left[x]=right[y]=('mtc1',i)
   else:
    assert fmt in(16,20)and(a&63)==(b&63)
    fn=a&63;fs,ft,fd=a>>11&31,a>>16&31,a>>6&31;ts,tt,td=b>>11&31,b>>16&31,b>>6&31
    assert fd<20 and td<20
    if fn in(0,1,2,3)and fmt==16:
     before=(left[fs],left[ft]);after=(right[ts],right[tt])
     if before!=after:assert fn in(0,2)and before==after[::-1];commuted.append((i*4,fn))
    else:
     assert fn in(7,32)and left[fs]==right[ts]and ft==tt
    mask=(31<<6)|(31<<11)|(31<<16);assert(a&~mask)==(b&~mask)
    left[fd]=right[td]=('expression',i)
  else:
   if op in(0x20,0x21,0x23,0x24,0x25):mask=scalar(a,b,i,(21,),(16,),(21,16))
   elif op in(0x28,0x29,0x2b):mask=scalar(a,b,i,(21,16),(),(21,16))
   elif op in(8,9,12,13,14):mask=scalar(a,b,i,(21,),(16,),(21,16))
   elif op==15:mask=scalar(a,b,i,(),(16,),(16,))
   elif op in(4,5,20,21):mask=scalar(a,b,i,(21,16),(),(21,16))
   elif op in(6,7,22,23):mask=scalar(a,b,i,(21,),(),(21,))
   elif op==0:
    fn=a&63;assert fn==b&63
    if fn in(0,2,3):mask=scalar(a,b,i,(16,),(11,),(16,11))
    elif fn==8:mask=scalar(a,b,i,(21,),(),(21,))
    else:assert fn in(0x21,0x23,0x24,0x25,0x26,0x2a,0x2b);mask=scalar(a,b,i,(21,16),(11,),(21,16,11))
   else:raise AssertionError(('unhandled scalar opcode',i,op))
   assert(a&~mask)==(b&~mask),('non-register change',i,hex(a),hex(b))
   if a!=b:out[i]=(a&~mask)|(b&mask)
   continue
  if a!=b:out[i]=(a&~mask)|(b&mask);rewritten.append(4*i)
 assert commuted==[(0x2f4,0)],commuted
 assert len(rewritten)==20 and out==retail
 patches=[]
 for i,w in enumerate(source):
  # CSV rows describe output order, whereas target() tracks instruction identity.
  j=i if i in(at,at+1)else target(i);new=out[j]
  if w!=new or i==at+1:
   patches.append(dict(offset=i*4,expected=w,replacement=new,expected_relocations=refs.get(i*4,[]),replacement_relocations=moved.get(j*4,[]),insert_after=0 if i==at+1 else None))
 assert sum(x['insert_after']is not None for x in patches)==1
 assert len(patches)==38
 return struct.pack('>255I',*out),moved,dict(guards=patches,insertions=1,omissions=0,float_register_words=rewritten,integer_register_words=integer_words,commutative_add_word=0x2f4,closed_branch_updates=[i*4 for i,_,delta in control if(source[i]&65535)!=(delta&65535)],all_stored_float_values_proven=True,all_integer_values_and_helper_arguments_proven=True,helper_FP_arguments=False)
