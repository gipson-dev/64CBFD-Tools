from pathlib import Path
import hashlib,json,struct,itertools
from tools.experiments import game_actor_projection_scan_15036148_recovery as source
OUT=source.OUT
ROOT=source.ROOT
SHA='7d4d50dbd89d5fc69a4c18ef41bb975244be1cfc60b7cc5acf574a2d22d5e513'
REFS={60:[('R_MIPS_HI16','D_800DBFF0')],64:[('R_MIPS_LO16','D_800DBFF0')],68:[('R_MIPS_HI16','D_800CC2D0')],72:[('R_MIPS_LO16','D_800CC2D0')],
      128:[('R_MIPS_HI16','.rodata')],136:[('R_MIPS_LO16','.rodata')],276:[('R_MIPS_26','func_1507C3E0')],364:[('R_MIPS_26','func_15035808')]}
ORIGINS=list(range(112));ORIGINS[84:91]=[85,84,90,89,88,87,86]

def derive(raw,refs):
    if hashlib.sha256(raw).hexdigest()!=SHA:raise ValueError('Changed projection scan payload')
    if refs!=REFS:raise ValueError('Changed projection scan bindings')
    words=struct.unpack('>112I',raw)
    result=struct.pack('>112I',*(words[i]for i in ORIGINS));bindings={}
    for new,old in enumerate(ORIGINS):
        if old*4 in refs:bindings[new*4]=[(kind,'D_80097D74'if symbol=='.rodata'else symbol)for kind,symbol in refs[old*4]]
    return result,bindings

def signature(w):
    op,rs,rt=w>>26,w>>21&31,w>>16&31;imm=((w&65535)^32768)-32768
    if op==35 and rs==16 and rt==6 and imm==20:return {'gr':{16},'gw':{6},'fr':set(),'mw':set(),'mr':{'actor.x'}}
    if op==17 and rs==0 and rt==7 and (w>>11&31)==0:return {'gr':set(),'gw':{7},'fr':{0},'mw':set(),'mr':set()}
    if op==57 and rs==29 and imm in(20,24,28,32,36):return {'gr':{29},'gw':set(),'fr':{rt},'mw':set(range(imm,imm+4)),'mr':set()}
    raise ValueError('Instruction outside independent packet block')

def commute(a,b):
    x,y=signature(a),signature(b)
    return not(x['gw']&(y['gr']|y['gw'])or y['gw']&(x['gr']|x['gw'])or x['mw']&y['mw'])

def symbolic_block(words):
    # Independent decoding over arbitrary incoming bit-vectors. The public
    # actor word and every private byte start as distinct symbolic terms.
    g=[('G',i)for i in range(32)];f=[('F',i)for i in range(32)]
    memory={i:('M',i)for i in range(40)};csr=('opaque incoming FCSR',)
    for w in words:
        if w==0:continue
        op,rs,rt,rd=w>>26,w>>21&31,w>>16&31,w>>11&31;imm=((w&65535)^32768)-32768
        if op==35 and rs==16:g[rt]=('actor word',imm)
        elif op==17 and rs==0 and w&2047==0:g[rt]=f[rd]
        elif op==57 and rs==29:
            for byte in range(4):memory[imm+byte]=('byte',f[rt],byte)
        else:raise ValueError('Unsupported independent symbolic packet instruction')
    return g,f,memory,csr

def block_controls(raw,retail):
    a=list(struct.unpack('>112I',raw))[84:91];b=list(struct.unpack('>112I',retail))[84:91]
    expected=symbolic_block(b);assert symbolic_block(a)==expected
    count=0
    for p in itertools.permutations(range(7)):
        assert symbolic_block([a[i]for i in p])==expected;count+=1
    changes={'wrong-actor-word':(0,a[0]+4),'wrong-mfc1-source':(1,a[1]^(2<<11)),
        'wrong-store-value':(2,a[2]^(2<<16)),'missing-store':(2,0),'wrong-store-home':(2,(a[2]&0xFFFF0000)|40)}
    rejected=[]
    for label,(index,word)in changes.items():
        wrong=a.copy();wrong[index]=word;assert symbolic_block(wrong)!=expected,label;rejected.append(label)
    return dict(all_symbolic_bit_vectors=True,positive_schedules=count,effective_semantic_controls=rejected,
        full_GPR_FPR_private_byte_state=True,FCSR_opaque_unchanged=True)

