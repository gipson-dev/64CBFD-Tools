"""Distance fade: bounded retail float32, callback and native32 qualification."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import floating,bits
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-actor-distance-fade-match';F='func_150E05F8';ENTRY=0x150E05F8;BODY=224;ACTOR=0x30000;PLAYER=0x50000
SYMS=dict(D_800A0FD0=0x800A0FD0,D_800A0FD4=0x800A0FD4,D_800DBFF0=0x800DBFF0)
u32=lambda n:n&0xFFFFFFFF
half=lambda n:((n&65535)^32768)-32768
f32=lambda n:floating(bits(n))
@dataclass(frozen=True)
class Case:
 coords:tuple=(0,0,0)
 player:tuple=(0,0,0)
 phase:int=0
 seed:int=0
def fixture(c,s=SYMS,p=PLAYER):
 m={STACK+i:(i*17+0xA5)&255 for i in range(-256,256)}
 for base,n in((ACTOR,256),(p,0x310)):m.update({base+i:(i*29+c.seed*11+0x59)&255 for i in range(n)})
 for j,v in enumerate(c.coords):put(m,ACTOR+0x10+j*2,v,2)
 for j,v in enumerate(c.player):put(m,p+0x2F8+j*4,v)
 put(m,s['D_800DBFF0'],p);put(m,s['D_800A0FD0'],bits(2570.));put(m,s['D_800A0FD4'],bits(3850.));return m
def reference(initial,s=SYMS):
 m=dict(initial);p=read(m,s['D_800DBFF0']);xyz=[f32(floating(read(m,p+0x2F8+j*4))-half(read(m,ACTOR+0x10+j*2,2)))for j in range(3)]
 total=f32(f32(xyz[2]*xyz[2])+f32(f32(xyz[0]*xyz[0])+f32(xyz[1]*xyz[1])));d=f32(math.sqrt(total))
 near=floating(read(m,s['D_800A0FD0']))
 if d<=near:answer=255
 else:
  far=floating(read(m,s['D_800A0FD4']))
  if far<=d:answer=0
  else:
   value=f32(255.-f32(f32(f32(d-near)*f32(1./f32(far-near)))*255.))
   answer=math.trunc(value)if math.isfinite(value)and -(2**31)<=value<2**31 else 0x80000000
 m[ACTOR+0x8A]=answer&255;return m
def cases():
 values=[bits(v)for v in(0.,-0.,1.,-1.,2569.,2570.,2571.,3000.,3849.,3850.,3851.,-3000.,65535.,1e20)]
 values += [0x7F800000,0xFF800000,0x7FC12345]
 rows=[Case(c,tuple(v if j==a else bits(float(half(c[j])))for j in range(3)),p)for c,a,v,p in itertools.product(((0,0,0),(-32768,32767,-12345),(32767,-32768,255)),range(3),values,(0,8))]
 for k in range(256):
  b=bits(2570.+(255-k)*1280./255.)
  rows.extend(Case(player=(n,0,0))for n in(b-1,b,b+1))
 rows.extend((Case(coords=(-1,-2,-3),player=(bits(1800.),bits(-1800.),bits(1800.))),Case(coords=(30000,-31000,30000),player=(bits(32000.),bits(-29000.),bits(32000.)))))
 return tuple(rows)
class Oracle(FactoryOracle):
 def __init__(self,words,memory,c,s=SYMS,entry=ENTRY,connected=None):
  super().__init__(words,memory,c,entry=entry,s=s,connected=connected,arguments=(ACTOR,));self.before=self.r[:];self.before_f=self.f[:]
 def execute(self,w):
  op,fmt,src,dst,fn=w>>26,w>>21&31,w>>11&31,w>>6&31,w&63
  if op==17 and fmt==16 and fn in(4,13):
   v=floating(self.f[src])
   if fn==4:self.f[dst]=bits(math.sqrt(v)if v>=0 else math.nan)
   else:self.f[dst]=u32(math.trunc(v))if math.isfinite(v)and -(2**31)<=v<2**31 else 0x80000000
   self.r[0]=0
  else:super().execute(w)
 def record_call(self,t):
  assert t==ENTRY;self.calls.append((t,tuple(self.arguments(1))));self.events.append(('CALL',t,tuple(self.arguments(1))))
 def hook(self,t):raise AssertionError(('Unexpected helper',t))
def linked(obj,label,s=SYMS,entry=ENTRY):
 text,fs,rs=parse_object(obj);rs={at:[(typ,'D_800A0FD0' if sym=='.rodata' else sym)for typ,sym in row]for at,row in rs.items()};asm,unknown=emit_function(text,fs[F],rs,F,s);assert not unknown;p=o/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry+'\n'.join('%s = 0x%X;'%(n,v)for n,v in s.items()));subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',F,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);return list(struct.unpack('>56I',sections(p.with_suffix('.elf'))['.text'][1][:BODY]))
def state(m):return(m.r,m.f,m.memory,m.calls,m.events,m.trace,m.hi,m.lo,m.condition)
def verify(m,initial,s=SYMS):
 assert m.memory==reference(initial,s)
 assert m.r[29]==m.before[29]and m.r[16:24]==m.before[16:24]and m.r[28]==m.before[28]and m.f[20:]==m.before_f[20:]and not m.calls
def run_suite():
 objects=(o/('original-'+F+'.o'),o/'selected-final.o',o/'qualified-padded.o');programs=[linked(p,'guest-'+str(i))for i,p in enumerate(objects)];assert programs[0]==programs[1]==programs[2];visited=set();count=0
 for c in cases():
  initial=fixture(c);machines=[]
  for program in programs:m=Oracle(program,initial,c);m.run();verify(m,initial);machines.append(m)
  assert state(machines[0])==state(machines[1])==state(machines[2]);visited.update(machines[0].visits);count+=1
 assert visited==set(range(ENTRY,ENTRY+BODY,4))-{ENTRY+0x9C}
 assert programs[0][36]==programs[0][39]==0x46101281
 targets={i+1+(((w&65535)^32768)-32768)for i,w in enumerate(programs[0])if w>>26 in(1,4,5,6,7,20,21,22,23)or(w>>26==17 and w>>21&31==8)};assert 39 not in targets
 prefixes=0
 for c in(Case(),Case(player=(bits(3000.),0,0)),Case(player=(bits(4000.),0,0)),Case(player=(0x7FC12345,0,0))):
  initial=fixture(c);m=Oracle(programs[0],initial,c);m.run()
  for cut in range(m.all_accesses):
   ms=[]
   for program in programs:
    q=Oracle(program,initial,c);q.cut=cut
    try:q.run()
    except faults.AccessBoundary:pass
    else:raise AssertionError(('Missing access boundary',cut))
    ms.append(q)
   assert state(ms[0])==state(ms[1])==state(ms[2]);prefixes+=1
 initial=fixture(Case());[initial.pop(SYMS['D_800A0FD4']+i)for i in range(4)]
 for program in programs:m=Oracle(program,initial,Case());m.run();verify(m,initial)
 rebased=0
 for k,entry in enumerate((0x15001000,0x1F008000,0x1000FFF0)):
  s=dict(D_800A0FD0=0x80007FFC+k*0x100000,D_800A0FD4=0x80008000+k*0x100000,D_800DBFF0=0x8001FFF0+k*0x100000);ps=[linked(p,'rebase-'+str(k)+'-'+str(i),s,entry)for i,p in enumerate(objects)]
  for c in cases()[::53]:
   initial=fixture(c,s);ms=[]
   for program in ps:m=Oracle(program,initial,c,s,entry);m.run();verify(m,initial,s);ms.append(m)
   assert state(ms[0])==state(ms[1])==state(ms[2]);rebased+=1
 aliases=0
 for p in(ACTOR,ACTOR-0x270,ACTOR-0x2E8):
  c=Case(player=(bits(3000.),0,0));initial=fixture(c,p=p);ms=[]
  for program in programs:m=Oracle(program,initial,c);m.run();verify(m,initial);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);aliases+=1
 rom=(r/'conker/conker.us.bin').read_bytes();assert struct.unpack_from('>3I',rom,0x22DB4C)==(ENTRY,0,0);assert(0x8008908C-0x80088C90)//12==85;window=struct.unpack_from('>5I',rom,0x141390);cc=0
 for c in cases()[::47]:
  initial=fixture(c);put(initial,ACTOR+0x38,ENTRY);want=reference(initial);ms=[]
  for program in programs:
   code=dict(zip(range(ENTRY,ENTRY+BODY,4),program));code[0x15113EF4]=0;m=Oracle(window,initial,c,entry=0x15113EE0,connected=code);m.r[16]=ACTOR;m.r[30]=7;m.code=WindowCode(m.code,m);m.code.ends=(0x15113EF4,)
   try:m.run()
   except WindowBoundary:pass
   else:raise AssertionError('Missing caller boundary')
   assert(m.memory,m.calls,m.r[30])==(want,[(ENTRY,(ACTOR,))],8);ms.append(m)
  assert state(ms[0])==state(ms[1])==state(ms[2]);cc+=1
 return dict(cases=count,executions=count*3,covered_words=55,compiler_words=56,slot_words=56,alignment_words=0,unreachable_offsets=[156],unreachable_duplicate_preserved=True,frame=0,guards=0,access_prefix_pairs=prefixes,sparse_near_branch_skips_far_load=True,rebase_layouts=3,rebase_cases=rebased,guest_alias_cases=aliases,registration_table='D_80088C90',registration_index=85,registration_stride=12,registration_ROM='0x22DB4C',caller_window_entry='0x15113EE0',caller_window_ROM='0x141390',caller_window_words=5,caller_window_cases=cc,result_register_ignored=True,literal_full_state_equal=True,bounded_nontrapping_float32_model=True,hardware_FCSR_or_complete_parent_claimed=False,private_only=True,installed=False,matching_credit=0)
def controls(body):return dict(wrong_near=body.replace('2570.0f','2571.0f'),wrong_far=body.replace('3850.0f','3840.0f'),wrong_output=body.replace('record[0x8A]','record[0x8B]'),wrong_scale=body.replace('* 255.0f','* 254.0f'),wrong_near_result=body.replace('result = 255;','result = 254;'),wrong_far_result=body.replace('result = 0;','result = 1;'),wrong_z=body.replace('record + 0x14','record + 0x12'),unsigned_coords=body.replace('*(s16 *)','*(u16 *)'))
def native_harness(selected):
 head,body=selected.split('/* Fade',1);body='/* Fade'+body;bad=controls(body);assert all(v!=body for v in bad.values());rows=[c for c in cases()if not c.phase and all(math.isfinite(floating(v))for v in c.player)]
 text=head+r'''
_Static_assert(sizeof(void*)==4,"native32");
typedef struct{u32 coords[3],player[3],result;}Fixture;
static u8 actor[256]__attribute__((aligned(8))),player[0x310]__attribute__((aligned(8)));u8 *D_800DBFF0;
f32 sqrtf(f32 value){f32 out;__asm__("sqrtss %1,%0":"=x"(out):"x"(value));return out;}
'''
 text+='\n'.join(v.replace(F,'test_'+k)for k,v in dict(selected=body,**bad).items());array=lambda vs:'{'+','.join('0x%Xu'%u32(v)for v in vs)+'}';text+='\nstatic const Fixture fixtures[]={\n'+',\n'.join('{'+array(c.coords)+','+array(c.player)+','+str(reference(fixture(c))[ACTOR+0x8A])+'u}'for c in rows)+'\n};\n'
 text+=r'''
typedef void(*Update)(u8*);
static int check(Update fn){u32 n,i,j;u8 expected;for(n=0;n<CASE_COUNT;n++){const Fixture*c=fixtures+n;for(i=0;i<256;i++)actor[i]=(u8)(i*29+0x59);for(i=0;i<0x310;i++)player[i]=(u8)(i*29+0x59);for(j=0;j<3;j++){*(s16*)(actor+0x10+j*2)=(s16)c->coords[j];*(u32*)(player+0x2F8+j*4)=c->player[j];}D_800DBFF0=player;fn(actor);if(D_800DBFF0!=player)return 1;for(i=0;i<256;i++){expected=(u8)(i*29+0x59);if(i>=0x10&&i<0x16)expected=(u8)(c->coords[(i-0x10)/2]>>(8*((i-0x10)&1)));if(i==0x8A)expected=(u8)c->result;if(actor[i]!=expected)return 2;}for(i=0;i<0x310;i++){expected=(u8)(i*29+0x59);if(i>=0x2F8&&i<0x304)expected=(u8)(c->player[(i-0x2F8)/4]>>(8*((i-0x2F8)&3)));if(player[i]!=expected)return 3;}}return 0;}
static int run(void){if(check(test_selected))return 10;
'''.replace('CASE_COUNT',str(len(rows)))
 for i,k in enumerate(bad):text+='if(!check(test_'+k+'))return '+str(20+i)+';\n'
 text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');return text,dict(cases=len(rows),negative_controls=len(bad),signature='void(u8*)',all_record_player_global_bytes_checked=True,sqrt_instruction='SSE sqrtss',native_domain='finite player coordinates; bounded signed conversion',nonfinite_guest_only=True)
def run_native(selected):
 text,counts=native_harness(selected);p=o/'native.c';p.write_text(text);reports={}
 for opt in('-O0','-O2','-O3'):
  exe=o/('native'+opt);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=r,capture_output=True,text=True);assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr;run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr);reports[opt]=dict(exit=0,**counts,UBSan=True)
 return dict(profiles=reports,**counts)
