"""Native32 renderer bytes, provider packets and effective semantic controls."""
from pathlib import Path
import json, os, subprocess
from tools.tests import game_piece_renderer_1517a3a0_oracle as b
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def main():
    root = Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve(); out = root/b.source.BUILD
    body = b.source.SELECTED
    controls = {
        'wrong_bypass_category': body.replace('!= 89', '!= 88'),
        'wrong_retirement_nibble': body.replace('16 << view', '8 << view'),
        'wrong_matrix_bank': body.replace('D_800BE9C0 * 64 + 16', 'D_800BE9C0 * 32 + 16'),
        'wrong_alpha_field': body.replace('0, 0, 0, 0, 0, record->opacity', '0, 0, 0, 0, 0, record->variant'),
        'wrong_material_mode': body.replace('0x5049D8', '0x5049D0'),
    }
    assert all(v != body for v in controls.values())
    s = (out/'selected.c').read_text(); a=s.index('typedef struct {'); z=s.index('} SettleFade1517A84C;',a)+len('} SettleFade1517A84C;')
    code = '#include <ultra64.h>\n'+s[a:z]+'\n'+b.source.EXTRA+'''\nextern s16 D_800DD450;
typedef union{u32 u;f32 f;}Bits;
typedef struct{u32 target,args[10],digest;}Packet;
typedef struct{u32 category,view,packed,opacity,cached,reject,page,mutation,seed;
u8 initial[184],expected[184];u32 first[7],last[7],commands[128],count,result;Packet packets[4];}Case;
static const Case cases[]={
'''
    arr=lambda v:'{'+','.join('0x%Xu'%b.u32(x) for x in v)+'}'
    rows=[]
    for c in b.cases():
        if c.phase or c.mutation&2 or not 0<=c.view<4: continue
        initial=b.fixture(c); final,calls,obs,value=b.reference(initial,c)
        packets=['{0x%Xu,%s,0x%Xu}'%(t,arr((*args,*([0]*(10-len(args))))),observed[0]) for (t,args),observed in zip(calls,obs)]
        fields=(c.category,c.view,c.packed,c.opacity,c.cached,c.reject,c.page,c.mutation,c.seed)
        rows.append('{'+','.join('0x%Xu'%b.u32(v) for v in fields)+','+','.join(arr(v) for v in (
            [initial[b.RECORD+i] for i in range(184)], [final[b.RECORD+i] for i in range(184)],
            [b.read(initial,a,n) for a,n in b.FIELDS], [b.read(final,a,n) for a,n in b.FIELDS],
            [b.read(final,b.COMMANDS+i*4) for i in range(128)]))+
            ',%d,0x%Xu,{%s}}'%(len(calls),value,','.join(packets)))
    code+=',\n'.join(rows)+'\n};\n'+r'''
static SettleFade1517A84C record;static Gfx commands[64];
f32 D_800D9B20,D_800D9B1C,D_800D35E0,D_800D35E4;u8 D_800D9C10[256],D_800BE9C0;
u32 D_800D2C9C;Gfx D_8008CDF0[1];s16 D_800DD450;
static const Case*current;static u32 calls,error;
static f32 real(u32 u){Bits b;b.u=u;return b.f;}static u32 word(f32 f){Bits b;b.f=f;return b.u;}
static u32 canon(u32 v){u32 p=(u32)&record;if(v>=p&&v<p+184)return 0x50000u+v-p;
p=(u32)commands;if(v>=p&&v<p+512)return 0x60000u+v-p;
p=(u32)D_800D9C10;if(v>=p&&v<p+256)return 0x800d9c10u+v-p;
if(v==(u32)D_8008CDF0)return 0x8008cdf0u;return v;}
static u32 byteIndex(u32 k){if(k>=0xa8&&k<0xac)return k^3u;
if((k>=0x90&&k<0x9c)||(k>=0xa0&&k<0xa8)||(k>=0xac&&k<0xb2))return k^1u;return k;}
static u32 get(u32 i){switch(i){case 0:return word(D_800D9B20);case 1:return word(D_800D9B1C);
case 2:return word(D_800D35E0);case 3:return word(D_800D35E4);case 4:return D_800BE9C0;
case 5:return (u16)D_800DD450;default:return D_800D2C9C;}}
static void set(u32 i,u32 v){switch(i){case 0:D_800D9B20=real(v);break;case 1:D_800D9B1C=real(v);break;
case 2:D_800D35E0=real(v);break;case 3:D_800D35E4=real(v);break;case 4:D_800BE9C0=(u8)v;break;
case 5:D_800DD450=(s16)v;break;default:D_800D2C9C=v;}}
static u32 digest(void){u32 i,h=2166136261u;for(i=0;i<184;i++)h=(h^((u8*)&record)[byteIndex(i)])*16777619u;
for(i=0;i<128;i++)h=(h^canon(((u32*)commands)[i]))*16777619u;for(i=0;i<7;i++)h=(h^get(i))*16777619u;return h;}
static u32 notify(u32 target,u32*a,u8*sync){u32 i,n=calls++;const Packet*p;
if(n>=current->count||n>=4)error=1;else{p=current->packets+n;if(p->target!=target||p->digest!=digest())error=1;
for(i=0;i<10;i++)if(p->args[i]!=canon(a[i]))error=1;}if(sync&&*sync)error=1;n++;
if(target==0x1517a9a8u||target==0x15142fbcu){Gfx*g=(Gfx*)a[0];g->words.w0=0xf1000000u|n;g->words.w1=0x12340000u|n;}
if(target==0x15043d90u)for(i=0;i<64;i++)((u8*)a[0])[i]=(u8)(i*7+n);
if(current->mutation&1){record.retained00[0]=(u8[]){8,9,12,89}[current->seed%4];record.variant^=0x55;
record.retireNibbles^=0x23;record.opacity=(u8)(current->opacity+n*17);
record.x=(s16)(0x8000+n*13);record.y=(s16)(0x8000+n*13+1);record.z=(s16)(0x8000+n*13+2);
record.angleX=(s16)(0x8000+n*13+3);record.angleY=(s16)(0x8000+n*13+4);record.angleZ=(s16)(0x8000+n*13+5);
record.scale=-1.0f;D_800BE9C0^=1;D_800DD450=-1;D_800D2C9C^=0x87654321u;D_800D9B20=-2.0f;}
if(sync)*sync=0x5a;if(target==0x1510aee0u)return current->reject;
return a[0]+8*(1+current->seed%2);}
s32 func_1510AEE0(void*p,f32 x,f32 y,f32 z,f32 a,f32 b,f32 c,f32 d,f32*e,f32*f){u32 args[10]={(u32)p,word(x),word(y),word(z),word(a),word(b),word(c),word(d),(u32)e,(u32)f};return (s32)notify(0x1510aee0u,args,0);}
s32 func_1517A9A8(s32 p,volatile s32 kind){u32 args[10]={(u32)p,(u32)kind};return (s32)notify(0x1517a9a8u,args,0);}
void func_15043D90(Mtx*p,f32 x,f32 y,f32 z,f32 a,f32 b,f32 c,f32 d,f32 e,f32 f){u32 args[10]={(u32)p,word(x),word(y),word(z),word(a),word(b),word(c),word(d),word(e),word(f)};notify(0x15043d90u,args,0);}
Gfx*func_15142FBC(Gfx*p,u32 mode,u32 kind,u8*sync){u32 args[10]={(u32)p,mode,kind,0x70000};return (Gfx*)notify(0x15142fbcu,args,sync);}
'''
    for i,candidate in enumerate([body,*controls.values()]): code+='\n'+candidate.replace(b.source.NAME,'candidate_'+str(i))+'\n'
    code+='\nstatic Gfx*(*tests[])(Gfx*,SettleFade1517A84C*,s16)={'+','.join('candidate_'+str(i) for i in range(6))+'};\n'+r'''
static int run(void){u32 i,j,k,killed=0;Gfx*answer;
if(sizeof(SettleFade1517A84C)!=184||sizeof(Gfx)!=8||sizeof(Mtx)!=64)return 20;
for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){current=cases+i;for(j=0;j<6;j++){
for(k=0;k<184;k++)((u8*)&record)[byteIndex(k)]=current->initial[k];for(k=0;k<128;k++)((u32*)commands)[k]=0xa5a5a5a5u;
for(k=0;k<7;k++)set(k,current->first[k]);calls=error=0;
answer=tests[j](commands,&record,(s16)current->view);if(canon((u32)answer)!=current->result||calls!=current->count)error=1;
for(k=0;k<184;k++)if(((u8*)&record)[byteIndex(k)]!=current->expected[k])error=1;
for(k=0;k<128;k++)if(canon(((u32*)commands)[k])!=current->commands[k])error=1;
for(k=0;k<7;k++)if(get(k)!=current->last[k])error=1;
if(error){if(!j)return 10;killed|=1u<<(j-1);}}}return killed==31u?0:11;}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    p=out/'native.c';p.write_text(code)
    for opt in ('-O0','-O2','-O3'):
        exe=out/('native'+opt);q=subprocess.run(native_command(opt)+['-o',str(exe),str(p)],cwd=root,capture_output=True,text=True)
        assert q.returncode==0,(q.stdout,q.stderr)
        q=subprocess.run([str(exe)],cwd=root,capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stderr)
    report=dict(native32=True,cases=len(rows),profiles=['-O0','-O2','-O3'],ubsan=True,
                negative_controls=list(controls),all_controls_detected=True,record_bytes=184,command_words=128,
                provider_packets_and_observations=True,valid_view_domain='0..3',guest_home_mutations_excluded=True)
    (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)

if __name__=='__main__':main()
