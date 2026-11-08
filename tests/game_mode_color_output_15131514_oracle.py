"""Mode color channels, actual jump edges, aliases and complete original wrapper."""
from dataclasses import dataclass,replace
import itertools,re,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ENTRY,PARENT,FOLLOW=0x15131514,0x1513164C,0x1513137C
RECORD,OUTPUT=0x30000,0x50000
OFFSETS=(52,76,128,160,52,160,196,100,224)
LAYOUTS=((216,218,220,222),(216,216,216,216),(222,220,218,216),(100,218,220,222),(216,102,220,222),(216,218,106,222),(108,218,220,222),(216,218,220,106),(176,218,220,222),(216,216,108,108))
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
 mode:int=0
 seed:int=0
 layout:int=0
 phase:int=0
 alias:int=0
def symbols(i=0):return {'jtbl_800A3820':(0x800A3820,0x80027FFC,0x90018000)[i]}
def outputs(c):
 if c.alias:
  home=STACK+c.phase
  return (home,home+4,home+8,home+12)if c.alias==1 else(home+(32 if c.alias==2 else 16),OUTPUT+2,OUTPUT+4,OUTPUT+6)
 return tuple(RECORD+v-64 if v<192 else OUTPUT+v-216 for v in LAYOUTS[c.layout])
def fixture(c=Case(),s=None,entry=ENTRY):
 s=symbols()if s is None else s;m={STACK+i:(i*17+c.seed*13+0xA5)&255 for i in range(-512,512)}
 for p,n in((RECORD-32,192),(OUTPUT-32,96)):
  m.update({p+i:(i*29+c.seed*53+0x5A)&255 for i in range(n)})
 m[RECORD+0x71]=c.mode
 for i,off in enumerate(OFFSETS):put(m,s['jtbl_800A3820']+4*i,entry+off)
 put(m,STACK+c.phase+16,RECORD)
 return m
def channels(memory,record,pointers,little=False):
 m=dict(memory);r,g,b,a=pointers;mode=m[record+0x71]
 def store(p,v):
  for i in range(2):m[p+i]=v>>(8*(i if little else 1-i))&255
 if mode in(1,5,8):
  store(b,0);value=int.from_bytes(bytes((m[b],m[b+1])),'little'if little else'big',signed=True);store(g,value);store(r,value)
 elif mode in(3,9):
  for p,off in((r,0x24),(g,0x25),(b,0x26)):store(p,m[record+off])
 elif mode in(4,6):
  for p,off in((r,0x28),(g,0x29),(b,0x2A)):store(p,m[record+off])
 else:
  value=m[record+0x2C]
  for p in(b,g,r):store(p,value)
 if mode in(1,2,3,5):alpha=0
 elif mode in(4,6,7,8,9):alpha=m[record+0x2B]
 else:alpha=(m[record+0x2B]*m[record+0x27])//256
 store(a,alpha);return m
def reference(initial,c=Case(),home=None,saved=0):
 home=STACK+c.phase if home is None else home;m=dict(initial);put(m,home-4,saved);p=read(m,home+16)
 return channels(m,p,outputs(c))
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c=Case(),entry=ENTRY,s=None,connected=None,arguments=None):
  super().__init__(words,memory,c,entry=entry,s=symbols()if s is None else s,connected=connected,arguments=(*outputs(c),RECORD)if arguments is None else arguments)
  self.hi=0xBEEFFACE;self.lo=0x13579BDF;self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==0 and w&63==25:
   product=self.r[w>>21&31]*self.r[w>>16&31];super().execute(w);self.hi=product>>32
  else:super().execute(w)
 def record_call(self,t):
  assert t in(ENTRY,FOLLOW),hex(t);a=tuple(map(u32,self.arguments(5)));self.calls.append((t,a));self.events.append(('CALL',t,a))
 def hook(self,t):
  assert t==FOLLOW
  for i in range(4):put(self.memory,self.r[29]+4*i,0xB5000000+i)
  for r in(1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
  self.r[2]=0x81234567;self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo,self.condition=0x87654321,0x12345678,True
def literal(m):return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses)
def original_object(core,q,out):
 text=(out/'frozen/conker/asm/15D730.s').read_text();body=re.search(r'^glabel func_15131514\n.*?(?=^glabel |\Z)',text,re.M|re.S).group()
 p=out/'original-reference.s';p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.text\n'+body+'\n.size '+core.FUNCTION+',.-'+core.FUNCTION+'\n')
 subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I','conker/include','-o',str(p.with_suffix('.o')),str(p)],cwd=core.ROOT,check=True,capture_output=True)
 q['original'],q['original_refs']=core.function_blob(p.with_suffix('.o'))
def programs(core,q,s):
 extended={**s,'.rodata':s['jtbl_800A3820']};values=[list(core.bound_blob(q[n],q[r],extended))for n,r in(('original','original_refs'),('raw','refs'),('normal','normal_refs'))]
 assert values[0]==values[1]==values[2];return values
