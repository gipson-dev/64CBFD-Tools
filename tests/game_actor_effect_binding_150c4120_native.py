"""Native32 sender validation with typed factories and defined-byte packet checks."""
import hashlib,json,subprocess
from tools.experiments import game_actor_effect_binding_150c4120_recovery as s
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests import game_actor_effect_binding_150c4120_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

CONTROLS={
    'lifetime-sentinel':('requestedLifetime == -1','requestedLifetime == 0'),
    'actor-selector':('binding.selector = 0x54','binding.selector = 0x55'),
    'random-width':('% 6U','% 5U'),
    'extent':('definition.extentY = 700.0f','definition.extentY = 701.0f'),
    'first-coefficient':('+ D_800A03AC','+ D_800A03B0'),
    'palette-index':('func_150ADA20() & 3','func_150ADA20() & 1'),
    'effect-flags':('| 0xC000','| 0x8000'),
    'effect-context':('func_15130280(&definition, 1, 0, sizeof(random), priority, context)','func_15130280(&definition, 1, 0, sizeof(random), priority, context ^ 1)'),
    'extra-copy':('&random, sizeof(random));','&random, sizeof(random) - 4);'),
}

def arr(values):return '{'+','.join(str(v&0xFFFFFFFF)+'U' for v in values)+'}'

