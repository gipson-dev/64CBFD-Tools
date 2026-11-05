"""Lazy resource loading, live cache/count mutations, private spills and callers."""

from dataclasses import dataclass
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_resource_cache_acquire_candidates as candidate
from tools.experiments import game_resource_cache_acquire_match as match
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.pad_generated_object import emit_padded_assembly
from tools.tests.game_frame_timing_oracle import TimingOracle, STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests import test_game_actor_burst_consumer_match as faults


ROOT=candidate.ROOT
COUNTS,LISTS,CACHE=0x800DF7D0,0x800DF9B8,0x800E0148
LOAD,PREPARE,ATTACH=0x1502B6BC,0x1510CE60,0x15168E54
HEADER,CACHED,LIST=0x22000,0x24000,0x26000
ALT_KIND,ALT_DATA,FINAL_DATA=42,0x13572468,0x89ABCDEF
MASK=0xFFFFFFFF


def cell(base,kind,stride=1):return (base+(kind&MASK)*stride)&MASK


@dataclass(frozen=True)
class Case:
    kind:int=166
    count:int=0
    success:bool=True
    plan:int=0
    phase:int=0


def fixture(case):
    memory={STACK+case.phase+i:(i*17+0xA5)&255 for i in range(-0x200,0x200)}
    for kind in (case.kind,ALT_KIND):
        memory[cell(COUNTS,kind)]=case.count if kind==case.kind else 253
        put(memory,cell(LISTS,kind,4),0x31415926)
        put(memory,cell(CACHE,kind,4),CACHED)
    for base in (HEADER,CACHED):
        for i in range(16):memory[base+i]=(i*13+0x59)&255
        put(memory,base,0x12345678 if base==HEADER else 0x76543210)
    return memory


def public(memory):
    return {at:value for at,value in memory.items() if not STACK-0x200<=at<STACK+0x200}


def effect(memory,case,role,kind):
    if role==LOAD and case.plan==1:memory[cell(COUNTS,case.kind)]=254
    if role==PREPARE:
        put(memory,cell(LISTS,kind,4),LIST)
        if case.plan==2:memory[cell(COUNTS,case.kind)]=255
        if case.plan==4:put(memory,HEADER,ALT_DATA)
    if role==ATTACH:
        if case.plan==3:
            memory[cell(COUNTS,case.kind)]=0;put(memory,HEADER,FINAL_DATA)
        if case.plan==5:put(memory,cell(CACHE,kind,4),CACHED)
        if case.plan==6:memory[cell(COUNTS,case.kind)]=127


def reference(initial,case):
    memory=dict(initial);calls=[]
    count_at=cell(COUNTS,case.kind);kind=case.kind
    if memory[count_at]==0:
        calls.append((LOAD,(0,0,0,2,9,case.kind&MASK)))
        effect(memory,case,LOAD,kind)
        if not case.success:return memory,calls,0
        if case.plan==7:kind=ALT_KIND
        if case.plan==9:count_at=cell(COUNTS,ALT_KIND)
        cached_kind=kind
        calls.append((PREPARE,(read(memory,HEADER),0,1,0x3E,cell(LISTS,kind,4))))
        effect(memory,case,PREPARE,kind)
        calls.append((ATTACH,(read(memory,HEADER),HEADER)))
        effect(memory,case,ATTACH,kind)
        if case.plan==10:count_at=cell(COUNTS,ALT_KIND)
        if case.plan==11:cached_kind=ALT_KIND
        put(memory,cell(CACHE,cached_kind,4),HEADER)
        resource=HEADER
    else:resource=read(memory,cell(CACHE,kind,4))
    if memory[count_at]!=255:memory[count_at]+=1
    return memory,calls,read(memory,resource)


