"""Aligned native32 dispatcher qualification with effectful opaque providers."""
import json
from pathlib import Path
import subprocess

from tools.experiments import game_route_dispatcher_match as source
from tools.tests.test_game_projected_packet_draw import native_command

CASES=1824
PREFIX=r'''
typedef unsigned char u8;typedef signed char s8;typedef unsigned int u32;typedef int s32;
static union {u32 align;u8 b[0x80000];} data,initial,expected;
static u32 log[512][5],savedLog[512][5];
static int calls,mode;
u8 *D_800872A0;
s8 D_800D2398,D_800D23A9;
#define D_800CC2D0 (data.b+0x20000)
typedef char ABI[(sizeof(void*)==4 && sizeof(s32)==4)?1:-1];
static void copy(u8 *a,const u8 *b,u32 n){u32 i;for(i=0;i<n;i+=4)*(u32*)(a+i)=*(const u32*)(b+i);}
static int same(const u8 *a,const u8 *b,u32 n){u32 i;for(i=0;i<n;i+=4)if(*(const u32*)(a+i)!=*(const u32*)(b+i))return 0;return 1;}
static void provider(u8 *r,u8 *a,u32 id,u32 alt){
 int i=calls++;
 if(i>=512)__builtin_trap();
 log[i][0]=id;log[i][1]=(u32)r;log[i][2]=(u32)a;log[i][3]=alt;log[i][4]=(u8)D_800D23A9;
 if(i!=0)return;
 switch(mode){
 case 1:D_800D2398=0;break;case 2:D_800D2398=-1;break;case 3:D_800D2398=3;break;
 case 4:D_800872A0=data.b+0x70000;break;case 5:D_800D23A9=(s8)0x99;break;
 case 6:data.b[0x60000+132+48]=3;break;case 7:data.b[0x60000+132+49]=128;break;
 case 8:*(u32*)(D_800CC2D0+792)=0;break;case 9:D_800D2398=-128;break;
 }
}
void func_150891E8(u8*r,u8*a){provider(r,a,0,0);}
s32 func_150896EC(u8*r,u8*a,s32 m){provider(r,a,1,(u32)m);return -123;}
'''
SUFFIX=r'''
static void reference(void){
 int index=0,limit;
 D_800D23A9=0;
 if(!D_800872A0)return;
 limit=D_800D2398;
 while(index<limit){
  u8 *r=(u8*)((u32)D_800872A0+(u32)index*132u);
  s32 slot=(s8)r[49];u8 *a=(u8*)((u32)D_800CC2D0+(u32)(slot*812));int which=-1,alt=0;
  if(*(u32*)(a+792)){
   if((s8)r[48]<2){if(!r[72])which=1;else if((s8)r[73]){which=1;alt=1;}}
   else which=0;
  }
  if(which>=0){provider(r,a,(u32)which,(u32)alt);limit=D_800D2398;}
  index++;
 }
}
static void setup(int count,int state,int slot,int gate,int alternate,int null){
 u32 i,j;
 for(i=0;i<sizeof(data.b);i+=4)*(u32*)(data.b+i)=0xA5A5A5A5u;
 for(i=0;i<2;i++)for(j=0;j<128;j++){
  u8 *r=data.b+(i?0x70000:0x60000)+j*132;
  r[48]=(u8)state;r[49]=(u8)slot;r[72]=(u8)gate;r[73]=(u8)alternate;
 }
 for(j=0;j<384;j++)*(u32*)(D_800CC2D0+((s32)j-128)*812+792)=0x12345000u+j*4;
 D_800872A0=null?0:data.b+0x60000;D_800D2398=(s8)count;D_800D23A9=0x5A;calls=0;
}
static int compare(int count,int state,int slot,int gate,int alternate,int null,int mutation){
 int n,c;u32 table;s8 limit,request;
 mode=mutation;setup(count,state,slot,gate,alternate,null);copy(initial.b,data.b,sizeof(data.b));
 func_15087CC0();
 n=calls;table=(u32)D_800872A0;limit=D_800D2398;request=D_800D23A9;
 copy(expected.b,data.b,sizeof(data.b));copy((u8*)savedLog,(u8*)log,(u32)n*sizeof(log[0]));
 copy(data.b,initial.b,sizeof(data.b));calls=0;D_800872A0=null?0:data.b+0x60000;D_800D2398=(s8)count;D_800D23A9=0x5A;
 reference();c=calls;
 if(n!=c)return 21;
 if(!same((u8*)log,(u8*)savedLog,(u32)c*sizeof(log[0])))return 22;
 if((u32)D_800872A0!=table||D_800D2398!=limit||D_800D23A9!=request)return 23;
 if(!same(data.b,expected.b,sizeof(data.b)))return 24;
 return 0;
}
static int check(void){
 int i,b,m,result,total=0;
#define CASE(c,s,sl,g,a,n,mu) do{result=compare(c,s,sl,g,a,n,mu);if(result)return result;total++;}while(0)
 for(i=0;i<256;i++)CASE(i,2,0,0,0,0,0);
 for(i=0;i<256;i++)CASE(1,i,i,i&1,i>>1,0,0);
 for(i=0;i<256;i++)for(b=0;b<3;b++)CASE(1,b?1:2,i,b==2,1,0,0);
 for(i=0;i<256;i++){CASE(1,0,0,i,1,0,0);CASE(1,0,0,1,i,0,0);}
 for(m=0;m<10;m++)for(b=0;b<3;b++)CASE(m==3?1:3,b?1:2,0,b==2,1,0,m);
 for(i=0;i<2;i++)CASE(i?1:128,2,0,0,0,i,0);
 return total==NATIVE_CASES?0:25;
}
void _start(void){int result=check();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");for(;;){}}
'''


