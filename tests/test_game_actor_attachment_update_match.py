"""Complete leaf attachment copies, bit-preserving floats and linked-only audit."""
import csv
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_attachment_update_matching as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,parse_object,emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_object_color_mode_match as color
from tools.tests import test_game_actor_update_dispatch_match as dispatch
from tools.tests import test_game_owner_points_initializer_match as initializer
from tools.tests import test_game_random_curve_record as native
from tools.tests.test_game_actor_triangle_transform_match import TriangleOracle
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import signed

ACTORS,LIMIT=tuple(screen.recovery.SYMBOLS.values())
STACK,MATRICES=color.STACK,0x24000
LINKS=((screen.ENTRY,ACTORS,LIMIT),(0x15207FF0,0x80107FFC,0x80118004),
    (0x15308004,0x80118004,0x80127FFC),(0x15417FFC,0x80207FF0,0x80218004))
FLOAT_BITS=(0,0x80000000,0x3F800000,0xC0200000,0x7F800000,0xFF800000,
    0x7FC12345,0x7F812345,1,0x807FFFFF,0x7F7FFFFF)


def fixture(slot=0,attachment=2,flags=0,matrix=True,joint=0,count=3,symbols=LINKS[0],pattern=0):
    _,base,limit=symbols
    actor=base+slot*0x32C
    attached=base+(attachment-1)*0x32C
    memory={STACK+i:0xA5 for i in range(-0x100,0x80)}
    for start,length in ((actor,0x33C),(attached,0x33C),(MATRICES,256),(limit,4)):
        memory.update({start+i:(i*17+0x35)&255 for i in range(length)})
    for offset,value,size in ((0x65,attachment,1),(0x101,flags,1),(0x5C,joint,4),
            (0x180,FLOAT_BITS[(pattern+3)%len(FLOAT_BITS)],4),(0x76,0xA180,2),
            (0x78,0x80FF,2),(0x7A,0xFF01,2),(0x1D4,MATRICES if matrix else 0,4)):
        put(memory,attached+offset,value,size)
    for index,offset in enumerate((0x14,0x18,0x1C,0x3C,0x40)):
        put(memory,attached+offset,FLOAT_BITS[(pattern+index)%len(FLOAT_BITS)])
    for index in range(64): put(memory,MATRICES+index*4,FLOAT_BITS[(pattern+index)%len(FLOAT_BITS)])
    # Source setup precedes destination inputs so self-attachment remains valid.
    for offset,value,size in ((0x65,attachment,1),(0x101,flags,1),(0x5C,joint,4)):
        put(memory,actor+offset,value,size)
    put(memory,limit,count)
    return memory


def reference(memory,slot=0,symbols=LINKS[0]):
    result,events=memory.copy(),[]
    _,base,limit=symbols
    actor=base+slot*0x32C
    def get(address,size=1):
        value=read(result,address,size)
        events.append(('R',address,size,value))
        return value
    def store(address,value,size=1):
        put(result,address,value,size)
        events.append(('W',address,size,value&((1<<(size*8))-1)))
    attachment=get(actor+0x65)
    if not attachment or get(actor+0x101)&2: return result,events
    attached=base+(attachment-1)*0x32C
    matrix=get(attached+0x1D4,4)
    if matrix:
        matrix=(matrix+(get(actor+0x5C,4)<<6))&0xFFFFFFFF
        for destination,offset in ((0x14,0x30),(0x18,0x34),(0x1C,0x38)):
            store(actor+destination,get(matrix+offset,4),4)
    else:
        for offset in (0x14,0x18,0x1C): store(actor+offset,get(attached+offset,4),4)
    flags=get(actor+0x101)
    store(actor+0x180,get(attached+0x180,4),4)
    store(actor+0x20,0xC0800000,4)
    if not flags&0x20:
        angle=get(attached+0x76,2)
        flags=get(actor+0x101)
        store(actor+0x76,angle,2)
        for offset,size in ((0x3C,4),(0x40,4),(0x76,2),(0x7A,2),(0x78,2)):
            store(actor+offset,get(attached+offset,size),size)
    if not flags&0x40:
        for offset in (7,8,9,10,15): store(actor+offset,get(attached+offset))
        if signed(get(limit,4))>=0:
            index=0
            while True:
                store(actor+11+index,get(attached+11+index))
                index+=1
                if signed(get(limit,4))<index: break
                assert index<64,'unbounded reference fixture'
    return result,events


