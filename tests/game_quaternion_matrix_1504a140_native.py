"""Actual semantic C under native32 O0/O2/O3, including valid buffer overlaps."""
from pathlib import Path
import hashlib,itertools,json,subprocess
from tools.experiments import game_quaternion_matrix_1504a140_recovery as source
from tools.tests import game_quaternion_matrix_1504a140_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command

def cases():
 rows=[]
 for i,q in enumerate(itertools.product((-2.,-.25,.5,1.),repeat=4)):rows.append(g.Case(tuple(g.bits(v) for v in q),i%7))
 extra=[tuple(1. if i==k else 0. for i in range(4)) for k in range(4)]
 extra.extend(((1.,2.,3.,4.),(3.,4.,0.,0.),(1e-10,2e-10,-1e-10,3e-10),(1e10,2e10,-1e10,.5e10),(2.**-64,)*4,(2.**60,2.**59,2.**58,2.**57)))
 for q,alias in itertools.product(extra,range(7)):rows.append(g.Case(tuple(g.bits(v) for v in q),alias))
 return rows

def main():
 arr=lambda xs:'{'+','.join('0x%08Xu'%v for v in xs)+'}'
 vectors=[]
 for c in cases():
  initial,args=g.fixture(c);expected=g.reference(initial,args,c.rule)
  words=lambda m:[g.read(m,base+i*4) for base in (0x30000,0x40000) for i in range(64)]
  q=80 if c.alias==0 else (16,17,24,14,28,31)[c.alias-1]
  vectors.append('{%d,%s,%s}'%(q,arr(words(initial)),arr(words(expected))))
 body=source.BODY
 controls=(body.replace('2.0f /','1.0f /'),body.replace('xz - wy','xz + wy'),body.replace('matrix[15] = 1.0f;','matrix[15] = 1.0f;\n    matrix[12] = matrix[13] = matrix[14] = 0.0f;'),body.replace('quaternion[0] * scaledX','quaternion[1] * scaledX'))
 assert all(b!=body for b in controls)
 functions=[body]+[b.replace(source.NAME,'negative%d'%i) for i,b in enumerate(controls)]
 code=r'''
#include <ultra64.h>
struct Input {u32 inputIndex,input[128],expected[128];};
static const struct Input cases[]={ROWS};static f32 bank[128];
static u32 word(f32*value){u32 n;__builtin_memcpy(&n,value,4);return n;}
FUNCTIONS
static int one(u32 c,void(*function)(f32*,f32*)){u32 i;for(i=0;i<128;i++)__builtin_memcpy(bank+i,cases[c].input+i,4);function(bank+cases[c].inputIndex,bank+16);for(i=0;i<128;i++)if(word(bank+i)!=cases[c].expected[i])return 1;return 0;}
static int run(void){u32 i,j,killed=0;void(*functions[])(f32*,f32*)={func_1504A140,negative0,negative1,negative2,negative3};
 if(sizeof(f32)!=4||sizeof(void*)!=4)return 30;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++)if(one(i,functions[0]))return 10;
 for(j=1;j<5;j++)for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++)if(one(i,functions[j])){killed++;break;}return killed==4?0:20;}
void __attribute__((force_align_arg_pointer)) _start(void){int n=run();__asm__ volatile("int $0x80"::"a"(1),"b"(n));__builtin_unreachable();}
'''.replace('ROWS',',\n'.join(vectors)).replace('FUNCTIONS','\n'.join(functions))
 path=source.OUT/'native-quaternion.c';path.write_text(code);report=[]
 for profile in ('-O0','-O2','-O3'):
  binary=source.OUT/('native-quaternion'+profile)
  q=subprocess.run([*native_command(profile),'-fno-tree-loop-distribute-patterns','-o',str(binary),str(path)],cwd=source.ROOT,capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
  result=subprocess.run([str(binary)],capture_output=True);assert result.returncode==0,(profile,result.returncode)
  report.append(dict(profile=profile,cases=len(vectors),public_bytes=512,valid_aliases=7,compiled_source_controls=4,undefined_behavior_traps=True,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),domain='finite inputs and finite nonzero norms'))
 (source.OUT/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
