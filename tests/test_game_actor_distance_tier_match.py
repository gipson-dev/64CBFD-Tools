"""Full tier behavior, original private traces, closed recipe and linked-only audit."""
import csv
import hashlib
import itertools
import json
import math
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_distance_tier_matching as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,parse_object,emit_padded_assembly
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_attachment_update_match as attachment
from tools.tests import test_game_owner_points_initializer_match as initializer
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_owner_state_match import metadata
from tools.tests.test_game_owner_actor_update_match import put,read
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import bits,floating

STACK=attachment.STACK
PLAYERS,TABLE,ALTERNATE=0x24000,0x28000,0x29000
IDENTITY,UPDATE=0x150849A0,0x150837D4
LINKS=(screen.recovery.SYMBOLS,
    dict(D_800CC2D0=0x80118004,D_800DBFF0=0x80127FFC,D_800BE616=0x80138004,
        D_800C35EA=0x80147FFC,D_80096DE0=0x80158004,D_80096DE4=0x80168004,
        func_150849A0=0x15208004,func_150837D4=0x15217FFC),
    dict(D_800CC2D0=0x80227FFC,D_800DBFF0=0x80238004,D_800BE616=0x80247FFC,
        D_800C35EA=0x80258004,D_80096DE0=0x80267FFC,D_80096DE4=0x80277FFC,
        func_150849A0=0x15317FFC,func_150837D4=0x15328004))


def rounded(value):
    try: return floating(bits(value))
    except OverflowError: return math.copysign(math.inf,value)


def public(address):
    return not STACK-0x300<=address<STACK+0x100


def projection(memory,events):
    return ({a:v for a,v in memory.items() if public(a)},
        [e for e in events if e[0]=='CALL' or public(e[1])])


def fixture(slot=0,view=0,selector=5,distance=1000.0,speed=3.0,identity=1,
        prepare=0,state=0,tier=255,force=0,mode=0,phase=0,symbols=LINKS[0]):
    actor=symbols['D_800CC2D0']+slot*0x32C
    view=((view&65535)^32768)-32768
    player=(PLAYERS+view*0x9A0)&0xFFFFFFFF
    memory={STACK+phase+i:0xA5 for i in range(-0x300,0x100)}
    for address,size in ((actor,0x32C),(player,0x310),(TABLE,256),(ALTERNATE,256)):
        memory.update({address+i:(i*17+0x35)&255 for i in range(size)})
    for address,value,size in ((actor+0x1C9,prepare,1),(actor+5,state,1),(actor+0x1C8,tier,1),
            (actor+0x2C8,selector,1),(actor+0x2C4,TABLE,4),(actor+0x3C,bits(speed),4),
            (symbols['D_800DBFF0'],PLAYERS,4),(symbols['D_80096DE0'],bits(730.0),4),
            (symbols['D_80096DE4'],bits(1500.0),4),(symbols['D_800BE616'],force,1),
            (symbols['D_800C35EA'],mode,1),(TABLE,identity,1)):
        put(memory,address,value,size)
    for axis,value in enumerate((distance,0.0,0.0)):
        put(memory,player+0x2F8+axis*4,bits(value))
        put(memory,actor+0x14+axis*4,0)
    for i in range(4): del memory[STACK+phase-0x50+0x10+i]
    return memory


