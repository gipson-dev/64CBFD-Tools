"""SDK32 direct C, char aliases, complete records, provider effects and controls."""
from pathlib import Path
import json,struct,subprocess,sys
from tools.experiments import game_sprite_frame_update_15168870_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_sprite_frame_update_15168870_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
def cases():return[c for c in g.cases()if c.index in(-1,*range(22))and c.texture<70 and not c.mode&16]
def digest(m,s=g.SYMS):
 values=[m[p+i]for p in(g.STATE,g.OTHER)for i in range(g.SIZE)]
 values +=[m[g.META+i]for i in range(256*16)]
 values +=[{0:0,g.CB0:1,g.CB1:2}[g.read(m,s['D_8008C9C8']+4*i)]for i in range(22)]
 values +=[g.read(m,s['D_800BE9E4'])];h=2166136261
 for v in values:h=((h^v)*16777619)&0xFFFFFFFF
 return h
def trace(calls,observations):
 h=2166136261
 for(t,(record,)),o in zip(calls,observations):
  assert record==o[0]
  for v in({g.CB0:1,g.CB1:2,g.CLEAN:3}[t],1 if record==g.STATE else 2,*o[1:]):h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
 return h
def mutations(body):
 positive='''                do {
                    state->phase -= upper;
                } while (state->phase > upper);'''
 negative='''                do {
                    state->phase += upper;
                } while (state->phase < 0);'''
 capture='        frames = D_8008CA4C[state->textureIndex][4];\n'
 update='        state->phase = (u32)state->phase + (u32)speed * (u32)D_800BE9E4;\n'
 result={
 'positive-speed-only':body.replace('if (speed != 0)','if (speed > 0)'),
 'wrong-frame-byte':body.replace('state->textureIndex][4]','state->textureIndex][5]'),
 'wrong-tick':body.replace('(u32)D_800BE9E4','((u32)D_800BE9E4 + 1)'),
 'lost-signed-phase-bit':body.replace(update,update+'        state->phase &= 0x7FFF;\n'),
 'wrong-period':body.replace('(frames << 8) - 1','(frames << 8) - 2'),
 'wrong-reflection-flag':body.replace('flags & 0x40','flags & 0x20'),
 'missing-speed-reflection':body.replace('state->speed = -speed;','state->speed = speed;'),
 'wrong-terminal-flag':body.replace('flags & 4','flags & 8'),
 'positive-modulo-shortcut':body.replace(positive,'                state->phase %= upper;'),
 'negative-modulo-shortcut':body.replace(negative,'                state->phase = (state->phase + upper) % upper;'),
 'late-frame-capture':body.replace(capture+update,update+capture),
 'missing-callback':body.replace('callback(state);',';'),
 'wrong-callback-slot':body.replace('D_8008C9C8[state->callbackIndex]','D_8008C9C8[state->callbackIndex ^ 1]'),
 'early-cleanup-decision':body.replace('    s32 upper;','    s32 upper;\n    s32 done;').replace('    if (state->callbackIndex != -1)','    done = state->phase == -1;\n    if (state->callbackIndex != -1)').replace('    if (state->phase == -1)','    if (done)'),
 'wrong-cleanup-sentinel':body.replace('    if (state->phase == -1)','    if (state->phase == 0)')}
 assert len(result)==15 and all(text!=body for text in result.values());return result
