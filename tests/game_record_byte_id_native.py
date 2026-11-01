"""Native32 byte-ID search against an independent used-ID set, including fallback cases."""
from pathlib import Path
import json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def harness(selected):
 head,tail=selected.split('/* Search',1);body='/* Search'+tail
 bad=dict(mode_width=body.replace('descending == 0','(u8)descending == 0'),forward_boundary=body.replace('index = descending = D_800DBF00','index = descending = 0'),forward_restart=body.replace('index = descending - 1;','index += 0;'),forward_fallback=body.replace('if (id >= 256) { id = 255; break; }','if (id >= 256) { id = 0; break; }'),reverse_restart=body.replace('index = -1;','index += 0;'),reverse_fallback=body.replace('if (id <= 0) { id = descending; break; }','if (id <= 0) { id = 0; break; }'),record_offset=body.replace('[index].id','[index].tail[0]'),reverse_boundary=body.replace('255 - D_800DBF00','254 - D_800DBF00'),empty_count=body.replace('    s32 index;','    s32 index;\n    if (D_800DBEF0 <= 0) return 255;'))
 assert len(bad)==9 and len(set(bad.values()))==9 and all(v!=body for v in bad.values())
 code=head+'\n'.join(v.replace('func_15004BF0','candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
 code+=r'''
typedef struct {u32 before;ByteIdRecordView records[256];u32 after;} World;
typedef char CheckView[sizeof(ByteIdRecordView)==0xA0 && __builtin_offsetof(ByteIdRecordView,id)==0x72?1:-1];
typedef char CheckLegacy[sizeof(struct131)==0xA0?1:-1];
static World actual,expected;static u8 used[256];static u32 killed,cases;
s32 D_800DBEF0;struct131 *D_800DBEF4;u8 D_800DBF00;
static u8 value(int pattern,int i){
 switch(pattern){case 0:return 0;case 1:return(u8)(i+1);case 2:return 1;case 3:return(u8)(255-i);case 4:return(u8)(2*i+1);default:return(u8)((i^1)+1);}
}
static s32 reference(s32 descending,int reserved,int count){int i,id,limit;
 for(i=0;i<256;i++)used[i]=0;
 if(!descending){for(i=reserved;i<count;i++)used[actual.records[i].id]=1;for(id=1;id<256;id++)if(!used[id])return id;return 255;}
 for(i=0;i<count;i++)used[actual.records[i].id]=1;
 limit=255-reserved;for(id=limit;id>0;id--)if(!used[id])return id;return limit;
}
typedef s32 (*Candidate)(s32);
'''
 code+='static Candidate candidates[]={'+','.join('candidate_'+str(i) for i in range(10))+'};\n'
 code+=r'''
static int one(s32 mode,int reserved,int count,int pattern){int i,j,same;s32 got,want;
 for(i=0;i<(int)sizeof(World);i++)((u8*)&actual)[i]=((u8*)&expected)[i]=0xA5;
 for(i=0;i<256;i++)actual.records[i].id=expected.records[i].id=value(pattern,i);
 D_800DBEF0=count;D_800DBEF4=(struct131*)actual.records;D_800DBF00=(u8)reserved;want=reference(mode,reserved,count);
 for(j=0;j<10;j++){
  got=candidates[j](mode);same=got==want && D_800DBEF0==count && D_800DBEF4==(struct131*)actual.records && D_800DBF00==(u8)reserved;
  for(i=0;i<(int)sizeof(World);i++)if(((u8*)&actual)[i]!=((u8*)&expected)[i])same=0;
  if(!same){if(!j)return 1;killed|=1u<<(j-1);}cases++;
 }
 return 0;
}
static int run(void){int m,s,n,p;
 static s32 modes[]={0,1,-1,0x100};static int starts[]={0,1,2,127,254,255},counts[]={-1,0,1,4,16,256};
 for(m=0;m<4;m++)for(s=0;s<6;s++)for(n=0;n<6;n++)for(p=0;p<6;p++)if(one(modes[m],starts[s],counts[n],p))return 10;
 if(killed!=511u||cases!=8640u)return 11;return 0;
}
'''+START
 return code,list(bad)

def run_native(root,out,selected):
 code,names=harness(selected);path=out/'native-byte-id.c';path.write_text(code);rows=[]
 for profile in ('-O0','-O2','-O3'):
  exe=out/('native-byte-id'+profile);q=subprocess.run(native_command(profile)+['-o',str(exe),str(path)],cwd=root,capture_output=True,text=True)
  (out/('native-byte-id'+profile+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],cwd=root,capture_output=True);assert q.returncode==0,(profile,q.returncode,q.stderr)
  rows.append(dict(profile=profile,exit=0,UBSan=True,baseline_cases=864,negative_cases_per_control=864,negative_controls=names,all_controls_effective=True))
 report=dict(private_only=True,installed=False,matching_credit=0,native32=True,typed_view_and_legacy_stride_asserted=True,complete_record_bytes_canaries_and_globals_unchanged=True,independent_set_reference=True,rows=rows)
 (out/'native-byte-id.json').write_text(json.dumps(report,indent=2)+'\n');return report