def reference(memory,slot=0,view=0,unused=0x12345678,phase=0,symbols=LINKS[0],
        identity=1,actions=(),update_actions=(),actual=False):
    result,events=memory.copy(),[]
    frame=STACK+phase-0x50
    def get(address,size=4):
        assert all(address+i in result for i in range(size)),(address,size)
        value=read(result,address,size)
        events.append(('R',address,size,value))
        return value
    def store(address,value,size=4):
        assert all(address+i in result for i in range(size)),(address,size)
        put(result,address,value,size)
        events.append(('W',address,size,value&((1<<(size*8))-1)))
    store(frame+0x54,view)
    store(frame+0x14,0xDEAD0000)
    store(frame+0x50,slot)
    store(frame+0x58,unused)
    slot=get(frame+0x50)
    actor=(symbols['D_800CC2D0']+slot*0x32C)&0xFFFFFFFF
    prepare=get(actor+0x1C9,1)
    signed_view=((view&65535)^32768)-32768
    player=(get(symbols['D_800DBFF0'])+signed_view*0x9A0)&0xFFFFFFFF
    if prepare or get(actor+5,1)==7:
        get(frame+0x14)
        return result,events
    thresholds=(bits(500.0),get(symbols['D_80096DE0']),get(symbols['D_80096DE4']),bits(2000.0))
    for index,value in enumerate(thresholds): store(frame+0x28+index*4,value)
    selector=get(actor+0x2C8,1)-1
    if selector==-1:
        get(frame+0x14)
        return result,events
    store(frame+0x4C,player)
    store(frame+0x3C,selector)
    store(frame+0x1C,actor)
    events.append(('CALL',symbols['func_150849A0'],(actor,)))
    if actual:
        current=get(actor+0x1C9,1)
        table=get(actor+0x2C4)
        identity=get((table+max(current-1,0))&0xFFFFFFFF,1)
    for address,value,size in actions: store(address,value,size)
    player,actor,selector=get(frame+0x4C),get(frame+0x1C),get(frame+0x3C)
    selector=(selector^0x80000000)-0x80000000
    coordinates=[]
    for axis in range(3):
        coordinates.append((floating(get(player+0x2F8+axis*4)),floating(get(actor+0x14+axis*4))))
    limit0=floating(get(frame+0x28))
    deltas=[rounded(a-b) for a,b in coordinates]
    distance=rounded(rounded(rounded(deltas[0]*deltas[0])+rounded(deltas[1]*deltas[1]))+
        rounded(deltas[2]*deltas[2]))
    limit1=floating(get(frame+0x2C))
    if distance<rounded(limit0*limit0): tier=0
    else:
        limit2=floating(get(frame+0x30))
        if distance<rounded(limit1*limit1): tier=1
        else:
            limit3=floating(get(frame+0x34))
            if distance<rounded(limit2*limit2): tier=2
            elif distance<rounded(limit3*limit3): tier=3
            else: tier=4
    if tier>=2 and floating(get(actor+0x3C))<3.0: tier-=1
    if identity:
        if identity==90 and tier==0: tier=1
    elif get(symbols['D_800BE616'],1): tier=1
    if get(symbols['D_800C35EA'],1)==1: tier=0
    if selector<tier: tier=max(selector,0)
    if tier!=-1 and tier!=get(actor+0x1C8,1):
        table=get(actor+0x2C4)
        slot=get(frame+0x50)
        identity=get((table+tier)&0xFFFFFFFF,1)
        store(frame+0x1C,actor)
        store(frame+0x40,tier)
        events.append(('CALL',symbols['func_150837D4'],(slot,identity,0)))
        for address,value,size in update_actions: store(address,value,size)
        tier,actor=get(frame+0x40),get(frame+0x1C)
        store(actor+0x1C8,tier,1)
    get(frame+0x14)
    return result,events


class DistanceOracle(attachment.AttachmentOracle):
    def __init__(self,words,memory,slot=0,view=0,unused=0x12345678,phase=0,symbols=LINKS[0],
            identity=1,actions=(),update_actions=(),**kwargs):
        super().__init__(words,memory,slot,(screen.ENTRY,0,0),phase,
            arguments=(slot,view,unused),**kwargs)
        self.symbols,self.identity,self.actions,self.update_actions=symbols,identity,actions,update_actions
    def record_call(self,target):
        count=1 if target==self.symbols['func_150849A0'] else 3
        assert target in (self.symbols['func_150849A0'],self.symbols['func_150837D4'])
        args=self.arguments(count)
        self.calls.append((target,*args))
        self.events.append(('CALL',target,args))
    def hook(self,target):
        actions=self.actions if target==self.symbols['func_150849A0'] else self.update_actions
        for address,value,size in actions: self.put(address,value,size)
        for register in (1,2,3,*range(4,16),24,25): self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=self.identity
    def execute(self,word):
        try: super().execute(word)
        except OverflowError:
            op,rs,fn=word>>26,word>>21&31,word&63
            assert op==17 and rs==16 and fn in (0,1,2)
            left,right=floating(self.f[word>>11&31]),floating(self.f[word>>16&31])
            result=left+right if fn==0 else left-right if fn==1 else left*right
            self.f[word>>6&31]=bits(math.copysign(math.inf,result))


