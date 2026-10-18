"""Complete route stepping with retail helpers and a bounded u16 atan provider."""
import csv
import io
import itertools
import json
import math
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_route_snap as source
from tools.experiments import game_record_progress_lap as progress
from tools.experiments import game_record_neighbor_selector as selector
from tools.tests import game_view_point_projection_oracle as base
from tools.tests.test_game_record_progress_lap import LapOracle,reference as step_reference,ANCHORS as STEP_ANCHORS
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command

put,read,STACK=base.put,base.read,base.STACK
ACTORS,RECORDS,ROUTES=0x800CC2D0,0x30000,0x60000
LOOKUP,STEP,NEIGHBOR,VECTORS,CUBIC,DERIVATIVE,ATAN,WRAP=(
    0x1508855C,0x15088A08,0x150888A8,0x15088F30,0x150497E0,0x150498A4,0x1505A630,0x15144BC8)
TABLE,ROUTE_TABLE,SCALE,COUNT_A,COUNT_B=0x800872A0,0x800D2350,0x8009DA04,0x800D2398,0x800D2399
HELPERS={LOOKUP:36,STEP:212,NEIGHBOR:88,VECTORS:83,CUBIC:49,DERIVATIVE:62,WRAP:25}
DEFAULT=(0,2,-1,0,0,0x43360B61,0)
HEADER='''#include <ultra64.h>
extern u8 *D_800872A0,*D_800D2350;
extern u8 D_800CC2D0[];
extern s8 D_8008FD90,D_800D2398,D_800D2399;
s32 func_1508855C(s32);
s32 func_15088A08(u8*,f32);
s32 func_150888A8(u8,u8,s8);
'''


class OutsideConversionDomain(Exception):pass


def signed(v,n=32):return ((v&((1<<n)-1))^(1<<(n-1)))-(1<<(n-1))
def addr(v):return v&0xFFFFFFFF
def public(m):return {a:v for a,v in m.items() if not STACK-0x400<=a<STACK+0x400}


def fixture(p=DEFAULT,alias=0,anchors=None):
    actor_id,steps,pattern,mode,angle,scale,gate=p
    a=anchors or {};sym=lambda name,value:a.get(name,value)
    actor=addr(sym('D_800CC2D0',ACTORS)+actor_id*0x32C)
    bank=RECORDS if not alias else actor+0xC-actor_id*0x84
    m={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x400)}
    for start,n in ((actor,0x32C),(bank,4*0x84),(ROUTES,4096),
            (sym('D_800E0C10',progress.BEST),16),(sym('D_800E0C18',progress.TOTAL),24)):
        m.update({addr(start+i):0xA5 for i in range(n)})
    for i in range(256):
        for j,value in enumerate((i*3-100,i*5-200,300-i*7)):put(m,ROUTES+i*16+j*2,value,2)
        for j in range(5):put(m,ROUTES+i*16+9+j,255,1)
        put(m,ROUTES+i*16+14,0,1);put(m,ROUTES+i*16+15,0,1)
    for i in range(1,64):
        put(m,ROUTES+i*16+9,128+i,1);put(m,ROUTES+i*16+10,i+1,1)
        put(m,ROUTES+(128+i)*16+14,4,1);put(m,ROUTES+(128+i)*16+15,1 if i<=steps else 0,1)
    if pattern>=0:
        for j in range(5):
            category=(pattern>>(j*2))&3
            candidate=(255,200+j,180+j,190+j)[category]
            put(m,ROUTES+16+9+j,candidate,1)
            if category:
                put(m,ROUTES+candidate*16+14,3 if category==1 else 4,1)
                put(m,ROUTES+candidate*16+15,1 if category==3 else 0,1)
    for i in range(4):
        row=addr(bank+i*0x84)
        for off,value in ((0,base.bits(-1.)),(4,base.bits(2.)),(8,base.bits(7.)),
                (0xC,base.bits(-2.5)),(0x10,base.bits(3.75)),(0x18,0),(0x1C,100),(0x20,0xA5A5A5A5)):
            put(m,row+off,value)
        put(m,row+0x24,5,2)
        for off,value in ((0x26,3),(0x27,0),(0x28,0),(0x2B,0),(0x2C,1),(0x2D,2),(0x2E,3),
                (0x2F,mode),(0x30,0),(0x31,i if gate!=3 else 0)):
            put(m,row+off,value,1)
        put(m,sym('D_800E0C10',progress.BEST)+i*2,300*(i+1),2)
        put(m,sym('D_800E0C18',progress.TOTAL)+i*4,1000*(i+1))
    globals=((TABLE,'D_800872A0',0 if gate==1 else bank,4),(ROUTE_TABLE,'D_800D2350',ROUTES,4),
        (SCALE,'D_8009DA04',scale,4),(COUNT_A,'D_800D2398',128 if gate==4 else 1,1),
        (COUNT_B,'D_800D2399',0 if gate in (2,4) else 3,1),(progress.MODE,'D_800D23A8',mode,1),
        (progress.EVENT,'D_800D2390',0xA5,1),(progress.GOAL,'D_800E0BE7',2,1),
        (progress.CLAMP,'D_800BE616',0,1),(progress.COUNT,'D_8008FD90',4,1))
    for location,name,value,n in globals:put(m,sym(name,location),value,n)
    return m,(actor,)


