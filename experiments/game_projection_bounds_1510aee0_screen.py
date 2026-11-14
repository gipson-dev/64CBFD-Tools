"""Reproduce the uncredited projection bounds candidate screen."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-projection-bounds-1510aee0-durable';out.mkdir(parents=True,exist_ok=True)
expected={'conker/conker.us.bin':'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
          'conker/build/conker.us.elf':'058f88114ae93f5fa9a271c240f4c0be1afcf68769fd51e3cb646c977cbde195',
          'conker/src/game/generated_137ED0.c':'a9ade8103bc0f2d2a671a6f627ee023803c9ad72251cec9da6b61e572fe676ce',
          'ido/ido5.3_recomp/cc':'ca4b4385eb89c5098b665ffe256f59aa1bfd73ccd8f104fcb3eee0314dcd236a'}
for name,digest in expected.items():
 data=(root/name).read_bytes()
 if name.endswith('.c'):data=data.replace(b'\r\n',b'\n')
 if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('screen input changed: '+name)
path=root/'conker/src/game/generated_137ED0.c';owner=path.read_text();old='s32 func_1510AEE0() {\n    return 0;\n}';assert owner.count(old)==1
decl='f32 fabsf(f32);\n#pragma intrinsic (fabsf)\n'
body='''s32 func_1510AEE0(f32 matrix[4][4], f32 x, f32 y, f32 z,
                  f32 nearPlane, f32 farPlane, f32 xScale, f32 yScale,
                  f32 *xResult, f32 *yResult) {
    f32 depth, horizontal, vertical;
    depth = -(matrix[3][2] + (matrix[0][2] * x + matrix[1][2] * y + matrix[2][2] * z));
    if (depth < nearPlane || farPlane < depth) return 1;
    horizontal = fabsf(matrix[3][0] + (matrix[0][0] * x + matrix[1][0] * y + matrix[2][0] * z)) * xScale;
    if (depth < horizontal) return 1;
    vertical = fabsf(matrix[3][1] + (matrix[0][1] * x + matrix[1][1] * y + matrix[2][1] * z)) * yScale;
    if (depth < vertical) return 1;
    if (xResult != 0) *xResult = 1.0f - horizontal / depth;
    if (yResult != 0) *yResult = 1.0f - vertical / depth;
    return 0;
}'''
symbols={r[1]:r[2][1] for r in symbol_rows((root/'conker/build/conker.us.elf').read_bytes())};truth=struct.unpack_from('>100I',(root/'conker/conker.us.bin').read_bytes(),0x138390)
base,bd=compile_owner(root,out,owner,'baseline');rows=[]
for i in (26,):
 candidate=body
 if i&1:candidate=candidate.replace('f32 depth, horizontal, vertical;', 'f32 vertical, horizontal, depth;')
 if i&2:candidate=candidate.replace('if (depth < nearPlane || farPlane < depth) return 1;', 'if (depth < nearPlane) return 1;\n    if (farPlane < depth) return 1;')
 if i&4:candidate=candidate.replace('f32 matrix[4][4]', 'f32 *matrix').replace('matrix[3][2]','matrix[14]').replace('matrix[0][2]','matrix[2]').replace('matrix[1][2]','matrix[6]').replace('matrix[2][2]','matrix[10]').replace('matrix[3][0]','matrix[12]').replace('matrix[0][0]','matrix[0]').replace('matrix[1][0]','matrix[4]').replace('matrix[2][0]','matrix[8]').replace('matrix[3][1]','matrix[13]').replace('matrix[0][1]','matrix[1]').replace('matrix[1][1]','matrix[5]').replace('matrix[2][1]','matrix[9]')
 if i&8:candidate=candidate.replace('f32 depth, horizontal, vertical;', 'f32 depth, horizontal; volatile f32 vertical;').replace('f32 vertical, horizontal, depth;', 'volatile f32 vertical; f32 horizontal, depth;')
 if i&16:candidate=candidate.replace('f32 x, f32 y, f32 z,', 'f32 x, f32 y, volatile f32 z,')
 try:
  obj,diag=compile_owner(root,out,owner.replace(old,decl+candidate),'candidate-'+str(i));raw,refs=payload(obj,'func_1510AEE0');ws=bound_blob(raw,refs,symbols)
  row={'variant':i,'words':len(ws),'same_positions':sum(a==b for a,b in zip(ws,truth)), 'neighbors':same_functions(base,obj,('func_1510AEE0',)),'pools_equal':normalized_pools(base)==normalized_pools(obj),'diagnostics':diag, 'references':list({x[1] for v in refs.values() for x in v})}
 except Exception as ex:row={'variant':i,'error':str(ex)}
 rows.append(row);print(row,flush=True)
assert rows==[{'variant':26,'words':96,'same_positions':27,'neighbors':3,'pools_equal':True,'diagnostics':'','references':[]}],rows
staged=candidate.replace('depth = -(matrix[3][2] + (matrix[0][2] * x + matrix[1][2] * y + matrix[2][2] * z));', 'depth = matrix[0][2] * x;\n    depth += matrix[1][2] * y;\n    depth += matrix[2][2] * z;\n    depth = -(matrix[3][2] + depth);')
staged=staged.replace('horizontal = fabsf(matrix[3][0] + (matrix[0][0] * x + matrix[1][0] * y + matrix[2][0] * z)) * xScale;', 'horizontal = matrix[0][0] * x;\n    horizontal += matrix[1][0] * y;\n    horizontal += matrix[2][0] * z;\n    horizontal = fabsf(matrix[3][0] + horizontal) * xScale;')
staged=staged.replace('vertical = fabsf(matrix[3][1] + (matrix[0][1] * x + matrix[1][1] * y + matrix[2][1] * z)) * yScale;', 'vertical = matrix[0][1] * x + matrix[1][1] * y + matrix[2][1] * z;\n    vertical = fabsf(matrix[3][1] + vertical) * yScale;')
obj,diag=compile_owner(root,out,owner.replace(old,decl+staged),'staged');ws=bound_blob(*payload(obj,'func_1510AEE0'),symbols)
assert len(ws)==96 and sum(a==b for a,b in zip(ws,truth))==15 and same_functions(base,obj,('func_1510AEE0',))==3 and normalized_pools(base)==normalized_pools(obj) and diag==''
(out/'screen.json').write_text(json.dumps(rows,indent=2)+'\n')
env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root),PYTHONDONTWRITEBYTECODE='1')
for test in ('guest','nan'):subprocess.run([sys.executable,'-m','tools.tests.game_projection_bounds_1510aee0_'+test+'_screen'],cwd=root,env=env,check=True)
