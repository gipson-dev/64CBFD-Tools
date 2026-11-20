"""Compatible-object SDK32 check; no arbitrary native stack initialization."""
from pathlib import Path
import json,re,subprocess
from tools.tests import game_list_render_1517e28c_oracle as g
from tools.experiments import game_list_render_1517e28c_recovery as source
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
out=source.OUT
ROOT=source.ROOT
BODY=source.BODY
PREAMBLE=source.PREAMBLE
RECORD=source.RECORD

def hash_words(words):
    h=2166136261
    for w in words:h=((h^w)*16777619)&0xFFFFFFFF
    return h
def memory_hash(m):
    return hash_words([g.read(m,g.NODES+i*4)for i in range(64)]+
        [g.read(m,g.COMMANDS+i*4)for i in range(32)]+
        [g.read(m,g.HEAD),g.read(m,g.TOUCHED,1),g.read(m,g.GATE,1),g.read(m,g.INTENSITY,1)])
def call_hash(calls):
    return hash_words([w for target,args in calls for w in(target,len(args),*args)])
def corpus():
    rows=[]
    for c in g.cases():
        initial=g.fixture(c);want,calls,value=g.reference(initial,c)
        first_depth=next((ordinal for ordinal,(target,args)in enumerate(calls,1)if target==g.DEPTH),None)
        if first_depth is not None and(c.seed+first_depth)%3==0:continue
        meta=[c.seed,c.mode,c.phase,value,call_hash(calls),memory_hash(want),len(calls)]
        nodes=[g.read(initial,g.NODES+4*i)for i in range(64)]
        commands=[g.read(initial,g.COMMANDS+4*i)for i in range(32)]
        rows.append('{'+','.join('{'+','.join('0x%Xu'%v for v in a)+'}'for a in(meta,nodes,commands))+'}')
    return rows
