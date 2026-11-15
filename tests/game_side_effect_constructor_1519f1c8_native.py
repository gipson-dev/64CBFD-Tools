"""Native32 typed request/payload checks; skip reads of uninitialized fields."""
import itertools,json,subprocess
from tools.experiments import game_side_effect_constructor_1519f1c8_match as s
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def source():
    cases=list(itertools.product((0,6,7,0xFFFFFF06),(0,1),(0,1),(0,10,255),(0,1,2,4,7)))
    prefix='#include <ultra64.h>\n'+s.PIN['declarations']+'''
s32 func_1519EF90(u8 *,u8,f32 *);
f32 D_800A8CE8,D_800A8CEC;
u8 D_800AB414[768];
typedef struct {u8 reserved[0x18];u8 *actor;u8 tail[0x50];} NativeState;
typedef struct {u8 reserved[0x14];f32 x,y,z;} NativeActor;
typedef struct {u8 reserved[0x98];void *payload;u8 tail[8];} NativeObject;
typedef struct {u32 mode,hit,success,color,effects;} NativeCase;
static NativeState state;
static NativeActor actor,other;
static NativeObject created;
static SidePayload1519F1C8 output;
static const NativeCase *current;
static u32 ordinal,failure;
static f32 number(u32 v){union {u32 u;f32 f;} x;x.u=v;return x.f;}
static u32 word(f32 v){union {u32 u;f32 f;} x;x.f=v;return x.u;}
typedef char request_size[sizeof(SideRequest1519F1C8)==28?1:-1];
typedef char payload_size[sizeof(SidePayload1519F1C8)==80?1:-1];
typedef char state_actor[__builtin_offsetof(NativeState,actor)==0x18?1:-1];
typedef char object_payload[__builtin_offsetof(NativeObject,payload)==0x98?1:-1];
u8 func_151D8E20(void){
 if(ordinal++!=0)failure=1;
 if(current->effects&1){state.actor=(u8 *)&other;actor.x=11.f;actor.z=-17.f;D_800A8CE8=number(0x80000000);D_800A8CEC=number(0x7FC12345);}
 if(current->effects&2)for(u32 i=0;i<768;i++)D_800AB414[i]=(255-i)&255;
 return current->color;
}
s32 func_1519EF90(u8 *p,u8 mode,f32 *point){
 SidePayload1519F1C8 *v=(SidePayload1519F1C8 *)p;
 if(ordinal++!=1||mode!=(current->mode&255)||v->state!=(u8 *)&state||v->kind!=6||v->referenceX!=actor.x||v->referenceZ!=actor.z)failure=2;
 if(current->effects&4){v->scale=number(0xDEADBEEF);state.actor=(u8 *)&actor;for(u32 i=0;i<768;i++)D_800AB414[i]^=0x55;}
 if(current->hit){point[0]=number(0xC0500000);point[1]=number(0x80000000);point[2]=number(0x7FC54321);}
 return current->hit;
}
u8 *func_15147A80(void *p,s32 bytes,s32 entry,s32 active,s32 first,s32 second,s32 resource,s32 value,void *optional,u8 channel,s32 context){
 SideRequest1519F1C8 *q=(SideRequest1519F1C8 *)p;
 if(ordinal++!=2||bytes!=80||entry!=36||active!=5||first!=5||second!=5||resource||value||optional!=(u8 *)&state+0x34||channel!=255||context!=1)failure=3;
 if(q->lifetime!=300||q->flags!=(current->hit?0x46:0x42)||q->count!=10||q->mode!=(s32)(current->mode&255))failure=4;
 if(current->hit&&(word(q->position.x)!=0xC0500000||word(q->position.y)!=0x80000000||word(q->position.z)!=0x7FC54321))failure=5;
 return current->success?(u8 *)&created:0;
}
void *memcpy(void *to,const void *from,u32 n){
 if(ordinal++!=3||to!=&output||n!=80)failure=6;
 for(u32 i=0;i<n;i++)((u8 *)to)[i]=((const u8 *)from)[i];
 return to;
}
'''
    rows=['{'+','.join('0x%Xu'%v for v in c)+'}' for c in cases]
    harness='\nstatic const NativeCase cases[]={'+','.join(rows)+'};\n'+'''
static int run(void){
 for(u32 i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  current=&cases[i];ordinal=failure=0;state.actor=(u8 *)&actor;actor.x=1.25f;actor.y=4.5f;actor.z=-2.f;other.x=-3.f;other.y=4.5f;other.z=9.f;
  D_800A8CE8=.25f;D_800A8CEC=.5f;created.payload=&output;
  for(u32 j=0;j<768;j++)D_800AB414[j]=(j*13+0x53)&255;
  for(u32 j=0;j<sizeof(output);j++)((u8 *)&output)[j]=0xA5;
  u8 *answer=func_1519F1C8((u8 *)&state,current->mode);
  if(failure||ordinal!=(current->success?4:3)||answer!=(current->success?(u8 *)&created:0))return 141;
  if(!current->success)continue;
  u32 scale=current->effects&4?0xDEADBEEF:current->effects&1?0x80000000:0x3E800000;
  if(output.state!=(u8 *)&state||output.kind!=6||word(output.scale)!=scale||word(output.speed)!=(current->effects&1?0x7FC12345:0x3F000000)||word(output.phase)||word(output.elapsed))return 142;
  if(output.duration!=200||output.alpha!=255||output.width!=40||output.height!=25||output.count!=6||output.command!=0x325||output.zero28||output.zero46||output.style!=3||output.first!=0x55||output.second!=3||output.third!=0x55||output.fourth!=0x88||output.fifth!=0xC4||output.limit!=1.f||output.rate!=1.5f)return 142;
  u32 color=current->color&255;
  if(output.red!=D_800AB414[color*3]||output.green!=D_800AB414[color*3+1]||output.blue!=D_800AB414[color*3+2])return 142;
  if(current->hit&&(word(output.position.x)!=0xC0500000||word(output.position.y)!=0x80000000||word(output.position.z)!=0x7FC54321))return 142;
 }
 return 0;
}
'''
    return prefix+s.PIN['source']+harness+START,len(cases)

def main():
    text,count=source();path=s.OUT/'native.c';path.write_text(text);profiles=[];controls=0
    mutants={'flags':text.replace('request.flags = 0x42;','request.flags = 0x40;'),
             'kind':text.replace('packet.kind = 6;','packet.kind = 7;'),
             'width':text.replace('packet.width = 40;','packet.width = 41;')}
    for label,bad in mutants.items():assert bad!=text,label
    for opt in ('-O0','-O2','-O3'):
        for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
            exe=s.OUT/('native'+opt+alias);p=subprocess.run(native_command(opt)+['-mstackrealign',alias,'-o',str(exe),str(path)],capture_output=True,text=True);assert p.returncode==0,p.stderr
            q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==0,(opt,alias,q.returncode,q.stderr);profiles.append(opt+alias)
        for label,wrong in mutants.items():
            bad=s.OUT/('native-control-'+label+'.c');bad.write_text(wrong);exe=bad.with_suffix('')
            p=subprocess.run(native_command(opt)+['-mstackrealign','-o',str(exe),str(bad)],capture_output=True,text=True);assert p.returncode==0,p.stderr
            assert subprocess.run([str(exe)],capture_output=True).returncode in (141,142),label;controls+=1
    report=dict(cases_per_profile=count,profiles=profiles,effective_controls=controls,UBSan=True,actual_typed_objects=True,uninitialized_field_reads_excluded=True)
    (s.OUT/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