def prove(raw,bindings):
    normalized,refs=derive(raw,bindings);a=list(struct.unpack('>112I',raw));b=list(struct.unpack('>112I',normalized))
    assert all(a[i]==b[i]for i in range(112)if not 84<=i<=90)
    # The actor table and active stack frame are disjoint. Every memory write
    # is to its distinct aligned private outgoing argument word; no read can
    # alias one of these writes. MFC1, LW and SWC1 do not alter FCSR.
    assert signature(a[84])['mr']=={'actor.x'} and signature(a[85])['gw']=={7}
    assert len(set(a[86:91]))==5 and {a[i]&65535 for i in range(86,91)}=={20,24,28,32,36}
    order=list(range(84,91));swaps=[]
    for pos,wanted in enumerate(ORIGINS[84:91]):
        j=order.index(wanted)
        while j>pos:
            left,right=order[j-1],order[j];assert commute(a[left],a[right]);swaps.append([left,right]);order[j-1:j+1]=[right,left];j-=1
    assert order==ORIGINS[84:91]
    for i,w in enumerate(a):
        op=w>>26
        if op in(4,5,6,7,20,21,22,23)or(op==17 and w>>21&31==8):
            target=i+1+(((w&65535)^32768)-32768)
            assert not 85<=target<=90,(i,target)
    return dict(words=112,frame=152,permutation_words=7,changed_words=6,adjacent_independent_swaps=swaps,symbolic_block_controls=block_controls(raw,normalized),
        no_FP_operation_changed=True,FCSR_opaque_unchanged=True,complete_block_state_equal=True,
        all_other_instructions_and_branches_identical=True,no_branch_enters_block_interior=True,
        private_outgoing_store_offsets=[20,24,28,32,36],quiet_mapped_memory=True,
        helper_contract='normal o32, actor/active stack disjoint, unpassed private/code PCs not inspected',matching_credit=0)


from copy import deepcopy
import subprocess
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_path_heading_turn_roles import bound_blob

def independent_links():
    folder=OUT/"links";folder.mkdir(exist_ok=True)
    raw,refs=payload(OUT/'qualified-screen/candidate.o','func_15036148');derived,bindings=derive(raw,refs);report=prove(raw,refs)
    full=(ROOT/'conker/asm/61D10.s').read_text();start=full.index('glabel func_15036148\n');end=full.index('endlabel func_15036148',start)+len('endlabel func_15036148')
    p=folder/'original.s';p.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+full[start:end]+'\n.size func_15036148,.-func_15036148\n')
    original=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(original),str(p)],capture_output=True,check=True)
    expected,oldrefs=payload(original,'func_15036148');assert(derived,bindings)==(expected,oldrefs)
    anchors={n:int(n.split('_')[1],16)for rows in bindings.values()for _,n in rows}
    truth=struct.unpack_from('>112I',(ROOT/'conker/conker.us.bin').read_bytes(),0x635f8);assert tuple(bound_blob(derived,bindings,anchors))==truth
    negative=[]
    bad=bytearray(raw);bad[3]^=1;altered=deepcopy(refs);altered[128]=[('R_MIPS_HI16','D_80097D70')]
    for label,blob,relocs in(('payload',bytes(bad),refs),('binding',raw,altered)):
        try:derive(blob,relocs)
        except ValueError:negative.append(label)
        else:raise AssertionError('Changed input accepted')
    contexts=[]
    for index,(entry_shift,code_shift,data_shift)in enumerate(((0,0,0),(0x1000,0x2000,0x4348))):
        output=[]
        for name,blob,relocs in(('derived',derived,bindings),('original',expected,oldrefs)):
            text=['.set noat','.set noreorder','.text','.globl func_15036148','func_15036148:']
            for i,w in enumerate(struct.unpack('>112I',blob)):
                for kind,symbol in relocs.get(i*4,[]):text.append('.reloc ., '+kind+', '+symbol)
                text.append('.word 0x%08X'%w)
            p=folder/(name+'-'+str(index)+'.s');p.write_text('\n'.join(text)+'\n');obj=p.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-o',str(obj),str(p)],check=True,capture_output=True)
            script=p.with_suffix('.ld');script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(0x15036148+entry_shift))
            values={n:int(n.split('_')[1],16)+(code_shift if n.startswith('func_')else data_shift)for rows in relocs.values()for _,n in rows}
            elf=p.with_suffix('.elf');subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e','func_15036148',
                *['--defsym=%s=0x%X'%v for v in values.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
            output.append(sections(elf)['.text'][1])
        assert output[0]==output[1];contexts.append(dict(entry_shift=entry_shift,code_shift=code_shift,data_shift=data_shift))
    report.update(independent_links=contexts,HI16_LO16_carry=True,raw_binding_negative_controls=negative,retail_words=112,alignment_words=2)
    (OUT/'independent-links.json').write_text(json.dumps(report,indent=2)+'\n')

    return report
