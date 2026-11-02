"""Three original bounded caller windows and complete aligned direct-call census."""
import itertools,json,struct
from tools.tests.game_embedded_integer_oscillator_integration import aligned_hits
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
WINDOWS=((0x150254B0,0x52960,8,(0x150265B0,0x150265B4)),(0x150997D0,0xC6C80,4,(0x150997E0,)),(0x15070114,0x9D5C4,12,(0x81234560,)))
def qualify(root,output,g):
 rom=(root/'conker/conker.us.bin').read_bytes();sites=aligned_hits(rom,0x0C000000|(g.ENTRY>>2&0x3FFFFFF));assert sites==[0x52970,0x9D5DC,0xC6C88],sites
 assert not aligned_hits(rom,g.ENTRY)
 entry,s,roots=g.programs(output,0);records=[]
 for index,(start,off,words,ends)in enumerate(WINDOWS):
  window=struct.unpack_from('>%dI'%words,rom,off);count=0
  for owner,active,tag,mutation,outcome,phase in itertools.product((0,g.OWNER),(0,1,256),(0,128,255),(0,3),(0,1),(0,8)):
   c=g.Case(owner=owner,active=active,tag=tag,ignored1=255,ignored2=1,mutation=mutation,outcome=outcome,phase=phase)
   initial=g.fixture(c,s);g.put(initial,g.STACK+phase+0x16C,owner);g.put(initial,0x800D154C,owner)
   expected,calls,packets=g.reference(initial,c,s,home=g.STACK+phase-(24 if index==2 else 0))
   if owner or index:calls=[(entry,(owner,255,1)),*calls]
   models=[]
   for codewords in roots:
    connected=dict(zip(range(entry,entry+240,4),codewords));connected.update({end:0 for end in ends})
    m=g.Oracle(window,initial,c,s,start,connected=connected,target=entry);m.r[17]=m.before[17]=owner
    if index==2:m.r[31]=m.before[31]=ends[0]
    m.code=WindowCode(m.code,m);m.code.ends=ends
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller window boundary not reached')
    assert m.r[17]==owner
    if index==0 and owner:assert m.r[2]==1
    models.append(m)
   g.compare(models,c,expected,calls,packets);count+=1
  records.append(dict(entry=hex(start),words=words,boundaries=[hex(x)for x in ends],cases=count,executions=count*2,void_return_not_consumed=True))
 assert struct.unpack_from('>4I',rom,0xC6C90)==(0x02202025,0x240500FF,0x0C000000|(0x151D6BFC>>2&0x3FFFFFF),0x24060001)
 report=dict(success=True,original_callers=3,all_aligned_ROM_JAL_sites=sites,literal_target_pointers=0,windows=records,total_cases=sum(v['cases']for v in records),executions=sum(v['executions']for v in records),three_argument_ABI_verified=True,first_caller_null_gate=True,return_value_unused_in_both_windows=True,whole_parents_executed=False,gameplay_acceptance_claimed=False)
 (output/'private-callers-v6.json').write_text(json.dumps(report,indent=2)+'\n');return report
