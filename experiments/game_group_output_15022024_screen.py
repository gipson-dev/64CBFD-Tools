"""Private group-output reconstruction screen; does not install or credit C."""
from pathlib import Path
import hashlib, inspect, itertools, json, os, struct
from tools.experiments.game_actor_state_tick_integration import symbol_rows, same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.tests.game_owner_float_payload_oracle import FactoryOracle, Case
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read

root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
out=root/'conker/build/game-group-output-15022024-screen-v2'
entry=0x15022024
CANDIDATE = """extern f32 D_80096A14;
typedef struct { u16 kind; u8 identity; u8 reserved[5]; } GroupOutputRecord49D30;
s32 func_15022024(volatile f32 *outputA, volatile f32 *outputB, s32 actorIndex, s32 group) {
    s32 i, count;
    u16 *enabled;
    GroupOutputRecord49D30 *record;
    f32 sentinel, value;
    if (D_800C35EA[group] != 1) return 0;
    count = D_800C363A[group];
    if (count <= 0) return 0;
    enabled = D_800C35C8[group];
    for (i = 0; i < count; i++) {
        if (enabled[i] != 0) {
            record = (GroupOutputRecord49D30 *)(D_800C35F0[group] + i * 8);
            if (record->kind == 2 && record->identity == D_800CC2D0[actorIndex].unique_id) {
                sentinel = D_80096A14;
                outputA[1] = 0.0f;
                outputB[1] = 0.0f;
                outputA[0] = 0.0f;
                outputB[0] = 0.0f;
                value = *(f32 *)(D_800C3958[group] + i * 0x44 + 0x3C);
                if (sentinel != value) {
                    outputB[0] = value;
                    outputB[1] = outputB[0];
                }
                value = *(f32 *)(D_800C3958[group] + i * 0x44 + 0x40);
                if (sentinel != value) {
                    outputA[0] = value;
                    outputA[1] = outputA[0];
                }
                return 1;
            }
        }
    }
    return 0;
}
"""

enabled,records,runtime,output=0x31000,0x32000,0x33000,0x34000

def fixture(mode,index,first,second,alias):
 m={STACK+i:(i*17+0xa5)&255 for i in range(-128,128)}
 for base,n in ((enabled,128),(records,512),(runtime,2048),(output,64),(s['D_800CC2D0'],0x700)):
  m.update({base+i:(i*19+0x51)&255 for i in range(n)})
 group=0; actor=1
 m[s['D_800C35EA']]= 0 if mode==0 else 1
 m[s['D_800C363A']]= 0 if mode==1 else 3
 put(m,s['D_800C35C8'],enabled);put(m,s['D_800C35F0'],records);put(m,s['D_800C3958'],runtime);put(m,s['D_80096A14'],0x7f7fffff)
 m[s['D_800CC2D0']+actor*0x32c+0x3b]=0x77
 for i in range(3):
  put(m,enabled+2*i,1 if mode>=3 else 0,2);put(m,records+8*i,2 if mode>=4 else 1,2)
  m[records+8*i+2]=0x77 if mode>=5 and i==index else 0x66
  put(m,runtime+i*0x44+0x3c,first);put(m,runtime+i*0x44+0x40,second)
 a,b=((output,output+16),(output,output),(output,output+4),(runtime+index*0x44+0x3c,output),(output,runtime+index*0x44+0x3c),(runtime+index*0x44+0x40,output))[alias]
 return m,(a,b,actor,group)

def reference(m,args):
 m=m.copy();a,b,actor,group=args
 if m[s['D_800C35EA']+group]!=1:return m,0
 count=m[s['D_800C363A']+group]
 if not count:return m,0
 en=read(m,s['D_800C35C8']+group*4)
 for i in range(count):
  if read(m,en+2*i,2)==0:continue
  record=read(m,s['D_800C35F0']+group*4)+i*8
  if read(m,record,2)!=2 or m[record+2]!=m[s['D_800CC2D0']+actor*0x32c+0x3b]:continue
  sentinel=read(m,s['D_80096A14'])
  for dest in (a+4,b+4,a,b):put(m,dest,0)
  p=read(m,s['D_800C3958']+group*4)+i*0x44
  first=read(m,p+0x3c)
  unequal=lambda x,y: struct.unpack('>f',struct.pack('>I',x))[0]!=struct.unpack('>f',struct.pack('>I',y))[0]
  if unequal(sentinel,first):
   put(m,b,first);put(m,b+4,read(m,b));p=read(m,s['D_800C3958']+group*4)+i*0x44
  second=read(m,p+0x40)
  if unequal(sentinel,second):put(m,a,second);put(m,a+4,read(m,a))
  return m,1
 return m,0

def public(m):return {a:b for a,b in m.items() if not STACK-128<=a<STACK+128}


