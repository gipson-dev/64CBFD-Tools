"""Actual SDK32 source, typed objects, exact state tapes and effective controls."""
from pathlib import Path
import json,struct,subprocess,sys
from tools.experiments import game_indexed_matrix_renderer_15168c4c_match as packet
r,o=packet.ROOT,packet.OUT
from tools.tests import game_indexed_matrix_renderer_15168c4c_guest as q
g=q.g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.game_remaining_donor_candidates import function_span
OFFSETS=set(range(0x10,0x90,4))|{0x90,0x94,0x98,0x9C,0xA0,0xA4,0xC0,0xC4,0xC8,0xD0}
def state_values(m):
 result=[];i=0
 while i<240:
  n=4 if i in OFFSETS else 1;result.append(g.get(m,q.STATE+i,n));i+=n
 return result
def command_values(m):return[g.get(m,q.OUTPUT+i*4)for i in range(128)]
def cache_values(m):return[m[g.SYMS['D_800BE9C0']],*[g.get(m,g.SYMS[n],2)for n in('D_800DD1C0','D_800DD1C2','D_800DD1C4','D_800DD1C6')],g.get(m,g.SYMS['D_800DD218']),g.get(m,g.SYMS['D_800DD21C'])]
def trace_values(log):
 result=[]
 for tag,args in log:result.extend([1 if tag=='matrix'else 2,*[0xF001 if a=='sync'else a for a in args]])
 return result
def controls(body):
 result={
 'missing-matrix-provider':body.replace('    func_15043D90(', '    if (0) func_15043D90(',1),
 'wrong-matrix-buffer':body.replace('&state->matrix[D_800BE9C0]', '&state->matrix[0]',1),
 'wrong-angle-arguments':body.replace('state->angles[0], state->angles[1], state->angles[2]','state->translation[0], state->translation[1], state->translation[2]'),
 'wrong-scale-argument':body.replace('state->scale[0], state->scale[1], state->scale[2]','state->scale[0], state->scale[0], state->scale[2]'),
 'missing-pipe-sync':body.replace('gDPPipeSync(output++);',';'),
 'wrong-primitive-alpha':body.replace('0, 0, 0, state->alpha);','0, 0, 0, 255);'),
 'wrong-alpha-cache':body.replace('D_800DD1C6 = state->alpha;','D_800DD1C6 = 0;'),
 'missing-cache-reset':body.replace('D_800DD1C2 = D_800DD1C4;',';'),
 'wrong-tile-origin':body.replace('G_TX_RENDERTILE, 2,','G_TX_RENDERTILE, 1,'),
 'wrong-tile-extent':body.replace('state->tileOffset, 126, 254','state->tileOffset, 125, 254'),
 'wrong-first-mode':body.replace('0x00552230','0x00552231'),
 'wrong-second-mode':body.replace('0x00504A50','0x00504A51'),
 'wrong-high-mode':body.replace('0x0008ACA0','0x0008ACA1'),
 'wrong-combine-gate':body.replace('state->combine == 1','state->combine != 1'),
 'wrong-combine-alpha':body.replace('PRIMITIVE, 0, SHADE, 0,','TEXEL0, 0, SHADE, 0,',1),
 'missing-display-list':body.replace('gSPDisplayList(output++, state->displayList);',';'),
 'wrong-return-cursor':body.replace('return output;','return output + 1;'),
 }
 marker='    IndexedMatrixRenderState *state = record;';stale=body.replace(marker,marker+'\n    u8 cachedBuffer = D_800BE9C0;');pos=stale.rindex('&state->matrix[D_800BE9C0]');stale=stale[:pos]+stale[pos:].replace('&state->matrix[D_800BE9C0]','&state->matrix[cachedBuffer]',1);result['stale-final-buffer']=stale
 assert all(v!=body for v in result.values());return result