def spline(values,t,derivative=False):
    p0,p1,p2,p3=values;b=base.bits
    half0=base.mul(b(-.5),p0)
    c3=base.add(base.add(base.add(half0,base.mul(b(1.5),p1)),base.mul(b(-1.5),p2)),base.mul(p3,b(.5)))
    c2=base.add(base.mul(p3,b(-.5)),base.add(base.add(p0,base.mul(b(-2.5),p1)),base.add(p2,p2)))
    c1=base.add(base.mul(p2,b(.5)),half0)
    value=base.add(base.mul(base.add(base.mul(base.add(base.mul(c3,t),c2),t),c1),t),p1)
    slope=base.add(base.mul(base.add(base.mul(base.mul(c3,b(3.)),t),base.add(c2,c2)),t),c1)
    return (value,slope) if derivative else value


def reference(initial,args,angle,anchors=None):
    a=anchors or {};sym=lambda name,value:a.get(name,value);m=dict(initial);calls=[('lookup',args[0])]
    bank=read(m,sym('D_800872A0',TABLE));index=-1
    if bank:
        delta=signed(args[0]-sym('D_800CC2D0',ACTORS));actor_index=abs(delta)//0x32C*(-1 if delta<0 else 1)
        if actor_index==0:index=0
        else:
            count=signed(read(m,sym('D_800D2398',COUNT_A),1),8)+signed(read(m,sym('D_800D2399',COUNT_B),1),8)
            for i in range(1,max(1,count)):
                if signed(read(m,bank+i*0x84+0x31,1),8)==actor_index:index=i;break
    if index<0:return m,calls
    row=addr(read(m,sym('D_800872A0',TABLE))+index*0x84)
    for off in (0,4,8):put(m,row+off,base.bits(.5))
    for _ in range(65):
        routes=read(m,sym('D_800D2350',ROUTE_TABLE));node=read(m,row+0x2C,1);kind=0
        for j in range(5):
            candidate=read(m,routes+node*16+9+j,1)
            if candidate!=255 and read(m,routes+candidate*16+14,1)==4:kind=read(m,routes+candidate*16+15,1)
        if not kind:break
        calls.append(('step',row,base.bits(1.)))
        step_anchors={name:a.get(name,v) for name,v in STEP_ANCHORS.items()}
        m,_,_,nested=step_reference(m,(row,base.bits(1.)),step_anchors)
        calls.extend(('neighbor',*values) for _,values in nested)
    else:raise ValueError('Unqualified nonterminating route')
    put(m,row+8,0);calls.append(('vectors',row,(-32,-48,-64)));vectors=[[],[],[]]
    for j in range(4):
        node=read(m,row+0x2B+j,1)
        if node==255:
            point=(base.bits(float(j*64)),0,0)
        else:
            routes=read(m,sym('D_800D2350',ROUTE_TABLE));node_at=routes+node*16;chosen=node_at
            for k in range(5):
                candidate=read(m,node_at+9+k,1)
                if candidate!=255 and read(m,routes+candidate*16+14,1)==4:chosen=routes+candidate*16;break
            x=signed(read(m,node_at,2),16);z=signed(read(m,node_at+4,2),16)
            dx=signed(read(m,chosen,2),16)-x;dz=signed(read(m,chosen+4,2),16)-z
            point=(base.add(base.bits(float(x)),base.mul(base.bits(float(dx)),read(m,row))),
                base.bits(float(signed(read(m,node_at+2,2),16))),
                base.add(base.bits(float(z)),base.mul(base.bits(float(dz)),read(m,row))))
        for axis in range(3):vectors[axis].append(point[axis])
    for axis,offset in enumerate((0x14,0x18,0x1C)):
        t=read(m,row+8);values=tuple(vectors[axis]);derivative=axis!=1
        calls.append(('derivative' if derivative else 'cubic',values,0,t,*((-12 if axis==0 else -16,) if derivative else ())))
        result=spline(values,t,derivative);put(m,args[0]+offset,result[0] if derivative else result)
    calls.append(('atan',read(m,row+0x10),read(m,row+0xC),0))
    heading=base.mul(base.bits(float(angle+0x8000)),0x3BB40000);calls.append(('wrap',heading))
    while base.floating(heading)>360.:heading=base.sub(heading,base.bits(360.))
    while base.floating(heading)<0.:heading=base.add(heading,base.bits(360.))
    put(m,args[0]+0x40,heading);value=base.floating(base.mul(heading,read(m,sym('D_8009DA04',SCALE))))
    if not math.isfinite(value) or not -2147483648<=math.trunc(value)<=2147483647:raise OutsideConversionDomain((m,calls))
    rotation=math.trunc(value)-0x4000
    for off in (0x7A,0x78,0x76):put(m,args[0]+off,rotation,2)
    return m,calls