class CacheOracle(TimingOracle):
    def __init__(self,words,memory,case,natural=False,entry=match.ENTRY,connected=None):
        super().__init__(words,memory,phase=case.phase,entry=entry,
                         arguments=(case.kind&MASK,),connected=connected)
        self.case,self.natural=case,natural
        self.target_frame=STACK+case.phase-0x40

    def record_call(self,target):
        sizes={LOAD:6,PREPARE:5,ATTACH:2,match.ENTRY:1}
        if target not in sizes:raise AssertionError("Unexpected cache helper %08X"%target)
        args=tuple(self.arguments(sizes[target]))
        self.calls.append((target,args));self.events.append(("CALL",target,args))

    def hook(self,target):
        case=self.case
        if target not in (LOAD,PREPARE,ATTACH):raise AssertionError("Missing connected cache routine")
        kind=ALT_KIND if case.plan==7 else case.kind
        if target==LOAD:result=HEADER if case.success else 0
        elif target==PREPARE:result=MASK if case.plan&1 else 0
        else:result=0xBADC0DE
        effect(self.memory,case,target,kind)
        if target==LOAD and case.plan==7:self.put(self.target_frame+0x40,ALT_KIND,4)
        if target==PREPARE and case.plan==8:self.put(self.target_frame+0x40,ALT_KIND,4)
        count_home=0x34 if self.natural else 0x38
        index_home=0x28 if self.natural else 0x2C
        if target==LOAD and case.plan==9:self.put(self.target_frame+count_home,cell(COUNTS,ALT_KIND),4)
        if target==ATTACH and case.plan==10:self.put(self.target_frame+count_home,cell(COUNTS,ALT_KIND),4)
        if target==ATTACH and case.plan==11:self.put(self.target_frame+index_home,ALT_KIND*4,4)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA6000000+i for i in range(20)]
        self.r[2]=result


def controls():
    replacements={
        "wrong-miss-gate":("if (*count == 0)","if (*count != 0)"),
        "wrong-load-category":("NULL, 2, 9, kind","NULL, 2, 8, kind"),
        "wrong-load-depth":("NULL, 2, 9, kind","NULL, 1, 9, kind"),
        "wrong-load-kind":("NULL, 2, 9, kind","NULL, 2, 9, kind + 1"),
        "wrong-failure-return":("return 0;","return 1;"),
        "wrong-prepare-retain":("resource[0], 0, 1, 0x3E","resource[0], 0, 0, 0x3E"),
        "wrong-prepare-priority":("resource[0], 0, 1, 0x3E","resource[0], 0, 1, 0x3F"),
        "wrong-output-cell":("&D_800DF9B8[kind]","&D_800DF9B8[(kind + 1) % 485]"),
        "wrong-attach-order":("func_15168E54((void *)resource[0], resource);","func_15168E54(resource, (void *)resource[0]);"),
        "missing-attach":("func_15168E54((void *)resource[0], resource);","(void)resource;"),
        "missing-cache-publish":("D_800E0148[kind] = resource;","(void)resource;"),
        "wrong-cache-cell":("D_800E0148[kind] = resource;","D_800E0148[(kind + 1) % 485] = resource;"),
        "wrong-saturation":("*count != 0xFF","*count != 0xFE"),
        "double-retain":("(*count)++;","*count += 2;"),
        "wrong-return-field":("return resource[0];","return resource[1];"),
    }
    result={name:candidate.SELECTED.replace(old,new,1) for name,(old,new) in replacements.items()}
    early=candidate.SELECTED.replace('        func_15168E54((void *)resource[0], resource);\n        D_800E0148[kind] = resource;',
        '        D_800E0148[kind] = resource;\n        func_15168E54((void *)resource[0], resource);',1)
    result['early-cache-publication']=early
    if any(body==candidate.SELECTED for body in result.values()):raise AssertionError("Ineffective cache control")
    return result


