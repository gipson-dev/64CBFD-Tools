"""Record release: ordered aliases, float32 capture, caller windows and exact image."""
from copy import deepcopy
from dataclasses import replace
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_record_release_candidates as source
from tools.experiments import game_record_release_layout as layout
from tools.experiments import game_record_release_integration as integration
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_record_release_oracle as oracle
from tools.tests.test_game_packed_peer_lookup_match import state
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.pad_generated_object import emit_padded_assembly


NATIVE=r'''
typedef unsigned char u8;typedef unsigned int u32;typedef int s32;typedef float f32;
s32 D_800D23B0;u8 D_800CC2D0[26*0x32C] __attribute__((aligned(16)));
SOURCE_BODY
typedef struct {s32 slot,record,mode,nextState;u32 flags,coords[3],seed,null,start,count,result;} Case;
static const Case cases[]={CASES};static const u32 patches[]={PATCHES};
static u32 a[1408] __attribute__((aligned(16))),b[1408] __attribute__((aligned(16))),wanted[8094];
static u32 *cell(u32 i){return i<1408?a+i:i<2816?b+i-1408:(u32 *)D_800CC2D0+i-2816;}
static u32 pattern(u32 i,u32 seed,u32 bank){return (i*0x1020305u)^(seed*0x01010101u)^(bank*0x11223344u)^0xA53C719Bu;}
void _start(void){
    u32 failure=0,n,i,at,offset,actorOffset;const Case *c;
    if(sizeof(void*)!=4 || sizeof(f32)!=4)failure=29;
    for(n=0;!failure && n<sizeof(cases)/sizeof(cases[0]);n++){
        c=cases+n;
        for(i=0;i<1408;i++){a[i]=pattern(i,c->seed,0);b[i]=pattern(i,c->seed,1);}
        for(i=0;i<5278;i++)((u32 *)D_800CC2D0)[i]=pattern(i,c->seed,2);
        a[0xEAC/4]=b[0xEAC/4]=(u32)c->nextState;
        offset=((u32)c->slot*4+0xEB0)/4;
        if(offset>=1408){failure=29;break;}a[offset]=b[offset]=(u32)c->record;
        if(c->record>=0){offset=((u32)c->record*4+0x11F4)/4;a[offset]=b[offset]=c->flags;}
        actorOffset=(u32)c->slot*0x32C;
        if(actorOffset<=26*0x32C-0x20)for(i=0;i<3;i++)((u32 *)D_800CC2D0)[actorOffset/4+5+i]=c->coords[i];
        D_800D23B0=c->null?0:(s32)a;
        for(i=0;i<8094;i++)wanted[i]=*cell(i);
        for(i=0;i<c->count;i++){at=c->start+i*2;wanted[patches[at]]=patches[at+1];}
        if((u32)func_1508DAEC(c->slot,c->mode)!=c->result)failure=21;
        if(D_800D23B0!=(c->null?0:(s32)a))failure=21;
        for(i=0;i<8094;i++)if(*cell(i)!=wanted[i])failure=21;
    }
    __asm__ volatile("int $0x80"::"a"(1),"b"(failure));__builtin_unreachable();
}
'''


class RecordReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.values=source.freeze(cls.root,cls.out);cls.obj,cls.raw_words,cls.row=source.compile_candidate(cls.root,cls.out,'qualified')
        cls.raw,cls.bindings=source.payload(cls.obj);cls.normalized,cls.moved=layout.normalize(cls.raw,cls.bindings)
        cls.words=layout.relocate(cls.normalized,cls.moved,oracle.DEFAULT)
        cls.retail=list(struct.unpack_from('>78I',cls.values['conker/conker.us.bin'],source.ROM));cls.cases=list(oracle.cases())

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_all_words_register_only_recipe_and_FP_fields(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['diagnostics']),(78,0,7,''))
        self.assertEqual(self.words,self.retail);self.assertEqual(self.moved,self.bindings);self.assertEqual(len(self.bindings),4)
        for a,b in zip(struct.unpack('>78I',self.raw),struct.unpack('>78I',self.normalized)):
            if a>>26==17:self.assertEqual(a,b)
            if a>>26==49:self.assertEqual(a&~(31<<21),b&~(31<<21))
        guards=layout.private_guards(self.values['conker/retail_word_patches.us.csv'],self.raw,self.bindings)
        self.assertTrue(guards.startswith(self.values['conker/retail_word_patches.us.csv']))
        rows=[r for r in csv.DictReader(io.StringIO(guards.decode())) if r['filename']==source.OWNER and r['function']==source.FUNCTION]
        self.assertEqual(len(rows),7);self.assertTrue(all(not r['insert_after'] and r['omit']=='false' for r in rows))

    def test_02_independent_query_release_float_and_ordered_alias_reference(self):
        visits=set();pairs=redirects=0;layouts=set()
        for case in self.cases:
            for phase in (0,8):
                memory,args,_,_=oracle.fixture(case,phase);trace=[];result,after=oracle.reference(memory,args,trace=trace)
                models=[oracle.ReleaseModel(words,memory,args,phase).run() for words in (self.retail,self.words,self.raw_words)]
                self.assertEqual(state(models[0]),state(models[1]),case)
                for model in models:
                    self.assertEqual((model.r[2],oracle.public(model.memory)),(result,oracle.public(after)),case)
                    self.assertEqual([e[1:] for e in model.events if e[0]=='W'],trace,case);self.assertFalse(model.calls)
                    self.assertIn(model.conversions,(0,3))
                if oracle.read(after,oracle.STATE,4)!=oracle.read(memory,oracle.STATE,4):redirects+=1
                if case.layout:layouts.add(case.layout)
                visits.update(models[0].visits);pairs+=1
        self.assertEqual(visits,set(range(source.ENTRY,source.ENTRY+312,4)));self.assertEqual(layouts,set(range(1,9)))
        self.receipt('functional-cases',cases=len(self.cases),phases=2,paired_literal_runs=pairs,raw_public_same_corpus=pairs,
            all78_words_visited=True,ordered_stores_and_result_checked=True,context_redirection_executions=redirects,
            alias_layouts=sorted(layouts),wide_indices_guest_only=True)

    def test_03_fired_access_cuts_and_invalid_pointer_prefixes(self):
        count=0
        cases=(oracle.Case(null=True),oracle.Case(record=-1),oracle.Case(mode=-1),oracle.Case(flags=2),
            oracle.Case(mode=0),oracle.Case(),oracle.Case(layout=1),oracle.Case(layout=2),oracle.Case(layout=7),oracle.Case(layout=8))
        for case in cases:
            for phase in (0,8):
                memory,args,_,_=oracle.fixture(case,phase);run=oracle.ReleaseModel(self.retail,memory,args,phase).run()
                for cut in range(run.accesses):
                    models=[]
                    for words in (self.retail,self.words):
                        model=oracle.ReleaseModel(words,memory,args,phase);model.fault=cut
                        with self.assertRaises(oracle.core.AccessFault):model.run()
                        self.assertEqual(model.accesses,cut);models.append(model)
                    self.assertEqual((state(models[0]),models[0].requested),(state(models[1]),models[1].requested));count+=1
        prefixes=[]
        slot=0x20000000;context=(oracle.STATE-0xEB0-slot*4)&0xFFFFFFFF
        memory,args,_,_=oracle.fixture(oracle.Case(slot,0,0));oracle.put(memory,oracle.STATE,context,4)
        prefixes.append((memory,args,4,('R',(0xFFFFFFFF+context*4+0x11F4)&0xFFFFFFFF,4)))
        for offset,cut,request in ((0xF70,7,('W',0x10EF,4)),(0x10F0,9,('R',0xEAB,4))):
            memory,args,_,_=oracle.fixture(oracle.Case(mode=0),banks=(oracle.STATE-offset,oracle.BANKS[1]));prefixes.append((memory,args,cut,request))
        for memory,args,cut,request in prefixes:
            models=[]
            for words in (self.retail,self.words):
                model=oracle.ReleaseModel(words,memory,args);model.fault=cut
                with self.assertRaises(oracle.core.AccessFault):model.run()
                self.assertEqual((model.accesses,model.requested),(cut,request));models.append(model)
            self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(oracle.read(models[0].memory,oracle.STATE,4),0xFFFFFFFF)
        self.receipt('fired-cuts',pairs=count,all_requested_cuts_fired=True,invalid_pointer_prefix_pairs=len(prefixes),
            before_alignment_or_invalid_memory_access=True,not_hardware_exception_evidence=True)

    def test_04_invalid_FP_load_and_finite_conversion_dispatch_boundaries(self):
        load_pairs=conversion_pairs=0
        base=oracle.Case(coords=tuple(map(oracle.bits,(1.75,-49.5,-1.75))))
        for axis in range(3):
            valid,args,_,actor=oracle.fixture(base);run=oracle.ReleaseModel(self.retail,valid,args).run()
            address=actor+0x14+axis*4;cut=next(i for i,e in enumerate(run.events) if e[:3]==('R',address,4))
            for value in (0x7F800001,0x7FC00000,0x7F800000,0xFF800000,0x4F000000,0xCF000001):
                coords=list(base.coords);coords[axis]=value;case=replace(base,coords=tuple(coords))
                for phase in (0,8):
                    memory,args,_,_=oracle.fixture(case,phase);models=[]
                    for words in (self.retail,self.words):
                        model=oracle.ReleaseModel(words,memory,args,phase);model.fault=cut
                        with self.assertRaises(oracle.core.AccessFault):model.run()
                        self.assertEqual((model.accesses,model.requested),(cut,('R',address,4)));models.append(model)
                    self.assertEqual(state(models[0]),state(models[1]));load_pairs+=1
            for value in (0x4F000000,0xCF000001):
                coords=list(base.coords);coords[axis]=value;case=replace(base,coords=tuple(coords))
                for phase in (0,8):
                    memory,args,_,_=oracle.fixture(case,phase);models=[]
                    for words in (self.retail,self.words):
                        model=oracle.ReleaseModel(words,memory,args,phase);model.stop_conversion=axis
                        with self.assertRaises(oracle.ConversionBoundary):model.run()
                        self.assertEqual(model.conversions,axis)
                        self.assertIsNotNone(model.conversion_word)
                        with self.assertRaises(ValueError):oracle.truncate(model.f[model.conversion_word>>11&31])
                        models.append(model)
                    self.assertEqual(state(models[0]),state(models[1]));conversion_pairs+=1
        self.receipt('FP-boundaries',invalid_load_cut_pairs=load_pairs,finite_out_of_range_conversion_dispatch_pairs=conversion_pairs,
            every_requested_gate_fired=True,invalid_conversions_not_executed=True,FCSR_traps_and_invalid_results_not_modeled=True)

    def test_05_native32_full_buffers_float32_and_effective_negatives(self):
        rows=[];patches=[];number=lambda v:'0x%Xu'%(v&0xFFFFFFFF)
        for case in oracle.native_cases():
            before,args,_,_=oracle.fixture(case);result,after=oracle.reference(before,args);start=len(patches)
            changed=sorted({a&~3 for a,v in after.items() if before.get(a)!=v})
            for at in changed:
                if oracle.BANKS[0]<=at<oracle.BANKS[0]+oracle.SIZE:index=(at-oracle.BANKS[0])//4
                elif oracle.BANKS[1]<=at<oracle.BANKS[1]+oracle.SIZE:index=1408+(at-oracle.BANKS[1])//4
                elif oracle.ACTORS<=at<oracle.ACTORS+26*0x32C:index=2816+(at-oracle.ACTORS)//4
                else:self.fail(('Unexpected native write',case,hex(at)))
                patches.extend((index,oracle.read(after,at,4)))
            rows.append('{%d,%d,%d,%d,%s,{%s},%d,%d,%d,%d,%d}'%(oracle.signed(case.slot&0xFFFFFFFF),case.record,case.mode,
                case.next_state,number(case.flags),','.join(map(number,case.coords)),case.seed,int(case.null),start,(len(patches)-start)//2,result))
        template=NATIVE.replace('CASES',',\n'.join(rows)).replace('PATCHES',','.join(map(number,patches)));body=source.FITTED
        controls={'o0':body,'o2':body,'ubsan':body,
            'wrong-query':body.replace('mode < 0','mode < -1'),
            'wrong-flag':body.replace('0x11F4) & 2','0x11F4) & 1'),
            'wrong-record-clear':body.replace('0xF70) = -1','0xF70) = 0'),
            'wrong-double-height':body.replace('+ 50.0f','+ 50.0'),
            'wrong-truncate-first':body.replace('(s32)(*(f32 *)(actor + 0x18) + 50.0f)','((s32)*(f32 *)(actor + 0x18) + 50)')}
        exits={}
        for name,unit in controls.items():
            if name not in ('o0','o2','ubsan'):self.assertNotEqual(unit,body)
            path=self.out/('native-'+name+'.c');path.write_text(template.replace('SOURCE_BODY',source.DECLARATIONS+unit));exe=path.with_suffix('')
            result=subprocess.run([*native_command('-O0' if name=='o0' else '-O2',name not in ('o0','o2')),
                '-mstackrealign','-fno-strict-aliasing',str(path),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''),name)
            result=subprocess.run([str(exe)],capture_output=True,text=True)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0 if name in ('o0','o2','ubsan') else 21,'',''),name);exits[name]=result.returncode
        self.receipt('native-cases',fixtures=len(rows),numeric_words_checked_per_fixture=8094,exits=exits,
            evaluated_conversions_finite_in_signed_range=True,arbitrary_FP_bits_only_on_unvisited_paths=True,
            actor_slots0_through25_or_unvisited_only=True,endian_neutral_expected_word_patches=True)

    def test_06_guest_controls_cached_context_and_flag_read_order(self):
        body=source.FITTED;cached=body.replace('(u8 *)D_800D23B0','cached').replace('    s32 record;',
            '    u8 *cached = (u8 *)D_800D23B0;\n    s32 record;')
        clear='        *(s32 *)((u8 *)D_800D23B0 + slot * 4 + 0xEB0) = -1;'
        flags=body.replace('    s32 record;','    u32 cachedFlags;\n    s32 record;').replace(clear,
            '        cachedFlags = *(u32 *)((u8 *)D_800D23B0 + record * 4 + 0x11F4);\n'+clear).replace(
            '!(*(u32 *)((u8 *)D_800D23B0 + record * 4 + 0x11F4) & 2)','!(cachedFlags & 2)')
        controls=(('cached-context',cached,oracle.Case(layout=2,coords=tuple(map(oracle.bits,(1.75,-49.5,-1.75))))),
            ('cached-flags',flags,oracle.Case(209,0,1,coords=tuple(map(oracle.bits,(1.75,-49.5,-1.75))))))
        for name,unit,case in controls:
            self.assertNotEqual(unit,body);_,words,row=source.compile_candidate(self.root,self.out,'wrong-'+name,unit);self.assertFalse(row['diagnostics'])
            memory,args,_,_=oracle.fixture(case);wanted,after=oracle.reference(memory,args)
            model=oracle.ReleaseModel(words,memory,args).run()
            self.assertNotEqual((model.r[2],oracle.public(model.memory)),(wanted,oracle.public(after)),name)
        self.receipt('guest-source-negatives',effective_completed_public_controls=2,cached_context_and_early_flags=True,
            backed_guest_indices_and_pointer_aliases_not_native_claims=True)

    def test_07_six_distinct_actual_caller_windows_and_delay_effects(self):
        rom=self.values['conker/conker.us.bin'];sites=((0x1508AB28,0xB7FD8,0xAD400FF0),
            (0x1508E520,0xBB9D0,0x00002825),(0x1509E11C,0xCB5CC,0x8E05000C),
            (0x150ED904,0x11ADB4,0x93A4016A),(0x150ED92C,0x11ADDC,0x00002825),(0x150EDA58,0x11AF08,0x8FA40060))
        count=0
        for site,offset,delay in sites:
            actual=list(struct.unpack_from('>2I',rom,offset));self.assertEqual(actual,[0x0D4236BB,delay])
            for slot in (0,1,7,25):
                for mode in ((-1,0,1,2) if site in (0x1508AB28,0x1509E11C) else (0,)):
                    for phase in (0,8):
                        case=oracle.Case(slot,1,mode,coords=tuple(map(oracle.bits,(1.75,-49.5,-1.75))))
                        memory,args,context,_=oracle.fixture(case,phase);expected_memory=memory.copy()
                        if delay==0xAD400FF0:oracle.put(expected_memory,context+slot*4+0xFF0,0,4)
                        if delay==0x8E05000C:oracle.put(memory,0x7800C,mode,4);oracle.put(expected_memory,0x7800C,mode,4)
                        if delay==0x93A4016A:oracle.put(memory,oracle.STACK+phase+0x16A,slot,1);oracle.put(expected_memory,oracle.STACK+phase+0x16A,slot,1)
                        if delay==0x8FA40060:oracle.put(memory,oracle.STACK+phase+0x60,slot,4);oracle.put(expected_memory,oracle.STACK+phase+0x60,slot,4)
                        wanted,after=oracle.reference(expected_memory,args);models=[]
                        for words in (self.retail,self.words):
                            model=oracle.ReleaseModel(actual+[0x02E00008,0],memory,args,phase,site)
                            model.r[23]=model.before[23]=0xDEAD0000;model.before[31]=site+8
                            if delay==0xAD400FF0:model.r[10]=context+slot*4
                            if delay==0x8E05000C:model.r[16]=model.before[16]=0x78000;model.r[5]=0xDEADC0DE
                            if delay in (0x00002825,):model.r[5]=0xDEADC0DE
                            if delay in (0x93A4016A,0x8FA40060):model.r[4]=0xDEADC0DE
                            model.code.update(zip(range(source.ENTRY,source.ENTRY+312,4),words));model.run()
                            self.assertEqual(model.caller_args,[args]);self.assertEqual((model.r[2],oracle.public(model.memory)),(wanted,oracle.public(after)));models.append(model)
                        self.assertEqual(state(models[0]),state(models[1]));count+=1
        hits=[i for i in range(0,len(rom)-3,4) if rom[i:i+4]==b'\x0D\x42\x36\xBB']
        self.assertEqual(hits,sorted(offset for _,offset,_ in sites))
        self.receipt('ABI-windows',distinct_retail_sites=6,aligned_retail_JAL_hits=len(hits),pairs=count,actual_words_per_window=2,
            synthetic_stop_after_actual_delay=True,upstream_liveins_explicit_not_executed=True,delay_store_and_argument_loads_checked=True)

    def test_08_independent_GNU_code_globals_and_alias_context_maps(self):
        asm=self.values['conker/asm/B3020.s'].decode();start=asm.index('glabel '+source.FUNCTION+'\n');end=asm.index('endlabel '+source.FUNCTION,start)
        prelude=(self.root/'conker/include/asm_processor_prelude.inc').read_text();original=self.out/'original.s'
        original.write_text(prelude+'\n.text\n.type '+source.FUNCTION+', @function\n'+asm[start:end]+'\n.size '+source.FUNCTION+', .-'+source.FUNCTION+'\n')
        lines=[prelude,'\n.text\n.globl '+source.FUNCTION,source.FUNCTION+':']
        for i,word in enumerate(struct.unpack('>78I',self.normalized)):
            entries=self.moved.get(i*4,[])
            if entries:
                kind,name=entries[0];lines+=['.word 0x%08X'%(word&0xFFFF0000),'.reloc .-4,%s,%s'%(kind,name)]
            else:lines.append('.word 0x%08X'%word)
        normalized=self.out/'normalized.s';normalized.write_text('\n'.join(lines)+'\n')
        for path in (original,normalized):
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(self.root/'conker/include'),
                '-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
        maps=((source.ENTRY,oracle.STATE,oracle.ACTORS,oracle.BANKS),(0x1621FFF4,0x80218004,0x8032FFFC,(0x98000,0x9C000)),
            (0x18FFF000,0x8065FFFC,0x80768004,(0xC0000,0xC4000)));count=0
        for n,(entry,state_address,actors,banks) in enumerate(maps):
            anchors={'D_800D23B0':state_address,'D_800CC2D0':actors};images=[]
            for path in (original,normalized):
                script=self.out/(path.stem+'-map-%d.ld'%n);elf=script.with_suffix('.elf');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(path.with_suffix('.o'))],check=True,capture_output=True)
                images.append(sections(elf)['.text'][1][:312])
            self.assertEqual(*images);words=list(struct.unpack('>78I',images[0]));self.assertEqual(words,layout.relocate(self.normalized,self.moved,anchors))
            for case in self.cases[::29]+self.cases[-12:]:
                for phase in (0,8):
                    memory,args,_,_=oracle.fixture(case,phase,anchors,banks);wanted,after=oracle.reference(memory,args,anchors)
                    model=oracle.ReleaseModel(words,memory,args,phase,entry).run();self.assertEqual((model.r[2],oracle.public(model.memory)),(wanted,oracle.public(after)));count+=1
        self.receipt('GNU-maps',maps=maps,executed_mapped_cases=count,code_both_globals_actors_contexts_and_pointer_values_rebased=True,all4_bindings_independently_assembled=True)

    def test_09_raw_binding_and_GPR_recipe_corruptions(self):
        count=0
        for at in (0,132,188,311):
            bad=bytearray(self.raw);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'Unknown record-release'):layout.normalize(bytes(bad),self.bindings)
            count+=1
        for at in self.bindings:
            bad=deepcopy(self.bindings);bad[at]=[('R_MIPS_26',source.FUNCTION)]
            with self.assertRaisesRegex(ValueError,'Unknown record-release'):layout.normalize(self.raw,bad)
            count+=1
        with patch.object(layout,'GP',{3:5,5:4}):
            with self.assertRaisesRegex(ValueError,'Changed record-release'):layout.normalize(self.raw,self.bindings)
        self.receipt('corruption-controls',raw_binding_recipe_controls=count+1)

    def test_10_actual_owner_padder_and_stale_manifest(self):
        out=self.root/integration.BUILD;result=integration.qualify(self.root,out);self.assertEqual(result['word_differences'],0)
        reader=csv.DictReader(io.StringIO((out/'qualified-guards.csv').read_text()));rows=list(reader)
        for index in (len(rows)-7,len(rows)-4,len(rows)-1):
            for field in ('expected','expected_relocations'):
                bad=[dict(r) for r in rows];bad[index][field]='0xFFFFFFFF' if field=='expected' else 'R_MIPS_26:'+source.FUNCTION
                text=io.StringIO();writer=csv.DictWriter(text,fieldnames=reader.fieldnames);writer.writeheader();writer.writerows(bad)
                path=self.out/('bad-%d-%s.csv'%(index,field));path.write_text(text.getvalue())
                with self.assertRaisesRegex(ValueError,'stale word patch' if field=='expected' else 'stale relocations'):
                    emit_padded_assembly(out/'after-primary.o',self.root/'conker/asm/B3020.s',
                        function_objects={'func_150891E8':out/'after-normal.o'},word_patches_path=path,filename=source.OWNER)
        if (self.root/source.SOURCE).read_bytes()==self.values[source.SOURCE]:
            for name,value in self.values.items():self.assertEqual((self.root/name).read_bytes(),value,name)
        else:integration.audit(self.root,out)

    def test_11_actual_Make_first_image_and_image_corruptions(self):
        out=self.root/integration.BUILD;integration.make_shadow(self.root,out);self.assertTrue(integration.predict(self.root,out)['exact_prediction'])
        before=source.freeze(self.root,out)['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+312]
        expected=integration.predicted_image(before,truth)
        for at in (64,elf_slot_offset(before,source.ENTRY,312)+132,len(before)-1):
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'image differs'):integration.check_image(before,bytes(bad),truth)
        if (self.root/source.SOURCE).read_bytes()!=self.values[source.SOURCE]:integration.audit(self.root,out)


if __name__=='__main__':unittest.main()