def program():
 rows=q.cases();encoded=[];raw=g.bound_blob(*g.payload(o/'selected-final/candidate.o','func_15168C4C'),g.SYMS);retail=q.words('func_15168C4C')
 def arr(xs):return'{'+','.join('0x%Xu'%g.u32(v)for v in xs)+'}'
 for c in rows:
  initial=q.fixture(c);expected,log,value=q.reference(initial,c)
  for ws in(raw,retail):
   m=q.Oracle(ws,initial,c).run();assert(g.public(m.memory),m.log,m.r[2])==(g.public(expected),log,value),c
  encoded.append('{'+','.join((str(c.effect),str(c.view),arr(state_values(initial)),arr(cache_values(initial)),arr(state_values(expected)),arr(command_values(expected)),arr(cache_values(expected)),arr(trace_values(log)),str((value-q.OUTPUT)//8),str(c.pattern)))+'}')
 initial_count=len(state_values(q.fixture(q.Case())));assert initial_count==114
 source=(o/'baseline/conker/src/game_16EE20.c').read_text();assert source.count('Gfx *func_15142FBC(')==1
 # The existing span helper recognizes void*, not Gfx*. Mask only that
 # equal-length return token for locating the unchanged original body.
 masked=source.replace('Gfx *func_15142FBC(','void*func_15142FBC(',1);assert len(masked)==len(source)
 lo,hi=function_span(masked,'func_15142FBC');mode=source[lo:hi].replace('func_15142FBC(','mode_actual(')
 upstream=(o/'additional-baseline/conker/src/game/generated_19E040.c').read_text();begin=upstream.index('typedef struct DebrisPacket19E040 {');end=upstream.index('} DebrisPacket19E040;',begin)+len('} DebrisPacket19E040;');packet=upstream[begin:end]
 text='#include <ultra64.h>\n'+packet+'\n'+(o/'selected-final/declarations.c').read_text()+r'''
struct Case{u32 effect;s32 view;u32 initial[114],cache[7],expected[114],commands[128],expectedCache[7],trace[16],cursor,pattern;};
static const struct Case cases[]={ROWS};
static const struct Case *c;
static struct{u8 before[16];IndexedMatrixRenderState value;u8 after[16];}record;
static struct{u8 before[16];Gfx value[64];u8 after[16];}commands;
static struct{u8 before[16];u8 buffer,reserved[3];s16 color[4];u32 high,low;u8 after[16];}cache;
#define D_800BE9C0 cache.buffer
#define D_800DD1C0 cache.color[0]
#define D_800DD1C2 cache.color[1]
#define D_800DD1C4 cache.color[2]
#define D_800DD1C6 cache.color[3]
#define D_800DD218 cache.high
#define D_800DD21C cache.low
_Static_assert(sizeof(void*)==4&&sizeof(long)==4&&sizeof(Gfx)==8&&sizeof(Mtx)==64,"SDK32 widths");
_Static_assert(sizeof(IndexedMatrixRenderState)==240,"record extent");
#define CHECK(f,n) _Static_assert(__builtin_offsetof(IndexedMatrixRenderState,f)==n,"record "#f)
CHECK(matrix,0x10);CHECK(translation,0x90);CHECK(angles,0x9C);CHECK(scale,0xC0);
CHECK(displayList,0xD0);CHECK(alpha,0xE5);CHECK(tileOffset,0xE6);CHECK(mode,0xEC);CHECK(combine,0xED);
_Static_assert(sizeof(DebrisPacket19E040)==96,"constructor packet extent");
#define COPYCHECK(a,b) _Static_assert(__builtin_offsetof(IndexedMatrixRenderState,a)==0x90+__builtin_offsetof(DebrisPacket19E040,b),"copied "#a)
COPYCHECK(translation,position);COPYCHECK(angles,rotation);COPYCHECK(scale,scale);COPYCHECK(displayList,asset);
COPYCHECK(alpha,alpha);COPYCHECK(tileOffset,zero56);COPYCHECK(mode,control5C);COPYCHECK(combine,control5D);
static u32 trace[16],traceCount,error;
static u32 word(f32 f){union{u32 u;f32 f;}x;x.f=f;return x.u;}
static u32 identity(const void*p){u32 a=(u32)p,base=(u32)&record.value,end=base+240;if(a>=base&&a<end)return STATE+(a-base);base=(u32)commands.value;end=base+512;if(a>=base&&a<end)return OUTPUT+(a-base);error=2;return a;}
static void append(u32 x){if(traceCount<16)trace[traceCount]=x;else error=3;traceCount++;}
void func_15043D90(Mtx*m,f32 a,f32 b,f32 d,f32 e,f32 f,f32 h,f32 j,f32 k,f32 l){
 u32 args[10]={identity(m),word(a),word(b),word(d),word(e),word(f),word(h),word(j),word(k),word(l)},i;
 append(1);for(i=0;i<10;i++)append(args[i]);
 for(i=0;i<16;i++)m->m[i/4][i%4]=(long)(0x4D000000u^args[1+i%9]^(i*0x01010101u));
 if(c->effect&1)D_800BE9C0^=1;
 if(c->effect&2){record.value.alpha^=0x5A;record.value.tileOffset^=0x3F;record.value.mode=record.value.mode==1?2:1;}
 if(c->effect&4){record.value.combine=record.value.combine!=1;record.value.displayList=(Gfx*)0x80123458u;}
 if(c->effect&8){D_800DD1C0=D_800DD1C2=D_800DD1C4=D_800DD1C6=0x4321;}
}
MODE
Gfx *func_15142FBC(Gfx*output,u32 high,u32 low,u8*sync){
 append(2);append(identity(output));append(high);append(low);append(0xF001);if(*sync!=0)error=4;
 return mode_actual(output,high,low,sync);
}
BODY
static Gfx*(*volatile invoke)(Gfx*,void*,s16)=subject;
static u32 numeric(u32 i){return(i>=0x10&&i<0x90&&i%4==0)||(i>=0x90&&i<0xA8&&i%4==0)||(i>=0xC0&&i<0xCC&&i%4==0)||i==0xD0;}
static void load_record(void){u32 i=0,j=0,v;u8*p=(u8*)&record.value;while(i<240){v=c->initial[j++];if(numeric(i)){__builtin_memcpy(p+i,&v,4);i+=4;}else p[i++]=(u8)v;}if(j!=114)error=5;}
static int check_record(void){u32 i=0,j=0,v;u8*p=(u8*)&record.value;while(i<240){if(numeric(i)){__builtin_memcpy(&v,p+i,4);i+=4;}else v=p[i++];if(v!=c->expected[j++])return 0;}return j==114;}
static int run(void){u32 row,i,v,gotCache[7];Gfx*answer;u8*p;
 for(row=0;row<sizeof(cases)/sizeof(cases[0]);row++){
  c=&cases[row];traceCount=error=0;
  for(i=0;i<16;i++)record.before[i]=record.after[i]=commands.before[i]=commands.after[i]=cache.before[i]=cache.after[i]=0xA5;
  for(i=0;i<3;i++)cache.reserved[i]=0xA5;
  load_record();p=(u8*)commands.value;for(i=0;i<128;i++){u32 j;v=0;for(j=0;j<4;j++)v=(v<<8)|(u8)((i*4+j)*13+c->pattern*23+0x5A);__builtin_memcpy(p+i*4,&v,4);}
  cache.buffer=(u8)c->cache[0];for(i=0;i<4;i++)cache.color[i]=(s16)c->cache[1+i];cache.high=c->cache[5];cache.low=c->cache[6];
  answer=invoke(commands.value,&record.value,(s16)c->view);
  if(error||answer!=commands.value+c->cursor||traceCount!=16||!check_record())return 1;
  for(i=0;i<16;i++)if(trace[i]!=c->trace[i])return 1;
  for(i=0;i<64;i++){v=commands.value[i].words.w1;if(commands.value[i].words.w0==0xDA380003u)v=identity((void*)v);if(commands.value[i].words.w0!=c->commands[i*2]||v!=c->commands[i*2+1])return 1;}
  gotCache[0]=cache.buffer;for(i=0;i<4;i++)gotCache[1+i]=(u16)cache.color[i];gotCache[5]=cache.high;gotCache[6]=cache.low;
  for(i=0;i<7;i++)if(gotCache[i]!=c->expectedCache[i])return 1;
  for(i=0;i<3;i++)if(cache.reserved[i]!=0xA5)return 1;
  for(i=0;i<16;i++)if(record.before[i]!=0xA5||record.after[i]!=0xA5||commands.before[i]!=0xA5||commands.after[i]!=0xA5||cache.before[i]!=0xA5||cache.after[i]!=0xA5)return 1;
 }
 return 0;
}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
 body=(o/'selected-final/body.c').read_text().replace('func_15168C4C(','subject(')
 text=text.replace('ROWS',',\n'.join(encoded)).replace('STATE',hex(q.STATE)+'u').replace('OUTPUT',hex(q.OUTPUT)+'u').replace('MODE',mode).replace('BODY',body)
 return text,body,len(rows)
def main():
 text,body,count=program();profiles={}
 def run(src,label,opt):
  p=o/(label+'.c');p.write_text(src);exe=o/(label+opt);cmd=native_command(opt)+['-fstrict-aliasing','-Wno-maybe-uninitialized',str(p),'-o',str(exe)]
  result=subprocess.run(cmd,cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_text(result.stdout+result.stderr);assert result.returncode==0,(label,result.stdout+result.stderr)
  return subprocess.run([str(exe)],capture_output=True,timeout=60)
 for opt in(('-O0',)if '--first'in sys.argv else('-O0','-O2','-O3')):
  result=run(text,'native',opt);assert result.returncode==0 and not result.stdout and not result.stderr,(opt,result.returncode,result.stdout,result.stderr)
  profiles[opt]=dict(cases=count,SDK32=True,strict_aliasing=True,UBSan=True)
 effective=[]
 if '--first'not in sys.argv:
  for name,changed in controls((o/'selected-final/body.c').read_text()).items():
   result=run(text.replace(body,changed.replace('func_15168C4C(','subject(')),'native-control-'+name,'-O2');assert result.returncode==1,('Ineffective or trap-only source control',name,result.returncode,result.stderr);effective.append(name)
 report=dict(profiles=profiles,effective_source_controls=effective,all_240_record_bytes_opaque_and_numeric_and_512_command_bytes_compared=True,cache_and_ordered_helper_arguments_and_cursor_compared=True,SDK_offsets_asserted=True,record_output_cache_canaries=True,source_installed=packet.installed(),matching_credit=0,limits='Complete actual SDK32 renderer and actual semantic mode helper with bounded matrix provider; defined post-provider modes1/2 only, finite transported float bits. No native equivalence for retail uninitialized mode0/other modes or FCSR/rotation/hardware/gameplay claim.')
 (o/('native-first.json'if '--first'in sys.argv else'native.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
