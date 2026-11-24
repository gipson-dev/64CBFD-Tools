"""All selector bytes, ordered halfword aliases and distinct private tables."""
import itertools,json,struct
from tools.experiments import game_base_color_output_1513137c_match as p
from tools.tests import game_mode_color_output_15131514_oracle as old
from tools.tests.game_base_color_output_1513137c_tables import OFFSETS
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
Case=old.Case;put,read,STACK,RECORD,OUTPUT=old.put,old.read,old.STACK,old.RECORD,old.OUTPUT
r,o=p.ROOT,p.OUT;ENTRY=0x1513137c;TABLE=0x800a3800;PRIVATE=0x800a1000;PARENT=0x1513164c
def symbols():return{'jtbl_800A3800':TABLE,'.rodata':PRIVATE}
def fixture(c,entry=ENTRY,s=None):
 s=symbols()if s is None else s;m=old.fixture(c);m[RECORD+0x70]=c.mode;m[RECORD+0x71]=(c.mode+c.seed*17)&255
 for i in range(80):m[s['.rodata']+i]=0
 for i,offset in enumerate(old.OFFSETS):put(m,s['.rodata']+4*i,old.ENTRY+offset)
 for i,offset in enumerate(OFFSETS):put(m,s['.rodata']+36+4*i,entry+offset);put(m,s['jtbl_800A3800']+4*i,entry+offset)
 return m
def channels(initial,pointers,record=RECORD,little=False):
 m=initial.copy();red,green,blue,alpha=pointers;mode=m[record+0x70];products=[]
 def store(a,v):
  for i in range(2):m[a+i]=v>>(8*(i if little else 1-i))&255
 def reload(a):return int.from_bytes(bytes((m[a],m[a+1])),'little'if little else'big',signed=True)
 def product(a,b):v=m[record+a]*m[record+b];products.append(v);return v>>8
 if mode in(1,5):
  store(blue,0);value=reload(blue);store(green,value);store(red,value)
 elif mode in(4,6):
  store(alpha,0);value=reload(alpha);store(blue,value);store(green,value);store(red,value);return m,products
 elif mode in(2,7,8):
  for at,field in((red,0x24),(green,0x25),(blue,0x26)):store(at,m[record+field])
 elif mode==3:
  for at,field in((red,0x28),(green,0x29),(blue,0x2a)):store(at,m[record+field])
 else:
  for at,field in((red,0x24),(green,0x25),(blue,0x26)):store(at,product(field,0x2c))
  store(alpha,0);return m,products
 store(alpha,product(0x27,0x2b)if mode in(1,2,3)else m[record+0x2b]if mode in(5,7)else 0);return m,products
def programs(s=None):
 s=symbols()if s is None else s;return{label:bound_blob(*payload(o/path,p.FUNCTION),s)for label,path in dict(raw='selected-final/candidate.o',generic='qualified-owner/generic.o',generated='qualified-owner/generated.o',retail='original-target.o').items()}
class Oracle(old.Oracle):
 def __init__(self,words,initial,c,entry=ENTRY,s=None,connected=None,arguments=None):super().__init__(words,initial.copy(),c,entry=entry,s=symbols()if s is None else s,connected=connected,arguments=arguments);self.target_modes=[]
 def record_call(self,t):
  assert t in(ENTRY,old.ENTRY,PARENT),hex(t);a=tuple(self.arguments(9 if t==PARENT else 5));self.calls.append((t,a));self.events.append(('CALL',t,a))
  if t==ENTRY:self.target_modes.append(self.memory[a[-1]+0x70])
def verify(m,initial,c):
 expected=initial.copy();put(expected,STACK+c.phase-4,m.before[16]);expected,products=channels(expected,old.outputs(c));assert m.memory==expected,(c,'memory');assert m.calls==[];assert(m.hi,m.lo)==((0,products[-1])if products else(0xbeefface,0x13579bdf));assert m.r[16:24]==m.before[16:24]and m.r[29:]==m.before[29:]and m.f==m.before_f
def canonical(events,c,s=None,mode=None):
 s=symbols()if s is None else s;result=[];count=0
 mode=c.mode if mode is None else mode
 for event in events:
  if event[0]=='R'and event[1]==s['.rodata']+36+4*(mode-1)and 1<=mode<=8:
   assert event[2]==4;event=('R',s['jtbl_800A3800']+4*(mode-1),*event[2:]);count+=1
  result.append(event)
 assert count==(1 if 1<=mode<=8 else 0);return result
def state(m,c,raw=False,s=None):
 mode=m.target_modes[0]if m.target_modes else c.mode
 return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.calls,canonical(m.events,c,s,mode)if raw else m.events,canonical(m.trace,c,s,mode)if raw else m.trace,m.current_pc,m.delay_of,m.all_accesses,m.target_modes)
def cases():
 for mode,seed,layout in itertools.product(range(256),(0,5),range(10)):yield Case(mode=mode,seed=seed,layout=layout,phase=8*(seed&1))
 for mode,alias in itertools.product(range(256),(1,2,3)):yield Case(mode=mode,alias=alias,seed=3)
