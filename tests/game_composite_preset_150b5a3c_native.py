"""Native32 union storage, canonical packet/public bytes and effective controls."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
sys.path.insert(0,str(Path.cwd()));
from tools.tests import game_composite_preset_150b5a3c_guest as g
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.experiments import game_composite_preset_150b5a3c_match as p
def main():
 r,o=p.ROOT,p.OUT;source=p.MANIFEST['selected_source'];lo,hi=function_span(source,'func_150B5A3C');body=source[lo:hi]
 def declaration(name):
  end=source.index('} '+name+';')+len('} '+name+';');start=source.rfind('typedef ',0,end);return source[start:end]
 types='\n'.join(declaration(n)for n in['CompositeEffectPosition','CompositePositionStorage150B5A3C','CompositeEffectInput'])
 rows=[];corpus=[c for c in g.cases()if not c.ghost_homes]
 def canonical_public(m):return g.data(m,g.POINT,12)+g.data(m,g.ALT,12)+b''.join(g.data(m,a,4)for a in g.COEFF)+g.data(m,g.MARK,16)
 def cs(values):return '{'+','.join(str(v)for v in values)+'}'
 for c in corpus:
  initial=g.fixture(c);end,calls,obs,fcsr,value=g.reference(initial,c)
  rows.append('{'+','.join([cs(c.coords),cs(g.coefficient_words()),str(c.mode),str(g.u32(c.extra))+'u',str(c.seed),str(c.mutation),str(c.rm),cs(obs[0][1]),'{'+','.join(cs(canonical_public(q[0]))for q in obs)+','+cs(canonical_public(end))+'}'])+'}')
 vectors='typedef struct {u32 position[3],coeff[3],mode,extra,seed,mutation,rm;u8 packet[116],observed[4][52];} Row;\nstatic const Row rows[]={\n'+',\n'.join(rows)+'\n};\n';(o/'native-vectors.h').write_text(vectors)
 prefix='''typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;
 typedef short s16;typedef int s32;typedef unsigned int u32;typedef float f32;
 '''+types+'''
 f32 D_8009FCA0,D_8009FCA4,D_8009FCA8;
 void func_15152B38(CompositeEffectInput *,u8,s32);
 s32 func_150B5E34();
 void func_150B6000(f32 *,u8,s32);
 typedef char assert_Input116[sizeof(CompositeEffectInput)==116?1:-1];
 typedef char assert_Position12[sizeof(CompositePositionStorage150B5A3C)==12?1:-1];
 typedef char assert_position08[__builtin_offsetof(CompositeEffectInput,position)==8?1:-1];
 typedef char assert_fixed44[__builtin_offsetof(CompositeEffectInput,fixed44)==0x44?1:-1];
 typedef char assert_field5C[__builtin_offsetof(CompositeEffectInput,field5C)==0x5C?1:-1];
 typedef char assert_field6C[__builtin_offsetof(CompositeEffectInput,field6C)==0x6C?1:-1];
 typedef char assert_tail72[__builtin_offsetof(CompositeEffectInput,privateTail72)==0x72?1:-1];
 '''
 suffix=r'''
 static CompositePositionStorage150B5A3C live,alternate;
 static u8 marker[16];static u32 bad,callIndex;static const Row *current;
 static u32 get32(const void *p){const u8 *b=p;return (u32)b[0]|((u32)b[1]<<8)|((u32)b[2]<<16)|((u32)b[3]<<24);}
 static void put32(void *p,u32 v){u8 *b=p;b[0]=(u8)v;b[1]=(u8)(v>>8);b[2]=(u8)(v>>16);b[3]=(u8)(v>>24);}
 static void big(u8 *p,u32 v){p[0]=(u8)(v>>24);p[1]=(u8)(v>>16);p[2]=(u8)(v>>8);p[3]=(u8)v;}
 static u32 mxcsr(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v));return v;}
 static u32 expectedCSR(u32 phase){static const u32 map[4]={0,3,2,1};return 0x1f80u|(map[current->rm]<<13)|(phase?1u<<(phase-1):0);}
 static void setCSR(u32 value){__asm__ volatile("ldmxcsr %0"::"m"(value));}
 static void publicBytes(u8 *out){u32 i;for(i=0;i<3;i++)big(out+4*i,get32(&live.array[i]));for(i=0;i<3;i++)big(out+12+4*i,get32(&alternate.array[i]));big(out+24,get32(&D_8009FCA0));big(out+28,get32(&D_8009FCA4));big(out+32,get32(&D_8009FCA8));big(out+36,get32(marker));for(i=4;i<16;i++)out[36+i]=marker[i];}
 static u32 hole(u32 i){return i==89||i==90||i==91||i==107;}
 static u8 packetByte(const u8 *p,u32 at){
  static const u32 words[16]={0,4,8,12,16,20,24,28,32,36,40,52,56,92,96,108};
  static const u32 halves[10]={44,46,48,50,60,62,64,100,102,104};u32 j;
  for(j=0;j<16;j++)if(at>=words[j]&&at<words[j]+4)return p[words[j]+3-(at-words[j])];
  for(j=0;j<10;j++)if(at>=halves[j]&&at<halves[j]+2)return p[halves[j]+1-(at-halves[j])];
  return p[at];
 }
 static void boundary(u32 id,u32 mode,u32 extra){u32 i;u8 actual[52];
  if(id!=callIndex||mode!=current->mode||extra!=current->extra||mxcsr()!=expectedCSR(callIndex))bad=1;
  publicBytes(actual);for(i=0;i<52;i++)if(actual[i]!=current->observed[callIndex][i])bad=1;
  put32(marker,get32(marker)+1);
 }
 void func_15152B38(CompositeEffectInput *input,u8 mode,s32 extra){u32 i;u8 *p=(u8 *)input;boundary(0,mode,(u32)extra);
  for(i=0;i<116;i++)if(!hole(i)&&packetByte(p,i)!=current->packet[i])bad=1;
  if(current->mutation&1){put32(&live.array[0],0xc0900000u);put32(&live.array[1],0x40c80000u);put32(&live.array[2],0xc1000000u);}
  if(current->mutation&2){put32(&D_8009FCA0,0x40000000u);put32(&D_8009FCA4,0xc0400000u);put32(&D_8009FCA8,0x40800000u);}
  if(current->mutation&4)for(i=0;i<116;i++)p[i]=(u8)(i*7+current->seed*11+0x31);
  callIndex++;setCSR(expectedCSR(callIndex));
 }
 s32 func_150B5E34(f32 *position,s32 mode,s32 extra){boundary(1,(u32)mode,(u32)extra);if(position!=live.array)bad=1;if(current->mutation&8)put32(&position[2],0xc1180000u);callIndex++;setCSR(expectedCSR(callIndex));return (s32)0x87654321u;}
 void func_150B6000(f32 *position,u8 mode,s32 extra){boundary(2,mode,(u32)extra);if(position!=live.array)bad=1;callIndex++;setCSR(expectedCSR(callIndex));}
 static s32 main(void){u32 row,i;u8 actual[52];
  for(row=0;row<sizeof(rows)/sizeof(rows[0]);row++){
   current=&rows[row];callIndex=0;bad=0;
   for(i=0;i<3;i++){put32(&live.array[i],current->position[i]);put32(&alternate.array[i],current->position[i]);}
   put32(&D_8009FCA0,current->coeff[0]);put32(&D_8009FCA4,current->coeff[1]);put32(&D_8009FCA8,current->coeff[2]);
   for(i=0;i<16;i++)marker[i]=(u8)(i*29+current->seed*11+0x5a);put32(marker,0);setCSR(expectedCSR(0));
   func_150B5A3C(&live,(u8)current->mode,(s32)current->extra);
   if(callIndex!=3||mxcsr()!=expectedCSR(3))bad=1;publicBytes(actual);for(i=0;i<52;i++)if(actual[i]!=current->observed[3][i])bad=1;
   if(bad)return 42;
  }
  return 0;
 }
 __attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 code=main();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
 '''
 basecmd=['cc','-m32','-std=gnu99','-ffreestanding','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-misleading-indentation']
 def run(name,text,opt,expected):
  c=o/(name+'.c');exe=o/(name+'.exe');c.write_text(prefix+text+'\n'+vectors+suffix);cmd=[*basecmd,opt,str(c),'-o',str(exe)];p=subprocess.run(cmd,capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0,(name,p.stderr);p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==expected,(name,p.returncode,p.stdout,p.stderr);return dict(comparison_exit=p.returncode,source_sha256=hashlib.sha256(c.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),command=cmd)
 profiles={opt:run('native-'+opt,body,'-'+opt,0)for opt in('O0','O2','O3')}
 mutations=[('count','packet.baseCount=5;','packet.baseCount=6;'),('range','packet.countRange=5;','packet.countRange=6;'),('color','packet.byteBase46=255;','packet.byteBase46=254;'),('fixed-control','packet.fixed44=3;','packet.fixed44=4;'),('resource','packet.field5C=0x200005;','packet.field5C=0x200004;'),('radius','packet.radiusBase=39.0f;','packet.radiusBase=38.0f;'),('tail','((s8 *)packet.privateTail72)[1]=-1;','((s8 *)packet.privateTail72)[1]=1;'),('mode','func_15152B38(&packet,mode,extra);','func_15152B38(&packet,mode^1,extra);'),('extra','func_150B6000(position->array,mode,extra);','func_150B6000(position->array,mode,extra^1);'),('omit-companion','    func_150B5E34(position->array,mode,extra);\n',''),('wrong-position','packet.position=position->vector;','packet.position=position->vector; packet.position.z=position->vector.x;')]
 controls=[]
 for name,old,new in mutations:
  assert body.count(old)==1,(name,old);result=run('native-control-'+name,body.replace(old,new),'-O2',42);controls.append(dict(name=name,**result))
 q=dict(cases_per_profile=len(corpus),profiles=profiles,effective_source_controls=controls,comparison_exit42_only=True,no_signal_or_UBSan_trap_counted=True,strict_aliasing_and_UBSan=True,native_union_size=12,native_packet_size=116,observed_initialized_packet_bytes=112,unspecified_packet_bytes_excluded=4,canonical_public_bytes=52,all256_mode_bytes=True,all_four_rounding_modes=True,FP_status_preserved_between_providers=True,no_private_inspection_without_passed_pointer=True,ghost_home_cases_excluded=True,source_installed=p.installed(),matching_credit=0)
 (o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k not in('profiles','effective_source_controls')}),flush=True)
 return q
if __name__=='__main__':main()
