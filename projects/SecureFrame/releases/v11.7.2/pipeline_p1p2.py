"""Local-only P1/P2 orchestration. No source coordinates in reports.

Inject the private V11.6 adapter at runtime. This module never downloads
models, sends images outside loopback, or mutates source files.
"""
from __future__ import annotations

import argparse
import base64
import importlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
V1171 = HERE.parent / "v11.7.1"
if str(V1171) not in sys.path:
    sys.path.insert(0, str(V1171))
from hybrid_bus import validate_semantic, ground_nodes
from qwen_contract import request_semantic
from hybrid_fusion import fuse_grounded

def _local_host(host):
    from urllib.parse import urlsplit
    u = urlsplit(host)
    if u.scheme != "http" or u.hostname not in ("127.0.0.1", "localhost", "::1") or u.username or u.password or u.query or u.fragment or u.path not in ("", "/"):
        raise ValueError("Ollama host must be loopback HTTP only")
    return host

def local_ollama_infer(model, host, *, temperature=0.1, seed=42):
    """Ollama python SDK: string content, images=[base64], no OpenAI content lists."""
    _local_host(host)
    if not isinstance(model, str) or not model.strip():
        raise ValueError("model is required")
    def infer(prompt, image):
        from ollama import Client
        if not isinstance(image, (bytes, bytearray)):
            raise TypeError("image must be bytes")
        client = Client(host=host)
        response = client.chat(
            model=model,
            messages=[{"role":"user","content":prompt,
                       "images":[base64.b64encode(image).decode("ascii")]}],
            options={"temperature":temperature,"seed":seed},
            stream=False)
        if isinstance(response, dict):
            text = response["message"]["content"]
        else:
            text = response.message.content
        if not isinstance(text, str):
            raise TypeError("Ollama content must be string")
        return text
    return infer

def tesseract_tokens(image_bytes, *, upscale=1.0, psm=None, lang="eng"):
    """Return OCR bboxes in ORIGINAL image pixels, not resized coordinates."""
    from io import BytesIO
    from PIL import Image
    import pytesseract
    from pytesseract import Output
    if upscale <= 0 or upscale > 8:
        raise ValueError("ocr upscale must be in (0,8]")
    if psm is not None and (not isinstance(psm,int) or not 0 <= psm <= 13):
        raise ValueError("invalid psm")
    with Image.open(BytesIO(image_bytes)) as source:
        original = source.convert("RGB")
    if upscale != 1.0:
        scaled = original.resize((max(1,round(original.width*upscale)),
                                  max(1,round(original.height*upscale))))
    else:
        scaled = original
    config = "" if psm is None else f"--psm {psm}"
    data = pytesseract.image_to_data(scaled, lang=lang, config=config,
                                    output_type=Output.DICT)
    tokens=[]
    for i,raw in enumerate(data["text"]):
        value=raw.strip()
        if not value:
            continue
        left,top,width,height=(float(data[k][i])/upscale
                               for k in ("left","top","width","height"))
        if width<=0 or height<=0:
            continue
        tokens.append({"text":value,"bbox":[left,top,left+width,top+height]})
    return tokens

def _resolve_adapter(adapter=None):
    if adapter is not None:
        if not callable(getattr(adapter,"to_geometry",None)):
            raise TypeError("adapter must expose to_geometry(v116, image_path, ...)")
        return adapter
    try:
        module=importlib.import_module("adapter_v116")
    except ImportError as exc:
        raise RuntimeError("Local adapter_v116 is required; inject it or add it to PYTHONPATH") from exc
    if not callable(getattr(module,"to_geometry",None)):
        raise RuntimeError("adapter_v116.to_geometry missing")
    return module

def _safety_check(result):
    if result.get("auto_approval") is not False or result.get("llm_coordinates_used") is not False:
        raise ValueError("unsafe fusion result")
    for edge in result.get("edges",[]):
        if edge.get("source_verified") is not False or edge.get("review_state")!="needs_review" or edge.get("status") not in ("candidate","ambiguous"):
            raise ValueError("unsafe edge state")