def harness(body=BODY):
    rows=corpus()
    code='#include <ultra64.h>\n'+RECORD+'\n'+PREAMBLE+r'''
struct Case {u32 meta[7],nodes[64],commands[32];};
static const struct Case cases[]={ROWS};
static const struct Case *current;
struct Slot {ListRecord1AB530 record;u8 extra[12];};
static struct Slot nodes[4];
static Gfx commands[16];
static u8 context[32];
static f32 point[3];
ListRecord1AB530 *D_800DDD64;
u8 D_800DDD60,D_800DCDD0,D_800DD2D0;
u8 *D_800B0DF0;
f32 *D_8008CFFC[2];
const ListFlarePair1AB530 D_8008D004={{0,1}},D_8008D008={{7,3}},D_8008D00C={{1,30}};
static u32 ordinal,trace,error,observed[100];
static u32 hash(u32 h,u32 w){return(h^w)*16777619u;}
static void call(u32 target,u32 n,const u32 *args){u32 i;ordinal++;trace=hash(hash(trace,target),n);for(i=0;i<n;i++)trace=hash(trace,args[i]);}
static u32 word(f32 f){union{u32 w;f32 f;}v;v.f=f;return v.w;}
static u32 readLE(const void*p){const u8*q=p;return(u32)q[0]|(u32)q[1]<<8|(u32)q[2]<<16|(u32)q[3]<<24;}
static void writeLE(void*p,u32 w){u8*q=p;q[0]=w;q[1]=w>>8;q[2]=w>>16;q[3]=w>>24;}
static u32 address(const void*p){u32 v=(u32)p;
 if(!p)return 0;
 if(v>=(u32)nodes&&v<(u32)nodes+sizeof(nodes))return 0x30000u+v-(u32)nodes;
 if(v>=(u32)commands&&v<(u32)commands+sizeof(commands))return 0x50000u+v-(u32)commands;
 if(p==&D_800DD2D0)return 0x800DD2D0u;
 error=1;return 0xDEAD0000u;}
static u32 answer(u32 target){return(u32[4]){1,0,2,0xFFFFFFFFu}[(current->meta[0]+current->meta[1]+ordinal+(target==0x1517EAACu))%4];}
static void effect(ListRecord1AB530*node){
 node->valueC=current->meta[0]*0.5f+ordinal;node->value10=(f32)(-(s32)current->meta[1])*1.25f;
 if(current->meta[1]==1)node->flags2E^=3;
 if(current->meta[1]==2){D_800DDD64=&nodes[3].record;D_800DCDD0=ordinal&1;
  if(node->next)node->next=node->next->next;node->sample2A=ordinal&1?0xFFFC:0;}}
__attribute__((noinline,noipa)) s32 func_1517EAAC(f32 x,f32 y,f32 z,f32*px,f32*py){
 ListRecord1AB530*node=(ListRecord1AB530*)((u8*)px-12);
 u32 args[5]={word(x),word(y),word(z),address(px),address(py)};
 if(py!=&node->value10||word(x)!=word(point[0])||word(y)!=word(point[1])||word(z)!=word(point[2]))error=1;
 call(0x1517EAACu,5,args);effect(node);return(s32)answer(0x1517EAACu);}
__attribute__((noinline,noipa)) s32 func_1517EC1C(ListRecord1AB530*node,u32*depth){
 u32 args[2]={address(node),0x7FFFF000u+current->meta[2]-120+0x6C};
 call(0x1517EC1Cu,2,args);
 if((current->meta[0]+ordinal)%3)*depth=(u32[4]){4000,1,0,0xFFFFFFFFu}[(current->meta[0]/4+ordinal)%4];
 node->depth2C=(node->depth2C+(current->meta[1]&1)*31)&65535;effect(node);return(s32)answer(0x1517EC1Cu);}
__attribute__((noinline,noipa)) Gfx *func_1517E4A8(Gfx*cursor,ListRecord1AB530*node,s32 group,s32 count,s32 falloff,s32 strength,u8*intensity){
 u32 args[7]={address(cursor),address(node),group,count,falloff,strength,address(intensity)};
 call(0x1517E4A8u,7,args);writeLE(cursor,0xC0000000u|(u32)group<<16|(u32)count<<8|(u32)falloff);writeLE((u8*)cursor+4,strength);
 node->state28=(u16)(node->state28+count);D_800DDD60=1;
 if(intensity)*intensity=(current->meta[0]+ordinal*31)&255;
 if(current->meta[1]==3)node->next=0;return cursor+1;}
BODY
static u32 digest(void){u32 h=2166136261u,i,j,w;ListRecord1AB530*n;
 for(i=0;i<4;i++){n=&nodes[i].record;for(j=0;j<64;j+=4){w=readLE((u8*)&nodes[i]+j);
  if(j==0x24)w=address(n->next);
  if(j==0x28)w=(u32)(u16)n->state28<<16|n->sample2A;
  if(j==0x2C)w=(u32)n->depth2C<<16|(u32)n->flags2E<<8|n->first2F;
  if(j>=0x30){u8*p=(u8*)&nodes[i]+j;w=(u32)p[0]<<24|(u32)p[1]<<16|(u32)p[2]<<8|p[3];}
  observed[i*16+j/4]=w;h=hash(h,w);}}
 for(i=0;i<32;i++){w=readLE((u8*)commands+4*i);observed[64+i]=w;h=hash(h,w);}
 observed[96]=address(D_800DDD64);observed[97]=D_800DDD60;observed[98]=D_800DCDD0;observed[99]=D_800DD2D0;
 h=hash(h,address(D_800DDD64));h=hash(h,D_800DDD60);h=hash(h,D_800DCDD0);return hash(h,D_800DD2D0);}
static int run(void){u32 c,i,j,w;Gfx*value;ListRecord1AB530*n;
 if(sizeof(void*)!=4||sizeof(ListRecord1AB530)!=52||sizeof(struct Slot)!=64||__builtin_offsetof(ListRecord1AB530,second30)!=0x30)return 10;
 for(c=0;c<sizeof(cases)/sizeof(cases[0]);c++){
 current=&cases[c];ordinal=error=0;trace=2166136261u;
 for(i=0;i<4;i++){n=&nodes[i].record;
  for(j=0;j<64;j+=4){w=current->nodes[i*16+j/4];writeLE((u8*)&nodes[i]+j,w);
   if(j==0x24)n->next=w?&nodes[(w-0x30000u)/64].record:0;
   if(j==0x28){n->state28=w>>16;n->sample2A=w;}
   if(j==0x2C){n->depth2C=w>>16;n->flags2E=w>>8;n->first2F=w;}
   if(j>=0x30){u8*p=(u8*)&nodes[i]+j;p[0]=w>>24;p[1]=w>>16;p[2]=w>>8;p[3]=w;}}}
 for(i=0;i<32;i++)writeLE((u8*)commands+4*i,current->commands[i]);
 for(i=0;i<3;i++)point[i]=((s32)i-1)*1.25f+current->meta[0]*0.125f;
 D_800DDD64=current->meta[0]?&nodes[0].record:0;D_800DDD60=0xA5;D_800DD2D0=current->meta[0];
 D_800DCDD0=(current->meta[0]+current->meta[1])%4!=0;D_800B0DF0=context;context[16]=1;D_8008CFFC[0]=0;D_8008CFFC[1]=point;
 value=func_1517E28C(commands,0x87654321u);
 if(error||ordinal!=current->meta[6]||trace!=current->meta[4])return 11;
 if(address(value)!=current->meta[3]||digest()!=current->meta[5]){
  u32 report[104];report[0]=c;report[1]=address(value);report[2]=digest();report[3]=current->meta[5];
  for(i=0;i<100;i++)report[4+i]=observed[i];
  __asm__ volatile(".byte 0xcd,0x80" : : "a"(4),"b"(1),"c"(report),"d"(sizeof(report)) : "memory");
  return 12;}
 }return 0;}
'''
    return code.replace('0x7FFFF000u','0x%Xu'%g.STACK).replace('ROWS',',\n'.join(rows)).replace('BODY',body)+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'),len(rows)

