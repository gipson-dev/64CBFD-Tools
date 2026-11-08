"""Actor context loop, closed register/constant schedule and overflow closure."""
import csv,hashlib,io,json,shlex,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object
from tools.pad_generated_object import parse_object,ELF_HEADER,SECTION_HEADER,SYMBOL,read_c_string
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
ROOT=Path(__file__).resolve().parents[2]
BUILD='conker/build/game-actor-context-1504ADD0-match'
SOURCE='conker/src/game_77AD0.c'
OBJECT='conker/build/src/game_77AD0.c.o'
OWNER,FUNCTION='game_77AD0','func_1504ADD0'
ENTRY,ROM,WORDS,FRAME=0x1504ADD0,0x78280,73,88
ELF,GUARDS='conker/build/conker.us.elf','conker/retail_word_patches.us.csv'
BEFORE_SHA='fb078ed1821b645c2d9f5f636c2450eb4fc0f6a8734f6fe672f7cdc8f83d7b91'
GUARD_SHA='931b6ca3673b8157c374871d9065dffbf39d419211960ab9383c6503808f7f25'
BINDINGS={44: [('R_MIPS_HI16', 'D_800C35EA')], 48: [('R_MIPS_LO16', 'D_800C35EA')], 64: [('R_MIPS_HI16', 'D_800CC2D0')], 100: [('R_MIPS_LO16', 'D_800CC2D0')], 68: [('R_MIPS_HI16', 'D_800BE728')], 96: [('R_MIPS_LO16', 'D_800BE728')], 72: [('R_MIPS_HI16', 'D_8008FD8C')], 92: [('R_MIPS_LO16', 'D_8008FD8C')], 76: [('R_MIPS_HI16', 'D_800C3E78')], 88: [('R_MIPS_LO16', 'D_800C3E78')], 80: [('R_MIPS_HI16', 'D_800CC284')], 84: [('R_MIPS_LO16', 'D_800CC284')], 116: [('R_MIPS_HI16', 'D_800D154C')], 132: [('R_MIPS_LO16', 'D_800D154C')], 188: [('R_MIPS_26', 'bzero')], 220: [('R_MIPS_26', 'func_150ED578')]}
sha=lambda b:hashlib.sha256(b).hexdigest()
STUB='// NON-MATCHING: ported from ects_proto (ECTS ROM build), not yet byte-verified for us\nvoid func_1504ADD0(void) {\n    s32 i;\n    struct127 *obj;\n    u8 sp48[6];\n\n    i = 0;\n    if (D_800C35EA != 1) {\n        obj = D_800CC2D0;\n        do {\n            if (obj->interaction_state != 0) {\n                D_800C3E78 = i;\n                D_800D154C = obj;\n                if ((s32) i < D_8008FD8C) {\n                    if (i < 4) {\n                        D_800CC284 = (*(s32 **) D_800BE728)[i];\n                    } else {\n                        bzero(sp48, 6);\n                        D_800CC284 = (s32) sp48;\n                    }\n                }\n                if ((obj->id == 0x28) || (obj->id == 0x77)) {\n                    func_150ED578(obj);\n                }\n            }\n            i++;\n            obj++;\n        } while (i != 0x19);\n    }\n}'
SELECTED='void func_150ED578(struct127 *actor);\n/* Refresh the active actor context and dispatch the selected actor kinds. */\nvoid func_1504ADD0(void) {\n    s32 slot;\n    struct127 *actor;\n    u8 fallback[6];\n\n    slot = 0;\n    if (D_800C35EA != 1) {\n\n        do {\n            actor = &D_800CC2D0[slot];\n            if (actor->interaction_state != 0) {\n                D_800C3E78 = slot;\n                D_800D154C = actor;\n                if (slot < D_8008FD8C) {\n                    if (slot < 4) D_800CC284 = (*(s32 **)D_800BE728)[slot];\n                    else {\n                        bzero(fallback, 6);\n                        D_800CC284 = (s32)fallback;\n                    }\n                }\n                if (actor->id == 0x28 || actor->id == 0x77) func_150ED578(actor);\n            }\n            slot++;\n\n        } while (slot != 25);\n    }\n}'
RAW_SHA='bdb126c9d1b4accd1fff0856b4c5918c457dcb67ab1b03a0108915aefcf7f693'


