"""Defined SDK32 objects, real SDK macros and complete command-buffer checks."""
from pathlib import Path
import sys
from tools.experiments import game_projection_filtered_draw_15035d6c_recovery as source
ROOT=source.ROOT
import json,subprocess
from tools.tests import game_projection_filtered_draw_15035d6c_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
OUT=source.OUT

def source_parts():
    text=(OUT/'qualified-screen/selected-owner.c').read_text()
    a=text.index('typedef struct {');b=text.index('} ProjectionDisplayDescriptor61D10;',a)+len('} ProjectionDisplayDescriptor61D10;')
    begin=text.index('/* Draw matching projection');end=text.index('/* Draw queued records',begin)
    return text[a:b],text[begin:end]

def rows():
    result=[]
    for c in g.cases(native=True):
        memory,trace,cursor=g.reference(g.fixture(c),c)
        h=g.hashseq(g.read(memory,g.CURSOR+i*4)for i in range(g.GFX_WORDS))
        values=[c.seed,c.count,c.lists,c.mask,c.pattern,c.alpha,c.red,c.green,c.blue,h,cursor]
        result.append('{'+','.join('0x%Xu'%v for v in values)+'}')
    return ',\n'.join(result),len(result)

def harness(body,data):
    declaration,_=source_parts()
    text='#include <ultra64.h>\n'+declaration+r'''
static const u32 cases[][11]={ROWS};
u8 D_800C3F00;
ProjectionDrawRecord61D10 D_800C3F08[255];
Gfx D_80083140[1],D_80082FC0[1];
static ProjectionDisplayDescriptor61D10 descriptor;
static Gfx graphics[2048],targets[256];
static Gfx *lists[256];
static u8 bank[255][64];
static u32 hash(u32 h,u32 v){return(h^v)*16777619u;}
static u32 normalized(u32 v){
 if(v==(u32)D_80082FC0)return 0x80082FC0u;
 if(v==(u32)D_80083140)return 0x80083140u;
 if(v>=(u32)bank&&v<(u32)bank+sizeof(bank))return 0x80000u+v-(u32)bank;
 if(v>=(u32)targets&&v<(u32)targets+sizeof(targets))return 0x90000u+v-(u32)targets;
 return v;}
BODY
static u32 readonlyHash(void){u32 h=2166136261u,i;const u8*p;
 p=(const u8*)&descriptor;for(i=0;i<sizeof(descriptor);i++)h=hash(h,p[i]);
 p=(const u8*)D_800C3F08;for(i=0;i<sizeof(D_800C3F08);i++)h=hash(h,p[i]);
 p=(const u8*)lists;for(i=0;i<sizeof(lists);i++)h=hash(h,p[i]);return hash(h,D_800C3F00);}
static int run(void){u32 k,i,j,seed,pattern,h,before;const u32*c;Gfx*result;u8*p;
 if(sizeof(void*)!=4||sizeof(Gfx)!=8||sizeof(ProjectionDrawRecord61D10)!=12||
    sizeof(ProjectionDisplayDescriptor61D10)!=40||
    __builtin_offsetof(ProjectionDrawRecord61D10,descriptorId)!=9||
    __builtin_offsetof(ProjectionDrawRecord61D10,descriptorVariant)!=10||
    __builtin_offsetof(ProjectionDrawRecord61D10,renderMode)!=11||
    __builtin_offsetof(ProjectionDisplayDescriptor61D10,disabledLists)!=19||
    __builtin_offsetof(ProjectionDisplayDescriptor61D10,displayListCount)!=20||
    __builtin_offsetof(ProjectionDisplayDescriptor61D10,displayLists)!=36)return 10;
 for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){
  c=cases[k];seed=c[0];pattern=c[4];
  for(i=0;i<2048;i++){graphics[i].words.w0=0xA5A50000u^seed^(i*2);graphics[i].words.w1=0xA5A50000u^seed^(i*2+1);}
  p=(u8*)&descriptor;for(i=0;i<sizeof(descriptor);i++)p[i]=0xA5;
  descriptor.id=seed;descriptor.alpha=c[5];descriptor.variant=seed*3;
  descriptor.disabledLists=c[3];descriptor.displayListCount=c[2];descriptor.displayLists=lists;
  for(i=0;i<256;i++)lists[i]=targets+i;
  for(i=0;i<255;i++){
   ProjectionDrawRecord61D10*r=&D_800C3F08[i];r->matrix=bank[i];r->alpha=seed*13+i*19;
   for(j=0;j<3;j++)r->color[j]=seed+i+j+5;r->slot=seed+i+8;
   r->descriptorId=descriptor.id;r->descriptorVariant=descriptor.variant;r->renderMode=1;
   if(pattern==1)r->renderMode=0;
   else if(pattern==2)r->descriptorId^=1;
   else if(pattern==3)r->descriptorVariant^=1;
   else if(pattern==4){if(i%4==1)r->renderMode=255;else if(i%4==2)r->descriptorId^=1;else if(i%4==3)r->descriptorVariant^=1;}
  }
  D_800C3F00=c[1];before=readonlyHash();
  result=func_15035D6C(graphics,&descriptor,(s32)c[6],(s32)c[7],(s32)c[8]);
  if(result<graphics||result>graphics+2048||0x50000u+8*(u32)(result-graphics)!=c[10])return 11;
  h=2166136261u;for(i=0;i<2048;i++){h=hash(h,normalized(graphics[i].words.w0));h=hash(h,normalized(graphics[i].words.w1));}
  if(h!=c[9])return 12;if(readonlyHash()!=before)return 13;
 }return 0;}
__attribute__((force_align_arg_pointer)) void _start(void){int result=run();
 __asm__ volatile(".byte 0xcd,0x80" : : "a"(1),"b"(result) : "memory");__builtin_unreachable();}
'''
    return text.replace('ROWS',data).replace('BODY',body)

def run():
    where=OUT/'native';where.mkdir(exist_ok=True);_,body=source_parts();data,count=rows();valid=[];rejected={}
    def execute(name,text,opt):
        p=where/(name+'.c');p.write_text(harness(text,data));exe=p.with_suffix('')
        q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
        assert q.returncode==0,q.stdout+q.stderr
        return subprocess.run([str(exe)],capture_output=True,timeout=30).returncode
    for opt in('-O0','-O2','-O3'):
        code=execute(opt[1:],body,opt);assert code==0,(opt,code)
        valid.append(dict(optimization=opt,cases=count,strict_aliasing=True,UBSan=True))
    controls={'wrong-mode':body.replace('renderMode != 1','renderMode != 0'),
        'wrong-alpha':body.replace(') >> 8;',') >> 7;'),
        'wrong-shift-mask':body.replace('(list & 31)','(list & 7)'),
        'wrong-state':body.replace('gSPSegment(commands++, 8, D_80082FC0)','gSPSegment(commands++, 8, D_80083140)'),
        'wrong-cull-clear':body.replace('gSPClearGeometryMode(commands++, G_CULL_FRONT)','gSPClearGeometryMode(commands++, G_CULL_BACK)'),
        'wrong-return':body.replace('return commands;','return commands + 1;')}
    for name,text in controls.items():
        assert text!=body;code=execute(name,text,'-O2');assert code in(11,12),(name,code);rejected[name]=code
    report=dict(valid=valid,rejected=rejected,complete_native_objects=True,record_extent=255,list_extent=256,
        SDK_macros=True,native_alias_inputs_excluded=True,matching_credit=0)
    (OUT/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report