def native_source(body):
    return r'''#include <stdarg.h>
typedef unsigned char u8;typedef signed short s16;typedef signed int s32;typedef unsigned int u32;
#define NULL ((void *)0)
u8 D_800DF7D0[485];s16 *D_800DF9B8[485];s32 *D_800E0148[485];
''' + candidate.DECLARATIONS + body + r'''
static s32 header[4],cached[4];static s16 list[4];
static u32 kind,plan,success,step,error;
static u32 prep_data,attached_data;
void *func_1502B6BC(s32 *a,s32 b,s32 *c,s32 depth,...) {
    va_list args;s32 category,index;va_start(args,depth);category=va_arg(args,s32);index=va_arg(args,s32);va_end(args);
    if(step++!=0 || a || b || c || depth!=2 || category!=9 || (u32)index!=kind)error=1;
    if(plan==1)D_800DF7D0[kind]=254;
    return success?header:NULL;
}
s32 func_1510CE60(void *data,s32 unresolved,s32 retain,s32 priority,s32 *output) {
    if(step++!=1 || (u32)data!=prep_data || unresolved || retain!=1 || priority!=0x3E || output!=(s32 *)&D_800DF9B8[kind])error=1;
    D_800DF9B8[kind]=list;
    if(plan==2)D_800DF7D0[kind]=255;
    if(plan==4)header[0]=(s32)0x13572468;
    return (plan&1)?-1:0;
}
void func_15168E54(void *data,void *resource) {
    if(step++!=2 || (u32)data!=attached_data || resource!=header)error=1;
    if(plan==3){D_800DF7D0[kind]=0;header[0]=(s32)0x89ABCDEF;}
    if(plan==5)D_800E0148[kind]=cached;
    if(plan==6)D_800DF7D0[kind]=127;
}
static s32 run(void) {
    static const u32 kinds[6]={0,1,166,184,186,483};
    static const u8 counts[6]={0,1,127,128,254,255};
    u32 seed,i,initial,expected_count,expected_data,expected_steps,failed; s32 actual;
    if(sizeof(void *)!=4)return 9;
    for(seed=0;seed<4096;seed++) {
        kind=kinds[seed%6];initial=counts[(seed/6)%6];success=(seed/36)&1;plan=(seed/72)%7;
        for(i=0;i<485;i++){D_800DF7D0[i]=77;D_800DF9B8[i]=(s16 *)0x31415926;D_800E0148[i]=cached;}
        D_800DF7D0[kind]=(u8)initial;header[0]=0x12345678;header[1]=0x55AA;cached[0]=0x76543210;cached[1]=0xAA55;
        expected_count=initial;expected_data=(u32)cached[0];expected_steps=0;failed=0;
        prep_data=(u32)header[0];attached_data=plan==4?0x13572468:prep_data;
        if(!initial) {
            expected_steps=1;
            if(plan==1)expected_count=254;
            if(!success){failed=1;expected_data=0;}
            else {
                expected_steps=3;expected_data=plan==4?0x13572468:0x12345678;
                if(plan==2)expected_count=255;
                if(plan==3){expected_count=0;expected_data=0x89ABCDEF;}
                if(plan==6)expected_count=127;
            }
        }
        if(!failed && expected_count!=255)expected_count++;
        error=step=0;actual=func_1518C900((s32)kind);
        if(error || step!=expected_steps || (u32)actual!=expected_data)return 10;
        for(i=0;i<485;i++) {
            if(D_800DF7D0[i]!=(i==kind?expected_count:77))return 11;
            if(D_800DF9B8[i]!=(i==kind && !initial && success?list:(s16 *)0x31415926))return 12;
            if(D_800E0148[i]!=(i==kind && !initial && success?header:cached))return 13;
        }
    }
    return 0;
}
void _start(void){s32 code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code));__builtin_unreachable();}
'''


def run_native(label,body,optimization,should_pass):
    output=ROOT/match.BUILD/"native";output.mkdir(parents=True,exist_ok=True)
    source,binary=output/(label+".c"),output/(label+".elf");source.write_text(native_source(body))
    result=subprocess.run(["gcc","-m32","-std=gnu89",optimization,"-fno-pie","-no-pie",
        "-ffreestanding","-fno-strict-aliasing","-fno-stack-protector","-fsanitize=undefined",
        "-fsanitize-undefined-trap-on-error","-Wall","-Wextra","-Werror","-nostdlib",
        str(source),"-o",str(binary)],capture_output=True,text=True)
    if result.returncode:raise AssertionError(result.stdout+result.stderr)
    executed=subprocess.run([str(binary)],timeout=30)
    if should_pass!=(executed.returncode==0):raise AssertionError((label,executed.returncode))


