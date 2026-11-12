"""Menyisipkan bagian baru ke laporan akhir YANG SUDAH DISUNTING peneliti, tanpa membuat file baru.

Aturan (disepakati 12 Nov 2026): hanya satu file laporan. Perubahan dari Claude disisipkan langsung ke file
itu; paragraf lain (editan peneliti) tidak disentuh. Sebelum menulis, file dicadangkan ke backup/.

Sumber bagian baru: dokumen hasil luaran/buat_laporan_akhir.js (berkas sementara).

    python luaran/sisip_ke_laporan.py <laporan_peneliti.docx> <sumber.docx> <operasi...>
Operasi: ruang_lingkup, model_matematis, lampiran2, lampiran3, bukti_logbook
"""
import re
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOK = re.compile(r"<w:p[ >].*?</w:p>|<w:tbl>.*?</w:tbl>", re.S)


def teks(b):
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", b)).replace("&apos;", "'").replace("&quot;", '"').replace("&amp;", "&").strip()


def blok_body(x):
    b0 = x.index("<w:body>") + len("<w:body>")
    b1 = x.rindex("<w:sectPr")
    body = x[b0:b1]
    return b0, b1, [m for m in BLOK.finditer(body)], body


def cari(blocks, body, pred, mulai=0):
    for i in range(mulai, len(blocks)):
        if pred(teks(blocks[i].group(0))):
            return i
    raise ValueError("blok tidak ditemukan")


