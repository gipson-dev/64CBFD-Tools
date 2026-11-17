"""Execute the recovered C with guest-qualified canonical byte fixtures."""
from pathlib import Path
import hashlib,json,struct,subprocess,sys
from tools.experiments import game_strip_update_151ad174_private_recovery as source
from tools.tests import game_strip_update_151ad174_private_oracle as o
p=source.PACKET
def main():
 source.check_inputs()
 out=source.OUT/'native';out.mkdir(exist_ok=False)
 regions=list(o.REGIONS)+[(o.TICKS,4),(o.CATEGORY,4)]+[(v['address'],len(bytes.fromhex(v['bytes'])))for v in o.CONSTANTS.values()]
 offsets={};size=0
 for at,n in regions:size=(size+7)&~7;offsets[at]=size;size+=n
 size=(size+7)&~7
 def flat(at):
  for base,n in regions:
   if base<=at<base+n:return offsets[base]+at-base
  raise AssertionError(hex(at))
 fields=[(o.RECORD+off,4)for off in(0x38,0x3C,0x44,0x4C)]+[(o.RECORD+off,2)for off in(0x52,0x54)]+[(o.MARK,4),(o.TICKS,4),(o.CATEGORY,4)]
 for base in(o.POINTS,o.OTHER_POINTS):fields.extend((base+i*4,4)for i in range(120))
 for base in(o.OWNER,o.OTHER_OWNER):fields.extend(((base+0x3C,4),(base+0x76,2),(base+0x31C,4)))
 for base in(o.EFFECT,o.OTHER_EFFECT):fields.append((base+0xA8,4))
 fields.extend((v['address'],len(bytes.fromhex(v['bytes'])))for v in o.CONSTANTS.values())
 pointers=[o.RECORD+0x38,o.RECORD+0x44,o.OWNER+0x31C,o.OTHER_OWNER+0x31C]
 def canonical(m):
  b=bytearray(size)
  for base,n in regions:b[offsets[base]:offsets[base]+n]=bytes(m[base+i]for i in range(n))
  for at,n in fields:b[flat(at):flat(at)+n]=o.read(m,at,n).to_bytes(n,'little')
  return bytes(b)
 vectors=bytearray();fixtures=[];codes={o.SIN:0,o.COS:1,o.QUERY:2,o.RNG:3,o.EMIT:4}
 def append(b):
  while len(vectors)%4:vectors.append(0)
  at=len(vectors);vectors.extend(b);return at
 def words(*w):return struct.pack('<%dI'%len(w),*w)
 class Capture(o.Service):
  def __init__(self,m,c):super().__init__(m,c);self.events=[]
  def invoke(self,t,a):
   before=canonical(self.m);result=super().invoke(t,a);after=canonical(self.m)
   changed={i:v for i,v in enumerate(after)if before[i]!=v}
   for pointer in pointers:
    offset=flat(pointer)
    if before[offset:offset+4]!=after[offset:offset+4]:
     changed.update({offset+i:after[offset+i]for i in range(4)})
   changed=sorted(changed.items())
   self.events.append((codes[t],tuple(a),result,changed));return result
 original_service=o.Service;o.Service=Capture
 try:
  for c in o.cases():
   initial=o.fixture(c)
   # The independent reference constructs its own service; capture that instance.
   instances=[]
   def create(m,case):
    instance=Capture(m,case);instances.append(instance);return instance
   o.Service=create
   expected,calls=o.reference(initial,c);assert len(instances)==1;events=instances[0].events
   first=append(canonical(initial));second=append(canonical(expected));start=len(vectors)
   for t,a,result,changed in events:
    append(words(t,len(a),result,len(changed),*a,*[n for pair in changed for n in pair]))
   fixtures.append((first,second,start,len(events)))
 finally:o.Service=original_service
 (out/'vectors.bin').write_bytes(vectors)
 (out/'vectors.s').write_text('.section .rodata\n.balign 16\n.global strip_vectors\nstrip_vectors:\n.incbin "vectors.bin"\n.section .note.GNU-stack,"",@progbits\n')
 subprocess.run(['as','--32','-o','vectors.o','vectors.s'],cwd=out,check=True,capture_output=True)
 ownertext=(source.FROZEN/source.SOURCE).read_text();types=ownertext.split('typedef struct { f32 position[3], velocity[3]; } StripPoint151ACBD4;',1)[1].split('} StripRecord151ACBD4;',1)[0]
 types='typedef struct { f32 position[3], velocity[3]; } StripPoint151ACBD4;'+types+'} StripRecord151ACBD4;'
 header='''typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;typedef double f64;typedef struct Vtx Vtx;
 #define NULL ((void*)0)
 '''+types+'\ntypedef char record_size_check[sizeof(StripRecord151ACBD4)==88?1:-1];\n'
 header+='enum { ARENA_SIZE=%d, CASES=%d };\n'%(size,len(fixtures))
 header+='static u8 arena[ARENA_SIZE] __attribute__((aligned(16)));extern const u8 strip_vectors[];\n'
 header+='static const u32 fixtures[CASES][4]='+json.dumps(fixtures,separators=(',',':')).replace('[','{').replace(']','}')+';\n'
 header+='static const u32 bases[]='+json.dumps([at for at,n in regions]).replace('[','{').replace(']','}')+';\n'
 header+='static const u32 starts[]='+json.dumps([offsets[at]for at,n in regions]).replace('[','{').replace(']','}')+';\n'
 header+='static const u32 pointer_slots[]='+json.dumps([flat(at)for at in pointers]).replace('[','{').replace(']','}')+';\n'
 for name,at,kind in [('D_800BE9E4',o.TICKS,'s32'),('D_800BE9F0',o.CATEGORY,'s32')]+[(n,v['address'],'f64'if len(bytes.fromhex(v['bytes']))==8 else'f32')for n,v in o.CONSTANTS.items()]:
  header+='#define %s (*(%s*)(arena+%d))\n'%(name,kind,flat(at))
 header+='''static u32 cursor,stage,expected_calls,bad;
 static u32 map(u32 p){u32 i;for(i=0;i<sizeof(bases)/sizeof(*bases);i++)if(p==bases[i])return (u32)(arena+starts[i]);return p;}
 static u32 unmap(u32 p){u32 i;for(i=0;i<sizeof(bases)/sizeof(*bases);i++)if(p==(u32)(arena+starts[i]))return bases[i];return p;}
 static void fix(void){u32 i;for(i=0;i<sizeof(pointer_slots)/sizeof(*pointer_slots);i++){u32*p=(u32*)(arena+pointer_slots[i]);*p=map(*p);}}
 static u32 service(u32 t,const u32*a,u32 n){const u32*p=(const u32*)(strip_vectors+cursor);u32 i,count,result;if(stage>=expected_calls){bad=1;return 0;}if(p[0]!=t||p[1]!=n)bad=1;result=p[2];count=p[3];p+=4;for(i=0;i<n;i++)if(p[i]!=a[i])bad=1;p+=n;for(i=0;i<count;i++){arena[p[0]]=(u8)p[1];p+=2;}cursor=(u32)((const u8*)p-strip_vectors);stage++;fix();return result;}
 static f32 real(u32 n){union{u32 n;f32 f;}u;u.n=n;return u.f;}
 f32 func_150489B0(u8 a){u32 x=a;return real(service(0,&x,1));}
 f32 func_15048A40(u8 a){u32 x=a;return real(service(1,&x,1));}
 s32 func_1000F3D0(u16 a){u32 x=a;return (s32)service(2,&x,1);}
 s32 func_150ADA20(void){return (s32)service(3,(const u32*)0,0);}
 u16 func_10010E78(s32 a,s32 b,s32 c,s32 d,s32 e,s32 f,s32 g,s32 h,s32 i,s32 j,s32 k){u32 x[11]={(u32)a,(u32)b,(u32)c,(u32)d,(u32)e,(u32)f,(u32)g,(u32)h,(u32)i,(u32)j,(u32)k};return (u16)service(4,x,11);}
 f32 fabsf(f32 x){union{u32 n;f32 f;}u;u.f=x;u.n&=0x7fffffff;return u.f;}
 f32 sqrtf(f32 x){f32 r;__asm__("sqrtss %1,%0":"=x"(r):"x"(x));return r;}
 '''
 footer='''
 static s32 check(void){u32 n,i;for(n=0;n<CASES;n++){const u32*c=fixtures[n];for(i=0;i<ARENA_SIZE;i++)arena[i]=strip_vectors[c[0]+i];fix();cursor=c[2];expected_calls=c[3];stage=bad=0;func_151AD174(arena+RECORD_OFFSET);if(bad||stage!=expected_calls)return 3;for(i=0;i<sizeof(pointer_slots)/sizeof(*pointer_slots);i++){u32*p=(u32*)(arena+pointer_slots[i]);*p=unmap(*p);}for(i=0;i<ARENA_SIZE;i++)if(arena[i]!=strip_vectors[c[1]+i])return 3;}return 0;}
 __attribute__((force_align_arg_pointer,noreturn)) void _start(void){s32 code=check();__asm__ volatile("int $0x80"::"a"(1),"b"(code):"memory");__builtin_unreachable();}
 '''.replace('RECORD_OFFSET',str(offsets[o.RECORD]))
 body=source.PIN['body']
 forms=[('positive',body,'-O0'),('positive',body,'-O2'),('positive',body,'-O3'),('force-Z-score',body.replace('fabsf(velocity[2])','fabsf(force[2])'),'-O2'),('wrong-decay',body.replace('r->time *= D_800A927C;','r->time *= 0.5f;'),'-O2'),('signed-countdown',body.replace('effect[0xAD] - 1','(s8)effect[0xAD] - 1'),'-O2'),('wrong-smoothing',body.replace('smoothingScale = D_800A9288;','smoothingScale = 1.0;'),'-O2')]
 rows=[]
 for tag,text,opt in forms:
  if tag!='positive':assert text!=body,tag
  stem=tag+'-'+opt[1:];src=out/(stem+'.c');exe=out/stem;src.write_text(header+text+footer)
  cmd=['gcc','-m32','-std=c99',opt,'-msse2','-mfpmath=sse','-ffp-contract=off','-fno-fast-math','-fno-builtin','-ffreestanding','-fno-pie','-no-pie','-fno-stack-protector','-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-nostdlib','-Wl,-e,_start','-Wl,-z,noexecstack','-o',str(exe),str(src),str(out/'vectors.o')]
  q=subprocess.run(cmd,capture_output=True,text=True);(out/(stem+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0 and not q.stderr,q.stderr
  q=subprocess.run([str(exe)],capture_output=True);assert q.returncode==(0 if tag=='positive'else 3),(tag,opt,q.returncode,q.stderr)
  row=dict(label=tag,opt=opt,exit_code=q.returncode,source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest());rows.append(row);print(json.dumps(row),flush=True)
 report=dict(cases=len(fixtures),runs=rows,passes=True,vector_sha256=hashlib.sha256(vectors).hexdigest(),all_declared_public_bytes_and_calls_checked=True,domain='544 finite guest-qualified cases, fresh disjoint objects, SSE single/double round-to-nearest; no FCSR or private-frame claim')
 (out/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(fixtures),executions=len(rows),passes=True)),flush=True)
 source.check_inputs()
if __name__=="__main__":main()
