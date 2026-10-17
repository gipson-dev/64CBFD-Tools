"""Actual SDK and five C callers on the defined native32 conversion domain."""
from tools.experiments import game_color_overlay_draw as source
from tools.tests import game_color_overlay_draw_oracle as model

VIEW_START,VIEW_BYTES=model.VIEWS-64,4*0x180+128
OUT_START,OUT_BYTES=model.OUTPUT-32,128
HEADER='''#include <ultra64.h>
extern u8 *D_800BE628;
struct ColorBank{u32 pre;u8 bytes[0xB0];u32 post;};extern struct ColorBank colors;
#define D_800DDD90 (colors.bytes)
#define D_800DDD9C (colors.bytes+0xC)
#define D_800DDDA0 (colors.bytes+0x10)
#define D_800DDDAC ((s8*)(colors.bytes+0x1C))
#define D_800DDDB0 ((s32*)(colors.bytes+0x20))
#define D_800DDDC0 (colors.bytes+0x30)
#define D_800DDE10 ((u16*)(colors.bytes+0x80))
#define D_800DDE28 ((s32*)(colors.bytes+0x98))
Gfx *func_1517F08C(Gfx*,s32,s32,s32,s32,s32);
s32 func_1517EF00(s32);s32 func_1517F3A0(s32,s32);s32 func_1517F4D8(s32,s32);
s32 func_15182768(s32,u8*,s16);s32 func_1510448C(s32,u8*,s16);s32 func_150D22F4(s32,u8*,s16);
'''


def controls(body):
    cached=body.replace('''    gDPFillRectangle(commands++,
        (u32)OVERLAY_VIEWS_1AC2F0[channel].left,
        (u32)OVERLAY_VIEWS_1AC2F0[channel].top,
        (u32)OVERLAY_VIEWS_1AC2F0[channel].right,
        (u32)OVERLAY_VIEWS_1AC2F0[channel].bottom);''','    gDPFillRectangle(commands++, left, top, right, bottom);')
    cached=cached.replace('    gDPPipeSync(commands++);',
        '\n'.join('    u32 %s = (u32)OVERLAY_VIEWS_1AC2F0[channel].%s;'%(n,n) for n in ('left','top','right','bottom'))+'\n    gDPPipeSync(commands++);',1)
    return dict(zero_alpha_gate=body.replace('    gDPPipeSync','    if (alpha == 0) return commands;\n    gDPPipeSync',1),
        wrong_coverage=body.replace('G_ZS_PRIM | CVG_DST_SAVE','G_ZS_PRIM | CVG_DST_FULL'),
        swapped_color=body.replace('0, 0, red, green, blue, alpha','0, 0, blue, green, red, alpha'),
        swapped_bounds=body.replace('.left,','.temporary,').replace('.top,','.left,').replace('.temporary,','.top,'),
        wrong_channel=body.replace('OVERLAY_VIEWS_1AC2F0[channel]','OVERLAY_VIEWS_1AC2F0[0]'),
        wrong_return=body.replace('return commands;','return commands - 1;'),
        cached_bounds=cached,missing_sync=body.replace('gDPPipeSync(commands++);','commands++;'))


def cursor_supported(cursor):
    return cursor%8==0 and (OUT_START<=cursor<=OUT_START+OUT_BYTES-40 or VIEW_START<=cursor<=VIEW_START+VIEW_BYTES-40)


def cases():
    for memory,args,phase in model.cases():
        if phase or args[5]>=4 or not cursor_supported(args[0]):continue
        expected,result,valid,_=model.reference(memory,args,phase)
        if valid and model.read(expected,model.BASE)==model.VIEWS:yield 0,memory,args,expected,result
    for kind in range(5):
        for channel in range(4):
            for variant in range(6):
                for coords in (0,2,4,7):
                    memory,args=model.caller_fixture(kind,channel,variant,coords)
                    expected,result,calls,packet=model.caller_reference(memory,args,kind)
                    if packet and not model.reference(memory,packet)[2]:continue
                    yield kind+1,memory,(*args,*([0]*(6-len(args)))),expected,result


def words(memory,start,size):
    return [sum(memory.get(start+i+j,0xA5)<<(24-8*j) for j in range(4)) for i in range(0,size,4)]


