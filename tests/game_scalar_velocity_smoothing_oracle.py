"""Finite private smoothing behavior; explicitly not byte-matching qualification."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,math,random,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=o=None;ENTRY=0x150495B0;A,B=0x20004,0x20008
f32=lambda x:floating(bits(x))
@dataclass(frozen=True)
class Case:phase:int=0
class Oracle(FactoryOracle):
 def __init__(self,words,initial,args,phase):
  super().__init__(words,initial,Case(phase),entry=ENTRY,s={},arguments=args);self.before_f=self.f[:]
 def execute(self,w):
  if w>>26==17 and w>>21&31==16 and w&63==50:self.condition=floating(self.f[w>>11&31])==floating(self.f[w>>16&31])
  else:super().execute(w)
 def record_call(self,t):raise AssertionError(('Unexpected call',hex(t)))
 def hook(self,t):raise AssertionError(('Unexpected helper',hex(t)))
def corpus():
 rows=[(0,10,0,4,6,1/60),(10,0,-1,4,6,1/60),(0,10,1000,4,6,1),(10,0,-1000,4,6,1),(1,1,0,0,0,0),(-0.0,0.0,-0.0,1,1,0),(0.0,-0.0,0.0,0,0,0),(1,-1,3,-4,-6,.25),(1,1,9,1,1,0),(0,1,4,0,0,.25),(0,-1,-4,0,0,.25),(100,-100,0,16,9,.5)]
 rng=random.Random(ENTRY)
 for i in range(256):rows.append((rng.randrange(-4096,4097)*.25,rng.randrange(-4096,4097)*.25,rng.randrange(-1024,1025)*.25,rng.choice((-8,0,1,4,16)),rng.choice((-2,0,.5,6,9)),rng.choice((-1,0,1/60,.25,.5,1))))
 return [tuple(map(f32,row))for row in rows]
def fixture(row,alias):
 p,t,v,k,d,dt=row;velocity=A if alias else B;m={STACK+i:(i*17+0xA5)&255 for i in range(-128,256)};m.update({A-4+i:(i*29+0x59)&255 for i in range(16)});put(m,A,bits(p))
 if not alias:put(m,B,bits(v))
 return m,(A,bits(t),velocity,bits(k),bits(d),bits(dt))
def reference(initial,args):
 p,t,v,k,d,dt=args;t,k,d,dt=map(floating,(t,k,d,dt));m=dict(initial);difference=f32(t-floating(read(m,p)));direction=-1 if difference<0 else 1;force=f32(difference*k);old=floating(read(m,v));adjust=f32(f32(f32(force-old)*d)*dt);put(m,v,bits(f32(old+adjust)));step=f32(floating(read(m,v))*dt);next=f32(step+floating(read(m,p)));next_direction=-1 if t<next else 1
 assert math.isfinite(next)
 if next_direction==direction:put(m,p,bits(next));snap=False
 else:put(m,p,bits(t));put(m,v,0);snap=True
 return m,snap
def public(m):return {a:v for a,v in m.items()if not STACK-128<=a<STACK+256}
def link(name):
 p=o/name;p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%ENTRY);subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e','func_150495B0','-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True);text=sections(p.with_suffix('.elf'))['.text'][1];return list(struct.unpack('>%dI'%(len(text)//4),text))
def qualify(root,output,candidate='selected'):
 global r,o
 r,o=Path(root),Path(output)
 programs=[link('original-func_150495B0'),link(candidate)];count=snaps=0;seen=[set(),set()];native_cases=[]
 for row,alias,phase in itertools.product(corpus(),(False,True),(0,8)):
  initial,args=fixture(row,alias);expected,snap=reference(initial,args);pair=[]
  for i,program in enumerate(programs):
   m=Oracle(program,initial,args,phase);m.run();assert public(m.memory)==public(expected),(row,alias,i,read(m.memory,A),read(expected,A));assert all(m.r[j]==m.before[j]for j in(*range(16,24),28,29,30,31))and m.f[20:]==m.before_f[20:]and not m.calls;seen[i].update(m.visits);pair.append(public(m.memory))
  assert pair[0]==pair[1];count+=1;snaps+=snap
  if phase==0:native_cases.append((row,alias,initial,expected,args))
 assert seen[0]==set(range(ENTRY,ENTRY+216,4))-{ENTRY+0x3C,ENTRY+0xC4}
 source=(o/(candidate+'.c')).read_text();body=source[source.index('/* Smooth'):];bad={
  'missing_strength':body.replace('difference *= strength;','difference *= 1.0f;'),
  'missing_damping':body.replace('* damping * deltaTime;','* deltaTime;'),
  'missing_update_dt':body.replace('* damping * deltaTime;','* damping;'),
  'wrong_initial_sign':body.replace('difference < 0.0f','difference > 0.0f'),
  'wrong_equality':body.replace('target < next','target <= next'),
  'missing_velocity_zero':body.replace('*velocity = 0.0f;','(void)velocity;'),
  'wrong_snap_store_order':body.replace('*position = target;\n        *velocity = 0.0f;','*velocity = 0.0f;\n        *position = target;'),
  'missing_position_update':body.replace('*position = next;','(void)next;')}
 assert len(set(bad.values()))==8 and all(v!=body for v in bad.values())
 code='#include <ultra64.h>\n'+'\n'.join(v.replace('func_150495B0','candidate_%d'%i)for i,v in enumerate([body,*bad.values()]))
 code+='\ntypedef union {u32 u[4];f32 f[4];} World;\ntypedef struct {u32 initial[4],arguments[4],expected[4],alias;} Test;\nstatic const Test tests[]={\n'
 rows=[]
 for row,alias,initial,expected,args in native_cases:
  data=lambda m:[read(m,A-4+4*j)for j in range(4)]
  rows.append('{{%s},{%s},{%s},%d}'%(','.join('0x%Xu'%v for v in data(initial)),','.join('0x%Xu'%v for v in(args[1],*args[3:])),','.join('0x%Xu'%v for v in data(expected)),alias))
 code+=',\n'.join(rows)+'\n};\ntypedef void (*Candidate)(f32*,f32,f32*,f32,f32,f32);\nstatic Candidate candidates[]={'+','.join('candidate_%d'%i for i in range(9))+'};\n'
 code+=r'''
 static int run(void){u32 i,j,k,killed=0;World w,a;int same;
  for(i=0;i<sizeof(tests)/sizeof(tests[0]);i++)for(j=0;j<9;j++){
   for(k=0;k<4;k++){w.u[k]=tests[i].initial[k];a.u[k]=tests[i].arguments[k];}
   candidates[j](w.f+1,a.f[0],w.f+(tests[i].alias?1:2),a.f[1],a.f[2],a.f[3]);
   same=1;for(k=0;k<4;k++)if(w.u[k]!=tests[i].expected[k])same=0;
   if(!same){if(!j)return 10;killed|=1u<<(j-1);}
  }
  return killed==255?0:11;
 }
 '''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 p=o/'native-private-semantics-v20.c';p.write_text(code);native=[]
 for profile in ('-O0','-O2','-O3'):
  exe=o/('native-private-semantics-v20'+profile);q=subprocess.run(native_command(profile)+['-o',str(exe),str(p)],cwd=r,capture_output=True,text=True);(o/('native-private-semantics-v20'+profile+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout,q.stderr);q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(profile,q.returncode,q.stderr);native.append(dict(profile=profile,cases=len(native_cases),UBSan=True,negative_controls=list(bad),all_controls_effective=True))
 report=dict(private_only=True,installed=False,matching_credit=0,finite_guest_cases=count,executions=count*2,snap_cases=snaps,accepted_cases=count-snaps,retail_reachable_words=len(seen[0]),retail_static_words=54,retail_two_unreachable_delay_fill_copies=True,raw_candidate_reachable_words=len(seen[1]),position_velocity_alias_cases=True,saved_state_preserved=True,full_public_memory_and_canaries_checked=True,argument_stack_aliases_excluded=True,hardware_FCSR_NaN_and_denormal_traps_claimed=False,caller_execution_claimed=False,compiler_match_claimed=False,native=native)
 (o/'semantic-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
 return report
