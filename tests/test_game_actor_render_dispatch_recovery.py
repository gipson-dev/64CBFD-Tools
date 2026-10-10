"""Complete caller semantics; disjoint public traces, not a physical byte-match claim."""
import hashlib
import itertools
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_actor_render_dispatch_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object
from tools.check_game_data_layout import audit_layout
from tools.tests import test_game_actor_distance_tier_match as distance
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import signed

STACK,OUTPUT,CONFIG,OWNER,TABLE=distance.STACK,0x20000,0x2A000,0x2B000,0x2C000
NAMES=('func_150229E4','func_1506196C','func_1502C6E8','func_150849CC',
    'func_1502D54C','func_1502D630','func_1502CCFC')
COUNTS=dict(zip(NAMES,(1,2,3,2,2,3,8)))
S=screen.SYMBOLS
ALPHAS=(-0x80000000,-1,0,1,254,255,256,0x7FFFFFFF)
PATHS=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
    guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
    rodata='conker/asm/data/23B8A0.rodata.s')


def public(address):
    return not STACK-0x600<=address<STACK+0x100


def fixture(slot=0,view=0,mask=0,first_gate=0,second_gate=0,matrix=True,
        enabled=0,owner=0,owner_view=0,factor=128,limit=32,base=OUTPUT):
    memory={STACK+i:0xA5 for i in range(-0x600,0x100)}
    actor=S['D_800CC2D0']+slot*0x32C
    for start,length in ((actor,0x32C),(OUTPUT,0x200),(CONFIG,0x100),
            (OWNER,0x40),(TABLE,256),(S['D_800BE9C8'],1024)):
        memory.update({start+i:(i*17+0x35)&255 for i in range(length)})
    for address,value,size in ((S['D_800C3638'],first_gate,1),
            (S['D_800C3656'],second_gate,1),(actor+0x74,mask,1),
            (actor+0x1D4,0x22000 if matrix else 0,4),(actor+0x318,OWNER if owner else 0,4),
            (OWNER+0x2C,owner,4),(actor+0x127,owner_view,1),
            (actor+0x1C8,2,1),(actor+0x1C9,0,1),(actor+0x2C8,5,1),(actor+0x2C4,TABLE,4),
            (S['D_800B0DF0'],CONFIG,4),(CONFIG+0x3E,enabled,2),
            (S['D_800DF7C4'],factor,1),(S['D_800DF7C0'],0x23000,4),
            (S['D_800BE9C0'],0,1),(S['D_800BE9C8'],base,4),(S['D_800BEBA4'],limit,4)):
        distance.put(memory,address,value,size)
    return memory


class Plan:
    def __init__(self,first=255,second=255,visible=1,rendered=OUTPUT+16,actions=None):
        self.first,self.second,self.visible,self.rendered=first,second,visible,rendered
        self.actions=actions or {}


