"""Full setup workspace provenance, closed GP proof, linked guards and installation."""
import csv
import hashlib
import io
import itertools
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_owner_link_setup_matching as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,parse_object,emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_owner_state_match import metadata
from tools.tests import test_game_owner_link_setup_recovery as recovery
from tools.tests import test_game_owner_link_allocator_match as allocator
from tools.tests import test_game_random_curve_record as native

INSERT=screen.TYPES+screen.DECLARATIONS.replace('void *memcpy(void *, const void *, u32);\n','')+'\n'


class StrictSetupOracle(recovery.SetupOracle):
    def get(self,address,size):
        if any(address+i not in self.memory for i in range(size)):
            raise KeyError(('read',address,size))
        return super().get(address,size)


def guard_text(rows):
    stream=io.StringIO()
    writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n')
    writer.writerows(rows)
    return stream.getvalue()


def normalized_object(source,destination):
    data=bytearray(source.read_bytes())
    h=ELF_HEADER.unpack_from(data)
    sections=[SECTION_HEADER.unpack_from(data,h[6]+i*h[11]) for i in range(h[12])]
    names=sections[h[13]]
    pool=data[names[4]:names[4]+names[5]]
    text=next(s for s in sections if pool[s[0]:].split(b'\0',1)[0]==b'.text')
    _,functions,_=parse_object(source)
    base=text[4]+functions[screen.FUNCTION]['value']
    words=list(struct.unpack_from('>210I',data,base))
    screen.certify(words)
    struct.pack_into('>210I',data,base,*screen.normalize(words))
    destination.write_bytes(data)


