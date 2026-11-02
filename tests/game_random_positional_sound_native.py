"""Native32 copied-table timing, typed audio boundary and eight effective controls."""
from pathlib import Path
import subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import game_random_positional_sound_oracle as g
def qualify(root,output,body,headers):
 root,output=Path(root),Path(output)
 variants=[('baseline',body)]
 variants.append(('live-table',body.replace('    SoundIds sounds;\n','').replace('    sounds = *(SoundIds *)D_800A66E4;\n','').replace('sounds.ids[','D_800A66E4[')))
 variants.append(('constant-index',body.replace('(u32)func_150ADA20() % 10U','0')))
 variants.append(('modulo-nine',body.replace('% 10U','% 9U')))
 variants.append(('truncate-rng16',body.replace('(u32)func_150ADA20()','(u16)func_150ADA20()')))
 variants.append(('cached-X',body.replace('    SoundIds sounds;','    s32 cachedX = (s32)position->unk0;\n    SoundIds sounds;').replace('(s32)position->unk0,','cachedX,')))
 variants.append(('swapped-XY',body.replace('(s32)position->unk0, (s32)position->unk4,','(s32)position->unk4, (s32)position->unk0,')))
 variants.append(('narrow-channel',body.replace('flags, channel,','flags, (s16)channel,')))
 variants.append(('narrow-minimum8',body.replace('minimum, maximum);','(u8)minimum, maximum);')))
 assert len(set(b for _,b in variants))==9
 rows=[];s=dict(table=0x800A66E4,rng=g.RNG,audio=g.AUDIO)
 for c in g.cases():
  if c.phase or c.mutation>1:continue
  initial=g.fixture(c,s);expected,calls=g.reference(initial,c,s);a=g.arguments(c,s)
  addresses=[s['table']+4*j for j in range(10)]+[g.POSITION+4*j for j in range(3)]+[g.SECOND+4*j for j in range(3)]
  before=[g.read(initial,p)for p in addresses];after=[g.read(expected,p)for p in addresses]
  audio=list(calls[-1][1]);audio[5:]=[g.u32(g.half(v))for v in audio[5:]]
  rows.append((c.rng,c.mutation,c.profile==3,list(a[:4])+list(a[5:]),before,after,audio))
 def array(v):return '{'+','.join('0x%08Xu'%x for x in v)+'}'
 vectors=[]
 for rng,mode,alias,a,before,after,audio in rows:vectors.append('{0x%08Xu,%du,%du,%s,%s,%s,%s}'%(rng,mode,alias,array(a),array(before),array(after),array(audio)))
 functions='\n'.join(b.replace('func_151618BC(',f'candidate_{j}(')for j,(_,b)in enumerate(variants))
 code=headers+'''
s32 D_800A66E4[10];
static struct17 positions[2];
static u32 rngValue,mode,observed[10],rngCalls,audioCalls;
static f32 as_float(u32 v){union{u32 u;f32 f;}p;p.u=v;return p.f;}
static u32 as_word(f32 v){union{u32 u;f32 f;}p;p.f=v;return p.u;}
s32 func_150ADA20(void){
 rngCalls++;
 if(mode){
  int j;
  for(j=0;j<10;j++)D_800A66E4[j]=(s32)as_word(100.25f+j*7.5f);
  for(j=0;j<3;j++){((f32*)&positions[0])[j]=-321.75f+j*700.25f;((f32*)&positions[1])[j]=65536.5f+j*12.25f;}
 }
 return (s32)rngValue;
}
u16 func_10010F88(s32 id,u16 volume,s16 pitch,u8 flags,s32 channel,s16 x,s16 y,s16 z,s16 minimum,s16 maximum){
 u32 values[10]={(u32)id,volume,(u32)pitch,flags,(u32)channel,(u32)x,(u32)y,(u32)z,(u32)minimum,(u32)maximum};int j;
 audioCalls++;for(j=0;j<10;j++)observed[j]=values[j];return 0xC7D8;
}
'''+functions+'''
typedef struct {u32 rng,mode,alias,args[6],before[16],after[16],audio[10];} Vector;
static const Vector vectors[]={'''+','.join(vectors)+'''};
typedef void(*Candidate)(u16,s16,u8,s32,struct17*,s16,s16);
static Candidate functions[]={'''+','.join(f'candidate_{j}'for j in range(9))+'''};
static void mismatch(u32 i,u32 j,u32 actual,u32 expected){u32 v[4]={i,j,actual,expected};int result;__asm__ volatile(".byte 0xcd,0x80":"=a"(result):"0"(4),"b"(1),"c"(v),"d"(16):"memory");(void)result;}
static int run(void){
 unsigned i;int j;
 for(i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++){
  const Vector*v=&vectors[i];rngValue=v->rng;mode=v->mode;rngCalls=audioCalls=0;
  for(j=0;j<10;j++)D_800A66E4[j]=(s32)v->before[j];
  for(j=0;j<6;j++)((f32*)positions)[j]=as_float(v->before[10+j]);
  functions[VARIANT]((u16)v->args[0],(s16)v->args[1],(u8)v->args[2],(s32)v->args[3],v->alias?(struct17*)D_800A66E4:&positions[0],(s16)v->args[4],(s16)v->args[5]);
  if(rngCalls!=1||audioCalls!=1)return 11;
  for(j=0;j<10;j++)if(observed[j]!=v->audio[j]){mismatch(i,j,observed[j],v->audio[j]);return 12;}
  for(j=0;j<10;j++)if((u32)D_800A66E4[j]!=v->after[j])return 13;
  for(j=0;j<6;j++)if(as_word(((f32*)positions)[j])!=v->after[10+j])return 14;
 }
 return 0;
}
'''+START.replace('void _start(void)', '__attribute__((force_align_arg_pointer)) void _start(void)')
 report=[]
 for opt in ('-O0','-O2','-O3'):
  controls=[]
  for j,(name,_)in enumerate(variants):
   p=output/('native-'+opt[1:]+'-'+name);p.with_suffix('.c').write_text(code)
   q=subprocess.run(native_command(opt)+['-fno-strict-aliasing','-DVARIANT=%d'%j,str(p.with_suffix('.c')),'-o',str(p)],cwd=root,capture_output=True,text=True);assert q.returncode==0,(opt,name,q.stdout,q.stderr)
   q=subprocess.run([str(p)],capture_output=True)
   if j:assert q.returncode in(11,12,13,14),(opt,name,q.returncode,q.stderr);controls.append(name)
   else:assert q.returncode==0,(opt,q.returncode,q.stdout,q.stderr)
  report.append(dict(profile=opt,cases=len(rows),baseline_executions=len(rows),controls=controls,eight_controls_effective=True,UBSan=True,all_public_table_and_position_words_checked=True,typed_audio_boundary_checked=True,finite_s32_float_domain=True,guest_home_mutations_excluded=True))
 return report
