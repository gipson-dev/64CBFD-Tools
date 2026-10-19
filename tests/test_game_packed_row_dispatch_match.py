"""Packed-row dispatch: helper reloads, full literal state, native C and ABI."""
from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_packed_row_dispatch_candidates as source
from tools.experiments import game_packed_row_dispatch_layout as layout
from tools.experiments import game_packed_row_dispatch_integration as integration
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.tests import game_packed_row_dispatch_oracle as oracle
from tools.tests.test_game_packed_peer_lookup_match import state
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.pad_generated_object import emit_padded_assembly


NATIVE=r'''
typedef unsigned char u8;typedef unsigned short u16;typedef unsigned int u32;typedef int s32;
u8 *D_800D23C0;u32 D_80087380;
SOURCE_BODY
typedef struct {u32 args[2],count,mode,first,index;u16 lengths[4],entries[4][8];u32 expected[112];} TestCase;
static const TestCase cases[]={CASES};
static PackedPeerRow rows[2][4] __attribute__((aligned(16)));
static const TestCase *active;
static u32 trace[128],calls,handlers,failure;
static void record(u32 id,u32 arg){if(calls<64){trace[calls*2]=id;trace[calls*2+1]=arg;}else failure=22;calls++;}
static void handle(u32 id,u32 arg){
    u32 i;PackedPeerRow *row;
    record(id,arg);handlers++;
    if(handlers!=1 || active->mode==0)return;
    if(active->mode==1 || active->mode==3 || active->mode==4)D_800D23C0=(u8 *)rows[1];
    row=(PackedPeerRow *)D_800D23C0+active->first;
    if(active->mode==2)row->count=0;
    else if(active->mode==3)D_80087380=0;
    else if(active->mode==4){row->count=8;D_80087380=active->first;}
    else if(active->mode==5)for(i=active->index+1;i<active->lengths[active->first];i++)
        row->entries[i]=((i&1?3:1)<<12)|(0x500+active->first*16+i);
}
void func_15114B94(s32 arg){handle(1,(u32)arg);}
void func_1503DDD0(s32 arg){handle(2,(u32)arg);}
CLEAR_BODY
static void setup(const TestCase *c){
    u32 b,i,j,value;active=c;calls=handlers=0;D_80087380=c->count;D_800D23C0=(u8 *)rows[0];
    for(i=0;i<128;i++)trace[i]=0;
    for(b=0;b<2;b++)for(i=0;i<4;i++){
        rows[b][i].unk0=0x1234+b*16+i;rows[b][i].count=c->lengths[i];rows[b][i].unk4=0xABC00000+b*256+i;
        for(j=0;j<8;j++){
            value=j<c->lengths[i]?c->entries[i][j]:((2+j%3)<<12)|(0x400+i*16+j);
            if(b && j<c->lengths[i])value=(value&0xF000)|((value+0x40)&4095);
            rows[b][i].entries[j]=value;
        }
    }
}
static void check(const TestCase *c){
    u32 b,i,j,k=4,observed[112];
    observed[0]=D_80087380;observed[1]=D_800D23C0==(u8 *)rows[1];observed[2]=handlers;observed[3]=calls;
    for(b=0;b<2;b++)for(i=0;i<4;i++){
        observed[k++]=rows[b][i].unk0;observed[k++]=rows[b][i].count;observed[k++]=rows[b][i].unk4;
        for(j=0;j<8;j++)observed[k++]=rows[b][i].entries[j];
    }
    for(i=0;i<20;i++)observed[k++]=trace[i];
    for(i=0;i<112;i++)if(observed[i]!=c->expected[i])failure=21;
}
void _start(void){
    u32 n,v,dimension,key,hit;TestCase sweep={0};
    if(sizeof(void*)!=4 || sizeof(PackedPeerRow)!=24 || sizeof(u16)!=2)failure=29;
    for(n=0;!failure && n<sizeof(cases)/sizeof(cases[0]);n++){
        setup(cases+n);func_1508EE0C(cases[n].args[0],cases[n].args[1]);check(cases+n);
    }
    sweep.count=1;sweep.lengths[0]=3;sweep.entries[0][0]=0x1001;sweep.entries[0][1]=0x2002;sweep.entries[0][2]=0x3003;
    for(dimension=0;dimension<2;dimension++)for(v=0;!failure && v<65536;v++){
        sweep.args[0]=dimension?1:v;sweep.args[1]=dimension?v:1;setup(&sweep);
        func_1508EE0C(sweep.args[0],sweep.args[1]);
        key=dimension?(0x1000+v)&65535:((v&15)<<12)+1;
        hit=key==0x1001 || key==0x2002 || key==0x3003;
        if(D_80087380!=1 || D_800D23C0!=(u8 *)rows[0] || handlers!=(hit?2:0) || calls!=(hit?3:0))failure=21;
        if(rows[0][0].unk0!=(hit?0:0x1234) || rows[0][0].count!=(hit?0:3) || rows[0][0].unk4!=(hit?0:0xABC00000))failure=21;
        if(hit && (trace[0]!=1 || trace[1]!=2 || trace[2]!=2 || trace[3]!=3 || trace[4]!=3 || trace[5]!=0))failure=21;
    }
    __asm__ volatile("int $0x80"::"a"(1),"b"(failure));__builtin_unreachable();
}
'''


class PackedRowDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.values=source.freeze(cls.root,cls.out);cls.obj,cls.raw_words,cls.row=source.compile_candidate(cls.root,cls.out,'qualified')
        cls.raw,cls.bindings=source.payload(cls.obj);cls.normalized,cls.moved=layout.normalize(cls.raw,cls.bindings)
        cls.words=layout.relocate(cls.normalized,cls.moved,oracle.DEFAULT)
        cls.retail=list(struct.unpack_from('>91I',cls.values['conker/conker.us.bin'],source.ROM));cls.cases=list(oracle.cases())
        cls.clear=list(struct.unpack_from('>20I',cls.values['conker/conker.us.bin'],source.ROM-80))
        at=elf_slot_offset(cls.values['conker/build/conker.us.elf'],oracle.CLEAR,80)
        if list(struct.unpack_from('>20I',cls.values['conker/build/conker.us.elf'],at))!=cls.clear:
            raise ValueError('Connected clear helper is not retail-exact')

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def model(self,words,case,phase=0,real_clear=False):
        memory,args=oracle.fixture(case,phase)
        return oracle.DispatchModel(words,memory,args,case,phase,clear_words=self.clear if real_clear else None)

    def test_01_complete_body_guards_and_tail_padding(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['diagnostics']),(91,48,15,''))
        self.assertEqual(self.words,self.retail);self.assertEqual(len(self.moved),11)
        self.assertEqual(sorted(layout.origins()),list(range(91)))
        guards=layout.private_guards(self.values['conker/retail_word_patches.us.csv'],self.raw,self.bindings)
        self.assertTrue(guards.startswith(self.values['conker/retail_word_patches.us.csv']))
        rows=[r for r in csv.DictReader(io.StringIO(guards.decode())) if r['filename']==source.OWNER and r['function']==source.FUNCTION]
        self.assertEqual(len(rows),15);self.assertTrue(all(r['omit']=='false' and not r['insert_after'] for r in rows))
        self.assertEqual(self.values['conker/conker.us.bin'][source.ROM+364:source.ROM+372],bytes(8))

    def test_02_independent_algorithm_full_state_and_callback_mutations(self):
        visits=set();pairs=0;modes=set()
        for case in self.cases:
            for phase in (0,8):
                memory,_=oracle.fixture(case,phase);want,calls=oracle.reference(memory,case)
                original=self.model(self.retail,case,phase).run();normalized=self.model(self.words,case,phase).run()
                raw=self.model(self.raw_words,case,phase).run()
                self.assertEqual(state(original),state(normalized),case)
                for model in (original,normalized,raw):
                    self.assertEqual((oracle.public(model.memory),model.calls),(oracle.public(want),calls),case)
                if original.handlers:modes.add(case.mode)
                visits.update(original.visits);pairs+=1
        self.assertEqual(modes,set(range(6)))
        self.receipt('functional-cases',cases=len(self.cases),phases=2,paired_literal_runs=pairs,raw_public_runs=pairs,
            retail_visited_words=len(visits),statically_compared_words=91,callback_modes=sorted(modes),no_numeric_return_contract=True)

    def test_03_fired_root_access_cuts(self):
        cases=(oracle.Case((1,1),()),oracle.Case((1,1),((),)),oracle.Case((1,1),((0x1001,),)),
            oracle.Case((1,1),((0x2002,0x1001,0x3003),),1),oracle.Case((1,1),((0x3003,0x1001,0x2002),),2),
            oracle.Case((1,1),((0x3003,0x1001,0x2002),),4),oracle.Case((1,1),((0x1002,),)))
        count=0
        for case in cases:
            for phase in (0,8):
                run=self.model(self.retail,case,phase).run()
                if not case.rows:self.assertFalse(any(e[0]=='R' and e[1]==oracle.TABLE for e in run.events))
                for cut in range(run.accesses):
                    models=[]
                    for words in (self.retail,self.words):
                        model=self.model(words,case,phase);model.fault=cut
                        with self.assertRaises(oracle.core.AccessFault):model.run()
                        self.assertEqual(model.accesses,cut);models.append(model)
                    self.assertEqual(state(models[0]),state(models[1]));count+=1
        self.receipt('fired-cuts',pairs=count,all_requested_cuts_fired=True,provider_internal_stores_not_cut=True,
            empty_global_count_does_not_read_table=True)

    def test_04_actual_clear_helper_connected_and_wide_count_prefixes(self):
        count=0
        for case in self.cases[::7]+self.cases[-24:]:
            for phase in (0,8):
                memory,_=oracle.fixture(case,phase);want,calls=oracle.reference(memory,case)
                models=[self.model(words,case,phase,True).run() for words in (self.retail,self.words)]
                self.assertEqual(state(models[0]),state(models[1]))
                self.assertEqual((oracle.public(models[0].memory),models[0].calls),(oracle.public(want),calls));count+=1
        probes=0
        for size in (0x8000,0xFFFF):
            case=oracle.Case((1,1),((0x1001,0x2002),),2);memory,args=oracle.fixture(case)
            oracle.put(memory,oracle.BANKS[0]+2,size,2)
            models=[oracle.DispatchModel(words,memory,args,case).run() for words in (self.retail,self.words)]
            self.assertEqual(state(models[0]),state(models[1]));self.assertEqual(models[0].handlers,1);probes+=1
        for size in (0x10000,0x80000000,0xFFFFFFFF):
            case=oracle.Case((1,1),((),(),(),()));memory,args=oracle.fixture(case);oracle.put(memory,oracle.COUNT,size,4);models=[]
            for words in (self.retail,self.words):
                model=oracle.DispatchModel(words,memory,args,case);model.fault=14
                with self.assertRaises(oracle.core.AccessFault):model.run()
                self.assertEqual(model.accesses,14);models.append(model)
            self.assertEqual(state(models[0]),state(models[1]));probes+=1
        self.receipt('connected-clear',pairs=count,actual_clear_words=20,handler_providers_still_bounded=True,wide_count_probes=probes,
            huge_global_counts_are_fired_prefixes_not_completed_iterations=True)

    def test_05_native32_numeric_corpus_and_halfword_views(self):
        number=lambda v:'0x%Xu'%(v&0xFFFFFFFF)
        rows=[]
        for case in self.cases:
            lengths=[len(row) for row in case.rows]+[0]*(4-len(case.rows))
            entries=[tuple(row)+(0,)*(8-len(row)) for row in case.rows]+[(0,)*8]*(4-len(case.rows))
            memory,_=oracle.fixture(case);wanted,calls=oracle.reference(memory,case);observed=oracle.observation(wanted,calls)
            self.assertEqual(len(observed),112)
            rows.append('{{%s},%s,%s,%s,%s,{%s},{%s},{%s}}'%(','.join(map(number,case.arguments)),number(len(case.rows)),
                number(case.mode),number(oracle.matched_row(case) or 0),number(oracle.first_handler(case) or 0),
                ','.join(map(number,lengths)),','.join('{'+','.join(map(number,row))+'}' for row in entries),','.join(map(number,observed))))
        old=self.values[source.SOURCE].decode();start,end=function_span(old,'func_1508EDBC');clear=old[start:end]
        clear=clear.replace('{','{\n    record(3, arg0);',1)
        template=NATIVE.replace('CASES',',\n'.join(rows)).replace('CLEAR_BODY',clear)
        body=source.FITTED
        cached=body.replace('    u32 rowIndex;','    PackedPeerRow *cached = (PackedPeerRow *)D_800D23C0;\n    u32 rowIndex;').replace(
            '((PackedPeerRow *)D_800D23C0)[rowIndex]','cached[rowIndex]')
        controls={'o0':body,'o2':body,'ubsan':body,
            'wrong-or':body.replace('(group << 12) + value','(group << 12) | value'),
            'wrong-dispatch':body.replace('func_15114B94(packed','func_1503DDD0(packed'),
            'wrong-mask':body.replace(' & 0xFFF',' & 0xFF'),
            'wrong-all-rows':body.replace('                return;','                break;'),
            'wrong-cache-table':cached}
        exits={}
        for name,unit in controls.items():
            if name not in ('o0','o2','ubsan'):self.assertNotEqual(unit,body)
            path=self.out/('native-'+name+'.c');path.write_text(template.replace('SOURCE_BODY',source.ROW_TYPE+source.DECLARATIONS+unit))
            exe=path.with_suffix('');command=[*native_command('-O0' if name=='o0' else '-O2',name not in ('o0','o2')),
                '-mstackrealign','-fno-strict-aliasing',str(path),'-o',str(exe)]
            result=subprocess.run(command,cwd=self.root,capture_output=True,text=True)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''),name)
            result=subprocess.run([str(exe)],capture_output=True,text=True);want=0 if name in ('o0','o2','ubsan') else 21
            self.assertEqual((result.returncode,result.stdout,result.stderr),(want,'',''),name);exits[name]=result.returncode
        self.receipt('native-cases',fixture_cases=len(self.cases),numeric_observation_words=112,halfword_views=2,values_per_view=65536,
            extra_sweep_calls_per_positive=131072,clear_body_existing_semantic_C=True,handler_contracts_bounded=True,exits=exits)

    def test_06_raw_binding_and_recipe_corruption_controls(self):
        controls=0
        for at in (0,88,196,363):
            bad=bytearray(self.raw);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'Unknown packed-row'):layout.normalize(bytes(bad),self.bindings)
            controls+=1
        for at in self.bindings:
            bad=deepcopy(self.bindings);bad[at]=[('R_MIPS_LO16','D_80087380')]
            if bad==self.bindings:bad[at]=[('R_MIPS_HI16','D_800D23C0')]
            with self.assertRaisesRegex(ValueError,'Unknown packed-row'):layout.normalize(self.raw,bad)
            controls+=1
        bad=deepcopy(layout.GP);bad[22]={24:25}
        with patch.object(layout,'GP',bad):
            with self.assertRaisesRegex(ValueError,'Changed dispatcher layout'):layout.normalize(self.raw,self.bindings)
        controls+=1
        self.receipt('corruption-controls',raw_binding_and_recipe_controls=controls)

    def test_07_actual_owner_profiles_padder_and_stale_manifest(self):
        out=self.root/integration.BUILD;result=integration.qualify(self.root,out);self.assertEqual(result['word_differences'],0)
        good=(out/'qualified-guards.csv').read_bytes();reader=csv.DictReader(io.StringIO(good.decode()));rows=list(reader)
        for index in (len(rows)-15,len(rows)-8,len(rows)-1):
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

    def test_08_independent_GNU_maps_all_eleven_bindings(self):
        asm=self.values['conker/asm/B3020.s'].decode();start=asm.index('glabel '+source.FUNCTION+'\n')
        end=asm.index('endlabel '+source.FUNCTION,start);prelude=(self.root/'conker/include/asm_processor_prelude.inc').read_text()
        original=self.out/'original.s';original.write_text(prelude+'\n.text\n.type '+source.FUNCTION+', @function\n'+asm[start:end]+
            '\n.size '+source.FUNCTION+', .-'+source.FUNCTION+'\n')
        lines=[prelude,'\n.text\n.globl '+source.FUNCTION,source.FUNCTION+':']
        for i,word in enumerate(struct.unpack('>91I',self.normalized)):
            entries=self.moved.get(i*4,[])
            if entries:
                kind,name=entries[0];lines+=['.word 0x%08X'%(word&(0xFC000000 if kind=='R_MIPS_26' else 0xFFFF0000)),
                    '.reloc .-4,%s,%s'%(kind,name)]
            else:lines.append('.word 0x%08X'%word)
        normalized=self.out/'normalized.s';normalized.write_text('\n'.join(lines)+'\n')
        for path in (original,normalized):
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(self.root/'conker/include'),
                '-o',str(path.with_suffix('.o')),str(path)],check=True,capture_output=True)
        maps=((source.ENTRY,oracle.COUNT,oracle.TABLE,0x15114B94,0x1503DDD0,oracle.CLEAR,oracle.BANKS),
            (0x1621FFF4,0x8020FFF4,0x80318004,0x16318000,0x1642FFFC,0x16530004,(0x98000,0x9C000)),
            (0x18FFF000,0x80428004,0x8053FFFC,0x1800FFFC,0x18A08004,0x18B1FFF4,(0xA0000,0xA4000)))
        count=0;selected=self.cases[::24]+self.cases[-12:]
        for n,(entry,count_address,table_address,h2,h3,clear,banks) in enumerate(maps):
            anchors=dict(zip(oracle.DEFAULT,(count_address,table_address,h2,h3,clear)));images=[]
            for path in (original,normalized):
                script=self.out/(path.stem+'-map-%d.ld'%n);elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(path.with_suffix('.o'))],check=True,capture_output=True)
                images.append(sections(elf)['.text'][1][:364])
            self.assertEqual(*images);words=list(struct.unpack('>91I',images[0]));self.assertEqual(words,layout.relocate(self.normalized,self.moved,anchors))
            for case in selected:
                for phase in (0,8):
                    memory,args=oracle.fixture(case,phase,anchors,banks);wanted,calls=oracle.reference(memory,case,anchors,banks)
                    model=oracle.DispatchModel(words,memory,args,case,phase,entry,anchors,banks).run()
                    self.assertEqual((oracle.public(model.memory),model.calls),(oracle.public(wanted),calls));count+=1
        self.receipt('GNU-maps',maps=maps,executed_mapped_cases=count,code_globals_handlers_and_row_pointer_rebased=True,
            all11_bindings_independently_assembled=True,actual_clear_connected_only_at_default_map=True)

    def test_09_actual_retail_call_windows_and_fullword_argument_homes(self):
        sites=((0x1511A264,0x147714,0),(0x150BFF48,0xED3F8,0x24040002),(0x150BFF74,0xED424,0))
        count=0;selected=[oracle.Case((2,value),((0x2000|value,0x3007),),mode) for value in (0,1,4095) for mode in range(6)]
        for entry,rom,delay in sites:
            actual=list(struct.unpack_from('>2I',self.values['conker/conker.us.bin'],rom));self.assertEqual(actual,[0x0D423B83,delay])
            window=actual+[0x02E00008,0]
            for case in selected:
                for phase in (0,8):
                    memory,args=oracle.fixture(case,phase);models=[]
                    for words in (self.retail,self.words):
                        model=oracle.DispatchModel(window,memory,args,case,phase,entry)
                        model.r[4]=model.before[4]=0xF00D0000 if delay else 2
                        model.r[23]=model.before[23]=0xDEAD0000;model.before[31]=entry+8
                        model.code.update(zip(range(source.ENTRY,source.ENTRY+364,4),words));model.run()
                        self.assertEqual(model.caller_args,[args]);self.assertEqual(tuple(oracle.read(model.memory,oracle.STACK+phase+i*4,4) for i in range(2)),args)
                        wanted,calls=oracle.reference(memory,case)
                        self.assertEqual((oracle.public(model.memory),model.calls),(oracle.public(wanted),calls));models.append(model)
                    self.assertEqual(state(models[0]),state(models[1]));count+=1
        high=0
        for case in self.cases[-24:]:
            for phase in (0,8):
                models=[self.model(words,case,phase).run() for words in (self.retail,self.words)]
                self.assertEqual(state(models[0]),state(models[1]))
                self.assertEqual(tuple(oracle.read(models[0].memory,oracle.STACK+phase+i*4,4) for i in range(2)),case.arguments);high+=1
        self.receipt('ABI-windows',retail_sites=3,pairs=count,two_actual_words_then_synthetic_stop=True,
            upstream_quotient_is_explicit_valid_livein_not_executed=True,fullword_entry_pairs=high,no_return_value_assumption=True)

    def test_10_actual_Make_first_image_and_image_corruptions(self):
        out=self.root/integration.BUILD;integration.make_shadow(self.root,out)
        self.assertTrue(integration.predict(self.root,out)['exact_prediction'])
        before=source.freeze(self.root,out)['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+364]
        expected=integration.predicted_image(before,truth)
        for at in (64,elf_slot_offset(before,source.ENTRY,364)+196,len(before)-1):
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'image differs'):integration.check_image(before,bytes(bad),truth)
        if (self.root/source.SOURCE).read_bytes()!=self.values[source.SOURCE]:integration.audit(self.root,out)


if __name__=='__main__':unittest.main()
