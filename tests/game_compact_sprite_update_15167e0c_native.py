"""Native SDK32 partial record, byte aliases, callback traces and source controls."""
from pathlib import Path
import json,struct,subprocess,sys
from tools.experiments import game_compact_sprite_update_15167e0c_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_compact_sprite_update_15167e0c_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
def cases():return[c for c in g.cases()if c.index in(-1,*range(22))and c.completion in(-1,*range(11))and not c.mode&48]
def fnv(values):
 h=2166136261
 for v in values:h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
 return h
def meta_id(p):return{g.META:1,g.META+32:2,g.META+64:3,g.STATE+0x18:4,g.STATE+0x19:5,g.STATE+0x1A:6}[p]
def record_values(m,p):return[m[p+i]for i in range(g.SIZE)if not 0x10<=i<0x14]+[meta_id(g.word(m,p+0x10,'little'))]
def state_hash(m):
 values=record_values(m,g.STATE)+record_values(m,g.OTHER)+[m[g.META+i]for i in range(96)]
 values +=[{0:0,g.CB0:1,g.CB1:2}[g.word(m,g.SYMS['D_8008C9C8']+4*i,'little')]for i in range(22)]
 values +=[{g.END0:1,g.END1:2}[g.word(m,g.SYMS['D_8008CA20']+4*i,'little')]for i in range(11)]
 values +=[g.word(m,g.SYMS['D_800BE9E4'],'little')];return fnv(values)
def trace_hash(observations):
 values=[];ids={g.CB0:1,g.CB1:2,g.END0:3,g.END1:4,g.CLEAN:5}
 for t,p,record,tick,flag in observations:
  mm={p+i:b for i,b in enumerate(record)};values +=[ids[t],1 if p==g.STATE else 2,*record_values(mm,p),tick]
 return fnv(values)
def controls(body):
 positive='''                        do {
                            state->phase -= upper;
                        } while (state->phase > upper);'''
 negative='''                    do {
                        state->phase += upper;
                    } while (state->phase < 0);'''
 capture='            upper = (state->texture[4] << 8) - 1;\n';update='            state->phase = (u32)state->phase + (u32)speed * (u32)D_800BE9E4;\n'
 result={
 'wrong-timer-sentinel':body.replace('!= 0x7FFF','!= 0x7FFE'),
 'lost-signed-timer-store':body.replace('        if (state->remaining < 0)','        state->remaining &= 0x7FFF;\n        if (state->remaining < 0)'),
 'unsigned-fade':body.replace('if (state->fadeStep > 0)','if ((u8)state->fadeStep > 0)'),
 'fade-equality':body.replace('state->fadeStep < state->alpha','state->fadeStep <= state->alpha'),
 'cleared-alpha-on-completion':body.replace('        } else {\n            state->remaining = 0;','        } else {\n            state->alpha = 0;\n            state->remaining = 0;'),
 'missing-update-callback':body.replace('        D_8008C9C8[state->callbackIndex]((SpriteFrameState *)(void *)state);','        ;'),
 'completion-not-sticky':body.replace('    if (state->remaining != 0) {','    finished = 0;\n    if (state->remaining != 0) {'),
 'stale-tick-after-callback':body.replace('    u8 finished;','    u8 finished;\n    u32 ticks = D_800BE9E4;').replace('(u32)D_800BE9E4','ticks'),
 'no-vertical-acceleration':body.replace('state->velocityY += state->accelerationY;','state->velocityY += 0;'),
 'unsigned-x-velocity':body.replace('(u32)(s32)state->velocityX','(u32)(u16)state->velocityX'),
 'wrong-fixed-point-shift':body.replace('<< 8) | state->fraction','<< 7) | state->fraction'),
 'lost-fraction':body.replace('state->fractionY = (u32)packed + (u32)delta;','state->fractionY = 0;'),
 'wrong-period':body.replace('(state->texture[4] << 8) - 1','(state->texture[4] << 8) - 2'),
 'late-frame-capture':body.replace(capture+update,update+capture),
 'wrong-upper-termination':body.replace('state->flags & 0x20','state->flags & 0x10'),
 'wrong-lower-termination':body.replace('state->flags & 0x40','state->flags & 0x10'),
 'missing-upper-history-flag':body.replace('state->flags |= 0x80;','state->flags |= 0;'),
 'wrong-bounce-flag':body.replace('state->flags & 2','state->flags & 4'),
 'positive-modulo-shortcut':body.replace(positive,'                        state->phase %= upper;'),
 'negative-modulo-shortcut':body.replace(negative,'                    state->phase = (state->phase + upper) % upper;'),
 'wrong-completion-sentinel':body.replace('state->completionIndex != -1','state->completionIndex != 0'),
 'cleanup-before-completion':body.replace('    if (finished != 0) {','    if (finished != 0) {\n        func_1516972C((struct102 *)(void *)state);').replace('        func_1516972C((struct102 *)(void *)state);\n    }','    }'),
 'missing-cleanup':body.replace('        func_1516972C((struct102 *)(void *)state);','        ;'),
 'stopped-resuscitated-motion':body.replace('if (state->remaining != 0) {','if (state->remaining != 0 && !finished) {')}
 assert len(result)==24 and all(v!=body for v in result.values());return result
