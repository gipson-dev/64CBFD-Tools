"""Native32 polygon-loop callback contracts, mutations and whole vertex copies."""
import itertools,json,struct,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def fixtures():
 patterns=((),(0,),(1,),(0,1),(1,0),(1,1,1),(0,0,0),(1,0,1,0),(1,0,0,1,0,1,1,0))
 for plane,pattern,skip,negative,mutation in itertools.product(range(10),(*patterns,None,False),(0,1),(0,1),(0,1)):
  count=-1 if pattern is None else -2147483648 if pattern is False else len(pattern);flags=()if pattern is None or pattern is False else pattern
  initial=bytearray([0xA5]*160)
  for i,flag in enumerate(flags):initial[20*i:20*i+20]=struct.pack('<IIIhhhBB',0x3F800000+i,0x40000000+i,0x40400000+i,flag,-3+i,17+i,0x80+i,0xC0+i)
  output=bytearray([0xA5]*1280);cursor=0;calls=[]
  for i in range(max(0,count)):
   prev=(i-1)%count;keep,prior=flags[i],flags[prev];calls.extend(((0,plane,i,0,0),(0,plane,prev,0,0)))
   if keep!=prior:
    calls.append((1,plane,prev,i,cursor));a=struct.unpack_from('<IIIhhhBB',initial,prev*20);b=struct.unpack_from('<IIIhhhBB',initial,i*20)
    output[cursor*20:cursor*20+20]=struct.pack('<IIIhhhBB',a[0],b[1],0x3F000000,100+plane,a[3]-b[3],200+plane,0xB0+plane,0xC7);cursor+=1+skip
   if keep:output[cursor*20:cursor*20+20]=initial[i*20:i*20+20];cursor+=1
  yield count,plane,skip,negative,mutation,bytes(initial),bytes(output),cursor,calls