def run():
    where=out/'native';where.mkdir(exist_ok=True);text,count=harness();valid=[]
    def execute(name,text,opt):
        p=where/(name+'.c');p.write_text(text);exe=where/name
        q=subprocess.run(native_command(opt)+[str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
        assert q.returncode==0,q.stdout+q.stderr
        completed=subprocess.run([str(exe)],timeout=15,capture_output=True)
        if completed.stdout:
            import struct
            diagnostics=struct.unpack('<104I',completed.stdout)
            (where/(name+'-mismatch.json')).write_text(json.dumps(diagnostics,indent=2)+'\n')
        return completed.returncode
    for opt in ('-O0','-O2','-O3'):
        result=execute(opt[1:],text,opt);assert result==0,(opt,result)
        valid.append(dict(optimization=opt,cases=count,UBSan=True,strict_aliasing=True))
    controls={'unsigned-depth-test':BODY.replace('(s32)((u32)node->depth2C - sampleDepth)','((u32)node->depth2C - sampleDepth)'),
      'nonzero-success':BODY.replace(') != 1)',') == 0)'),
      'stale-helper-flags':BODY.replace('                    flags = node->flags2E;','').replace('                flags = node->flags2E;','')}
    codes={}
    for name,body in controls.items():
        assert body!=BODY;altered,_=harness(body);code=execute(name,altered,'-O2');assert code in (11,12),(name,code);codes[name]=code
    report=dict(valid=valid,rejected=codes,first_depth_output_initialized=True,retained_later_unwritten_depth_covered=True,
        compatible_objects_only=True,native_stack_or_fault_prefix_claim=False)
    (where/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':print(json.dumps(run()))