def source_states(live):
    if live.count(STUB)==1:return live,live.replace(STUB,SELECTED,1),False
    if live.count(SELECTED)!=1:raise ValueError('Actor context source changed')
    return live.replace(SELECTED,STUB,1),live,True

def function_blob(obj):
    text,functions,refs=parse_object(obj);f=functions[FUNCTION];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in refs.items()if a<=p<a+n}

def normalize(raw,refs):
 if len(raw)!=292 or sha(raw)!=RAW_SHA or refs!=BINDINGS:raise ValueError('Unknown actor-context C words/bindings')
 w=list(struct.unpack('>73I',raw));order=list(range(26))+[27,58,39]+list(range(28,39))+[46]+list(range(40,46))+list(range(47,51))+[26]+list(range(51,58))+list(range(59,73))
 assert sorted(order)==list(range(73));inverse={v:i for i,v in enumerate(order)};mp={16:17,17:16,18:19,19:18,20:21,21:22,22:23,23:30}
 def rename(x,mapping):
  op=x>>26;shifts=(21,16,11)if op==0 else(16,)if op==15 else(21,16);y=x
  for b in shifts:y=(y&~(31<<b))|(mapping.get((x>>b)&31,(x>>b)&31)<<b)
  return y
 result=[];relocs={}
 for j,i in enumerate(order):
  x=w[i]
  if 14<=i<=60:x=rename(x,{30:1}if i==26 else{1:20}if i==58 else{**mp,30:1}if i==53 else{**mp,1:20}if i==59 else mp)
  if i in(51,53):x=(x&~((31<<21)|(31<<16)))|((x>>21&31)<<16)|((x>>16&31)<<21)
  if x>>26 in(1,4,5,6,7,20,21,22,23):
   target=i+1+((w[i]&65535)^32768)-32768
   dest=inverse[59 if i in(30,53)else 47 if i==38 else target];x=(x&0xFFFF0000)|((dest-j-1)&65535)
  result.append(x)
  if i*4 in refs:relocs[j*4]=refs[i*4]
 return struct.pack('>73I',*result),relocs
def guard_rows(raw,refs):
    normal,nrefs=normalize(raw,refs);spec=lambda rs:';'.join(k+':'+n for k,n in rs)or'-'
    rows=[[OWNER,FUNCTION,hex(i*4),f'0x{a:08X}',f'0x{b:08X}',spec(refs.get(i*4,[])),spec(nrefs.get(i*4,[])),
      'Normalize closed actor-context register lifetimes and invariant setup','','','false']for i,(a,b)in enumerate(zip(struct.unpack('>73I',raw),struct.unpack('>73I',normal)))if a!=b or refs.get(i*4)!=nrefs.get(i*4)]
    if len(rows)!=44:raise ValueError('Actor context guard derivation changed')
    return rows

def guard_manifest(before,raw,refs):
    if sha(before)!=GUARD_SHA or not before.endswith(b'\n'):raise ValueError('Inherited guard prefix changed')
    stream=io.StringIO(newline='');csv.writer(stream,lineterminator='\n').writerows(guard_rows(raw,refs));return before+stream.getvalue().encode()