def program(body):
 selected=body.replace('func_15168870(','subject(');decl=packet.MANIFEST['declarations'];controls=mutations(body);rows=[]
 arr=lambda xs:'{'+','.join(arr(x)if isinstance(x,(list,tuple,bytes))else'0x%Xu'%(x&0xFFFFFFFF)for x in xs)+'}'
 for c in cases():
  initial=g.fixture(c,order='little');m,calls,obs=g.reference(initial,c,order='little')
  rows.append(arr([c.frames,c.ticks,c.callback,c.mode,c.texture,c.alias,bytes(initial[g.STATE+i]for i in range(g.SIZE)),digest(m),trace(calls,obs),len(calls)]))
 text='#include <ultra64.h>\n#include "structs.h"\n'+decl+'\nextern s32 D_800BE9E4;\nextern u8 *D_8008CA4C[];\nvoid func_1516972C(struct102 *);\n'+selected+'\n'
 for name,source in controls.items():text+=source.replace('func_15168870(','negative_'+name.replace('-','_')+'(')+'\n'
 text+='''
_Static_assert(sizeof(void*)==4&&sizeof(SpriteFrameState)==184&&__builtin_offsetof(SpriteFrameState,phase)==0x98&&__builtin_offsetof(SpriteFrameState,speed)==0x9A&&__builtin_offsetof(SpriteFrameState,flags)==0xA8&&__builtin_offsetof(SpriteFrameState,textureIndex)==0xB0&&__builtin_offsetof(SpriteFrameState,callbackIndex)==0xB2,"Measured SDK32 sprite frame view");
typedef struct{u32 frames,ticks,callback,mode,texture,alias;u8 initial[184];u32 state_hash,trace_hash,calls;}Row;
static const Row rows[]={'''+',\n'.join(rows)+'''};
struct Box{u8 before[16];SpriteFrameState object;u8 after[16];};
static struct Box box,other;static struct{u8 before[16],bytes[256][16],after[16];}metadataStore;
#define metadata metadataStore.bytes
#define beforeMetadata metadataStore.before
#define afterMetadata metadataStore.after
u8 *D_8008CA4C[256];static void callback0(SpriteFrameState*);static void callback1(SpriteFrameState*);
void(*D_8008C9C8[22])(SpriteFrameState*);s32 D_800BE9E4;static const Row *row;static u32 trace_hash,call_count;
static void fill(u8*p,u32 n,u8 v){u32 i;for(i=0;i<n;i++)p[i]=v;}
static void hash(u32*h,u32 v){*h=(*h^v)*16777619u;}
static void record(u32 target,SpriteFrameState*s){u32 id=s==&box.object?1:s==&other.object?2:0;
 hash(&trace_hash,target);hash(&trace_hash,id);hash(&trace_hash,(u32)(s32)s->phase);hash(&trace_hash,(u32)(s32)s->speed);hash(&trace_hash,(u8)s->callbackIndex);hash(&trace_hash,(u32)D_800BE9E4);call_count++;
}
static void effect(SpriteFrameState*s){
 if(row->mode&1)s->phase=-1;if(row->mode&2)s->phase=123;if(row->mode&4)s->speed=-3;
 if(row->mode&8){D_8008C9C8[(s32)s->callbackIndex]=0;s->callbackIndex=-1;}
 if(row->mode&32){s->textureIndex^=0x80;D_800BE9E4=0x13579BDF;}
}
static void callback0(SpriteFrameState*s){record(1,s);effect(s);}
static void callback1(SpriteFrameState*s){record(2,s);effect(s);}
void func_1516972C(struct102*p){SpriteFrameState*s=(SpriteFrameState*)(void*)p;record(3,s);
 if(row->mode&64){fill((u8*)s+8,4,0);((u8*)s)[0x40]^=0xA5;}
}
static u32 state_hash(void){u32 h=2166136261u,i,j;
 for(i=0;i<184;i++)hash(&h,((u8*)&box.object)[i]);for(i=0;i<184;i++)hash(&h,((u8*)&other.object)[i]);
 for(i=0;i<256;i++)for(j=0;j<16;j++)hash(&h,metadata[i][j]);
 for(i=0;i<22;i++)hash(&h,D_8008C9C8[i]==callback0?1:D_8008C9C8[i]==callback1?2:0);
 hash(&h,(u32)D_800BE9E4);return h;
}
static u32 run(void(*fn)(SpriteFrameState*)){u32 n,i,j,fail=0;
 for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){
  row=&rows[n];fill(box.before,16,0xD1);fill(box.after,16,0xD2);fill(other.before,16,0xD3);fill(other.after,16,0xD4);fill(beforeMetadata,16,0xD5);fill(afterMetadata,16,0xD6);
  for(i=0;i<184;i++){((u8*)&box.object)[i]=row->initial[i];((u8*)&other.object)[i]=(u8)(i*13+0x310+7);}
  other.object.phase=-1;other.object.speed=0x1234;
  for(i=0;i<256;i++){
   for(j=0;j<16;j++)metadata[i][j]=(u8)(i*11+j*17+3);
   metadata[i][4]=(u8)(row->frames+29*i+7);D_8008CA4C[i]=metadata[i];
  }
  D_8008CA4C[row->texture]=row->alias?(u8*)&box.object+(row->alias==1?0x90:row->alias==2?0x94:0x96):metadata[row->texture];
  if(!row->alias)metadata[row->texture][4]=(u8)row->frames;
  for(i=0;i<22;i++)D_8008C9C8[i]=row->callback?(i&1?callback1:callback0):0;
  D_800BE9E4=(s32)row->ticks;trace_hash=2166136261u;call_count=0;fn(&box.object);
  if(state_hash()!=row->state_hash||trace_hash!=row->trace_hash||call_count!=row->calls){
   if(fn==subject&&!fail){u32 diagnostic[7]={n,state_hash(),row->state_hash,trace_hash,row->trace_hash,call_count,row->calls};__asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(diagnostic),"d"(28));}
   fail++;
  }
  for(i=0;i<16;i++)if(box.before[i]!=0xD1||box.after[i]!=0xD2||other.before[i]!=0xD3||other.after[i]!=0xD4||beforeMetadata[i]!=0xD5||afterMetadata[i]!=0xD6)fail++;
 }return fail;
}
void _start(void){u32 mask=0,expected='''+str((1<<len(controls))-1)+'''u;u32 fail=run(subject);int result;
'''
 for i,name in enumerate(controls):text+='if(run(negative_'+name.replace('-','_')+'))mask|='+str(1<<i)+'u;\n'
 text+='result=fail||mask!=expected;\nif(result){u32 diagnostic[2]={fail,mask};__asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(diagnostic),"d"(8));}\n__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}\n'
 return text,controls
def main():
 source=out/'native.c';text,controls=program(packet.MANIFEST['body']);source.write_text(text);profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);cmd=native_command(opt)+['-fstrict-aliasing',str(source),'-o',str(exe)]
  q=subprocess.run(cmd,cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  q=subprocess.run([str(exe)],capture_output=True,timeout=60)
  if q.returncode:
   (out/'native-failure.bin').write_bytes(q.stderr)
  assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,struct.unpack('<%dI'%(len(q.stderr)//4),q.stderr)if len(q.stderr)%4==0 else q.stderr)
  profiles[opt]=dict(cases=len(cases()),SDK32=True,strict_aliasing=True,UBSan=True,effective_controls=len(controls))
 r=dict(profiles=profiles,effective_source_controls=list(controls),full_records_metadata_callbacks_and_provider_trace=True,typed_record_layout=True,record_and_metadata_canaries=True,
  limits='Native selectors -1 or0..21 and textures0..69. Numeric byte aliases use explicit little-endian native fixtures. Incoming-home mutations and extended table indices remain guest-only; cleanup is contracted.',source_installed=packet.installed(),matching_credit=0)
 (out/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
