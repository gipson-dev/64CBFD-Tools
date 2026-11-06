"""Defined-field SDK/native32 checks; reserved descriptor bytes are not scored."""
from tools.experiments import game_five_source_effect_candidates as source
from tools.tests.test_game_row_destination_fill import START
def controls():
    b=source.SELECTED
    result={
        'skip_fifth_gate':b.replace(' && fifth && duration',' && duration'),
        'reject_negative_duration':b.replace(' && duration)', ' && duration > 0)'),
        'wrong_duration':b.replace('request.duration = duration;', 'request.duration = duration + 1;'),
        'wrong_mode':b.replace('request.mode = 0x401;', 'request.mode = 0x400;'),
        'wrong_alpha':b.replace('request.alpha = 200;', 'request.alpha = 201;'),
        'wrong_size':b.replace('8, 0, 20, channel, context','8, 0, 24, channel, context'),
        'wrong_channel':b.replace('20, channel, context','20, channel + 1, context'),
        'wrong_fifth_source':b.replace('effect->fifth = fifth;', 'effect->fifth = fourth;'),
        'skip_fourth_store':b.replace('            effect->fourth = fourth;',''),
        'skip_channel_zero':b.replace('if (effect) {', 'if (effect && channel != 0) {'),
    }
    assert all(v!=b for v in result.values());return result
TEST=r'''
typedef char pointer_is_32[sizeof(void*)==4?1:-1];
typedef char request_is_58[sizeof(EffectRequest150DB518)==0x58?1:-1];
typedef char sources_is_124[sizeof(EffectSources150DB518)==0x124?1:-1];
#define OFFSET(type,field,at) typedef char offset_##field[__builtin_offsetof(type,field)==at?1:-1]
OFFSET(EffectRequest150DB518,kind,0);OFFSET(EffectRequest150DB518,mode,2);
OFFSET(EffectRequest150DB518,duration,4);OFFSET(EffectRequest150DB518,value,8);
OFFSET(EffectRequest150DB518,flags,12);OFFSET(EffectRequest150DB518,red,16);
OFFSET(EffectRequest150DB518,green,17);OFFSET(EffectRequest150DB518,blue,18);
OFFSET(EffectRequest150DB518,alpha,19);OFFSET(EffectRequest150DB518,allocationFlags,64);
OFFSET(EffectRequest150DB518,first,68);OFFSET(EffectRequest150DB518,second,69);
typedef char sources_first[__builtin_offsetof(EffectSources150DB518,first)==0x110?1:-1];
typedef char sources_second[__builtin_offsetof(EffectSources150DB518,second)==0x114?1:-1];
typedef char sources_third[__builtin_offsetof(EffectSources150DB518,third)==0x118?1:-1];
typedef char sources_fifth[__builtin_offsetof(EffectSources150DB518,fifth)==0x11c?1:-1];
typedef char sources_fourth[__builtin_offsetof(EffectSources150DB518,fourth)==0x120?1:-1];
static struct {u32 left[4];EffectSources150DB518 record;u32 right[4];} actual,expected;
static u32 backing[32],calls,error,root_calls,current_context,current_channel,current_success;
static s16 current_duration;
void *func_1513D524(void *p,u8 kind,u8 mode,u8 first,u8 setup,u8 variant,s32 size,u8 channel,s32 context){
    EffectRequest150DB518 *r=p;calls++;
    if(kind||mode!=10||first||setup!=8||variant||size!=20||channel!=current_channel||(u32)context!=current_context)error=42;
    if(r->kind!=23||r->mode!=0x401||r->duration!=current_duration||r->value||r->flags!=0x243a||r->allocationFlags!=0x401)error=42;
    if(r->red!=200||r->green!=200||r->blue!=200||r->alpha!=200||r->first!=255||r->second!=255)error=42;
    return current_success?&actual.record:0;
}
typedef void (*Constructor)(void*,void*,void*,void*,void*,s16,u8,s32);
static int check(Constructor fn,u32 route,u32 mask,u32 duration,u32 channel,u32 context,u32 success,u32 alias){
    void *p[5];u32 i,active;u8 *a=(u8*)&actual,*b=(u8*)&expected;
    for(i=0;i<sizeof(actual);i++)a[i]=b[i]=(u8)(i*29+duration*11+mask);
    for(i=0;i<5;i++)p[i]=(mask&(1u<<i))?(alias?(void*)((u8*)&actual.record+0x110+4*i):(void*)(backing+i)):0;
    active=mask==31&&(u16)duration!=0;
    current_duration=(s16)(u16)duration;current_channel=channel;current_context=context;current_success=success;calls=error=0;
    if(active&&success){expected.record.first=p[0];expected.record.second=p[1];expected.record.third=p[2];expected.record.fifth=p[4];expected.record.fourth=p[3];}
    if(route)fn(p[0],p[1],p[2],p[3],p[4],current_duration,(u8)channel,(s32)context);
    else func_150DB518(p[0],p[1],p[2],p[3],p[4],current_duration,(u8)channel,(s32)context);
    root_calls++;if(error||calls!=active)return 42;
    for(i=0;i<sizeof(actual);i++)if(a[i]!=b[i])return 42;
    return 0;
}
int run(void){
    static const u32 durations[]={0,1,0x7fff,0x8000,0xffff,0x10000,0x12340001,0xffff8000};
    static const u32 channels[]={0,1,127,128,254,255};
    static const u32 contexts[]={0,0x7fffffff,0x80000000,0xffffffff};
    u32 route,n,m,d,ch,ctx,success,alias;
    for(route=0;route<2;route++){
        for(n=0;n<65536;n++)if(check(func_150DB518,route,31,n,n&255,contexts[n&3],n&1,n&1))return 42;
        for(m=0;m<32;m++)for(d=0;d<8;d++)for(ch=0;ch<6;ch++)for(ctx=0;ctx<4;ctx++)for(success=0;success<2;success++)for(alias=0;alias<2;alias++)
            if(check(func_150DB518,route,m,durations[d],channels[ch],contexts[ctx],success,alias))return 42;
    }
    if(root_calls!=180224)return 43;
    return 0;
}
'''
def program(body=None):return '#include <ultra64.h>\n'+source.HEADERS+(source.SELECTED if body is None else body)+'\n'+TEST+'\n'+START
