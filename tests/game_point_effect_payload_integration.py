"""Complete direct-call census, two original windows and one complete wrapper."""
import itertools,json,struct
from tools.tests.game_embedded_integer_oscillator_integration import aligned_hits
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
WINDOWS=((0x15029188,0x56638,8,(0x15029BA4,)),(0x150997C0,0xC6C70,4,(0x150997D0,)),(0x150700E4,0x9D594,12,(0x81234560,)))
def qualify(root,output,g):
 rom=(root/'conker/conker.us.bin').read_bytes();sites=aligned_hits(rom,0x0C000000|(g.ENTRY>>2&0x3FFFFFF));assert sites==[0x56648,0x9D5AC,0xC6C78],sites;assert not aligned_hits(rom,g.ENTRY)
 entry,s,roots=g.programs(output,0);records=[]
 for index,(start,off,words,ends)in enumerate(WINDOWS):
  window=struct.unpack_from('>%dI'%words,rom,off);count=0
  for owner,active,attached,mode,mutation,phase in itertools.product((0,g.OWNER),(0,1,256),(0,g.MATRIX),(0,128,255),(0,3,4),(0,8)):
   c=g.Case(owner=owner,active=active,attached=attached,mode=mode if index==0 else 255,extra=0 if index==0 else 1,mutation=mutation,phase=phase,seed=mode%8)
   initial=g.fixture(c,s);home=g.STACK+phase;g.put(initial,home+0x764,owner);initial[home+0x773]=mode;g.put(initial,0x800D154C,owner)
   expected,calls,packets=g.reference(initial,c,s,home=home-(24 if index==2 else 0))
   if owner or index:calls=[(entry,(owner,c.mode,c.extra)),*calls]
   models=[]
   for code in roots:
    connected=dict(zip(range(entry,entry+404,4),code));connected.update({end:0 for end in ends});m=g.Oracle(window,initial,c,s,start,connected=connected,target=entry);m.r[17]=m.before[17]=owner
    if index==2:m.r[31]=m.before[31]=ends[0]
    m.code=WindowCode(m.code,m);m.code.ends=ends
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller boundary not reached')
    if index==0:assert m.r[2]==1
    models.append(m)
   g.compare(models,c,expected,calls,packets);count+=1
  records.append(dict(entry=hex(start),words=words,cases=count,executions=count*3))
 assert struct.unpack_from('>4I',rom,0xC6C80)==(0x02202025,0x240500FF,0x0C000000|(0x151937F4>>2&0x3FFFFFF),0x24060001)
 report=dict(success=True,original_callers=3,all_aligned_ROM_JAL_sites=sites,literal_target_pointers=0,windows=records,total_cases=sum(v['cases']for v in records),executions=sum(v['executions']for v in records),dynamic_first_mode_byte_and_zero_extra=True,other_callers_FF_and_one=True,whole_large_parents_executed=False,complete_wrapper_executed=True,gameplay_acceptance_claimed=False)
 (output/'private-callers-v11.json').write_text(json.dumps(report,indent=2)+'\n');return report