class RouteOracle(LapOracle):
    def __init__(self,words,memory,args,angle,helpers,phase=0,entry=source.ENTRY,anchors=None,connected=None):
        self.angle,self.a=angle,anchors or {};self.trace=[];self.setter_reads=[];self.setter_writes=[];self.forwarded=[]
        code=dict(connected or {});code.update(helpers)
        base.PointProjectionOracle.__init__(self,words,memory,args,[],phase,entry,code)
        self.initial_sp=STACK+phase

    def execute(self,word):
        if word>>26==17 and (word>>21)&31==16 and word&63==13:
            value=base.floating(self.f[(word>>11)&31])
            if not math.isfinite(value) or not -2147483648<=math.trunc(value)<=2147483647:raise OutsideConversionDomain((self.memory,self.calls))
            self.f[(word>>6)&31]=math.trunc(value)&0xFFFFFFFF;return
        return super().execute(word)

    def record_call(self,target):
        sym=lambda name,value:self.a.get(name,value)
        if target==source.ENTRY:self.forwarded.append(self.arguments(1));return
        if target==sym('func_1508855C',LOOKUP):value=('lookup',self.r[4])
        elif target==sym('func_15088A08',STEP):value=('step',*self.arguments(2))
        elif target==sym('func_150888A8',NEIGHBOR):value=('neighbor',*self.arguments(3))
        elif target==sym('func_15088F30',VECTORS):value=('vectors',self.r[4],tuple(v-self.initial_sp for v in self.r[5:8]))
        elif target in (sym('func_150497E0',CUBIC),sym('func_150498A4',DERIVATIVE)):
            derivative=target==sym('func_150498A4',DERIVATIVE)
            value=('derivative' if derivative else 'cubic',tuple(read(self.memory,self.r[4]+i*4) for i in range(4)),
                self.r[5],self.r[6],*((self.r[7]-self.initial_sp,) if derivative else ()))
        elif target==sym('func_1505A630',ATAN):value=('atan',self.f[12],self.f[14],self.r[6])
        elif target==sym('func_15144BC8',WRAP):value=('wrap',self.f[12])
        else:raise AssertionError('Unexpected route placement helper '+hex(target))
        self.calls.append(value)

    def hook(self,target):
        if target!=self.a.get('func_1505A630',ATAN):raise AssertionError('All non-atan helpers must execute their retail bodies')
        for j in range(4):put(self.memory,self.r[29]+j*4,0xB5000000+j)
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=self.angle


def corpus():
    for pattern,mode in itertools.product(range(1024),(0,128)):yield (0,3,pattern,mode,0x8000,0x43360B61,0)
    for actor,steps,mode,angle,gate in itertools.product(range(4),(0,1,2,7,31),(0,1,128),(0,1,0x7FFF,0x8000,0x8001,0xFFFF),range(5)):
        yield (actor,steps,-1,mode,angle,0x43360B61,gate)
    for angle,scale in itertools.product((0,1,0x7FFF,0x8000,0x8001,0xFFFF),(-1024.125,-0.,0.,1.,1024.125)):
        yield (0,2,-1,0,angle,base.bits(scale),0)


def controls():
    b=source.SELECTED
    cached=b.replace('    s32 rotation;','    f32 fraction;\n    s32 rotation;').replace(
        '        func_15088F30(record, x, y, z);','        func_15088F30(record, x, y, z);\n        fraction = *(f32 *)(record + 8);')
    start=cached.index('        fraction =')+len('        fraction = *(f32 *)(record + 8);')
    cached=cached[:start]+cached[start:].replace('*(f32 *)(record + 8)','fraction')
    return {
        'wrong-type':b.replace('neighbor * 0x10 + 0xE] == 4','neighbor * 0x10 + 0xE] == 3'),
        'scan-four':b.replace('i < 5','i < 4'),
        'first-class':b.replace('neighbor * 0x10 + 0xE] == 4','neighbor * 0x10 + 0xE] == 4 && kind == 0'),
        'single-step':b.replace('while (kind != 0)','while (0)'),
        'wrong-initial-fraction':b.replace('= 0.5f;','= 0.25f;'),
        'swapped-vectors':b.replace('func_15088F30(record, x, y, z)','func_15088F30(record, y, x, z)'),
        'wrong-angle-bias':b.replace('+ 0x8000','+ 0x4000'),
        'wrong-angle-scale':b.replace('0.0054931640625f','0.005f'),
        'missing-rotation':b.replace('        *(s16 *)(actor + 0x7A) = rotation;\n',''),
        'wrong-rotation-bias':b.replace('- 0x4000','- 0x3000'),
        'cached-fraction':cached,
    }


RECORD_FIELDS=((0,4),(4,4),(8,4),(0xC,4),(0x10,4),(0x18,4),(0x1C,4),(0x20,4),(0x24,2),
    (0x26,1),(0x27,1),(0x28,1),(0x2B,1),(0x2C,1),(0x2D,1),(0x2E,1),(0x2F,1),(0x30,1),(0x31,1))


def native_case(p):
    memory,args=fixture(p);expected,calls=reference(memory,args,p[4]);bank=RECORDS
    records=[read(expected,bank+i*0x84+off,n) for i in range(4) for off,n in RECORD_FIELDS]
    actor=[read(expected,args[0]+off,n) for off,n in ((0x14,4),(0x18,4),(0x1C,4),(0x40,4),(0x76,2),(0x78,2),(0x7A,2))]
    counts=[sum(c[0]==name for c in calls) for name in ('lookup','step','vectors','derivative','cubic','atan','wrap')]
    arrays=(p,records,actor,[read(expected,progress.BEST+i*2,2) for i in range(4)],
        [read(expected,progress.TOTAL+i*4) for i in range(4)],counts)
    return '{'+','.join('{'+','.join('0x%Xu'%(v&0xFFFFFFFF) for v in row)+'}' for row in arrays)+',0x%Xu}'%read(expected,progress.EVENT,1)


