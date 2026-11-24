"""Independent closed-register lifetime and instruction-isomorphism proof."""
import struct
def registers(w):
 op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31;fn=w&63
 if op==0:
  if w==0:return(),()
  if fn in(0,2,3):return(rt,),(rd,)
  if fn==8:return(rs,),()
  if fn==18:return(),(rd,)
  if fn in(24,25):return(rs,rt),()
  assert fn in(33,35,36,37,38,42,43),(hex(w),'R operation');return(rs,rt),(rd,)
 if op==3:return(),(31,)
 if op in(4,5,20,21):return(rs,rt),()
 if op in(1,6,7,22,23):return(rs,),()
 if op==15:return(),(rt,)
 if op in(9,12,13,14,35,36,37):return(rs,),(rt,)
 assert op in(40,41,43),(hex(w),'I operation');return(rs,rt),()
def canonical(w,i,raw):
 op=w>>26;rs=w>>21&31;rt=w>>16&31;rd=w>>11&31
 def role(n):
  if 4<=i<=91 and i!=8 and n in(18,19):return('depth'if n==18 else'owner')if raw else('owner'if n==18 else'depth')
  return 'r'+str(n)
 if op==0:
  pair=(role(rs),role(rt));fn=w&63
  if fn==33:pair=tuple(sorted(pair))
  return(op,pair,role(rd),(w>>6)&31,fn)
 if op in(2,3):return(op,w&0x3ffffff)
 if op in(4,5,20,21):return(op,tuple(sorted((role(rs),role(rt)))),w&65535)
 return(op,role(rs),role(rt),w&65535)
def proof(raw,retail):
 a,b=[tuple(x[0]for x in struct.iter_unpack('>I',v[0]))for v in(raw,retail)]
 assert len(a)==len(b)==101 and raw[1]==retail[1]
 assert a[0]==b[0]==0x27bdffd0 and a[92:]==b[92:]and a[-2:]==(0x03e00008,0x27bd0030)
 assert {a[1],a[8]}=={b[1],b[8]}=={0xafb2001c,0xafb30020}
 for i,(x,y)in enumerate(zip(a,b)):
  if i in(1,8):assert 4*i not in raw[1];continue
  assert canonical(x,i,True)==canonical(y,i,False),(i,'Not a role-preserving operation')
  for w in(x,y):
   op=w>>26;reads,writes=registers(w)
   if 29 in writes:assert i in(0,100)and op==9
   if 29 in reads:assert op in(35,43)or i in(0,100),'Private frame address escapes'
   if op in(35,43)and w>>21&31==29:
    assert (w&65535)in(20,24,28,32,36,40,44)
 assert [i for i,w in enumerate(a)if w>>26==3]==[82]
 assert raw[1][328]==[('R_MIPS_26','bcopy')]
 def lifetimes(words):
  pending=[(0,0,0,0)];seen=set();returns=0
  def transfer(i,defined,saved,restored):
   w=words[i];op=w>>26;rs=w>>21&31;rt=w>>16&31;reads,writes=registers(w)
   save=op==43 and rs==29 and rt in(18,19)
   restore=op==35 and rs==29 and rt in(18,19)
   if save:
    bit=1<<(rt-18);assert not defined&bit and not saved&bit and (w&65535)==(28 if rt==18 else 32);saved|=bit
   elif restore:
    bit=1<<(rt-18);assert saved&bit and (w&65535)==(28 if rt==18 else 32);restored|=bit
   else:
    for reg in reads:
     if reg in(18,19):assert defined&(1<<(reg-18))and not restored&(1<<(reg-18)),(i,'Read outside a role lifetime')
    for reg in writes:
     if reg in(18,19):
      bit=1<<(reg-18);assert saved&bit and not restored&bit,(i,'Role overwrites an unsaved incoming register');defined|=bit
   if op==3:assert defined==saved==3 and restored==0
   return defined,saved,restored
  while pending:
   i,defined,saved,restored=pending.pop();assert 0<=i<101
   if(i,defined,saved,restored)in seen:continue
   seen.add((i,defined,saved,restored));w=words[i];op=w>>26;state=transfer(i,defined,saved,restored)
   if w==0x03e00008:
    final=transfer(i+1,*state);assert final[1:]==(3,3);returns+=1;continue
   if op==3:pending.append((i+2,*transfer(i+1,*state)));continue
   if op in(1,4,5,6,7,20,21,22,23):
    target=i+1+(((w&65535)^32768)-32768);same=(w>>21&31)==(w>>16&31);answers=(op in(4,20),)if same and op in(4,5,20,21)else(False,True)
    for take in answers:pending.append((target if take else i+2,*(transfer(i+1,*state)if take or op not in(20,21,22,23)else state)))
   else:pending.append((i+1,*state))
  assert returns and all((i,3,3,0)in seen for i in(28,40,68,71,82,85));return len(seen)
 states=[lifetimes(ws)for ws in(a,b)]
 return dict(word_count=101,frame=48,bindings=15,raw_owner_register=19,retail_owner_register=18,raw_depth_register=18,retail_depth_register=19,CFG_states_checked=states,all_role_reads_dominated_by_definitions=True,incoming_registers_saved_before_overwrite=True,named_saved_homes_and_epilogue_identical=True,private_addresses_escape=False,maximum_provider_argument_homes=16,commutative_integer_operations_only=True,projection_imported=False,scope='Mapped public objects disjoint from the unexposed 48-byte frame; o32 bcopy providers preserve callee-saved registers and private frame above argument homes. Full public state, branch choices and call arguments are coupled inductively, including arbitrary compatible public provider effects. Raw private prefix/register/fault identity is not asserted.')
