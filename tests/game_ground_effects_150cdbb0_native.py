"""Native finite-domain actor/query tests and negative controls."""
import itertools
import subprocess
from tools.experiments import game_ground_effects_150cdbb0_match as packet
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests import game_ground_effects_150cdbb0_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def run(state):
    root=packet.ROOT;out=packet.OUT
    source=packet.MANIFEST['selected_source'];fn=body(source,packet.NAME)
    controls={'null_gate':('actor != NULL','actor != NULL && flags == 0'),
              'height_start':('+ 1000.0f','+ 999.0f'), 'height_threshold':('- D_800A07B0','+ D_800A07B0'),
              'ground_result':('point[1] = result.height','point[1] = result.height + 1.0f'),
              'first_size':('251.0f','250.0f'), 'second_size':('290.0f','289.0f'),
              'first_random':('(random & 15U) + 35','(random & 15U) + 36'),
              'second_random':('(random % 21U) + 30','(random % 20U) + 30'),
              'first_kind':('0x17, 0, 0.0f','0x16, 0, 0.0f'), 'second_kind':('0x18, 0, 0.0f','0x19, 0, 0.0f')}
    cases=[]
    for present,flags,hit,mutation,randoms in itertools.product((0,1),(0,1,127,128,255),(0,1),(0,1,2,3,4,7),((0,0),(15,20),(0xffffffff,0xffffffff))):
        c=g.Case(g.ACTOR if present else 0,flags,0x87654321,0,hit,mutation,randoms);_,calls=g.reference(g.fixture(c),c)
        query=next((x for x in calls if x[0]==g.QUERY),None);effects=[list(x[1])for x in calls if x[0]==g.EFFECT]
        for e in effects:e[-1]=flags
        threshold=query[1][2]if query else 0;point=list(query[2])if query else [0]*3
        while len(effects)<2:effects.append([0]*12)
        cases.append((present,flags,hit,mutation,*randoms,threshold,*point,len([x for x in calls if x[0]==g.INIT]),len([x for x in calls if x[0]==g.QUERY]),len([x for x in calls if x[0]==g.RNG]),sum(x[0]==g.EFFECT for x in calls),*effects[0],*effects[1]))
    head=source[:source.index('void func_150CDBB0(')];text=head+fn.replace('func_150CDBB0(','selected(',1)+'\n'
    for key,(a,b) in controls.items():
        assert fn.count(a)==1,(key,a)
        text+=fn.replace('func_150CDBB0(','bad_'+key+'(',1).replace(a,b,1)+'\n'
    rows=',\n'.join('{'+','.join(str(x)+'u'for x in row)+'}'for row in cases)
    text+='''\nstatic const u32 rows[][38]={\n'''+rows+'''\n};
    typedef union {u32 u; f32 f;} Word;
    static u8 actor_data[64] __attribute__((aligned(16)));
    static const u32 *cur; static u32 ninit,nquery,nrng,neffect,broken,q[4],got[2][12]; static f32 *query_point;
    f32 D_800A07B0;
    static u32 fb(f32 x){Word w;w.f=x;return w.u;}
    static void stage(u32 n){if(cur[3]&4){query_point[0]=(f32)(30+n);query_point[2]=(f32)(-30-(s32)n);}}
    void func_1504715C(GroundResult150CDBB0 *out,void *p){(void)out;ninit++;if(p!=actor_data)broken=1;if(cur[3]&1){*(f32*)(actor_data+0x14)=7.0f;*(f32*)(actor_data+0x18)=-3.0f;*(f32*)(actor_data+0x1C)=11.0f;D_800A07B0=75.0f;}}
    s32 func_15046C80(f32 *p,u16 selector,f32 threshold,GroundResult150CDBB0 *r){nquery++;if(selector)broken=1;query_point=p;q[0]=fb(threshold);q[1]=fb(p[0]);q[2]=fb(p[1]);q[3]=fb(p[2]);r->height=12.5f;if(cur[3]&2){p[0]=21.0f;p[2]=-19.0f;}return (s32)cur[2];}
    u32 func_150ADA20(void){u32 v=cur[4+nrng];stage(2+2*nrng);nrng++;return v;}
    void func_1514C678(f32 a,f32 b,f32 c,f32 d,s16 e,s16 f,s16 h,u8 i,s32 j,f32 k,void*l,u8 m){u32 *o=got[neffect];o[0]=fb(a);o[1]=fb(b);o[2]=fb(c);o[3]=fb(d);o[4]=(u32)(s32)e;o[5]=(u32)(s32)f;o[6]=(u32)(s32)h;o[7]=i;o[8]=(u32)j;o[9]=fb(k);o[10]=(u32)l;o[11]=m;neffect++;if(neffect==1)stage(3);}
    typedef void (*Routine)(u8*,u8,s32);
    static int check(Routine f){u32 n,i,j;for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){cur=rows[n];ninit=nquery=nrng=neffect=broken=0;query_point=(f32*)0;D_800A07B0=50.0f;for(i=0;i<64;i++)actor_data[i]=0;for(i=0;i<4;i++)q[i]=0;for(i=0;i<2;i++)for(j=0;j<12;j++)got[i][j]=0;*(f32*)(actor_data+0x14)=1.25f;*(f32*)(actor_data+0x18)=4.5f;*(f32*)(actor_data+0x1C)=-3.0f;f(cur[0]?actor_data:(u8*)0,(u8)cur[1],(s32)0x87654321u);if(broken||ninit!=cur[10]||nquery!=cur[11]||nrng!=cur[12]||neffect!=cur[13])return 1;if(nquery)for(i=0;i<4;i++)if(q[i]!=cur[6+i])return 2;for(i=0;i<neffect;i++)for(j=0;j<12;j++)if(got[i][j]!=cur[14+12*i+j])return 3;}return 0;}
    static int run(void){if(check(selected))return 10;\n'''
    for i,key in enumerate(controls):text+='if(!check(bad_'+key+'))return '+str(20+i)+';\n'
    text+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    file=out/'native.c';file.write_text(text);reports={}
    for opt in ('-O0','-O2','-O3'):
        exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(file),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0,(r.stdout,r.stderr)
        r=subprocess.run([str(exe)],capture_output=True,timeout=30);assert r.returncode==0,(opt,r.returncode,r.stderr)
        reports[opt]={'cases':len(cases),'effective_negative_controls':len(controls),'ubsan':True}
    result={'profiles':reports,'scope':'native actor and query mutations; guest-only stack-home alias effects modeled separately'}
    return result
