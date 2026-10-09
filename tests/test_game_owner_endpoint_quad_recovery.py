"""Bounded endpoint quad recovery, partial vertex writes and retained helper lifetimes."""
import hashlib
import itertools
import json
import math
import struct
import subprocess
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from tools.check_game_data_layout import audit_layout
from tools.experiments import game_owner_endpoint_quad_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_context_classifier_candidates import compile_owner
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_area_sampler_recovery import AreaOracle
from tools.tests.test_game_camera_ribbon_renderer_recovery import CameraRibbonOracle, trunc
from tools.tests.test_game_record_ring_renderer_recovery import narrow, external, writes, rounded, NATIVE_TYPES
from tools.tests import test_game_random_curve_record as native
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_queued_segment_writer import STACK

ACTOR, ENDPOINT, ALTERNATE = 0x20000, 0x22000, 0x24000
MATRICES, OTHER_MATRIX, VIEWS, OTHER_VIEWS = 0x28000, 0x2D000, 0x40000, 0x50000
VERTICES, OUTPUT = 0x60000, 0x70000
COUNTS = dict(func_151D5D60=5, func_15143134=3, func_15142B7C=3,
    func_15142E24=11, func_15142C10=6, func_15142CF0=8,
    func_1513F4E4=3, func_15142FBC=4)


def fixture(invalid=0, resource=True, alias=False, pattern=0, view=0, joint=0, vertex_alias=False):
    memory = {STACK+i: (i*13+7)&255 for i in range(-0x600, 0x140)}
    for base, size in ((ACTOR,0x240),(ENDPOINT,0x240),(ALTERNATE,0x240),
            (VERTICES,96),(OUTPUT,96),(MATRICES,0x4040),(OTHER_MATRIX,0x4040)):
        memory.update({base+i:(i*17+0xA5)&255 for i in range(-16,size)})
    endpoint = ACTOR if alias else ENDPOINT
    for base in (endpoint,ALTERNATE):
        put(memory,base,0 if invalid==1 and base==endpoint else 1)
        put(memory,base+0x3B,173,1)
        put(memory,base+0x1D4,MATRICES if resource or base==ALTERNATE else 0)
    put(memory,ACTOR+0x28,endpoint)
    put(memory,ACTOR+0x2C,172 if invalid==2 else 173,1)
    put(memory,ACTOR+0x2D,joint,1)
    points=(((2.25,-3.5,7.75),(19.5,5.25,-11.75)),
        ((0.,0.,0.),(0.,0.,0.)), ((0.,0.,0.),(2.,0.,0.)),
        ((-100.25,99.75,0.125),(100.25,-99.75,-0.125)))[pattern]
    for offset,point in ((0x30,points[0]),(0x3C,points[1])):
        for axis,value in enumerate(point):put(memory,ACTOR+offset+axis*4,bits(value))
    put(memory,ACTOR+0x2C,read(memory,endpoint+0x3B,1)^(1 if invalid==2 else 0),1)
    put(memory,ACTOR+0x48,bits(-5.0 if pattern==3 else 5.0))
    for base in (MATRICES,OTHER_MATRIX):
        for index in (0,joint,255):
            for axis,value in enumerate((2.75,-1.25,0.5) if pattern!=2 else (0.,0.,0.)):
                put(memory,base+index*64+axis*4,bits(value+(10. if base==OTHER_MATRIX else 0.)))
    signed=narrow(view,16)
    for base in (VIEWS,OTHER_VIEWS):
        origin=base+signed*0x9A0+0x2F8
        for axis,value in enumerate((0.,0.,0.) if pattern==2 else (7.25,-8.5,9.75)):
            put(memory,(origin+axis*4)&0xFFFFFFFF,bits(value+(10. if base==OTHER_VIEWS else 0.)))
    put(memory,screen.SYMBOLS['D_800DBFF0'],VIEWS)
    put(memory,screen.SYMBOLS['D_800D2C9C'],0x12340000)
    for index,value in ((10,0x87654321),(11,0x10203040)):
        put(memory,screen.SYMBOLS['D_800A4AC8']+index*4,value)
    return memory, ACTOR+0x30 if vertex_alias else VERTICES


def changes(name, ordinal, mode):
    if mode==1 and name=='func_151D5D60':
        return [(ACTOR+0x28,ALTERNATE,4),(ACTOR+0x2D,255,1)]
    if mode==2 and name=='func_15143134' and ordinal==0:
        return [(ACTOR+0x3C,bits(25.5),4),(ACTOR+0x2D,255,1),
            (ENDPOINT+0x1D4,OTHER_MATRIX,4),(ACTOR+0x1D4,OTHER_MATRIX,4)]
    if mode==3 and name=='func_15143134' and ordinal==1:
        return [(screen.SYMBOLS['D_800DBFF0'],OTHER_VIEWS,4)]
    if mode==4 and name=='func_15142B7C':
        return [(screen.SYMBOLS['D_800DBFF0'],OTHER_VIEWS,4)]
    if mode==5 and name=='func_1513F4E4':
        return [(screen.SYMBOLS['D_800D2C9C'],0xFF001100,4),
            (screen.SYMBOLS['D_800A4AC8']+44,0x66778899,4),
            (ACTOR+0x48,bits(-7.),4),(ACTOR+0x2C,0,1)]
    return []


