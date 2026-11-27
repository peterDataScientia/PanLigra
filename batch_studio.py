"""Batch Studio: reuse PanLigra's native publication editor for many complexes."""
import argparse
import csv
import json
import re
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def _json(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c")

BRIDGE = """
window.panligraBatch = {
    snapshot: () => clone(state),
    svg: () => sceneSvg(),
    restore: candidate => loadLayoutObject(candidate),
    style: () => clone(state.style),
    applyStyle: style => {
        pushUndo();
        for (const key of ['residue','distance','interactions','interactionWidth','note','arrow']) {
            if (style[key] !== undefined) state.style[key] = clone(style[key]);
        }
        syncStylePanel(); syncCanvasUI(); renderAnnotations(); renderSelection();
    }
};
"""

SHELL = r"""<!doctype html><html lang="en"><meta charset="utf-8">
<title>PanLigra Batch Studio</title>
<style>
*{box-sizing:border-box}body{margin:0;font:14px Arial,sans-serif;color:#172033;background:#f5f7fa}
header{position:sticky;top:0;background:white;padding:12px;z-index:2;border-bottom:1px solid #ccd3df}
nav{display:flex;gap:8px;flex-wrap:wrap;align-items:center}button,select{font:inherit;padding:8px;border:1px solid #aab4c2;border-radius:5px;background:white;color:inherit}button:disabled{opacity:.45}button{cursor:pointer}iframe{width:100%;height:calc(100vh - 116px);border:0;background:white}#status{margin:8px 0 0}h1{font-size:18px;margin:0 0 8px}
</style>
<header><h1>PanLigra Batch Studio</h1><nav>
<button id="prev">Previous</button><select id="pick" aria-label="Complex"></select><button id="next">Next</button>
<button id="approve">Save &amp; Next</button><button id="global">Apply current style to all</button>
<button id="save">Save editable HTML</button><button id="export">Export all SVGs (ZIP)</button>
</nav><div id="status" role="status"></div></header>
<iframe id="editor" title="PanLigra interaction editor"></iframe>
<script id="batch-data" type="application/json">__BATCH_DATA__</script>
<script>
'use strict';
const data=JSON.parse(document.getElementById('batch-data').textContent);
const $=id=>document.getElementById(id), frame=$('editor');
let current=Math.min(data.index||0,data.entries.length-1), busy=false;
const entries=data.entries;
const copy=x=>JSON.parse(JSON.stringify(x));
const safeJSON=x=>JSON.stringify(x).replace(/</g,'\\u003c');
function api(){return frame.contentWindow?.panligraBatch}
function capture(){if(!api())throw Error('Editor is not ready');entries[current].layout=api().snapshot();entries[current].svg=api().svg();}
function refresh(message=''){
  $('pick').replaceChildren(...entries.map((e,i)=>new Option((i+1)+'. '+e.id+(e.done?' ✓':''),i)));
  $('pick').value=current;
  $('prev').disabled=busy||current===0;$('next').disabled=busy||current===entries.length-1;
  for(const id of ['pick','approve','global','save','export'])$(id).disabled=busy;
  $('status').textContent=message||((current+1)+' / '+entries.length+' • '+entries.filter(e=>e.done).length+' reviewed • '+data.failures.length+' failed inputs');
}
function openEditor(e){
  return new Promise((resolve,reject)=>{
    frame.onload=()=>{try{
      if(!api())throw Error('Native editor failed to initialize');
      if(e.layout)api().restore(e.layout);
      resolve();
    }catch(err){reject(err)}};
    frame.srcdoc=data.template.replace('__PANLIGRA_SCENE__',()=>safeJSON(e.scene));
  });
}
async function show(i,save=true){
  if(busy)return;busy=true;refresh();
  try{if(save)capture();current=i;await openEditor(entries[current]);}
  catch(e){$('status').textContent=e.message;busy=false;refresh(e.message);return;}
  busy=false;refresh();
}
function download(name,blob){const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
$('prev').onclick=()=>show(current-1);$('next').onclick=()=>show(current+1);$('pick').onchange=()=>show(Number($('pick').value));
$('approve').onclick=()=>{try{capture();entries[current].done=true;if(current<entries.length-1)show(current+1,false);else refresh();}catch(e){refresh(e.message)}};
$('global').onclick=()=>{
  try{capture();const style=api().style();
    for(const e of entries){
      const layout=e.layout||copy(e.scene);
      layout.style=layout.style||{};
      for(const key of ['residue','distance','interactions','interactionWidth','note','arrow'])if(style[key]!==undefined)layout.style[key]=copy(style[key]);
      e.layout=layout;e.svg=null;
    }
    api().applyStyle(style);capture();refresh('Global defaults applied; individual object overrides retained.');
  }catch(e){refresh(e.message)}
};
$('save').onclick=()=>{try{capture();data.index=current;const root=document.documentElement.cloneNode(true);
  root.querySelector('#editor').removeAttribute('srcdoc');
  root.querySelector('#batch-data').textContent=safeJSON(data);
  download('PanLigra_batch_edited.html',new Blob(['<!doctype html>'+root.outerHTML],{type:'text/html;charset=utf-8'}));
  refresh('Editable HTML saved.');
}catch(e){refresh(e.message)}};
// ZIP store method, CRC32 and central directory; no external dependency.
function zip(files){
 const enc=new TextEncoder(), chunks=[], central=[];let offset=0,cs=0;
 function header(n){return new Uint8Array(n)}
 function put(a,i,v,n=4){const d=new DataView(a.buffer);n===2?d.setUint16(i,v,true):d.setUint32(i,v>>>0,true)}
 function crc(a){let c=0xffffffff;for(const b of a){c^=b;for(let k=0;k<8;k++)c=(c>>>1)^((c&1)?0xedb88320:0)}return (c^0xffffffff)>>>0}
 for(const [name,txt] of files){
  const fn=enc.encode(name),body=enc.encode(txt),sum=crc(body),h=header(30),z=header(46);
  put(h,0,0x04034b50);put(h,4,20,2);put(h,6,0x800,2);put(h,14,sum);put(h,18,body.length);put(h,22,body.length);put(h,26,fn.length,2);
  put(z,0,0x02014b50);put(z,4,20,2);put(z,6,20,2);put(z,8,0x800,2);put(z,16,sum);put(z,20,body.length);put(z,24,body.length);put(z,28,fn.length,2);put(z,42,offset);
  chunks.push(h,fn,body);central.push(z,fn);offset+=h.length+fn.length+body.length;cs+=z.length+fn.length;
 }
 const end=header(22);put(end,0,0x06054b50);put(end,8,files.length,2);put(end,10,files.length,2);put(end,12,cs);put(end,16,offset);return new Blob([...chunks,...central,end],{type:'application/zip'});
}
$('export').onclick=async()=>{
 if(busy)return;busy=true;refresh();const start=current;
 try{capture();const files=[];
  for(let i=0;i<entries.length;i++){const e=entries[i];await openEditor(e);e.svg=api().svg();const name=String(i+1).padStart(3,'0')+'_'+e.id.replace(/[^a-zA-Z0-9_.-]/g,'_');files.push([name+'.svg',e.svg],[name+'.panligra.json',JSON.stringify(api().snapshot(),null,2)]);$('status').textContent='Exporting '+(i+1)+' / '+entries.length;}
  files.push(['batch_report.json',JSON.stringify({failures:data.failures,entries:entries.map(e=>({id:e.id,done:e.done}))},null,2)]);
  download('PanLigra_figures.zip',zip(files));
 }catch(e){alert('Export failed: '+e.message)}
 finally{try{await openEditor(entries[start]);}finally{busy=false;refresh();}}
};
show(current,false);
</script></html>"""

def export_html(entries, output, failures=None, *, offline=True):
    """Build one editable HTML from native PanLigra scene dictionaries."""
    entries = list(entries)
    if not entries:
        raise ValueError("No successful complexes to export")
    if len({e["id"] for e in entries}) != len(entries):
        raise ValueError("Complex IDs must be unique")
    template = (ROOT / "editor.html").read_text(encoding="utf-8")
    marker = "})();"
    pos = template.rfind(marker)
    if pos < 0 or "__PANLIGRA_SCENE__" not in template:
        raise RuntimeError("Incompatible native editor")
    template = template[:pos] + BRIDGE + template[pos:]
    if offline:
        template = re.sub(r'<script\s+src="https?://[^"]+"\s*></script>', "", template)
    payload = {"template": template, "entries": entries, "failures": failures or [], "index": 0}
    output = Path(output)
    output.write_text(SHELL.replace("__BATCH_DATA__", _json(payload), 1), encoding="utf-8")
    return output

def analyze_complex(path, site=None, *, width=1200, height=850):
    # Import RDKit before PLIP/Open Babel, matching the native application.
    from rdkit import Chem
    from plip_compat import ensure_inchikey_support
    ensure_inchikey_support()
    from plip.structure.preparation import PDBComplex
    from utils import plip_2d_interactions
    from interactive_engine import build_editor_scene
    from interaction_3d import build_3d_interaction_segments
    path = Path(path).resolve()
    if not site:
        mol = PDBComplex()
        mol.load_pdb(str(path))
        sites = [x.strip() for x in str(mol).splitlines()[1:]
                 if x.strip() and x.split(":")[0] not in {"ARN","ASH","GLH","LYN","HIE","HIP","SO4","PO4","HOH","WAT"}]
        if len(sites) != 1:
            raise ValueError(f"Expected exactly one eligible site; specify site explicitly: {sites}")
        site = sites[0]
    with tempfile.TemporaryDirectory(prefix="panligra_batch_") as tmp:
        analysis = plip_2d_interactions(str(path), site, save_files=False, save_pymol=False,
                                       canvas_height=height, canvas_width=width, output_dir=tmp)
        scene, _ = build_editor_scene(str(path), site, width=width, height=height,
                                      base_svg=None, analysis=analysis)
        scene["threeDStructure"] = Path(analysis["file_prot"]).read_text(encoding="utf-8", errors="replace")
        scene["threeDInteractions"] = build_3d_interaction_segments(analysis["my_interactions"], scene)
    return scene

def batch(items, output, *, offline=True):
    """Items: iterable of dictionaries with id, path and optional site."""
    entries, failures = [], []
    seen = set()
    for item in items:
        ident = str(item["id"])
        if ident in seen:
            raise ValueError(f"Duplicate complex ID: {ident}")
        seen.add(ident)
        try:
            entries.append({"id": ident, "scene": analyze_complex(item["path"], item.get("site"))})
        except Exception as exc:
            failures.append({"id": ident, "path": str(item["path"]), "error": str(exc)})
            print(f"[FAILED] {ident}: {exc}", flush=True)
    report = Path(str(output) + ".report.json")
    report.write_text(json.dumps({"successful": [e["id"] for e in entries], "failures": failures}, indent=2), encoding="utf-8")
    if not entries:
        print(f"No successful complexes. See {report}", flush=True)
        return failures
    export_html(entries, output, failures, offline=offline)
    return failures

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--input", type=Path, help="Directory of complete PDB complexes")
    inputs.add_argument("--manifest", type=Path, help="CSV with id,path,site (site optional)")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--online", action="store_true", help="Retain external 3D/PDF libraries")
    args = parser.parse_args()
    if args.manifest:
        with args.manifest.open(newline="", encoding="utf-8-sig") as f:
            items = list(csv.DictReader(f))
        for item in items:
            item["path"] = args.manifest.parent / item["path"]
    else:
        items = [{"id": p.stem, "path": p} for p in sorted(args.input.glob("*.pdb"))]
    if not items:
        parser.error("No complexes found")
    failures = batch(items, args.output, offline=not args.online)
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
