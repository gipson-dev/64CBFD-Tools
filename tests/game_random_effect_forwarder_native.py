"""SDK native32 checked against independently rounded Python payload rows."""
import math
from tools.experiments import game_random_effect_forwarder_candidates as source
from tools.tests import game_random_effect_forwarder_oracle as g

def controls():
    b=source.SELECTED
    return dict(missing_draw=b.replace('    random[1] = func_150ADA20();\n',''),wrong_bias=b.replace('604.0f','600.0f'),wrong_pair=b.replace('scale[1]','PLACEHOLDER').replace('scale[0]','scale[1]').replace('PLACEHOLDER','scale[0]'),wrong_mask=b.replace('(random[0] & 3)','(random[0] & 1)'),wrong_angle=b.replace('270.0f','271.0f'),narrow_duration=b.replace('0, duration, priority','0, duration & 255, priority'),wrong_position=b.replace('position, 255','position + 1, 255'),wrong_parameter=b.replace('priority, parameter','priority, parameter ^ 1'))

def program():
    rows=[]
    for c in g.cases():
        if c.connected or any(not math.isfinite(g.floating(v))or abs(g.floating(v))>1. for v in c.floats):continue
        expected=g.reference(g.fixture(c),c);m=expected['memory'];call=expected['calls'][-1][1]
        vals=(*c.floats,*c.integers,*c.constants,g.u32(c.duration),g.u32(c.priority),g.u32(c.parameter),c.mutation,c.outcome,bool(c.owner),*expected['pair'],call[5],call[7],*(g.read(m,k)for k in g.GLOBALS),*expected['templates'],*(g.read(m,g.POSITION+4*i)for i in range(3)),m[c.owner]if c.owner else 0)
        number=lambda v:'0x%Xu'%v
        array=lambda values:'{'+','.join(map(number,values))+'}'
        rows.append('{'+','.join([array(vals[:3]),array(vals[3:5]),array(vals[5:9]),*map(number,vals[9:15]),array(vals[15:17]),*map(number,vals[17:19]),array(vals[19:23]),array(vals[23:29]),array(vals[29:32]),number(vals[32])])+'}')
    controls_map=controls();text='#include <ultra64.h>\n'+source.DECLARATION+source.SELECTED+'\n'
    for n,b in controls_map.items():
        assert b!=source.SELECTED,n;text+=b.replace(source.FUNCTION,'negative_'+n)+'\n'
    text+=r'''
f32 D_800AAABC,D_800AAAC0,D_800AAAC4,D_800AAAC8,D_800AAA90[3],D_800AAA9C[3];
typedef struct{u32 samples[3],randoms[2],constants[4],duration,priority,parameter,mutation,outcome,owner,pair[2],kind,angle,finalConstants[4],templates[6],position[3],ownerByte;}Row;
static const Row rows[]={'''+',\n'.join(rows)+r'''};
static const Row*c;static u32 stage,fi,ii,bad;static u8 ownerBytes[128],outputBytes[512];static f32 positionValues[4];
static f32 value(u32 word){union{u32 word;f32 real;}v;v.word=word;return v.real;}
static u32 bits(f32 real){union{u32 word;f32 real;}v;v.real=real;return v.word;}
static void effect(void){u32 n=stage,i;if(c->mutation&1){D_800AAABC=(n+1)*0.25f;D_800AAAC0=(n+2)*0.25f;D_800AAAC4=(n+3)*0.25f;D_800AAAC8=(n+4)*0.25f;}
 if(c->mutation&2){if(c->owner)ownerBytes[0]=(u8)(n*17);for(i=0;i<3;i++)positionValues[i]=(f32)(n*10+i);}
 if(c->mutation&4)for(i=0;i<3;i++){D_800AAA90[i]=(f32)(n+i);D_800AAA9C[i]=(f32)(n+1+i);}
}
f32 func_150ADA68(void){if(stage!=0&&stage!=1&&stage!=4)bad=1;stage++;effect();return value(c->samples[(fi++)%3]);}
s32 func_150ADA20(void){if(stage!=2&&stage!=3)bad=1;stage++;effect();return(s32)c->randoms[(ii++)%2];}
u8*func_15102B38(u8*owner,u8 mode,f32*a,f32*b,f32*pair,s16 kind,u8 color,f32 angle,f32*position,u8 alpha,s32 zero,s16 duration,u8 priority,s32 parameter){
 u32 i;if(stage++!=5||owner!=(c->owner?ownerBytes:0)||mode||a!=D_800AAA90||b!=D_800AAA9C||position!=positionValues||kind!=(s32)c->kind||color!=255||bits(angle)!=c->angle||alpha!=255||zero||duration!=(s16)c->duration||priority!=(u8)c->priority||(u32)parameter!=c->parameter)bad=1;
 for(i=0;i<2;i++)if(bits(pair[i])!=c->pair[i])bad=1;
 for(i=0;i<3;i++)if(bits(a[i])!=c->templates[i]||bits(b[i])!=c->templates[3+i]||bits(positionValues[i])!=c->position[i])bad=1;
 if(bits(D_800AAABC)!=c->finalConstants[0]||bits(D_800AAAC0)!=c->finalConstants[1]||bits(D_800AAAC4)!=c->finalConstants[2]||bits(D_800AAAC8)!=c->finalConstants[3]||(c->owner&&ownerBytes[0]!=c->ownerByte))bad=1;
 return c->outcome&&c->owner?outputBytes:0;
}
typedef u8*(*Callback)(u8*,f32*,s16,u8,s32);
static Callback callbacks[]={'''+','.join([source.FUNCTION,*['negative_'+n for n in controls_map]])+r'''};
static int run(void){u32 row,v,i,killed=0;u8*result;
 for(row=0;row<sizeof(rows)/sizeof(rows[0]);row++)for(v=0;v<9;v++){
  c=&rows[row];stage=fi=ii=bad=0;for(i=0;i<128;i++)ownerBytes[i]=(u8)(i*29+89);
  D_800AAABC=value(c->constants[0]);D_800AAAC0=value(c->constants[1]);D_800AAAC4=value(c->constants[2]);D_800AAAC8=value(c->constants[3]);
  for(i=0;i<3;i++){D_800AAA90[i]=D_800AAA9C[i]=(f32)(i+1);positionValues[i]=(f32)(10+i);}positionValues[3]=123.0f;
  result=callbacks[v](c->owner?ownerBytes:0,positionValues,(s16)c->duration,(u8)c->priority,(s32)c->parameter);
  if(bad||stage!=6||fi!=3||ii!=2||result!=(c->outcome&&c->owner?outputBytes:0)){if(!v)return 41;killed|=1u<<(v-1);}
 }return killed==255?0:42;
}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r):"memory");__builtin_unreachable();}
'''
    return text,list(controls_map),len(rows)
