"""Native32 semantic C qualification with real helper bodies and explicit scope."""
import json
from pathlib import Path
import subprocess

from tools.experiments import game_route_projection_call_lifetime_fit as source
from tools.experiments import game_object_command_enqueue as enqueue
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.tests.test_game_projected_packet_draw import native_command

BUILD='conker/build/game-route-projection-integration'
CASES=5*8*3*2*2*6+8*8*2+9+4+13*3*2+3+1+2+256*20
HEADER='''#include <ultra64.h>
s16 D_80087290;u8 *D_800D2350,*D_800DC2B0;u16 D_8008FDBC;s8 D_800D23A8;f32 D_8009DA08;
static u32 calls[160],callCount;
static void logCall(u32 code,u32 a,u32 b,u32 c,u32 d){
 u32 *p=calls+callCount*5; if(callCount>=32)__builtin_trap();
 p[0]=code;p[1]=a;p[2]=b;p[3]=c;p[4]=d;callCount++;
}
f32 sqrtf(f32 x){f32 result;__asm__ volatile("sqrtss %1,%0":"=x"(result):"x"(x));return result;}
'''
WRAPPERS='''
u8 func_1508907C(u8 a,u8 b,u8 c,u8 d){logCall(1,a,b,c,d);return actual_selector(a,b,c,d);}
void func_1512D560(u8 *a,s32 b,void *c){logCall(2,(u32)a,(u32)b,(u32)c,0);actual_enqueue(a,b,c);}
'''
FIXTURE=r'''
typedef union {u32 align;u8 bytes[0x14000];} Arena;
static Arena arena,wanted;static u32 wantedCalls[160],wantedCount,total;
static u8 *record,*actor,*object,*table,*queue;
static f32 rounded(f32 x){volatile f32 r=x;return r;}
static int nanbits(u32 x){return (x&0x7F800000U)==0x7F800000U&&(x&0x7FFFFFU);}
static void initialize(int state,int position,int mode,int flag,int cursor,int bank,int alias,int count,int special){
 static const f32 positions[8][3]={{10,5,10},{99,20,0},{0,-20,100},{1000,1000,1000},
  {-32768,32767,-32768},{0,0,0},{-0.0f,-0.0f,-0.0f},{25000,30,-30000}};
 static const int offsets[5]={0x54,0x4C,0x38,0x34,0x58};
 int i,j;u32 newBank;
 for(i=0;i<(int)sizeof(arena.bytes);i++)arena.bytes[i]=(u8)(i*13+7);
 actor=arena.bytes+0x800;object=arena.bytes+0x1000;table=arena.bytes+0x2000;queue=arena.bytes+0x6000;
 record=alias>=1&&alias<=5?actor-offsets[alias-1]:alias==6?table-0x4C:arena.bytes+0x100;
 if(alias==7)queue=actor+0x314;
 if(alias==8){queue=object+0x238;bank=0;cursor=0;}
 D_80087290=(s16)count;D_800D2350=table;D_800DC2B0=queue;
 D_8008FDBC=(u16)flag;D_800D23A8=(s8)mode;D_8009DA08=1e9f;
 for(i=0;i<512;i++){
  for(j=0;j<3;j++)*(s16 *)(table+i*16+j*2)=(s16)((i*37+j*19)%511-255);
  for(j=0;j<5;j++)table[i*16+9+j]=255;
  table[i*16+14]=4;table[i*16+15]=0;
 }
 for(i=0;i<3;i++){
  *(s16 *)(table+i*16)=i==1?100:0;
  *(s16 *)(table+i*16+2)=i==1?20:i==2?-20:0;
  *(s16 *)(table+i*16+4)=i==2?100:0;
  table[i*16+9]=(u8)((i+1)%3);table[i*16+10]=(u8)((i+2)%3);
  table[i*16+15]=i==0?2:3;
 }
 table[14]=5;
 if(state==2&&count>0&&count<3)table[14]=4;
 for(i=0;i<3;i++)*(f32 *)(actor+0x14+i*4)=positions[position][i];
 *(u8 **)(actor+0x318)=special==1?0:object;
 object[0x23D]=(u8)bank;record[0x30]=(u8)state;record[0x4A]=0;
 record[0x4B]=(u8)(state==2&&count<3?255:1);
 *(u32 *)(queue+bank*0xB0+0xAC)=(u32)cursor;
 if(alias==8){newBank=((u32)record>>8)&255;*(u32 *)(queue+newBank*0xB0+0xAC)=0;}
 if(special==2){
  for(i=0;i<3;i++){*(s16 *)(table+16+i*2)=(s16)(i==1?-20:-100);*(f32 *)(actor+0x14+i*4)=i==1?-19.0f:-99.0f;}
 }
 if(special==3){
  D_80087290=4;table[16+9]=2;table[16+10]=3;table[32+15]=0;table[48+15]=1;
 }
 if(special==4){
  table[14]=4;table[258*16+14]=5;table[258*16+15]=2;
  table[258*16+9]=1;table[258*16+10]=2;
 }
 callCount=0;for(i=0;i<160;i++)calls[i]=0;
}
static u8 reference_pick(u8 id,u8 excluded,u8 preferred){
 int i;u8 result=255,c;u8 *n;
 logCall(1,id,255,excluded,preferred);
 if(id>=D_80087290)return 255;
 n=D_800D2350+id*16;
 for(i=0;i<5;i++){
  c=n[9+i];if(c==255||c==excluded)continue;result=c;
  if(D_800D2350[c*16+15]==preferred)break;
 }
 return result;
}
static void reference_queue(u8 *obj,u32 command,u8 *payload){
 u8 *row;u32 index;logCall(2,(u32)obj,command,(u32)payload,0);
 row=D_800DC2B0+obj[0x23D]*176;index=*(u32 *)(row+172);*(u32 *)(row+index*8)=command;
 row=D_800DC2B0+obj[0x23D]*176;index=*(u32 *)(row+172);*(u32 *)(row+index*8+4)=(u32)payload;
 row=D_800DC2B0+obj[0x23D]*176;*(u32 *)(row+172)+=1;
 row=D_800DC2B0+obj[0x23D]*176;if(*(u32 *)(row+172)==20)*(u32 *)(row+172)=0;
}
static f32 horizontal(u8 *node,f32 *dx,f32 *dz){
 *dx=rounded(*(f32 *)(actor+20)-(f32)*(s16 *)node);
 *dz=rounded(*(f32 *)(actor+28)-(f32)*(s16 *)(node+4));
 return rounded(rounded(*dx**dx)+rounded(*dz**dz));
}
static int reference(void){
 u8 *entry=*(u8 **)(actor+0x318),*n,*currentNode,*previousNode,*payload;
 u8 current,previous,first,next,c,preferred;int i,j,mode,guard=0;
 f32 best,distance,currentDistance,dx,dz,dy,length,targetZ;
 if(!entry)return 0;preferred=(D_8008FDBC&64)?1:0;
 if(*(s8 *)(record+0x30)==2){
  for(i=0;i<D_80087290;i++){
   n=D_800D2350+i*16;
   if(n[14]!=5||n[15]!=2)continue;
   record[0x4A]=(u8)i;record[0x4B]=(u8)i;
   for(j=0;j<5;j++){
    c=n[9+j];if(c==255)continue;mode=D_800D23A8;
    if((mode==0)==(D_800D2350[c*16+15]==3))record[0x4B]=c;
   }
   i=D_80087290;
  }
  current=record[0x4B];previous=record[0x4A];first=current;best=D_8009DA08;
  do{
   if(++guard>300)return 71;
   n=D_800D2350+current*16;next=reference_pick(current,previous,preferred);
   distance=horizontal(n,&dx,&dz);
   if(distance<best){best=distance;record[0x4A]=current;record[0x4B]=next;}
   previous=current;current=next;
  }while(current!=first);
  reference_queue(*(u8 **)(actor+0x318),5,0);record[0x30]=3;
 }
 current=record[0x4B];previous=record[0x4A];
 currentNode=D_800D2350+current*16;previousNode=D_800D2350+previous*16;
 currentDistance=horizontal(currentNode,&dx,&dz);best=horizontal(previousNode,&dx,&dz);
 if(currentDistance<best){
  record[0x4A]=current;record[0x4B]=reference_pick(current,previous,preferred);
  previousNode=currentNode;horizontal(previousNode,&dx,&dz);best=currentDistance;
 }
 dy=rounded(*(f32 *)(actor+24)-(f32)*(s16 *)(previousNode+2));
 length=sqrtf(rounded(rounded(dy*dy)+best));
 dx=rounded(dx/length);dy=rounded(dy/length);dz=rounded(dz/length);
 if(length>1000.0f)length=1000.0f;
 payload=record+0x4C;*(u32 *)payload=0;
 *(f32 *)(payload+32)=*(f32 *)(actor+20);*(f32 *)(payload+36)=*(f32 *)(actor+24);*(f32 *)(payload+40)=*(f32 *)(actor+28);
 *(f32 *)(payload+20)=rounded(*(f32 *)(actor+20)-rounded(dx*length));
 *(f32 *)(payload+24)=rounded(*(f32 *)(actor+24)-rounded(dy*length));
 targetZ=rounded(*(f32 *)(actor+28)-rounded(dz*length));
 *(u32 *)(payload+4)=0;*(f32 *)(payload+48)=30;*(f32 *)(payload+52)=30;
 *(u32 *)(payload+44)=0;*(f32 *)(payload+28)=targetZ;
 reference_queue(*(u8 **)(actor+0x318),7,payload);
 *(f32 *)(entry+0x19C)=30;*(f32 *)(entry+0x1A4)=30;*(f32 *)(entry+0x1A0)=30;*(f32 *)(entry+0x1A8)=30;
 return 0;
}
static int compare(int state,int position,int mode,int flag,int cursor,int bank,int alias,int count,int special,int axis,u32 encoding){
 int i,j,allowed,result;u32 at,offset;
 initialize(state,position,mode,flag,cursor,bank,alias,count,special);
 if(axis>=0)*(u32 *)(actor+20+axis*4)=encoding;
 result=reference();if(result)return result;
 for(i=0;i<(int)sizeof(arena.bytes);i++)wanted.bytes[i]=arena.bytes[i];
 for(i=0;i<160;i++)wantedCalls[i]=calls[i];wantedCount=callCount;
 initialize(state,position,mode,flag,cursor,bank,alias,count,special);
 if(axis>=0)*(u32 *)(actor+20+axis*4)=encoding;
 func_150891E8(record,actor);
 if(callCount!=wantedCount)return 22;
 for(i=0;i<160;i++)if(wantedCalls[i]!=calls[i])return 23;
 for(i=0;i<(int)sizeof(arena.bytes);i++)if(wanted.bytes[i]!=arena.bytes[i]){
  allowed=0;offset=(u32)(record-arena.bytes);
  for(j=0;j<3;j++){
   at=offset+0x60+j*4;
   if((u32)i>=at&&(u32)i<at+4&&nanbits(*(u32 *)(wanted.bytes+at))&&nanbits(*(u32 *)(arena.bytes+at)))allowed=1;
  }
  if(!allowed)return 21;
 }
 total++;return 0;
}
static int run(void){
 static const int states[5]={2,3,0,128,255},modes[3]={0,1,-128},banks[6]={0,1,127,128,254,255};
 static const int counts[9]={-32768,-1,0,1,2,3,255,256,32767};
 static const u32 special[13]={0,0x80000000U,1,0x80000001U,0x7FFFFFU,0x800000U,0x7F7FFFFFU,
  0x7F800000U,0xFF800000U,0x7FC12345U,0xFFC12345U,0x7FA45678U,0xFFA45678U};
 int s,p,m,f,c,b,a,k,r;
 if(sizeof(void *)!=4||sizeof(f32)!=4)return 70;
 for(s=0;s<5;s++)for(p=0;p<8;p++)for(m=0;m<3;m++)for(f=0;f<2;f++)for(c=0;c<2;c++)for(b=0;b<6;b++){
  r=compare(states[s],p,modes[m],f*64,c*19,banks[b],0,3,0,-1,0);if(r)return r;
 }
 for(a=1;a<=8;a++)for(p=0;p<8;p++)for(f=0;f<2;f++){
  r=compare(3,p,0,f*64,0,0,a,3,0,-1,0);if(r)return r;
 }
 for(c=0;c<9;c++){r=compare(2,0,0,0,0,0,0,counts[c],0,-1,0);if(r)return r;}
 for(s=0;s<4;s++){r=compare(states[s],0,0,0,0,0,0,3,1,-1,0);if(r)return r;}
 for(k=0;k<13;k++)for(a=0;a<3;a++)for(s=0;s<2;s++){
  r=compare(s?3:2,0,0,0,0,0,0,3,0,a,special[k]);if(r)return r;
 }
 for(m=0;m<3;m++){r=compare(2,0,modes[m],0,0,0,0,300,4,-1,0);if(r)return r;}
 r=compare(3,1,0,0,0,0,0,3,2,-1,0);if(r)return r;
 for(f=0;f<2;f++){r=compare(3,1,0,f*64,0,0,0,3,3,-1,0);if(r)return r;}
 for(b=0;b<256;b++)for(c=0;c<20;c++){r=compare(3,1,0,64,c,b,0,3,0,-1,0);if(r)return r;}
 return total==NATIVE_CASES?0:72;
}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''


def translation_unit(root,body=source.SELECTED):
    owner=(root/'conker/src/game/generated_B3020.c').read_text()
    lo,hi=function_span(owner,'func_1508907C');selector=owner[lo:hi]
    return HEADER+'\n#define NATIVE_CASES %d\n'%CASES+'\n#define func_1508907C actual_selector\n'+selector+'\n#undef func_1508907C\n'+\
        '\n#define func_1512D560 actual_enqueue\n'+enqueue.SELECTED+'\n#undef func_1512D560\n'+WRAPPERS+body+FIXTURE


def controls():
    body=source.SELECTED
    clamp='''        if (best > 1000.0f) {
            best = 1000.0f;
        }
