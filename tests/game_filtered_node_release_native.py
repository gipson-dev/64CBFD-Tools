"""Native32 public state and eight effective semantic controls at three profiles."""
from pathlib import Path
import json,subprocess,sys,types
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import game_filtered_node_release_oracle as g
from tools.experiments.game_filtered_node_release_match import HEADERS
def qualify(root,output,body):
 r,o=Path(root),Path(output);headers=HEADERS
 wrong_next=body.replace('            next = *(u8 **)(current + 0x54);\n','').replace('                    current = next;','                    next = *(u8 **)(current + 0x54);\n                    current = next;').replace('            current = next;','            next = *(u8 **)(current + 0x54);\n            current = next;')
 controls=(('missing-zero-key-gate',body.replace('actor[0x3B] == 0','0')),
  ('reload-next-after-release',wrong_next),
  ('cached-actor-key',body.replace('    s32 released;','    s32 released;\n    u8 key = actor[0x3B];').replace('actor[0x3B] == current[0]','key == current[0]')),
  ('wrong-filter-byte',body.replace('current[6]','current[7]')),
  ('narrow-filter',body.replace('    released = 0;','    released = 0;\n    filter = (u8)filter;')),
  ('narrow-countdown',body.replace('    released = 0;','    released = 0;\n    skip &= 255;')),
  ('wrong-all-sentinel',body.replace('skip != 0xFF','skip != 0xFE')),
  ('wrong-return',body.replace('return released;','return released & 0;')))
 assert all(text!=body for _,text in controls)
 def index(p):return 0 if not p else 7 if p==g.ALT else 1+(p-g.NODES)//g.STRIDE
 def array(a):return'{'+','.join(str(v)for v in a)+'}'
 rows=[];s=dict(D_800C3EE0=0x800C3EE0,func_15030158=0x15030158)
 for c in g.cases():
  if c.phase:continue
  initial=g.fixture(c,s);expected,calls,answer=g.reference(initial,c,s)
  groups=[expected[g.NODES+j*128]for j in range(6)];nexts=[index(g.read(expected,g.NODES+j*128+84))for j in range(6)];prevs=[index(g.read(expected,g.NODES+j*128+88))for j in range(6)];order=[index(a[0])for _,a in calls]+[0]*4
  rows.append('{'+','.join([str(c.key),str(c.filter),'0x%Xu'%c.skip,str(c.length),str(c.pattern),str(c.mode),str(answer),str(expected[g.ACTOR+59]),str(index(g.read(expected,s['D_800C3EE0']))),str(len(calls)),array(order[:4]),array(groups),array(nexts),array(prevs)])+'}')
 code=headers+r'''
 struct Case{s32 key,filter;u32 skip,length,pattern,mode,answer,finalKey,head,calls,order[4],group[6],next[6],prev[6];};
 static const struct Case cases[]={ROWS};static const struct Case *c;
 static union{u32 align;u8 bytes[768];} nodes;static u8 actor[96],alt[92];u8 *D_800C3EE0;static u32 calls,error;
 static u8 *pointer(u32 i){return !i?0:i==7?alt:nodes.bytes+(i-1)*128;}
 static u32 pointer_index(u8 *p){return !p?0:p==alt?7:1+(p-nodes.bytes)/128;}
 void func_15030158(u8 *p,s32 immediate){u8 *next=*(u8**)(p+84),*prev=*(u8**)(p+88);
  if(immediate||calls>=c->calls||pointer_index(p)!=c->order[calls])error=1;calls++;
  if(D_800C3EE0==p)D_800C3EE0=next;if(prev)*(u8**)(prev+84)=next;if(next)*(u8**)(next+88)=prev;
  p[0]=238;*(u8**)(p+84)=0;*(u8**)(p+88)=0;
  if(c->mode&1)actor[59]^=1;if(c->mode&2)D_800C3EE0=alt;
 }
 '''.replace('ROWS',',\n'.join(rows))
 for i,(_,text)in enumerate((('valid',body),)+controls):code+=text.replace('func_15030310(','root_%d('%i)+'\n'
 code+='static s32 (*roots[])(u8*,s32,u32)={'+','.join('root_%d'%i for i in range(9))+'};\n'
 code+=r'''
 static int run(void){u32 n,k,i,j,bad,killed=0;u8 *p;
  for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++)for(k=0;k<9;k++){
   c=&cases[n];for(i=0;i<96;i++)actor[i]=(i*29+90)&255;for(i=0;i<768;i++)nodes.bytes[i]=(i*29+90)&255;
   actor[59]=c->key;D_800C3EE0=c->length?nodes.bytes:0;
   for(j=0;j<6;j++){
    p=nodes.bytes+j*128;p[0]=(c->pattern==0||(c->pattern==1&&j%2==0)||(c->pattern==2&&j<2))?c->key:c->key^1;
    p[6]=(u8)((u32)c->filter+(c->pattern==1&&j%3==0?1u:0u));*(u8**)(p+84)=j+1<c->length?p+128:0;*(u8**)(p+88)=j?p-128:0;
   }
   calls=error=0;bad=(u32)roots[k](actor,c->filter,c->skip)!=c->answer||error||calls!=c->calls||D_800C3EE0!=pointer(c->head)||actor[59]!=c->finalKey;
   for(i=0;i<96;i++)if(i!=59&&actor[i]!=(u8)(i*29+90))bad=1;
   for(j=0;j<6;j++){
    p=nodes.bytes+j*128;if(p[0]!=c->group[j]||*(u8**)(p+84)!=pointer(c->next[j])||*(u8**)(p+88)!=pointer(c->prev[j]))bad=1;
    for(i=1;i<128;i++)if(i<84||i>=92){u8 expected=(u8)((j*128+i)*29+90);if(i==6)expected=(u8)((u32)c->filter+(c->pattern==1&&j%3==0?1u:0u));if(p[i]!=expected)bad=1;}
   }
   if(!k&&bad)return 2;if(k&&bad)killed|=1u<<(k-1);
  }
  return killed==255u?0:3;
 }
 '''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 report=[]
 for opt in('-O0','-O2','-O3'):
  p=o/('native-'+opt[1:]);p.with_suffix('.c').write_text(code);q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p.with_suffix('.c')),'-o',str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr);q=subprocess.run([str(p)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stdout,q.stderr)
  report.append(dict(profile=opt,cases=len(rows),executions=len(rows)*9,controls=[n for n,_ in controls],all_eight_controls_effective=True,UBSan=True,complete_node_and_actor_bytes_checked=True,cached_next_and_live_key=True,full_filter_and_countdown=True,return_and_release_order=True))
 return report
