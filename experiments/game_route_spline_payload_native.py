"""Native32 spline payload C with real helper bodies and effectful providers."""
import argparse
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import subprocess

from tools.experiments import game_route_spline_payload_layout as layout
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.tests import test_game_route_spline_payload_recovery as guest
from tools.tests.test_game_projected_packet_draw import native_command

BUILD='conker/build/game-route-spline-payload-integration'
CASES=6270
HELPER_SHA={'func_15086CBC':'31b0b5b9cac0396e1359a3952051370b2d34a57194a298b3ea13c3caa21022e9',
    'func_1508907C':'589294572985178cc986279fc419c6f4e1f4df015f02fef8ff708c116184ad61',
    'func_1512D560':'b9c83513e453dcb50d5166ed0f7904fac0e1a2014bc6fe48603158de213a5efc',
    'func_150497E0':'27759ba0cb99958e7bc308312c14ee0f6ccf93ed9830ca7a20f64deb9ae7d619'}
FIELDS=('stop','null','initialized','valid','fraction','frames','heading','bank','cursor','mode','count','late','alias','effect')
DEFAULTS=dict(stop=0,null=0,initialized=1,valid=4,fraction=.25,frames=1,heading=45.,bank=0,cursor=0,mode=0,count=8,late=0,alias=0,effect=0)
HEADER=r'''#include <ultra64.h>
s16 D_80087290;u8 *D_800D2350,*D_800DC2B0;s8 D_800D23A8;s32 D_800BE9E4;
f32 D_8009DA0C=999.0f,D_8009DA10=0.017f;
typedef union {u64 align;u8 bytes[0x14000];} Arena;
static Arena arena,wanted;
static u8 *record,*actor,*object,*other,*table,*queue;
static u32 calls[512],wantedCalls[512],callCount,wantedCount,enqueueCount,splineCount,effect,trigMiss;
static u32 fired,everFired;
static u32 bits(f32 value){union{f32 f;u32 u;}x;x.f=value;return x.u;}
static f32 value(u32 encoding){union{f32 f;u32 u;}x;x.u=encoding;return x.f;}
static f32 rounded(f32 x){volatile f32 result=x;return result;}
static void logCall(u32 code,u32 a,u32 b,u32 c,u32 d,u32 e,u32 f,u32 g){
 u32 *p=calls+callCount*8;if(callCount>=64)__builtin_trap();
 p[0]=code;p[1]=a;p[2]=b;p[3]=c;p[4]=d;p[5]=e;p[6]=f;p[7]=g;callCount++;
}
static void enqueue_effect(void){
 enqueueCount++;
 if(enqueueCount!=1)return;
 if(effect&&effect!=2)fired|=1U<<effect;
 if(effect==1||effect==4)*(u8 **)(actor+0x318)=other;
 if(effect==3){*(f32 *)(record+0x38)=-9.5f;*(f32 *)(record+0x3C)=6.25f;*(f32 *)(record+0x40)=100.0f;*(f32 *)(actor+0x40)=0.625f;}
 if(effect==4)object[0x23D]=128;
 if(effect==5)D_800BE9E4=8;
}
static void spline_effect(void){splineCount++;if(effect==2&&splineCount==1){fired|=4;*(f32 *)(record+0x34)=0.875f;}}
'''
WRAPPERS=r'''
s32 func_15086CBC(s32 id,f32 *x,f32 *y,f32 *z){
 s32 result=actual_position(id,x,y,z);if(!result)__builtin_trap();
 logCall(1,(u32)id,bits(*x),bits(*y),bits(*z),0,0,0);return result;
}
u8 func_1508907C(u8 id,u8 type,u8 excluded,u8 preferred){
 logCall(2,id,type,excluded,preferred,0,0,0);return actual_selector(id,type,excluded,preferred);
}
void func_1512D560(u8 *obj,s32 command,void *payload){
 logCall(3,(u32)obj,(u32)command,(u32)payload,obj[0x23D],0,0,0);
 actual_enqueue(obj,command,payload);enqueue_effect();
}
f32 func_150497E0(f32 *p,s32 index,f32 phase){
 f32 result;logCall(4,bits(p[0]),bits(p[1]),bits(p[2]),bits(p[3]),(u32)index,bits(phase),0);
 result=actual_spline(p,index,phase);spline_effect();return result;
}
f32 sinf(f32 angle){logCall(5,bits(angle),0,0,0,0,0,0);return trig(bits(angle),0);}
f32 cosf(f32 angle){logCall(6,bits(angle),0,0,0,0,0,0);return trig(bits(angle),1);}
'''
REFERENCE=r'''
static void reference_queue(u8 *obj,s32 command,void *payload){
 u8 *q;u32 i;logCall(3,(u32)obj,(u32)command,(u32)payload,obj[0x23D],0,0,0);
 q=D_800DC2B0+obj[0x23D]*176;i=*(u32 *)(q+172);*(u32 *)(q+i*8)=(u32)command;
 q=D_800DC2B0+obj[0x23D]*176;i=*(u32 *)(q+172);*(u32 *)(q+i*8+4)=(u32)payload;
 q=D_800DC2B0+obj[0x23D]*176;*(u32 *)(q+172)+=1;
 q=D_800DC2B0+obj[0x23D]*176;if(*(u32 *)(q+172)==20)*(u32 *)(q+172)=0;
 enqueue_effect();
}
static u8 reference_neighbor(u8 id,u8 type,u8 excluded){
 int j;u8 c,result=255;logCall(2,id,type,excluded,0,0,0,0);
 if(id<D_80087290)for(j=0;j<5;j++){
  c=D_800D2350[id*16+9+j];if(c==255||c==excluded||D_800D2350[c*16+14]!=type)continue;
  result=c;if(D_800D2350[c*16+15]==0)break;
 }
 return result;
}
static void reference_position(u8 id,f32 *x,f32 *y,f32 *z){
 if(id>=D_80087290)__builtin_trap();
 *x=(f32)*(s16 *)(D_800D2350+id*16);*y=(f32)*(s16 *)(D_800D2350+id*16+2);*z=(f32)*(s16 *)(D_800D2350+id*16+4);
 logCall(1,id,bits(*x),bits(*y),bits(*z),0,0,0);
}
static f32 reference_cubic(f32 *p,f32 phase){
 f32 half,cubic,quadratic,linear,result;
 logCall(4,bits(p[0]),bits(p[1]),bits(p[2]),bits(p[3]),0,bits(phase),0);
 half=rounded(-.5f*p[0]);
 cubic=rounded(rounded(.5f*p[3])+rounded(rounded(half+rounded(1.5f*p[1]))+rounded(-1.5f*p[2])));
 quadratic=rounded(rounded(-.5f*p[3])+rounded(rounded(p[0]+rounded(-2.5f*p[1]))+rounded(p[2]+p[2])));
 linear=rounded(rounded(.5f*p[2])+half);
 result=rounded(rounded(rounded(rounded(rounded(rounded(cubic*phase)+quadratic)*phase)+linear)*phase)+p[1]);
 spline_effect();return result;
}
static void reference(s32 stop){
 u8 *captured=*(u8 **)(actor+0x318),*payload=record+0x4C;u8 id,next,old;int i,c,previous=0;
 f32 points[6][4],phase,angle,sine,cosine;
 if(!captured)return;
 if(stop){
  *(s32 *)(payload+16)=120;*(f32 *)(payload+12)=D_8009DA0C;
  reference_queue(*(u8 **)(actor+0x318),10,payload);
  reference_queue(*(u8 **)(actor+0x318),6,(void *)(u32)captured[0x23D]);record[0x49]=0;return;
 }
 if((s8)record[0x49]==0){
  for(i=0;i<D_80087290;i++)if(D_800D2350[i*16+14]==6&&D_800D2350[i*16+15]==(u8)(D_800D23A8+1)){
   record[0x44]=(u8)i;i=D_80087290;
  }
  record[0x45]=reference_neighbor(record[0x44],6,255);
  record[0x46]=reference_neighbor(record[0x45],6,record[0x44]);
  record[0x47]=reference_neighbor(record[0x46],6,record[0x45]);
  for(i=0;i<3;i++)*(f32 *)(record+56+i*4)=*(f32 *)(actor+20+i*4);
  *(f32 *)(record+52)=0;reference_queue(*(u8 **)(actor+0x318),5,(void *)(u32)captured[0x23D]);record[0x49]=1;
 }
 phase=rounded(*(f32 *)(record+52)+rounded(D_8009DA10*(f32)D_800BE9E4));*(f32 *)(record+52)=phase;
 if(phase>=1){
  id=record[0x46];
  if(id==255)*(f32 *)(record+52)=1;
  else{
   next=record[0x47];old=record[0x45];record[0x45]=id;*(f32 *)(record+52)=rounded(phase-1);
   record[0x46]=next;record[0x44]=old;record[0x47]=reference_neighbor(next,6,id);
  }
 }
 for(i=0;i<4;i++){
  id=record[0x44+i];
  if(id!=255){
   previous=1;reference_position(id,&points[0][i],&points[1][i],&points[2][i]);
   reference_position(reference_neighbor(record[0x44+i],4,255),&points[3][i],&points[4][i],&points[5][i]);
  }else if(previous){
   previous=0;angle=(f32)((f64)*(f32 *)(actor+64)*0.01745);
   logCall(5,bits(angle),0,0,0,0,0,0);sine=trig(bits(angle),0);
   points[0][i]=rounded(*(f32 *)(record+56)-rounded(sine*500));points[1][i]=rounded(*(f32 *)(record+60)+180);
   logCall(6,bits(angle),0,0,0,0,0,0);cosine=trig(bits(angle),1);
   points[2][i]=rounded(*(f32 *)(record+64)-rounded(cosine*500));points[3][i]=*(f32 *)(record+56);
   points[4][i]=rounded(*(f32 *)(record+60)+120);points[5][i]=*(f32 *)(record+64);
  }else{
   if(i<2)__builtin_trap();
   for(c=0;c<6;c++)points[c][i]=rounded(rounded(points[c][i-1]-points[c][i-2])+points[c][i-1]);
  }
 }
 phase=*(f32 *)(record+52);
 for(c=0;c<6;c++)*(f32 *)(payload+20+c*4)=reference_cubic(points[c],phase);
 *(u32 *)payload=0;*(u32 *)(payload+4)=0;*(f32 *)(payload+48)=30;*(f32 *)(payload+52)=30;*(f32 *)(payload+44)=0;
 reference_queue(*(u8 **)(actor+0x318),7,payload);
}
'''
FIXTURE=r'''
typedef struct {s32 stop,null,initialized,valid;u32 fraction;s32 frames;u32 heading;s32 bank,cursor,mode,count,late,alias,effect;} Case;
static void initialize(const Case *c){
 int i,j;u32 *p=(u32 *)arena.bytes;
 for(i=0;i<(int)sizeof(arena.bytes)/4;i++)p[i]=0xA5A5A5A5U;
 actor=arena.bytes+0x800;object=arena.bytes+0x1000;other=arena.bytes+0x1800;table=arena.bytes+0x2000;queue=arena.bytes+0x6000;
 record=c->alias==1?actor-0x58:arena.bytes+0x100;
 D_80087290=(s16)c->count;D_800D2350=table;D_800DC2B0=queue;D_800D23A8=(s8)c->mode;D_800BE9E4=c->frames;
 for(i=0;i<270;i++){
  for(j=0;j<3;j++)*(s16 *)(table+i*16+j*2)=(s16)((i*37+j*19)%511-255);
  for(j=0;j<5;j++)table[i*16+9+j]=255;
  table[i*16+14]=(u8)(i>=4&&i<8?4:6);table[i*16+15]=(u8)(i>=4&&i<8?0:(s8)c->mode+1);
 }
 for(i=0;i<4;i++){table[i*16+9]=(u8)((i+1)%4);table[i*16+10]=(u8)((i+3)%4);table[i*16+11]=(u8)(i+4);}
 if(c->late){for(i=0;i<258;i++)table[i*16+15]=3;table[257*16+14]=6;table[257*16+15]=(u8)((s8)c->mode+1);}
 for(i=0;i<4;i++)record[0x44+i]=(u8)(i<c->valid?i:255);
 *(f32 *)(actor+20)=17.5f;*(f32 *)(actor+24)=-91.25f;*(f32 *)(actor+28)=255;
 *(f32 *)(record+56)=35;*(f32 *)(record+60)=-182.5f;*(f32 *)(record+64)=510;
 record[0x49]=(u8)c->initialized;*(u32 *)(record+52)=c->fraction;*(u32 *)(actor+64)=c->heading;
 *(u8 **)(actor+0x318)=c->null?0:object;object[0x23D]=(u8)c->bank;other[0x23D]=1;
 for(i=0;i<256;i++)*(u32 *)(queue+i*176+172)=(u32)c->cursor;
 callCount=enqueueCount=splineCount=trigMiss=fired=0;effect=(u32)c->effect;
 for(i=0;i<512;i++)calls[i]=0;
}
static int compare(const Case *c){
 int i;u32 wantedFrames,wantedFired;initialize(c);reference(c->stop);
 if(trigMiss)return 71;
 for(i=0;i<(int)sizeof(arena.bytes)/4;i++)((u32 *)wanted.bytes)[i]=((u32 *)arena.bytes)[i];
 for(i=0;i<512;i++)wantedCalls[i]=calls[i];wantedCount=callCount;wantedFrames=(u32)D_800BE9E4;wantedFired=fired;
 initialize(c);func_150896EC(record,actor,c->stop);
 if(callCount!=wantedCount)return 22;
 for(i=0;i<512;i++)if(calls[i]!=wantedCalls[i])return 23;
 for(i=0;i<(int)sizeof(arena.bytes)/4;i++)if(((u32 *)arena.bytes)[i]!=((u32 *)wanted.bytes)[i])return 21;
 if(trigMiss)return 71;
 if(fired!=wantedFired)return 24;everFired|=fired;
 return (u32)D_800BE9E4==wantedFrames?0:24;
}
'''


