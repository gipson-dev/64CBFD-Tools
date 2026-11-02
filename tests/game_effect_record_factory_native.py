"""Independent native32 controls for the effect-record factory."""

import json
import subprocess

from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START


def harness(selected):
    variants = [
        ("valid", selected),
        ("wrong_category", selected.replace("? 0x57 : 0x5D", "? 0x5D : 0x57")),
        ("wrong_count", selected.replace("pairCount > 0", "pairCount >= 0")),
        ("wrong_copy", selected.replace("descriptor, 0x58", "descriptor, 0x54")),
        ("wrong_size", selected.replace("extraBytes + 0x70", "extraBytes + 0x6C")),
        ("wrong_callback", selected.replace("(u8)callback", "(u8)(callback + 1)")),
        ("wrong_reject", selected.replace("if (func_151555AC(descriptor, position, pair, pairCount))",
                                           "if (0 && func_151555AC(descriptor, position, pair, pairCount))")),
    ]
    assert all(body != selected for _, body in variants[1:])
    text = r'''
typedef unsigned char u8; typedef unsigned short u16; typedef unsigned int u32;
typedef int s32; typedef float f32;
#define NULL ((void *)0)
static u8 *activeDescriptor, *activeRecord; static s32 rejectOverlap, allowAllocation, mutation;
static u32 logWords[32], logCount;
static void log(u32 value){if(logCount<32)logWords[logCount++]=value;}
static u32 fb(f32 value){union{f32 f;u32 u;}v;v.f=value;return v.u;}
s32 func_151555AC(u8 *descriptor,f32 *position,s32 *pair,s32 count){
 log(0xA1000000u);log(fb(position[0]));log(fb(position[1]));log((u32)count);log((u32)(pair!=NULL));
 if(mutation&1){descriptor[0x14]^=0x20;descriptor[2]^=0x5A;}return rejectOverlap;
}
void *func_15167A68(s32 category,s32 context,s32 bytes,s32 flag,u8 slot,u8 pool){
 log(0xA2000000u|(u32)category);log((u32)context);log((u32)bytes);log((u32)flag);log(slot);log(pool);
 if(mutation&2)activeDescriptor[3]^=0xA5;return allowAllocation?activeRecord:NULL;
}
void *memcpy(void *destination,const void *source,u32 count){u32 i;u8*d=destination;const u8*s=source;
 log(0xA3000000u|count);for(i=0;i<count;i++)d[i]=s[i];return destination;}
'''
    names = []
    for index, (_, body) in enumerate(variants):
        name = "candidate_%d" % index
        names.append(name)
        text += body.replace("void *func_1515548C(", "static void *%s(" % name) + "\n"
    text += r'''
static void *reference(u8 *descriptor,s32 callback,s32 *pair,s32 pairCount,
                       s32 extraBytes,u8 slot,s32 context){
 f32 position[2];u8*created;
 if(pair!=NULL&&pairCount>0){position[0]=*(f32*)(descriptor+8);position[1]=*(f32*)(descriptor+12);
  if(func_151555AC(descriptor,position,pair,pairCount))return NULL;}
 created=func_15167A68((*(u16*)(descriptor+0x14)&0x20)?0x57:0x5D,
  context,extraBytes+0x70,1,slot,1);if(created==NULL)return NULL;
 memcpy(created+0x10,descriptor,0x58);created[0x68]=0;created[0x68]|=(u8)callback;return created;
}
typedef void *(*Fn)(u8*,s32,s32*,s32,s32,u8,s32);
static Fn candidates[]={'''+','.join(names)+r'''};
static u8 initialDescriptor[128],initialRecord[224],descA[128],recordA[224],descB[128],recordB[224];
static u32 expectedLog[32];static s32 dummyPair[4];
static void copy(u8*d,const u8*s,u32 n){u32 i;for(i=0;i<n;i++)d[i]=s[i];}
static int equal(const u8*a,const u8*b,u32 n){u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static int run(void){u32 n,j,k,killed=0;for(n=0;n<256;n++){
 for(k=0;k<128;k++)initialDescriptor[k]=(u8)(k*29+n*7+0x51);
 for(k=0;k<224;k++)initialRecord[k]=(u8)(k*17+n*11+0xA5);
 *(u32*)(initialDescriptor+8)=0x3F800000u+n;*(u32*)(initialDescriptor+12)=0xBF000000u+n;
 *(u16*)(initialDescriptor+0x14)=(u16)((n&1)?0x20:0);
 {s32 branch=(s32)(n&3),count=branch==0?-1:(branch==1?0:(branch==2?1:3));
  s32 *pair=branch==0?NULL:dummyPair;rejectOverlap=(branch==3&&(n&4))?1:0;
  allowAllocation=n%7!=0;mutation=(s32)((n>>3)&3);copy(descA,initialDescriptor,128);copy(recordA,initialRecord,224);
  activeDescriptor=descA;activeRecord=recordA;logCount=0;
  {void*want=reference(descA,(s32)n,pair,count,(s32)(n*0x01020305u),(u8)n,(s32)(0x76540000u|n));
   u32 wantCount=logCount;for(k=0;k<32;k++)expectedLog[k]=logWords[k];
   for(j=0;j<7;j++){void*got;int failed=0;copy(descB,initialDescriptor,128);copy(recordB,initialRecord,224);
    activeDescriptor=descB;activeRecord=recordB;logCount=0;
    got=candidates[j](descB,(s32)n,pair,count,(s32)(n*0x01020305u),(u8)n,(s32)(0x76540000u|n));
    if((got!=NULL)!=(want!=NULL)||logCount!=wantCount||!equal(descA,descB,128)||!equal(recordA,recordB,224))failed=1;
    for(k=0;k<wantCount;k++)if(logWords[k]!=expectedLog[k])failed=1;
    if(!j&&failed)return 2;if(j&&failed)killed|=1u<<(j-1);
   }
  }
 }}return killed==63u?0:3;}
'''
    return text + START.replace("void _start(void)",
        "__attribute__((force_align_arg_pointer)) void _start(void)")


def qualify(root, output, selected):
    source = output / "native_harness_v1.c"
    source.write_text(harness(selected))
    profiles = []
    for option in ("-O0", "-O2", "-O3"):
        executable = output / ("native-v1-" + option[1:])
        build = subprocess.run(native_command(option) + ["-fno-strict-aliasing",
            "-ffp-contract=off", str(source), "-o", str(executable)], cwd=root,
            capture_output=True, text=True)
        if build.returncode or build.stderr:
            raise ValueError((option, build.stdout, build.stderr))
        run = subprocess.run([str(executable)], capture_output=True)
        if run.returncode:
            raise ValueError((option, run.returncode, run.stderr))
        profiles.append({"optimization": option, "cases": 256,
                         "negative_controls": 6, "UBSan_clean": True,
                         "complete_descriptor_and_record_canaries": True})
    report = {
        "success": True, "private_only": True, "matching_credit": 0,
        "profiles": profiles, "total_executions": 768,
        "all256_callback_and_slot_bytes": True,
        "overlap_and_allocation_branches": True,
        "both_category_flags": True,
        "live_descriptor_mutations": True,
        "complete_128_and_224_byte_images_checked": True,
    }
    (output / "private-native-v1.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