def freeze(root,out):
    folder=out/'frozen';receipt=out/'frozen-inputs.json'
    if not receipt.exists():
        if sha((root/ELF).read_bytes())!=BEFORE_SHA:raise ValueError('Freeze the committed actor-context predecessor first')
        names=[SOURCE,OBJECT,ELF,GUARDS,'conker/Makefile','conker/build/conker.ld','conker/retail_layout.us.txt',
          'conker/conker.us.bin','conker/progress.csv','conker/src/game_45B80.c',
          'conker/src/game/generated_11A680.c','conker/asm/nonmatchings/game_11A680/func_150ED578.s',
          'conker/include/asm_processor_prelude.inc','conker/include/macro.inc',
          'conker/symbol_addrs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs.us.txt',
          'conker/undefined_syms_auto.txt','conker/undefined_funcs_auto.txt']
        names+=['conker/'+p for p in __import__('re').findall(r'#pragma GLOBAL_ASM\("([^\"]+)"\)',(root/SOURCE).read_text())]
        names += [p.relative_to(root).as_posix()for p in(root/'conker/include').rglob('*.h')]
        names += ['ido/ido5.3_recomp/'+n for n in('cc','cfe','uopt','ugen')]
        for name in names:
            p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/name).read_bytes())
        receipt.write_text(json.dumps({n:sha((folder/n).read_bytes())for n in names},indent=2)+'\n')
    hashes=json.loads(receipt.read_text());allowed={SOURCE,OBJECT,ELF,GUARDS}
    for n,h in hashes.items():
        if sha((folder/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Actor-context input changed: '+n)
    return hashes

def predict_image(before,truth):
    private='__retail_overflow_'+FUNCTION
    if sha(before)!=BEFORE_SHA or len(truth)!=292 or sha(truth)!='82707cca00466c010818305913b3167731b187e65d25863206c47b9fbc978459':raise ValueError('Actor context image inputs changed')
    header=list(ELF_HEADER.unpack_from(before));sections=[list(SECTION_HEADER.unpack_from(before,header[6]+i*header[11]))for i in range(header[12])]
    if header[12:]!=[12,11]:raise ValueError('Actor context ELF inventory changed')
    sh=sections[11];names=before[sh[4]:sh[4]+sh[5]]
    if [read_c_string(names,r[0])for r in sections][8:]!=['.game_overflow','.symtab','.strtab','.shstrtab']:raise ValueError('Actor context terminal sections changed')
    overflow,symtab,strtab=sections[8:11];strings=before[strtab[4]:strtab[4]+strtab[5]]
    rows=[list(SYMBOL.unpack_from(before,at))for at in range(symtab[4],symtab[4]+symtab[5],16)];labels=[read_c_string(strings,r[0])for r in rows];by_name=dict(zip(labels,rows))
    deleted=labels.index(private);removed=rows[deleted];root_index=labels.index(FUNCTION);root=rows[root_index]
    if tuple(removed[1:])!=(0x15F00000,296,2,0,8)or tuple(root[1:])!=(ENTRY,292,18,0,5):raise ValueError('Actor context old entry/overflow extent changed')
    cut_va,length=removed[1:3];end_va=cut_va+length
    moved={name:r[1]for name,r in zip(labels,rows)if r[5]==8 and end_va<=r[1]<overflow[3]+overflow[5]}
    if set(moved)!={'__retail_overflow_func_'+n for n in('1505210C','1506EE60','150768DC','150A7B80','15125490')}:raise ValueError('Actor context moved-private census changed')
    prefix=bytearray(before[:overflow[4]]);target_at=elf_slot_offset(before,ENTRY,292)
    if struct.unpack_from('>I',prefix,target_at)[0]!=0x08000000|(cut_va>>2&0x3FFFFFF):raise ValueError('Actor context predecessor trampoline changed')
    prefix[target_at:target_at+292]=truth;trampolines=[];expected_sites=set()
    for name,old in moved.items():
        canonical=name.removeprefix('__retail_overflow_');r=by_name[canonical];at=elf_slot_offset(before,r[1],4);word=struct.unpack_from('>I',before,at)[0]
        if word==0x08000000|(old>>2&0x3FFFFFF):
            struct.pack_into('>I',prefix,at,0x08000000|((old-length)>>2&0x3FFFFFF));trampolines.append(canonical);expected_sites.add(at)
    scanned=set();deleted_sites=set();pointer_words=[]
    for section in sections[1:9]:
        if section[2]&2:
            pointer_words.extend(section[4]+at for at in range(0,section[5],4)if cut_va<=struct.unpack_from('>I',before,section[4]+at)[0]<overflow[3]+overflow[5])
        if not section[2]&4:continue
        for offset in range(0,section[5],4):
            at=section[4]+offset;word=struct.unpack_from('>I',before,at)[0]
            if word>>26 not in(2,3):continue
            dest=((section[3]+offset+4)&0xF0000000)|((word&0x3FFFFFF)<<2)
            if end_va<=dest<overflow[3]+overflow[5]:scanned.add(at)
            if cut_va<=dest<end_va:deleted_sites.add(at)
    if scanned!=expected_sites or deleted_sites!={target_at}or pointer_words:raise ValueError('Actor context overflow reference closure changed: '+repr((scanned-expected_sites,deleted_sites,pointer_words)))
    start=removed[0];old_name=private.encode()+b'\0';root_text=FUNCTION.encode()+b'\0'
    if strings[start:start+len(old_name)]!=old_name or root[0]!=start+len('__retail_overflow_'):raise ValueError('Actor context shared string suffix changed')
    if labels[root_index-1:root_index+2]!=['D_800AE9C6',FUNCTION,'func_15071D08']:raise ValueError('Actor context global string order changed')
    insertion_old=rows[root_index-1][0]+len(labels[root_index-1].encode())+1
    def compact(at):
        if start<=at<start+len(old_name):raise ValueError('Unexpected shared actor context private string')
        return at-len(old_name)if at>=start+len(old_name)else at
    insertion=compact(insertion_old);flat=strings[:start]+strings[start+len(old_name):];new_strings=flat[:insertion]+root_text+flat[insertion:]
    old_size=overflow[5];new_size=old_size-length;rom_delta=((old_size+15)&~15)-((new_size+15)&~15)
    if(old_size,new_size,rom_delta)!=(0x64C,0x524,0x120):raise ValueError('Actor context overflow geometry changed')
    fresh=[]
    for index,(name,row)in enumerate(zip(labels,rows)):
        if index==deleted:continue
        r=row[:]
        if name==FUNCTION:r[0]=insertion
        else:
            at=compact(r[0]);r[0]=at+(len(root_text)if at>=insertion else 0)
        if read_c_string(new_strings,r[0])!=name:raise ValueError('Actor context symbol-string rewrite changed')
        if name in moved:r[1]-=length
        if name in('__romPos','debugger_overflow_ROM_START'):
            if tuple(row[1:])!=(0x25AC30,0,16,0,0xFFF1):raise ValueError('Actor context ROM cursor symbol changed')
            r[1]-=rom_delta
        fresh.append(r)
    data=before[overflow[4]:overflow[4]+old_size];cut=cut_va-overflow[3];new_overflow=data[:cut]+data[cut+length:]
    payloads={8:new_overflow,9:b''.join(SYMBOL.pack(*r)for r in fresh),10:new_strings,11:before[sections[11][4]:sections[11][4]+sections[11][5]]};result=prefix
    for index in range(8,12):
        section=sections[index];alignment=max(1,section[8]);result.extend(b'\0'*((-len(result))%alignment));section[4]=len(result);section[5]=len(payloads[index]);result.extend(payloads[index])
    sections[9][7]-=1;result.extend(b'\0'*((-len(result))%4));header[6]=len(result);result.extend(b''.join(SECTION_HEADER.pack(*r)for r in sections));result[:ELF_HEADER.size]=ELF_HEADER.pack(*header)
    program=struct.Struct('>8I');changed=0
    for i in range(header[10]):
        at=header[5]+i*header[9];r=list(program.unpack_from(before,at))
        if r[2]==0x15F00000:
            if r[4:6]!=[old_size,old_size]:raise ValueError('Actor context overflow segment changed')
            r[4]-=length;r[5]-=length;program.pack_into(result,at,*r);changed+=1
    if changed!=1:raise ValueError('Actor context overflow segment census changed')
    proof=dict(removed_private_body=private,removed_private_bytes=length,moved_private_definitions=moved,retargeted_trampolines=sorted(trampolines),removed_symbols=1,owner_file_symbol_retained=True,
      rom_cursor_bytes_removed=rom_delta,overflow_before=old_size,overflow_after=new_size,before_bytes=len(before),after_bytes=len(result),removed_file_bytes=len(before)-len(result),strict_exclusions=0)
    return bytes(result),proof

def strict_image(before,actual,truth):
    predicted,proof=predict_image(before,truth)
    if actual!=predicted:
        diffs=[i for i,(a,b)in enumerate(zip(predicted,actual))if a!=b]
        raise ValueError('Actor-context literal full-image prediction differs: '+repr((len(predicted),len(actual),len(diffs),diffs[:24])))
    return proof

def owner_pools(a,b):
    if normalized_pools(a)!=normalized_pools(b):raise ValueError('Actor-context owner pools changed')
    if sections(a).get('.reginfo')!=sections(b).get('.reginfo'):raise ValueError('Actor-context owner register metadata changed')

def prepare(root=ROOT):
    root=Path(root).resolve();out=root/BUILD;out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    before,after,installed=source_states((root/SOURCE).read_text())
    if before!=(out/'frozen'/SOURCE).read_text():raise ValueError('Actor-context predecessor source changed')
    old,old_diag=compile_owner(root,out,before,'predecessor-owner');new,new_diag=compile_owner(root,out,after,'qualified-owner')
    if diagnostic_rows(old_diag)!=diagnostic_rows(new_diag)or new_diag:raise ValueError('Actor-context owner diagnostics changed')
    neighbors=same_functions(old,new,(FUNCTION,));owner_pools(old,new)
    raw,refs=function_blob(new);normal,nrefs=normalize(raw,refs);truth=(root/'conker/conker.us.bin').read_bytes()[ROM:ROM+292]
    if struct.pack('>73I',*bound_blob(normal,nrefs,{name:(0x100226F0 if name=='bzero'else int(name.split('_')[1],16))for rows in nrefs.values()for _,name in rows}))!=truth:raise ValueError('Actor-context normalized C is not retail')
    old_guards=out/'predecessor-guards.csv';old_guards.write_bytes((out/'frozen'/GUARDS).read_bytes())
    guards=out/'qualified-guards.csv';guards.write_bytes(guard_manifest(old_guards.read_bytes(),raw,refs))
    if(root/GUARDS).read_bytes()!=(guards if installed else old_guards).read_bytes():raise ValueError('Actor-context live guard scope changed')
    old_pad=padded(root,out,old,old_guards,'predecessor-padded');new_pad=padded(root,out,new,guards,'qualified-padded');strict=new_pad
    if len(parse_object(new_pad)[1])!=58:raise ValueError('Actor-context complete padded owner inventory changed')
    padded_neighbors=same_functions(old_pad,new_pad,(FUNCTION,))
    if normalized_pools(old_pad)!=normalized_pools(new_pad)or function_blob(new_pad)!=(normal,nrefs):raise ValueError('Actor-context padded body/pools changed')
    if(root/OBJECT).read_bytes()!=(new_pad if installed else old_pad).read_bytes():raise ValueError('Actor-context live owner differs')
    proposal=out/'proposed-owner.c';proposal.write_text(after);make=make_shadow(root,out,proposal,guards,new_pad,new)
    old_image,new_image=link(root,out,old_pad,'predecessor-image'),link(root,out,new_pad,'qualified-image')
    if(root/ELF).read_bytes()!=(new_image if installed else old_image).read_bytes():raise ValueError('Actor-context live ELF differs')
    changed=strict_image(old_image.read_bytes(),new_image.read_bytes(),truth)
    a,_,aa=load_elf_functions(str(old_image),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_image),'mips-linux-gnu-objdump')
    canonical={n for n in a if not n.startswith('__retail_overflow_')};expected={FUNCTION,*changed['retargeted_trampolines']};
    if canonical!={n for n in b if not n.startswith('__retail_overflow_')}or any(aa[n]!=bb[n]for n in canonical)or{n for n in canonical if a[n]!=b[n]}!=expected:raise ValueError('Actor context canonical body/address closure changed')
    if set(a)-set(b)!={'__retail_overflow_'+FUNCTION}or set(b)-set(a):raise ValueError('Actor context deleted function census changed')
    for name,old in changed['moved_private_definitions'].items():
        if a[name]!=b[name]or aa[name]!=old or bb[name]!=old-296:raise ValueError('Actor context private code/relocation closure changed: '+name)
    data=audit_layout(new_image,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Actor-context protected data changed')
    report=dict(source_installed=installed,frozen_inputs=len(frozen),words=73,raw_words=73,frame=88,guards=44,direct_C=False,
      raw_neighbors=neighbors,padded_neighbors=padded_neighbors,diagnostics=0,
      actual_Make=make,image_prediction=changed,exclusions=0,functions_before=len(a),functions_after=len(b),canonical_functions=len(canonical),all_canonical_addresses_fixed=True,
      changed_bodies=sorted(expected),protected_data=data,owner_sha256=sha(new_pad.read_bytes()),ELF_sha256=sha(new_image.read_bytes()),guard_sha256=sha(guards.read_bytes()))
    (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,raw=raw,refs=refs,normal=normal,normal_refs=nrefs,predecessor_elf=old_image,qualified_elf=new_image,qualified_object=new_pad)

def padded(root,out,obj,guards,label,strict=False):
    folder=out/label;folder.mkdir(exist_ok=True);destination=folder/'game_77AD0.c.o';assembly=folder/'game_77AD0.c.o.padded.s'
    sys.modules.setdefault('pad_generated_object',pad_generated_object)
    from tools import pad_c_object
    assembly.write_text(pad_c_object.emit_padded_assembly(obj,root/'conker/retail_layout.us.txt',OWNER,word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(destination),str(assembly)],cwd=root/'conker',capture_output=True,check=True)
    return destination

def link(root, out, owner, label):
    script = (out/'frozen/conker/build/conker.ld').read_text()
    name = OBJECT.removeprefix('conker/')
    if script.count(name) != 1:
        raise ValueError('Actor-context linker owner changed')
    p = out/(label+'.ld')
    p.write_text(script.replace(name, owner.relative_to(root/'conker').as_posix()))
    destination = out/(label+'.elf')
    subprocess.run(['mips-linux-gnu-ld', '-T', str(p.relative_to(root/'conker')),
                    *[v for n in ('undefined_syms.us.txt', 'undefined_funcs.us.txt', 'undefined_syms_auto.txt', 'undefined_funcs_auto.txt') for v in ('-T', n)],
                    '--no-check-sections', '--no-warn-mismatch', '-o', str(destination.relative_to(root/'conker'))], cwd=root/'conker', capture_output=True, check=True)
    return destination

def make_shadow(root, out, proposal, guards, wanted, compact):
    shadow = out/'make-shadow'
    source_path = SOURCE
    conker = root/'conker'
    target = shadow/'src/game_77AD0.c.o'
    target.parent.mkdir(parents=True, exist_ok=True)
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR='+shadow.relative_to(conker).as_posix(), target.relative_to(conker).as_posix()], cwd=conker, capture_output=True, text=True, check=True)
    (out/'actual-Make-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected actor-context Make command: '+repr(args))
        args = [proposal.relative_to(conker).as_posix() if a == source_path.removeprefix('conker/') else guards.relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown actor-context Make redirect')
            redirect = (conker/args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        result = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        allowed_diagnostics = Counter()
        if result.returncode or diagnostic_rows(result.stderr) != allowed_diagnostics or (redirect is None and result.stdout):
            raise ValueError(result.stdout+result.stderr)
        if redirect is not None:
            redirect.write_text(result.stdout)
        commands.append(args)
    if len(commands) != 5 or len([a for a in commands if a[0] == '../ido/ido5.3_recomp/cc' and '-O2' in a and '-g3' in a]) != 1:
        raise ValueError('Actor-context actual Make profile changed')
    if target.read_bytes() != wanted.read_bytes():
        raise ValueError('Actor-context actual Make padded owner differs')
    count = same_functions(compact, Path(str(target)+'.compact'))
    (out/'actual-Make-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    return dict(commands=len(commands), functions=count, padded_object_equal=True, inherited_Make_warnings=plan.stderr)

if __name__=="__main__":print(json.dumps(prepare()["report"],indent=2))