def reference(memory,slot=0,view=0,mode=0,extra=0,plan=None):
    plan=plan or Plan()
    result,events=memory.copy(),[]
    counts={}
    params=[0xA5A5A5A5]*4
    def get(address,size=4):
        value=distance.read(result,address,size)
        events.append(('R',address,size,value))
        return value
    def store(address,value,size=4):
        distance.put(result,address,value,size)
        if public(address): events.append(('W',address,size,value&((1<<(8*size))-1)))
    def call(name,args):
        ordinal=counts.get(name,0)
        counts[name]=ordinal+1
        events.append(('CALL',name,tuple(args)))
        if name=='func_1502C6E8':
            store(S['D_800CC2D0']+slot*0x32C+0x1C8,3,1)
        elif name=='func_1502D54C': params[:3]=(11,22,33)
        elif name=='func_1502D630': params[3]=144
        for address,value,size in plan.actions.get((name,ordinal),()): store(address,value,size)
        return plan.first if ordinal==0 else plan.second
    actor=(S['D_800CC2D0']+slot*0x32C)&0xFFFFFFFF
    if get(S['D_800C3638'],1) and not get(S['D_800C3656'],1):
        call('func_150229E4',(actor,))
        if not plan.visible: return OUTPUT,result,events
    mask=1<<(view&31)
    if get(actor+0x74,1)&mask==mask: return OUTPUT,result,events
    first=call('func_1506196C',(actor,view&0xFFFFFFFF))
    if not first or not get(actor+0x1D4): return OUTPUT,result,events
    if mode not in (3,4,5):
        narrow=(((view&65535)^32768)-32768)&0xFFFFFFFF
        call('func_1502C6E8',(slot,narrow,mode&0xFFFFFFFF))
        get(actor+0x1C8,1)
    else:
        call('func_150849CC',(actor,'tier-out'))
    call('func_1502D54C',(slot,'parameters'))
    enabled=get(get(S['D_800B0DF0'])+0x3E,2)
    if enabled: call('func_1502D630',(actor,'parameters',view&0xFFFFFFFF))
    else: params[3]=255
    alpha=signed(call('func_1506196C',(actor,view&0xFFFFFFFF)))
    if alpha<255:
        owner=get(actor+0x318)
        if owner:
            kind=get(owner+0x2C)
            if kind==0x100 and view&0xFFFFFFFF!=get(actor+0x127,1): alpha=255
    if mode==4:
        factor=get(S['D_800DF7C4'],1)
        matrix=get(S['D_800DF7C0'])
        alpha=signed(factor*(alpha&0xFFFFFFFF)&0xFFFFFFFF)>>8
    else: matrix=get(actor+0x1D4)
    call('func_1502CCFC',(OUTPUT,slot,view&0xFFFFFFFF,matrix,
        alpha&0xFFFFFFFF,tuple(params),mode&0xFFFFFFFF,extra&0xFFFFFFFF))
    index=get(S['D_800BE9C0'],1)
    base=get(S['D_800BE9C8']+index*4)
    limit=signed(get(S['D_800BEBA4']))
    output=OUTPUT if limit<(signed((plan.rendered-base)&0xFFFFFFFF)>>3) else plan.rendered
    return output,result,events


class DispatchOracle(distance.DistanceOracle):
    def __init__(self,words,memory,slot=0,view=0,mode=0,extra=0,phase=0,plan=None,connected=None):
        distance.attachment.AttachmentOracle.__init__(self,words,memory,slot,
            (screen.ENTRY,0,0),phase,entry=screen.ENTRY,
            arguments=(OUTPUT,slot,view,mode,extra),connected=connected)
        self.symbols,self.identity=distance.LINKS[0],1
        self.actions,self.update_actions=(),()
        self.plan=plan or Plan()
        self.counts={}
        self.pending=None
    def record_call(self,target):
        if target not in (S[name] for name in NAMES):
            return super().record_call(target)
        name=next(name for name in NAMES if S[name]==target)
        args=list(self.arguments(COUNTS[name]))
        ordinal=self.counts.get(name,0)
        self.counts[name]=ordinal+1
        self.pending=(name,args.copy(),ordinal)
        if name=='func_150849CC': args[1]='tier-out'
        elif name in ('func_1502D54C','func_1502D630'): args[1]='parameters'
        elif name=='func_1502CCFC':
            args[5]=tuple(self.peek(args[5]+i*4,4) for i in range(4))
        event=('CALL',name,tuple(args))
        self.calls.append(event)
        self.events.append(event)
    def hook(self,target):
        if target not in (S[name] for name in NAMES):
            return super().hook(target)
        name,args,ordinal=self.pending
        result=0
        if name=='func_150229E4': result=self.plan.visible
        elif name=='func_1506196C': result=self.plan.first if ordinal==0 else self.plan.second
        elif name=='func_1502C6E8': self.put(S['D_800CC2D0']+args[0]*0x32C+0x1C8,3,1)
        elif name=='func_150849CC': self.put(args[1],4,4)
        elif name=='func_1502D54C':
            for i,value in enumerate((11,22,33)): self.put(args[1]+i*4,value,4)
        elif name=='func_1502D630': self.put(args[1]+12,144,4)
        elif name=='func_1502CCFC': result=self.plan.rendered
        for address,value,size in self.plan.actions.get((name,ordinal),()): self.put(address,value,size)
        for register in (1,2,3,*range(4,16),24,25): self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=result&0xFFFFFFFF


def projection(model):
    return (model.r[2],{a:v for a,v in model.memory.items() if public(a)},
        [e for e in model.events if e[0]=='CALL' or public(e[1])])

