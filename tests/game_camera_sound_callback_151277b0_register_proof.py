"""Lockstep symbolic proof for this acyclic routine's GPR-only differences.

Identical memory prefixes have identical load terms, including arbitrary aliases.
Branches fork on identical predicates. Calls compare the recovered one-argument
ABI, then assign identical arbitrary public-memory and caller-clobber effects.
This checks allocation changes, not the C algorithm or floating hardware model.
"""
from pathlib import Path
import copy,json,struct,sys
from tools.experiments import game_camera_sound_callback_151277b0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY=0x151277B0;SIZE=496;HELPER=0x100111C8
def sym(op,*args):
 if op=='add'and args[1]==0:return args[0]
 if op=='or'and args[1]==0:return args[0]
 if op=='or'and args[0]==0:return args[1]
 if op=='and'and 0 in args:return 0
 if all(isinstance(a,int)for a in args):
  a=args[0];b=args[1]if len(args)>1 else 0
  return {'add':lambda:(a+b)&0xFFFFFFFF,'sub':lambda:(a-b)&0xFFFFFFFF,'or':lambda:a|b,'and':lambda:a&b,
   'sll':lambda:(a<<b)&0xFFFFFFFF,'srl':lambda:a>>b,'ltu':lambda:int(a<b)}[op]()
 return(op,*args)
def initial():return dict(r=[0]+[('input',i)for i in range(1,32)],f=[('fp',i)for i in range(32)],version=0,calls=0)
def step(w,s,pc):
 r=s['r'];f=s['f'];op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;fun=w&63
 imm=w&65535;si=(imm^32768)-32768;event=None
 def put(i,v):
  if i:r[i]=v
 if not w:pass
 elif op==0:
  if fun in(0,2):put(rd,sym('sll'if fun==0 else'srl',r[rt],w>>6&31))
  elif fun in(0x21,0x23,0x24,0x25):put(rd,sym({0x21:'add',0x23:'sub',0x24:'and',0x25:'or'}[fun],r[rs],r[rt]))
  else:raise AssertionError(('unsupported SPECIAL',hex(w),pc))
 elif op==9:put(rt,sym('add',r[rs],si))
 elif op==15:put(rt,imm<<16)
 elif op==13:put(rt,sym('or',r[rs],imm))
 elif op==11:put(rt,sym('ltu',r[rs],si&0xFFFFFFFF))
 elif op in(35,36,37,49):
  width={35:4,36:1,37:2,49:4}[op];address=sym('add',r[rs],si)
  value=('load',width,s['version'],address);event=('read',width,address)
  if op==49:f[rt]=value
  else:put(rt,value)
 elif op in(41,43,57):
  width=2 if op==41 else 4;address=sym('add',r[rs],si);value=f[rt]if op==57 else r[rt]
  event=('write',width,address,value);s['version']+=1
 elif op==17:
  if rs==0:put(rt,f[rd])
  elif rs==16 and fun in(2,13):f[w>>6&31]=('mul.s',f[rd],f[rt])if fun==2 else('trunc.w.s',f[rd])
  else:raise AssertionError(('unsupported COP1',hex(w),pc))
 else:raise AssertionError(('unsupported opcode',hex(w),pc))
 return event
def allowed_mask(w):
 op=w>>26;rs=w>>21&31
 if not w:return 0
 if op==0:return(31<<16)|(31<<11)if w&63 in(0,2)else(31<<21)|(31<<16)|(31<<11)
 if op==17:return 31<<16 if rs==0 else 0
 if op in(3,):return 0
 if op==15:return 31<<16
 assert op in(4,5,9,11,13,20,21,35,36,37,41,43,49,57),(op,hex(w))
 return(31<<21)|(31<<16)if op not in(49,57)else 31<<21