def verify(m,initial,c=Case()):
 wanted=reference(initial,c,saved=m.before[16]);assert(m.memory,m.calls)==(wanted,[]),(c,[(hex(a),m.memory.get(a),v)for a,v in wanted.items()if m.memory.get(a)!=v][:8])
 assert m.f[20:]==m.before_f[20:]
def cases():return [Case(mode=mode,seed=seed,phase=p)for mode,seed,p in itertools.product(range(256),range(4),(0,8))]
def guest(core,q):
 original_object(core,q,core.ROOT/core.BUILD);seen=set();rows=[(c,symbols(),ENTRY)for c in cases()]
 rows +=[(Case(mode=mode,seed=3),symbols(i),0x17508000 if i==1 else 0x1F007FFC)for i,mode in itertools.product((1,2),range(256))]
 for c,s,entry in rows:
  initial=fixture(c,s,entry);models=[Oracle(w,initial,c,entry=entry,s=s).run()for w in programs(core,q,s)]
  for m in models:verify(m,initial,c)
  assert literal(models[0])==literal(models[1])==literal(models[2]);seen.update(pc-entry for pc in models[0].visits)
 assert seen==set(range(0,312,4)),sorted(set(range(0,312,4))-seen)
 aliases=0
 for c in(Case(mode=mode,layout=layout,seed=seed)for mode,layout,seed in itertools.product(range(256),range(1,len(LAYOUTS)),(0,5))):
  s=symbols();initial=fixture(c);models=[Oracle(w,initial,c).run()for w in programs(core,q,s)]
  for m in models:verify(m,initial,c)
  assert literal(models[0])==literal(models[1])==literal(models[2]);aliases+=1
 for c in(Case(mode=mode,alias=a)for mode,a in itertools.product(range(256),(1,2,3))):
  initial=fixture(c);models=[Oracle(w,initial,c).run()for w in programs(core,q,symbols())]
  for m in models:verify(m,initial,c)
  assert literal(models[0])==literal(models[1])==literal(models[2]);aliases+=1
 cuts=0
 for c in(Case(mode=mode,layout=layout)for mode,layout in itertools.product((0,1,2,3,4,7,8,9),(0,5,9))):
  initial=fixture(c);ps=programs(core,q,symbols());full=Oracle(ps[0],initial,c).run()
  for cut in range(full.all_accesses):
   models=[]
   for w in(ps[0],ps[2]):
    m=Oracle(w,initial,c);m.cut=cut
    try:m.run();raise AssertionError('Unfired mode color access cut')
    except AccessBoundary:pass
    models.append(m)
   assert literal(models[0])==literal(models[1]);cuts+=1
 return dict(cases=len(rows),reached_words=78,all_256_modes=True,alias_cases=aliases,fault_prefix_cuts=cuts,independent_complete_memory=True,literal_full_state=True,
  source_byte_reads_and_output_order_exact=True,separate_guest_big_endian_and_native_little_endian_alias_models=True,return_value_not_a_portable_contract=True)
def connections(core,q):
 rom=(core.ROOT/'conker/conker.us.bin').read_bytes();body=struct.unpack_from('>24I',rom,0x15EAFC);count=0
 rows=[Case(mode=m,layout=l,phase=p)for m,l,p in itertools.product(range(256),(0,1,5,9),(0,8))]
 rows +=[Case(mode=m,alias=a,phase=p)for m,a,p in itertools.product(range(256),(1,2,3),(0,8))]
 for c in rows:
  s=symbols();initial=fixture(c);home=STACK+c.phase;args=(0x80000000,0xFFFFFFFF,0x12345678,0x7FFFFFFF,*outputs(c),RECORD)
  for i,value in enumerate(args):put(initial,home+4*i,value)
  models=[]
  for w in programs(core,q,s):
   code=dict(zip(range(ENTRY,ENTRY+312,4),w));m=Oracle(body,initial,c,entry=PARENT,connected=code,arguments=args).run();models.append(m)
   wanted=dict(initial);put(wanted,home-4,0xDEAD0000)
   for i,value in enumerate(args[:4]):put(wanted,home+4*i,value)
   put(wanted,home-16,RECORD);wanted=reference(wanted,c,home=home-32,saved=m.before[16]);follow=tuple(read(wanted,home+4*i)for i in range(4))+(read(wanted,home+32),)
   put(wanted,home-16,follow[4])
   for i in range(4):put(wanted,home-32+4*i,0xB5000000+i)
   assert(m.memory,m.calls,m.r[2])==(wanted,[(ENTRY,(*outputs(c),RECORD)),(FOLLOW,follow)],0x81234567),(c,m.calls,follow)
  assert literal(models[0])==literal(models[1])==literal(models[2]);count+=1
 return dict(original_complete_wrapper_words=24,original_complete_wrapper_cases=count,only_direct_call_ROM='15EB28',target_result_ignored=True,
  all_nine_stack_and_register_arguments_qualified=True,late_parent_argument_and_record_home_reload=True,followup_result_forwarded=True,bounded_followup_provider=True,complete_followup_not_claimed=True)