def transform(memory, source, matrix):
    return [rounded(floating(read(memory,source+i*4))+floating(read(memory,matrix+i*4))) for i in range(3)]


class QuadOracle(CameraRibbonOracle):
    def __init__(self,words,memory,view=0,success=True,mode=0,phase=0,vertex=VERTICES,
            symbols=None,entry=screen.ENTRY,connected=None):
        AreaOracle.__init__(self,words,memory,(OUTPUT,ACTOR,view),phase=phase,entry=entry,connected=connected)
        self.success,self.mode,self.vertex=success,mode,vertex
        self.symbols=symbols or screen.SYMBOLS
        self.targets={self.symbols[n]:n for n in COUNTS}
        self.arguments_by_call=[];self.transforms=0

    def get(self,address,size):
        if any((address+i)&0xFFFFFFFF not in self.memory for i in range(size)):
            raise KeyError(('read',address,size))
        return super().get(address,size)

    def record_call(self,target):
        if target==screen.ENTRY:
            self.forwarded=self.arguments(3);return
        name=self.targets[target];args=list(self.arguments(COUNTS[name]))
        self.arguments_by_call.append((name,tuple(args)))
        if name=='func_151D5D60':args[3]='cursor'
        elif name=='func_15143134':args[1]='point'+str(self.transforms)
        elif name in ('func_15142E24','func_15142C10','func_15142CF0','func_1513F4E4','func_15142FBC'):
            index=9 if name=='func_15142E24' else len(args)-1
            sync=args[index];assert self.get(sync,1)==(1 if name=='func_15142E24' else 0)
            args[index]='sync'
        self.calls.append((name,tuple(args)))

    def hook(self,target):
        name,args=self.arguments_by_call[-1];result=0
        if name=='func_151D5D60':
            self.put(args[3],self.vertex if self.success else 0,4)
        elif name=='func_15143134':
            for i,value in enumerate(transform(self.memory,args[0],args[2])):
                self.put(args[1]+i*4,bits(value),4)
        else:
            result=args[0]+8
            if name!='func_15142B7C':
                self.put(args[9] if name=='func_15142E24' else args[-1],0,1)
        for address,value,width in changes(name,self.transforms,self.mode):self.put(address,value,width)
        if name=='func_15143134':self.transforms+=1
        for offset in range(0,44,4):self.put(self.r[29]+offset,0xCD000000+offset,4)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=result

    def put(self,address,value,size):
        if self.recording and any((address+i)&0xFFFFFFFF not in self.memory for i in range(size)):
            raise KeyError(('write',address,size))
        return super().put(address,value,size)