def main():
    selected=body((s.OUT/'recovered.c').read_text(),s.NAME)
    code='''#include <ultra64.h>
'''+s.PREAMBLE+'''
BindingPalette150C4120 D_800A0340;
BindingVector150C4120 D_800A5480;
f32 D_800A03AC,D_800A03B0,D_800A03B4;
_Static_assert(sizeof(BindingPayload150C4120)==28 && sizeof(BindingDefinition150C4120)==112 && sizeof(BindingRandom150C4120)==16,"payload extents");
_Static_assert(__builtin_offsetof(BindingDefinition150C4120,scale)==0x24 && __builtin_offsetof(BindingDefinition150C4120,first)==0x30 && __builtin_offsetof(BindingDefinition150C4120,flags58)==0x58 && __builtin_offsetof(BindingDefinition150C4120,coefficient)==0x6c,"definition offsets");
_Static_assert(__builtin_offsetof(BindingPayload150C4120,selector)==0x14 && __builtin_offsetof(BindingRandom150C4120,scale)==4,"other offsets");
static u8 actorStorage[128] __attribute__((aligned(16)));
static u8 firstStorage[256] __attribute__((aligned(16)));
static u8 secondStorage[256] __attribute__((aligned(16)));
static u8 *actor=actorStorage+32,*first=firstStorage+32,*second=secondStorage+32;
struct Event{u32 target,count,args[9];};
struct Case{u32 seed,outcome,mutation,lifetime,priority,context,mark,count;u8 actorBefore[128],actorAfter[128],firstBefore[256],firstAfter[256],secondBefore[256],secondAfter[256],binding[28],definition[112],random[16],globals[40];struct Event calls[20];};
static const struct Case cases[]={
'''
    values=list(g.cases())
    for c in values:
        initial=g.fixture(c);final,calls,packets=g.reference(initial,c);assert len(calls)<=20
        p=dict(packets);events='{'+','.join('{'+str(t)+'U,'+str(len(a))+'U,'+arr(a)+'}' for t,a in calls)+'}'
        arrays=[arr(initial[base+i] for i in range(n)) for base,n in ((g.OWNER-32,128),(g.FIRST-32,256),(g.SECOND-32,256))]
        finals=[arr(final.get(base+i,0) for i in range(n)) for base,n in ((g.OWNER-32,128),(g.FIRST-32,256),(g.SECOND-32,256))]
        global_bytes=[final[base+i] for base,n in ((g.PALETTE,16),(g.VECTOR,12),(g.C1,12)) for i in range(n)]
        row=[str(v)+'U' for v in (c.seed,c.outcome,c.mutation,*g.args(c)[1:],g.read(final,g.MARK),len(calls))]
        row += [arrays[0],finals[0],arrays[1],finals[1],arrays[2],finals[2],arr(p.get('binding',{}).get(i,0) for i in range(28)),arr(p.get('definition',{}).get(i,0) for i in range(112)),arr(p.get('random',{}).get(i,0) for i in range(16)),arr(global_bytes),events]
        code+='{'+','.join(row)+'},\n'
    code+='''};
static const struct Case *current;static u32 index,bad,mark,counts[4];
static u32 raw(const u8*p,u32 n){u32 v=0,i;u8*q=(u8*)&v;for(i=0;i<n;i++)q[i]=p[i];return v;}
static void store(u8*p,u32 v,u32 n){u32 i;u8*q=(u8*)&v;for(i=0;i<n;i++)p[i]=q[i];}
static void be(u8*p,u32 v,u32 n){u32 i;for(i=0;i<n;i++)p[i]=(u8)(v>>(8*(n-1-i)));}
static f32 value(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}
static u32 word(f32 f){union{u32 u;f32 f;}x;x.f=f;return x.u;}
static void event(u32 t,u32 n,const u32*a){const struct Event*v;u32 i;
 if(index>=current->count){bad=1;return;}v=&current->calls[index++];if(t!=v->target||n!=v->count)bad=2;
 for(i=0;i<n;i++)if(a[i]!=v->args[i])bad=3;
}
static u32 effect(u32 t,u32 slot){u32 n=counts[slot]++,i;mark=0x13579bdfU+t+n*0x10203U;
 if(!current->mutation)return n;
 if(t==0x15167a68){actor[4]^=3;actor[0x3b]^=0x55;}
 if(t==0x150ada20 && n==0)for(i=0;i<4;i++)D_800A0340.values[i]=(s32)(0xaa00U+i);
 if(t==0x150ada68){D_800A03AC=1.25f+(f32)n;D_800A03B0=2.5f+(f32)n;}
 if(t==0x150ada20 && (n==4||n==5)){
  D_800A5480.x=(f32)(10+n);D_800A5480.y=(f32)(11+n);D_800A5480.z=(f32)(12+n);D_800A03B4=-3.5f-(f32)n;
 }return n;
}
static const u32 offsets32[]={'''+','.join(str(v) for v in g.M32)+'''};
static const u32 offsets16[]={'''+','.join(str(v) for v in g.M16)+'''};
static u32 padding(u32 n,u32 i){if(n==28)return i==5||i==6||i==7||i==23;return n==112&&(i==103||i==106||i==107);}
static void packet(u32 n,const void*source){u8 b[112];const u8*p=source,*want;u32 i;
 if(n!=28&&n!=112&&n!=16){bad=4;return;}for(i=0;i<n;i++)b[i]=p[i];
 if(n==28){if(raw(p,4)!=(u32)actor)bad=5;be(b,0x30040,4);for(i=8;i<=16;i+=4)be(b+i,raw(p+i,4),4);be(b+20,raw(p+20,2),2);be(b+24,raw(p+24,4),4);want=current->binding;}
 else if(n==112){for(i=0;i<sizeof(offsets32)/4;i++)be(b+offsets32[i],raw(p+offsets32[i],4),4);for(i=0;i<sizeof(offsets16)/4;i++)be(b+offsets16[i],raw(p+offsets16[i],2),2);want=current->definition;}
 else{for(i=4;i<16;i+=4)be(b+i,raw(p+i,4),4);want=current->random;}
 for(i=0;i<n;i++)if(!padding(n,i)&&b[i]!=want[i])bad=6;
}
static u32 guest(const void*p){if(p==first+40)return 0x50068;if(p==second+16)return 0x60050;if(p==second+168)return 0x600e8;bad=7;return 0;}
void *memcpy(void*d,const void*s,u32 n){u32 i;u8*a=d;const u8*b=s;event(0x10022ec0,3,(u32[]){guest(d),0,n});packet(n,s);for(i=0;i<n;i++)a[i]=b[i];return d;}
static u8 *allocate(u32 kind,u32 context,u32 size,u32 priority){u32 n,i;u8*p;
 event(0x15167a68,6,(u32[]){kind,context,size,1,priority,1});n=effect(0x15167a68,0);
 p=(n==0&&(current->outcome&1))?first:(n==1&&current->outcome==3)?second:0;
 if(p)for(i=0;i<size;i++)p[i]=(u8)(i*19+current->seed*7+n*23+0x31);return p;
}
u8 *func_15149130(s16 life,s8 a1,s8 a2,s8 a3,u8 active,u8 flags,s32 bytes,u8 priority,s32 context){u8*p;u32 i;
 event(0x15149130,9,(u32[]){(u32)life,(u32)a1,(u32)a2,(u32)a3,active,flags,(u32)bytes,priority,(u32)context});
 p=allocate(35,(u32)context,40+(u32)bytes,priority);if(!p)return 0;
 store(p+14,(u16)life,2);p[13]=active;p[16]=(u8)a1;p[17]=(u8)a2;p[18]=(u8)a3;p[19]=flags;
 event(0x100226f0,2,(u32[]){0x50054,16});effect(0x100226f0,1);for(i=0;i<16;i++)p[20+i]=0;return p;
}
u8 *func_15130280(BindingDefinition150C4120*d,u8 mode,void*position,s32 bytes,u8 priority,s32 context){u8*p;
 event(0x15130280,6,(u32[]){0,mode,(u32)position,(u32)bytes,priority,(u32)context});packet(112,d);
 p=allocate(82,(u32)context,168+(u32)bytes,priority);if(!p)return 0;memcpy(p+16,d,112);p[156]=0;return p;
}
s32 func_150ADA20(void){static const u32 draws[]={0,0xffffffffU,0x80000000U,5,6,255,256};u32 n;event(0x150ada20,0,(u32[]){0});n=effect(0x150ada20,2);return(s32)draws[(current->seed+n)%7];}
f32 func_150ADA68(void){static const u32 draws[]={0,0x3e800000,0x3f000000,0x3f800000,0x80000000,0x3fc00000};u32 n;event(0x150ada68,0,(u32[]){0});n=effect(0x150ada68,3);return value(draws[(current->seed+n)%6]);}
'''
    for name,text in [('selected',selected)]+[(name,selected.replace(a,b,1)) for name,(a,b) in CONTROLS.items()]:
        if name!='selected':assert text!=selected,name
        code+='\n'+text.replace(s.NAME,'test_'+name.replace('-','_'),1)+'\n'
    code+='''
typedef void(*Test)(u8*,s16,u8,s32);
static int check(Test test){u32 n,i,j,ptr;u8 b[256],globals[40];
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){
  const struct Case*c=&cases[n];current=c;index=bad=mark=0;for(i=0;i<4;i++)counts[i]=0;
  for(i=0;i<128;i++)actorStorage[i]=c->actorBefore[i];for(i=0;i<256;i++){firstStorage[i]=c->firstBefore[i];secondStorage[i]=c->secondBefore[i];}
  D_800A0340.values[0]=0;D_800A0340.values[1]=15;D_800A0340.values[2]=255;D_800A0340.values[3]=(s32)0xdeadbeefU;
  D_800A5480.x=.125f;D_800A5480.y=-2.5f;D_800A5480.z=13.25f;D_800A03AC=.5f;D_800A03B0=.75f;D_800A03B4=-.25f;
  test(actor,(s16)c->lifetime,(u8)c->priority,(s32)c->context);
  if(bad||index!=c->count||mark!=c->mark)return 1;for(i=0;i<128;i++)if(actorStorage[i]!=c->actorAfter[i])return 2;
  for(i=0;i<256;i++)b[i]=firstStorage[i];
  if(c->outcome&1){be(b+46,raw(first+14,2),2);ptr=raw(first+40,4);if(ptr!=(u32)actor)return 3;be(b+72,0x30040,4);
   for(i=8;i<=16;i+=4)be(b+72+i,raw(first+40+i,4),4);ptr=raw(first+52,4);if(ptr!=(c->outcome==3?(u32)second:0))return 4;be(b+84,c->outcome==3?0x60040:0,4);be(b+92,raw(first+60,2),2);be(b+96,raw(first+64,4),4);
  }
  for(i=0;i<256;i++)if(!((c->outcome&1)&&i>=72&&i<100&&padding(28,i-72))&&b[i]!=c->firstAfter[i])return 5;
  for(i=0;i<256;i++)b[i]=secondStorage[i];
  if(c->outcome==3){for(j=0;j<sizeof(offsets32)/4;j++)be(b+48+offsets32[j],raw(second+16+offsets32[j],4),4);for(j=0;j<sizeof(offsets16)/4;j++)be(b+48+offsets16[j],raw(second+16+offsets16[j],2),2);for(i=4;i<16;i+=4)be(b+200+i,raw(second+168+i,4),4);}
  for(i=0;i<256;i++)if(!(c->outcome==3&&i>=48&&i<160&&padding(112,i-48))&&b[i]!=c->secondAfter[i])return 6;
  for(i=0;i<4;i++)be(globals+4*i,(u32)D_800A0340.values[i],4);
  be(globals+16,word(D_800A5480.x),4);be(globals+20,word(D_800A5480.y),4);be(globals+24,word(D_800A5480.z),4);
  be(globals+28,word(D_800A03AC),4);be(globals+32,word(D_800A03B0),4);be(globals+36,word(D_800A03B4),4);for(i=0;i<40;i++)if(globals[i]!=c->globals[i])return 7;
 }return 0;
}
static int run(void){if(check(test_selected))return 1;
'''
    for i,name in enumerate(CONTROLS):code+='if(!check(test_'+name.replace('-','_')+'))return '+str(20+i)+';\n'
    code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    src=s.OUT/'native.c';src.write_text(code);profiles={}
    for opt in ('-O0','-O2','-O3'):
        exe=s.OUT/('native'+opt);p=subprocess.run(native_command(opt)+['-fno-builtin','-fno-strict-aliasing',str(src),'-o',str(exe)],cwd=s.ROOT,capture_output=True,text=True)
        assert p.returncode==0 and not p.stdout and not p.stderr,(opt,p.stdout,p.stderr)
        p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode,p.stderr)
        profiles[opt]=dict(cases=len(values),effective_controls=len(CONTROLS),UBSan=True,sha256=hashlib.sha256(exe.read_bytes()).hexdigest())
    report=dict(profiles=profiles,finite_only=True,typed_factories_modeled=True,defined_payload_bytes_compared=True,padding_bytes_uncredited=7,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),installed=False,c_match_credit=0)
    (s.OUT/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