def process_figure(v116, image_path, *, adapter=None, infer=None,
                   model="qwen3vl-30b-local", host="http://127.0.0.1:11434",
                   ocr_upscale=1.0, ocr_psm=None, ocr_lang="eng",
                   scale=1.0, max_retries=2, ocr_engine=tesseract_tokens):
    """Returns sanitized metrics only; raw geometry and inference stay in memory."""
    image_path=Path(image_path).resolve(strict=True)
    if not image_path.is_file():
        raise ValueError("image path is not a file")
    image=image_path.read_bytes()
    geometry=_resolve_adapter(adapter).to_geometry(v116, str(image_path))
    if not isinstance(geometry,dict):
        raise ValueError("adapter returned invalid geometry")
    geometry=dict(geometry)
    # OCR always comes from the original image; never prompt-inject OCR labels.
    geometry["ocr"]=ocr_engine(image,upscale=ocr_upscale,psm=ocr_psm,lang=ocr_lang)
    response=request_semantic(infer or local_ollama_infer(model,host),image,max_retries=max_retries)
    if response["status"]!="valid":
        return {"status":"needs_review","semantic_valid":False,
                "attempts":response["attempts"],"pass_90":"NOT_EVALUABLE"}
    semantic=validate_semantic(response["semantic"])
    grounded=ground_nodes(semantic,geometry)
    result=fuse_grounded(semantic,geometry,grounded,scale=scale)
    _safety_check(result)
    return {"status":"candidate_review","semantic_valid":True,
            "attempts":response["attempts"],
            "node_count":len(grounded),
            "grounded_count":sum(n["grounding"]=="grounded" for n in grounded),
            "ambiguous_count":sum(n["grounding"]=="ambiguous" for n in grounded),
            "ungrounded_count":sum(n["grounding"]=="needs_review" for n in grounded),
            "edge_candidates":sum(e["status"]=="candidate" for e in result["edges"]),
            "edge_ambiguous":sum(e["status"]=="ambiguous" for e in result["edges"]),
            "auto_approval":False,"llm_coordinates_used":False,
            "source_verified":False,"review_state":"needs_review",
            "pass_90":"NOT_EVALUABLE"}

def run_figures(figures, *, adapter=None, infer=None, **options):
    """Each item: {image: local path, v116: private dict or local JSON path}."""
    out=[]
    for index,item in enumerate(figures):
        try:
            v116=item["v116"]
            if isinstance(v116,(str,Path)):
                v116=json.loads(Path(v116).read_text(encoding="utf-8"))
            metrics=process_figure(v116,item["image"],adapter=adapter,infer=infer,**options)
        except Exception as exc:
            # Never serialize exception text: it can contain private paths/data.
            metrics={"status":"needs_review","error_type":type(exc).__name__,
                     "pass_90":"NOT_EVALUABLE"}
        out.append({"figure_index":index,**metrics})
    return {"schema_version":"p1p2-dev","figures":out,
            "auto_approval":False,"llm_coordinates_used":False,
            "pass_90":"NOT_EVALUABLE"}

def main(argv=None):
    parser=argparse.ArgumentParser(description="Local P1/P2 SecureFrame orchestration")
    parser.add_argument("--v116",help="private V11.6 JSON input")
    parser.add_argument("--image",help="local image path")
    parser.add_argument("--figures",help="local JSON list of {v116,image}")
    parser.add_argument("--model",default=os.getenv("TM_OLLAMA_MODEL","qwen3vl-30b-local"))
    parser.add_argument("--ollama-host",default=os.getenv("TM_OLLAMA_HOST","http://127.0.0.1:11434"))
    parser.add_argument("--ocr-upscale",type=float,default=float(os.getenv("TM_OCR_UPSCALE","1")))
    parser.add_argument("--ocr-psm",type=int,default=None)
    parser.add_argument("--ocr-lang",default="eng")
    parser.add_argument("--scale",type=float,default=1.0)
    parser.add_argument("--report",help="local sanitized JSON report")
    args=parser.parse_args(argv)
    _local_host(args.ollama_host)
    if args.figures:
        if args.image or args.v116:
            parser.error("--figures cannot be combined with --image/--v116")
        figures=json.loads(Path(args.figures).read_text(encoding="utf-8"))
    else:
        if not args.image or not args.v116:
            parser.error("provide --figures or both --v116 and --image")
        figures=[{"v116":args.v116,"image":args.image}]
    if not isinstance(figures,list):
        parser.error("--figures must be a JSON list")
    report=run_figures(figures,model=args.model,host=args.ollama_host,
                       ocr_upscale=args.ocr_upscale,ocr_psm=args.ocr_psm,
                       ocr_lang=args.ocr_lang,scale=args.scale)
    serialized=json.dumps(report,ensure_ascii=False,indent=2)
    if args.report:
        target=Path(args.report)
        if target.exists():
            raise FileExistsError("refusing to overwrite existing report")
        with target.open("x",encoding="utf-8") as f:
            f.write(serialized+"\n")
    else:
        print(serialized)

if __name__=="__main__":
    main()