def harness(selected):
 head,body=selected.split('/* Clip a closed',1);body='/* Clip a closed'+body
 address='(ClipVertex *)((u32)count * sizeof(ClipVertex) + (u32)vertices - sizeof(ClipVertex))'
 bad=dict(wrong_closure=body.replace(address,'vertices'),negative_count_result=body.replace('    current = vertices;','    if (count < 0) return out + 1;\n    current = vertices;'),positive_only_predicate=body.replace('if (classify(current))','if (classify(current) > 0)'),reversed_endpoints=body.replace('interpolate(previous, current, out)','interpolate(current, previous, out)'),ignored_cursor=body.replace('out = interpolate(previous, current, out);','interpolate(previous, current, out);'),short_copy=body.replace('*out++ = *current;','{ out->x = current->x; out++; }'),reloaded_classifier=body.replace('classify(current)','D_8008D4C0[plane](current)').replace('classify(previous)','D_8008D4C0[plane](previous)'),reloaded_interpolator=body.replace('interpolate(previous, current, out)','D_8008D498[plane](previous, current, out)'))
 bad['reloaded_classifier']=bad['reloaded_classifier'].replace('    ClipClassify classify = D_8008D4C0[plane];\n','')
 bad['reloaded_interpolator']=bad['reloaded_interpolator'].replace('    ClipInterpolate interpolate = D_8008D498[plane];\n','')
 assert len(set(bad.values()))==8 and all(v!=body for v in bad.values())
 code=head+'\n'.join(v.replace('func_15185DD4','candidate_'+str(i))for i,v in enumerate([body,*bad.values()]))
 code+='\ntypedef struct {s32 kind,id,a,b,out;} Event;\ntypedef struct {s32 count;u32 plane,skip,negative,mutation;u8 initial[160],expected[1280];u32 cursor,event_count;Event events[24];} Case;\nstatic const Case cases[]={\n';rows=[]
 for count,plane,skip,negative,mutation,initial,output,cursor,events in fixtures():
  rows.append('{%s,%d,%d,%d,%d,{%s},{%s},%d,%d,{%s}}'%('(-2147483647-1)'if count==-2147483648 else str(count),plane,skip,negative,mutation,','.join(map(str,initial)),','.join(map(str,output)),cursor,len(events),','.join('{'+','.join(map(str,e))+'}'for e in events)or'{0,0,0,0,0}'))
 code+=',\n'.join(rows)+'\n};\n'
 code+=r'''
typedef char Layout[sizeof(void*)==4 && sizeof(ClipVertex)==20?1:-1];
typedef struct {u32 before;ClipVertex input[8];u32 between;ClipVertex output[64];u32 after;} World;
static World world;static const Case *current;static u32 error,event_count;static Event events[24];
static s32 classify_common(u32,ClipVertex*);static ClipVertex *interpolate_common(u32,ClipVertex*,ClipVertex*,ClipVertex*);
'''
 for i in range(10):code+='static s32 classifier_%d(ClipVertex*p){return classify_common(%d,p);}\nstatic ClipVertex*interpolator_%d(ClipVertex*a,ClipVertex*b,ClipVertex*p){return interpolate_common(%d,a,b,p);}\n'%(i,i,i,i)
 code+='static ClipClassify classifiers[]={'+','.join('classifier_'+str(i)for i in range(10))+'};\nstatic ClipInterpolate interpolators[]={'+','.join('interpolator_'+str(i)for i in range(10))+'};\nClipClassify D_8008D4C0[10];ClipInterpolate D_8008D498[10];\n'
 code+=r'''
static s32 input_index(ClipVertex*p){u32 n=(u32)p-(u32)world.input;if(n%20||n>=160){error=1;return 0;}return n/20;}
static void event(s32 kind,s32 id,s32 a,s32 b,s32 out){if(event_count>=24){error=1;return;}events[event_count++]=(Event){kind,id,a,b,out};if((u32)id!=current->plane)error=1;}
static s32 classify_common(u32 id,ClipVertex*p){s32 i=input_index(p),keep=world.input[i].first&1;
 event(0,id,i,0,0);
 if(current->mutation&&event_count==1){D_8008D4C0[current->plane]=classifiers[(current->plane+1)%10];D_8008D498[current->plane]=interpolators[(current->plane+1)%10];}
 return keep?(current->negative?-1:1):0;
}
static ClipVertex *interpolate_common(u32 id,ClipVertex*a,ClipVertex*b,ClipVertex*out){s32 ai=input_index(a),bi=input_index(b);u32 n=((u32)out-(u32)world.output)/20;
 event(1,id,ai,bi,n);if(n>=62){error=1;return world.output;}
 out->x=a->x;out->y=b->y;out->z=.5f;out->first=100+id;out->second=a->first-b->first;out->third=200+id;out->retained[0]=0xB0+id;out->retained[1]=0xC7;
 return out+1+current->skip;
}
typedef ClipVertex *(*Candidate)(ClipVertex*,s32,u32,ClipVertex*);
'''
 code+='static Candidate candidates[]={'+','.join('candidate_'+str(i)for i in range(9))+'};\n'
 code+=r'''
static int run(void){u32 i,j,k,killed=0;ClipVertex*got;int same;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++)for(j=0;j<9;j++){
  current=cases+i;world.before=0x12345678;world.between=0x87654321;world.after=0xABCDEF12;
  for(k=0;k<160;k++)((u8*)world.input)[k]=current->initial[k];for(k=0;k<1280;k++)((u8*)world.output)[k]=0xA5;
  for(k=0;k<10;k++){D_8008D4C0[k]=classifiers[k];D_8008D498[k]=interpolators[k];}
  error=event_count=0;got=candidates[j](world.input,current->count,current->plane,world.output);
  same=!error&&got==world.output+current->cursor&&event_count==current->event_count;
  for(k=0;k<160;k++)if(((u8*)world.input)[k]!=current->initial[k])same=0;
  for(k=0;k<1280;k++)if(((u8*)world.output)[k]!=current->expected[k])same=0;
  for(k=0;k<event_count&&k<24;k++)if(events[k].kind!=current->events[k].kind||events[k].id!=current->events[k].id||events[k].a!=current->events[k].a||events[k].b!=current->events[k].b||events[k].out!=current->events[k].out)same=0;
  if(world.before!=0x12345678||world.between!=0x87654321||world.after!=0xABCDEF12)return 12;
  if(!same){if(!j)return 10;killed|=1u<<(j-1);}
 }
 return killed==255u?0:11;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 return code,list(bad),len(rows)
def run_native(root,out,selected):
 code,names,count=harness(selected);p=out/'native-polygon.c';p.write_text(code);rows=[]
 for profile in ('-O0','-O2','-O3'):
  exe=out/('native-polygon'+profile);q=subprocess.run(native_command(profile)+['-o',str(exe),str(p)],cwd=root,capture_output=True,text=True);(out/('native-polygon'+profile+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],cwd=root,capture_output=True);assert q.returncode==0,(profile,q.returncode,q.stderr)
  rows.append(dict(profile=profile,UBSan=True,baseline_cases=count,negative_controls=names,all_controls_effective=True))
 result=dict(native32=True,table_slots=10,callback_contracts_not_original_geometry=True,negative_and_empty_counts=True,nonunit_return_cursor=True,signed_nonzero_predicates=True,live_table_mutations_with_cached_callbacks=True,all_input_output_bytes_and_canaries_checked=True,rows=rows)
 (out/'native-polygon.json').write_text(json.dumps(result,indent=2)+'\n');return result
