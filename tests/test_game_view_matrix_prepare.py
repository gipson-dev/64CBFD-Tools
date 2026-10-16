"""Direct matrix preparation with real decoder/product helpers and caller-loop cuts."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_view_matrix_prepare as source
from tools.experiments import game_view_orthographic_setup as sdk_build
from tools.tests import game_view_matrix_pass_oracle as model
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.pad_generated_object import parse_object
from tools import pad_c_object
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections

OUTPUT, CALLER, JOIN, COUNT = 0x800D2CA8,0x15019268,0x1501929C,model.COUNT


def fixture(index,page,pattern,alias=0):
    memory = model.fixture(3,page if page in model.PAGES else 0,pattern)
    memory.update({OUTPUT+i:0xA5 for i in range(-32,288)})
    memory[model.PAGE] = page
    model.put(memory,model.TABLE+page*4,model.FIXED if page%2 == 0 else model.OTHER)
    pointer = model.VIEWS+index*0x180+page*64+0x100
    for i,word in enumerate(model.packed(pattern+index+page)):
        model.put(memory,pointer+i*4,word)
    if alias == 1:
        model.put(memory,model.TABLE+page*4,OUTPUT)
        for i,word in enumerate(model.packed(pattern+index)):
            model.put(memory,OUTPUT+index*64+i*4,word)
    elif alias == 2:
        model.put(memory,model.BASE,(OUTPUT+index*64-(index*0x180+page*64+0x100))&0xFFFFFFFF)
        for i,word in enumerate(model.packed(pattern+index+page)):
            model.put(memory,OUTPUT+index*64+i*4,word)
    return memory


def effect(memory,index,ordinal,mode,first,second):
    if ordinal == 1 and mode == 1:
        memory[model.PAGE] = 1 if memory[model.PAGE] == 0 else 0
        model.put(memory,model.BASE,model.ALTERNATE)
        model.put(memory,model.TABLE+memory[model.PAGE]*4,model.OTHER)
    elif ordinal == 2 and mode == 2:
        model.put(memory,first,model.bits(7.25))
        model.put(memory,OUTPUT+index*64+4,model.bits(9))
    elif ordinal == 2 and mode == 3:
        model.put(memory,second+20,model.bits(-6.5))
    elif ordinal == 1 and mode == 4:
        model.put(memory,COUNT,0xFFFFFFFF)
    else:
        return False
    return True


def reference(memory,index,mode=0,phase=0):
    memory,calls = dict(memory),[]
    first,second = model.machine.STACK+phase-0x40,model.machine.STACK+phase-0x80
    args = (first,model.read(memory,model.TABLE+memory[model.PAGE]*4)+index*64)
    calls.append((model.CONVERT,args))
    model.decode(memory,*args)
    effect(memory,index,1,mode,first,second)
    args = (second,model.read(memory,model.BASE)+index*0x180+memory[model.PAGE]*64+0x100)
    calls.append((model.CONVERT,args))
    model.decode(memory,*args)
    effect(memory,index,2,mode,first,second)
    args = (first,second,OUTPUT+index*64)
    calls.append((model.MULTIPLY,args))
    model.multiply(memory,*args)
    return memory,calls


def public(memory):
    return {a:b for a,b in memory.items() if not model.machine.STACK-0x800 <= a < model.machine.STACK+0x180}


class CallerJoin(Exception):
    pass


class CallerCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc == JOIN:
            self.owner.current_pc = pc
            raise CallerJoin
        return super().__getitem__(pc)


class PrepareOracle(model.MatrixPassOracle):
    def __init__(self,words,memory,index=0,mode=0,phase=0,fault=None,connected=None,entry=source.ENTRY):
        super().__init__(words,memory,mode=0,phase=phase,fault=fault,connected=connected,
            entry=entry,arguments=(index,))
        self.prepare_mode,self.index,self.first,self.second = mode,index,None,None
        self.actions = []
        if entry == CALLER:
            self.r[16] = self.before[16] = COUNT
            self.code = CallerCode(self.code,self)

    def record_call(self,target):
        if target == source.ENTRY:
            args = self.arguments(1)
            self.calls.append((target,args))
            self.events.append(('CALL',target,args))
            self.index,self.conversions = args[0],0
            return
        super().record_call(target)
        if target == model.CONVERT:
            if self.conversions%2:
                self.first = self.calls[-1][1][0]
            else:
                self.second = self.calls[-1][1][0]

    def execute(self,word):
        super().execute(word)
        if self.current_pc == model.CONVERT+44*4:
            if effect(self.memory,self.index,self.conversions,self.prepare_mode,self.first,self.second):
                self.actions.append((self.index,self.conversions,self.prepare_mode))

    def hook(self,target):
        raise AssertionError(('Opaque preparation helper is not accepted',hex(target)))


def state(m):
    return m.r,m.f,m.memory,m.events,m.calls,m.lo,m.condition,m.root_accesses,m.actions


def cases():
    yield from itertools.product(range(4),model.PAGES,range(4),range(5),range(3),(0,8))
    for page,phase in itertools.product(range(256),(0,8)):
        yield 0,page,page%4,0,page%3,phase


def native_program(header,sdk):
    literal = lambda values:'{'+','.join('0x%Xu'%v for v in values)+'}'
    packed = ','.join(literal(model.packed(p)) for p in range(12))
    converter = source.build.body(sdk,'guMtxL2F').replace('guMtxL2F(', 'actual_decoder(',1)
    return header+'''\nstatic const u32 packed[12][16]={'''+packed+'''};
static Mtx fixed[2][4],views[2][4][6];
Mtx *D_800DC2A0[256];u8 *D_800BE628;u8 D_800BE9C0;f32 D_800D2CA8[4][4][4];
static u32 indexValue,pageValue,modeValue,conversions,products,error;
static f32 *firstMatrix,*secondMatrix;
void func_15094EA0(s32 index);
static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 value(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
static void reference_decode(f32 out[4][4],Mtx *in){u32 i,a,b,x,y,*p=(u32*)in;
 for(i=0;i<8;i++){a=p[i];b=p[8+i];x=(a&0xFFFF0000u)|(b>>16);y=(a<<16)|(b&65535u);
 (&out[0][0])[i*2]=(f32)(s32)x/65536.0f;(&out[0][0])[i*2+1]=(f32)(s32)y/65536.0f;}}
static void product(f32 a[4][4],f32 b[4][4],f32 out[4][4]){u32 r,c,k;f32 v;
 for(r=0;r<4;r++)for(c=0;c<4;c++){v=a[r][0]*b[0][c];for(k=1;k<4;k++)v+=a[r][k]*b[k][c];out[r][c]=v;}}
'''+converter+'''
void guMtxL2F(f32 out[4][4],Mtx *in){Mtx *expected;
 if(error||conversions>=2){error=21;return;}
 if(!conversions){expected=&fixed[pageValue][indexValue];firstMatrix=&out[0][0];}
 else{expected=&views[modeValue==1][indexValue][(modeValue==1?1-pageValue:pageValue)+4];secondMatrix=&out[0][0];}
 if(in!=expected){error=21;return;}actual_decoder(out,in);conversions++;
 if(conversions==1&&modeValue==1){D_800BE9C0=(u8)(1-pageValue);D_800BE628=(u8*)views[1];D_800DC2A0[D_800BE9C0]=fixed[1];}
 if(conversions==2&&modeValue==2){firstMatrix[0]=7.25f;D_800D2CA8[indexValue][0][1]=9;}
 if(conversions==2&&modeValue==3)secondMatrix[5]=-6.5f;
}
void func_150A7A48(f32 left[4][4],f32 right[4][4],f32 out[4][4]){f32 cached[4][4],row[4],v;u32 r,c,k;
 if(error||conversions!=2||products||&left[0][0]!=firstMatrix||&right[0][0]!=secondMatrix||out!=D_800D2CA8[indexValue]){error=22;return;}
 for(r=0;r<4;r++)for(c=0;c<4;c++)cached[r][c]=right[r][c];
 for(r=0;r<4;r++){for(k=0;k<4;k++)row[k]=left[r][k];
  for(c=0;c<4;c++){v=row[0]*cached[0][c];for(k=1;k<4;k++)v+=row[k]*cached[k][c];out[r][c]=v;}}
 products++;
}
static int run(void){u32 p,i,page,mode,b,j,k,r,c;f32 a[4][4],q[4][4],expected[4][4];
 if(sizeof(void*)!=4||sizeof(Mtx)!=64||sizeof(ProjectedViewFrame95760)!=0x180)return 29;
 for(p=0;p<4;p++)for(i=0;i<4;i++)for(page=0;page<2;page++)for(mode=0;mode<4;mode++){
  for(b=0;b<2;b++)for(j=0;j<4;j++)for(k=0;k<16;k++)((u32*)&fixed[b][j])[k]=packed[p+j+b][k];
  for(b=0;b<2;b++)for(j=0;j<4;j++)for(k=0;k<6;k++)for(r=0;r<16;r++)((u32*)&views[b][j][k])[r]=packed[p+j+(k&1)+b*4][r];
  for(j=0;j<4;j++)for(r=0;r<4;r++)for(c=0;c<4;c++)D_800D2CA8[j][r][c]=value(0xA55A1234u);
  reference_decode(a,&fixed[page][i]);reference_decode(q,&views[mode==1][i][(mode==1?1-page:page)+4]);
  if(mode==2)a[0][0]=7.25f;if(mode==3)q[1][1]=-6.5f;product(a,q,expected);
  indexValue=i;pageValue=page;modeValue=mode;conversions=products=error=0;firstMatrix=secondMatrix=0;
  D_800BE9C0=(u8)page;D_800BE628=(u8*)views[0];D_800DC2A0[0]=fixed[0];D_800DC2A0[1]=fixed[1];
  func_15094EA0((s32)i);if(error)return (int)error;if(conversions!=2||products!=1)return 23;
  for(r=0;r<4;r++)for(c=0;c<4;c++)if(word(D_800D2CA8[i][r][c])!=word(expected[r][c]))return 24;
  for(j=0;j<4;j++)if(j!=i)for(r=0;r<4;r++)for(c=0;c<4;c++)if(word(D_800D2CA8[j][r][c])!=0xA55A1234u)return 25;
  if(D_800BE9C0!=(mode==1?1-page:page)||D_800BE628!=(u8*)views[mode==1])return 26;
 }return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class ViewMatrixPrepareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[2]
        cls.out = cls.root/source.BUILD
        cls.obj,cls.padded,cls.raw,_,cls.row = source.qualify(cls.root,cls.out)
        cls.rom = (cls.out/'before-retail_rom').read_bytes()
        cls.truth = list(struct.unpack_from('>40I',cls.rom,source.ROM))
        data,functions = source.build.link_owner(cls.root,cls.out,cls.padded,source.OWNER)
        cls.words = list(struct.unpack_from('>40I',data,functions[source.FUNCTION]['value']))
        sdk,cls.sdk_diagnostics = sdk_build.compile_sdk(cls.root,cls.out,(cls.out/'before-sdk').read_text(),source.PATHS['sdk'],'fresh-sdk')
        assembly = pad_c_object.emit_padded_assembly(sdk,cls.root/source.PATHS['layout'],'mtxutil2',word_patches_path=cls.out/'before-guards')
        sdk_obj = cls.assemble(assembly,'sdk-padded')
        sdk_data,sdk_functions = source.build.link_owner(cls.root,cls.out,sdk_obj,'mtxutil2')
        cls.converter = list(struct.unpack_from('>46I',sdk_data,sdk_functions['guMtxL2F']['value']))
        kernel,cls.kernel_diagnostics = source.build.compile_owner(cls.root,cls.out,
            (cls.out/'before-multiply_owner').read_text(),'fresh-product')
        kernel_text,kernel_functions,_ = parse_object(kernel)
        cls.multiply = list(struct.unpack_from('>78I',kernel_text,kernel_functions['func_150A7A48']['value']))
        cls.connected = {target+i*4:word for target,words in ((model.CONVERT,cls.converter),(model.MULTIPLY,cls.multiply))
            for i,word in enumerate(words)}

    @classmethod
    def assemble(cls,text,label):
        path = cls.out/(label+'.s')
        path.write_text('.include "'+str(cls.root/'conker/include/asm_processor_prelude.inc')+'"\n'+text)
        obj = path.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],capture_output=True,check=True)
        return obj

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_direct_words_homes_fresh_sdk_and_original_product(self):
        self.assertEqual((self.raw,self.words),(self.truth,self.truth))
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['new_guards']),(40,152,0,0))
        self.assertEqual(self.words[11],0x27A40058)
        self.assertEqual(self.words[27],0x27A40018)
        self.assertEqual(self.sdk_diagnostics,'uld:\nWarning: -Xfullwarn not supported.\n')
        self.assertEqual(self.kernel_diagnostics,'')
        self.assertEqual(self.converter,list(struct.unpack_from('>46I',self.rom,0x21D368)))
        self.assertEqual(self.multiply,list(struct.unpack_from('>78I',self.rom,0xD4EF8)))

    def test_02_all_frame_bytes_real_helpers_aliases_and_live_effects(self):
        count,visits,actions = 0,set(),0
        for index,page,pattern,mode,alias,phase in cases():
            memory = fixture(index,page,pattern,alias)
            expected,calls = reference(memory,index,mode,phase)
            models = [PrepareOracle(words,memory,index,mode,phase,connected=self.connected).run()
                for words in (self.truth,self.raw,self.words)]
            for m in models:
                self.assertEqual(public(m.memory),public(expected),(index,page,pattern,mode,alias,phase))
                self.assertEqual(m.calls,calls)
                self.assertEqual(m.root_accesses,10)
                self.assertEqual(len(m.actions),int(mode!=0))
                self.assertEqual(state(m),state(models[0]))
            visits.update(models[1].visits)
            actions += len(models[1].actions)
            count += 1
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+160,4)) <= visits)
        self.receipt('guest',cases=count,frame_bytes=256,complete_modeled_state_three_way=True,
            root_words_covered=40,real_sdk_slot_words=46,real_product_slot_words=78,fired_effects=actions,
            full_hardware_FCSR_or_gameplay_parity_not_claimed=True)

    def test_03_every_root_access_fault_prefix(self):
        count = 0
        for index,page,mode,alias,phase,cut in itertools.product((0,1,3),(0,255),range(5),range(3),(0,8),range(10)):
            memory = fixture(index,page,3,alias)
            models = [PrepareOracle(words,memory,index,mode,phase,cut,self.connected) for words in (self.truth,self.words)]
            for m in models:
                with self.assertRaises(faults.AccessBoundary):
                    m.run()
                self.assertEqual(m.root_accesses,cut)
            self.assertEqual(state(models[0]),state(models[1]))
            count += 1
        self.receipt('faults',cases=count,flat_guest_access_prefixes=True,portable_C_fault_or_hardware_claim=False)

    def test_04_retail_caller_view_loop_to_original_join_installed_caller_still_stubbed(self):
        before = (self.out/'before-elf').read_bytes()
        row = next(r for r in symbol_rows(before) if r[1] == 'func_15019130')
        self.assertEqual(row[2][1:3],(0x15019130,12))
        self.assertEqual(before[elf_slot_offset(before,CALLER,52):elf_slot_offset(before,CALLER,52)+52],b'\0'*52)
        caller = list(struct.unpack_from('>13I',self.rom,0x46718))
        count,invocations = 0,0
        for views,page,pattern,mode,phase in itertools.product((-1,0,1,3),(0,1,255),range(4),range(5),(0,8)):
            memory = fixture(0,page,pattern)
            model.put(memory,COUNT,views&0xFFFFFFFF)
            expected,calls,index = dict(memory),[],0
            while index <= model.signed(model.read(expected,COUNT)):
                calls.append((source.ENTRY,(index,)))
                expected,more = reference(expected,index,mode,phase)
                calls.extend(more)
                index = (index+1)&255
            models = []
            for target in (self.truth,self.words):
                connected = dict(self.connected)
                connected.update({source.ENTRY+i*4:w for i,w in enumerate(target)})
                m = PrepareOracle(caller,memory,mode=mode,phase=phase,connected=connected,entry=CALLER)
                with self.assertRaises(CallerJoin):
                    m.run()
                self.assertEqual(public(m.memory),public(expected))
                self.assertEqual(m.calls,calls)
                self.assertEqual(m.r[29],model.machine.STACK+phase)
                models.append(m)
            self.assertEqual(state(models[0]),state(models[1]))
            count += 1
            invocations += sum(t == source.ENTRY for t,_ in calls)
        self.receipt('caller',cases=count,invocations=invocations,original_words=13,join=hex(JOIN),
            installed_caller_still_12_byte_stub=True,whole_caller_or_gameplay_parity_not_claimed=True)

    def test_05_native32_actual_preparation_sdk_decoder_and_effective_controls(self):
        before = (self.out/'before-packet_owner').read_text()
        header = source.recovered_owner(before).split('/* Non-matching placeholders',1)[0]
        harness = self.out/'native-harness.c'
        harness.write_text(native_program(header,(self.out/'before-sdk').read_text()))
        body = source.SELECTED
        page = body.replace('D_800BE9C0','page').replace('    f32 model[4][4];',
            '    u8 page = D_800BE9C0;\n    f32 model[4][4];')
        base = body.replace('D_800BE628','base').replace('    f32 model[4][4];',
            '    u8 *base = D_800BE628;\n    f32 model[4][4];')
        controls = dict(cached_page=page,cached_base=base,
            reversed_product=body.replace('func_150A7A48(model, projection,','func_150A7A48(projection, model,'),
            wrong_fixed_slot=body.replace('+ 0x100','+ 0xC0'),wrong_output=body.replace('D_800D2CA8[index]','D_800D2CA8[0]'))
        exits = {}
        for label,opt,selected,valid in [('O2','-O2',body,True),('O0','-O0',body,True)]+[
                (label,'-O2',selected,False) for label,selected in controls.items()]:
            if not valid:
                self.assertNotEqual(selected,body)
            path = self.out/('native-body-'+label+'.c')
            path.write_text(header+selected)
            exe = self.out/('native-'+label)
            result = subprocess.run([*native_command(opt,valid),'-mstackrealign','-fno-strict-aliasing',str(path),str(harness),'-o',str(exe)],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            result = subprocess.run([str(exe)],capture_output=True,timeout=30)
            self.assertIn(result.returncode,(0,) if valid else (21,22,23,24,25,26),(label,result.stderr))
            exits[label] = result.returncode
        self.receipt('native',cases_per_selected=128,separate_units_native32_O2_O0_UBSan=True,
            actual_preparation_and_sdk_C=True,product_is_ordered_contract_fixture=True,exits=exits)

    def test_06_neighbors_all_screens_object_relocations_and_frozen_controls(self):
        obj,diagnostics = source.build.compile_owner(self.root,self.out,(self.out/'before-packet_owner').read_text(),'neighbor-before')
        self.assertFalse(diagnostics)
        before,after = parse_object(obj),parse_object(self.obj)
        self.assertEqual(set(before[1]),set(after[1]))
        for name,f in before[1].items():
            if name == source.FUNCTION:
                continue
            g = after[1][name]
            self.assertEqual(before[0][f['value']:f['value']+f['size']],after[0][g['value']:g['value']+g['size']],name)
            bindings = lambda o,f:{a-f['value']:v for a,v in o[2].items() if f['value'] <= a < f['value']+f['size']}
            self.assertEqual(bindings(before,f),bindings(after,g),name)
        self.assertEqual(len(before[1])-1,18)
        owner = (self.out/'before-packet_owner').read_text()
        for label,body,declarations in source.forms():
            row = json.loads((self.out/(label+'.json')).read_text())
            self.assertEqual((self.out/(label+'.c')).read_text(),source.recovered_owner(owner,body,declarations))
            raw,functions,relocations = parse_object(self.out/(label+'.o'))
            f = functions[source.FUNCTION]
            self.assertEqual(hashlib.sha256(raw[f['value']:f['value']+f['size']]).hexdigest(),row['raw_sha256'])
            bindings = {str(a-f['value']):v for a,v in relocations.items() if f['value'] <= a < f['value']+f['size']}
            self.assertEqual(bindings,{a:[tuple(v) for v in values] for a,values in row['relocations'].items()})
            data = sections(self.out/(label+'.elf'))['.text'][1]
            words = struct.unpack_from('>%dI'%(f['size']//4),data,f['value'])
            differences = sum(a != b for a,b in zip(words,self.truth))+abs(len(words)-40)
            self.assertEqual((len(words),(-words[0])&65535,differences,row['diagnostics']),
                (row['words'],row['frame'],row['differences'],''))
            self.assertFalse(row['pools'])
        text,functions,rel = after
        f = functions[source.FUNCTION]
        for i in range(40):
            bad = bytearray(text)
            bad[f['value']+i*4] ^= 1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        for offset in source.RELOCATIONS:
            bad = dict(rel)
            bad[f['value']+offset] = [('R_MIPS_26','wrong')]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):
                    source.checked_object(self.obj)
        with patch.object(source,'sections',return_value={'.rodata':(0,b'x')}):
            with self.assertRaises(ValueError):
                source.checked_object(self.obj)
        read = Path.read_bytes
        for key in source.ALL_PATHS:
            path = self.out/('before-'+key)
            with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p == path else read(p)):
                with self.assertRaisesRegex(ValueError,'fixture'):
                    source.freeze(self.root,self.out)

    def test_07_independent_symbol_carries_and_complete_first_prediction(self):
        anchors = dict(D_800BE9C0=0x9000FFF0,D_800DC2A0=0x90017FF0,D_800BE628=0x9002FFFC,
            D_800D2CA8=0x90038010,guMtxL2F=0x15123450,func_150A7A48=0x15034560)
        text,functions,rel = parse_object(self.obj)
        assembly,unresolved = emit_function(text,functions[source.FUNCTION],rel,source.FUNCTION,anchors)
        self.assertFalse(unresolved)
        obj = self.assemble(assembly,'rebase')
        script = self.out/'rebase.ld'
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%source.ENTRY)
        elf = self.out/'rebase.elf'
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
            *['--defsym=%s=0x%X'%item for item in anchors.items()],'-o',str(elf),str(obj)],capture_output=True,check=True)
        actual = list(struct.unpack('>40I',sections(elf)['.text'][1][:160]))
        expected = self.raw.copy()
        for offset,bindings in source.RELOCATIONS.items():
            kind,name = bindings[0]
            value = anchors[name]
            if kind == 'R_MIPS_26':
                expected[offset//4] = (expected[offset//4]&0xFC000000)|((value>>2)&0x03FFFFFF)
            else:
                expected[offset//4] = (expected[offset//4]&0xFFFF0000)|(((value+0x8000)>>16)&65535 if kind == 'R_MIPS_HI16' else value&65535)
        self.assertEqual(actual,expected)
        row = source.prelink_prediction(self.root,self.out)
        self.assertEqual((row['changed_ELF_bytes'],row['metadata_serialization_bytes'],row['metadata_exclusions']),(138,0,0))
        slot = (self.out/'predicted-slot.bin').read_bytes()
        for i in range(40):
            bad = bytearray(slot)
            bad[i*4] ^= 1
            with self.assertRaises(ValueError):
                source.slot_expected_image((self.out/'before-elf').read_bytes(),bytes(bad))


if __name__ == '__main__':
    unittest.main()
