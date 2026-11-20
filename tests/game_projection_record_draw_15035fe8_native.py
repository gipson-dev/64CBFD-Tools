"""Defined complete SDK32 objects and bounded mutable draw-provider checks."""
from pathlib import Path
import sys
from tools.experiments import game_projection_record_draw_15035fe8_recovery as source
ROOT=source.ROOT
import json,subprocess
from tools.tests import game_projection_record_draw_15035fe8_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
OUT=source.OUT

def source_parts():
    text=(OUT/'qualified-screen/selected-owner.c').read_text()
    a=text.index('typedef struct {');b=text.index('} ProjectionDrawRecord61D10;',a)+len('} ProjectionDrawRecord61D10;')
    begin=text.index('/* Draw queued records');end=text.index('\ns32 func_15036148()',begin)
    return text[a:b],text[begin:end]

def rows():
    result=[]
    for c in g.cases(native=True):
        memory,trace,cursor=g.reference(g.fixture(c),c)
        h=g.hashseq([v for args,packet,count in trace for v in(*args,*packet,count)])
        values=[c.seed,c.count,c.view,c.mode,c.pattern,h,g.hashseq(g.public_values(memory)),cursor,len(trace)]
        result.append('{'+','.join('0x%Xu'%v for v in values)+'}')
    return ',\n'.join(result),len(result)

def harness(body):
    declaration,_=source_parts();data,count=rows()
    text='#include <ultra64.h>\n'+declaration+r'''
static const u32 cases[][9]={ROWS};
u8 D_800C3F00;
ProjectionDrawRecord61D10 D_800C3F08[15];
static Gfx graphics[512],other[512];
static u32 bank[16][16],otherBank[16][16];
static const u32 *current;
static u32 trace,ordinal,error;
static s32 *seenPacket;
static u32 hash(u32 h,u32 v){return(h^v)*16777619u;}
static u32 address(const void*p){u32 v=(u32)p;
 if(!p)return 0;
 if(v>=(u32)graphics&&v<(u32)graphics+sizeof(graphics))return 0x50000u+v-(u32)graphics;
 if(v>=(u32)other&&v<(u32)other+sizeof(other))return 0x60000u+v-(u32)other;
 if(v>=(u32)bank&&v<(u32)bank+sizeof(bank))return 0x70000u+v-(u32)bank;
 if(v>=(u32)otherBank&&v<(u32)otherBank+sizeof(otherBank))return 0x74000u+v-(u32)otherBank;
 error=1;return 0xDEAD0000u;}
Gfx *func_1502CCFC(Gfx *commands,s32 slot,s32 view,u8 *matrix,s32 alpha,s32 *parameters,s32 mode,s32 extra){
 u32 args[8]={address(commands),(u32)slot,(u32)view,address(matrix),(u32)alpha,0xF0010000u,(u32)mode,(u32)extra};
 u32 i;ProjectionDrawRecord61D10*r;
 if(seenPacket&&seenPacket!=parameters)error=1;seenPacket=parameters;
 for(i=0;i<8;i++)trace=hash(trace,args[i]);for(i=0;i<4;i++)trace=hash(trace,(u32)parameters[i]);trace=hash(trace,D_800C3F00);
 ordinal++;commands->words.w0=0xCD000000u|ordinal;commands->words.w1=args[1]^args[2];
 if(current[3]==1)D_800C3F00=0;
 if(current[3]==2){
  D_800C3F00=15;i=(current[0]+ordinal*3)%15;r=&D_800C3F08[i];
  r->matrix=(u8*)otherBank[i];r->alpha+=7;r->color[0]^=17;r->slot++;r->skip^=255;}
 if(current[3]==3){for(i=0;i<4;i++)parameters[i]=(s32)((current[0]^ordinal^0xB7000000u)+i);return other+ordinal*2;}
 return commands+1+(current[0]+ordinal)%3;}
BODY
static u32 checksum(void){u32 h=hash(2166136261u,D_800C3F00),i,j;
 for(i=0;i<15;i++){ProjectionDrawRecord61D10*r=&D_800C3F08[i];
  h=hash(h,address(r->matrix));h=hash(h,r->alpha);for(j=0;j<3;j++)h=hash(h,r->color[j]);
  h=hash(h,r->slot);h=hash(h,r->reserved09[0]);h=hash(h,r->reserved09[1]);h=hash(h,r->skip);}
 for(i=0;i<512;i++){h=hash(h,graphics[i].words.w0);h=hash(h,graphics[i].words.w1);}
 for(i=0;i<512;i++){h=hash(h,other[i].words.w0);h=hash(h,other[i].words.w1);}
 for(i=0;i<16;i++)for(j=0;j<16;j++)h=hash(h,bank[i][j]);
 for(i=0;i<16;i++)for(j=0;j<16;j++)h=hash(h,otherBank[i][j]);return h;}
static int run(void){u32 k,i,j,seed,pattern,value,returned;Gfx*result;
 if(sizeof(void*)!=4||sizeof(Gfx)!=8||sizeof(ProjectionDrawRecord61D10)!=12||
    __builtin_offsetof(ProjectionDrawRecord61D10,skip)!=11)return 10;
 for(k=0;k<sizeof(cases)/sizeof(cases[0]);k++){
  current=cases[k];seed=current[0];pattern=current[4];
  for(i=0;i<512;i++){
   graphics[i].words.w0=other[i].words.w0=0xA5A50000u^seed^(i*2);
   graphics[i].words.w1=other[i].words.w1=0xA5A50000u^seed^(i*2+1);}
  for(i=0;i<16;i++)for(j=0;j<16;j++)bank[i][j]=otherBank[i][j]=0xB6000000u^seed^(i*16+j);
  for(i=0;i<15;i++){ProjectionDrawRecord61D10*r=&D_800C3F08[i];r->matrix=(u8*)bank[i];r->alpha=seed*13+i*19;
   r->color[0]=seed+i*7;r->color[1]=seed*5+i*11;r->color[2]=255-i*17+seed;r->slot=i*31+seed;
   r->reserved09[0]=r->reserved09[1]=0xA5;
   value=pattern==0?0:pattern==1?255:pattern==2?((i+seed)&1):((i+seed)%5==0);r->skip=value;}
  D_800C3F00=current[1];trace=2166136261u;ordinal=error=0;seenPacket=0;
  result=func_15035FE8(graphics,(s32)current[2]);returned=address(result);
  if(error||trace!=current[5]||ordinal!=current[8]||returned!=current[7])return 11;
  if(checksum()!=current[6]||error)return 12;
 }return 0;}
'''
    return text.replace('ROWS',data).replace('BODY',body)+START,count