class GameActorDistanceTierMatchTests(unittest.TestCase):
    run_host=attachment.GameActorAttachmentUpdateMatchTests.run_host
    assemble=classmethod(attachment.GameActorAttachmentUpdateMatchTests.assemble.__func__)
    write_rows=classmethod(attachment.GameActorAttachmentUpdateMatchTests.write_rows.__func__)

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-distance-tier-match-test'
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
        cls.retail=list(struct.unpack_from('>163I',cls.rom,screen.ROM))
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
            cls.current=list(struct.unpack_from('>163I',cls.elf,elf_slot_offset(cls.elf,screen.ENTRY,652)))
        body=list(struct.unpack_from('>11I',cls.elf,elf_slot_offset(cls.elf,IDENTITY,44)))
        assert body==list(struct.unpack_from('>11I',cls.rom,0xB1E50))
        cls.banked={IDENTITY+i*4:word for i,word in enumerate(body)}
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
        cls.fixture='''typedef unsigned char u8; typedef unsigned int u32; typedef int s32;
typedef short s16; typedef float f32;
static u8 D_800CC2D0[26*0x32C] __attribute__((aligned(16))),players[4*0x9A0],*D_800DBFF0=players;
static u8 D_800BE616,D_800C35EA,table[256];
static f32 D_80096DE0=730.0f,D_80096DE4=1500.0f;
static s32 identity,calls,updates,lastSlot,lastId,lastZero,mutate;
s32 func_150849A0(u8 *actor) {
    calls++;
    if(mutate) { *(f32 *)(actor+0x14)=1000.0f;actor[0x2C8]=1;D_800BE616=1;D_80096DE0=1.0f; }
    return identity;
}
void func_150837D4(s32 slot,s32 id,s32 zero) {
    updates++;lastSlot=slot;lastId=id;lastZero=zero;
    D_800CC2D0[slot*0x32C+0x1C8]=99;
}
static f32 frombits(u32 value) { union {u32 word;f32 value;} u;u.word=value;return u.value; }
static s32 expected(f32 x,f32 speed,s32 selector,s32 code,s32 force,s32 mode) {
    f32 square=x*x; s32 tier;
    if(square<250000.0f) tier=0;else if(square<532900.0f) tier=1;
    else if(square<2250000.0f) tier=2;else if(square<4000000.0f) tier=3;else tier=4;
    if(tier>=2 && speed<3.0f) tier--;
    if(code==0) {if(force) tier=1;} else if(code==90 && tier==0) tier=1;
    if(mode==1) tier=0;
    if(selector-1<tier) tier=selector-1;
    return tier;
}
''' + screen.SELECTED+'\n'

    @classmethod
    def link(cls,name,symbols):
        script=cls.out/('link-%s-%X-%X.ld'%(name,symbols['D_800CC2D0'],symbols['D_80096DE0']))
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%screen.ENTRY)
        elf=script.with_suffix('.elf')
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(cls.out/(name+'.o'))],
            check=True,capture_output=True)
        size=parse_object(cls.out/(name+'.o'))[1][screen.FUNCTION]['size']//4
        return list(struct.unpack_from('>%dI'%size,sections(elf)['.text'][1]))

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def compare(self,memory,slot=0,view=0,unused=0x12345678,phase=0,symbols=LINKS[0],
            identity=1,actions=(),update_actions=(),actual=False,bodies=None,raw=True):
        expected,events=reference(memory,slot,view,unused,phase,symbols,identity,actions,update_actions,actual)
        models=[]
        for body in bodies or (self.retail,self.current):
            model=DistanceOracle(body,memory,slot,view,unused,phase,symbols,identity,actions,update_actions,
                connected=self.banked if actual else None).run()
            self.assertEqual((model.memory,model.events),(expected,events))
            models.append(model)
        if raw and symbols==LINKS[0]:
            model=DistanceOracle(self.raw,memory,slot,view,unused,phase,symbols,identity,actions,update_actions,
                connected=self.banked if actual else None).run()
            self.assertEqual(projection(model.memory,model.events),projection(expected,events))
        return models

    def test_01_closed_shape_and_all_words(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['pool_bytes'],self.meta['diagnostics']),
            (163,0x50,0,''))
        self.assertEqual(self.linked,self.retail)
        self.assertEqual(self.current,self.retail)
        self.assertEqual(len(self.rows),163)
        self.assertEqual(sum(r['expected']!=r['replacement'] for r in self.rows),33)
        self.assertFalse(any(r['insert_after'] or r['omit']!='false' for r in self.rows))
        self.receipt('shape',words=163,frame=80,guards=163,changed_words=33,dependencies=130,
            insertions=0,omissions=0,padding=0,relocations=14,one_HI16_schedule_move=True)

    def test_02_distance_boundaries_modes_and_signed_view_ABI(self):
        cases,coverage=0,set()
        distances=(0.0,499.99997,500.0,729.99994,730.0,1499.9999,1500.0,1999.9999,2000.0,
            math.inf,math.nan,1e20,-500.0)
        for distance,speed,identity,force,mode,selector in itertools.product(distances,(2.0,3.0,math.nan),
                (0,90,255),(0,1),(0,1,2),(1,2,5)):
            models=self.compare(fixture(selector=selector,distance=distance,speed=speed,identity=identity,
                force=force,mode=mode),identity=identity)
            coverage.update(models[0].visits)
            cases+=1
        for slot,view,prepare,state,selector,tier in itertools.product((0,25),
                (0,1,3,0xFFFF,0x8000,0x12340002),(0,1),(0,7),(0,5),(0,255)):
            model=self.compare(fixture(slot,view,selector,prepare=prepare,state=state,tier=tier),slot,view)[0]
            coverage.update(model.visits)
            cases+=1
        for tier,distance in enumerate((0.0,500.0,730.0,1500.0,2000.0)):
            model=self.compare(fixture(distance=distance,tier=tier))[0]
            self.assertEqual(model.calls,[(IDENTITY,LINKS[0]['D_800CC2D0'])])
            coverage.update(model.visits)
            cases+=1
        self.assertEqual([i for i in range(163) if screen.ENTRY+i*4 not in coverage],[141,144])
        self.receipt('guest',cases=cases,retail_words_reached=len(coverage),
            unreachable_words=[i for i in range(163) if screen.ENTRY+i*4 not in coverage],
            raw_disjoint_public_results_and_order_exact=True,retail_fitted_full_private_traces_exact=True,
            finite_overflow_infinity_and_NaN_tiers=True,raw_nan_payloads_and_FP_exceptions_not_claimed=True)

    def test_03_actual_banked_callee_and_mutations(self):
        cases=0
        for slot,view,identity,selector,phase in itertools.product((0,25),(0,3),(0,90,255),(0,1,5,255),(0,8)):
            self.compare(fixture(slot,view,selector,identity=identity,phase=phase),slot,view,phase=phase,actual=True)
            cases+=1
        for slot,phase in itertools.product((0,25),(0,8)):
            actor=LINKS[0]['D_800CC2D0']+slot*0x32C
            memory=fixture(slot,selector=5,distance=2000,phase=phase)
            actions=((actor+0x14,bits(1000.0),4),(actor+0x2C8,1,1),
                (LINKS[0]['D_800DBFF0'],0x90000000,4),(LINKS[0]['D_80096DE0'],bits(1.0),4),
                (actor+0x2C4,ALTERNATE,4),(LINKS[0]['D_800C35EA'],1,1))
            update=((actor+0x1C8,99,1),(actor+0x2C4,TABLE,4))
            self.compare(memory,slot,phase=phase,actions=actions,update_actions=update)
            cases+=1
        self.receipt('callee',cases=cases,actual_banked_identity_words=11,
            cached_player_selector_thresholds_and_fresh_coordinates_globals_table=True,
            final_tier_store_overwrites_callback_mutation=True,second_callback_bounded_opaque=True)

    def test_04_private_aliases_and_physical_distinction(self):
        cases=0
        for phase,offset in itertools.product((0,8),(0x14,0x1C,0x28,0x2C,0x30,0x34,0x3C,0x40,0x4C,0x50)):
            memory=fixture(phase=phase)
            actor=LINKS[0]['D_800CC2D0']
            put(memory,actor+0x2C4,STACK+phase-0x50+offset-1)
            self.compare(memory,phase=phase,identity=1,raw=False)
            cases+=1
        for phase,selector in itertools.product((0,8),(0xFFFFFFFF,0x80000000,0,4)):
            memory=fixture(phase=phase)
            actions=((STACK+phase-0x50+0x3C,selector,4),)
            self.compare(memory,phase=phase,actions=actions,raw=False)
            cases+=1
        memory=fixture(distance=1000.0,selector=5)
        actions=((STACK-0x50+0x3C,0,4),)
        expected,events=reference(memory,actions=actions)
        wrong=DistanceOracle(self.raw,memory,actions=actions).run()
        self.assertNotEqual(projection(wrong.memory,wrong.events),projection(expected,events))
        self.receipt('aliases',cases=cases,retail_fitted_complete_private_aliases_exact=True,
            raw_physical_home_difference_discriminated=True,raw_not_claimed_private_alias_equivalent=True)

    def test_05_complete_verified_fault_prefixes(self):
        prefixes=0
        for prepare,state,selector,distance,phase in itertools.product((0,1),(0,7),(0,5),(0.0,2000.0),(0,8)):
            memory=fixture(prepare=prepare,state=state,selector=selector,distance=distance,phase=phase)
            _,events=reference(memory,phase=phase)
            ordinal=0
            for index,event in enumerate(events):
                if event[0]=='CALL': continue
                expected=memory.copy()
                for prior in events[:index]:
                    if prior[0]=='W': put(expected,prior[1],prior[3],prior[2])
                for body in (self.retail,self.current):
                    model=DistanceOracle(body,memory,phase=phase)
                    model.fault=ordinal
                    with self.assertRaises(attachment.AccessFault) as caught: model.run()
                    self.assertEqual(caught.exception.args,(ordinal,))
                    self.assertEqual((model.memory,model.events),(expected,events[:index]))
                prefixes+=1
                ordinal+=1
        self.receipt('faults',verified_prefixes=prefixes,executions=prefixes*2,
            full_private_public_prefixes_and_fired_gates_exact=True)

    def test_06_independent_links_and_actual_stale_rejections(self):
        cases=0
        for symbols in LINKS:
            bodies=tuple(self.link(name,symbols) for name in ('original','fitted'))
            for slot,view,identity,distance in itertools.product((0,25),(0,3),(0,90),(0.0,730.0,2000.0)):
                self.compare(fixture(slot,view,distance=distance,identity=identity,symbols=symbols),slot,view,
                    symbols=symbols,identity=identity,bodies=bodies,raw=False)
                cases+=1
        data=(self.out/'selected.o').read_bytes()
        h=ELF_HEADER.unpack_from(data)
        headers=[SECTION_HEADER.unpack_from(data,h[6]+i*h[11]) for i in range(h[12])]
        ns=headers[h[13]]
        names=data[ns[4]:ns[4]+ns[5]]
        text=next(s for s in headers if names[s[0]:].split(b'\0',1)[0]==b'.text')
        for index in range(163):
            stale=bytearray(data)
            struct.pack_into('>I',stale,text[4]+index*4,screen.RAW[index]^0x10000)
            path=self.out/'stale.o'
            path.write_bytes(stale)
            with self.assertRaisesRegex(ValueError,'stale complete'):
                screen.recipe([w^0x10000 if i==index else w for i,w in enumerate(screen.RAW)])
            with self.assertRaisesRegex(ValueError,'stale word patch'):
                emit_padded_assembly(path,self.slot_asm,word_patches_path=self.out/'isolated.csv',filename='generated_58F80')
        for offset in screen.RELOCATIONS:
            rows=[dict(row) for row in self.rows]
            rows[offset//4]['expected_relocations']='-'
            path=self.out/'stale-relocations.csv'
            self.write_rows(path,rows)
            with self.assertRaisesRegex(ValueError,'stale relocations'):
                emit_padded_assembly(self.out/'selected.o',self.slot_asm,word_patches_path=path,filename='generated_58F80')
        self.receipt('links-and-stale',cases=cases,independent_links=6,symbol_sets=3,
            actual_word_rejections=163,actual_relocation_rejections=14,moved_HI16_and_signed_LO16_carries=True)

    def test_07_copied_owner_and_actual_padder(self):
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
        self.assertEqual(padded[1][1][screen.FUNCTION]['size'],652)
        self.assertEqual(padded[0][0][:start],padded[1][0][:start])
        self.assertEqual(padded[0][0][start+652:],padded[1][0][start+652:])
        self.receipt('owner',neighbors=len(nf)-1,relative_relocations_and_pools_unchanged=True,
            only_target_padded_slot_changes=True)

    def test_08_actual_native32_complete_C(self):
        self.run_host('''s32 slot,view,selector,k,j,code,i,want,beforeCalls,beforeUpdates;
static f32 distances[]={0,499,500,730,1500,2000};
static s32 codes[]={0,90,255};
for(i=0;i<256;i++) table[i]=(u8)(i*17+0x35);
for(slot=0;slot<26;slot++) for(view=0;view<4;view++) for(selector=0;selector<256;selector++)
for(k=0;k<6;k++) for(j=0;j<3;j++) for(code=0;code<3;code++) {
    u8 *actor=D_800CC2D0+slot*0x32C,*player=players+view*0x9A0;
    f32 speed=j==2?frombits(0x7FC12345):(f32)(j+2);
    actor[0x1C9]=0;actor[5]=0;actor[0x1C8]=255;actor[0x2C8]=(u8)selector;
    *(u8 **)(actor+0x2C4)=table;*(f32 *)(actor+0x3C)=speed;
    for(i=0;i<3;i++) {*(f32 *)(actor+0x14+i*4)=0;*(f32 *)(player+0x2F8+i*4)=i==0?distances[k]:0;}
    identity=codes[code];D_800BE616=(u8)(selector&1);D_800C35EA=(u8)(selector%3);
    want=expected(distances[k],speed,selector,identity,D_800BE616,D_800C35EA);
    beforeCalls=calls;beforeUpdates=updates;func_1502C6E8(slot,(s16)view,0x12345678);
    if(calls!=beforeCalls+(selector!=0) || updates!=beforeUpdates+(selector!=0)) return 1;
    if(actor[0x1C8]!=(selector?want:255) || (selector&&(lastSlot!=slot||lastId!=table[want]||lastZero))) return 2;
}
mutate=1;
for(slot=0;slot<26;slot++) for(view=0;view<4;view++) {
    u8 *actor=D_800CC2D0+slot*0x32C,*player=players+view*0x9A0;
    actor[0x1C9]=0;actor[5]=0;actor[0x1C8]=255;actor[0x2C8]=5;
    *(u8 **)(actor+0x2C4)=table;*(f32 *)(actor+0x3C)=3;
    for(i=0;i<3;i++) {*(f32 *)(actor+0x14+i*4)=0;*(f32 *)(player+0x2F8+i*4)=i==0?2000:0;}
    identity=1;D_800BE616=0;D_800C35EA=0;D_80096DE0=730;
    func_1502C6E8(slot,(s16)view,0);
    if(actor[0x1C8]!=2 || actor[0x2C8]!=1 || lastId!=table[2]) return 3;
}''')
        self.receipt('native',cases=26*4*256*6*3*3+26*4,actual_complete_C=True,
            all_bounded_slots_views_and_selector_bytes=True,callback_capture_and_final_store=True)

    def test_09_fresh_effective_negative_controls(self):
        controls={name:body for name,body in screen.recovery.candidates() if name.startswith('negative-')}
        controls['negative-view-cap']=screen.SELECTED.replace('if (selector < tier)','if (view < tier)').replace(
            'tier = selector;','tier = view;').replace('if (selector < 0)','if (view < 0)')
        for name,body in controls.items():
            _,words=screen.compile_candidate(self.root,self.out,name,body)
            selector=0 if name=='negative-zero-based-selector' else 1 if name=='negative-no-clamp' else 5
            distance=500.0 if name=='negative-inclusive-distance' else 2000.0
            memory=fixture(selector=selector,distance=distance,speed=2.0)
            expected,events=reference(memory)
            wrong=DistanceOracle(words,memory).run()
            self.assertTrue(projection(wrong.memory,wrong.events)!=projection(expected,events),name)
        self.receipt('negatives',fresh_effective_complete_controls=len(controls),wrong_view_cap_rejected=True)

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
        struct.pack_into('>163I',expected,elf_slot_offset(before,screen.ENTRY,652),*self.retail)
        with patch.multiple(initializer.base,FUNCTION=screen.FUNCTION,ENTRY=screen.ENTRY):
            struct.pack_into('>I',expected,initializer.target_symbol_size_offset(before),652)
        actual=(self.root/self.paths['elf']).read_bytes()
        em,am=metadata(bytes(expected)),metadata(actual)
        self.assertEqual(em[:4],am[:4])
        for section in em[4:]:
            offset,length=section[4],section[5]
            expected[offset:offset+length]=actual[offset:offset+length]
        self.assertEqual(bytes(expected),actual)
        audit=audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertTrue(audit['exact'],audit)
        self.receipt('installation',installed=True,only_target_652_bytes_and_symbol_extent_changed=True,
            old_guards_exact_prefix_conversion_unchanged=True,protected_data=audit)

    def test_11_literal_call_site_forwarding_not_complete_caller(self):
        class Connected(DistanceOracle):
            def record_call(model,target):
                if target!=screen.ENTRY: return super().record_call(target)
                args=model.arguments(3)
                model.calls.append((target,*args))
                model.events.append(('CALL',target,args))
        caller=list(struct.unpack_from('>4I',self.rom,0x59F4C))
        self.assertEqual(caller,[0x87A50062,0x8FA4005C,0x0D40B1BA,0xAFA7002C])
        # Synthetic return boundary isolates the literal call from the unrestored caller.
        caller.extend((0x8FBF0020,0x03E00008,0))
        cases=0
        for slot,view,selector,unused,phase in itertools.product((0,25),
                (0,3,0xFFFF,0x8000,0x12340002),(0,5),(0,1,2),(0,8)):
            memory=fixture(slot,view,selector,phase=phase)
            stack=STACK+phase
            actor=LINKS[0]['D_800CC2D0']+slot*0x32C
            put(memory,stack+0x20,0xDEAD0000)
            put(memory,stack+0x5C,slot)
            put(memory,stack+0x60,view)
            models=[]
            for body in (self.retail,self.current,self.raw):
                connected={screen.ENTRY+i*4:word for i,word in enumerate(body)}
                model=Connected(caller,memory,slot,view,unused,phase,entry=0x1502CA9C,connected=connected)
                model.r[7]=actor
                model.run()
                signed_view=(((view&65535)^32768)-32768)&0xFFFFFFFF
                self.assertIn((screen.ENTRY,slot,signed_view,unused),model.calls)
                models.append(model)
            self.assertEqual((models[0].memory,models[0].events,models[0].calls),
                (models[1].memory,models[1].events,models[1].calls))
            self.assertEqual(projection(models[0].memory,models[0].events),
                projection(models[2].memory,models[2].events))
            cases+=1
        self.receipt('caller',cases=cases,literal_retail_instructions=4,synthetic_return_boundary=True,
            complete_placeholder_caller_not_qualified=True,slot_signed_view_unused_forwarding=True)


if __name__=='__main__':
    unittest.main()