def cases():
    result=list(guest.cases())
    result.extend(dict(stop=1,bank=b,cursor=c) for b,c in product(range(256),range(20)))
    result.extend(dict(effect=e,stop=s,initialized=i,valid=v) for e,s,i,v in product(range(1,6),(0,1),(0,1),range(1,5)))
    result.append(dict(valid=1,heading=.625))
    return [dict(DEFAULTS,**c) for c in result]


def translation_unit(root,body=None,subset=None):
    body=layout.source.joint_selected() if body is None else body
    if body.count('D_8009DA18')!=1:raise ValueError('Unexpected native heading-literal declaration')
    body=body.replace('    extern f64 D_8009DA18;\n','')
    rows=cases() if subset is None else subset;helpers=[];fingerprints={}
    for path,name,new in (('conker/src/game/generated_B3020.c','func_15086CBC','actual_position'),
            ('conker/src/game/generated_B3020.c','func_1508907C','actual_selector'),
            ('conker/src/game/generated_15AA10.c','func_1512D560','actual_enqueue'),
            ('conker/src/game/generated_76C90.c','func_150497E0','actual_spline')):
        owner=(root/path).read_text();lo,hi=function_span(owner,name);span=owner[lo:hi]
        fingerprints[name]=hashlib.sha256(span.encode()).hexdigest()
        helpers.append('#define '+name+' '+new+'\n'+span+'\n#undef '+name+'\n')
    if fingerprints!=HELPER_SHA:raise ValueError('Native helper source changed')
    trig={}
    for row in rows:
        heading=guest.guest.base.floating(guest.guest.base.bits(row['heading']))
        angle=guest.guest.base.bits(heading*.01745)
        x=guest.guest.base.floating(angle)
        trig[angle]=(guest.guest.base.bits(math.sin(x)),guest.guest.base.bits(math.cos(x)))
    trig[guest.guest.base.bits(.625*.01745)]=(guest.guest.base.bits(math.sin(guest.guest.base.floating(guest.guest.base.bits(.625*.01745)))),
        guest.guest.base.bits(math.cos(guest.guest.base.floating(guest.guest.base.bits(.625*.01745)))))
    provider='static f32 trig(u32 angle,int cosine){\nswitch(angle){\n'+''.join(
        'case 0x%XU:return value(cosine?0x%XU:0x%XU);\n'%(key,b,a) for key,(a,b) in sorted(trig.items()))+\
        'default:trigMiss++;return 0.375f;\n}}\n'
    values=[]
    for row in rows:
        encoded=[guest.guest.base.bits(row[k]) if k in ('fraction','heading') else int(row[k])&0xFFFFFFFF for k in FIELDS]
        values.append('{'+','.join('0x%XU'%v for v in encoded)+'}')
    require=int({r['effect'] for r in rows}>=set(range(1,6)))
    tail='#define REQUIRE_EFFECTS %d\n'%require+'static const Case cases[]={\n'+',\n'.join(values)+'\n};\n'+r'''
void _start(void){u32 i;int result=70;
 if(sizeof(void *)==4&&sizeof(f32)==4){result=0;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){result=compare(cases+i);if(result)break;}}
 if(!result&&REQUIRE_EFFECTS&&(everFired&62)!=62)result=72;
 __asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
    return HEADER+provider+'\n'.join(helpers)+WRAPPERS+body+REFERENCE+FIXTURE+tail,fingerprints


def controls():
    body=layout.source.joint_selected()
    cached_channel=body.replace('    f32 phase;','    u32 cachedChannel;\n    f32 phase;').replace(
        '        xCursor = node;','        xCursor = node;\n        cachedChannel = node[0x23D];').replace('((u8 *)xCursor)[0x23D]','cachedChannel')
    cached_frames=body.replace('    f32 phase;','    s32 cachedFrames = D_800BE9E4;\n    f32 phase;').replace(
        'D_8009DA10 * (f32)D_800BE9E4','D_8009DA10 * (f32)cachedFrames')
    return {'wrong-command':body.replace('), 10, payload);','), 9, payload);'),
        'signed-channel':body.replace('(void *)(u32)((u8 *)xCursor)[0x23D]','(void *)(s32)(s8)((u8 *)xCursor)[0x23D]'),
        'narrow-stop':body.replace('if (stop != 0)','if ((s8)stop != 0)'),
        'wrong-decrement':body.replace('*(f32 *)(record + 0x34) -= 1.0f;','*(f32 *)(record + 0x34) -= 2.0f;'),
        'float-scale':body.replace('(f32)((f64)*(f32 *)(actor + 0x40) * 0.01745)','*(f32 *)(actor + 0x40) * 0.01745f'),
        'fresh-channel':body.replace('((u8 *)xCursor)[0x23D]','(*(u8 **)(actor + 0x318))[0x23D]'),
        'cached-channel':cached_channel,'cached-frames':cached_frames,
        'reloaded-spline-phase':body.replace('    f32 phase;\n','').replace('            phase = *(f32 *)(record + 0x34);\n','').replace(
            ', 0, phase);',', 0, *(f32 *)(record + 0x34));')}


def qualify(root,out,smoke=False):
    layout.source.source.freeze(root,out);rows=cases()
    layout.source.qualify(root,out,joint=True)
    if len(rows)!=CASES:raise ValueError('Changed native corpus size')
    if smoke:rows=[rows[0],dict(DEFAULTS,initialized=0),dict(DEFAULTS,stop=1),dict(DEFAULTS,valid=1,heading=.625)]
    result={};bodies=[('O0',None,'-O0',False),('O2',None,'-O2',False),('O2-UBSAN',None,'-O2',True)]
    if not smoke:bodies.extend((n,b,'-O2',True) for n,b in controls().items())
    for name,body,opt,checked in bodies:
        if body is not None and body==layout.source.joint_selected():raise ValueError('Ineffective native source control '+name)
        unit=out/('native-'+name+('-smoke' if smoke else '')+'.c');text,helpers=translation_unit(root,body,rows);unit.write_text(text)
        exe=unit.with_suffix('');command=[*native_command(opt,checked),'-mstackrealign','-fno-strict-aliasing',str(unit),'-o',str(exe)]
        p=subprocess.run(command,cwd=root,capture_output=True,text=True)
        (unit.with_suffix('.compile.json')).write_text(json.dumps(dict(command=command,exit=p.returncode,diagnostics=p.stdout+p.stderr),indent=2)+'\n')
        if p.returncode or p.stdout or p.stderr:raise ValueError('Native compile failed '+name+'\n'+p.stdout+p.stderr)
        p=subprocess.run([str(exe)],cwd=root,capture_output=True,timeout=120);result[name]=p.returncode
        if p.stdout or p.stderr or (p.returncode!=0 if body is None else p.returncode not in (21,22,23,24)):
            raise ValueError('Native semantic/control failure '+name+' exit '+str(p.returncode))
        print(json.dumps(dict(profile=name,cases=len(rows),exit=p.returncode,smoke=smoke)),flush=True)
    receipt=dict(cases_per_positive_build=len(rows),profiles=['O0','O2','O2+UBSAN'],effective_controls=0 if smoke else len(controls()),
        exits=result,helper_source_SHA256=helpers,full_native_arena_and_log=True,effectful_modes=5,
        aligned_host_endian_memory=True,finite_arithmetic_vectors=True,trig_providers_opaque=True,
        all_five_effectful_gates_required=not smoke,no_provider_table_misses=True,unused_extern_only_removed_for_GCC=True,
        private_stack_and_unmapped_aliases_excluded=True,smoke_only=smoke)
    (out/('native32-smoke.json' if smoke else 'native32.json')).write_text(json.dumps(receipt,indent=2)+'\n');return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--smoke',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];print(json.dumps(qualify(root,root/BUILD,args.smoke),indent=2))
