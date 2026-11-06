"""Native32 controller sampler cases, legal signed slots and effective controls."""
from tools.experiments import game_controller_axis_sampler_candidates as source
from tools.tests.test_game_row_destination_fill import START
def controls():
    body=source.SELECTED
    changes={
    'unsigned_slot':body.replace('D_800BE728[slot]','D_800BE728[(u16)slot]'),
    'wrong_decrement':body.replace('D_80084484 - 1','D_80084484 - 2'),
    'wrong_period':body.replace('D_80084484 = 5','D_80084484 = 4'),
    'unsigned_axis':body.replace('slot = pad->x','slot = (u8)pad->x'),
    'deadzone_boundary':body.replace('slot < -20 || slot > 20','slot <= -20 || slot >= 20'),
    'wrong_y':body.replace('value = pad->y','value = pad->x'),
    'skip_x_consumption':body.replace('        pad->x = 0;',''),
    'skip_y_consumption':body.replace('        pad->y = 0;',''),
    'skip_clamp':body.replace('        *x = *x < -1 ? -1 : *x > 1 ? 1 : *x;',''),
    'skip_blocked_y':body.replace('        *y = 0;\n    } else {','    } else {'),
}
    assert all(b!=body for b in changes.values())
    return changes
TEST='\nControllerAxes1503F9F0 **D_800BE728;\ns16 D_80084484;\nstatic ControllerAxes1503F9F0 input,other;\nstatic ControllerAxes1503F9F0 *backing[98304];\nstatic u32 calls;\ntypedef void (*Sampler)(s16,s16 *,s16 *);\ntypedef char pointer_is_32[sizeof(void*)==4?1:-1];\ntypedef char input_is_four[sizeof(ControllerAxes1503F9F0)==4?1:-1];\ntypedef char axes_at_two[__builtin_offsetof(ControllerAxes1503F9F0,x)==2?1:-1];\nstatic s16 clamp_axis(s32 a){if(a>=-20&&a<=20)return 0;return a<0?-1:1;}\nstatic int check(Sampler fn,u32 count,s16 slot,s32 x,s32 y,u32 alias,u32 callback){\n    s16 actual[8],expect[8],*ox,*oy;u32 i;u16 wanted;\n    for(i=0;i<8;i++)actual[i]=expect[i]=(s16)(0x5a00+i*17);\n    input.buttons=0xa55a;input.x=(s8)x;input.y=(s8)y;\n    other.buttons=0x1234;other.x=(s8)-91;other.y=(s8)93;\n    D_800BE728[slot]=&input;D_80084484=(s16)(u16)count;\n    ox=actual+2;oy=actual+(alias?2:5);\n    if(count==1){\n        expect[2]=clamp_axis(x);expect[alias?2:5]=clamp_axis(y);wanted=5;\n    }else{expect[2]=0;expect[alias?2:5]=0;wanted=(u16)(count-1);}\n    if(callback)fn(slot,ox,oy);else func_1503F9F0(slot,ox,oy);calls++;\n    if((u16)D_80084484!=wanted||input.buttons!=0xa55a)return 42;\n    if(input.x!=(count==1?0:(s8)x)||input.y!=(count==1?0:(s8)y))return 42;\n    for(i=0;i<8;i++)if(actual[i]!=expect[i])return 42;\n    D_800BE728[slot]=&other;\n    return 0;\n}\nstatic int run_cases(Sampler fn,u32 callback){\n    u32 n,x,y,i;static const s16 slots[]={-32768,-1,0,1,32767};\n    for(n=0;n<65536;n++)if(check(fn,n,slots[n%5],(s8)n,(s8)(n>>8),n&1,callback))return 42;\n    for(x=0;x<256;x++)for(y=0;y<256;y++)if(check(fn,1,slots[(x+y)%5],(s8)x,(s8)y,(x+y)&1,callback))return 42;\n    for(i=0;i<5;i++)if(check(fn,1,slots[i],127,-128,1,callback))return 42;\n    return 0;\n}\nint run(void){\n    u32 i;int result;\n    D_800BE728=backing+32768;\n    for(i=0;i<98304;i++)backing[i]=&other;\n    result=run_cases(func_1503F9F0,0);if(result)return result;\n    result=run_cases(func_1503F9F0,1);if(result)return result;\n    if(calls!=262154)return 43;\n    return 0;\n}\n'
def program(body=None):
    return '#include <ultra64.h>\n'+source.HEADERS+(source.SELECTED if body is None else body)+'\n'+TEST+'\n'+START