class QuadReference:
    def __init__(self,memory,view=0,success=True,mode=0,vertex=VERTICES,symbols=None):
        self.memory=dict(memory);self.view=narrow(view,16)
        self.success,self.mode,self.vertex=success,mode,vertex
        self.symbols=symbols or screen.SYMBOLS
        self.calls=[];self.events=[];self.result=OUTPUT;self.transforms=0

    def get(self,address,size=4):return read(self.memory,address&0xFFFFFFFF,size)
    def store(self,address,value,size=4):
        address&=0xFFFFFFFF
        if any((address+i)&0xFFFFFFFF not in self.memory for i in range(size)):
            raise KeyError(('write',address,size))
        put(self.memory,address,value,size)
        self.events.append(('W',address,size,value&((1<<(8*size))-1)))

    def call(self,name,*args):
        self.calls.append((name,tuple(a&0xFFFFFFFF if isinstance(a,int) else a for a in args)))
        for address,value,width in changes(name,self.transforms,self.mode):self.store(address,value,width)
        if name=='func_15143134':self.transforms+=1
        if name not in ('func_151D5D60','func_15143134'):self.result+=8

    def transformed(self,source,matrix):
        self.calls.append(('func_15143134',(source,'point'+str(self.transforms),matrix)))
        value=transform(self.memory,source,matrix)
        for address,word,width in changes('func_15143134',self.transforms,self.mode):
            self.store(address,word,width)
        self.transforms+=1
        return value

    def run(self):
        endpoint=self.get(ACTOR+0x28)
        invalid=self.get(endpoint)==0 or self.get(ACTOR+0x2C,1)!=self.get(self.get(ACTOR+0x28)+0x3B,1)
        if invalid:
            self.store(ACTOR+0xE,-1,2);return self
        if self.get(self.get(ACTOR+0x28)+0x1D4)==0:return self
        self.call('func_151D5D60',ACTOR+0x14,self.view,64,'cursor',0)
        if not self.success:return self
        matrix=self.get(self.get(ACTOR+0x28)+0x1D4)+(self.get(ACTOR+0x2D,1)<<6)
        first=self.transformed(ACTOR+0x30,matrix)
        second=self.transformed(ACTOR+0x3C,matrix)
        origin=self.get(self.symbols['D_800DBFF0'])+self.view*0x9A0+0x2F8
        self.call('func_15142B7C',self.result,0x200005,0x60600)
        self.call('func_15142E24',self.result,self.symbols['D_80090DE8'],0,0,0,0,54,0,0,'sync',3)
        self.call('func_15142C10',self.result,255,255,255,255,'sync')
        self.call('func_15142CF0',self.result,0,0,255,255,255,255,'sync')
        self.call('func_1513F4E4',self.result,0x2B,'sync')
        self.call('func_15142FBC',self.result,self.get(self.symbols['D_800D2C9C'])|0x80000|0x2CA0,
            self.get(self.symbols['D_800A4AC8']+44)|self.get(self.symbols['D_800A4AC8']+40),'sync')
        delta=[rounded(b-a) for a,b in zip(first,second)]
        ray=[rounded(rounded(rounded(d*0.5)+a)-floating(self.get(origin+i*4))) for i,(d,a) in enumerate(zip(delta,first))]
        normal=[rounded(rounded(delta[1]*ray[2])-rounded(ray[1]*delta[2])),
            rounded(rounded(delta[2]*ray[0])-rounded(ray[2]*delta[0])),
            rounded(rounded(delta[0]*ray[1])-rounded(ray[0]*delta[1]))]
        squared=[rounded(v*v) for v in normal]
        length2=rounded(rounded(squared[0]+squared[1])+squared[2])
        if length2==0:offset=[0.,0.,0.]
        else:
            scale=rounded(floating(self.get(ACTOR+0x48))/rounded(math.sqrt(length2)))
            offset=[rounded(v*scale) for v in normal]
        cursor=self.vertex
        for point,sign,s,t in ((second,1,0,0),(second,-1,0x3C0,0),
                (first,-1,0x3C0,0x3C0),(first,1,0,0x3C0)):
            for axis in range(3):
                value=rounded(point[axis]+offset[axis]) if sign==1 else rounded(point[axis]-offset[axis])
                self.store(cursor+axis*2,trunc(value),2)
            self.store(cursor+8,s,2);self.store(cursor+10,t,2);cursor+=16
        for word,value in ((0x01004008,self.vertex),(0x05000204,0),(0x05000406,0)):
            self.store(self.result,word);self.store(self.result+4,value);self.result+=8
        return self


