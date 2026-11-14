from pathlib import Path
import sys,json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r=Path.cwd();o=r/'conker/build/game-template-effect-151a9390-screen'
from tools.tests import game_template_effect_151a9390_behavior as b
s=(o/'selected.c').read_text();a=s.index('typedef struct { f32 x, y, z; } TemplatePosition151A9390;');z=s.index('typedef struct {\n    f32 base0, base1, range0, range1;',a);piece=s[a:z];head,body=piece.split('/* Select a template',1);body='/* Select a template'+body
bad={
 'wrong_limit':body.replace('selector < 9','selector < 8'),
 'wrong_request_flag':body.replace('low = low ? 4 : 0','low = low ? 16 : 0'),
 'wrong_payload_size':body.replace('table->payload, 0x2C','table->payload, 0x28'),
 'wrong_payload_flag':body.replace('record[0x28] |= 1','record[0x28] |= 4'),
 'wrong_default_lifetime':body.replace('? 300 : lifetime','? 301 : lifetime'),
 'wrong_coordinate':body.replace('(s32)position->x','(s32)position->y'),
 'wrong_effect_kind':body.replace('table->effectKind, 255','table->arg4, 255')}
assert all(v!=body for v in bad.values()) and len(set(bad.values()))==7
code='#include <ultra64.h>\ntypedef struct {s8 unk0,unk1;s16 unk2;s8 unk4;u8 pad5;} Header;\ntypedef struct struct225 struct225;\nvoid *memcpy(void *,const void *,u32);\n'+head+'\nu8 *func_151A8B20(TemplateRequest151A9390*,s16,s32,u8,s32);\n'+'\n'.join(v.replace('func_151A9390','candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
code+=r'''
typedef union {u32 u;f32 f;} Bits;
typedef struct {u32 flags,selector,hasOwner,hasPosition,life,channel,context,p0,p1,mutation,outcome,seed,requestFlags,primary,secondary,vector[3],coords[3],headerFlags,headerLife,headerKind,args[4];u8 output[44];} Case;
static const Case cases[]={
'''
rows=[]
for c in b.cases():
 if c.phase or c.mutation&2:continue
 m,calls,obs=b.reference(b.fixture(c),c);request=next((x[1] for x in obs if x[0]=='REQUEST'),bytes(40));event=next((x for x in obs if x[0]=='HEADER'),('HEADER',bytes(6),bytes(12)));args=next((a for t,a in calls if t==b.EMIT),(0,)*11)
 values=[c.flags,c.selector,bool(c.owner),bool(c.position),b.u32(c.lifetime),c.channel,c.context,c.parameter0,c.parameter1,c.mutation,c.outcome,c.seed,request[0],int.from_bytes(request[8:12],'big'),int.from_bytes(request[12:16],'big')]
 row='{'+','.join('0x%Xu'%v for v in values)+',{'+','.join('0x%Xu'%int.from_bytes(request[i:i+4],'big') for i in (16,20,24))+'},{'+','.join('0x%Xu'%int.from_bytes(event[2][i:i+4],'big') for i in (0,4,8))+'},'
 row+=','.join('0x%Xu'%v for v in (event[1][0],int.from_bytes(event[1][2:4],'big'),event[1][4]))+',{' + ','.join(str(args[i]) for i in (2,3,4,8))+'},{'+','.join(str(m[b.OUTPUT+128+i]) for i in range(44))+'}}'
 rows.append(row)
code+=',\n'.join(rows)+'\n};\n'
code+=r'''
typedef char TemplateLayout[sizeof(EffectTemplate151A9390)==20 && __builtin_offsetof(EffectTemplate151A9390,payload)==16?1:-1];
typedef char RequestLayout[sizeof(TemplateRequest151A9390)==40 && __builtin_offsetof(TemplateRequest151A9390,type)==36?1:-1];
EffectTemplate151A9390 D_8008F9AC[9];static u8 payloads[9][2][44],output[1024];static s16 owner[3];static TemplatePosition151A9390 position;
static const Case*current;static u32 allocated,copied,emitted,error;
static f32 real(u32 x){Bits b;b.u=x;return b.f;}static u32 word(f32 x){Bits b;b.f=x;return b.u;}
static void effect(u32 index){u32 j;if(!current->mutation)return;
 for(j=0;j<9;j++){EffectTemplate151A9390*t=D_8008F9AC+j;t->payload=payloads[j][1];t->arg2=(current->seed+index*7+8)&255;t->arg3=(current->seed+index*7+9)&255;t->arg4=(current->seed+index*7+10)&255;t->headerKind=(current->seed+index*7+11)&255;t->effectKind=(current->seed+index*7+12)&255;}
 position.x=(f32)(-20+(s32)current->seed+(s32)index*3)+.75f;position.y=position.x+1.;position.z=position.x+2.;
 for(j=0;j<3;j++)owner[j]=current->seed+index*17+j;
}
u8 *func_151A8B20(TemplateRequest151A9390*p,s16 life,s32 size,u8 channel,s32 context){
 if(allocated||p->flags!=current->requestFlags||p->owner!=(current->hasOwner?owner:0)||word(p->primary)!=current->primary||word(p->secondary)!=current->secondary||
 word(p->position.x)!=current->vector[0]||word(p->position.y)!=current->vector[1]||word(p->position.z)!=current->vector[2]||word(p->parameter0)!=current->p0||word(p->parameter1)!=current->p1||p->type!=2||p->mode!=-1||p->enabled!=1||
 life!=(s16)current->life||size!=44||channel!=(u8)current->channel||context!=(s32)current->context)error=1;
 allocated++;effect(0);return current->outcome?output:0;
}
void *memcpy(void*dest,const void*src,u32 n){u32 i,selector=(u8)current->selector;const u8*bytes=(const u8*)src;
 if(dest!=output+128||src!=payloads[selector][current->mutation?1:0]||n!=44||!allocated||copied)error=1;
 if(n<=44)for(i=0;i<n;i++)((u8*)dest)[i]=bytes[i];copied++;effect(1);return dest;
}
struct225 *func_1516284C(Header*h,s32 address,s32 a2,s32 a3,s32 a4,u8 a5,u8 a6,s32 a7,u8 a8,u8 a9,s32 a10){s32*p=(s32*)address;
 if(!allocated||emitted||(u8)h->unk0!=current->headerFlags||h->unk1!=2||(u16)h->unk2!=current->headerLife||(u8)h->unk4!=current->headerKind||
 (u32)p[0]!=current->coords[0]||(u32)p[1]!=current->coords[1]||(u32)p[2]!=current->coords[2]||a2!=(s32)current->args[0]||a3!=(s32)current->args[1]||a4!=(s32)current->args[2]||a5!=255||a6||a7||a8!=current->args[3]||a9!=255||a10!=1)error=1;
 emitted++;return (struct225*)0;
}
typedef void(*Candidate)(u8,u8,s16*,TemplatePosition151A9390*,f32,f32,s16,u8,s32);
'''
code+='static Candidate candidates[]={'+','.join('candidate_'+str(i) for i in range(8))+'};\n'
code+=r'''
static int run(void){u32 i,j,k,l,q,killed=0;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;
  for(j=0;j<8;j++){
   for(k=0;k<9;k++){EffectTemplate151A9390*t=D_8008F9AC+k;t->primary=1.+k;t->secondary=-2.-k;t->arg2=(8*11+k*7)&255;t->arg3=(9*11+k*7)&255;t->arg4=(10*11+k*7)&255;t->headerKind=(11*11+k*7)&255;t->effectKind=(12*11+k*7)&255;t->payload=payloads[k][0];
    for(l=0;l<2;l++)for(q=0;q<44;q++)payloads[k][l][q]=(q*23+k*17+l*128+current->seed)&255;
   }
   for(k=0;k<1024;k++)output[k]=(k*19+current->seed*7)&255;
   owner[0]=-32768;owner[1]=0;owner[2]=32767;position.x=-12.75;position.y=.5;position.z=32766.75;
   allocated=copied=emitted=error=0;
   candidates[j](current->flags,current->selector,current->hasOwner?owner:0,current->hasPosition?&position:0,real(current->p0),real(current->p1),current->life,current->channel,current->context);
   k=(u8)current->selector<9;
   if(allocated!=k||copied!=(k&&current->outcome)||emitted!=(k&&((u8)current->flags&4)!=0))error=1;
   for(k=0;k<1024;k++)if(output[k]!=(k>=128&&k<172?current->output[k-128]:(u8)(k*19+current->seed*7)))error=1;
   if(error){if(j==0)return 10;killed|=1u<<(j-1);}
  }
 }
 return killed==127u?0:11;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
p=o/'native-template-effect.c';p.write_text(code);profiles=[]
for opt in ('-O0','-O2','-O3'):
 for alias in ('-fstrict-aliasing','-fno-strict-aliasing'):
  exe=o/('native-template-effect'+opt+alias);q=subprocess.run(native_command(opt)+[alias,'-o',str(exe),str(p)],cwd=r,capture_output=True,text=True)
  assert q.returncode==0,(q.stdout,q.stderr);q=subprocess.run([str(exe)],cwd=r,capture_output=True);assert q.returncode==0,(opt,alias,q.returncode,q.stderr)
  profiles.append((opt,alias))
report=dict(native32=True,cases=len(rows),profiles=profiles,ubsan=True,negative_controls=list(bad),all_controls_detected=True,request_retained_bytes_excluded=4,header_retained_bytes_excluded=1,typed_disjoint_inputs=True,helpers_modeled=True)
(o/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
