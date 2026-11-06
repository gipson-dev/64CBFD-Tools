"""Lockstep symbolic memory/control proof over all acyclic branch paths."""
import struct
C=lambda x:('C',x&0xFFFFFFFF)
def expr(op,*args):
 if op in('add','and','or','eq'):args=tuple(sorted(args,key=repr))
 if op=='add'and args[0]==C(0):return args[1]
 return(op,*args)
def fields(w):
 op=w>>26;fn=w&63
 if op==0:return(16,11)if fn in(0,3)else(21,)if fn==8 else(21,16,11)
 if op==15:return(16,)
 if op==1:return(21,)
 return(21,16)
def step(w,r,mem):
 op,rs,rt,rd,sh,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;imm=((w&65535)^32768)-32768;event=None
 if op==0:
  if fn==8:return r,mem,('return',r[rs])
  if w==0:pass
  elif fn in(0,3):r[rd]=expr('shl'if fn==0 else'sra',r[rt],sh)
  elif fn in(33,35,36,37,42):r[rd]=expr({33:'add',35:'sub',36:'and',37:'or',42:'slt'}[fn],r[rs],r[rt])
  else:raise AssertionError(('R opcode',hex(w)))
 elif op==15:r[rt]=C((w&65535)<<16)
 elif op in(9,12):r[rt]=expr('add'if op==9 else'and',r[rs],C(imm if op==9 else w&65535))
 elif op in(35,43):
  addr=expr('add',r[rs],C(imm))
  if op==35:r[rt]=('load',mem,addr);event=('R',addr)
  else:event=('W',addr,r[rt]);mem=('store',mem,addr,r[rt])
 else:raise AssertionError(('opcode',hex(w)))
 r[0]=C(0);return r,mem,event

def prove(first,second,bindings):
    a=list(struct.unpack('>69I',first));b=list(struct.unpack('>69I',second))
    for ws in(a,b):
        for at,rows in bindings.items():
            kind,name=rows[0];value=int(name[2:],16)
            ws[at//4]=(ws[at//4]&0xFFFF0000)|(((value+32768)>>16)&65535 if kind=='R_MIPS_HI16'else value&65535)
    initial=[('arg',i)for i in range(32)];initial[0]=C(0);pending=[(0,initial[:],initial[:],('mem',),('mem',),None)];done=states=0
    while pending:
     pc,ra,rb,ma,mb,after_delay=pending.pop();assert 0<=pc<69*4;wa,wb=a[pc//4],b[pc//4];mask=sum(31<<s for s in fields(wa));assert wa&~mask==wb&~mask,(hex(pc),hex(wa),hex(wb),'non-register bits')
     op=wa>>26;states+=1
     if op in(1,4,5):
      assert after_delay is None
      if op==1:
       assert wa>>16&31 in(1,3);ca=('gez',ra[wa>>21&31]);cb=('gez',rb[wb>>21&31]);likely=wa>>16&31==3
      else:ca=expr('eq',ra[wa>>21&31],ra[wa>>16&31]);cb=expr('eq',rb[wb>>21&31],rb[wb>>16&31]);likely=False
      assert ca==cb,(hex(pc),'branch',ca,cb)
      dest=pc+4+4*(((wa&65535)^32768)-32768);assert dest>pc;always=op==4 and wa>>21&31==0 and wa>>16&31==0
      pending.append((pc+4,ra[:],rb[:],ma,mb,dest))
      if not always:pending.append((pc+8 if likely else pc+4,ra[:],rb[:],ma,mb,None if likely else pc+8))
      continue
     ra,ma,ea=step(wa,ra,ma);rb,mb,eb=step(wb,rb,mb);assert ea==eb,(hex(pc),'event',ea,eb)
     if ea and ea[0]=='return':
      assert after_delay is None;pending.append((pc+4,ra[:],rb[:],ma,mb,'return'));continue
     if after_delay=='return':assert ma==mb;done+=1;continue
     pending.append((pc+4 if after_delay is None else after_delay,ra,rb,ma,mb,None))
    if (states,done)!=(265,17):raise ValueError('Packed coordinate path geometry changed')
    return dict(states=states,paths=done,register_fields_only=True,ordered_memory_and_conditions=True)