def controls():
    body=source.SELECTED
    cached=body.replace('    u8 *record;','    u8 *record;\n    u8 *cachedTable;').replace(
        '        for (i = 0;','        cachedTable = D_800872A0;\n        for (i = 0;').replace('record = D_800872A0 +','record = cachedTable +')
    count=body.replace('    s32 i;','    s32 i;\n    s32 cachedCount;').replace(
        '        for (i = 0;','        cachedCount = D_800D2398;\n        for (i = 0;').replace('i < D_800D2398','i < cachedCount')
    late=body.replace('    D_800D23A9 = 0;\n','');late=late.rsplit('}',1)[0]+'    D_800D23A9 = 0;\n}\n'
    return {
        'unsigned-slot':body.replace('*(s8 *)(record + 0x31)','*(u8 *)(record + 0x31)'),
        'unsigned-state':body.replace('*(s8 *)(record + 0x30)','*(u8 *)(record + 0x30)'),
        'unsigned-count':body.replace('i < D_800D2398','i < (u8)D_800D2398'),
        'wrong-alternate':body.replace('func_150896EC(record, actor, 1);','func_150896EC(record, actor, 0);'),
        'cached-table':cached,'cached-count':count,'late-request-clear':late,
    }


def qualify(root,out):
    source.freeze(root,out);results={}
    forms=[(name,source.SELECTED,opt,checked) for name,opt,checked in (('O0','-O0',False),('O2','-O2',False),('O2-UBSAN','-O2',True))]
    forms.extend((name,body,'-O2',True) for name,body in controls().items())
    for name,body,opt,checked in forms:
        unit=out/('native-'+name+'.c');unit.write_text('#define NATIVE_CASES %d\n'%CASES+PREFIX+body+SUFFIX)
        exe=unit.with_suffix('');command=[*native_command(opt,checked),'-fno-strict-aliasing',str(unit),'-o',str(exe)]
        p=subprocess.run(command,cwd=root,capture_output=True,text=True)
        (out/('native-'+name+'-diagnostics.txt')).write_text(p.stdout+p.stderr)
        if p.returncode or p.stdout or p.stderr:raise ValueError('Native dispatcher compile failed: '+name+'\n'+p.stdout+p.stderr)
        p=subprocess.run([str(exe)],cwd=root,capture_output=True,timeout=120);results[name]=p.returncode
        if p.stdout or p.stderr or (p.returncode!=0 if name in ('O0','O2','O2-UBSAN') else p.returncode not in (21,22,23,24)):
            raise ValueError('Native dispatcher gate failed: '+name+' exit '+str(p.returncode))
    result=dict(cases_per_profile=CASES,profiles=3,effective_controls=7,exits=results,full_aligned_host_endian_arena=True,
        opaque_provider_mutations=True,private_stack_misaligned_unmapped_aliases_excluded=True,hardware_or_other_callee_semantics_claim=False)
    (out/'native.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root,root/source.BUILD),indent=2))