def main():
    lap, src, ops = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
    bak = ROOT / "backup" / f"{lap.stem}.sebelum_sisip_{datetime.now():%Y%m%d_%H%M%S}.docx"
    bak.parent.mkdir(exist_ok=True)
    shutil.copy(lap, bak)
    zl, zs = zipfile.ZipFile(lap), zipfile.ZipFile(src)
    xl = zl.read("word/document.xml").decode("utf-8")
    xs = zs.read("word/document.xml").decode("utf-8")
    rels_l = zl.read("word/_rels/document.xml.rels").decode("utf-8")
    rels_s = zs.read("word/_rels/document.xml.rels").decode("utf-8")
    ct = zl.read("[Content_Types].xml").decode("utf-8")
    media_baru = {}
    n_rel = [0]

    def bawa_gambar(xml):
        """Salin gambar yang dirujuk blok sumber ke laporan; ganti r:embed & docPr id."""
        def ganti(m):
            rid = m.group(1)
            tgt = re.search(rf'Id="{rid}"[^>]*Target="([^"]+)"', rels_s) or re.search(rf'Target="([^"]+)"[^>]*Id="{rid}"', rels_s)
            tgt = tgt.group(1)
            n_rel[0] += 1
            new_id = f"rIdSisip{datetime.now():%H%M%S}{n_rel[0]}"
            nama = f"media/sisip_{n_rel[0]}_{Path(tgt).name}"
            media_baru["word/" + nama] = zs.read("word/" + tgt)
            nonlocal_rels.append(f'<Relationship Id="{new_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="{nama}"/>')
            return f'r:embed="{new_id}"'
        xml = re.sub(r'r:embed="(rId[^"]+)"', ganti, xml)
        return re.sub(r'(<wp:docPr id=")(\d+)', lambda m: f"{m.group(1)}{70000 + int(m.group(2))}", xml)

    nonlocal_rels = []
    _, _, bs, body_s = blok_body(xs)

    def ambil(awal_pred, akhir_pred, termasuk_awal=True):
        i = cari(bs, body_s, awal_pred)
        j = cari(bs, body_s, akhir_pred, i + 1)
        return "".join(bawa_gambar(b.group(0)) for b in bs[(i if termasuk_awal else i + 1):j])

    log = []
    for op in ops:
        b0, b1, bl, body_l = blok_body(xl)
        if op == "ruang_lingkup":
            if any(teks(b.group(0)).startswith("Ruang lingkup.") for b in bl):
                log.append("ruang_lingkup: sudah ada, dilewati"); continue
            sis = ambil(lambda t: t.startswith("Ruang lingkup."), lambda t: t.startswith("1.3. Tujuan"))
            k = cari(bl, body_l, lambda t: t.startswith("Hipotesis: (H1)"))
            pos = b0 + bl[k].end()
        elif op == "model_matematis":
            if any(teks(b.group(0)) == "2.3.10. Model Matematis" for b in bl):
                log.append("model_matematis: sudah ada, dilewati"); continue
            sis = ambil(lambda t: t == "2.3.10. Model Matematis", lambda t: t == "2.4. Hasil")
            k = cari(bl, body_l, lambda t: t == "2.4. Hasil")
            pos = b0 + bl[k].start()
        elif op in ("lampiran2", "lampiran3"):
            h, h2 = (("Lampiran 2. Dokumentasi Kegiatan", "Lampiran 3. Contoh Keluaran Sistem") if op == "lampiran2"
                     else ("Lampiran 3. Contoh Keluaran Sistem", "Lampiran 4. Lembar Persetujuan Responden"))
            sis = ambil(lambda t: t == h, lambda t: t == h2, termasuk_awal=False)
            i = cari(bl, body_l, lambda t: t == h)
            j = cari(bl, body_l, lambda t: t == h2, i + 1)
            lama = [teks(b.group(0)) for b in bl[i + 1:j]]
            if any("[GAMBAR]" in t for t in lama) or "<w:drawing" in body_l[bl[i + 1].start():bl[j].start()]:
                log.append(f"{op}: isi peneliti sudah berisi gambar, TIDAK diganti"); continue
            xl = xl[:b0 + bl[i + 1].start()] + sis + xl[b0 + bl[j].start():]
            log.append(f"{op}: {j - i - 1} paragraf placeholder diganti isi baru")
            continue
        elif op == "bukti_logbook":
            nama = ["study literatus.png", "Penyiapan lingkungan pengembangan.png", "integrasi pipeline VAD.png",
                    "implementasi baseline rule-based.png", "Penyusunan data latih.png"]
            n = 0
            for nm in nama:
                pat = re.compile(r"(<w:t[^>]*>)" + re.escape(nm) + r"(</w:t>)")
                xl, k = pat.subn(r"\1[ISI]\2", xl, count=1)
                n += k
            log.append(f"bukti_logbook: {n} sel diganti [ISI]")
            continue
        elif op == "foto_kegiatan":
            # sumber berisi penanda SISIP_FOTO_MULAI ... SISIP_FOTO_SELESAI; disisipkan sebelum paragraf "[ISI: foto"
            # pertama di Lampiran 2
            if "Gambar L.6. Perekaman" in xl:
                log.append("foto_kegiatan: sudah ada, dilewati"); continue
            sis = ambil(lambda t: t == "SISIP_FOTO_MULAI", lambda t: t == "SISIP_FOTO_SELESAI", termasuk_awal=False)
            i = cari(bl, body_l, lambda t: t == "Lampiran 2. Dokumentasi Kegiatan")
            k = cari(bl, body_l, lambda t: t.startswith("[ISI: foto"), i + 1)
            pos = b0 + bl[k].start()
        elif op.startswith("ganti:"):
            import json
            from xml.sax.saxutils import escape
            for e in json.load(open(op[6:], encoding="utf-8")):
                placeholder = e["cari"].startswith("[")
                hit = None
                for m in re.finditer(r"<w:p[ >].*?</w:p>", xl, re.S):
                    t = teks(m.group(0))
                    ok = {"persis": t == e["cari"], "awal": t.startswith(e["cari"]), "berisi": e["cari"] in t}[e["mode"]]
                    if ok:
                        hit = m
                        break
                if not hit:
                    log.append(f"ganti: TIDAK DITEMUKAN '{e['cari'][:50]}'"); continue
                p = hit.group(0)
                rprs = re.findall(r"<w:r[ >](?:(?!</w:r>).)*?(<w:rPr>.*?</w:rPr>)(?:(?!</w:r>).)*?<w:t", p, re.S)
                rpr = (rprs[-1] if e["aksi"] == "tambah" else rprs[0]) if rprs else ""
                if placeholder:
                    rpr = re.sub(r"<w:highlight [^>]*/>|<w:b/>|<w:bCs/>", "", rpr)
                run = f'<w:r>{rpr}<w:t xml:space="preserve">{escape(e["teks"])}</w:t></w:r>'
                if e["aksi"] == "tambah":
                    baru = p[: p.rindex("</w:p>")] + run + "</w:p>"
                else:
                    ppr = re.search(r"<w:pPr>.*?</w:pPr>", p, re.S)
                    baru = p[: p.index(">") + 1] + (ppr.group(0) if ppr else "") + run + "</w:p>"
                xl = xl[:hit.start()] + baru + xl[hit.end():]
                log.append(f"ganti ({e['aksi']}): '{e['cari'][:50]}'")
            continue
        else:
            raise ValueError(op)
        xl = xl[:pos] + sis + xl[pos:]
        log.append(f"{op}: disisipkan")

    import itertools
    nomor = itertools.count(1)   # docPr id wajib unik (temuan 12 Nov: sumber docx-js memakai id sama)
    xl = re.sub(r'(<wp:docPr id=")\d+', lambda m: m.group(1) + str(next(nomor)), xl)
    if "xmlns:m=" not in xl[:3000]:
        xl = xl.replace("<w:document ", '<w:document xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" ', 1)
    if nonlocal_rels:
        rels_l = rels_l.replace("</Relationships>", "".join(nonlocal_rels) + "</Relationships>")
    for ext, mime in (("png", "image/png"), ("jpeg", "image/jpeg"), ("jpg", "image/jpeg")):
        if any(k.endswith("." + ext) for k in media_baru) and f'Extension="{ext}"' not in ct:
            ct = ct.replace("</Types>", f'<Default Extension="{ext}" ContentType="{mime}"/></Types>')
    tmp = lap.with_suffix(".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
        for it in zl.infolist():
            if it.filename.endswith("/"):
                continue
            data = {"word/document.xml": xl.encode("utf-8"), "word/_rels/document.xml.rels": rels_l.encode("utf-8"),
                    "[Content_Types].xml": ct.encode("utf-8")}.get(it.filename, None)
            zo.writestr(it, data if data is not None else zl.read(it.filename))
        for k, v in media_baru.items():
            zo.writestr(k, v)
    zl.close(); zs.close()
    tmp.replace(lap)
    print("cadangan:", bak.relative_to(ROOT))
    print("\n".join(log))


if __name__ == "__main__":
    main()