class AccessFault(Exception):
    pass


class AttachmentOracle(TriangleOracle):
    def __init__(self,words,memory,slot=0,symbols=LINKS[0],phase=0,entry=None,arguments=None,connected=None):
        super().__init__(words,memory,entry=entry or symbols[0],arguments=(slot,) if arguments is None else arguments,
            phase=phase,connected=connected)
        self.fault,self.accesses=None,0
    def gate(self):
        if self.accesses==self.fault: raise AccessFault(self.accesses)
        self.accesses+=1
    def get(self,address,size):
        self.gate()
        assert all(address+i in self.memory for i in range(size)),('unmapped read',address,size)
        return super().get(address,size)
    def put(self,address,value,size):
        if self.recording:
            self.gate()
            assert all(address+i in self.memory for i in range(size)),('unmapped write',address,size)
        super().put(address,value,size)
    def hook(self,target):
        raise AssertionError(('unexpected leaf call',target))


class GameActorAttachmentUpdateMatchTests(unittest.TestCase):
    run_host=native.GameRandomCurveRecordTests.run_host
    write_rows=classmethod(color.GameObjectColorModeMatchTests.write_rows.__func__)
    assemble=classmethod(color.GameObjectColorModeMatchTests.assemble.__func__)

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-attachment-update-match-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',guards='conker/retail_word_patches.us.csv',
            progress='conker/progress.csv',rodata='conker/asm/data/23B8A0.rodata.s')
        if not (cls.out/'baseline.json').exists():
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(hashes,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        with (cls.out/'before-guards').open(newline='') as stream:
            reader=csv.DictReader(stream)
            cls.fields,cls.old_rows=reader.fieldnames,list(reader)
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>89I',cls.rom,screen.ROM))
        assembly=(cls.root/'conker/asm/58F80.s').read_text().split('glabel '+screen.FUNCTION,1)[1].split(
            'endlabel '+screen.FUNCTION,1)[0]
        cls.slot_asm=cls.out/'slot.s'
        cls.slot_asm.write_text('glabel '+screen.FUNCTION+assembly+'endlabel '+screen.FUNCTION+'\n')
        cls.write_rows(cls.out/'isolated.csv',screen.guard_rows(cls.out/'selected.o'))
        cls.assemble('fitted',emit_padded_assembly(cls.out/'selected.o',cls.slot_asm,
            word_patches_path=cls.out/'isolated.csv',filename='generated_58F80'))
        cls.assemble('original','.text\n.set noat\n.set noreorder\n.globl '+screen.FUNCTION+'\n.type '+
            screen.FUNCTION+',@function\n'+screen.FUNCTION+':\n'+assembly+'\n.size '+screen.FUNCTION+',.-'+screen.FUNCTION+'\n')
        cls.linked=cls.link('fitted',LINKS[0])
        cls.current=cls.linked
        cls.elf=(cls.root/cls.paths['elf']).read_bytes()
        if screen.recovery.ORIGINAL not in (cls.root/screen.SOURCE).read_text():
            cls.current=list(struct.unpack_from('>89I',cls.elf,elf_slot_offset(cls.elf,screen.ENTRY,356)))
            assert cls.current==cls.linked
        cls.banked={}
        for entry,rom,words in ((dispatch.ENTRY,0x59234,88),(0x1502EEF4,0x5C3A4,74),
                (0x1502EE8C,0x5C33C,26),(0x1507E3C0,0xAB870,80)):
            body=list(struct.unpack_from('>%dI'%words,cls.elf,elf_slot_offset(cls.elf,entry,words*4)))
            assert body==list(struct.unpack_from('>%dI'%words,cls.rom,rom))
            cls.banked.update({entry+i*4:word for i,word in enumerate(body)})
        cls.objects,cls.diagnostics=[],[]
        before=(cls.out/'before-source').read_text()
        for name,body in (('owner-before',before),('owner-after',screen.install(before))):
            obj,warnings=compile_owner(cls.root,cls.out,body,name)
            subprocess.run(['python3',str(cls.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((cls.out/(name+'.c')).relative_to(cls.root/'conker')),'--post-process',
                str(obj.relative_to(cls.root/'conker')),'--assembler','mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=cls.root/'conker',check=True,capture_output=True)
            cls.objects.append(obj)
            cls.diagnostics.append(warnings)
        cls.rows=screen.guard_rows(cls.objects[1])
        cls.guards=cls.out/'qualified-guards.csv'
        cls.write_rows(cls.guards,cls.old_rows+cls.rows)
        cls.directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path=Path(cls.directory.name)
        cls.fixture='''#define NULL ((void *)0)
typedef unsigned char u8; typedef unsigned short u16;
typedef unsigned int u32; typedef int s32; typedef float f32;
static u8 D_800CC2D0[26*0x32C] __attribute__((aligned(16)));
static s32 D_80082FA0;
static u32 matrices[64],expected[26*0x32C/4];
static void store(u8 *p,u32 value) { *(u32 *)p=value; }
static u32 word(u8 *p) { return *(u32 *)p; }
static void reset(s32 slot,s32 attachment,s32 flags,s32 count,s32 matrix) {
    s32 i; u8 *actor=D_800CC2D0+slot*0x32C;
    u8 *attached=D_800CC2D0+(attachment ? attachment-1 : slot)*0x32C;
    for(i=0;i<26*0x32C;i++) D_800CC2D0[i]=(u8)(i*17+0x35);
    for(i=0;i<64;i++) matrices[i]=0x7F810001u+(u32)i;
    store(attached+0x1D4,matrix?(u32)matrices:0);
    actor[0x65]=(u8)attachment;actor[0x101]=(u8)flags;store(actor+0x5C,3);
    D_80082FA0=count;
    for(i=0;i<26*0x32C/4;i++) expected[i]=((u32 *)D_800CC2D0)[i];
}
static void expect(s32 slot) {
    u8 *actor=(u8 *)expected+slot*0x32C,*attached;
    u32 *matrix; s32 i;
    if(!actor[0x65] || (actor[0x101]&2)) return;
    attached=(u8 *)expected+(actor[0x65]-1)*0x32C;
    matrix=(u32 *)word(attached+0x1D4);
    if(matrix) { matrix+=word(actor+0x5C)*16;
        for(i=0;i<3;i++) store(actor+0x14+i*4,matrix[12+i]);
    } else { for(i=0;i<3;i++) store(actor+0x14+i*4,word(attached+0x14+i*4)); }
    store(actor+0x180,word(attached+0x180));store(actor+0x20,0xC0800000);
    if(!(actor[0x101]&0x20)) {
        *(u16 *)(actor+0x76)=*(u16 *)(attached+0x76);
        store(actor+0x3C,word(attached+0x3C));store(actor+0x40,word(attached+0x40));
        *(u16 *)(actor+0x76)=*(u16 *)(attached+0x76);
        *(u16 *)(actor+0x7A)=*(u16 *)(attached+0x7A);
        *(u16 *)(actor+0x78)=*(u16 *)(attached+0x78);
    }
    if(!(actor[0x101]&0x40)) {
        actor[7]=attached[7];actor[8]=attached[8];actor[9]=attached[9];
        actor[10]=attached[10];actor[15]=attached[15];
        for(i=0;i<=D_80082FA0;i++) actor[11+i]=attached[11+i];
    }
}
''' + screen.SELECTED+'\n'

    @classmethod
    def link(cls,name,symbols):
        script=cls.out/('link-%s-%X-%X.ld'%(name,symbols[0],symbols[2]))
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%symbols[0])
        elf=script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            '--defsym=D_800CC2D0=0x%X'%symbols[1],'--defsym=D_80082FA0=0x%X'%symbols[2],
            '-o',str(elf),str(cls.out/(name+'.o'))],check=True,capture_output=True)
        count=parse_object(cls.out/(name+'.o'))[1][screen.FUNCTION]['size']//4
        return list(struct.unpack_from('>%dI'%count,sections(elf)['.text'][1]))

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def compare(self,memory,slot=0,symbols=LINKS[0],phase=0,bodies=None):
        expected,events=reference(memory,slot,symbols)
        if bodies is None:
            bodies=(self.retail,self.current,self.raw)
        models=[AttachmentOracle(body,memory,slot,symbols,phase).run() for body in bodies]
        for model in models:
            self.assertEqual(model.memory,expected)
            self.assertEqual(model.events,events)
            self.assertEqual(model.calls,[])
        return models

    def test_01_closed_leaf_shape_and_all_words(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes'],self.meta['diagnostics']),
            (89,0,0,''))
        self.assertEqual(self.linked,self.retail)
        self.assertEqual(len(self.rows),89)
        self.assertEqual(sum(r['expected']!=r['replacement'] for r in self.rows),29)
        self.assertFalse(any(r['insert_after'] or r['omit']!='false' for r in self.rows))
        self.receipt('shape',words=89,frame=0,guards=89,changed_words=29,dependencies=60,
            insertions=0,omissions=0,padding=0,relocations=4,zero_diagnostics=True)

    def test_02_all_flag_bytes_slots_attachments_and_float_bits(self):
        cases,coverage=0,set()
        inputs=itertools.product((0,12,25),(0,1,26),(False,True),range(256),(-1,0,3))
        for slot,attachment,matrix,flags,count in inputs:
            memory=fixture(slot,attachment,flags,matrix,3,count,pattern=flags%len(FLOAT_BITS))
            models=self.compare(memory,slot,phase=8 if flags&1 else 0)
            coverage.update(models[0].visits)
            cases+=1
        for slot in range(26):
            self.compare(fixture(slot,slot+1,0,True,0,8),slot)
            cases+=1
        for attachment in range(256):
            self.compare(fixture(0,attachment,0,False,count=-1))
            cases+=1
        self.assertEqual(len(coverage),88)
        self.receipt('guest',cases=cases,executions=cases*3,retail_words_reached=88,
            unreachable_word=28,all_flag_and_attachment_bytes=True,
            all_bounded_slots=True,raw_float_bits_and_complete_order_exact=True)

    def test_03_matrix_aliases_and_fresh_global_limit(self):
        cases=0
        for slot,attachment,offset,flags in itertools.product((0,25),(1,26),
                (0x14,0x18,0x1C,0x3C,0x40,0x74,0x180),(0,0x20,0x40,0x60)):
            memory=fixture(slot,attachment,flags,True,joint=0)
            actor=ACTORS+slot*0x32C
            put(memory,ACTORS+(attachment-1)*0x32C+0x1D4,actor+offset-0x30)
            self.compare(memory,slot)
            cases+=1
        for offset in (8,12,16):
            symbols=(screen.ENTRY,ACTORS,ACTORS+offset)
            bodies=tuple(self.link(name,symbols) for name in ('original','fitted','selected'))
            memory=fixture(0,2,0,False,count=2,symbols=symbols)
            attached=ACTORS+0x32C
            for byte in (8,9,10,11,12,13,14,15,16,17,18,19): put(memory,attached+byte,0,1)
            if offset==12: put(memory,attached+12,255,1)
            self.compare(memory,symbols=symbols,bodies=bodies)
            cases+=1
        self.receipt('aliases',cases=cases,executions=cases*3,
            ordered_matrix_overlap=True,limit_aliases_fixed_and_loop_stores=True)

    def test_04_every_verified_fault_prefix(self):
        cases=faults=0
        for attachment,flags,matrix,count,phase in itertools.product((0,2),(0,2,0x20,0x40,0x60),
                (False,True),(-1,0,3),(0,8)):
            memory=fixture(0,attachment,flags,matrix,count=count)
            _,events=reference(memory)
            for ordinal in range(len(events)):
                expected=memory.copy()
                for event in events[:ordinal]:
                    if event[0]=='W': put(expected,event[1],event[3],event[2])
                for body in (self.retail,self.linked,self.raw):
                    model=AttachmentOracle(body,memory,phase=phase)
                    model.fault=ordinal
                    with self.assertRaises(AccessFault) as caught: model.run()
                    self.assertEqual(caught.exception.args,(ordinal,))
                    self.assertEqual(model.events,events[:ordinal])
                    self.assertEqual(model.memory,expected)
                faults+=1
            cases+=1
        self.receipt('faults',cases=cases,verified_prefixes=faults,executions=faults*3,
            actual_fault_gates_verified=True,complete_memory_and_trace_prefix=True)

    def test_05_independent_links(self):
        cases=0
        for symbols in LINKS:
            bodies=tuple(self.link(name,symbols) for name in ('original','fitted','selected'))
            for slot,flags,matrix,count in itertools.product((0,25),(0,2,0x20,0x40,0x60),
                    (False,True),(-1,0,3)):
                self.compare(fixture(slot,2,flags,matrix,count=count,symbols=symbols),slot,symbols,bodies=bodies)
                cases+=1
        self.receipt('rebases',independent_links=12,symbol_sets=4,cases=cases,
            signed_LO16_carries_and_full_traces=True)

    def test_06_copied_owner_and_real_padder(self):
        self.assertEqual(self.diagnostics,[[],[]])
        old,of,orels=parse_object(self.objects[0])
        new,nf,nrels=parse_object(self.objects[1])
        self.assertEqual(of.keys(),nf.keys())
        relative=lambda rs,f:{o-f['value']:r for o,r in rs.items() if f['value']<=o<f['value']+f['size']}
        for name in of:
            if name==screen.FUNCTION: continue
            a,b=of[name],nf[name]
            self.assertEqual((a['size'],old[a['value']:a['value']+a['size']],relative(orels,a)),
                (b['size'],new[b['value']:b['value']+b['size']],relative(nrels,b)),name)
        self.assertEqual(normalized_pools(self.objects[0]),normalized_pools(self.objects[1]))
        padded=[]
        for index,obj in enumerate(self.objects):
            name='padded-owner-%d'%index
            self.assemble(name,emit_padded_assembly(obj,self.root/'conker/asm/58F80.s',
                word_patches_path=self.out/'before-guards' if index==0 else self.guards,
                filename='generated_58F80',rodata_symbol='jtbl_80096DF8_game'))
            padded.append(parse_object(self.out/(name+'.o')))
        start=padded[1][1][screen.FUNCTION]['value']
        self.assertEqual(padded[1][1][screen.FUNCTION]['size'],356)
        self.assertEqual(padded[0][0][:start],padded[1][0][:start])
        self.assertEqual(padded[0][0][start+356:],padded[1][0][start+356:])
        self.receipt('owner',neighbors=len(nf)-1,relative_relocations_and_pools_unchanged=True,
            only_target_padded_slot_changes=True,typed_caller_prototype_no_neighbor_change=True)

    def test_07_actual_stale_word_and_relocation_rejection(self):
        data=(self.out/'selected.o').read_bytes()
        h=ELF_HEADER.unpack_from(data)
        headers=[SECTION_HEADER.unpack_from(data,h[6]+i*h[11]) for i in range(h[12])]
        ns=headers[h[13]]
        names=data[ns[4]:ns[4]+ns[5]]
        text=next(s for s in headers if names[s[0]:].split(b'\0',1)[0]==b'.text')
        for index in range(89):
            stale=bytearray(data)
            struct.pack_into('>I',stale,text[4]+index*4,screen.RAW[index]^0x10000)
            path=self.out/'stale.o'
            path.write_bytes(stale)
            with self.assertRaisesRegex(ValueError,'stale complete'): screen.recipe(
                [w^0x10000 if i==index else w for i,w in enumerate(screen.RAW)])
            with self.assertRaisesRegex(ValueError,'stale word patch'):
                emit_padded_assembly(path,self.slot_asm,word_patches_path=self.out/'isolated.csv',filename='generated_58F80')
        for offset in screen.RELOCATIONS:
            rows=[dict(row) for row in self.rows]
            rows[offset//4]['expected_relocations']='-'
            path=self.out/'stale-relocations.csv'
            self.write_rows(path,rows)
            with self.assertRaisesRegex(ValueError,'stale relocations'):
                emit_padded_assembly(self.out/'selected.o',self.slot_asm,word_patches_path=path,filename='generated_58F80')
        self.receipt('stale',actual_word_rejections=89,relocation_rejections=4)

    def test_08_actual_native32_complete_C(self):
        self.run_host('''s32 slot,attachment,flags,count,matrix,i,k;
static s32 counts[]={-2,-1,0,1,3,8};
for(slot=0;slot<26;slot++) for(k=0;k<4;k++) {
    attachment=k==0?0:k==1?1:k==2?26:slot+1;
    for(flags=0;flags<256;flags++) for(count=0;count<6;count++) for(matrix=0;matrix<2;matrix++) {
        reset(slot,attachment,flags,counts[count],matrix);expect(slot);func_1502F264(slot);
        for(i=0;i<26*0x32C/4;i++) if(((u32 *)D_800CC2D0)[i]!=expected[i]) return 1;
    }
}''')
        self.receipt('native',cases=26*4*256*6*2,all_bounded_slots_and_flags=True,
            self_attachment_NULL_matrix_and_raw_NaN_bits=True,actual_complete_C=True)

    def test_09_fresh_compiled_negative_controls(self):
        changes={
            'negative-no-attachment':('actor[0x65] != 0','0'),
            'negative-zero-based':(' * 0x32C - 0x32C',' * 0x32C'),
            'negative-wrong-bit':('& 2) != 2','& 1) != 1'),
            'negative-fixed-limit':('*(volatile s32 *)&D_80082FA0','3'),
            'negative-exclusive-limit':(' >= index',' > index'),
            'negative-matrix-stride':(' * 0x40',' * 0x20'),
            'negative-no-repeat-angle':('                *(u16 *)(actor + 0x76) = *(u16 *)(attached + 0x76);\n',''),
        }
        controls={name:screen.SELECTED.replace(old,new) for name,(old,new) in changes.items()}
        cases={
            'negative-no-attachment':fixture(),
            'negative-zero-based':fixture(),
            'negative-wrong-bit':fixture(flags=1),
            'negative-fixed-limit':fixture(count=0),
            'negative-exclusive-limit':fixture(count=1),
            'negative-matrix-stride':fixture(joint=1),
            'negative-no-repeat-angle':fixture(),
        }
        for name,body in controls.items():
            _,words=screen.compile_candidate(self.root,self.out,name,body)
            memory=cases[name]
            expected,events=reference(memory)
            try:
                wrong=AttachmentOracle(words,memory).run()
                effective=(wrong.memory,wrong.events)!=(expected,events)
            except AssertionError as exc:
                self.assertIn('unmapped read',str(exc))
                effective=True
            self.assertTrue(effective,name)
        cached=screen.SELECTED.replace('s32 index;','s32 index, limit;').replace(
            '*(volatile s32 *)&D_80082FA0','limit').replace('                target = actor;\n',
            '                target = actor;\n                limit = *(volatile s32 *)&D_80082FA0;\n')
        screen.compile_candidate(self.root,self.out,'negative-cached-limit',cached)
        symbols=(screen.ENTRY,ACTORS,ACTORS+12)
        words=self.link('negative-cached-limit',symbols)
        memory=fixture(0,2,0,False,count=2,symbols=symbols)
        put(memory,ACTORS+0x32C+12,255,1)
        expected,events=reference(memory,symbols=symbols)
        wrong=AttachmentOracle(words,memory,symbols=symbols).run()
        self.assertNotEqual((wrong.memory,wrong.events),(expected,events))
        self.receipt('negatives',fresh_complete_effective_controls=len(controls)+1,
            cached_limit_alias_control_effective=True,
            repeated_angle_control_is_emitted_order_not_disjoint_final_value=True)

    def test_10_whole_linked_installation(self):
        source=(self.root/screen.SOURCE).read_text()
        if screen.recovery.ORIGINAL in source:
            self.assertEqual({name:hashlib.sha256((self.root/path).read_bytes()).hexdigest()
                for name,path in self.paths.items()},self.baseline)
            self.receipt('installation',installed=False,baseline_unchanged=True)
            return
        self.assertEqual(source,screen.install((self.out/'before-source').read_text()))
        with (self.root/self.paths['guards']).open(newline='') as stream:
            self.assertEqual(list(csv.DictReader(stream)),self.old_rows+self.rows)
        self.assertTrue((self.root/self.paths['guards']).read_bytes().startswith((self.out/'before-guards').read_bytes()))
        for name in ('progress','rodata'):
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes())
        before=(self.out/'before-elf').read_bytes()
        expected=bytearray(before)
        struct.pack_into('>89I',expected,elf_slot_offset(before,screen.ENTRY,356),*self.retail)
        with patch.multiple(initializer.base,FUNCTION=screen.FUNCTION,ENTRY=screen.ENTRY):
            struct.pack_into('>I',expected,initializer.target_symbol_size_offset(before),356)
        actual=(self.root/self.paths['elf']).read_bytes()
        em,am=metadata(bytes(expected)),metadata(actual)
        self.assertEqual(em[:4],am[:4])
        for section in em[4:]:
            offset,length=section[4],section[5]
            expected[offset:offset+length]=actual[offset:offset+length]
        self.assertEqual(bytes(expected),actual)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertTrue(audit['exact'],audit)
        self.receipt('installation',installed=True,only_target_356_bytes_and_symbol_extent_changed=True,
            old_guards_exact_prefix_and_conversion_unchanged=True,protected_data=audit)

    def test_11_complete_banked_dispatcher_and_slot_updater(self):
        class Connected(AttachmentOracle):
            def record_call(model,target):
                counts=dict(dispatch.COUNTS)
                counts.update({0x1502EE8C:2,0x1507E3C0:1})
                args=model.arguments(counts[target])
                model.calls.append((target,*args))
                model.events.append(('CALL',target,args))
            def hook(model,target):
                if target==0x1503A08C: model.put(model.actor+0x1D4,0,4)
                assert target not in (screen.ENTRY,0x1502EEF4,0x1502EE8C,0x1507E3C0)
                for register in (1,2,3,*range(4,16),24,25): model.r[register]=0xA5000000+register
                model.f[:20]=[0xA5000000+i for i in range(20)]
        cases=0
        caller=[self.banked[dispatch.ENTRY+i*4] for i in range(88)]
        for slot,state,active,flags,matrix,phase in itertools.product((0,25),(0,2,3,5),
                (0,1),(0,2,0x20,0x40,0x60),(False,True),(0,8)):
            attachment=26 if slot==0 else 1
            memory=fixture(slot,attachment,flags,matrix)
            actor=ACTORS+slot*0x32C
            for offset,value,size in ((0,active,4),(4,7,1),(5,state,1),(0xA4,0,1),
                    (0x6C,1,1),(0x6D,9,1),(0xF8,0,4),(0x1C9,0,1),(0x260,0,4)):
                put(memory,actor+offset,value,size)
            memory.update({dispatch.FLAGS+i:0 for i in range(26*16)})
            models=[]
            for body in (self.retail,self.current):
                connected=dict(self.banked)
                connected.update({screen.ENTRY+i*4:word for i,word in enumerate(body)})
                model=Connected(caller,memory,slot,phase=phase,entry=dispatch.ENTRY,
                    arguments=(actor,slot),connected=connected)
                model.actor=actor
                model.run()
                self.assertEqual((screen.ENTRY,slot) in model.calls,state==0 and bool(active))
                if state==0 and active:
                    self.assertIn((0x1502EEF4,slot),model.calls)
                    self.assertIn((0x1502EE8C,slot,0),model.calls)
                    self.assertIn((0x1507E3C0,actor),model.calls)
                models.append(model)
            self.assertEqual((models[0].memory,models[0].events,models[0].calls),
                (models[1].memory,models[1].events,models[1].calls))
            cases+=1
        self.receipt('caller',cases=cases,actual_banked_dispatcher_words=88,
            actual_slot_updater_words=74,actual_classifier_words=26,actual_final_helper_words=80,
            actual_installed_or_fitted_attachment_helper=True,other_callbacks_bounded_opaque=True,
            full_connected_memory_traces_and_ABI_exact=True)

    def test_12_actual_native_global_alias_decreases_loop_limit(self):
        original=self.fixture
        try:
            self.fixture=self.fixture.replace('static s32 D_80082FA0;',
                'extern s32 D_80082FA0;\n__asm__(".globl D_80082FA0\\n.set D_80082FA0,D_800CC2D0+12");').replace(
                'i<=D_80082FA0','i<=*(volatile s32 *)((u8 *)expected+12)')
            self.run_host('''s32 i;
reset(0,2,0,2,0);
for(i=12;i<=15;i++) D_800CC2D0[0x32C+i]=0;
for(i=0;i<26*0x32C/4;i++) expected[i]=((u32 *)D_800CC2D0)[i];
expect(0);func_1502F264(0);
for(i=0;i<26*0x32C/4;i++) if(((u32 *)D_800CC2D0)[i]!=expected[i]) return 1;
if(D_80082FA0!=0 || D_800CC2D0[13]!=((expected[3]>>8)&255)) return 2;''')
        finally:
            self.fixture=original
        self.receipt('native-alias',cases=1,actual_symbol_alias=True,complete_C_unchanged=True,
            freshly_decreasing_limit_not_cached=True,little_endian_native_alias_only=True)


if __name__=='__main__':
    unittest.main()