def program():
    data=[];colors=[];packets=[];rows=[]
    for kind,memory,args,expected,result in cases():
        at=len(data);ci=len(colors);pi=len(packets)
        for image in (memory,expected):
            data.extend(words(image,VIEW_START,VIEW_BYTES));data.extend(words(image,OUT_START,OUT_BYTES))
        colors.extend(memory.get(model.progress.BASE+i,0xA5) for i in range(model.progress.LENGTH))
        packets.extend(memory.get(model.PACKET+i,0xA5) for i in range(128))
        tail=((result-args[0])&0xFFFFFFFF,at,ci,pi)
        rows.append('{%d,{%s},%s}'%(kind,','.join('0x%Xu'%x for x in args),','.join('0x%Xu'%x for x in tail)))
    return HEADER+'''
u8 *D_800BE628;struct ColorBank colors;static struct ColorBank saved_colors;
static u32 views[416] __attribute__((aligned(8))),wanted_views[416];
static u32 output[32] __attribute__((aligned(8))),wanted_output[32];
static u8 packet[144],saved_packet[144];
struct Case{u32 kind,args[6],delta,at,colors,packet;};
'''+ 'static const u32 data[]={'+','.join('0x%Xu'%x for x in data)+'};\n'+ \
        'static const u8 color_data[]={'+','.join(map(str,colors))+'};\n'+ \
        'static const u8 packet_data[]={'+','.join(map(str,packets))+'};\n'+ \
        'static const struct Case cases[]={'+','.join(rows)+'};\n'+HARNESS


HARNESS=r'''
static __attribute__((noreturn)) void die(u32 code){__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
static void fill(void*p,u32 n){u32 i;for(i=0;i<n;i++)((u8*)p)[i]=0xA5;}
static void copy(void*d,const void*s,u32 n){u32 i;for(i=0;i<n;i++)((u8*)d)[i]=((const u8*)s)[i];}
static u32 big(const u8*p){return ((u32)p[0]<<24)|((u32)p[1]<<16)|((u32)p[2]<<8)|p[3];}
static void color_lanes(const u8*p){u32 k,i,at;
 for(k=0;k<2;k++)for(i=0;i<4;i++){at=(k?0x98:0x20)+i*4;*(u32*)(colors.bytes+at)=big(p+at);}
 for(i=0;i<4;i++){at=0x80+i*2;*(u16*)(colors.bytes+at)=(u16)((p[at]<<8)|p[at+1]);}
}
void _start(void){u32 n,i,value;const struct Case*c;Gfx*cursor;const u8*a,*b;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  c=&cases[n];copy(views,data+c->at,1664);copy(output,data+c->at+416,128);
  copy(wanted_views,data+c->at+448,1664);copy(wanted_output,data+c->at+864,128);
  D_800BE628=(u8*)views+64;
  cursor=(Gfx*)(c->args[0]>=0x2FFC0&&c->args[0]<0x30640?((u8*)views+(c->args[0]-0x2FFC0)):((u8*)output+(c->args[0]-0x20000)));
  fill(&colors,sizeof(colors));copy(colors.bytes,color_data+c->colors,0xB0);color_lanes(color_data+c->colors);copy(&saved_colors,&colors,sizeof(colors));
  fill(packet,sizeof(packet));copy(packet+8,packet_data+c->packet,128);copy(saved_packet,packet,sizeof(packet));
  if(c->kind==0)value=(u32)func_1517F08C(cursor,(s32)c->args[1],(s32)c->args[2],(s32)c->args[3],(s32)c->args[4],(s32)c->args[5]);
  else if(c->kind==1)value=(u32)func_1517F3A0((s32)cursor,(s32)c->args[1]);
  else if(c->kind==2)value=(u32)func_1517F4D8((s32)cursor,(s32)c->args[1]);
  else if(c->kind==3)value=(u32)func_15182768((s32)cursor,packet+8,(s16)c->args[2]);
  else if(c->kind==4)value=(u32)func_1510448C((s32)cursor,packet+8,(s16)c->args[2]);
  else value=(u32)func_150D22F4((s32)cursor,packet+8,(s16)c->args[2]);
  if(value!=(u32)cursor+c->delta)die(22);
  for(i=0;i<416;i++)if(views[i]!=wanted_views[i])die(22);
  for(i=0;i<32;i++)if(output[i]!=wanted_output[i])die(22);
  if(D_800BE628!=(u8*)views+64)die(22);
  a=(const u8*)&colors;b=(const u8*)&saved_colors;for(i=0;i<sizeof(colors);i++)if(a[i]!=b[i])die(22);
  for(i=0;i<sizeof(packet);i++)if(packet[i]!=saved_packet[i])die(22);
 }
 die(0);
}
'''
