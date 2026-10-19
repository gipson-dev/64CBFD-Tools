"""Complete semantic recovery, with the still-nonmatching layout kept explicit."""
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_category_boundaries_candidates as source
from tools.experiments import game_route_projection_integration as mixed
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_category_boundaries_oracle as oracle
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_projected_packet_draw import native_command


NATIVE=r'''
typedef unsigned char u8;typedef short s16;typedef unsigned int u32;typedef int s32;typedef float f32;
s16 D_80087290;u8 *D_800D2350;u8 D_800D2358,D_800D237C[16];f32 D_800D2360[7];
f32 D_8009D9C0=-10000.0f,D_8009D9C4=10000.0f,D_8009D9C8=100000.0f;
SOURCE_BODY
typedef struct {s32 count;u32 seed,nrows,poison,initialCount,active,result;
    s16 heights[32];u8 categories[32],initialIds[16],ids[16];u32 initialBounds[7],bounds[7];} Case;
static const Case cases[]={CASES};
static u8 rows[1024] __attribute__((aligned(16))),saved[1024];
static void reset(void){u32 i;D_800D2358=0xA5;for(i=0;i<16;i++)D_800D237C[i]=0xA5;
    for(i=0;i<7;i++)((u32 *)D_800D2360)[i]=0xA5A5A5A5u;}
static u32 simple(s32 active,s32 category){u32 i;if(D_800D2358!=active)return 21;
    for(i=0;i<16;i++)if(D_800D237C[i]!=(i==0 && active?(u32)category:0xA5))return 21;
    for(i=0;i<7;i++)if(((u32 *)D_800D2360)[i]!=(i==0?0x47C35000u:0xA5A5A5A5u))return 21;
    return 0;}
void _start(void){u32 failure=0,n,i,category; s32 value;const Case*c;
    if(sizeof(void*)!=4 || sizeof(s16)!=2 || sizeof(f32)!=4)failure=29;
    for(n=0;!failure && n<sizeof(cases)/sizeof(cases[0]);n++){
        c=cases+n;for(i=0;i<1024;i++)rows[i]=(u8)(i*137+c->seed*31+19);
        for(i=0;i<c->nrows;i++){*(s16 *)(rows+i*16+2)=c->heights[i];rows[i*16+6]=c->categories[i];}
        for(i=0;i<1024;i++)saved[i]=rows[i];D_80087290=(s16)c->count;D_800D2350=c->poison?(u8*)1:rows;
        D_800D2358=(u8)c->initialCount;
        for(i=0;i<16;i++)D_800D237C[i]=c->initialIds[i];
        for(i=0;i<7;i++)((u32 *)D_800D2360)[i]=c->initialBounds[i];
        if((u32)func_15085BE8()!=c->result || D_800D2358!=c->active)failure=21;
        for(i=0;i<16;i++)if(D_800D237C[i]!=c->ids[i])failure=21;
        for(i=0;i<7;i++)if(((u32 *)D_800D2360)[i]!=c->bounds[i])failure=21;
        for(i=0;i<1024;i++)if(rows[i]!=saved[i])failure=21;
        if(D_80087290!=(s16)c->count || D_800D2350!=(c->poison?(u8*)1:rows))failure=21;
    }
    for(category=0;!failure && category<6;category++)for(value=-32768;!failure && value<=32767;value++){
        reset();D_80087290=1;D_800D2350=rows;*(s16 *)(rows+2)=(s16)value;rows[6]=(u8)category;
        if(func_15085BE8()!=0)failure=21;else failure=simple(1,(s32)category);
    }
    for(value=-32768;!failure && value<=0;value++){
        reset();D_80087290=(s16)value;D_800D2350=(u8*)1;
        if(func_15085BE8()!=0)failure=21;else failure=simple(0,0);
    }
    __asm__ volatile("int $0x80"::"a"(1),"b"(failure));__builtin_unreachable();
}
'''


class CategoryBoundaryRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.values=source.freeze(cls.root,cls.out);cls.obj,cls.words,cls.row=source.compile_candidate(cls.root,cls.out,'qualified')
        cls.retail=list(struct.unpack_from('>112I',cls.values['conker/conker.us.bin'],source.ROM));cls.cases=list(oracle.cases())

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_complete_source_and_unresolved_instruction_layout(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['diagnostics']),(112,96,54,''))
        self.assertNotEqual(self.words,self.retail)
        self.assertEqual(self.values[source.SOURCE].count(source.ORIGINAL.encode()),1)
        guards=list(csv.DictReader(io.StringIO((self.root/'conker/retail_word_patches.us.csv').read_text())))
        self.assertFalse(any(r['function']==source.FUNCTION for r in guards))
        self.receipt('layout-boundary',words=112,frame=96,different_words=54,installed=False,guards_added=0,
            original_production_stub_preserved=True,raw_SHA256=self.row['raw_SHA256'])

    def test_02_independent_reference_and_ordered_public_stores(self):
        visits=set();raw_visits=set();runs=0
        for case in self.cases:
            for phase in (0,8):
                memory=oracle.fixture(case,phase);trace=[];wanted,after=oracle.reference(memory,trace=trace)
                public=oracle.public(memory)
                for words,coverage in ((self.retail,visits),(self.words,raw_visits)):
                    model=oracle.BoundaryModel(words,memory,phase).run()
                    self.assertEqual((model.r[2],oracle.public(model.memory)),(wanted,oracle.public(after)),case)
                    stores=[e[1:] for e in model.events if e[0]=='W' and e[1] in public]
                    self.assertEqual(stores,trace,case);self.assertFalse(model.calls);coverage.update(model.visits)
                runs+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+448,4)))
        self.assertEqual(raw_visits,set(range(source.ENTRY,source.ENTRY+448,4)))
        self.receipt('functional-cases',cases=len(self.cases),phases=2,paired_public_executions=runs,
            all112_retail_and_source_words_visited=True,ordered_public_stores_checked=True,
            private_register_memory_and_access_trace_equivalence_not_claimed=True)

    def native_rows(self):
        lines=[]
        fmt=lambda v:'{'+','.join(str(n) for n in v)+'}'
        words=lambda v:'{'+','.join('0x%Xu'%n for n in v)+'}'
        a=oracle.DEFAULT
        for case in self.cases:
            before=oracle.fixture(case);result,after=oracle.reference(before)
            count=len(case.rows) if case.count is None else case.count
            ids=lambda m:[oracle.read(m,a['D_800D237C']+i,1) for i in range(16)]
            bounds=lambda m:[oracle.read(m,a['D_800D2360']+i*4,4) for i in range(7)]
            lines.append('{%d,%d,%d,%d,%d,%d,%d,%s,%s,%s,%s,%s,%s}'%(
                count,case.seed,len(case.rows),case.poison,oracle.read(before,a['D_800D2358'],1),
                oracle.read(after,a['D_800D2358'],1),result,fmt([r[0] for r in case.rows]),fmt([r[1] for r in case.rows]),
                fmt(ids(before)),fmt(ids(after)),words(bounds(before)),words(bounds(after))))
        return ',\n'.join(lines)

    def test_03_native32_full_buffers_and_effective_source_negatives(self):
        bodies={'o0':source.FITTED,'o2':source.FITTED,'ubsan':source.FITTED,
            'wrong-signed-height':source.FITTED.replace('(f32)*(s16 *)','(f32)*(unsigned short *)'),
            'wrong-active-equality':source.FITTED.replace('minimum[i] <= maximum[i]','minimum[i] < maximum[i]'),
            'wrong-overlap-equality':source.FITTED.replace('if (lower < upper)','if (lower <= upper)'),
            'wrong-midpoint':source.FITTED.replace('(lower + upper)','(lower - upper)'),
            'wrong-sentinel':source.FITTED.replace('D_800D2360[i] = D_8009D9C8','D_800D2360[i] = 0.0f')}
        rows=self.native_rows();exits={}
        for name,body in bodies.items():
            path=self.out/('native-'+name+'.c');exe=path.with_suffix('')
            path.write_text(NATIVE.replace('SOURCE_BODY',body).replace('CASES',rows))
            argv=native_command('-O0' if name=='o0' else '-O2',name=='ubsan')+[
                '-mstackrealign','-fno-strict-aliasing','-o',str(exe),str(path)]
            subprocess.run(argv,cwd=self.root,check=True,capture_output=True)
            result=subprocess.run([str(exe)],capture_output=True);exits[name]=result.returncode
            self.assertEqual(result.returncode,0 if name in ('o0','o2','ubsan') else 21,(name,result.stderr))
        self.receipt('native-cases',fixtures=len(self.cases),full_input_bytes_checked=1024,all16_id_bytes_and7_boundary_words_checked=True,
            all_signed16_height_views_per_category=65536,all_nonpositive_signed16_count_views=32769,
            exits=exits,valid_categories0_through5_only=True,no_signal_or_trap_counted_as_success=True)

    def test_04_fired_retail_access_cuts_and_explicit_raw_order_boundary(self):
        cuts=0
        for case in (oracle.Case(),oracle.Case(((0,0),)),oracle.Case(((4,0),(1,1))),oracle.Case(((0,0),(0,1)))):
            for phase in (0,8):
                memory=oracle.fixture(case,phase);run=oracle.BoundaryModel(self.retail,memory,phase).run()
                for cut,event in enumerate(run.events):
                    model=oracle.BoundaryModel(self.retail,memory,phase);model.fault=cut
                    with self.assertRaises(oracle.core.AccessFault):model.run()
                    self.assertEqual((model.accesses,model.requested),(cut,event[:3]));cuts+=1
        memory=oracle.fixture(oracle.Case());models=[]
        for words in (self.retail,self.words):
            model=oracle.BoundaryModel(words,memory);model.fault=0
            with self.assertRaises(oracle.core.AccessFault):model.run()
            self.assertEqual(model.accesses,0);models.append(model)
        self.assertNotEqual(models[0].requested,models[1].requested)
        self.assertEqual(models[0].requested,('R',oracle.DEFAULT['D_8009D9C0'],4))
        self.assertEqual(models[1].requested,('R',oracle.DEFAULT['D_8009D9C4'],4))
        self.receipt('fired-cuts',retail_fired_cuts=cuts,first_access_boundary_fired_in_both=True,
            retail_first='D_8009D9C0',raw_first='D_8009D9C4',literal_fault_order_not_matched=True)

    def test_05_actual_returning_caller_window(self):
        rom=self.values['conker/conker.us.bin'];actual=list(struct.unpack_from('>6I',rom,0xB3080))
        self.assertEqual(actual,[0x0D4216FA,0,0x8FBF0014,0x27BD0018,0x03E00008,0])
        pairs=0
        for case in self.cases[::17]:
            for phase in (0,8):
                memory=oracle.fixture(case,phase);oracle.put(memory,oracle.STACK+phase-4,0xDEAD0000,4)
                wanted,after=oracle.reference(memory)
                for words in (self.retail,self.words):
                    model=oracle.BoundaryModel(actual,memory,phase,0x15085BD0)
                    model.r[29]=oracle.STACK+phase-24
                    model.code.update(zip(range(source.ENTRY,source.ENTRY+448,4),words));model.run()
                    self.assertEqual((model.r[2],oracle.public(model.memory)),(wanted,oracle.public(after)))
                    self.assertEqual(model.caller_args,[()])
                pairs+=1
        hits=[i for i in range(0,len(rom)-3,4) if rom[i:i+4]==b'\x0D\x42\x16\xFA']
        self.assertEqual(hits,[0xB3080])
        self.receipt('ABI-windows',actual_caller_words=6,returning_pairs=pairs,aligned_retail_JAL_hits=hits,
            caller_frame_livein_explicit=True,upstream_loader_not_executed=True,public_result_and_preserved_ABI_only=True)

    def test_06_independent_GNU_rebases_preserve_public_results_not_code_identity(self):
        asm=self.values['conker/asm/B3020.s'].decode();start=asm.index('glabel '+source.FUNCTION+'\n');end=asm.index('endlabel '+source.FUNCTION,start)
        original=self.out/'original.s';original.write_text((self.root/'conker/include/asm_processor_prelude.inc').read_text()+
            '\n.text\n.type '+source.FUNCTION+', @function\n'+asm[start:end]+'\n.size '+source.FUNCTION+', .-'+source.FUNCTION+'\n')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
            '-I',str(self.root/'conker/include'),'-o',str(original.with_suffix('.o')),str(original)],check=True,capture_output=True)
        count=0
        for n,(entry,delta,rows) in enumerate(((source.ENTRY,0,oracle.ROWS),(0x1621FFF4,0x118004,0x68000),(0x18FFF000,0x32FFFC,0x90000))):
            anchors={k:v+delta for k,v in oracle.DEFAULT.items()};images=[]
            for label,obj in (('retail',original.with_suffix('.o')),('raw',self.obj)):
                script=self.out/(label+'-map%d.ld'%n);elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
                images.append(list(struct.unpack('>112I',sections(elf)['.text'][1][:448])))
            self.assertNotEqual(*images)
            for case in self.cases[::29]:
                for phase in (0,8):
                    memory=oracle.fixture(case,phase,anchors,rows);wanted,after=oracle.reference(memory,anchors)
                    for words in images:
                        model=oracle.BoundaryModel(words,memory,phase,entry).run()
                        self.assertEqual((model.r[2],oracle.public(model.memory)),(wanted,oracle.public(after)))
                    count+=1
        self.receipt('GNU-maps',maps=3,executed_public_pairs=count,code_and_all8_anchors_and_rows_rebased=True,
            code_bytes_explicitly_still_different=True)

    def test_07_both_owner_profiles_actual_padding_and_frozen_production(self):
        same=mixed.candidate.source.neighbor.same_functions;profiles={}
        for label,normal in (('primary',False),('normal',True)):
            old,diag=source.compile_profile(self.root,self.out,self.values[source.SOURCE].decode(),'before-'+label,normal)
            new,_,row=source.compile_candidate(self.root,self.out,'after-'+label,normal=normal,whole=True)
            self.assertFalse(diag or row['diagnostics']);self.assertEqual(same(old,new,(source.FUNCTION,)),72)
            self.assertEqual(normalized_pools(old),normalized_pools(new));profiles[label]=new
        padded=mixed.padded(self.root,self.out,profiles['primary'],'private-padded',
            self.root/'conker/retail_word_patches.us.csv',profiles['normal'])
        baseline=self.root/'conker/build/src/game/generated_B3020.c.o'
        self.assertEqual(same(baseline,padded,(source.FUNCTION,)),72)
        self.assertEqual(normalized_pools(baseline),normalized_pools(padded))
        _,old_functions=source.link_owner(self.root,self.out,baseline,source.OWNER)
        image,functions=source.link_owner(self.root,self.out,padded,source.OWNER)
        self.assertEqual(old_functions.keys(),functions.keys())
        for name in functions:self.assertEqual(old_functions[name]['value'],functions[name]['value'],name)
        words=list(struct.unpack_from('>112I',image,functions[source.FUNCTION]['value']))
        self.assertEqual(words,self.words);self.assertEqual(sum(a!=b for a,b in zip(words,self.retail)),54)
        for name,value in self.values.items():self.assertEqual((self.root/name).read_bytes(),value,name)
        self.receipt('owner-isolation',neighbors_per_profile=72,padded_other_functions=72,pools_fixed=True,all_padded_function_addresses_fixed=True,
            actual_padding_still_different_words=54,all_frozen_production_inputs_unchanged=True,
            production_build_or_installation_performed=False)


if __name__=='__main__':unittest.main()
