"""Native32 interpolation within a finite, representable conversion domain."""
import json,struct,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def harness(selected,oracle):
 head,body=selected.split('/* Interpolate',1);body='/* Interpolate'+body
 attr='a->first + (b->first - a->first) * ratio'
 bad=dict(reversed_ratio=body.replace('ratio = (D_800D3688 - a->z) / (b->z - a->z);','ratio = 1.0f - (D_800D3688 - a->z) / (b->z - a->z);'),
  wrong_axis=body.replace('out->z = D_800D3688;','out->z = -D_800D3688;'),
  omitted_y=body.replace('out->y = a->y + (b->y - a->y) * ratio;','out->y = a->y;'),
  wrong_attribute=body.replace(attr,'a->second + (b->second - a->second) * ratio'),
  narrowed_attribute=body.replace(attr,'(u8)(s16)('+attr+')'),
  missing_third=body.replace('out->third = a->third + (b->third - a->third) * ratio;','out->third = 0;'),
  wrong_cursor=body.replace('return out + 1;','return out;'),
  touched_retained=body.replace('return out + 1;','out->retained[0] = 0;\n    return out + 1;'))
 assert len(set(bad.values()))==8 and all(v!=body for v in bad.values())
 code=head+'\nf32 D_800D3688;\n'+'\n'.join(v.replace('func_151858FC','candidate_'+str(i))for i,v in enumerate([body,*bad.values()]))
 code+='\ntypedef struct {u8 initial[60];u8 expected[60];u32 output;u32 plane;} Case;\nstatic const Case cases[]={\n';rows=[]
 def native(data):return struct.pack('<IIIhhhBB',*struct.unpack('>IIIhhhBB',data))
 for a,b,depth in oracle.corpus():
  for out in (oracle.OUT,oracle.A,oracle.B):
   initial=oracle.fixture(a,b,depth=depth);expected,cursor=oracle.reference(initial,out=out)
   packed=lambda m:b''.join(native(bytes(m[oracle.A+i*20+j]for j in range(20)))for i in range(3))
   old,new=packed(initial),packed(expected);rows.append('{{%s},{%s},%d,%du}'%(','.join(str(v)for v in old),','.join(str(v)for v in new),(out-oracle.A)//20,oracle.bits(depth)))
 code+=',\n'.join(rows)+'\n};\n'
 code+=r'''
typedef char Layout[sizeof(ClipVertex)==20 && __builtin_offsetof(ClipVertex,first)==12 && __builtin_offsetof(ClipVertex,retained)==18?1:-1];
typedef struct {u32 before;ClipVertex vertices[3];u32 after;} World;
typedef ClipVertex *(*Candidate)(ClipVertex*,ClipVertex*,ClipVertex*);
'''
 code+='static Candidate candidates[]={'+','.join('candidate_'+str(i)for i in range(9))+'};\n'
 code+=r'''
static int run(void){u32 i,j,k,killed=0;World world;ClipVertex *got;int same;union {u32 u;f32 f;} plane;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++)for(j=0;j<9;j++){
  world.before=0x12345678;world.after=0x87654321;
  for(k=0;k<60;k++)((u8*)world.vertices)[k]=cases[i].initial[k];
  plane.u=cases[i].plane;D_800D3688=plane.f;
  got=candidates[j](world.vertices,world.vertices+1,world.vertices+cases[i].output);
  same=got==world.vertices+cases[i].output+1;
  for(k=0;k<60;k++)if(((u8*)world.vertices)[k]!=cases[i].expected[k])same=0;
  if(world.before!=0x12345678||world.after!=0x87654321)return 12;
  if(!same){if(!j)return 10;killed|=1u<<(j-1);}
 }
 return killed==255u?0:11;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return code,list(bad),len(rows)
def run_native(root,out,selected,oracle):
 code,names,count=harness(selected,oracle);p=out/'native-interpolation.c';p.write_text(code);rows=[]
 for profile in ('-O0','-O2','-O3'):
  exe=out/('native-interpolation'+profile);q=subprocess.run(native_command(profile)+['-fsanitize=float-cast-overflow','-o',str(exe),str(p)],cwd=root,capture_output=True,text=True);(out/('native-interpolation'+profile+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],cwd=root,capture_output=True);assert q.returncode==0,(profile,q.returncode,q.stderr)
  rows.append(dict(profile=profile,UBSan=True,float_cast_overflow_sanitizer=True,baseline_cases=count,negative_controls=names,all_controls_effective=True))
 result=dict(native32=True,typed_20_byte_vertex=True,all_vertex_bytes_and_canaries_checked=True,input_output_aliases_checked=True,finite_domain_with_representable_attribute_conversion=True,hardware_FCSR_or_invalid_conversion_claimed=False,rows=rows)
 (out/'native-interpolation.json').write_text(json.dumps(result,indent=2)+'\n');return result