def prove(a,b):
 assert len(a)==len(b)==124
 changed=[]
 for i,(x,y)in enumerate(zip(a,b)):
  assert x&~allowed_mask(x)==y&~allowed_mask(y),('non-GPR difference',i,hex(x),hex(y))
  if x!=y:changed.append(i)
 pending=[(0,initial(),initial(),())];paths=0;visited=set();branch_predicates=0;calls=0
 while pending:
  i,x,y,history=pending.pop();steps=0
  while True:
   assert 0<=i<124 and steps<250;steps+=1;visited.add(i);u,v=a[i],b[i];op=u>>26
   if op in(4,5,20,21):
    def pred(w,s):
     values=(s['r'][w>>21&31],s['r'][w>>16&31]);return('eq'if op in(4,20)else'ne',*values)
    p,q=pred(u,x),pred(v,y);assert p==q,('branch predicate',i,p,q);branch_predicates+=1
    outcomes=(True,False)
    if p[1]==p[2]:outcomes=(p[0]=='eq',)
    elif isinstance(p[1],int)and isinstance(p[2],int):outcomes=((p[1]==p[2])==(p[0]=='eq'),)
    for take in outcomes:
     xx,yy=copy.deepcopy(x),copy.deepcopy(y)
     if take or op not in(20,21):
      visited.add(i+1);assert step(a[i+1],xx,i+1)==step(b[i+1],yy,i+1),('branch delay event',i)
     destination=i+1+(((u&65535)^32768)-32768)if take else i+2
     assert destination>i,('unexpected loop',i,destination)
     pending.append((destination,xx,yy,history+((i,take),)))
    break
   if op==3:
    target=((ENTRY+4*i+4)&0xF0000000)|((u&0x3FFFFFF)<<2);assert target==HELPER
    x['r'][31]=y['r'][31]=ENTRY+4*i+8
    visited.add(i+1);assert step(a[i+1],x,i+1)==step(b[i+1],y,i+1)
    assert x['r'][4]==y['r'][4],('release ABI',i)
    assert x['r'][29]==y['r'][29];assert x['version']==y['version']
    calls+=1
    for s in(x,y):
     s['calls']+=1;s['version']+=1
     for n in(1,2,3,*range(4,16),24,25):s['r'][n]=('callee-clobber',s['calls'],n)
     for n in range(20):s['f'][n]=('callee-fp-clobber',s['calls'],n)
    i+=2;continue
   if op==0 and u&63==8:
    assert u>>21&31==31;visited.add(i+1);assert step(a[i+1],x,i+1)==step(b[i+1],y,i+1)
    for n in(2,*range(16,24),28,29,30,31):assert x['r'][n]==y['r'][n],('return ABI',history,n)
    assert x['f'][20:]==y['f'][20:];paths+=1;break
   assert step(u,x,i)==step(v,y,i),('memory event',i,history)
   assert x['version']==y['version'];i+=1
 assert visited==set(range(124)),sorted(set(range(124))-visited)
 return dict(paths=paths,covered_words=len(visited),static_unreachable_offsets=[],changed_GPR_only_words=changed,
  identical_branch_predicates=branch_predicates,checked_call_boundaries=calls,all_alias_memory_prefixes_equal=True,
  limits='Acyclic decoded instruction graph, abstract float operations and recovered one-argument release ABI; independent C/native and provider semantics are separate gates.')
def run():
 rom=(root/'conker/conker.us.bin').read_bytes();retail=struct.unpack_from('>124I',rom,0x154C60)
 raw=bound_blob(*payload(out/'qualified-source/candidate.o','func_151277B0'),{'func_100111C8':HELPER,'D_800BE9E4':0x800BE9E4})
 r=prove(raw,retail);controls=[]
 for index in(2,24,76,69):
  bad=list(raw);bad[index]^=1<<16;failed=False
  try:prove(bad,retail)
  except AssertionError:failed=True
  assert failed,index;controls.append({'changed_register_word':index,'rejected':True})
 r.update(effective_controls=controls,source_installed=packet.installed(),matching_credit=0)
 (out/'register-proof.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':run()
