"""Run actual selected C in three native32 translation units with LTO ABI checks."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
sys.path.insert(0,str(Path.cwd()));pass
from tools.tests import game_sibling_preset_150b5c38_guest as g
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.experiments import game_sibling_preset_150b5c38_match as p
HARNESS='\n static CompositePositionStorage150B5A3C live,alternate;\n static CompositePositionStorage150B5A3C *livePointer;\n static struct127 actor,otherActor; static struct255 matrix;static u32 producerMode,transformCalls;static u8 finalSnapshot[56];\n static u8 marker[16];static u32 bad,callIndex;static const Row *current;\n static u32 get32(const void *p){const u8 *b=p;return (u32)b[0]|((u32)b[1]<<8)|((u32)b[2]<<16)|((u32)b[3]<<24);}\n static void put32(void *p,u32 v){u8 *b=p;b[0]=(u8)v;b[1]=(u8)(v>>8);b[2]=(u8)(v>>16);b[3]=(u8)(v>>24);}\n static void big(u8 *p,u32 v){p[0]=(u8)(v>>24);p[1]=(u8)(v>>16);p[2]=(u8)(v>>8);p[3]=(u8)v;}\n static u32 mxcsr(void){u32 v;__asm__ volatile("stmxcsr %0":"=m"(v));return v;}\n static u32 expectedCSR(u32 phase){static const u32 map[4]={0,3,2,1};return 0x1f80u|(map[current->rm]<<13)|(phase?1u<<(phase-1):0);}\n static void setCSR(u32 value){__asm__ volatile("ldmxcsr %0"::"m"(value));}\n static void publicBytes(u8 *out){u32 i;for(i=0;i<3;i++)big(out+4*i,get32(&livePointer->array[i]));for(i=0;i<3;i++)big(out+12+4*i,get32(&alternate.array[i]));big(out+24,get32(&D_8009FCAC));big(out+28,get32(&D_8009FCB0));big(out+32,get32(&D_8009FCB4));big(out+36,get32(&D_8009FCB8));big(out+40,get32(marker));for(i=4;i<16;i++)out[40+i]=marker[i];}\n static u32 hole(u32 i){return i==89||i==90||i==91||i==107;}\n static u8 packetByte(const u8 *p,u32 at){\n  static const u32 words[16]={0,4,8,12,16,20,24,28,32,36,40,52,56,92,96,108};\n  static const u32 halves[10]={44,46,48,50,60,62,64,100,102,104};u32 j;\n  for(j=0;j<16;j++)if(at>=words[j]&&at<words[j]+4)return p[words[j]+3-(at-words[j])];\n  for(j=0;j<10;j++)if(at>=halves[j]&&at<halves[j]+2)return p[halves[j]+1-(at-halves[j])];\n  return p[at];\n }\n static void boundary(u32 id,u32 mode,u32 extra){u32 i;u8 actual[56];\n  if(id!=callIndex||mode!=(producerMode?255:current->mode)||extra!=(producerMode?1:current->extra)||mxcsr()!=expectedCSR(callIndex))bad=1;\n  publicBytes(actual);for(i=0;i<56;i++)if(actual[i]!=current->observed[callIndex][i])bad=1;\n  put32(marker,get32(marker)+1);\n }\n void func_15152B38(CompositeEffectInput *input,u8 mode,s32 extra){u32 i;u8 *p=(u8 *)input;boundary(0,mode,(u32)extra);\n  for(i=0;i<116;i++)if(!hole(i)&&packetByte(p,i)!=current->packet[i])bad=1;\n  if(current->mutation&1){put32(&livePointer->array[0],0xc0900000u);put32(&livePointer->array[1],0x40c80000u);put32(&livePointer->array[2],0xc1000000u);}\n  if(current->mutation&2){put32(&D_8009FCAC,0x40000000u);put32(&D_8009FCB0,0xc0400000u);put32(&D_8009FCB4,0x40800000u);put32(&D_8009FCB8,0xc0a00000u);}\n  if(current->mutation&4)for(i=0;i<116;i++)p[i]=(u8)(i*7+current->seed*11+0x31);\n  callIndex++;setCSR(expectedCSR(callIndex));\n }\n void *func_150B5E34(CompositePositionStorage150B5A3C *storage,u8 mode,s32 extra){f32 *position=storage->array;boundary(1,(u32)mode,(u32)extra);if(storage!=livePointer)bad=1;if(current->mutation&8)put32(&position[2],0xc1180000u);callIndex++;setCSR(expectedCSR(callIndex));return (void *)0x87654321u;}\n void func_150B6000(f32 *position,u8 mode,s32 extra){boundary(2,mode,(u32)extra);if(position!=livePointer->array)bad=1;callIndex++;setCSR(expectedCSR(callIndex));publicBytes(finalSnapshot);}\n\n void func_150B60E0(u8 *source,f32 *position){u32 i;transformCalls++;\n  if(source!=(u8 *)&actor)bad=1;livePointer=(CompositePositionStorage150B5A3C *)position;\n  for(i=0;i<3;i++)put32(&position[i],current->position[i]);\n  D_800D154C=&otherActor;\n }\n static void setup(u32 row,u32 useProducer){u32 i;current=&rows[row];producerMode=useProducer;callIndex=bad=transformCalls=0;livePointer=&live;\n  for(i=0;i<3;i++){put32(&live.array[i],current->position[i]);put32(&alternate.array[i],current->position[i]);}\n  put32(&D_8009FCAC,current->coeff[0]);put32(&D_8009FCB0,current->coeff[1]);put32(&D_8009FCB4,current->coeff[2]);put32(&D_8009FCB8,current->coeff[3]);\n  for(i=0;i<16;i++)marker[i]=(u8)(i*29+current->seed*11+0x5a);put32(marker,0);setCSR(expectedCSR(0));D_800D154C=&actor;\n }\n static s32 main(void){u32 row,i,attached,flag,active;\n  for(row=0;row<sizeof(rows)/sizeof(rows[0]);row++){\n   setup(row,0);func_150B5C38(&live,(u8)current->mode,(s32)current->extra);\n   if(callIndex!=3||mxcsr()!=expectedCSR(3))bad=1;\n   for(i=0;i<56;i++)if(finalSnapshot[i]!=current->observed[3][i])bad=1;if(bad)return 42;\n   for(attached=0;attached<2;attached++){\n    setup(row,1);flag=row&255;actor.unk74=(u8)flag;actor.unk1D4=attached?&matrix:(struct255 *)0;active=attached&&((flag&15)!=15);\n    func_15071690((s32)row);livePointer=0;\n    if(transformCalls!=active||callIndex!=(active?3u:0u)||mxcsr()!=expectedCSR(active?3:0))bad=1;\n    if(active){if(D_800D154C!=&otherActor)bad=1;for(i=0;i<56;i++)if(finalSnapshot[i]!=current->observed[3][i])bad=1;}\n    else if(D_800D154C!=&actor)bad=1;\n    if(bad)return 42;\n   }\n  }\n  return 0;\n }\n __attribute__((force_align_arg_pointer,noreturn))void _start(void){s32 code=main();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}\n '
def main():
 r,o=p.ROOT,p.OUT
 def extract(source,name):
  a,b=function_span(source,name);return source[a:b]
 source=p.MANIFEST['selected_source'];producer=p.MANIFEST['selected_producer_source']
 body=extract(source,'func_150B5C38');parent=extract(producer,'func_15071690')
 def declaration(name):
  end=source.index('} '+name+';')+len('} '+name+';');start=source.rfind('typedef ',0,end);return source[start:end]
 types='\n'.join(declaration(n)for n in ['CompositeEffectPosition','CompositePositionStorage150B5A3C','CompositeEffectInput'])
 actor=(o/'baseline/conker/include/structs.h').read_text();actor=re.sub(r'/\*.*?\*/|//[^\n]*','',actor,flags=re.S);start=actor.index('struct struct127 {');at=actor.index('{',start)+1;depth=1
 while depth:
  depth+=(actor[at]=='{')-(actor[at]=='}');at+=1
 actor=actor[start:at]+';'
 matrix_type=(o/'baseline/conker/include/structs.h').read_text();matrix_type=re.sub(r'/\*.*?\*/|//[^\n]*','',matrix_type,flags=re.S);start=matrix_type.index('struct struct255 {');at=matrix_type.index('};',start)+2;matrix_type=matrix_type[start:at];tags=sorted(set(re.findall(r'\bstruct\d+\b',actor+matrix_type)))
 header='''typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef short s16;
 typedef int s32;typedef unsigned int u32;typedef float f32;typedef double f64;
 '''+''.join('typedef struct '+t+' '+t+';\n'for t in tags)+types+'\n'+actor+'\n'+matrix_type+'''
 extern f32 D_8009FCAC,D_8009FCB0,D_8009FCB4,D_8009FCB8;
 extern struct127 *D_800D154C;
 void func_15152B38(CompositeEffectInput *,u8,s32);
 void *func_150B5E34(CompositePositionStorage150B5A3C *,u8,s32);
 void func_150B6000(f32 *,u8,s32);
 void func_150B60E0(u8 *,f32 *);
 void func_150B5C38(CompositePositionStorage150B5A3C *,u8,s32);
 void func_15071690(s32);
 typedef char size_input[sizeof(CompositeEffectInput)==116?1:-1];
 typedef char size_position[sizeof(CompositePositionStorage150B5A3C)==12?1:-1];
 typedef char size_actor[sizeof(struct127)==0x32c?1:-1];
 typedef char actor_flag[__builtin_offsetof(struct127,unk74)==0x74?1:-1];
 typedef char actor_matrix[__builtin_offsetof(struct127,unk1D4)==0x1d4?1:-1];
 '''
 spans=[('baseCount',0,4),('countRange',4,4),('position',8,12),('field14Base',0x14,4),('field18Range',0x18,4),('field1CBase',0x1c,4),('field20Range',0x20,4),('radiusBase',0x24,4),('radiusRange',0x28,4),('firstBase',0x2c,2),('firstRange',0x2e,2),('secondBase',0x30,2),('secondRange',0x32,2),('headerByteBase',0x34,4),('headerByteRange',0x38,4),('headerShortBase',0x3c,2),('headerShortRange',0x3e,2),('field40',0x40,2)]
 spans +=[(name,0x42+i,1)for i,name in enumerate(('fixed42','fixed43','fixed44','byteBase45','byteBase46','byteBase47','byteBase48','byteRange49','byteRange4A','byteRange4B','byteRange4C','byteBase4D','byteBase4E','byteBase4F','byteBase50','byteRange51','byteRange52','byteRange53','byteRange54','byteBase55','byteRange56','fixed57','fixed58'))]
 spans +=[('padding59',0x59,3),('field5C',0x5c,4),('field60',0x60,4),('field64',0x64,2),('field66',0x66,2),('field68',0x68,2),('field6A',0x6a,1),('padding6B',0x6b,1),('field6C',0x6c,4),('field70',0x70,1),('field71',0x71,1),('privateTail72',0x72,2)]
 assert sorted(at+i for name,at,n in spans for i in range(n))==list(range(116))
 for name,at,n in spans:header+=f'typedef char offset_{name}[__builtin_offsetof(CompositeEffectInput,{name})=={at}?1:-1];\ntypedef char width_{name}[sizeof(((CompositeEffectInput *)0)->{name})=={n}?1:-1];\n'
 for name in ('vector','array'):header+=f'typedef char union_{name}_at0[__builtin_offsetof(CompositePositionStorage150B5A3C,{name})==0?1:-1];\n'
 for name,at in [('x',0),('y',4),('z',8)]:header+=f'typedef char vector_{name}_at{at}[__builtin_offsetof(CompositeEffectPosition,{name})=={at}?1:-1];\n'
 header+='typedef char matrix_size[sizeof(struct255)==0x244?1:-1];\n'
 (o/'native-shared.h').write_text(header)
 def cs(values):return '{'+','.join(str(v)for v in values)+'}'
 def canonical(m):return g.data(m,g.POINT,12)+g.data(m,g.ALT,12)+b''.join(g.data(m,a,4)for a in g.COEFF)+g.data(m,g.MARK,16)
 corpus=[c for c in g.cases()if not c.ghost_homes];rows=[]
 nonvacuity=dict(coefficients_differ=g.coefficient_words()[0]!=g.coefficient_words()[1],position_x_z_differ=any(c.coords[0]!=c.coords[2]for c in corpus),producer_gate_rows_14_15=all(any(i&15==v for i in range(len(corpus)))for v in(14,15)))
 assert all(nonvacuity.values()),nonvacuity
 for c in corpus:
  initial=g.fixture(c);end,calls,obs,fcsr,value=g.reference(initial,c)
  rows.append('{'+','.join([cs(c.coords),cs(g.coefficient_words()),str(c.mode),str(g.u32(c.extra))+'u',str(c.seed),str(c.mutation),str(c.rm),cs(obs[0][1]),'{'+','.join(cs(canonical(q[0]))for q in obs)+','+cs(canonical(end))+'}'])+'}')
 vectors='typedef struct {u32 position[3],coeff[4],mode,extra,seed,mutation,rm;u8 packet[116],observed[4][56];} Row;\nstatic const Row rows[]={\n'+',\n'.join(rows)+'\n};\n'
 (o/'native-vectors.h').write_text(vectors)
 harness='#include "native-shared.h"\nf32 D_8009FCAC,D_8009FCB0,D_8009FCB4,D_8009FCB8;struct127 *D_800D154C;\n'+vectors+HARNESS
 (o/'native-harness.c').write_text(harness)
 base=['cc','-m32','-std=gnu99','-ffreestanding','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-msse2','-mfpmath=sse','-ffp-contract=off','-fexcess-precision=standard','-fstrict-aliasing','-fsanitize=undefined','-fno-sanitize-recover=all','-fsanitize-undefined-trap-on-error','-flto','-Werror=lto-type-mismatch','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-misleading-indentation']
 def run(name,target,caller,opt,expected):
  files=[]
  for tag,text in [('target',target),('producer',caller)]:
   f=o/(name+'-'+tag+'.c');f.write_text('#include "native-shared.h"\n'+text+'\n');files.append(f)
  exe=o/(name+'.exe');cmd=[*base,opt,*map(str,files),str(o/'native-harness.c'),'-o',str(exe)]
  p=subprocess.run(cmd,capture_output=True,text=True);(o/(name+'-compile.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0,(name,p.stderr)
  p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==expected,(name,p.returncode,p.stdout,p.stderr)
  return dict(comparison_exit=p.returncode,command=cmd,translation_unit_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest()for f in [*files,o/'native-harness.c',o/'native-shared.h']},binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest())
 profiles={opt:run('native-'+opt,body,parent,'-'+opt,0)for opt in ('O0','O2','O3')}
 mutations=[('count','packet.baseCount=13;','packet.baseCount=14;'),('range','packet.countRange=8;','packet.countRange=9;'),('color','packet.byteBase47=180;','packet.byteBase47=181;'),('resource','packet.field5C=0x200005;','packet.field5C=0x200004;'),('radius','packet.radiusBase=152.0f;','packet.radiusBase=151.0f;'),('coefficient','packet.field14Base=D_8009FCAC;','packet.field14Base=D_8009FCB0;'),('mode','func_15152B38(&packet,mode,extra);','func_15152B38(&packet,mode^1,extra);'),('extra','func_150B6000(position->array,mode,extra);','func_150B6000(position->array,mode,extra^1);'),('omit-companion','    func_150B5E34(position,mode,extra);\n',''),('position','packet.position=position->vector;','packet.position=position->vector; packet.position.z=position->vector.x;')]
 controls=[]
 for name,old,new in mutations:
  assert body.count(old)==1,name;controls.append(dict(name=name,**run('control-'+name,body.replace(old,new),parent,'-O2',42)))
 for name,old,new in [('producer-gate','!= 0xF','!= 0xE'),('producer-mode','&position, 0xFF, 1','&position, 0xFE, 1'),('producer-context','&position, 0xFF, 1','&position, 0xFF, 2')]:
  assert parent.count(old)==1,name;controls.append(dict(name=name,**run('control-'+name,body,parent.replace(old,new),'-O2',42)))
 q=dict(cases_per_profile=len(corpus),direct_target_calls_per_profile=len(corpus),producer_invocations_per_profile=2*len(corpus),profiles=profiles,effective_controls=controls,translation_units=3,full_actual_SDK_actor_size=0x32c,genuine_position_bytes=12,packet_bytes=116,known_packet_bytes=112,unspecified_packet_bytes=4,canonical_public_bytes=56,all256_mode_and_producer_flag_bytes=True,strict_aliasing=True,UBSan_trap=True,LTO_type_mismatch_errors=True,escaped_position_observed_only_during_producer_lifetime=True,comparison_exit42_only=True,no_signal_or_trap_counted=True,source_installed=p.installed(),matching_credit=0)
 q.update(complete_packet_field_offsets_and_widths_pinned=len(spans),union_both_member_offsets_zero_pinned=True,full_actual_SDK_matrix_size=0x244,fixture_nonvacuity=nonvacuity,profile_comparison_exits={k:v['comparison_exit']for k,v in profiles.items()},control_comparison_exits={v['name']:v['comparison_exit']for v in controls},execution_environment='WSL PSBBN Linux native32, invoked from Windows orchestration')
 (o/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k not in ('profiles','effective_controls')}),flush=True)
 return q
if __name__=='__main__':main()