def machine(code, memory, args):
 return FactoryOracle(code,memory.copy(),Case(),entry=entry,s={},arguments=args).run()

def accesses(machine):
 return [event for event in machine.trace if not STACK-128<=event[1]<STACK+128]

def main():
 global s
 out.mkdir(parents=True,exist_ok=True)
 ownerfile=root/'conker/src/game/generated_49D30.c'
 owner=ownerfile.read_text();stub='s32 func_15022024() {\n    return 0;\n}'
 assert owner.count(stub)==1
 rom=(root/'conker/conker.us.bin').read_bytes(); elf=(root/'conker/build/conker.us.elf').read_bytes()
 s={r[1]:r[2][1] for r in symbol_rows(elf)}
 truth=list(struct.unpack_from('>91I',rom,0x4f4d4))
 namespace=dict(compile_owner.__globals__);source=inspect.getsource(compile_owner)
 assert source.count('*flags,')==2
 exec(source.replace('*flags,','*[f for f in flags if not f.startswith("-Wo,")],',1),namespace)
 compiler=namespace['compile_owner'];flags=('-O2','-g3','-Wo,-loopunroll,0')
 base,base_diag=compiler(root,out,owner,'baseline',flags)
 variants={}
 for label,body in (('ordinary',CANDIDATE.replace('volatile f32 *outputA, volatile f32 *outputB','f32 *outputA, f32 *outputB')),('volatile',CANDIDATE)):
  obj,diag=compiler(root,out,owner.replace(stub,body),label,flags)
  assert diag==base_diag and same_functions(base,obj,('func_15022024',))==56
  assert normalized_pools(base)==normalized_pools(obj)
  variants[label]=bound_blob(*payload(obj,'func_15022024'),s)
 programs={'retail':truth,**variants};differences={k:0 for k in variants};cases=0
 for mode,index,first,second,alias in itertools.product(range(6),range(3),(0x7f7fffff,0x3f800000,0x7fc00001),(0x7f7fffff,0xc0000000,0x7fc00001),range(6)):
  initial,args=fixture(mode,index,first,second,alias);want,retval=reference(initial,args)
  for label,code in programs.items():
   actual=machine(code,initial,args);different=(actual.r[2],public(actual.memory))!=(retval,public(want))
   if label=='retail':assert not different,(mode,index,first,second,alias)
   else:differences[label]+=different
  cases+=1
 assert cases==972 and all(v==0 for v in differences.values()),differences
 controls=((0x24010001,0x24010000),(0x24070002,0x24070003),(0xe6220004,0xe6220000))
 for old,new in controls:
  assert truth.count(old)==1,hex(old)
  altered=truth.copy();altered[altered.index(old)]=new;caught=False
  for mode,index,alias in itertools.product((0,1,3,4,5),range(3),range(6)):
   initial,args=fixture(mode,index,0x3f800000,0xc0000000,alias);want,retval=reference(initial,args)
   try:
    actual=machine(altered,initial,args);caught=(actual.r[2],public(actual.memory))!=(retval,public(want))
   except (AssertionError,KeyError):caught=True
   if caught:break
  assert caught,(hex(old),hex(new))
 traces={k:0 for k in variants};empty_loads={k:0 for k in programs};trace_cases=0
 for mode,index,first,second,alias in itertools.product(range(6),range(3),(0x7f7fffff,0x3f800000),(0x7f7fffff,0xc0000000),range(6)):
  initial,args=fixture(mode,index,first,second,alias);expected=accesses(machine(truth,initial,args))
  for label,code in programs.items():
   observed=accesses(machine(code,initial,args))
   if label!='retail':traces[label]+=observed!=expected
   if mode==1 and any(e[0]=='R' and e[1]==s['D_800C35C8'] for e in observed):empty_loads[label]+=1
  trace_cases+=1
 assert trace_cases==432 and traces['ordinary']==63 and traces['volatile']==0 and not any(empty_loads.values()),(traces,empty_loads)
 report={'private_uncredited':True,'owner_sha256':hashlib.sha256(ownerfile.read_bytes()).hexdigest(),'elf_sha256':hashlib.sha256(elf).hexdigest(),'retail_sha256':hashlib.sha256(rom).hexdigest(),'retail_words':len(truth),'variants':{k:{'words':len(v),'same_position_words':sum(a==b for a,b in zip(v,truth)),'public_access_trace_differences':traces[k]} for k,v in variants.items()},'same_neighbor_functions':56,'normalized_pools_equal':True,'semantic_cases_per_stream':cases,'access_cases_per_stream':trace_cases,'negative_controls':len(controls),'zero_count_enabled_pointer_reads':empty_loads,'limits':'group 0, actor 1, three records; no FCSR or fault-prefix qualification'}
 (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report),flush=True)
if __name__=='__main__':main()