class GameOwnerEndpointQuadRecoveryTests(unittest.TestCase):
    run_host=native.GameRandomCurveRecordTests.run_host
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-owner-endpoint-quad-test';cls.out.mkdir(exist_ok=True)
        cls.meta,cls.words=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.rom=(cls.root/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>340I',cls.rom,screen.ROM))
        cls.before={p:hashlib.sha256((cls.root/p).read_bytes()).hexdigest()
            for p in (screen.SOURCE,'conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/progress.csv')}
        directory=tempfile.TemporaryDirectory();cls.addClassCleanup(directory.cleanup)
        cls.path=Path(directory.name)

    def receipt(self,name,data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,memory,view=0,success=True,mode=0,phase=0,vertex=VERTICES,bodies=None,symbols=None,entry=screen.ENTRY):
        ref=QuadReference(memory,view,success,mode,vertex,symbols).run();models=[]
        for words in bodies or (self.retail,self.words):
            model=QuadOracle(words,memory,view,success,mode,phase,vertex,symbols,entry).run()
            self.assertEqual(model.r[2],ref.result)
            self.assertEqual(model.calls,ref.calls)
            self.assertEqual(external(model.memory),external(ref.memory))
            self.assertEqual(writes(model),ref.events)
            models.append(model)
        return ref,models

    def test_01_complete_profiles_and_reject_installation(self):
        rows=[]
        for name,body in screen.candidates():
            for profile in screen.compiler.PROFILES if name=='selected' else ('o2g3',):
                meta,words=screen.compile_candidate(self.root,self.out,name+'-'+profile,body,profile)
                self.assertNotEqual(words,self.retail)
                self.assertEqual(meta['diagnostics'],'');self.assertEqual(meta['pool_bytes'],0)
                rows.append(meta)
        self.assertEqual(tuple(self.meta[k] for k in ('body_words','frame','differences')),(340,184,140))
        self.assertIn(screen.ORIGINAL,(self.root/screen.SOURCE).read_text())
        self.receipt('shape',dict(rows=rows,production_placeholder_unchanged=True,no_installation_authorized=True))

    def test_02_guest_lazy_exits_geometry_aliases_and_writes(self):
        count=0;coverage=[set(),set()]
        for invalid,resource,success,alias,pattern,phase in itertools.product(range(3),(False,True),(False,True),(False,True),range(4),(0,8)):
            memory,vertex=fixture(invalid,resource,alias,pattern)
            _,models=self.compare(memory,success=success,phase=phase,vertex=vertex)
            for c,m in zip(coverage,models):c.update(m.visits)
            count+=1
        for view,joint,mode,phase,vertex_alias in itertools.product((0xFFFF,0x8000,0x7FFF,0x12340002),(0,255),range(6),(0,8),(False,True)):
            memory,vertex=fixture(view=view,joint=joint,vertex_alias=vertex_alias)
            self.compare(memory,view=view,mode=mode,phase=phase,vertex=vertex);count+=1
        missing=set(range(screen.ENTRY,screen.ENTRY+1360,4))-coverage[0]
        self.assertEqual(missing,{0x151B2A14})
        # Failure jumps to the epilogue; success likely-branches over this duplicate load.
        self.assertEqual(self.retail[0x90//4],0x57000004)
        self.assertEqual(self.retail[0x98//4],0x10000128)
        self.receipt('guest',dict(cases=count,executions=count*2,retail_words_reached=339,
            unreachable_duplicate_load='0x151B2A14',unreachable_predecessors_verified=True,
            public_memory_and_write_order_equal=True,partial_vertex_holes_preserved=True,
            saved_register_lifetimes=True,helpers_bounded=True,no_full_access_trace_or_FCSR_claim=True))

    def test_03_compiled_effective_negatives(self):
        variants={
            'wrong-triangle':screen.SELECTED.replace('0, 2, 3, 0','1, 3, 2, 0'),
            'zero-vertex-holes':screen.SELECTED.replace('cursor++;','cursor->v.flag = 0; cursor++;'),
            'wrong-UV':screen.SELECTED.replace('0x3C0','0x4000'),
            'wrong-width':screen.SELECTED.replace('*(f32 *)(pair + 0x20)','1.0f'),
            'reloaded-matrix':screen.SELECTED.replace('func_15143134(pair + 0x14, &second, matrix);',
                'func_15143134(pair + 0x14, &second, *(u8 **)(*(u8 **)pair + 0x1D4) + (pair[5] << 6));'),
            'late-origin':screen.SELECTED.replace('        sync = 1;',
                '        sync = 1;').replace(screen.GEOMETRY,
                '        origin = (OwnerQuadPosition2974 *)(D_800DBFF0 + view * 0x9A0 + 0x2F8);\n'+screen.GEOMETRY),
        }
        rows=[]
        for name,body in variants.items():
            meta,words=screen.compile_candidate(self.root,self.out,name,body)
            mode=2 if name=='reloaded-matrix' else 4 if name=='late-origin' else 0
            memory,vertex=fixture();ref=QuadReference(memory,mode=mode).run()
            model=QuadOracle(words,memory,mode=mode).run()
            self.assertFalse(model.calls==ref.calls and external(model.memory)==external(ref.memory))
            rows.append(dict(name=name,completed=True,public_output_or_call_mismatch=True,meta=meta))
        self.receipt('negatives',rows)

    def test_04_actual_owner_neighbors_and_scratch_padder(self):
        before=(self.root/screen.SOURCE).read_text()
        after=before.replace('/* Non-matching placeholders',screen.TYPES+screen.DECLARATIONS+
            '\n/* Non-matching placeholders',1).replace(screen.ORIGINAL,screen.SELECTED)
        objects=[];warnings=[]
        for name,body in (('owner-before',before),('owner-after',after)):
            obj,diagnostics=compile_owner(self.root,self.out,body,name)
            subprocess.run(['python3',str(self.root/'tools/asm-processor/asm_processor.py'),'-O2','-g3',
                str((self.out/(name+'.c')).relative_to(self.root/'conker')),'--post-process',str(obj.relative_to(self.root/'conker')),
                '--assembler','mips-linux-gnu-as -EB -march=vr4300','--asm-prelude','include/asm_processor_prelude.inc'],
                cwd=self.root/'conker',check=True,capture_output=True)
            objects.append(obj);warnings.append(diagnostics)
        self.assertEqual(warnings[0],warnings[1]);self.assertEqual(len(warnings[0]),4)
        old,of,orels=parse_object(objects[0]);new,nf,nrels=parse_object(objects[1])
        self.assertEqual(of.keys(),nf.keys())
        for name,f in nf.items():
            if name==screen.FUNCTION:continue
            prior=of[name]
            self.assertEqual((f['size'],new[f['value']:f['value']+f['size']]),
                (prior['size'],old[prior['value']:prior['value']+prior['size']]),name)
            self.assertEqual({o-f['value']:r for o,r in nrels.items() if f['value']<=o<f['value']+f['size']},
                {o-prior['value']:r for o,r in orels.items() if prior['value']<=o<prior['value']+prior['size']},name)
        self.assertEqual(normalized_pools(objects[0]),normalized_pools(objects[1]))
        assembly=emit_padded_assembly(objects[1],self.root/'conker/asm/1DF510.s',
            word_patches_path=self.root/'conker/retail_word_patches.us.csv',filename='generated_1DF510')
        source=self.out/'padded.s';source.write_text(assembly)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(self.out/'padded.o'),str(source)],check=True,capture_output=True)
        self.receipt('owner',dict(neighbors=17,existing_warnings=4,new_warnings=0,
            pools_and_relative_relocations_preserved=True,actual_padder_accepts_scratch_only=True))

    def test_05_production_unchanged_protected_data_and_registered_pointer(self):
        self.assertIn(screen.ORIGINAL,(self.root/screen.SOURCE).read_text())
        after={p:hashlib.sha256((self.root/p).read_bytes()).hexdigest() for p in self.before}
        self.assertEqual(after,self.before)
        self.assertEqual(struct.unpack_from('>I',self.rom,0x22F130)[0],screen.ENTRY)
        address,data=sections(self.root/'conker/build/conker.us.elf')['.game_data']
        self.assertEqual(struct.unpack_from('>I',data,0x8008A670-address)[0],screen.ENTRY)
        audit=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertTrue(audit['exact'],audit)
        self.receipt('unchanged',dict(hashes=after,protected_data=audit,
            registered_retail_and_installed_pointer='0x8008A670',production_C_not_recovered=True))


    def test_06_native32_actual_C_geometry_ABI_holes_and_aliases(self):
        self.fixture=NATIVE_TYPES+screen.TYPES+screen.DECLARATIONS+NATIVE_FIXTURE+'\n'+screen.SELECTED+'\n'
        self.run_host('int invalid,res,ok,alias,pat,mode,view,joint,va,result;\n'
            'for(invalid=0;invalid<3;invalid++)for(res=0;res<2;res++)for(ok=0;ok<2;ok++)'
            'for(alias=0;alias<2;alias++)for(pat=0;pat<4;pat++)for(mode=0;mode<6;mode++)'
            'for(view=-2;view<=2;view++)for(joint=0;joint<2;joint++)for(va=0;va<2;va++)'
            '{result=one(invalid,res,ok,alias,pat,mode,view,joint?255:0,va);if(result)return result;}')
        self.receipt('native',dict(cases=11520,pointer_bits=32,actual_body=True,
            defined_fields_and_partial_vertex_holes=True,full_view_boundaries_guest_only=True,
            finite_binary32_geometry=True,no_FCSR_or_hardware_claim=True))

    def test_07_independent_original_candidate_symbol_rebases(self):
        owner=(self.root/'conker/asm/1DF510.s').read_text()
        begin='glabel '+screen.FUNCTION;end='endlabel '+screen.FUNCTION
        self.assertEqual(owner.count(begin),1);self.assertEqual(owner.count(end),1)
        original=begin+owner.split(begin,1)[1].split(end,1)[0]+end+'\n'
        source=self.out/'original.s';obj=self.out/'original.o'
        source.write_text('.text\n.include "conker/include/asm_processor_prelude.inc"\n'+original)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(source)],
            cwd=self.root,check=True,capture_output=True)
        uses=lambda path:Counter(use for group in parse_object(path)[2].values() for use in group)
        self.assertEqual(uses(obj),uses(self.out/'selected.o'))
        count=0
        for index,entry in enumerate((screen.ENTRY,0x10008000,0x80007FFC,0x8FFF8000)):
            symbols=screen.SYMBOLS if index==0 else {name:(entry&0xF0000000)+0x108008+i*0x100
                for i,name in enumerate(screen.SYMBOLS)}
            script=self.out/('rebase-%d.ld'%index)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            bodies=[]
            for name,object_path in (('original',obj),('candidate',self.out/'selected.o')):
                elf=self.out/('rebase-%d-%s.elf'%(index,name))
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(object_path)],
                    check=True,capture_output=True)
                bodies.append(list(struct.unpack_from('>340I',sections(elf)['.text'][1])))
            if index==0:self.assertEqual(bodies[0],self.retail)
            for invalid,pattern,phase in itertools.product(range(3),range(4),(0,8)):
                memory,vertex=fixture(invalid=invalid,pattern=pattern)
                for name,size in (('D_800DBFF0',4),('D_800D2C9C',4),('D_800A4AC8',48)):
                    old=screen.SYMBOLS[name];new=symbols[name]
                    for i in range(size):
                        if old+i in memory:memory[new+i]=memory[old+i]
                self.compare(memory,phase=phase,vertex=vertex,bodies=bodies,symbols=symbols,entry=entry);count+=1
        self.receipt('rebases',dict(symbol_sets=4,independent_links=8,cases=count,executions=count*2,
            relocation_uses=sum(uses(obj).values()),no_byte_matching_claim=True))

    def test_08_actual_registered_graphics_dispatcher(self):
        entry=0x15149490;rom=0x176940
        dispatcher=list(struct.unpack_from('>20I',self.rom,rom))
        start,data=sections(self.root/'conker/build/conker.us.elf')['.game']
        self.assertEqual(list(struct.unpack_from('>20I',data,entry-start)),dispatcher)
        count=0
        for selector,view,success,alias,phase in itertools.product((0,255),(0,0xFFFF,0x8000),(False,True),(False,True),(0,8)):
            memory,vertex=fixture(alias=alias,view=view)
            put(memory,ACTOR+0x12,selector,1);put(memory,0x8008A670,screen.ENTRY)
            ref=QuadReference(memory,view,success,vertex=vertex).run() if selector==0 else None
            for body in (self.retail,self.words):
                connected={screen.ENTRY+i*4:word for i,word in enumerate(body)}
                model=QuadOracle(dispatcher,memory,view,success,phase=phase,vertex=vertex,
                    entry=entry,connected=connected).run()
                if ref is None:
                    self.assertEqual(model.r[2],OUTPUT);self.assertEqual(model.calls,[])
                    self.assertEqual(external(model.memory),external(memory))
                else:
                    self.assertEqual(model.forwarded,(OUTPUT,ACTOR,narrow(view,16)&0xFFFFFFFF))
                    self.assertEqual(model.r[2],ref.result);self.assertEqual(model.calls,ref.calls)
                    self.assertEqual(external(model.memory),external(ref.memory))
                    self.assertEqual(writes(model),ref.events)
            count+=1
        self.receipt('dispatcher',dict(cases=count,executions=count*2,actual_words=20,
            installed_caller_exact=True,table='0x8008A670',selector=0,
            signed_view_and_return_forwarding=True,other_selectors_not_qualified=True))

    def test_09_missing_byte_public_fault_prefixes_and_lazy_reads(self):
        count=0
        for alias in (False,True):
            memory,vertex=fixture(alias=alias)
            endpoint=read(memory,ACTOR+0x28)
            for address in (ACTOR+0x28,endpoint,endpoint+0x3B,endpoint+0x1D4,
                    ACTOR+0x30,screen.SYMBOLS['D_800DBFF0'],VIEWS+0x2F8,
                    ACTOR+0x48,VERTICES,OUTPUT+48):
                broken=dict(memory);del broken[address]
                ref=QuadReference(broken)
                with self.assertRaises(KeyError):ref.run()
                for body in (self.retail,self.words):
                    model=QuadOracle(body,broken)
                    with self.assertRaises(KeyError):model.run()
                    self.assertEqual(model.calls,ref.calls)
                    self.assertEqual(external(model.memory),external(ref.memory))
                    self.assertEqual(writes(model),ref.events)
                count+=1
        for invalid,resource,success in ((1,True,True),(2,True,True),(0,False,True),(0,True,False)):
            memory,vertex=fixture(invalid=invalid,resource=resource)
            # Every early exit must avoid graphics globals and vertex memory.
            for address in (screen.SYMBOLS['D_800DBFF0'],screen.SYMBOLS['D_800D2C9C'],VERTICES):
                del memory[address]
            self.compare(memory,success=success,vertex=vertex)
        self.receipt('faults',dict(cases=count,executions=count*2,lazy_exit_cases=4,
            public_memory_write_call_prefix_equal=True,no_private_access_FCSR_or_hardware_fault_claim=True))


