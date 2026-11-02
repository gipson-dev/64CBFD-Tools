"""Complete static call census and original 101-word attached-point caller."""
import itertools,json,struct
from tools.tests.game_embedded_integer_oscillator_integration import aligned_hits

def qualify(root,output,g):
 rom=(root/'conker/conker.us.bin').read_bytes();old=g.old
 jal=aligned_hits(rom,0x0C000000|(g.ENTRY>>2&0x3FFFFFF));jumps=aligned_hits(rom,0x08000000|(g.ENTRY>>2&0x3FFFFFF));pointers=aligned_hits(rom,g.ENTRY)
 assert jal==[0x1C0C8C]and not jumps and not pointers,(jal,jumps,pointers)
 g.configure(root,output);roots=g.programs(output)
 caller=struct.unpack_from('>101I',rom,0x1C0B10)
 image=(root/'conker/build/conker.us.elf').read_bytes();at=g.elf_slot_offset(image,old.ENTRY,404);assert image[at:at+404]==rom[0x1C0B10:0x1C0CA4]
 point=struct.unpack_from('>49I',rom,0x16F7C4);at=g.elf_slot_offset(image,old.POINT,196);assert image[at:at+196]==rom[0x16F7C4:0x16F888]
 points=dict(zip(range(old.POINT,old.POINT+196,4),point));count=entered=0;seen=set()
 for seed,mode,extra,mutation,phase,fixed,gate in itertools.product((0,3),(0,128,255),(0,1),(0,3,16,27),(0,8),(0,1),range(4)):
  c=old.Case(seed=seed,mode=mode,extra=extra,mutation=mutation,phase=phase,fixed=fixed,owner=0 if gate==1 else old.OWNER,active=0 if gate==2 else 1,attached=0 if gate==3 else old.MATRIX)
  initial=old.fixture(c,g.symbols)
  for i in range(16*512):initial[g.CHILD+i]=(i*37+c.seed*7+91)&255
  expected,calls,packets=old.reference(initial,c,g.symbols);factory_home=old.STACK+phase-152
  spawns=[];copies=[]
  if packets:
   expected,children,spawns,copies=g.expected(expected,packets[0][1],c,input_address=packets[0][0],factory_home=factory_home);calls+=children;entered+=1
  models=[]
  for index,words in enumerate(roots):
   connected=dict(points);connected.update(zip(range(g.ENTRY,g.ENTRY+852,4),words))
   memory=g.seed_raw(initial,factory_home)if index==2 else initial
   m=g.Machine(caller,memory,c,raw=index==2,entry=old.ENTRY,extra_code=connected).run();models.append(m);seen.update(m.visits)
  g.compare(models,c,expected,calls,spawns,copies,home=factory_home);count+=1
 assert set(range(old.ENTRY,old.ENTRY+404,4))<=seen and set(points)<=seen
 report=dict(success=True,all_aligned_ROM_JAL_sites=jal,tail_jump_sites=jumps,literal_target_pointers=pointers,original_callers=1,complete_caller_words=101,complete_point_resolver_words=49,cases=count,executions=count*3,factory_entered_cases=entered,all_caller_and_point_words_executed=True,all_caller_gates_and_byte_modes_and_zero_one_extra=True,real_wrapper_copy_chain_connected=True,original_raw_normalized_complete_pipeline_outputs_equal=True,gameplay_acceptance_claimed=False)
 (output/'private-caller-v19.json').write_text(json.dumps(report,indent=2)+'\n');return report