class PublicFault(Exception):
    pass


class PublicFaultOracle(DispatchOracle):
    def __init__(self,*args,**kwargs):
        self.public_fault,self.public_accesses=None,0
        super().__init__(*args,**kwargs)
    def public_gate(self,address):
        if not public(address): return
        if self.public_accesses==self.public_fault: raise PublicFault(self.public_accesses)
        self.public_accesses+=1
    def get(self,address,size):
        self.public_gate(address)
        return super().get(address,size)
    def put(self,address,value,size):
        if self.recording: self.public_gate(address)
        super().put(address,value,size)


class GameActorRenderDispatchRecoveryTests(unittest.TestCase):
    run_host=distance.GameActorDistanceTierMatchTests.run_host
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-render-dispatch-test'
        cls.out.mkdir(exist_ok=True)
        if not (cls.out/'baseline.json').exists():
            baseline={}
            for name,path in PATHS.items():
                data=(cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                baseline[name]=hashlib.sha256(data).hexdigest()
            (cls.out/'baseline.json').write_text(json.dumps(baseline,indent=2)+'\n')
        cls.baseline=json.loads((cls.out/'baseline.json').read_text())
        cls.meta,cls.raw=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.layout_meta,cls.layout=screen.compile_candidate(cls.root,cls.out,'volatile-actor',
            dict(screen.candidates())['volatile-actor'])
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>176I',cls.rom,screen.ROM))
        cls.directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        cls.path=Path(cls.directory.name)
        cls.coverage=set()
    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')
    def compare(self,memory,slot=0,view=0,mode=0,extra=0,phase=0,plan=None):
        returned,result,events=reference(memory,slot,view,mode,extra,plan)
        expected=(returned,{a:v for a,v in result.items() if public(a)},events)
        models=[]
        for body in (self.retail,self.raw,self.layout):
            model=DispatchOracle(body,memory,slot,view,mode,extra,phase,plan).run()
            self.assertEqual(projection(model),expected)
            models.append(model)
        self.coverage.update(models[0].visits)
        return models
    def test_01_full_semantic_paths_and_signed_boundaries(self):
        cases=0
        for slot,view,mode,alpha,owner in itertools.product((0,25),(-1,0,3,32,0x12340002),
                (-1,0,3,4,5,6,7),ALPHAS,(0,0x100,7)):
            memory=fixture(slot,view,enabled=cases%2,owner=owner,owner_view=0,factor=cases%256)
            self.compare(memory,slot,view,mode,extra=0x12345678,phase=8 if cases%2 else 0,
                plan=Plan(second=alpha))
            cases+=1
        for gate,other,mask,view,first,matrix,visible in itertools.product((0,1),(0,1),(0,1,128),
                (0,7,8,31,32),(0,255),(False,True),(0,1)):
            memory=fixture(view=view,mask=mask,first_gate=gate,second_gate=other,matrix=matrix)
            self.compare(memory,view=view,plan=Plan(first=first,visible=visible))
            cases+=1
        self.receipt('semantic',cases=cases,complete_original_and_raw_public_order=True,
            complete_compiled_C_forms=2,full_private_alias_or_fault_order_not_claimed=True)
    def test_02_all_factor_bytes_and_cursor_limits(self):
        cases=0
        for factor,alpha in itertools.product(range(256),ALPHAS):
            self.compare(fixture(factor=factor),mode=4,plan=Plan(second=alpha))
            cases+=1
        for returned,base,limit in itertools.product((OUTPUT-9,OUTPUT-8,OUTPUT-1,OUTPUT,OUTPUT+7,
                OUTPUT+8,OUTPUT+16,0,0xFFFFFFFF,0x80000000),(0,OUTPUT,0x80000000),
                (-0x80000000,-1,0,1,2,0x7FFFFFFF)):
            self.compare(fixture(base=base,limit=limit),plan=Plan(rendered=returned))
            cases+=1
        self.receipt('factor-and-limit',cases=cases,all_256_factor_bytes=True,
            signed_low_word_product_shift_and_pointer_difference=True)
    def test_03_callback_sensitive_reload_order(self):
        actor=S['D_800CC2D0']
        actions=(
            {('func_150229E4',0):((actor+0x74,1,1),)},
            {('func_1506196C',0):((actor+0x1D4,0,4),)},
            {('func_1506196C',0):((actor+0x318,OWNER,4),(OWNER+0x2C,0x100,4))},
            {('func_1502D54C',0):((S['D_800B0DF0'],CONFIG+32,4),(CONFIG+94,1,2))},
            {('func_1502D630',0):((actor+0x1D4,0x33000,4),)},
            {('func_1506196C',1):((actor+0x1D4,0x34000,4),(actor+0x318,OWNER,4),
                (OWNER+0x2C,0x100,4),(actor+0x127,1,1))},
            {('func_1506196C',1):((S['D_800DF7C4'],255,1),(S['D_800DF7C0'],0x35000,4))},
            {('func_1502CCFC',0):((S['D_800BE9C0'],255,1),
                (S['D_800BE9C8']+255*4,OUTPUT+16,4),(S['D_800BEBA4'],-1,4))})
        cases=0
        for plan,mode,phase in itertools.product(actions,(0,3,4,5),(0,8)):
            self.compare(fixture(first_gate=1,enabled=1),mode=mode,phase=phase,
                plan=Plan(second=-1,actions=plan))
            cases+=1
        self.receipt('mutations',cases=cases,first_and_second_alpha_distinct=True,
            captured_actor_fresh_matrix_owner_globals_and_post_render_limit=True)
    def test_04_actual_banked_alternate_and_distance_connections(self):
        elf=(self.root/PATHS['elf']).read_bytes()
        bodies={}
        for entry,rom,words in ((S['func_150849CC'],0xB1E7C,19),
                (distance.screen.ENTRY,distance.screen.ROM,163),(distance.IDENTITY,0xB1E50,11)):
            body=list(struct.unpack_from('>%dI'%words,elf,elf_slot_offset(elf,entry,words*4)))
            self.assertEqual(body,list(struct.unpack_from('>%dI'%words,self.rom,rom)))
            bodies[entry]={entry+i*4:word for i,word in enumerate(body)}
        cases=0
        for prepare,selector,mode in itertools.product((0,1,255),(0,1,5,255),(3,4,5)):
            memory=fixture()
            actor=S['D_800CC2D0']
            distance.put(memory,actor+0x1C9,prepare,1)
            distance.put(memory,actor+0x2C8,selector,1)
            models=[DispatchOracle(body,memory,mode=mode,
                connected=bodies[S['func_150849CC']]).run() for body in (self.retail,self.raw,self.layout)]
            for model in models[1:]: self.assertEqual(projection(models[0]),projection(model))
            cases+=1
        for slot,view,selector,mode in itertools.product((0,25),(0,3),(0,1,5),(0,6)):
            memory=fixture(slot,view)
            child=distance.fixture(slot,view,selector)
            memory.update({a:v for a,v in child.items() if public(a)})
            distance.put(memory,S['D_800CC2D0']+slot*0x32C+0x74,0,1)
            distance.put(memory,S['D_800CC2D0']+slot*0x32C+0x318,0,4)
            connected=dict(bodies[distance.screen.ENTRY])
            connected.update(bodies[distance.IDENTITY])
            models=[DispatchOracle(body,memory,slot,view,mode,connected=connected).run()
                for body in (self.retail,self.raw,self.layout)]
            for model in models[1:]: self.assertEqual(projection(models[0]),projection(model))
            cases+=1
        self.receipt('connected',cases=cases,complete_176_word_caller_executed=True,
            actual_banked_alternate_19_distance_163_identity_11=True,
            other_callbacks_explicitly_bounded=True)
    def test_05_fresh_effective_complete_negatives(self):
        controls={name:body for name,body in screen.candidates() if name.startswith('negative-')}
        for name,body in controls.items():
            _,wrong=screen.compile_candidate(self.root,self.out,name,body)
            alpha=-1 if name in ('negative-unsigned-alpha','negative-divide-product') else 254
            owner=0x100 if name=='negative-unsigned-alpha' else 0
            mode=4 if name=='negative-divide-product' else 0
            limit=2 if name=='negative-inclusive-limit' else 0 if name=='negative-wrong-rollback' else 32
            memory=fixture(owner=owner,factor=1,limit=limit)
            plan=Plan(second=alpha)
            expected=DispatchOracle(self.retail,memory,mode=mode,plan=plan).run()
            result=DispatchOracle(wrong,memory,mode=mode,plan=plan).run()
            self.assertTrue(projection(expected)!=projection(result),name)
        self.receipt('negatives',fresh_effective_complete_controls=len(controls))
    def test_06_owner_neighbors_and_unchanged_production_gate(self):
        before=(self.out/'before-source').read_text()
        self.assertEqual(before.count(screen.ORIGINAL),1)
        objects=[]
        for name,source in (('owner-before',before),('owner-after',before.replace(screen.ORIGINAL,
                screen.DECLARATIONS+screen.SELECTED))):
            # Use isolated declarations compatible with the owner's existing actor type.
            if name=='owner-after':
                source=source.replace(screen.DECLARATIONS,
                    screen.DECLARATIONS.replace('extern u8 D_800CC2D0[],','extern u8 ').replace(
                    's32 func_1506196C(u8 *,s32);','').replace('void func_1502C6E8(s32,s16,s32);',''))
                source=source.replace('func_1506196C(actor, view)','func_1506196C((ActorDisplay58F80 *)actor, view)')
                # Keep adjacent placeholder bodies intact; their ignored results use O32 v0.
                source=source.replace('void func_1502D54C(s32,s32 *);','s32 func_1502D54C();').replace(
                    'void func_1502D630(u8 *,s32 *,s32);','s32 func_1502D630();').replace(
                    'Gfx *func_1502CCFC(Gfx *,s32,s32,u8 *,s32,s32 *,s32,s32);','s32 func_1502CCFC();').replace(
                    'commands = func_1502CCFC(commands,','commands = (Gfx *)func_1502CCFC(commands,')
            obj,diagnostics=compile_owner(self.root,self.out,source,name)
            self.assertEqual(diagnostics,[])
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',
                str(obj.relative_to(self.root/'conker')),'--assembler','mips-linux-gnu-as -EB -march=vr4300',
                '--asm-prelude','include/asm_processor_prelude.inc'],cwd=self.root/'conker',
                check=True,capture_output=True)
            objects.append(parse_object(obj))
        target=objects[1][1][screen.FUNCTION]
        isolated=parse_object(self.out/'selected.o')
        selected=isolated[1][screen.FUNCTION]
        self.assertEqual(objects[1][0][target['value']:target['value']+target['size']],
            isolated[0][selected['value']:selected['value']+selected['size']])
        first,second=objects
        neighbors=0
        for name,meta in first[1].items():
            if name==screen.FUNCTION or not meta['size']: continue
            after=second[1][name]
            self.assertEqual(first[0][meta['value']:meta['value']+meta['size']],
                second[0][after['value']:after['value']+after['size']],name)
            rel=lambda data,m:{offset-m['value']:uses for offset,uses in data[2].items()
                if m['value']<=offset<m['value']+m['size']}
            self.assertEqual(rel(first,meta),rel(second,after),name)
            neighbors+=1
        self.assertEqual(normalized_pools(self.out/'owner-before.o'),normalized_pools(self.out/'owner-after.o'))
        self.assertEqual({name:hashlib.sha256((self.root/path).read_bytes()).hexdigest()
            for name,path in PATHS.items()},self.baseline)
        audit=audit_layout(self.root/PATHS['elf'],self.root/'conker')
        self.assertTrue(audit['exact'],audit)
        self.receipt('owner-and-production',neighbors=neighbors,body_relocations_pools_exact=True,
            production_source_ELF_guards_conversion_rodata_unchanged=True,protected_data=audit,
            not_installed_frame_and_extent_unqualified=True)

    def test_07_actual_native32_complete_C(self):
        self.fixture='''typedef unsigned char u8; typedef unsigned int u32; typedef int s32;
typedef short s16; typedef union { u32 words[2]; } Gfx;
#define NULL ((void *)0)
static u8 D_800CC2D0[26*0x32C] __attribute__((aligned(16)));
static u8 D_800C3638,D_800C3656,D_800DF7C4,D_800BE9C0;
static u8 config[128] __attribute__((aligned(16))),owner[64] __attribute__((aligned(16)));
static u8 *D_800B0DF0=config,*D_800DF7C0=(u8 *)0x23000;
static Gfx output[64],*D_800BE9C8[256];
static s32 D_800BEBA4,firstAlpha,secondAlpha,alphaCalls,updates,alternate,shadeCalls,renderCalls;
static s32 lastAlpha,lastSlot,lastView,lastMode,lastExtra,lastParameters[4],mutate;
static u8 *lastMatrix;
s32 func_150229E4(u8 *actor) { return 1; }
s32 func_1506196C(u8 *actor,s32 view) {
    s32 value=alphaCalls++?secondAlpha:firstAlpha;
    if(mutate && alphaCalls==2) *(u8 **)(actor+0x1D4)=(u8 *)0x34000;
    return value;
}
void func_1502C6E8(s32 slot,s16 view,s32 mode) { updates++;D_800CC2D0[slot*0x32C+0x1C8]=3; }
s32 func_150849CC(u8 *actor,s32 *tier) { alternate++;*tier=4;return 1; }
void func_1502D54C(s32 slot,s32 *parameters) { parameters[0]=11;parameters[1]=22;parameters[2]=33; }
void func_1502D630(u8 *actor,s32 *parameters,s32 view) { shadeCalls++;parameters[3]=144; }
Gfx *func_1502CCFC(Gfx *commands,s32 slot,s32 view,u8 *matrix,s32 alpha,
        s32 *parameters,s32 mode,s32 extra) {
    s32 i;renderCalls++;lastSlot=slot;lastView=view;lastMode=mode;lastExtra=extra;
    lastMatrix=matrix;lastAlpha=alpha;
    for(i=0;i<4;i++) lastParameters[i]=parameters[i];
    if(mutate) { D_800BE9C0=255;D_800BE9C8[255]=output+2;D_800BEBA4=-1; }
    return commands+2;
}
''' + screen.SELECTED+'\n'
        self.run_host('''
static s32 alphas[]={(-2147483647-1),-1,0,1,254,255,256,2147483647};
s32 slot,view,mode,index,factor,expected,kind,enabled;u8 *actor;Gfx *result;
for(slot=0;slot<26;slot++) for(view=0;view<4;view++) for(mode=0;mode<7;mode++)
for(index=0;index<8;index++) for(factor=0;factor<256;factor++) {
    actor=D_800CC2D0+slot*0x32C;
    actor[0x74]=0;actor[0x127]=(u8)(factor&3);
    *(u8 **)(actor+0x1D4)=(u8 *)0x22000;
    kind=factor%3;
    *(u8 **)(actor+0x318)=kind?owner:NULL;
    *(s32 *)(owner+0x2C)=kind==1?0x100:7;
    enabled=factor&1;*(s16 *)(config+0x3E)=(s16)enabled;
    D_800C3638=0;D_800C3656=0;D_800DF7C4=(u8)factor;
    D_800BE9C0=0;D_800BE9C8[0]=output;D_800BEBA4=2;
    firstAlpha=255;secondAlpha=alphas[index];
    alphaCalls=updates=alternate=shadeCalls=renderCalls=0;mutate=0;
    result=func_1502C974(output,slot,view,mode,0x12345678);
    expected=secondAlpha;
    if(expected<255 && kind==1 && view!=actor[0x127]) expected=255;
    if(mode==4) expected=(s32)((u32)factor*(u32)expected)>>8;
    if(result!=output+2 || alphaCalls!=2 || renderCalls!=1 || lastAlpha!=expected) return 1;
    if(lastSlot!=slot || lastView!=view || lastMode!=mode || lastExtra!=0x12345678) return 2;
    if(lastMatrix!=(u8 *)(mode==4?0x23000:0x22000)) return 3;
    if(lastParameters[0]!=11 || lastParameters[1]!=22 || lastParameters[2]!=33 ||
        lastParameters[3]!=(enabled?144:255) || shadeCalls!=enabled) return 4;
    if(updates!=(mode!=3 && mode!=4 && mode!=5) || alternate!=(mode==3 || mode==4 || mode==5)) return 5;
}
for(slot=0;slot<26;slot++) for(view=0;view<4;view++) {
    actor=D_800CC2D0+slot*0x32C;actor[0x74]=0;*(u8 **)(actor+0x318)=NULL;
    *(u8 **)(actor+0x1D4)=(u8 *)0x22000;firstAlpha=255;secondAlpha=-1;alphaCalls=0;
    D_800BE9C0=0;D_800BE9C8[0]=output;D_800BEBA4=2;mutate=1;
    if(func_1502C974(output,slot,view,0,0)!=output || lastMatrix!=(u8 *)0x34000) return 6;
}
''')
        self.receipt('native',cases=26*4*7*8*256+26*4,actual_complete_native32_C=True,
            valid_slot_view_bounds=True,all_factor_bytes_and_alpha_boundaries=True,
            callbacks_bounded_models=True,post_callback_reload_and_rollback=True)

    def test_08_verified_public_fault_prefixes(self):
        prefixes=0
        for mode,first,second,enabled,owner in ((0,0,255,0,0),(0,255,-1,0,0),
                (4,255,-1,1,0),(3,255,254,1,0x100),(5,255,255,0,0),
                (6,255,256,1,7)):
            memory=fixture(first_gate=1,enabled=enabled,owner=owner)
            plan=Plan(first=first,second=second)
            full=PublicFaultOracle(self.retail,memory,mode=mode,plan=plan).run()
            for ordinal in range(full.public_accesses):
                models=[]
                for body in (self.retail,self.raw,self.layout):
                    model=PublicFaultOracle(body,memory,mode=mode,plan=plan)
                    model.public_fault=ordinal
                    with self.assertRaises(PublicFault): model.run()
                    models.append(model)
                # A fault has no valid return; compare only the public memory/events prefix.
                for model in models[1:]: self.assertEqual(projection(models[0])[1:],projection(model)[1:])
                for model in models: self.assertEqual(model.public_accesses,ordinal)
                prefixes+=1
        self.receipt('public-faults',verified_prefixes=prefixes,executions=prefixes*3,
            emitted_disjoint_public_order=True,private_fault_order_not_claimed=True)

    def test_09_independent_symbol_links(self):
        cases=0
        for delta in (0x48034,0x98004):
            symbols={name:value+delta for name,value in S.items()}
            script=self.out/('rebase-%X.ld'%delta)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%screen.ENTRY)
            elf=script.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),
                str(self.out/'selected.o')],check=True,capture_output=True)
            raw=list(struct.unpack_from('>%dI'%len(self.raw),sections(elf)['.text'][1]))
            with patch.dict(S,symbols,clear=True):
                for slot,view,mode,alpha in itertools.product((0,25),(0,0x12340002),(0,3,4,5),(-1,255)):
                    memory=fixture(slot,view,enabled=1)
                    plan=Plan(second=alpha)
                    returned,result,events=reference(memory,slot,view,mode,plan=plan)
                    model=DispatchOracle(raw,memory,slot,view,mode,plan=plan).run()
                    self.assertEqual(projection(model),(returned,
                        {a:v for a,v in result.items() if public(a)},events))
                    cases+=1
        self.receipt('rebases',cases=cases,independent_compiled_links=2,
            signed_LO16_carries=True,raw_semantics_not_byte_match=True)

    def test_10_measured_physical_gates_and_retail_coverage(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame']), (162,0x60))
        self.assertEqual((self.layout_meta['body_words'],self.layout_meta['frame']), (167,0x58))
        self.assertEqual(self.meta['diagnostics'],'')
        self.assertEqual(self.layout_meta['diagnostics'],'')
        self.assertEqual(self.meta['pool_bytes'],0)
        self.assertEqual(self.layout_meta['pool_bytes'],0)
        missing=[i for i in range(176) if screen.ENTRY+i*4 not in self.coverage]
        self.receipt('physical-gates',retail_words=176,retail_frame=0x58,
            baseline_words=162,baseline_frame=0x60,volatile_actor_words=167,volatile_actor_frame=0x58,
            retail_words_reached=176-len(missing),unreached=missing,
            private_homes_and_full_extent_still_unqualified=True,not_installed=True)


if __name__=='__main__':
    unittest.main()
