"""Independent disjoint-store proof, without importing the normalizer."""
import struct
def proof(raw,truth):
 a,b=[list(struct.unpack('>99I',p[0]))for p in(raw,truth)];assert raw[1]==truth[1];assert all(x==y for i,(x,y)in enumerate(zip(a,b))if i not in(17,18));assert a[17:19]==b[17:19][::-1]
 def store(w):
  op,rs,rt=w>>26,w>>21&31,w>>16&31;offset=((w&65535)^32768)-32768;assert rs==29
  if op==40:return'GPR',rt,offset,1
  assert op==57;return'FPR',rt,offset,4
 left,right=map(store,a[17:19]);assert sorted((left,right))==[('FPR',0,136,4),('GPR',14,177,1)]
 assert set(range(left[2],left[2]+left[3])).isdisjoint(range(right[2],right[2]+right[3]));assert all(0<=offset and offset+size<=184 for _,_,offset,size in(left,right));assert 184%8==0 and 136%4==0
 assert not any(raw[1].get(i*4)for i in(17,18));branches=[];returns=[]
 for i,w in enumerate(a):
  op=w>>26
  if op in(1,4,5,6,7,20,21,22,23):
   target=i+1+(((w&65535)^32768)-32768);assert target not in(17,18)and i+1 not in(17,18);branches.append((i,target))
  if op==3:returns.append(i+2);assert i+2 not in(17,18)and i+1 not in(17,18)
  if op==2:raise AssertionError('Unexpected unbound direct jump')
  if op==0 and w&63 in(8,9):assert w==0x03e00008
 assert a[0]==0x27bdff48 and a[1]==0xafbf0034
 # The disjoint writes commute for any GPR/FPR values when both valid stack
 # accesses succeed. No register or FP state changes. There is no provider
 # boundary inside. Raw intermediate faults are explicitly outside this claim.
 return dict(instructions=99,unchanged_words=97,disjoint_store_words=2,store_regions=[list(x)for x in(left,right)],equal_join_for_arbitrary_values_on_valid_stack=True,no_register_or_FPU_arithmetic_change=True,no_control_entry_or_delay_into_pair=True,branch_edges=branches,call_returns=returns,raw_fault_prefix_identity_claim=False,raw_instruction_fetch_word_identity_claim=False,normalizer_imported=False)