def program(body):
 source=(out/'baseline/conker/src/game_1944C0.c').read_text();lo=source.index('/* Measured 0xB8-byte sprite-record view');hi=source.index('extern void (*D_8008C9C8',lo);sdk_view=source[lo:hi];decl=packet.MANIFEST['declarations'];rows=[]
 arr=lambda xs:'{'+','.join(arr(x)if isinstance(x,(list,tuple,bytes))else'0x%Xu'%(x&0xFFFFFFFF)for x in xs)+'}'
 for c in cases():
  initial=g.fixture(c,'little');m,calls,obs=g.reference(initial,c,'little')
  rows.append(arr([c.frames,c.ticks,c.callback,c.mode,c.alias,bytes(initial[g.STATE+i]for i in range(g.SIZE)),state_hash(m),trace_hash(obs),len(calls)]))
 pre='#include <ultra64.h>\n#include "structs.h"\n'+sdk_view+'\n'+decl+'''
extern s32 D_800BE9E4;extern void(*D_8008C9C8[22])(SpriteFrameState*);extern void(*D_8008CA20[11])(void*);void func_1516972C(struct102*);
'''
 selected=body.replace('func_15167E0C(','subject(');text=pre+selected+'''
_Static_assert(sizeof(void*)==4&&sizeof(CompactSpriteState)==76&&sizeof(SpriteFrameState)==184,"Actual SDK32 partial views");
_Static_assert(__builtin_offsetof(CompactSpriteState,texture)==0x10&&__builtin_offsetof(CompactSpriteState,phase)==0x1C&&__builtin_offsetof(CompactSpriteState,speed)==0x1E&&__builtin_offsetof(CompactSpriteState,x)==0x20&&__builtin_offsetof(CompactSpriteState,y)==0x22&&__builtin_offsetof(CompactSpriteState,z)==0x24&&__builtin_offsetof(CompactSpriteState,velocityX)==0x26&&__builtin_offsetof(CompactSpriteState,velocityZ)==0x28&&__builtin_offsetof(CompactSpriteState,fractionX)==0x2C&&__builtin_offsetof(CompactSpriteState,fractionZ)==0x2D&&__builtin_offsetof(CompactSpriteState,fractionY)==0x2E&&__builtin_offsetof(CompactSpriteState,callbackIndex)==0x2F&&__builtin_offsetof(CompactSpriteState,velocityY)==0x30&&__builtin_offsetof(CompactSpriteState,accelerationY)==0x32&&__builtin_offsetof(CompactSpriteState,remaining)==0x38&&__builtin_offsetof(CompactSpriteState,fadeStep)==0x3A&&__builtin_offsetof(CompactSpriteState,alpha)==0x3F&&__builtin_offsetof(CompactSpriteState,flags)==0x44&&__builtin_offsetof(CompactSpriteState,completionIndex)==0x48,"Recovered offsets");
typedef struct{u32 frames,ticks,callback,mode,alias;u8 initial[76];u32 state,trace,calls;}Row;
static const Row rows[]={'''+',\n'.join(rows)+'''};
static const Row*c;static struct{u8 before[16];CompactSpriteState object;u8 after[16];}box,other;
static struct{u8 before[16],bytes[96],after[16];}meta;
s32 D_800BE9E4;void(*D_8008C9C8[22])(SpriteFrameState*);void(*D_8008CA20[11])(void*);
static u32 trace,calls,error;static void cb0(SpriteFrameState*);static void cb1(SpriteFrameState*);static void end0(void*);static void end1(void*);
static void fill(u8*p,u32 n,u8 v){u32 i;for(i=0;i<n;i++)p[i]=v;}
static void hash(u32*h,u32 v){*h=(*h^v)*16777619u;}
static u32 metadata_id(u8*p){return p==meta.bytes?1:p==meta.bytes+32?2:p==meta.bytes+64?3:p==(u8*)&box.object+0x18?4:p==(u8*)&box.object+0x19?5:p==(u8*)&box.object+0x1A?6:0;}
static void record_hash(u32*h,CompactSpriteState*s){u32 i;for(i=0;i<76;i++)if(i<0x10||i>=0x14)hash(h,((u8*)s)[i]);hash(h,metadata_id(s->texture));}
static void observe(u32 target,CompactSpriteState*s){hash(&trace,target);hash(&trace,s==&box.object?1:s==&other.object?2:0);record_hash(&trace,s);hash(&trace,(u32)D_800BE9E4);calls++;}
static void update(CompactSpriteState*s,u32 target){observe(target,s);
 if(c->mode&1)s->remaining=0;if(c->mode&2)s->remaining=123;
 if(c->mode&4){s->phase=-1;s->speed=-3;s->velocityX=-7;}if(c->mode&8)D_800BE9E4=0x13579BDF;
 if(c->mode&128){D_8008C9C8[(s32)s->callbackIndex]=0;s->callbackIndex=-1;}
 if(c->mode&512){s->texture=meta.bytes+64;meta.bytes[68]=3;}
}
static void cb0(SpriteFrameState*p){update((CompactSpriteState*)(void*)p,1);}static void cb1(SpriteFrameState*p){update((CompactSpriteState*)(void*)p,2);}
static void complete(CompactSpriteState*s,u32 target){observe(target,s);if(c->mode&256){s->remaining=99;s->flags=0xA55A;}}
static void end0(void*p){complete(p,3);}static void end1(void*p){complete(p,4);}
void func_1516972C(struct102*p){CompactSpriteState*s=(CompactSpriteState*)(void*)p;observe(5,s);if(c->mode&64){fill((u8*)s+8,4,0);((u8*)s)[0x40]^=0xA5;}}
static u32 state_hash(void){u32 h=2166136261u,i;record_hash(&h,&box.object);record_hash(&h,&other.object);
 for(i=0;i<96;i++)hash(&h,meta.bytes[i]);for(i=0;i<22;i++)hash(&h,D_8008C9C8[i]==cb0?1:D_8008C9C8[i]==cb1?2:0);for(i=0;i<11;i++)hash(&h,D_8008CA20[i]==end0?1:2);hash(&h,(u32)D_800BE9E4);return h;
}
void _start(void){u32 n,i,h;int result=0;
 for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){
  c=&rows[n];trace=2166136261u;calls=0;error=0;fill(box.before,16,0xD1);fill(box.after,16,0xD2);fill(other.before,16,0xD3);fill(other.after,16,0xD4);fill(meta.before,16,0xD5);fill(meta.after,16,0xD6);
  for(i=0;i<76;i++){((u8*)&box.object)[i]=c->initial[i];((u8*)&other.object)[i]=(u8)(i*13+0x310+7);}
  other.object.phase=23;other.object.speed=-1;other.object.x=17;other.object.y=19;other.object.z=21;other.object.velocityX=3;other.object.velocityZ=-2;other.object.velocityY=1;other.object.accelerationY=0;other.object.remaining=5;other.object.flags=2;
  other.object.fractionX=255;other.object.fractionZ=128;other.object.fractionY=1;other.object.callbackIndex=-1;other.object.fadeStep=0;other.object.alpha=144;other.object.completionIndex=-1;
  for(i=0;i<96;i++)meta.bytes[i]=(u8)(i*17+3);meta.bytes[36]=2;
  box.object.texture=c->alias?(u8*)&box.object+(c->alias==1?0x18:c->alias==2?0x19:0x1A):meta.bytes;other.object.texture=meta.bytes+32;
  if(!c->alias)meta.bytes[4]=(u8)c->frames;
  for(i=0;i<22;i++)D_8008C9C8[i]=c->callback?(i&1?cb1:cb0):0;for(i=0;i<11;i++)D_8008CA20[i]=i&1?end1:end0;
  D_800BE9E4=(s32)c->ticks;subject(&box.object);h=state_hash();
  for(i=0;i<16;i++)if(box.before[i]!=0xD1||box.after[i]!=0xD2||other.before[i]!=0xD3||other.after[i]!=0xD4||meta.before[i]!=0xD5||meta.after[i]!=0xD6)error++;
  if(h!=c->state||trace!=c->trace||calls!=c->calls||error){u32 diagnostic[8]={n,h,c->state,trace,c->trace,calls,c->calls,error};__asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(diagnostic),"d"(32));result=1;break;}
 }
 __asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
 return text,selected
def main():
 body=packet.MANIFEST['body'];text,selected=program(body);profiles={};controls_list=controls(body)
 def run(text,label,opt):
  p=out/(label+'.c');p.write_text(text);exe=out/(label+opt);cmd=native_command(opt)+['-fstrict-aliasing',str(p),'-o',str(exe)]
  q=subprocess.run(cmd,cwd=root,capture_output=True,text=True);assert q.returncode==0 and not q.stdout and not q.stderr,q.stdout+q.stderr
  return subprocess.run([str(exe)],capture_output=True,timeout=60)
 for opt in('-O0','-O2','-O3'):
  q=run(text,'native',opt);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,struct.unpack('<%dI'%(len(q.stderr)//4),q.stderr)if len(q.stderr)%4==0 else q.stderr)
  profiles[opt]=dict(cases=len(cases()),SDK32=True,strict_aliasing=True,UBSan=True)
 effective=[]
 for name,changed in controls_list.items():
  q=run(text.replace(selected,changed.replace('func_15167E0C(','subject(')), 'native-control-'+name,'-O2');assert q.returncode!=0,('Ineffective source control',name);effective.append(name)
 r=dict(profiles=profiles,effective_source_controls=effective,full_partial_records_metadata_tables_and_ordered_callback_traces=True,record_and_metadata_canaries=True,all_19_field_offsets_asserted=True,
  limits='Actual SDK32 types and measured partial compact record. Native update selectors -1/0..21 and completion selectors -1/0..10; incoming-home redirection remains guest-only. Byte aliases use explicit native little-endian fixtures.',source_installed=packet.installed(),matching_credit=0)
 (out/'native.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
