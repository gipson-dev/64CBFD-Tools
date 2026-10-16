"""Separate-TU native32 packet tape, excluding initial indeterminate bytes."""
from tools.tests import game_random_packet_burst_oracle as guest
from tools.tests.game_table_debris_native import TYPES

PROTOTYPE = '''void func_15171200(s32,s32,f32,f32,f32,f32,f32,f32,f32,s32,s32,f32,u8,s32);'''


def declarations(owner):
    packet = owner.split('typedef struct DebrisPacket19E040 {', 1)[1].split('} DebrisPacket19E040;', 1)[0]
    return TYPES + 'typedef struct DebrisPacket19E040 {' + packet + '} DebrisPacket19E040;\n' + \
        's32 func_150ADA20(void);s32 func_1518C900(s32);void func_15168BE4(void*,u8,s32);\n'


def fixtures(rom, owner, count=512):
    rows = []
    for n in range(count):
        memory, args = guest.fixture(rom, n % 5, (0x80000000 + n * 0x1234567) & 0xFFFFFFFF,
            minimum=(0.5, 20.0, 0.0)[n % 3], maximum=(1.0, 30.0, 10.0)[n % 3])
        mode, rotation = (0, 2, 3, 4)[n // 5 % 4], n // 20 % 12
        _, packets = guest.reference(memory, args, mode, rotation)
        data = ['{' + ','.join(str(b) for b in guest.prior.initialized(p)) + '}' for p in packets]
        rows.append('{' + '{' + ','.join('0x%Xu' % a for a in args) + '},%d,%d,{' % (mode, rotation) +
            (','.join(data) if data else '{0}') + '}}')
    return declarations(owner) + r'''
_Static_assert(sizeof(void*)==4,"pointer width");
_Static_assert(sizeof(DebrisPacket19E040)==96,"packet size");
_Static_assert(__builtin_offsetof(DebrisPacket19E040,asset)==0x40,"asset");
_Static_assert(__builtin_offsetof(DebrisPacket19E040,duration)==0x59,"duration");
struct Case{u32 args[14],mode,rotation;u8 packets[4][90];};
static const struct Case cases[]={ROWS};
static const u32 randoms[12]={RANDOMS};
static const struct Case*c;static DebrisPacket19E040*retained;
static u32 draws,lookups,submits,error;
static f32 number(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
s32 func_150ADA20(void){u32 result=randoms[(draws+c->rotation)%12];draws++;
 if(retained){if(c->mode==3&&draws%12==0){retained->scale[0]=(f32)draws*0.25f;retained->scale[1]=(f32)draws*0.5f;}
 if(c->mode==4)retained->asset=(s32)(0x13570000u+draws);}return (s32)result;}
s32 func_1518C900(s32 kind){lookups++;if((u32)kind!=c->args[1]||draws!=(lookups-1)*12+3)error=20;
 return c->mode==4?0:(s32)(0xABCD0000u+lookups);}
static void append(u8*out,u32*n,u32 value){u32 j;for(j=0;j<4;j++)out[(*n)++]=(u8)(value>>(24-j*8));}
void func_15168BE4(void*p,u8 flags,s32 context){u8 out[90];u32 i,n=0,value;DebrisPacket19E040*q=p;
 if(submits>=c->args[0]||draws!=(submits+1)*12||lookups!=submits+1||flags!=(u8)c->args[12]||(u32)context!=c->args[13]){error=21;return;}
 for(i=0;i<0x44;i+=4){__builtin_memcpy(&value,(u8*)p+i,4);append(out,&n,value);}
 for(i=0x48;i<0x54;i+=4){__builtin_memcpy(&value,(u8*)p+i,4);append(out,&n,value);}
 for(i=0x54;i<0x5E;i++)out[n++]=((u8*)p)[i];
 if(n!=90)error=22;for(i=0;i<90;i++)if(out[i]!=c->packets[submits][i])error=23;
 if(c->mode==2||c->mode==3||c->mode==4){
 if(submits){for(i=0;i<4;i++)if(q->reserved44[i]!=(u8)(submits*19+0x44+i))error=24;
 for(i=0;i<2;i++)if(q->reserved5E[i]!=(u8)(submits*19+0x5E + i))error=24;}
 for(i=0;i<4;i++)q->reserved44[i]=(u8)((submits+1)*19+0x44+i);
 for(i=0;i<2;i++)q->reserved5E[i]=(u8)((submits+1)*19+0x5E + i);
 q->rotation[0]=q->coefficient[0]=(f32)(submits+1)*1.25f;q->lifetime=(s32)(submits+1)*101;q->alpha=(u8)(submits+1);}
 retained=q;submits++;}
PROTOTYPE
static void(*volatile invoke)(s32,s32,f32,f32,f32,f32,f32,f32,f32,s32,s32,f32,u8,s32)=func_15171200;
static int run(void){u32 n;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){c=&cases[n];
 draws=lookups=submits=error=0;retained=0;
 invoke((s32)c->args[0],(s32)c->args[1],number(c->args[2]),number(c->args[3]),number(c->args[4]),number(c->args[5]),
 number(c->args[6]),number(c->args[7]),number(c->args[8]),(s32)c->args[9],(s32)c->args[10],number(c->args[11]),(u8)c->args[12],(s32)c->args[13]);
 if(error)return (int)error;if(submits!=c->args[0]||lookups!=submits||draws!=submits*12)return 25;}return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''.replace('ROWS', ',\n'.join(rows)).replace('RANDOMS', ','.join('0x%Xu' % x for x in guest.RANDOMS)).replace('PROTOTYPE', PROTOTYPE)
