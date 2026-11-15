"""Native32 defined C behavior; finite modeled callbacks do not qualify a match."""
import hashlib,json,subprocess
from tools.experiments import game_attachment_effect_150f97ec_lifetime as s
from tools.tests.game_attachment_effect_150f97ec_lifetime_guest import corpus
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def harness(source):
    rows=[]
    for attached,index,selector,mutation,seed,rand,context in corpus():
        rows.append('{%d,%d,0x%Xu,%d,%d,{0x%Xu,0x%Xu},0x%Xu}'%(attached,index,selector,mutation,seed,*rand,context))
    code=source+r'''
typedef struct {u8 attached,slot;u32 selector,mutation,seed,random[2],context;} NativeCase;
static const NativeCase cases[]={ROWS};
static const NativeCase *current;
typedef struct {u8 pad[0x1D4];u8 *matrices;u8 tail[0x28];} NativeActor;
static NativeActor actor;
static u8 matrices[0x4000] __attribute__((aligned(8)));
static volatile u32 calls,failed,nfloat,nint;
static u8 returned;
f32 D_800A1C48[3]={-124.0f,-8.0f,28.0f};
f32 D_800A1C54[3]={-170.0f,-8.0f,28.0f};
u8 D_80088B50;
static u32 word(f32 x){union{f32 f;u32 u;}v;v.f=x;return v.u;}
static void step(u32 kind){static const u8 order[7]={1,2,2,3,3,2,4};u32 i=calls++;if(i>=7||order[i]!=kind)failed=1;}
void func_15145EA4(f32 **input,f32 **output,void *matrix,s32 count){
    step(1);if(*input!=D_800A1C48||matrix!=matrices+(u32)current->slot*64||count!=1)failed=1;
    (*output)[0]=1.25f;(*output)[1]=-2.5f;(*output)[2]=3.75f;*input+=3;*output+=3;
    if(current->mutation)D_80088B50=7;
}
f32 func_150ADA68(void){static const f32 draws[3]={0.25f,0.5f,0.75f};u32 i=nfloat++;step(2);if(i>=3){failed=1;return 0;}return draws[i];}
s32 func_150ADA20(void){u32 i=nint++;step(3);if(i>=2){failed=1;return 0;}return (s32)current->random[i];}
u8 *func_15102B38(u8 *owner,u8 slot,f32 *point,f32 *other,JointEffectSpread150F97EC *spread,s16 width,u8 lifetime,f32 coefficient,f32 *transformed,u8 alpha,s32 zero,s16 code,u8 priority,s32 context){
    step(4);
    if(owner!=(u8*)&actor||slot!=(current->mutation?7:current->slot)||point!=D_800A1C48||other!=D_800A1C54)failed=1;
    if(word(spread->horizontal)!=word(35.0f)||word(spread->vertical)!=word(2.25f)||word(coefficient)!=word(625.0f))failed=1;
    if((u32)width!=current->random[0]%3u+4||lifetime!=current->random[1]%156u+100)failed=1;
    if(word(transformed[0])!=word(1.25f)||word(transformed[1])!=word(-2.5f)||word(transformed[2])!=word(3.75f))failed=1;
    if(alpha!=255||zero!=0||code!=-1||priority!=(current->selector&255)||((u32)context)!=current->context)failed=1;
    return &returned;
}
int run(void){
    u32 i,j;for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        current=&cases[i];for(j=0;j<sizeof(actor);j++)((u8*)&actor)[j]=(u8)(j*29+current->seed*19+0x31);
        actor.matrices=current->attached?matrices:0;D_80088B50=current->slot;calls=failed=nfloat=nint=0;
        func_150F97EC((u8*)&actor,(u8)current->selector,(s32)current->context);
        if(failed||calls!=(current->attached?7u:0u)||nfloat!=(current->attached?3u:0u)||nint!=(current->attached?2u:0u))return 1;
    }return 0;
}
'''
    return code.replace('ROWS',',\n'.join(rows))+START

def main():
    s.immutable();source=s.MANIFEST['candidates']['conditional_pair']['source'];code=harness(source);path=s.OUT/'lifetime-native.c';path.write_text(code)
    controls=(('spread','* 14.0f + 28.0f','* 15.0f + 28.0f'),('modulus','firstRandom % 3U + 4','firstRandom % 4U + 4'),('lifetime','secondRandom % 156U + 100','secondRandom % 156U + 101'),('coefficient','* 300.0f + 400.0f','* 300.0f + 401.0f'),('context','255, 0, -1, priority, context);','255, 0, -1, priority, context ^ 1);'))
    profiles=[]
    for opt in ('-O0','-O2','-O3'):
        exe=s.OUT/('lifetime-native'+opt);q=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=s.ROOT,capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
        p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==0,(opt,p.returncode,p.stdout,p.stderr)
        killed=[]
        for label,old,new in controls:
            assert code.count(old)==1,(label,code.count(old));bad=s.OUT/('lifetime-negative-'+label+opt+'.c');binary=bad.with_suffix('');bad.write_text(code.replace(old,new))
            q=subprocess.run(native_command(opt)+[str(bad),'-o',str(binary)],cwd=s.ROOT,capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
            result=subprocess.run([str(binary)],capture_output=True);assert result.returncode!=0,('Ineffective native control',opt,label);killed.append(label)
        profiles.append(dict(profile=opt,cases=len(corpus()),negative_controls=killed,ubsan=True,exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest()))
    s.immutable();report=dict(profiles=profiles,source_sha256=hashlib.sha256(code.encode()).hexdigest(),finite_modeled_helpers_only=True,private_state_FP_exceptions_and_hardware_uncredited=True,c_match_credit=0)
    (s.OUT/'lifetime-native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
