"""e5 embedding na GPU przez transformers (bez sentence-transformers -> rocm-torch nietkniety).
mean-pool + L2-norm + prefix 'passage: ', fp16. Reużywane przez embed_silver i tag_web."""
import json, numpy as np, torch, torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel

_tok = _mdl = None
_dev = "cuda" if torch.cuda.is_available() else "cpu"
MODEL = "intfloat/multilingual-e5-base"

def load():
    global _tok, _mdl
    if _mdl is None:
        _tok = AutoTokenizer.from_pretrained(MODEL)
        _mdl = AutoModel.from_pretrained(MODEL).to(_dev).eval().half()

def embed(texts, bs=192, maxlen=192):
    load(); out = []
    for i in range(0, len(texts), bs):
        b = ["passage: " + (t or "")[:1500] for t in texts[i:i+bs]]
        enc = _tok(b, padding=True, truncation=True, max_length=maxlen, return_tensors="pt").to(_dev)
        with torch.no_grad():
            h = _mdl(**enc).last_hidden_state
            m = enc["attention_mask"].unsqueeze(-1).float()
            e = F.normalize((h*m).sum(1)/m.sum(1).clamp(min=1e-9), p=2, dim=1)
        out.append(e.float().cpu().numpy())
    return np.concatenate(out)

if __name__ == "__main__":
    ES = "/mnt/c/Projekty/Slayer/slayer-dsbench/eval_sets"
    rows = [json.loads(l) for l in open(f"{ES}/hplt-register-silver-v1.jsonl", encoding="utf-8") if l.strip()]
    X = embed([r["text"] for r in rows])
    np.save(f"{ES}/silver_emb.npy", X)
    json.dump([r["register"] for r in rows], open(f"{ES}/silver_labels.json", "w"))
    print("silver emb:", X.shape)
