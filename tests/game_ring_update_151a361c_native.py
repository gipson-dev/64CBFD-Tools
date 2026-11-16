"""Native32 exact C against independent memory images, with UB traps."""
import json,subprocess,time
from tools.experiments import game_ring_update_151a361c_recovery as m
from tools.tests import game_ring_update_151a361c_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def native_image(mem,base,n,fields):
 image=bytearray(g.data(mem,base,n))
 for offset,size in fields:image[offset:offset+size]=image[offset:offset+size][::-1]
 return image

def main():
 m.check_inputs();text=m.PIN['replacement'];at=text.index('/* Age the live');types,body=text[:at],text[at:]
 owner_fields=[(i,4)for i in(0x54,0x58,0x5C)]
 state_fields=[(0x1C,2),(0x24,4)]
 entry_fields=[(24*i+j,n)for i in range(8)for j,n in((0,4),(4,4),(8,4),(12,4),(16,2),(18,2))]
 rows=[];corpus=g.native_cases();array=lambda b:'{'+','.join(map(str,b))+'}'
 for c in corpus:
  initial=g.fixture(c);expected,answer=g.reference(c)
  images=[]
  for mem in(initial,expected):
   images +=[native_image(mem,g.OWNER,156,owner_fields),native_image(mem,g.STATE,80,state_fields),native_image(mem,g.RECORDS,192,entry_fields)]
  rows.append('{0x%Xu,0x%Xu,%du,%s}'%(c.tick&0xFFFFFFFF,g.bits(c.step),answer,','.join(array(b)for b in images)))
 prefix='''#include <ultra64.h>
 __attribute__((noreturn))static void quit(int code){__asm__ volatile(".byte 0xcd,0x80" : : "a"(1),"b"(code):"memory");__builtin_unreachable();}
 static void check(int x){if(!x)quit(3);}
 '''+types+'''
 s32 D_800BE9E4;f32 D_800BE9A4;
 typedef struct{u8 pre00[0x25];u8 capacity;u8 pre26[6];s8 count,head,tail;u8 pre2F[0x25];RingPosition151A361C output;u8 pre60[0x34];RingEntry151A361C *entries;u8 *state;}NativeOwner;
 typedef struct{u8 pre00[0x1C];s16 scale;u8 pre1E[6];f32 rate;u8 pre28[2];s8 byteStep;u8 pre2B[5];u8 flags;u8 pre31[0x1B];u8 phase;u8 pre4D[3];}NativeState;
 struct Vector{u32 tick,step,answer;u8 owner[156],state[80],entries[192],expectedOwner[156],expectedState[80],expectedEntries[192];};
 static const struct Vector vectors[]={
 '''+',\n'.join(rows)+'''};
 static NativeOwner owner;static NativeState state;static RingEntry151A361C entries[8];
 static void copy(void*d,const u8*s,unsigned n){for(unsigned i=0;i<n;i++)((u8*)d)[i]=s[i];}
 static void word(void*d,u32 value){copy(d,(u8*)&value,4);}
 _Static_assert(sizeof(void*)==4&&sizeof(NativeOwner)==156&&sizeof(NativeState)==80&&sizeof(RingEntry151A361C)==24,"complete native layouts");
 _Static_assert(__builtin_offsetof(NativeOwner,entries)==0x94&&__builtin_offsetof(NativeOwner,output)==0x54&&__builtin_offsetof(NativeState,phase)==0x4c,"native offsets");
 '''
 suffix='''
 static s32(*volatile invoke)(u8*)=func_151A361C;
 static int run(void){for(unsigned i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++){
  const struct Vector*v=&vectors[i];copy(&owner,v->owner,156);copy(&state,v->state,80);copy(entries,v->entries,192);
  owner.entries=entries;owner.state=(u8*)&state;word(&D_800BE9E4,v->tick);word(&D_800BE9A4,v->step);
  check((u32)invoke((u8*)&owner)==v->answer);
  for(unsigned j=0;j<156;j++)if(j<0x94)check(((u8*)&owner)[j]==v->expectedOwner[j]);
  check(owner.entries==entries&&owner.state==(u8*)&state);
  for(unsigned j=0;j<80;j++)check(((u8*)&state)[j]==v->expectedState[j]);
  for(unsigned j=0;j<192;j++)check(((u8*)entries)[j]==v->expectedEntries[j]);
 }return 0;}
 '''
 variants={'selected':body,
 'gate-count':body.replace('owner + 0x2C) < 2','owner + 0x2C) < 1'),
 'gate-bit':body.replace('(state[0x30] & 1)','(state[0x30] & 2)'),
 'phase-direction':body.replace('state[0x4C] +=','state[0x4C] -='),
 'delay-zero':body.replace('entry->delay > 0','entry->delay >= 0'),
 'expiry-zero':body.replace('entry->lifetime < 0','entry->lifetime <= 0'),
 'count-decrement':body.replace('owner + 0x2C) - 1','owner + 0x2C) - 2'),
 'float-rate':body.replace('D_800BE9A4 * *(f32 *)','-D_800BE9A4 * *(f32 *)'),
 'output-source':body.replace('entries[*(s8 *)(owner + 0x2D)].position','entries[0].position')}
 results=[]
 for label,fn in variants.items():
  assert label=='selected'or fn!=body,label
  for opt in(('-O0','-O2')if label=='selected'else('-O2',)):
   path=m.OUT/('native-'+label+opt+'.c');exe=path.with_suffix('');path.write_text(prefix+fn+suffix+START)
   start=time.monotonic();q=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=m.ROOT,capture_output=True,text=True);assert q.returncode==0 and not q.stderr,(label,q.stdout,q.stderr)
   p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==(0 if label=='selected'else 3),(label,opt,p.returncode)
   row=dict(label=label,opt=opt,exit_code=p.returncode,seconds=round(time.monotonic()-start,3));results.append(row);print(json.dumps(row),flush=True)
 report=dict(cases_per_selected_run=len(corpus),runs=results,native32=True,UB_traps=True,complete_owner_state_and_entries=True,all_count_bytes=True,valid_disjoint_native_storage=True,unsigned_wrapping_arithmetic=True,source_installed=m.installed(),c_match_credit=0)
 (m.OUT/'native.json').write_text(json.dumps(report,indent=2)+'\n');m.check_inputs()
if __name__=='__main__':main()