def native_rows():
 rows=[]
 for c in(Case(mode=m,seed=s,layout=l)for m,s,l in itertools.product(range(256),(0,5),range(len(LAYOUTS)))):
  memory={i:(i*29+c.seed*53+0x5A)&255 for i in range(256)};memory[64+0x71]=c.mode
  wanted=channels(memory,64,LAYOUTS[c.layout],little=True)
  rows.append('{%d,%d,%d,{'%(c.mode,c.seed,c.layout)+','.join(str(wanted[i])for i in range(256))+'}}')
 return ',\n'.join(rows),len(rows)
def controls(core):
 s=core.SELECTED;changes={
  'wrong_mode':('record[0x71]','record[0x70]'),
  'signed_mode':('switch (record[0x71])','switch ((s8)record[0x71])'),
  'wrong_scalar':('record[0x2C]','record[0x2D]'),
  'wrong_red':('*red = record[0x24]','*red = record[0x25]'),
  'wrong_explicit':('*blue = record[0x2A]','*blue = record[0x29]'),
  'wrong_alpha':('*alpha = record[0x2B]','*alpha = record[0x27]'),
  'wrong_default_shift':(']) >> 8',']) >> 7'),
  'wrong_blank':('*blue = 0;','*blue = 1;'),
  'wrong_mode_alias':('case 6:','case 10:'),
  'wrong_store_order':('*red = record[0x24];\n            *green = record[0x25];\n            *blue = record[0x26];','*blue = record[0x26];\n            *green = record[0x25];\n            *red = record[0x24];'),
  'cached_alpha':('    switch (record[0x71])','    s32 cachedAlpha = record[0x2B];\n    switch (record[0x71])'),
  'stub':('    switch (record[0x71])','    return;\n    switch (record[0x71])')}
 assert all(a in s for a,b in changes.values());bad={n:s.replace(a,b)for n,(a,b)in changes.items()}
 # Signed-vs-unsigned selector promotes identically for 0..9 and takes the same
 # default for every other byte. It is a shape-only control, never credited.
 del bad['signed_mode']
 bad['cached_alpha']=bad['cached_alpha'].replace('*alpha = record[0x2B];','*alpha = cachedAlpha;')
 return bad
def native_text(core):
 rows,n=native_rows();bad=controls(core);versions={'selected':core.SELECTED,**bad}
 code='#include <ultra64.h>\n'+'\n'.join(s.replace('func_15131514','test_'+name)for name,s in versions.items())
 code+=r'''
typedef char Width[(sizeof(void*)==4&&sizeof(s16)==2)?1:-1];
typedef struct{unsigned mode,seed,layout;u8 expected[256];}Case;
static const Case cases[]={
__ROWS__
};
static const unsigned layouts[][4]={__LAYOUTS__};
static s16 canvas[128];
typedef void(*Update)(s16*,s16*,s16*,s16*,u8*);
static int check(Update fn){unsigned i,j;u8*p=(u8*)canvas;const Case*c;const unsigned*l;
 for(i=0;i<__COUNT__;i++){
  c=cases+i;l=layouts[c->layout];for(j=0;j<256;j++)p[j]=(u8)(j*29+c->seed*53+0x5A);p[64+0x71]=(u8)c->mode;
  fn((s16*)(p+l[0]),(s16*)(p+l[1]),(s16*)(p+l[2]),(s16*)(p+l[3]),p+64);
  for(j=0;j<256;j++)if(p[j]!=c->expected[j])return 1;
 }
 return 0;
}
static int run(void){if(check(test_selected))return 1;
'''.replace('__ROWS__',rows).replace('__COUNT__',str(n)).replace('__LAYOUTS__',','.join('{'+','.join(map(str,row))+'}'for row in LAYOUTS))
 for i,name in enumerate(bad):code+='if(!check(test_'+name+'))return '+str(i+2)+';\n'
 return code+'return 0;}\n'+START
def native(core,out):
 p=out/'native.c';p.write_text(native_text(core));records=[]
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);build=subprocess.run([*native_command(opt),'-mstackrealign',str(p),'-o',str(exe)],cwd=core.ROOT,capture_output=True,text=True)
  assert build.returncode==0 and not build.stdout and not build.stderr,(opt,build.stdout,build.stderr)
  run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30);assert run.returncode==0 and not run.stdout and not run.stderr,(opt,run.returncode,run.stderr)
  records.append(dict(profile=opt,exit=0))
 return dict(cases_per_profile=native_rows()[1],profiles=records,trapping_UBSan=True,effective_controls=len(controls(core)),all_256_modes=True,
  aligned_typed_halfword_backing=True,record_byte_aliases_and_output_overlap=True,whole_canvas_canaries=True,precomputed_little_endian_reference=True,
  signed_selector_shape_control_not_credited=True,hardware_and_complete_followup_not_claimed=True)