def main():
 ws=programs();rom=(r/'conker/conker.us.bin').read_bytes();assert struct.pack('>102I',*ws['retail'])==rom[0x15e82c:0x15e9c4];count=0;visits=set()
 for c in cases():
  initial=fixture(c);models=[]
  for label,words in ws.items():m=Oracle(words,initial,c);m.run();verify(m,initial,c);models.append((label,m))
  assert all(state(m,c,label=='raw')==state(models[-1][1],c)for label,m in models);visits.update(models[-1][1].visits);count+=1
 assert visits==set(range(ENTRY,ENTRY+408,4)),sorted(set(range(ENTRY,ENTRY+408,4))-visits)
 report=dict(cases_per_stream=count,streams=4,all_256_selector_bytes=True,distinct_private_and_protected_tables=True,private_table_read_correspondence_only=True,all_registers_and_all_memory_equal=True,HI_LO_products_independently_verified=True,all_102_words_visited=True,incoming_home_aliases_guest_only=True,native_void_result_claim=False,source_installed=p.installed(),matching_credit=0);(o/'guest.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps(report),flush=True);return report
def faults():
 count=0;ws={n:w for n,w in programs().items()if n!='raw'}
 for mode,layout in itertools.product((*range(9),255),(0,5,9)):
  c=Case(mode=mode,layout=layout);initial=fixture(c);full=Oracle(ws['retail'],initial,c);full.run()
  for cut in range(full.all_accesses):
   models=[]
   for words in ws.values():
    m=Oracle(words,initial,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError('Fault boundary did not fire')
    models.append(m)
   assert all(state(m,c)==state(models[0],c)for m in models);count+=1
 report=dict(normalized_retail_prefix_triples=count,raw_private_table_prefix_excluded=True,portable_C_fault_claim=False);(o/'faults.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());return report

def wrapper_reference(initial,args,home,saved_s0,return_address):
 m=initial.copy();put(m,home-4,return_address)
 for i,value in enumerate(args[:4]):put(m,home+4*i,value)
 first=tuple(read(m,home+4*i)for i in range(4,8))+(read(m,home+32),);put(m,home-16,first[-1]);put(m,home-36,saved_s0);m=old.channels(m,first[-1],first[:4]);second=tuple(read(m,home+4*i)for i in range(4))+(read(m,home+32),);put(m,home-16,second[-1]);put(m,home-36,saved_s0);m,_=channels(m,second[:4],second[-1]);return m,[(old.ENTRY,first),(ENTRY,second)]
def callers():
 from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
 rom=(r/'conker/conker.us.bin').read_bytes();parent=list(struct.unpack_from('>24I',rom,0x15eafc));color=dict(zip(range(old.ENTRY,old.ENTRY+312,4),struct.unpack_from('>78I',rom,0x15e9c4)));counts=[]
 # Both actual parent call sites are bounded at their first continuation.
 for begin,end in((0x15130f54,0x15130f74),(0x15130fe0,0x15131020)):
  fragment=struct.unpack_from('>'+str((end-begin)//4)+'I',rom,begin-0x15000000+0x2d4b0);count=0
  for mode,phase in itertools.product(range(256),(0,8)):
   c=Case(mode=mode,phase=phase,seed=3);initial=fixture(c);home=STACK+phase;base=tuple(home+x for x in(0xea,0xe8,0xe6,0xe4));other=tuple(home+x for x in(0xe2,0xe0,0xde,0xdc));expected=initial.copy();tag=0x1234abcd;fp=0x3f800000;put(expected,home+0x100,tag);put(expected,home+0xbc,fp)
   if begin==0x15130f54:put(expected,home+16,RECORD);put(expected,home-4,RECORD);expected,_=channels(expected,base);calls=[(ENTRY,(*base,RECORD))]
   else:
    args=(*base,*other,RECORD)
    for i,value in enumerate(args[4:],4):put(expected,home+4*i,value)
    expected,inner=wrapper_reference(expected,args,home,RECORD,end);calls=[(PARENT,args),*inner]
   models=[]
   for label,words in programs().items():
    code={**color,**dict(zip(range(ENTRY,ENTRY+408,4),words)),**dict(zip(range(PARENT,PARENT+96,4),parent)),end:0};m=Oracle(fragment,initial,c,entry=begin,connected=code);m.r[16]=m.before[16]=RECORD;m.r[9]=tag;m.f[18]=fp;m.before_f=m.f[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Caller continuation not reached')
    assert m.memory==expected and m.calls==calls,(hex(begin),c,'memory/calls');assert m.r[31]==end and m.r[29]==home and m.r[16:24]==m.before[16:24]and m.f==m.before_f;models.append((label,m))
   assert all(state(m,c,label=='raw')==state(models[-1][1],c)for label,m in models);count+=1
  counts.append(dict(entry=hex(begin),original_window_words=len(fragment),cases_per_stream=count))
 count=0
 for mode,layout,phase in itertools.product(range(256),(0,3,8,9),(0,8)):
  c=Case(mode=mode,layout=layout,phase=phase,seed=5);initial=fixture(c);home=STACK+phase;base=old.outputs(c);other=tuple(RECORD+v-64 if v<192 else OUTPUT+v-216 for v in old.LAYOUTS[(layout+3)%10]);args=(*base,*other,RECORD)
  for i,value in enumerate(args):put(initial,home+4*i,value)
  models=[]
  for label,words in programs().items():
   code={**color,**dict(zip(range(ENTRY,ENTRY+408,4),words))};m=Oracle(parent,initial,c,entry=PARENT,connected=code,arguments=args);m.run();expected,calls=wrapper_reference(initial,args,home,m.before[16],0xdead0000);assert m.memory==expected and m.calls==calls,(c,'wrapper');models.append((label,m))
  assert all(state(m,c,label=='raw')==state(models[-1][1],c)for label,m in models);count+=1
 report=dict(parent_windows=counts,original_wrapper_words=24,original_color_helper_words=78,complete_wrapper_cases_per_stream=count,all_nine_arguments_and_late_reloads_verified=True,typed_wrapper_additional_matching_credit=0,parent_full_function_claim=False,native_void_result_claim=False);(o/'callers.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());return report
if __name__=='__main__':main();print(faults())