class WindowDone(Exception):pass


class WindowCode(faults.TrackedCode):
    def __init__(self,code,model,stop):super().__init__(code,model);self.stop=stop
    def __getitem__(self,pc):
        if pc==self.stop:raise WindowDone
        return super().__getitem__(pc)


class ResourceCacheAcquireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prepared=match.prepare(ROOT);cls.out=ROOT/match.BUILD
        cls.rom=(ROOT/match.ROM_IMAGE).read_bytes()
        cls.retail=list(struct.unpack_from('>65I',cls.rom,match.ROM))
        selected=candidate.compare()
        if selected["words"]!=65 or [r["offset"] for r in selected["differences"]]!=[r[0] for r in match.GUARD_WORDS]:
            raise AssertionError(selected)
        cls.natural=cls.retail.copy()
        for at,old,new in match.GUARD_WORDS:
            if cls.retail[at//4]!=new:raise AssertionError("Cache retail guard changed")
            cls.natural[at//4]=old

    def receipt(self,name,value):
        (self.out/(name+".json")).write_text(json.dumps(value,indent=2)+"\n")

    def compare(self,case):
        initial=fixture(case);expected,calls,result=reference(initial,case);models=[]
        for natural,words in ((False,self.retail),(True,self.natural)):
            model=CacheOracle(words,initial,case,natural).run()
            self.assertEqual(public(model.memory),public(expected),case)
            self.assertEqual(model.calls,calls,case);self.assertEqual(model.r[2],result,case)
            models.append(model)
        return models

    def test_01_owner_guard_preimages_caller_prototype_and_literal_image(self):
        report=self.prepared["report"]
        self.assertEqual((report["words"],report["guards"],report["neighbors"],report["relocations"]),(65,6,1,11))
        self.assertTrue(report["caller_prototype"]["padded_owner_byte_identical"])
        self.assertEqual(report["changed_bodies"],[match.FUNCTION])
        self.assertEqual(report["strict_changed_bytes"],197)
        for at,old,new in match.GUARD_WORDS:
            self.assertEqual(old&0xFFFF0000,new&0xFFFF0000)
            self.assertEqual((new&65535)-(old&65535),4)
            self.assertEqual(old>>21&31,29);self.assertIn(old>>26,(35,43))
        for index in range(len(match.PATCH_ROWS)):
            rows=self.prepared["predecessor_rows"]+[match.complete_row(r) for r in match.PATCH_ROWS]
            rows=[dict(row) for row in rows]
            rows[len(self.prepared["predecessor_rows"])+index]["expected"]="0x%08X"%(match.GUARD_WORDS[index][1]^1)
            path=self.out/("bad-guard-%d.csv"%index)
            harness.write_patches(path,self.prepared["fields"],rows)
            with self.assertRaises(ValueError):emit_padded_assembly(self.prepared["qualified_compact"],ROOT/match.ASM,
                word_patches_path=path,filename=match.FILENAME)
        before,after=self.prepared["predecessor_elf"].read_bytes(),self.prepared["qualified_elf"].read_bytes()
        for at in (0x80,elf_slot_offset(before,match.ENTRY,match.SIZE)):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),self.rom[match.ROM:match.ROM+match.SIZE])

    def test_02_lazy_loading_saturation_helper_mutations_and_all_words(self):
        coverage=[set(),set()];count=0
        cases=(Case(*args) for args in itertools.product((0,1,166,184,186,484),(0,1,127,128,254,255),
                (False,True),range(7),(0,8)))
        for case in itertools.chain(cases,(Case(kind,value,phase=phase) for kind,value,phase in
                itertools.product((0,1,166,184,186,484),range(256),(0,8)))):
            for i,model in enumerate(self.compare(case)):coverage[i].update(model.visits)
            count+=1
        full=set(range(match.ENTRY,match.ENTRY+match.SIZE,4));self.assertEqual(coverage,[full,full])
        self.receipt("guest-contract",{"cases_per_body":count,"covered_words":65,
            "all_256_byte_counts":True,"public_provider_plans":7})

    def test_03_sparse_guest_indices_and_private_spill_roles(self):
        count=0
        self.assertEqual(cell(LISTS,484,4),cell(CACHE,0,4))
        for model in self.compare(Case(kind=484)):
            self.assertEqual(read(model.memory,cell(CACHE,0,4)),LIST)
            self.assertEqual(read(model.memory,cell(CACHE,484,4)),HEADER)
        count+=1
        for kind,value,success,phase in itertools.product((-1,0x7FFFFFFF,-0x80000000,483),
                (0,1,255),(False,True),(0,8)):
            self.compare(Case(kind,value,success,phase=phase));count+=1
        for plan,phase in itertools.product(range(7,12),(0,8)):
            self.compare(Case(plan=plan,phase=phase));count+=1
        self.receipt("guest-private-and-indices",{"cases_per_body":count,"private_plans":5,
            "count_home_natural":52,"count_home_retail":56,"index_home_natural":40,"index_home_retail":44,
            "sparse_indices_guest_only":True,"kind_484_list_cell_aliases_cache_zero":True})

    def test_04_native32_and_effective_semantic_controls(self):
        for optimization in ("-O0","-O2","-O3"):run_native("positive"+optimization[1:],candidate.SELECTED,optimization,True)
        for name,body in controls().items():run_native("control-"+name,body,"-O2",False)
        self.receipt("native-contract",{"profiles":["O0","O2","O3"],"cases_per_profile":4096,"controls":sorted(controls())})

    def test_05_fault_boundaries_and_all_six_original_call_sites(self):
        observations=[]
        for case in (Case(),Case(success=False),Case(count=1),Case(count=255),Case(plan=4),Case(plan=3)):
            initial=fixture(case)
            for natural,words in ((False,self.retail),(True,self.natural)):
                baseline=CacheOracle(words,initial,case,natural).run()
                for cut in range(baseline.root_accesses):
                    model=CacheOracle(words,initial,case,natural);model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):model.run()
                    self.assertEqual(model.root_accesses,cut)
                    observations.append((model.current_pc,model.delay_of,cut))
        count=0
        for ordinal,rom in enumerate(match.CALLS):
            entry=rom-0x2D4B0+0x15000000;stop=entry+8
            window=list(struct.unpack_from('>2I',self.rom,rom))
            target={match.ENTRY+i*4:w for i,w in enumerate(self.retail)}|{stop:0}
            for value,success,plan,phase in itertools.product((0,1,254,255),(False,True),(0,3,4),(0,8)):
                kind=(184,186,166,166,166,166)[ordinal]
                case=Case(kind,value,success,plan,phase);initial=fixture(case)
                expected,calls,result=reference(initial,case)
                caller_record=0x2A000
                for i in range(8):initial[caller_record+i]=0xA5;expected[caller_record+i]=0xA5
                put(initial,caller_record,kind,2);put(expected,caller_record,kind,2)
                model=CacheOracle(window,initial,case,entry=entry,connected=target)
                if ordinal==3:model.r[16]=kind
                if ordinal==4:model.r[16]=caller_record
                if ordinal==5:
                    model.f[10]=0x3F400000;put(expected,STACK+phase+0x84,0x3F400000)
                model.before=model.r.copy();model.code=WindowCode(model.code,model,stop)
                with self.assertRaises(WindowDone):model.run()
                self.assertEqual(public(model.memory),public(expected))
                self.assertEqual(model.calls,[(match.ENTRY,(kind,))]+calls)
                self.assertEqual(model.r[2],result)
                if ordinal==5:self.assertEqual(read(model.memory,STACK+phase+0x84),0x3F400000)
                count+=1
        self.receipt("faults-and-callers",{"fault_observations":len(observations),
            "unique_boundaries":len(set(observations)),"caller_cases":count,"original_call_sites":6,
            "scope":"original JAL and argument/delay-slot window; complete callers remain separate"})


if __name__=="__main__":unittest.main()