class GameOwnerLinkSetupMatchTests(unittest.TestCase):
    run_host=native.GameRandomCurveRecordTests.run_host

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-owner-link-setup-match-test'
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.words=screen.normalize(cls.raw)
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>210I',cls.rom,screen.ROM))
        cls.wrapper=list(struct.unpack_from('>53I',cls.rom,allocator.screen.ROM))
        cls.rows=screen.guard_rows(cls.out/'selected.o')
        manifest=cls.root/'conker/retail_word_patches.us.csv'
        cls.guards=cls.out/'guards.csv'
        current=manifest.read_bytes()
        installed=screen.SELECTED in (cls.root/screen.SOURCE).read_text()
        cls.guards.write_bytes(current if installed else current+guard_text(cls.rows).encode())
        directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        cls.path=Path(directory.name)
        if not (cls.out/'baseline.json').exists() and not installed:
            hashes={}
            for name,path in dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
                    guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv').items():
                data=(cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')

    def receipt(self,name,value):
        if name=='chain' and hasattr(self,'chain_tag'):
            name='chain-'+self.chain_tag
        (self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')

    def compare(self,words,memory,first,second,mask,enabled,phase):
        model=recovery.SetupOracle(words,memory,first,second,mask,enabled,phase).run()
        self.assertEqual((recovery.public(model.memory),model.records),
            recovery.expected(memory,first,second,mask,enabled))
        frame=recovery.STACK+phase-168
        for i,result in enumerate(recovery.RESULTS):
            if mask&(1<<i):
                for offset in recovery.PACKET_HOLES:
                    self.assertEqual(model.memory[result+0x150+offset],memory[frame+0x34+offset])
        return model

    def test_01_shape_complete_closed_permutations_and_guards(self):
        self.assertEqual(tuple(self.meta[k] for k in ('body_words','frame','differences','pool_bytes')),(210,168,25,0))
        self.assertEqual(self.meta['diagnostics'],'')
        self.assertEqual(self.words,self.retail)
        self.assertEqual(screen.normalize(self.words),self.raw)
        self.assertEqual(sum(map(len,self.meta['relocations'].values())),22)
        proof=screen.certify(self.raw)
        self.assertEqual(len(self.rows),25)
        self.assertEqual(sum(r['expected_relocations']!='-' for r in self.rows),2)
        for r in self.rows:
            self.assertEqual(r['expected_relocations'],r['replacement_relocations'])
        bad=self.raw.copy()
        bad[0x64//4]=(bad[0x64//4]&~(31<<21))|(14<<21)
        with self.assertRaisesRegex(ValueError,'live input'):
            screen.certify(bad)
        bad=self.raw.copy()
        bad[0xA4//4]=(bad[0xA4//4]&~(31<<16))|(14<<16)
        with self.assertRaisesRegex(ValueError,'live output'):
            screen.certify(bad)
        self.receipt('shape',dict(meta=self.meta,certificate=proof,normalized_exact=True,
            guards=25,guarded_relocation_words=2,retail_lookup_for_permutation=False))

    def test_02_guest_raw_normalized_retail_full_stack_holes_and_result_aliases(self):
        coverage=set();count=0
        for alias in (False,True):
            results=(recovery.ACTOR,recovery.FIRST,recovery.SECOND) if alias else recovery.RESULTS
            with patch.object(recovery,'RESULTS',results):
                for seed,layout,mask,enabled,phase in itertools.product(range(3),range(4),range(8),(False,True),(0,8)):
                    memory,first,second=recovery.fixture(seed,layout)
                    outcomes=[]
                    for words in (self.retail,self.raw,self.words):
                        model=self.compare(words,memory,first,second,mask,enabled,phase)
                        coverage.update(model.visits)
                        outcomes.append((model.memory,model.events,model.records))
                    self.assertEqual(outcomes[0],outcomes[1])
                    self.assertEqual(outcomes[0],outcomes[2])
                    count+=1
        self.receipt('guest',dict(cases=count,executions=count*3,retail_words_reached=len(coverage),
            complete_private_stack_and_public_memory_and_trace_equal=True,
            seven_raw_packet_holes_preserved=True,result_endpoint_actor_aliases=True))

    def test_03_native32_actual_body_and_defined_packet_fields(self):
        self.fixture='''typedef unsigned char u8;typedef short s16;typedef int s32;typedef unsigned int u32;typedef float f32;
#define NULL ((void *)0)
'''+screen.TYPES+'''
static union { u32 align;u8 bytes[0x240]; } actorStorage,firstStorage,secondStorage,resultStorage[3];
static u8 *actor=actorStorage.bytes+16,*first,*second,*results[3],*returned;
static int calls,copies,mask,mutation,index,error;
static u8 codeA,codeB;
static u32 savedA[3],savedB[3];
OwnerLinkVector2348 D_800AA350,D_800AA35C,D_800AA320,D_800AA338,D_800AA32C,D_800AA344;
f32 D_800AA380,D_800AA384;
static u32 word(f32 v){union{u32 u;f32 f;}x;x.f=v;return x.u;}
static f32 number(u32 v){union{u32 u;f32 f;}x;x.u=v;return x.f;}
static OwnerLinkVector2348 *vectorsA[]={&D_800AA350,&D_800AA320,&D_800AA32C};
static OwnerLinkVector2348 *vectorsB[]={&D_800AA35C,&D_800AA338,&D_800AA344};
u8 *func_151B30B0(void *ptr,f32 parameter,s32 bytes,u8 slot,s32 context){
    OwnerLinkRequest2348 *request=ptr;
    u8 *a,*b;int i;
    index=calls++;if(index>=3){error=1;return NULL;}
    a=index==0?second:first;b=second;
    codeA=a[0x3b];codeB=b[0x3b];
    for(i=0;i<3;i++){savedA[i]=*(u32 *)(a+0x14+i*4);savedB[i]=*(u32 *)(b+0x14+i*4);}
    if(word(parameter)!=0x3ac49ba6||bytes!=48||slot!=255||context!=0)error=2;
    if(request->flags||request->duration!=1000||request->active!=1||request->enabled!=1||
        request->extra||word(request->width)!=0x40a00000||request->kind!=3||request->tail)error=3;
    if(word(request->distance)!=(index==0?0x42a00000u:0x432a0000u)||
        word(request->limitA)!=0x42c80000||word(request->limitB)!=0x43480000)error=4;
    for(i=0;i<3;i++)if(((u32 *)&request->start)[i]!=savedA[i]||((u32 *)&request->end)[i]!=savedB[i])error=5;
    returned=mask&(1<<index)?results[index]:NULL;
    if(mutation){
        a[0x3b]=(u8)(0xe0+index);b[0x3b]=(u8)(0xe0+index);
        *(u32 *)(a+0x14)=0xc1200000+index*0x100000;
        *(u32 *)(b+0x14)=0xc1200000+index*0x100000;
        *(u8 **)(actor+0x28)=NULL;*(u8 **)(actor+0x30)=NULL;
        D_800AA380=-1.0f;D_800AA384=-2.0f;
    }
    return returned;
}
void *memcpy(void *destination,const void *source,u32 size){
    u8 *d=destination;const u8 *s=source;u32 i;
    const OwnerLinkPacket2348 *packet=source;
    u8 *a=index==0?second:first;
    copies++;
    if(d!=returned+0x150||size!=48||packet->actor!=actor||packet->route!=2-index||
        packet->first.owner!=a||packet->second.owner!=second||
        packet->first.code!=codeA||packet->second.code!=codeB||
        packet->first.kind!=5||packet->second.kind!=(index==1?5:10))error=6;
    for(i=0;i<3;i++)if(((const u32 *)&packet->first.offset)[i]!=((u32 *)vectorsA[index])[i]||
        ((const u32 *)&packet->second.offset)[i]!=((u32 *)vectorsB[index])[i])error=7;
    if(*(u8 **)(actor+0x40-index*4)!=returned)error=8;
    for(i=0;i<size;i++)d[i]=s[i];
    if(mutation)*(u8 **)(actor+0x40-index*4)=NULL;
    return destination;
}
'''+screen.SELECTED+'\n'
        self.run_host('''int byte,layout,m,f,alias,i,j,k;
for(byte=0;byte<256;byte++)for(layout=0;layout<4;layout++)for(m=0;m<2;m++)for(f=0;f<8;f++)for(alias=0;alias<2;alias++){
    for(i=0;i<0x240;i++){actorStorage.bytes[i]=0xa5;firstStorage.bytes[i]=0x5a;secondStorage.bytes[i]=0x3c;
        for(j=0;j<3;j++)resultStorage[j].bytes[i]=0x7e;}
    first=layout==2?actor:firstStorage.bytes+16;
    second=layout==1?first:layout==3?actor:secondStorage.bytes+16;
    for(i=0;i<3;i++){*(u32 *)(first+0x14+4*i)=0x3f800000+byte*4096+i*0x800000;
        *(u32 *)(second+0x14+4*i)=0xc0000000+byte*4096+i*0x800000;}
    first[0x3b]=(u8)byte;second[0x3b]=(u8)(255-byte);
    *(u8 **)(actor+0x28)=first;*(u8 **)(actor+0x30)=second;
    for(i=0;i<3;i++){*(u32 *)(actor+0x40-i*4)=0xa5a5a5a5;
        results[i]=alias?(i==0?actor:i==1?first:second):resultStorage[i].bytes+16;
        for(j=0;j<3;j++){((u32 *)vectorsA[i])[j]=0x41200000+i*0x10000+j*4096;
            ((u32 *)vectorsB[i])[j]=0xc1200000+i*0x10000+j*4096;}}
    D_800AA380=100.0f;D_800AA384=200.0f;
    calls=copies=error=0;mask=f;mutation=m;
    func_151B2348(actor);
    if(error||calls!=3||copies!=((f&1)!=0)+((f&2)!=0)+((f&4)!=0))return 1;
    for(i=0;i<3;i++){
        u8 *expected=(f&(1<<i))&&!m?results[i]:NULL;
        if(*(u8 **)(actor+0x40-i*4)!=expected)return 2;
    }
    for(i=0;i<16;i++){
        if(actorStorage.bytes[i]!=0xa5||firstStorage.bytes[i]!=0x5a||secondStorage.bytes[i]!=0x3c)return 3;
        for(j=0;j<3;j++)if(resultStorage[j].bytes[i]!=0x7e)return 4;
    }
    for(k=0;k<3;k++)for(i=0x200;i<0x240;i++)if(resultStorage[k].bytes[i]!=0x7e)return 5;
}
''')
        self.receipt('native',dict(cases=256*4*2*8*2,pointer_bits=32,
            actual_body=True,defined_packet_fields_only=True,no_native_padding_parity_claim=True))

    def test_04_compiled_effective_negatives(self):
        variants={
            'wrong-route':screen.SELECTED.replace('work.packet.route = 1;','work.packet.route = 2;'),
            'wrong-distance':screen.SELECTED.replace('work.request.distance = 170.0f;','work.request.distance = 80.0f;'),
            'late-code':screen.SELECTED.replace('work.packet.first.code = first[0x3B];','work.packet.first.code = second[0x3B];'),
            'omit-failed-store':screen.SELECTED.replace('    *(u8 **)(pair + 0x18) = created;',
                '    if (created != NULL) *(u8 **)(pair + 0x18) = created;'),
            'short-copy':screen.SELECTED.replace('&work.packet, 48);','&work.packet, 44);')}
        records={}
        for name,body in variants.items():
            meta,words=screen.compile_candidate(self.root,self.out,'negative-'+name,body)
            mismatch=False
            for mask in (0,7):
                memory,first,second=recovery.fixture(0,0)
                model=recovery.SetupOracle(words,memory,first,second,mask,False,0).run()
                if (recovery.public(model.memory),model.records)!=recovery.expected(memory,first,second,mask,False):
                    mismatch=True
            self.assertTrue(mismatch,name)
            records[name]=dict(public_output_or_calls_mismatch=True,words=meta['body_words'])
        self.receipt('negatives',records)

    def test_05_copied_owner_postprocess_and_guarded_padder(self):
        current=(self.root/screen.SOURCE).read_text()
        before=current.replace(screen.SELECTED,screen.ORIGINAL).replace(INSERT,'')
        self.assertEqual(before.count(screen.ORIGINAL),1)
        after=before.replace('/* Non-matching placeholders',INSERT+'/* Non-matching placeholders',1).replace(
            screen.ORIGINAL,screen.SELECTED)
        objects,warnings=[],[]
        for name,body in (('owner-before',before),('owner-after',after)):
            obj,diagnostics=compile_owner(self.root,self.out,body,name)
            subprocess.run([sys.executable,str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',
                str(obj.relative_to(self.root/'conker')),'--assembler','mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',check=True,capture_output=True)
            objects.append(obj);warnings.append(diagnostics)
        self.assertEqual(warnings[0],warnings[1]);self.assertEqual(len(warnings[0]),4)
        old,old_fn,old_rel=parse_object(objects[0]);new,new_fn,new_rel=parse_object(objects[1])
        self.assertEqual(old_fn.keys(),new_fn.keys())
        for name,fn in new_fn.items():
            if name==screen.FUNCTION:continue
            prior=old_fn[name]
            self.assertEqual((fn['size'],new[fn['value']:fn['value']+fn['size']]),
                (prior['size'],old[prior['value']:prior['value']+prior['size']]),name)
            self.assertEqual({o-fn['value']:r for o,r in new_rel.items() if fn['value']<=o<fn['value']+fn['size']},
                {o-prior['value']:r for o,r in old_rel.items() if prior['value']<=o<prior['value']+prior['size']},name)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        rows=screen.guard_rows(objects[1])
        self.assertEqual(rows,self.rows)
        self.assertTrue(emit_padded_assembly(objects[1],self.root/'conker/asm/1DF510.s',
            word_patches_path=self.guards,filename='generated_1DF510'))
        self.receipt('owner',dict(neighbors=len(new_fn)-1,new_diagnostics=0,existing_diagnostics=4,
            pools_and_relative_relocations_unchanged=True,guards_identical_to_isolated=True,
            actual_postprocess_and_padder_accept=True))

    def test_06_independent_original_candidate_rebases(self):
        fragment=(self.root/'conker/asm/nonmatchings/generated_1DF510/func_151B2348.s').read_text()
        raw=self.out/'original.s';obj=self.out/'original.o';normalized=self.out/'normalized.o'
        raw.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n'+fragment)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(raw)],
            cwd=self.root,check=True,capture_output=True)
        normalized_object(self.out/'selected.o',normalized)
        self.assertEqual(parse_object(obj)[2],parse_object(normalized)[2])
        count=0
        for variant,entry in enumerate((screen.ENTRY,0x10008000,0x80007FFC,0x8FFF8000)):
            symbols=screen.SYMBOLS if variant==0 else {n:(entry&0xF0000000)+0x108008+i*0x100
                for i,n in enumerate(screen.SYMBOLS)}
            script=self.out/('rebase-%d.ld'%variant)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            bodies=[]
            for name,path in (('original',obj),('raw',self.out/'selected.o'),('normalized',normalized)):
                elf=self.out/('rebase-%d-%s.elf'%(variant,name))
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(path)],check=True,capture_output=True)
                bodies.append(list(struct.unpack_from('>210I',sections(elf)['.text'][1])))
            self.assertEqual(bodies[0],bodies[2])
            for mask,phase in itertools.product(range(8),(0,8)):
                memory,first,second=recovery.fixture(count%3,count%4)
                for name,address in screen.SYMBOLS.items():
                    if name.startswith('D_'):
                        size=12 if address<0x800AA380 else 4
                        for i in range(size):memory[symbols[name]+i]=memory[address+i]
                outcomes=[]
                with patch.object(recovery.screen,'SYMBOLS',symbols),patch.object(recovery.screen,'ENTRY',entry):
                    for words in bodies:
                        model=self.compare(words,memory,first,second,mask,True,phase)
                        outcomes.append((model.memory,model.events,model.records))
                self.assertEqual(outcomes[0],outcomes[1]);self.assertEqual(outcomes[0],outcomes[2])
                count+=1
        self.receipt('rebases',dict(symbol_sets=4,independent_links=12,cases=count,executions=count*3,
            raw_and_normalized_semantic_traces_equal=True,relocation_uses=22))

    def test_07_real_setup_and_exact_allocator_chain(self):
        for tag,words in (('original',self.retail),('raw',self.raw),('normalized',self.words)):
            self.chain_tag=tag
            with patch.object(self,'retail',self.wrapper),patch.object(self,'words',self.wrapper),patch.object(self,'setup_words',words,create=True):
                allocator.GameOwnerLinkAllocatorTests.test_07_actual_setup_chain(self)
        self.receipt('connected',dict(cases=384,executions=768,setup_forms=3,
            actual_setup_words=210,actual_wrapper_words=53,common_allocator_and_sdk_bounded=True))

    def test_08_missing_byte_fault_prefixes(self):
        count=0
        for layout in range(4):
            memory,first,second=recovery.fixture(0,layout)
            for address in (recovery.ACTOR+0x30,recovery.ACTOR+0x28,second+0x3B,
                    second+0x14,first+0x3B,first+0x14,0x800AA350,0x800AA384):
                broken=memory.copy();del broken[address]
                outcomes=[]
                for words in (self.retail,self.raw,self.words):
                    model=StrictSetupOracle(words,broken,first,second,7,False,0)
                    with self.assertRaises(KeyError):model.run()
                    outcomes.append((model.memory,model.events,model.records))
                self.assertEqual(outcomes[0],outcomes[1]);self.assertEqual(outcomes[0],outcomes[2])
                count+=1
        self.receipt('faults',dict(cases=count,executions=count*3,
            guest_order_only_not_native_or_hardware_fault_guarantee=True))

    def test_09_whole_elf_guards_and_progress_audit(self):
        if not (self.out/'baseline.json').exists():
            self.skipTest('immutable pre-install baseline absent')
        before=(self.out/'before-elf').read_bytes()
        current=(self.root/'conker/build/conker.us.elf').read_bytes()
        old_meta,new_meta=metadata(before),metadata(current)
        self.assertEqual(old_meta,new_meta)
        expected=bytearray(before)
        for section in old_meta[4:]:
            start,length=section[4],section[5]
            expected[start:start+length]=current[start:start+length]
        self.assertEqual(current,bytes(expected))
        installed=screen.SELECTED in (self.root/screen.SOURCE).read_text()
        guards=(self.root/'conker/retail_word_patches.us.csv').read_bytes()
        old_guards=(self.out/'before-guards').read_bytes()
        self.assertEqual(guards,old_guards+(guard_text(self.rows).encode() if installed else b''))
        old_progress=(self.out/'before-progress').read_bytes()
        progress=(self.root/'conker/progress.csv').read_bytes()
        if installed:
            old=list(csv.DictReader(io.StringIO(old_progress.decode())))
            new=list(csv.DictReader(io.StringIO(progress.decode())))
            changed=[]
            for a,b in zip(old,new):
                if a!=b:
                    self.assertEqual(a['function'],screen.FUNCTION)
                    self.assertEqual(a['language'],'asm');self.assertEqual(b['language'],'c')
                    expected_row=dict(a,language='c');self.assertEqual(b,expected_row)
                    changed.append(a['function'])
            self.assertEqual(changed,[screen.FUNCTION]);self.assertEqual(len(old),len(new))
        else:
            self.assertEqual(progress,old_progress)
        audit=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertTrue(audit['exact'],audit)
        self.receipt('audit',dict(installed=installed,all_loadable_bytes_identical=True,
            all_symbol_meanings_identical=True,symbol_string_order_normalized=True,
            only25_guard_rows_appended=installed,only_target_asm_to_c_row=installed,
            protected_data_layout=audit,source_sha256=hashlib.sha256((self.root/screen.SOURCE).read_bytes()).hexdigest(),
            elf_sha256=hashlib.sha256(current).hexdigest()))


if __name__=='__main__':
    unittest.main()
