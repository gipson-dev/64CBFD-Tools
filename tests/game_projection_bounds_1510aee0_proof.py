"""Ordered FP DAGs, full symbolic memory and all branch/alias paths."""
import itertools
def add(p,n):
 if isinstance(p,int):return(p+n)&0xffffffff
 if p[0]in('S','M','O'):return(p[0],p[1]+n)
 return('DYN',p,n)

def endpoints(words,px,py,matrix=('M',0)):
 r=[('R',i)for i in range(32)];r[0]=0;r[4]=matrix;r[5],r[6],r[7]=('X',),('Y',),('Z',);r[29]=('S',0);r[31]=('RET',)
 f=[('F',i)for i in range(32)];mem={add(matrix,i*4):('MAT',i)for i in range(16)}
 mem.update({('S',i*4):v for i,v in enumerate((('HOME0',),('HOME1',),('HOME2',),('HOME3',),('NEAR',),('FAR',),('SX',),('SY',),px,py))})
 states=[(0,r,f,mem,None,{})];result={};steps=0
 def execute(w,r,f,m,condition):
  if not w:return condition
  op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;imm=((w&65535)^32768)-32768
  if op==9:r[rt]=add(r[rs],imm)
  elif op==15:r[rt]=(w&65535)<<16
  elif op==0 and fn==37:
   # The late-pointer negative control uses a real OR-with-zero move.
   assert rs==0 or rt==0;r[rd]=r[rs]if rt==0 else r[rt]
  elif op in(35,43,49,57):
   address=add(r[rs],imm)
   if op in(35,49):
    value=m.get(address,('MEM',address))
    if op==35:r[rt]=value
    else:f[rt]=value
   else:m[address]=r[rt]if op==43 else f[rt]
  elif op==17:
   if rs==4:f[rd]=r[rt]
   elif rs==16:
    if fn in(0,1,2,3):f[fd]=(('ADD','SUB','MUL','DIV')[fn],f[rd],f[rt])
    elif fn in(5,7):f[fd]=('ABS'if fn==5 else'NEG',f[rd])
    elif fn in(60,62):condition=('LT'if fn==60 else'LE',f[rd],f[rt])
    else:raise AssertionError(hex(w))
   else:raise AssertionError(hex(w))
  else:raise AssertionError(hex(w))
  return condition
 while states:
  pc,r,f,m,cond,facts=states.pop();steps+=1;assert steps<10000
  w=words[pc//4];op,rs,rt,fn=w>>26,w>>21&31,w>>16&31,w&63
  if op==0 and fn==8:
   assert r[rs]==('RET',);cond=execute(words[pc//4+1],r,f,m,cond)
   key=tuple(sorted(facts.items(),key=repr));answer=(r[2],r[29],r[16:24],r[28:32],f[20:],m,cond)
   assert key not in result;result[key]=answer;continue
  if op in(4,20)or(op==17 and rs==8):
   if op==17:predicate=cond;positive=bool(rt&1);likely=bool(rt&2)
   else:predicate=('EQ',r[rs],r[rt]);positive=True;likely=op==20
   fixed=None
   if op in(4,20)and r[rs]==r[rt]:fixed=True
   if op in(4,20)and isinstance(r[rs],int)and isinstance(r[rt],int):fixed=r[rs]==r[rt]
   choices=(facts[predicate],)if predicate in facts else(fixed,)if fixed is not None else(False,True)
   for value in choices:
    nr,nf,nm,nfacts=r[:],f[:],m.copy(),facts.copy();nc=cond
    if fixed is None:nfacts[predicate]=value
    taken=value==positive
    if taken or not likely:nc=execute(words[pc//4+1],nr,nf,nm,nc)
    dest=pc+4+4*(((w&65535)^32768)-32768)if taken else pc+8
    states.append((dest,nr,nf,nm,nc,nfacts))
  else:
   cond=execute(w,r,f,m,cond);states.append((pc+4,r,f,m,cond,facts))
 return result

def prove(raw,normal):
    assert len(raw)==93 and len(normal)==97 and raw[:4]==normal[:4] and raw[-2:]==normal[-2:]
    aliases=(0,('O',0),('O',4),('M',0),('M',52),('S',-16),('S',12),('S',16),('S',32),('S',36))
    count=paths=0
    for px,py,matrix in itertools.product(aliases,aliases,(('M',0),('S',0),('S',-32))):
        x=endpoints(raw,px,py,matrix);y=endpoints(normal,px,py,matrix)
        assert x==y,(px,py,matrix,len(x),len(y));count+=1;paths+=len(x)
    assert count==300 and paths==2235
    return dict(alias_layouts=count,symbolic_terminal_paths=paths,ordered_fp_dags=True,full_memory_and_saved_state=True)

def main():
    import json,struct
    from tools.experiments import game_projection_bounds_1510aee0_match as source
    from tools.experiments.game_paired_ground_constructor_match import payload
    raw=list(struct.unpack('>93I',payload(source.OUT/'selected.o',source.NAME)[0]));normal=list(struct.unpack('>97I',source.normalize(payload(source.OUT/'selected.o',source.NAME)[0],{})[0]));report=prove(raw,normal)
    for offset,word in((0x4c,normal[0x4c//4]&~63|62),(0x80,normal[0x80//4]&0xffff0000|0x24)):
        changed=normal[:];assert changed[offset//4]!=word;changed[offset//4]=word
        assert endpoints(raw,('O',0),('O',4))!=endpoints(changed,('O',0),('O',4))
    changed=normal[:];assert changed[0x144//4]==0 and changed[0x150//4]==0x8fa20034
    changed[0x144//4]=0x8fa80034;changed[0x150//4]=0x01001025
    assert endpoints(raw,('O',0),('O',4))==endpoints(changed,('O',0),('O',4))
    assert endpoints(raw,('S',36),('O',4))!=endpoints(changed,('S',36),('O',4))
    report['independent_controls']=3;report['late_pointer_alias_control_killed']=True
    (source.OUT/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
