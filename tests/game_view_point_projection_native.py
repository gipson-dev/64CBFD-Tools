"""Native32 body/typed caller/semantic matrix adapter in three separate units."""
from tools.experiments import game_view_point_projection as source
from tools.tests import game_view_point_projection_oracle as model


def header(before):
    owner = source.recovered_owner(before)
    end = owner.index('} ViewProjection476D0;') + len('} ViewProjection476D0;')
    start = owner.rfind('typedef struct {', 0, end)
    return '#include <ultra64.h>\n' + owner[start:end] + '''
typedef union {u32 words[768];ViewProjection476D0 views[8];} ProjectionRecords;
extern ProjectionRecords records;extern f32 matrices[8][16];extern u32 output[16];
extern s32 viewBase;extern u8 page;
#define D_800BE628 viewBase
#define D_800BE9C0 page
#define D_800D9D10 ((s32 *)&matrices[2])
#define VIEW_PROJECTIONS_476D0 ((ViewProjection476D0 *)D_800BE628)
''' + source.DECLARATION + '\n'


HELPER = '''#include <ultra64.h>
void func_150A7A00(f32 matrix[4][4],f32 x,f32 y,f32 z,f32 *ox,f32 *oy,f32 *oz,f32 *ow){
 f32 result[4];int i;
 for(i=0;i<4;i++)result[i]=(matrix[0][i]*x+matrix[1][i]*y)+(matrix[2][i]*z+matrix[3][i]);
 *ox=result[0];*oy=result[1];*oz=result[2];*ow=result[3];
}
'''


def cases():
    for memory, args in model.corpus():
        view = model.half(args[0])
        if not -1 <= view <= 3 or memory[model.PAGE] > 1:
            continue
        allowed = {model.OUTPUT + 16, model.OUTPUT + 20, model.OUTPUT + 24,
            model.VIEWS + view * 384 + 16, model.VIEWS + view * 384 + 56}
        if any(a not in allowed for a in args[4:]): continue
        expected, _ = model.reference(memory, args)
        matrix = (model.MATRICES + view * 64) & 0xFFFFFFFF
        row = model.VIEWS + view * 384
        fields = [model.read(memory, row + p) for p in (12, 16, 52, 56)]
        viewport = [model.read(memory, row + frame * 16 + p, 2) for frame in (0, 1) for p in (0x44, 0x4C)]
        patches = []
        for address in args[4:]:
            index = 768 + (address - model.OUTPUT) // 4 if model.OUTPUT <= address < model.OUTPUT + 64 else (address - (model.VIEWS - 768)) // 4
            patches.append((index, model.read(expected, address)))
        yield args, memory[model.PAGE], [model.read(memory, matrix + i * 4) for i in range(16)], fields, viewport, patches


def program(before):
    rows = []
    for args, page, matrix, fields, viewport, patches in cases():
        values = (*args, page, *matrix, *fields, *viewport)
        rows.append('{{%s},{%s}}' % (','.join('0x%Xu' % v for v in values),
            ','.join('{%d,0x%Xu}' % p for p in patches)))
    return header(before) + '''
void func_1501A764(s16,f32,f32,f32,f32*,f32*,f32*);
struct Patch{u32 index,value;};struct Case{u32 a[32];struct Patch p[3];};
static const struct Case cases[]={''' + ',\n'.join(rows) + '''};
ProjectionRecords records;f32 matrices[8][16];u32 output[16];s32 viewBase;u8 page;
static u32 initial[784];
static void die(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static f32 scalar(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static int nanword(u32 u){return (u&0x7F800000u)==0x7F800000u&&(u&0x7FFFFFu);}
static u32 word(u32 i){return i<768?records.words[i]:output[i-768];}
static f32 *pointer(u32 a){
 if(a>=0x20000u&&a<0x20040u)return (f32*)((u8*)output+a-0x20000u);
 if(a>=0x2FD00u&&a<0x30900u)return (f32*)((u8*)&records+a-0x2FD00u);
 die(29);return 0;}
static void run(void){u32 n,i,j,row,wanted,actual;const struct Case*c;
 if(sizeof(void*)!=4||sizeof(ViewProjection476D0)!=384||sizeof(Vp)!=16||
  __builtin_offsetof(ViewProjection476D0,extentX)!=12||__builtin_offsetof(ViewProjection476D0,extentY)!=16||
  __builtin_offsetof(ViewProjection476D0,originX)!=52||__builtin_offsetof(ViewProjection476D0,originY)!=56||
  __builtin_offsetof(ViewProjection476D0,viewport[0].vp.vscale[2])!=0x44||
  __builtin_offsetof(ViewProjection476D0,viewport[0].vp.vtrans[2])!=0x4C)die(29);
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];row=(u32)(2+(s16)c->a[0]);
  for(i=0;i<768;i++)records.words[i]=0xA5A5A5A5u;
  for(i=0;i<16;i++)output[i]=0xA5A5A5A5u;
  for(i=0;i<128;i++)((u32*)matrices)[i]=0xA5A5A5A5u;
  for(i=0;i<16;i++)((u32*)matrices[row])[i]=c->a[8+i];
  records.words[row*96+3]=c->a[24];records.words[row*96+4]=c->a[25];
  records.words[row*96+13]=c->a[26];records.words[row*96+14]=c->a[27];
  for(i=0;i<2;i++){records.views[row].viewport[i].vp.vscale[2]=(s16)c->a[28+i*2];
   records.views[row].viewport[i].vp.vtrans[2]=(s16)c->a[29+i*2];}
  viewBase=(s32)&records.views[2];page=(u8)c->a[7];
  for(i=0;i<784;i++)initial[i]=word(i);
  func_1501A764((s16)c->a[0],scalar(c->a[1]),scalar(c->a[2]),scalar(c->a[3]),
   pointer(c->a[4]),pointer(c->a[5]),pointer(c->a[6]));
  if(viewBase!=(s32)&records.views[2]||page!=(u8)c->a[7])die(23);
  for(i=0;i<784;i++){wanted=initial[i];for(j=0;j<3;j++)if(c->p[j].index==i)wanted=c->p[j].value;
   actual=word(i);if(actual!=wanted){
    if(!(nanword(actual)&&nanword(wanted)))die(21);
    for(j=0;j<3;j++)if(c->p[j].index==i)break;if(j==3)die(21);
   }
  }
 }}
void _start(void){run();die(0);}
'''


def controls():
    body = source.SELECTED
    return dict(wrong_matrix_stride=body.replace('(s32)view * 64', '(s32)view * 16'),
        wrong_view_record=body.replace('VIEW_PROJECTIONS_476D0[view]', 'VIEW_PROJECTIONS_476D0[view + 1]'),
        missing_reciprocal=body.replace('1.0f / reciprocalW', 'reciprocalW'),
        unsigned_depth=body.replace('(f32)VIEW_PROJECTIONS_476D0[view].viewport[D_800BE9C0].vp.vscale[2]',
            '(f32)(u16)VIEW_PROJECTIONS_476D0[view].viewport[D_800BE9C0].vp.vscale[2]'),
        wrong_depth_scale=body.replace(') * 32.0f;', ') * 16.0f;'),
        swapped_tail_outputs=body.replace('&transformedX, &transformedY, &transformedZ, &reciprocalW',
            '&transformedY, &transformedX, &transformedZ, &reciprocalW'))