def run():
    where=OUT/'native';where.mkdir(exist_ok=True);_,body=source_parts();valid=[];rejected={}
    def execute(name,text,opt):
        code,count=harness(text);p=where/(name+'.c');p.write_text(code);exe=p.with_suffix('')
        q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(p),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
        assert q.returncode==0,q.stdout+q.stderr
        return subprocess.run([str(exe)],capture_output=True,timeout=30).returncode,count
    for opt in('-O0','-O2','-O3'):
        code,count=execute(opt[1:],body,opt);assert code==0,(opt,code)
        valid.append(dict(optimization=opt,cases=count,strict_aliasing=True,UBSan=True))
    controls={'reversed-skip':body.replace('record->skip == 0','record->skip != 0'),
              'wrong-color':body.replace('parameters[2] = record->color[2]','parameters[2] = record->color[1]'),
              'wrong-view':body.replace('record->slot, view, record->matrix','record->slot, 0, record->matrix'),
              'wrong-return-cursor':body.replace('return commands;','return commands + 1;')}
    for name,text in controls.items():
        assert text!=body;code,_=execute(name,text,'-O2');assert code==11,(name,code);rejected[name]=code
    report=dict(valid=valid,rejected=rejected,complete_native_objects=True,record_extent=15,helpers_are_bounded_providers=True,matching_credit=0)
    (OUT/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report