NATIVE=HEADER+r'''
typedef struct {f32 v0,v4,fraction,z,x;u8 pad14[4];s32 stamp,timer,elapsed;s16 ticks;
 s8 divisor,lap,maximum;u8 pad29[2];u8 previous,current,next,after;s8 mode,disabled,actor;u8 tail[82];} Record;
typedef struct {u8 pad0[0x14];f32 x,y,z;u8 pad20[0x20];f32 heading;u8 pad44[0x32];s16 r76,r78,r7A;u8 tail[0x2B0];} Actor;
typedef struct {s16 xyz[3];u8 reserved[3],neighbors[5],type,kind;} Route;
struct Case {u32 in[7],records[76],actor[7],best[4],total[4],calls[7],event;};
static const struct Case cases[]={ROWS};static const struct Case arithmetic=ARITHMETIC;
static Record records[4],expectedRecords[4];static Actor actors[4],expectedActor;
static Route routes[256],routeBefore[256];static u32 calls[7],error,activeActor,angleResult;
u8 *D_800872A0,*D_800D2350;u8 D_800BE616;s8 D_800D2398,D_800D2399,D_8008FD90,D_800D23A8,D_800D2390,D_800E0BE7;
s16 D_800E0C10[4];s32 D_800E0C18[4];f32 D_8009DA04;
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static void fill(void*p,u32 n){u32 i;for(i=0;i<n;i++)((u8*)p)[i]=0xA5;}
static int equal(const void*a,const void*b,u32 n){u32 i;for(i=0;i<n;i++)if(((const u8*)a)[i]!=((const u8*)b)[i])return 0;return 1;}
static void setRecord(Record*r,const u32*p){r->v0=real(p[0]);r->v4=real(p[1]);r->fraction=real(p[2]);r->z=real(p[3]);r->x=real(p[4]);
 r->stamp=(s32)p[5];r->timer=(s32)p[6];r->elapsed=(s32)p[7];r->ticks=(s16)p[8];r->divisor=(s8)p[9];
 r->lap=(s8)p[10];r->maximum=(s8)p[11];r->previous=(u8)p[12];r->current=(u8)p[13];r->next=(u8)p[14];
 r->after=(u8)p[15];r->mode=(s8)p[16];r->disabled=(s8)p[17];r->actor=(s8)p[18];}
s32 func_1508855C(s32 word){u32 i;s32 count;calls[0]++;
 if((u32)word!=(u32)&actors[activeActor])error=1;if(!D_800872A0)return -1;if(activeActor==0)return 0;
 count=D_800D2398+D_800D2399;for(i=1;(s32)i<count;i++)if(records[i].actor==(s32)activeActor)return (s32)i;return -1;}
s32 native_progress(u8*,f32);
s32 func_15088A08(u8*r,f32 d){calls[1]++;return native_progress(r,d);}
s32 func_15088F30(u8*p,f32*x,f32*y,f32*z){Record*r=(Record*)p;u32 j,k,node,id;Route*route,*chosen;f32 dx,dz,term;
 calls[2]++;for(j=0;j<4;j++){node=((u8*)r)[0x2B+j];if(node==255){x[j]=(f32)(j*64);y[j]=0.;z[j]=0.;continue;}
 route=routes+node;chosen=route;for(k=0;k<5;k++){id=route->neighbors[k];if(id!=255&&routes[id].type==4){chosen=routes+id;break;}}
 dx=(f32)((s32)chosen->xyz[0]-(s32)route->xyz[0]);dz=(f32)((s32)chosen->xyz[2]-(s32)route->xyz[2]);
 term=dx*r->v0;x[j]=(f32)route->xyz[0]+term;y[j]=(f32)route->xyz[1];term=dz*r->v0;z[j]=(f32)route->xyz[2]+term;}return 0;}
static f32 cubic(f32*p,f32 t,f32*slope){f32 half0,c3,c2,c1,value,a,b,c;
 half0=-.5f*p[0];a=1.5f*p[1];a=half0+a;b=-1.5f*p[2];a=a+b;b=p[3]*.5f;c3=a+b;
 a=-2.5f*p[1];a=p[0]+a;b=p[2]+p[2];a=a+b;b=p[3]*-.5f;c2=b+a;
 a=p[2]*.5f;c1=a+half0;a=c3*t;a=a+c2;a=a*t;a=a+c1;a=a*t;value=a+p[1];
 a=c3*3.f;a=a*t;b=c2+c2;a=a+b;a=a*t;c=a+c1;if(slope)*slope=c;return value;}
f32 func_150498A4(f32*p,s32 i,f32 t,f32*slope){calls[3]++;if(i)error=1;return cubic(p+i,t,slope);}
f32 func_150497E0(f32*p,s32 i,f32 t){calls[4]++;if(i)error=1;return cubic(p+i,t,0);}
u16 func_1505A630(f32 x,f32 z,s32 zero){calls[5]++;if(zero||x!=records[activeActor].x||z!=records[activeActor].z)error=1;return (u16)angleResult;}
f32 func_15144BC8(f32 f){calls[6]++;while(360.f<f)f-=360.f;while(f<0.f)f+=360.f;return f;}
void func_15088D58(u8*);
static int check(const struct Case*c,u32 overrideAngle,u32 exhaustive){const u32*p=c->in,*o=c->actor;u32 i,j,category,id;int status;
 f32 heading;s32 rotation;u32 initial[19]={0xBF800000u,0x40000000u,0x40E00000u,0xC0200000u,0x40700000u,0,100,0xA5A5A5A5u,5,3,0,0,0,1,2,3,0,0,0};
 activeActor=p[0];angleResult=exhaustive?overrideAngle:p[4];error=0;for(i=0;i<7;i++)calls[i]=0;
 fill(actors,sizeof(actors));fill(records,sizeof(records));fill(expectedRecords,sizeof(expectedRecords));fill(&expectedActor,sizeof(expectedActor));fill(routes,sizeof(routes));
 for(i=0;i<256;i++){routes[i].xyz[0]=(s16)((s32)i*3-100);routes[i].xyz[1]=(s16)((s32)i*5-200);routes[i].xyz[2]=(s16)(300-(s32)i*7);
 for(j=0;j<5;j++)routes[i].neighbors[j]=255;routes[i].type=routes[i].kind=0;}
 for(i=1;i<64;i++){routes[i].neighbors[0]=(u8)(128+i);routes[i].neighbors[1]=(u8)(i+1);routes[128+i].type=4;routes[128+i].kind=(u8)(i<=p[1]);}
 if((s32)p[2]>=0)for(j=0;j<5;j++){category=(p[2]>>(j*2))&3u;id=category==0?255:category==1?200+j:category==2?180+j:190+j;
 routes[1].neighbors[j]=(u8)id;if(category){routes[id].type=(u8)(category==1?3:4);routes[id].kind=(u8)(category==3);}}
 for(i=0;i<sizeof(routes);i++)((u8*)routeBefore)[i]=((u8*)routes)[i];
 for(i=0;i<4;i++){initial[16]=p[3];initial[18]=p[6]==3?0:i;setRecord(records+i,initial);setRecord(expectedRecords+i,c->records+i*19);
 D_800E0C10[i]=(s16)(300*(i+1));D_800E0C18[i]=(s32)(1000*(i+1));}
 D_800872A0=p[6]==1?0:(u8*)records;D_800D2350=(u8*)routes;D_8009DA04=real(p[5]);D_800D2398=(s8)(p[6]==4?128:1);
 D_800D2399=(s8)(p[6]==2||p[6]==4?0:3);D_800D23A8=(s8)p[3];D_800D2390=(s8)0xA5;D_800E0BE7=2;D_800BE616=0;D_8008FD90=4;
 expectedActor.x=real(o[0]);expectedActor.y=real(o[1]);expectedActor.z=real(o[2]);expectedActor.heading=real(o[3]);
 expectedActor.r76=(s16)o[4];expectedActor.r78=(s16)o[5];expectedActor.r7A=(s16)o[6];
 if(exhaustive){heading=(f32)(angleResult+32768u)*(180.f/32768.f);if(heading>360.f)heading-=360.f;
 rotation=(s32)(heading*D_8009DA04)-16384;expectedActor.heading=heading;expectedActor.r76=expectedActor.r78=expectedActor.r7A=(s16)rotation;}
 func_15088D58((u8*)&actors[activeActor]);status=23;
 if(error||!equal(records,expectedRecords,sizeof(records))||!equal(actors+activeActor,&expectedActor,sizeof(Actor))||
 !equal(routes,routeBefore,sizeof(routes)))return status;
 for(i=0;i<4;i++){if(i!=activeActor){for(j=0;j<sizeof(Actor);j++)if(((u8*)(actors+i))[j]!=0xA5)return status;}
 if((u16)D_800E0C10[i]!=c->best[i]||(u32)D_800E0C18[i]!=c->total[i])return status;}
 for(i=0;i<7;i++)if(calls[i]!=c->calls[i])return status;
 if((u8)D_800D2390!=c->event||D_800872A0!=(p[6]==1?0:(u8*)records)||D_800D2350!=(u8*)routes||
 D_800BE616||D_8008FD90!=4||D_800E0BE7!=2||(u8)D_800D23A8!=(p[3]&255u)||word(D_8009DA04)!=p[5]||
 (u8)D_800D2398!=(p[6]==4?128u:1u)||(u8)D_800D2399!=(p[6]==2||p[6]==4?0u:3u))return status;return 0;}
static int run(void){u32 i;int status;
 if(sizeof(void*)!=4||sizeof(Record)!=132||sizeof(Actor)!=0x32C||sizeof(Route)!=16||
 __builtin_offsetof(Record,previous)!=0x2B||__builtin_offsetof(Actor,r76)!=0x76)return 29;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){status=check(cases+i,0,0);if(status)return status;}
 for(i=0;i<65536;i++){status=check(&arithmetic,i,1);if(status)return status;}return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class ActorRouteSnapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD;cls.stage=source.verify(cls.root,cls.out)
        with source.historical_view(cls.root,cls.out):cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin');cls.truth=struct.unpack_from('>118I',cls.rom,source.ROM)
        cls.fixed=source.normalized(cls.words);cls.helpers={};cls.helper_bodies={}
        for entry,count in HELPERS.items():
            words=struct.unpack_from('>%dI'%count,cls.rom,entry-0x14FD2B50);cls.helper_bodies[entry]=words
            cls.helpers.update(zip(range(entry,entry+count*4,4),words))
        before=source.raw_read(cls.out/'before-01')
        for entry in (LOOKUP,STEP,NEIGHBOR,WRAP):
            count=HELPERS[entry];at=source.elf_slot_offset(before,entry,count*4)
            assert before[at:at+count*4]==cls.rom[entry-0x14FD2B50:entry-0x14FD2B50+count*4]

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,memory,args,angle,phase=0,bodies=None,entry=source.ENTRY,anchors=None,helpers=None):
        expected,calls=reference(memory,args,angle,anchors);models=[]
        for words in bodies or (self.words,self.fixed,self.truth):
            m=RouteOracle(words,memory,args,angle,helpers or self.helpers,phase,entry,anchors).run()
            self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.calls,calls)
            self.assertEqual(m.f[20:],m.saved_f)
            for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            models.append(m)
        self.assertEqual((models[1].memory,models[1].r,models[1].f,models[1].trace),
            (models[2].memory,models[2].r,models[2].f,models[2].trace))
        self.assertEqual(models[0].trace,models[2].trace);return models

    def test_01_complete_connected_route_and_placement(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['neighbors']),(118,168,3,72))
        self.assertEqual(self.fixed,list(self.truth));seen=set();count=0
        for p in corpus():
            memory,args=fixture(p);models=self.compare(memory,args,p[4],(count&1)*8);seen.update(models[0].visits);count+=1
        for steps,angle in itertools.product((0,1,2,7),(0,0x8000,0xFFFF)):
            p=(0,steps,-1,0,angle,0x43360B61,0);memory,args=fixture(p,1);self.compare(memory,args,angle);count+=1
        self.receipt('guest',three_way_cases=count,connected_retail_helper_words=sum(HELPERS.values()),
            sole_bounded_provider='u16 atan(f32,f32,s32)',target_words_visited=len({pc for pc in seen if source.ENTRY<=pc<source.ENTRY+472}),
            target_words_unvisited=[i for i in range(118) if source.ENTRY+i*4 not in seen],all1024_neighbor_categories_in_both_modes=True,
            actor_record_guest_alias=True,production_vector_and_spline_helpers_still_stubs=True,whole_gameplay_not_claimed=True)

    def test_02_native32_O2_O0_UBSan_all_angles_and_controls(self):
        rows=[native_case(p) for p in corpus()]
        harness=self.out/'native-driver.c';harness.write_text(NATIVE.replace('ROWS',','.join(rows)).replace('ARITHMETIC',native_case(DEFAULT)))
        helpers=self.out/'native-connected.c'
        owner=source.raw_read(self.out/'before-00').decode();bodies=[]
        for name in ('func_15088A08','func_150888A8'):
            lo,hi=source.function_span(owner,name);bodies.append(owner[lo:hi])
        helpers.write_text(HEADER+bodies[0].replace('s32 func_15088A08(','s32 native_progress(')+bodies[1])
        native_controls={n:b for n,b in controls().items() if n!='cached-fraction'}
        for name,opt,body,status in [('O2','-O2',source.SELECTED,0),('O0','-O0',source.SELECTED,0)]+[
                (n,'-O2',b,23) for n,b in native_controls.items()]:
            unit=self.out/('native-'+name+'.c');unit.write_text(HEADER+body);exe=unit.with_suffix('')
            c=subprocess.run([*native_command(opt),'-mstackrealign',str(unit),str(helpers),str(harness),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(c.returncode,0,c.stderr)
            self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=180).returncode,status,name)
        self.receipt('native',cases_per_profile=len(rows)+65536,all65536_atan_results=True,UBSan=True,
            connected_real_C_progress_and_selector=True,progress_counter_wrapper=True,bounded_typed_lookup_vector_spline_atan_models=True,
            native_nonalias_actor_record_route_objects=True,native_controls=len(native_controls),wrong_result_status=23)

    def test_03_guest_controls_change_public_results(self):
        cases=[(fixture(p),p[4]) for p in itertools.chain(
            ((0,3,pattern,0,0x8000,0x43360B61,0) for pattern in range(1024)),(DEFAULT,))]
        cases.extend((fixture((0,n,-1,0,a,0x43360B61,0),1),a) for n,a in itertools.product((0,2,7),(0,0x8000,0xFFFF)))
        for name,body in controls().items():
            obj,diagnostics=source.compile_owner(self.root,self.out,HEADER+body,'negative-'+name);self.assertFalse(diagnostics)
            _,functions,bindings=source.parse_object(obj);f=functions[source.FUNCTION]
            symbols={symbol:int(symbol.split('_')[1],16) for entries in bindings.values() for _,symbol in entries
                if symbol.startswith(('D_','func_')) and symbol!=source.FUNCTION}
            script=self.out/('negative-private-'+name+'.ld');elf=script.with_suffix('.elf')
            script.write_text('SECTIONS { .text 0x15200000 : { *(.text) } .rodata ALIGN(16) : { *(.rodata*) } }\n')
            subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',source.FUNCTION,
                *['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
            linked=sections(elf);words=struct.unpack_from('>%dI'%(f['size']//4),linked['.text'][1],f['value'])
            for (memory,args),angle in cases:
                expected,_=reference(memory,args,angle)
                initial=dict(memory)
                for section,(address,data) in linked.items():
                    if section.startswith(('.rodata','.data','.sdata','.lit')):initial.update({address+i:v for i,v in enumerate(data)})
                # Keep enlarged controls and their read-only pools clear of connected callees.
                m=RouteOracle(words,initial,args,angle,self.helpers,entry=0x15200000).run()
                if {a:v for a,v in public(m.memory).items() if a in memory}!=public(expected):break
            else:self.fail('Ineffective route placement control: '+name)
        self.receipt('controls',observable_guest_controls=len(controls()),native_controls=len(controls())-1,public_memory_not_private_offsets=True)

    def test_04_independent_main_and_all_seven_helper_rebases(self):
        context=type('OriginalContext',(),dict(root=self.root,out=self.out))
        original=assembly.ViewListSetupTests.original.__func__(context,'original-snap',source.raw_text(self.root/'conker/asm/B3020.s'),source.FUNCTION)
        objects={}
        for entry in HELPERS:
            name='func_%08X'%entry
            if entry==WRAP:
                emitted,missing=emit_function(struct.pack('>25I',*self.helper_bodies[entry]),dict(value=0,size=100),{},name,{})
                self.assertFalse(missing);path=self.out/'original-wrap.s';path.write_text(emitted);obj=path.with_suffix('.o')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],check=True,capture_output=True)
            else:
                asm='conker/asm/76C90.s' if entry in (CUBIC,DERIVATIVE) else 'conker/asm/B3020.s'
                obj=assembly.ViewListSetupTests.original.__func__(context,'original-helper-%X'%entry,source.raw_text(self.root/asm),name)
            objects[entry]=obj
        global_symbols=dict(STEP_ANCHORS,**{'D_800872A0':TABLE,'D_800CC2D0':ACTORS,'D_8009DA04':SCALE,
            'D_800D2398':COUNT_A,'D_800D2399':COUNT_B})
        globals_order=list(global_symbols)
        placements=[(source.ENTRY,dict(global_symbols),LOOKUP),
            (0x16218004,dict(zip(globals_order,(0x23458004,0x800A8004,0x800A7FFF,0x800E7FFF,
                0x800B8004,0x80087FFC,0x800F7FFC,0x800F8008,0x16211000,
                0x12347FFC,0x45678004,0x34567FFC,0x800D7FFF,0x800D8004))),0x16210000),
            (0x18FFF000,dict(zip(globals_order,(0x23457FFC,0x800A7FFC,0x800A8003,0x800E8003,
                0x800B7FFC,0x80088004,0x800F8004,0x800F8010,0x18FF1000,
                0x12348004,0x45677FFC,0x34568004,0x800D8003,0x800D7FFF))),0x18FF0000)]
        count=0
        for placement,(entry,anchors,helper_base) in enumerate(placements):
            if placement:
                for i,address in enumerate((*HELPERS,ATAN)):anchors['func_%08X'%address]=helper_base+i*0x800
            else:
                for address in (*HELPERS,ATAN):anchors['func_%08X'%address]=address
            linked=[];helpers={}
            for label,obj,name,pc,length in [('original',original,source.FUNCTION,entry,118),
                    ('raw',self.obj,source.FUNCTION,entry,118),('padded',self.padded,source.FUNCTION,entry,118)]+[
                    ('helper-%X'%address,obj,'func_%08X'%address,anchors['func_%08X'%address],HELPERS[address]) for address,obj in objects.items()]:
                if label!='original':
                    text,functions,rel=source.parse_object(obj);f=functions[name]
                    bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}
                    emitted,missing=emit_function(text[f['value']:f['value']+f['size']],dict(value=0,size=f['size']),bindings,name,anchors)
                    self.assertFalse(missing);path=self.out/('rebase-%s-%d.s'%(label,placement));path.write_text(emitted);obj=path.with_suffix('.o')
                    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],check=True,capture_output=True)
                script=self.out/('rebase-%s-%d.ld'%(label,placement));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%pc)
                subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',name,
                    *['--defsym=%s=0x%X'%v for v in anchors.items() if v[0]!=name],'-o',str(elf),str(obj)],check=True,capture_output=True)
                words=list(struct.unpack_from('>%dI'%length,sections(elf)['.text'][1]))
                if label.startswith('helper-'):
                    helpers.update(zip(range(pc,pc+length*4,4),words))
                    if not placement:self.assertEqual(words,list(self.helper_bodies[int(label[7:],16)]))
                else:linked.append(words)
            self.assertEqual(linked[0],linked[2]);self.assertEqual(source.normalized(linked[1]),linked[0])
            for steps,mode,actor,alias,phase in itertools.product((0,2),(0,128),(0,3),(0,1),(0,8)):
                p=(actor,steps,-1,mode,0x8000,0x43360B61,0);memory,args=fixture(p,alias,anchors)
                self.compare(memory,args,p[4],phase,(linked[1],linked[2],linked[0]),entry,anchors,helpers);count+=1
        self.receipt('rebases',independent_main_links=9,independent_helper_links=21,three_way_cases=count,
            all14_main_bindings=True,all_seven_helper_bodies_rebased=True,carry_boundaries=True)

    def test_05_fault_prefixes_and_conversion_fail_closed(self):
        states=count=0
        for steps,mode,alias in itertools.product((0,2),(0,128),(0,1)):
            p=(0,steps,-1,mode,0x8000,0x43360B61,0);memory,args=fixture(p,alias)
            full=RouteOracle(self.fixed,memory,args,p[4],self.helpers).run()
            for fault in range(full.all_accesses):
                models=[]
                for words in (self.words,self.fixed,self.truth):
                    m=RouteOracle(words,memory,args,p[4],self.helpers);m.access_fault=fault
                    with self.assertRaises(base.faults.AccessBoundary):m.run()
                    models.append(m)
                self.assertEqual((models[0].memory,models[0].trace),(models[2].memory,models[2].trace))
                self.assertEqual(base.state(models[1]),base.state(models[2]));count+=1
            states+=1
        rejected=0
        for scale in (0x7FC12345,0x7F800000,0xFF800000,base.bits(1e20),base.bits(-1e20)):
            p=(0,0,-1,0,0,scale,0);memory,args=fixture(p)
            with self.assertRaises(OutsideConversionDomain) as raised:reference(memory,args,p[4])
            expected,calls=raised.exception.args[0];models=[]
            for words in (self.words,self.fixed,self.truth):
                m=RouteOracle(words,memory,args,p[4],self.helpers)
                with self.assertRaises(OutsideConversionDomain):m.run()
                self.assertEqual((public(m.memory),m.calls),(public(expected),calls));models.append(m)
            self.assertEqual(base.state(models[1]),base.state(models[2]));rejected+=1
        self.receipt('faults',states=states,equal_public_and_stack_fault_prefixes=count,
            full_normalized_retail_state=True,raw_dead_GPR_not_claimed=True,invalid_conversions_rejected=rejected,
            hardware_FCSR_and_indefinite_integer_not_invented=True)

    def test_06_original_retained_parent_window_and_complete_parent_slot(self):
        entry=0x1507D4DC;window=struct.unpack_from('>7I',self.rom,0xAA98C);count=0
        old=source.raw_read(self.out/'before-01');offset=source.elf_slot_offset(old,0x1507D1D8,800)
        self.assertEqual(old[offset:offset+800],self.rom[0xAA688:0xAA9A8])
        for actor,steps,phase,angle,gate in itertools.product((0,3),(0,2),(0,8),(0,0x8000,0xFFFF),(0,1)):
            p=(actor,steps,-1,0,angle,0x43360B61,gate);memory,args=fixture(p);expected,calls=reference(memory,args,angle)
            for words in (self.words,self.fixed):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+472,4),words))
                m=RouteOracle(window,memory,args,angle,self.helpers,phase,entry,connected=connected)
                sp=STACK+phase;m.r[16]=args[0];m.before[29]=sp+0x48
                for off,r in ((0x1C,16),(0x20,17),(0x24,31)):put(m.memory,sp+off,m.before[r])
                m.run();self.assertEqual(m.forwarded,[args]);self.assertEqual((public(m.memory),m.calls),(public(expected),calls))
            count+=1
        self.receipt('caller',paired_original_windows=count,original_parent_bytes=800,parent_slot_exact=True,
            pointer_in_actual_JAL_delay=True,whole_parent_gameplay_not_claimed=True)

    def test_07_fail_closed_words_bindings_guards_inputs_and_installation(self):
        text,functions,rel=source.parse_object(self.obj);f=functions[source.FUNCTION];raw,bindings=source.checked_object(self.obj)
        for i in range(118):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for i in bindings:
            bad=dict(rel);bad[f['value']+i]=[]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        reader=csv.DictReader(io.StringIO(source.raw_read(self.out/'qualified-guards.csv').decode()));rows=list(reader)
        for row in source.owner_guards(raw,bindings):
            path=self.out/'bad-guard.csv';wrong=[dict(r,expected='0x%08X'%(int(r['expected'],16)^1))
                if (r['filename'],r['function'],r['offset'])==(row['filename'],row['function'],row['offset']) else r for r in rows]
            with path.open('w',newline='') as stream:
                w=csv.DictWriter(stream,fieldnames=reader.fieldnames);w.writeheader();w.writerows(wrong)
            with self.assertRaisesRegex(ValueError,source.FUNCTION):
                source.emit_padded_assembly(self.obj,self.root/'conker/asm/B3020.s',filename=source.OWNER,word_patches_path=path)
        with source.historical_view(self.root,self.out):
            read_bytes=Path.read_bytes
            for index,p in enumerate(source.INPUTS):
                for path in (self.root/p,self.out/('before-%02d'%index)):
                    with patch.object(Path,'read_bytes',lambda x:read_bytes(x)+b'\n' if x==path else read_bytes(x)):
                        with self.assertRaises(ValueError):source.freeze(self.root,self.out)
            with self.assertRaisesRegex(RuntimeError,'cannot nest'):
                with source.historical_view(self.root,self.out):pass
        self.assertEqual(source.verify(self.root,self.out),self.stage)
        if self.stage=='after':self.assertEqual(source.audit(self.root,self.out)['functions'],6057)


if __name__=='__main__':unittest.main()
