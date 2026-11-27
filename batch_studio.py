"""Batch Studio: reuse PanLigra's native publication editor for many complexes."""
import argparse
import base64
import csv
import json
import re
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def _json(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c")

BATCH_EDITOR_CSS = """
/* Batch-only application chrome; SVG scientific scene untouched. */
html,body{height:100%;margin:0!important;overflow:hidden;background:#eef2f7;color:#101e32;font-family:Arial,sans-serif}
body{display:flex;flex-direction:column;min-height:0}
#pv-root{flex:1;min-height:0;display:grid!important;grid-template-columns:minmax(0,1fr);grid-template-rows:auto minmax(0,1fr);gap:0;width:100%;overflow:hidden}
#pv-root.batch-inspector-open{grid-template-columns:minmax(0,1fr) minmax(280px,330px)}
#pv-toolbar{grid-column:1/-1;grid-row:1;position:relative;top:auto;z-index:40;border-radius:0;padding:6px 9px;gap:5px;box-shadow:none}
#pv-wrap{grid-column:1;grid-row:2;min-height:0;min-width:0;overflow:hidden;display:flex;flex-direction:column}
#pv-stage{flex:1;min-height:0;overflow:auto!important;padding:8px;background:#edf1f6}
#pv-sync-grid{min-width:0;align-items:start}
#pv-style-panel{grid-column:2;grid-row:2;position:relative;top:auto;min-height:0;max-height:none;overflow:auto;border-radius:0;border:0;border-left:1px solid #b9c8da;padding:10px;box-shadow:none;background:white}
#pv-style-panel .pv-style-grid{display:grid;grid-template-columns:minmax(0,1fr);gap:8px}
#pv-style-panel .pv-style-grid section{padding:8px;background:#fff;border:1px solid #c5cfdd}
#pv-style-panel .pv-style-row{gap:5px;margin:5px 0}
#pv-style-panel :is(label,h4,strong,output,span,.pv-style-help){color:#142238;font-weight:700}
#pv-style-panel .pv-style-row label{font-size:12px}
#pv-style-panel :is(input,select,button){color:#111e30;font:600 12px Arial,sans-serif;max-width:100%}
#pv-style-panel select{min-width:0}
#pv-toolbar :is(button,summary,select){font-size:13px;font-weight:750}
#pv-toolbar button:not(.active):not(.primary){color:#10243d}
#pv-interaction-records{flex:none;margin:0;border-radius:0;max-height:34vh;overflow:auto}
#pv-interaction-records .head{padding:6px 10px}
#pv-interaction-records .summary{color:#23374d;font-weight:700}
@media(max-width:720px){#pv-root.batch-inspector-open{grid-template-columns:minmax(0,1fr) minmax(210px,42%)}#pv-style-panel{padding:5px}}
"""
BRIDGE = r"""
async function batchOfflinePDF(){
  const g=scaledExportGeometry(), name=(state.site||'PanLigra').replace(/[^a-zA-Z0-9_.-]/g,'_')+'_edited_'+g.scale+'x.pdf';
  status.textContent='Preparing offline PDF…';
  try{
    const image=await new Promise((resolve,reject)=>{
      const url=URL.createObjectURL(new Blob([sceneSvg()],{type:'image/svg+xml;charset=utf-8'}));
      const im=new Image();
      im.onload=()=>{URL.revokeObjectURL(url);resolve(im)};
      im.onerror=()=>{URL.revokeObjectURL(url);reject(Error('Cannot rasterize figure'))};
      im.src=url;
    });
    const canvas=document.createElement('canvas');canvas.width=g.width;canvas.height=g.height;
    const ctx=canvas.getContext('2d',{alpha:false});ctx.fillStyle='#fff';ctx.fillRect(0,0,g.width,g.height);ctx.drawImage(image,0,0,g.width,g.height);
    const rgba=ctx.getImageData(0,0,g.width,g.height).data;
    let rgb=new Uint8Array(g.width*g.height*3);
    for(let i=0,j=0;i<rgba.length;i+=4){rgb[j++]=rgba[i];rgb[j++]=rgba[i+1];rgb[j++]=rgba[i+2]}
    let filter='';
    if(typeof CompressionStream==='function'){
      rgb=new Uint8Array(await new Response(new Blob([rgb]).stream().pipeThrough(new CompressionStream('deflate'))).arrayBuffer());
      filter=' /Filter /FlateDecode';
    }
    const enc=new TextEncoder(), parts=[], offsets=[0];let length=0;
    const add=v=>{const p=typeof v==='string'?enc.encode(v):v;parts.push(p);length+=p.length};
    const obj=(n,body)=>{offsets[n]=length;add(n+' 0 obj\n');add(body);add('\nendobj\n')};
    const w=(g.baseWidth*.75).toFixed(4),h=(g.baseHeight*.75).toFixed(4);
    add('%PDF-1.4\n');
    obj(1,'<< /Type /Catalog /Pages 2 0 R >>');
    obj(2,'<< /Type /Pages /Kids [3 0 R] /Count 1 >>');
    obj(3,'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 '+w+' '+h+'] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>');
    offsets[4]=length;add('4 0 obj\n<< /Type /XObject /Subtype /Image /Width '+g.width+' /Height '+g.height+' /ColorSpace /DeviceRGB /BitsPerComponent 8'+filter+' /Length '+rgb.length+' >>\nstream\n');add(rgb);add('\nendstream\nendobj\n');
    const commands='q\n'+w+' 0 0 '+h+' 0 0 cm\n/Im0 Do\nQ\n';
    obj(5,'<< /Length '+enc.encode(commands).length+' >>\nstream\n'+commands+'endstream');
    const xref=length;add('xref\n0 6\n0000000000 65535 f \n');
    for(let i=1;i<=5;i++)add(String(offsets[i]).padStart(10,'0')+' 00000 n \n');
    add('trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'+xref+'\n%%EOF\n');
    download(name,'application/pdf',new Blob(parts,{type:'application/pdf'}));
    status.textContent='Offline PDF exported ('+g.width+' × '+g.height+' pixels, lossless raster).';
  }catch(e){status.textContent='PDF export failed: '+e.message;alert(status.textContent)}
}
const batchPdfButton=document.getElementById('pv-pdf');
batchPdfButton.onclick=()=>{if(window.jspdf?.jsPDF && typeof window.jspdf.jsPDF.API.svg==='function')return exportPDF();return batchOfflinePDF()};

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
*{box-sizing:border-box}html,body{height:100%;margin:0}body{display:flex;flex-direction:column;font:14px Arial,sans-serif;color:#172033;background:#eef2f7}
header{flex:none;background:#fff;border-bottom:1px solid #cbd5e1;padding:9px 14px}
.brand{display:flex;align-items:center;gap:9px;margin-bottom:8px}.brand img{width:29px;height:29px;object-fit:contain}.brand strong{font-size:19px;color:#142b50}.brand small{color:#64748b}.mode{margin-left:auto;font-size:12px;color:#475569}
nav{display:flex;gap:6px;flex-wrap:wrap;align-items:center}button,select{font:inherit;font-weight:700;padding:6px 10px;border:1px solid #b9c8da;border-radius:6px;background:white;color:#10243d;min-height:32px}button:disabled,select:disabled{opacity:.45}button{cursor:pointer}button:hover:not(:disabled){background:#eaf1fa}button.primary{background:#17488a;color:#fff;border-color:#17488a}button.primary:hover:not(:disabled){background:#12386c}#pick{max-width:240px}.separator{height:25px;border-left:1px solid #cbd5e1;margin:0 3px}
#editor{display:block;flex:1;min-height:0;width:100%;border:0;background:white}#status{margin:6px 0 0;color:#172033;font-size:12px;font-weight:700}.progress{height:4px;background:#e2e8f0;margin-top:7px;border-radius:4px;overflow:hidden}.progress span{display:block;height:100%;background:#17488a;width:0}
</style>
<header><div class="brand"><img id="logo" alt="" src="__BATCH_LOGO__"><strong>PanLigra</strong><small>Batch Studio · __BATCH_VERSION__</small><span class="mode" id="mode"></span></div><nav>
<button id="prev" title="Previous complex">‹ Previous</button><select id="pick" aria-label="Complex"></select><button id="next" title="Next complex">Next ›</button>
<button class="primary" id="approve">Save &amp; Next</button><span class="separator"></span>
<button id="fit" title="Fit figure to viewport">Fit to screen</button><button id="minus" aria-label="Zoom out">−</button><button id="plus" aria-label="Zoom in">+</button><span id="zoom" aria-live="polite">Fit</span>
<span class="separator"></span><button id="toggle3d">Show 3D</button><button id="global">Apply style to all</button>
<button id="save">Save editable HTML</button><button id="export">Export SVGs (ZIP)</button>
</nav><div id="status" role="status"></div><div class="progress" role="progressbar" aria-label="Reviewed complexes" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><span></span></div></header>
<iframe id="editor" title="PanLigra interaction editor"></iframe>
<script id="batch-data" type="application/json">__BATCH_DATA__</script>
<script>
'use strict';
const data=JSON.parse(document.getElementById('batch-data').textContent);
const $=id=>document.getElementById(id), frame=$('editor');
let current=Math.min(data.index||0,data.entries.length-1), busy=false, zoom=1, fit=true, show3d=false;
const entries=data.entries;
const copy=x=>JSON.parse(JSON.stringify(x));
const safeJSON=x=>JSON.stringify(x).replace(/</g,'\\u003c');
function api(){return frame.contentWindow?.panligraBatch}
function view(){
  const doc=frame.contentDocument, svg=doc?.getElementById('pv-svg-canvas'), panel=doc?.getElementById('pv-3d-panel'), grid=doc?.getElementById('pv-sync-grid');
  if(!svg||!panel||!grid)return;
  const inspector=doc.getElementById('pv-style-panel');
  doc.getElementById('pv-root').classList.toggle('batch-inspector-open',inspector.style.display!=='none');
  const available=!!frame.contentWindow?.$3Dmol && !data.offline;
  if(!available)show3d=false;
  panel.style.display=show3d?'':'none';
  grid.style.gridTemplateColumns=show3d?'':'minmax(0,1fr)';
  $('toggle3d').disabled=busy||!available;
  $('toggle3d').textContent=show3d?'Hide 3D':'Show 3D';
  $('mode').textContent=available?'2D + 3D available':'Offline / 2D editor';
  const stage=doc.getElementById('pv-stage');
  const ratio=Number(svg.getAttribute('width'))/Number(svg.getAttribute('height'));
  if(!Number.isFinite(ratio)||ratio<=0)return;
  const availableWidth=Math.max(100,stage.clientWidth-20);
  const availableHeight=Math.max(100,stage.clientHeight-20);
  const baseline=Math.min(availableWidth*(show3d ? 0.52 : 1),availableHeight*ratio);
  const w=Math.round(baseline*(fit?1:zoom));
  svg.style.width=w+'px';svg.style.maxWidth='none';svg.style.height='auto';svg.style.justifySelf=w>availableWidth?'start':'center';
  stage.style.overflow='auto';
  $('zoom').textContent=fit?'Fit':Math.round(zoom*100)+'% of fit';
}
function capture(){if(!api())throw Error('Editor is not ready');entries[current].layout=api().snapshot();entries[current].svg=api().svg();}
function refresh(message=''){
  $('pick').replaceChildren(...entries.map((e,i)=>new Option((i+1)+'. '+e.id+(e.done?' ✓':''),i)));
  $('pick').value=current;
  $('prev').disabled=busy||current===0;$('next').disabled=busy||current===entries.length-1;
  for(const id of ['pick','approve','global','save','export','fit','minus','plus'])$(id).disabled=busy;
  $('approve').textContent=current===entries.length-1?'Finish editing':'Save & Next';
  const percent=Math.round(100*entries.filter(e=>e.done).length/entries.length);
  document.querySelector('.progress span').style.width=percent+'%';
  document.querySelector('.progress').setAttribute('aria-valuenow',percent);
  $('status').textContent=((current+1)+' / '+entries.length+' • '+entries.filter(e=>e.done).length+' reviewed • '+data.failures.length+' failed inputs')+(message?' • '+message:'');
}
function openEditor(e){
  return new Promise((resolve,reject)=>{
    frame.onload=()=>{try{
      if(!api())throw Error('Native editor failed to initialize');
      if(e.layout)api().restore(e.layout);
      const doc=frame.contentDocument, inspector=doc.getElementById('pv-style-panel');
      new frame.contentWindow.MutationObserver(view).observe(inspector,{attributes:true,attributeFilter:['style']});
      doc.getElementById('pv-interaction-toggle').addEventListener('click',()=>frame.contentWindow.requestAnimationFrame(view));
      view();resolve();
    }catch(err){reject(err)}};
    frame.srcdoc=data.template.replace('__PANLIGRA_SCENE__',()=>safeJSON(e.scene));
  });
}
async function show(i,save=true){
  if(busy)return;busy=true;refresh();
  try{if(save)capture();current=i;await openEditor(entries[current]);}
  catch(e){$('status').textContent=e.message;busy=false;refresh(e.message);return;}
  busy=false;refresh();view();
}
function download(name,blob){const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
$('fit').onclick=()=>{fit=true;zoom=1;view()};
$('minus').onclick=()=>{fit=false;zoom=Math.max(.25,zoom/1.2);view()};
$('plus').onclick=()=>{fit=false;zoom=Math.min(4,zoom*1.2);view()};
$('toggle3d').onclick=()=>{show3d=!show3d;view();frame.contentWindow.dispatchEvent(new Event('resize'))};
window.addEventListener('resize',view);
$('prev').onclick=()=>show(current-1);$('next').onclick=()=>show(current+1);$('pick').onchange=()=>show(Number($('pick').value));
$('approve').onclick=()=>{try{capture();entries[current].done=true;if(current<entries.length-1)show(current+1,false);else refresh('Review complete. Use Save editable HTML to download your changes.');}catch(e){refresh(e.message)}};
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
 finally{try{await openEditor(entries[start]);}finally{busy=false;refresh();view();}}
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
    template = template.replace("</style>", BATCH_EDITOR_CSS + "</style>", 1)
    if offline:
        template = re.sub(r'<script\s+src="https?://[^"]+"\s*></script>', "", template)
    payload = {"template": template, "entries": entries, "failures": failures or [], "index": 0, "offline": offline}
    output = Path(output)
    logo_path = ROOT / "assets" / "panligra_logo_icon.png"
    logo = "data:image/png;base64," + base64.b64encode(logo_path.read_bytes()).decode("ascii") if logo_path.is_file() else ""
    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
    html = SHELL.replace("__BATCH_LOGO__", logo, 1).replace("__BATCH_VERSION__", version, 1)
    output.write_text(html.replace("__BATCH_DATA__", _json(payload), 1), encoding="utf-8")
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