'''
    cached=body.replace('    f32 targetZ;','    f32 targetZ;\n    f32 cachedX,cachedY,cachedZ;')
    head,tail=cached.split('        payload = record + 0x4C;',1)
    head+='''        cachedX=*(f32 *)(actor+0x14);cachedY=*(f32 *)(actor+0x18);cachedZ=*(f32 *)(actor+0x1C);
        payload = record + 0x4C;'''
    for axis,offset in zip('XYZ',('14','18','1C')):tail=tail.replace('*(f32 *)(actor + 0x'+offset+')','cached'+axis)
    fresh=body
    for offset in ('19C','1A4','1A0','1A8'):fresh=fresh.replace('(object + 0x'+offset+')','(*(u8 **)(actor + 0x318) + 0x'+offset+')')
    fresh=fresh.replace('    u8 *object;\n','').replace('        object = (u8 *)(u32)i;\n','')
    return {
        'wrong-command':body.replace('), 7, payload);','), 6, payload);'),
        'wrong-preference':body.replace('D_8008FDBC & 0x40','D_8008FDBC & 0x80'),
        'unsigned-coordinates':body.replace('s16 x, y, z;','u16 x, y, z;'),
        'clamp-before-normalize':body.replace(clamp,'').replace('        dx /= best;',clamp+'        dx /= best;'),
        'cached-payload-coordinates':head+tail,
        'reload-entry-object':fresh,
    }


def qualify(root,out):
    source.prior.freeze(root,out);results={}
    bodies=[(name,source.SELECTED,opt,checked) for name,opt,checked in (('O0','-O0',False),('O2','-O2',False),('O2-UBSAN','-O2',True))]
    bodies.extend((name,body,'-O2',True) for name,body in controls().items())
    for name,body,opt,checked in bodies:
        unit=out/('native-'+name+'.c');unit.write_text(translation_unit(root,body));exe=unit.with_suffix('')
        command=[*native_command(opt,checked),'-mstackrealign','-fno-strict-aliasing',str(unit),'-o',str(exe)]
        p=subprocess.run(command,cwd=root,capture_output=True,text=True)
        (out/('native-'+name+'-diagnostics.txt')).write_text(p.stdout+p.stderr)
        if p.returncode or p.stdout or p.stderr:raise ValueError('Native compile failed: '+name+'\n'+p.stdout+p.stderr)
        p=subprocess.run([str(exe)],cwd=root,capture_output=True,timeout=120);results[name]=p.returncode
        if p.stdout or p.stderr or (p.returncode!=0 if name in ('O0','O2','O2-UBSAN') else p.returncode not in (21,22,23)):
            raise ValueError('Native semantic/control gate failed: '+name+' exit '+str(p.returncode))
    result=dict(cases_per_positive_build=CASES,profiles=['O0','O2','O2+UBSAN'],effective_controls=6,exits=results,
        actual_parent_and_helper_C=True,full_native_arena_and_call_log=True,host_endian_aligned_memory=True,
        arithmetic_NaNs_compared_by_class=True,guest_private_stack_misaligned_and_unmapped_aliases_excluded=True,
        guest_hardware_or_FP_status_claim=False)
    (out/'native32.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];out=root/BUILD
    print(json.dumps(qualify(root,out),indent=2))