NATIVE_FIXTURE = r'''
float sqrtf(float v){float r;__asm__("sqrtss %1,%0":"=x"(r):"x"(v));return r;}
u8 *D_800DBFF0;u8 D_80090DE8[16];u32 D_800D2C9C,D_800A4AC8[12];
Gfx *func_151B2974(Gfx *,u8 *,s16);
static union {u32 align;u8 b[576];} actor,endpoint,alternate;
static f32 matrices[256][16],otherMatrices[256][16];
static union {u32 align;u8 b[5*0x9A0+0x310];} views,otherViews;
static Vtx vertices[6],wanted[4];static Gfx commands[12];
static u8 vertexBefore[64];
static int error,used,transforms,mode,success,vertexAlias;static s16 expectedView;
static f32 first[3],second[3],widthWanted;static u8 *matrixWanted;
static f32 add(f32 a,f32 b){volatile f32 v=a+b;return v;}
static f32 sub(f32 a,f32 b){volatile f32 v=a-b;return v;}
static f32 mul(f32 a,f32 b){volatile f32 v=a*b;return v;}
static f32 divide(f32 a,f32 b){volatile f32 v=a/b;return v;}
static void fill(u8 *p,int n,int v){int i;for(i=0;i<n;i++)p[i]=v;}
static void mutation(int ordinal){
 if(mode==1 && ordinal==0){*(u8 **)(actor.b+0x28)=alternate.b;actor.b[0x2D]=255;}
 if(mode==2 && ordinal==1){*(f32 *)(actor.b+0x3C)=25.5f;actor.b[0x2D]=255;
  *(u8 **)(endpoint.b+0x1D4)=(u8 *)otherMatrices;
  *(u8 **)(actor.b+0x1D4)=(u8 *)otherMatrices;}
 if(mode==3 && ordinal==2)D_800DBFF0=otherViews.b+2*0x9A0;
 if(mode==4 && ordinal==3)D_800DBFF0=otherViews.b+2*0x9A0;
 if(mode==5 && ordinal==7){D_800D2C9C=0xFF001100;D_800A4AC8[11]=0x66778899;
  *(f32 *)(actor.b+0x48)=-7.0f;widthWanted=-7.0f;actor.b[0x2C]=0;}
}
void func_151D5D60(void *p,s16 v,s32 n,Vtx **out,u8 *fresh){
 if(used++ || p!=actor.b+0x14 || v!=expectedView || n!=64 || fresh)error=1;
 *out=success?(vertexAlias?(Vtx *)(actor.b+0x30):vertices):NULL;mutation(0);
 if(success)matrixWanted=*(u8 **)(*(u8 **)(actor.b+0x28)+0x1D4)+(actor.b[0x2D]<<6);
}
void func_15143134(void *p,void *out,u8 *matrix){
 int i;f32 *source=p,*dest=out,*want=transforms?second:first;
 if(used!=(transforms?2:1) || p!=actor.b+(transforms?0x3C:0x30) || matrix!=matrixWanted)error=2;
 for(i=0;i<3;i++)want[i]=dest[i]=add(source[i],((f32 *)matrix)[i]);
 mutation(used++);transforms++;
}
static Gfx *step(Gfx *g,int id,u8 *sync){
 if(used!=id || g!=commands+id-3)error=3;
 if(sync){if(*sync!=(id==4?1:0))error=4;*sync=0;}
 mutation(used++);return g+1;
}
Gfx *func_15142B7C(Gfx *g,u32 a,u32 b){
 if(a!=0x200005 || b!=0x60600){error=5;}return step(g,3,NULL);
}
Gfx *func_15142E24(Gfx *g,void *tex,s32 a,s32 b,s32 c,s32 d,s32 n,u8 f,u8 *zero,u8 *sync,s32 k){
 if(tex!=D_80090DE8 || a || b || c || d || n!=54 || f || zero || k!=3)error=6;
 return step(g,4,sync);
}
Gfx *func_15142C10(Gfx *g,s32 r,s32 gg,s32 b,s32 a,u8 *sync){
 if(r!=255 || gg!=255 || b!=255 || a!=255){error=7;}return step(g,5,sync);
}
Gfx *func_15142CF0(Gfx *g,s32 a,s32 b,s32 r,s32 gg,s32 bb,s32 alpha,u8 *sync){
 if(a || b || r!=255 || gg!=255 || bb!=255 || alpha!=255)error=8;
 return step(g,6,sync);
}
Gfx *func_1513F4E4(Gfx *g,u8 k,u8 *sync){
 if(k!=0x2B){error=9;}return step(g,7,sync);
}
Gfx *func_15142FBC(Gfx *g,u32 a,u32 b,u8 *sync){
 int i;u8 *v=vertexAlias?actor.b+0x30:(u8 *)vertices;
 if(a!=(D_800D2C9C|0x80000|0x2CA0) || b!=(D_800A4AC8[11]|D_800A4AC8[10]))error=10;
 for(i=0;i<64;i++)vertexBefore[i]=v[i];
 return step(g,8,sync);
}
static void expected(Vtx *out){
 f32 d[3],ray[3],n[3],offset[3],squared,scale;int i,j;
 f32 *origin=(f32 *)((mode==3?otherViews.b:views.b)+(expectedView+2)*0x9A0+0x2F8);
 for(i=0;i<3;i++){d[i]=sub(second[i],first[i]);ray[i]=sub(add(mul(d[i],0.5f),first[i]),origin[i]);}
 n[0]=sub(mul(d[1],ray[2]),mul(ray[1],d[2]));
 n[1]=sub(mul(d[2],ray[0]),mul(ray[2],d[0]));
 n[2]=sub(mul(d[0],ray[1]),mul(ray[0],d[1]));
 squared=add(add(mul(n[0],n[0]),mul(n[1],n[1])),mul(n[2],n[2]));
 if(squared==0.0f)offset[0]=offset[1]=offset[2]=0.0f;
 else {scale=divide(widthWanted,sqrtf(squared));for(i=0;i<3;i++)offset[i]=mul(n[i],scale);}
 for(j=0;j<4;j++){
  f32 *point=j<2?second:first;
  for(i=0;i<3;i++)out[j].v.ob[i]=(s32)((j==0 || j==3)?add(point[i],offset[i]):sub(point[i],offset[i]));
  out[j].v.tc[0]=(j==1 || j==2)?0x3C0:0;out[j].v.tc[1]=j<2?0:0x3C0;
 }
}
static int one(int invalid,int resource,int ok,int alias,int pattern,int mutationMode,s16 view,int joint,int va){
 int i,j;u8 *e;Gfx *result;Vtx *v;
 const f32 points[4][2][3]={{{2.25f,-3.5f,7.75f},{19.5f,5.25f,-11.75f}},
  {{0,0,0},{0,0,0}},{{0,0,0},{2,0,0}},{{-100.25f,99.75f,.125f},{100.25f,-99.75f,-.125f}}};
 fill(actor.b,576,0xA5);fill(endpoint.b,576,0xA5);fill(alternate.b,576,0xA5);
 fill((u8 *)vertices,sizeof(vertices),0xA5);fill((u8 *)commands,sizeof(commands),0xA5);
 mode=mutationMode;success=ok;expectedView=view;vertexAlias=va;error=used=transforms=0;
 e=alias?actor.b:endpoint.b;*(s32 *)e=invalid==1?0:1;e[0x3B]=173;
 *(u8 **)(e+0x1D4)=resource?(u8 *)matrices:NULL;
 *(s32 *)alternate.b=1;*(u8 **)(alternate.b+0x1D4)=(u8 *)matrices;
 *(u8 **)(actor.b+0x28)=e;actor.b[0x2C]=invalid==2?172:173;actor.b[0x2D]=joint;
 for(i=0;i<3;i++){*(f32 *)(actor.b+0x30+i*4)=points[pattern][0][i];
  *(f32 *)(actor.b+0x3C+i*4)=points[pattern][1][i];}
 actor.b[0x2C]=e[0x3B]^(invalid==2?1:0);
 *(f32 *)(actor.b+0x48)=widthWanted=pattern==3?-5.0f:5.0f;
 for(j=0;j<256;j++)for(i=0;i<3;i++){
  f32 f=pattern==2?0.0f:(i==0?2.75f:i==1?-1.25f:.5f);
  matrices[j][i]=f;otherMatrices[j][i]=f+10.0f;
 }
 for(j=0;j<5;j++)for(i=0;i<3;i++){
  f32 f=pattern==2?0.0f:(i==0?7.25f:i==1?-8.5f:9.75f);
  *(f32 *)(views.b+j*0x9A0+0x2F8+i*4)=f;
  *(f32 *)(otherViews.b+j*0x9A0+0x2F8+i*4)=f+10.0f;
 }
 D_800DBFF0=views.b+2*0x9A0;D_800D2C9C=0x12340000;
 D_800A4AC8[10]=0x87654321;D_800A4AC8[11]=0x10203040;
 v=va?(Vtx *)(actor.b+0x30):vertices;
 result=func_151B2974(commands,actor.b,view);
 if(invalid || !resource || !ok){
  if(result!=commands || used!=(invalid || !resource?0:1))return 11;
  if(*(s16 *)(actor.b+0xE)!=(invalid?-1:(s16)0xA5A5))return 12;
 }else{
  if(result!=commands+9 || used!=9 || transforms!=2)return 13;
  /* The expected width is captured separately from aliased output memory. */
  for(i=0;i<64;i++)((u8 *)wanted)[i]=vertexBefore[i];
  expected(wanted);
  for(i=0;i<64;i++)if(((u8 *)v)[i]!=((u8 *)wanted)[i])return 14;
  if(commands[6].words.w0!=0x01004008 || commands[6].words.w1!=(u32)v ||
   commands[7].words.w0!=0x05000204 || commands[7].words.w1 ||
   commands[8].words.w0!=0x05000406 || commands[8].words.w1)return 15;
 }
 return error;
}
'''

if __name__=='__main__':
    unittest.main()
