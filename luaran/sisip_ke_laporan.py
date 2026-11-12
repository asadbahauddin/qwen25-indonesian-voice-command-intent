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
    n_bak = 1
    while bak.exists():                     # dua proses dalam detik yang sama tidak boleh saling menimpa cadangan
        bak = bak.with_name(f"{bak.stem.split('__')[0]}__{n_bak}.docx"); n_bak += 1
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
            while f'Id="{new_id}"' in rels_l + "".join(nonlocal_rels):   # temuan 12 Nov: dua proses dalam 1 detik -> Id ganda
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
        elif op == "bukti_hki":
            # sumber berisi SISIP_HKI_MULAI ... SISIP_HKI_SELESAI (Gambar 4.1); disisipkan sebelum judul "4.2. Artikel Ilmiah"
            if "Gambar 4.1. Bukti pengajuan" in xl:
                log.append("bukti_hki: sudah ada, dilewati"); continue
            sis = ambil(lambda t: t == "SISIP_HKI_MULAI", lambda t: t == "SISIP_HKI_SELESAI", termasuk_awal=False)
            k = cari(bl, body_l, lambda t: t == "4.2. Artikel Ilmiah")
            pos = b0 + bl[k].start()
        elif op == "lampiran4":
            # sumber = lembar persetujuan bertanda tangan (docx peneliti). Penomoran daftar diubah jadi teks
            # ("1. ") karena definisi numbering milik dokumen sumber tidak ikut tersalin.
            if "LEMBAR PERSETUJUAN RESPONDEN" in xl:
                log.append("lampiran4: sudah ada, dilewati"); continue
            from xml.sax.saxutils import escape
            k_no, parts = 0, []
            for b in bs:
                x_b = b.group(0)
                if "LEMBAR PERSETUJUAN RESPONDEN" in teks(x_b):
                    k_no = 0
                if "<w:numPr>" in x_b:
                    k_no += 1
                    x_b = re.sub(r"<w:numPr>.*?</w:numPr>", "", x_b, flags=re.S)
                    rp = re.search(r"<w:r[ >](?:(?!</w:r>).)*?(<w:rPr>.*?</w:rPr>)", x_b, re.S)
                    rpr = re.sub(r"<w:b/>|<w:bCs/>", "", rp.group(1)) if rp else ""
                    m_r = re.search(r"<w:r[ >]", x_b)
                    x_b = x_b[:m_r.start()] + f'<w:r>{rpr}<w:t xml:space="preserve">{k_no}. </w:t></w:r>' + x_b[m_r.start():]
                parts.append(bawa_gambar(x_b))
            sis = "".join(parts)
            i = cari(bl, body_l, lambda t: t == "Lampiran 4. Lembar Persetujuan Responden")
            j = cari(bl, body_l, lambda t: t.startswith("Lampiran 5."), i + 1)
            pb = '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
            xl = xl[:b0 + bl[i + 1].start()] + sis + pb + xl[b0 + bl[j].start():]
            log.append(f"lampiran4: {len(bs)} blok lembar persetujuan menggantikan {j - i - 1} paragraf placeholder")
            continue
        elif op == "lampiran6":
            if "Lampiran 6. Daftar Perangkat Lunak dan Versi" in xl:
                log.append("lampiran6: sudah ada, dilewati"); continue
            sis = ambil(lambda t: t == "SISIP_L6_MULAI", lambda t: t == "SISIP_L6_SELESAI", termasuk_awal=False)
            pos = b0 + bl[-1].end()          # akhir isi dokumen (setelah Lampiran 5)
        elif op == "lampiran7":
            if "Lampiran 7. Data Card dan Struktur Dataset" in xl:
                log.append("lampiran7: sudah ada, dilewati"); continue
            sis = ambil(lambda t: t == "SISIP_L7_MULAI", lambda t: t == "SISIP_L7_SELESAI", termasuk_awal=False)
            pos = b0 + bl[-1].end()          # akhir isi dokumen (setelah Lampiran 6)
        elif op == "lampiran8":
            if "Lampiran 8. Draf Artikel Ilmiah" in xl:
                log.append("lampiran8: sudah ada, dilewati"); continue
            sis = ambil(lambda t: t == "SISIP_L8_MULAI", lambda t: t == "SISIP_L8_SELESAI", termasuk_awal=False)
            pos = b0 + bl[-1].end()          # akhir isi dokumen (setelah Lampiran 7)
        elif op == "lampiran9":
            if "Lampiran 9. Poster Ilmiah" in xl:
                log.append("lampiran9: sudah ada, dilewati"); continue
            sis = ambil(lambda t: t == "SISIP_L9_MULAI", lambda t: t == "SISIP_L9_SELESAI", termasuk_awal=False)
            pos = b0 + bl[-1].end()          # akhir isi dokumen (setelah Lampiran 8)
        elif op.startswith("logbook:"):
            # Tabel logbook (Lampiran 1) disusun ulang dari spesifikasi JSON: tiap entri memakai baris lama ke-"baris"
            # (format sel dipertahankan); "baru": true = salinan baris itu. Kolom yang tidak disebut tidak diubah.
            # "gambar": kunci penanda SISIP_LB_<kunci> pada sumber; gambar + teks "bukti" mengisi kolom Bukti.
            import json
            from xml.sax.saxutils import escape
            spek = json.load(open(op[8:], encoding="utf-8"))
            tbs = [m for m in re.finditer(r"<w:tbl>.*?</w:tbl>", xl, re.S)
                   if "Paraf Pembimbing" in teks(m.group(0)) and "24–28 Agt 2026" in teks(m.group(0))]
            if len(tbs) != 1:
                raise RuntimeError(f"tabel logbook ditemukan {len(tbs)}")
            tb = tbs[0].group(0)
            if "<w:drawing" in tb:
                log.append("logbook: kolom bukti sudah berisi gambar, dilewati"); continue
            rows = [m.group(0) for m in re.finditer(r"<w:tr[ >].*?</w:tr>", tb, re.S)]
            r0 = tb.index(rows[0]) + len(rows[0])
            ps_s = re.findall(r"<w:p[ >].*?</w:p>", body_s, re.S)

            def gbr(k):
                i = next(i for i, p in enumerate(ps_s) if teks(p) == "SISIP_LB_" + k)
                return bawa_gambar(ps_s[i + 1])

            def isi_sel(sel, teks_baru=None, gambar=()):
                tcpr = re.search(r"<w:tcPr>.*?</w:tcPr>", sel, re.S).group(0)
                p1 = re.search(r"<w:p[ >].*?(</w:p>|/>)", sel[len("<w:tc>") + len(tcpr):], re.S).group(0)
                ppr = re.search(r"<w:pPr>.*?</w:pPr>", p1, re.S)
                ppr = ppr.group(0) if ppr else ""
                rpr = re.search(r"<w:rPr>.*?</w:rPr>", sel, re.S)
                rpr = rpr.group(0) if rpr else '<w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
                rpr = re.sub(r"<w:highlight [^>]*/>|<w:b/>|<w:bCs/>", "", rpr)   # format penanda [ISI] tidak dibawa
                par = [f'<w:p>{ppr}<w:r>{rpr}<w:t xml:space="preserve">{escape(teks_baru)}</w:t></w:r></w:p>'] if teks_baru else []
                par += [gbr(k) for k in gambar]
                return f"<w:tc>{tcpr}{''.join(par) or '<w:p/>'}</w:tc>"

            baru_rows = []
            for e in spek:
                row = rows[e["baris"]]
                cells = re.findall(r"<w:tc>.*?</w:tc>", row, re.S)
                if e.get("baru"):
                    row = re.sub(r' w14:(paraId|textId)="[^"]+"', "", row)
                    cells = re.findall(r"<w:tc>.*?</w:tc>", row, re.S)
                ubah = {0: e.get("no"), 1: e.get("tgl"), 2: e.get("desk")}
                for ci, t in ubah.items():
                    if t is not None:
                        cells[ci] = isi_sel(cells[ci], t)
                if "bukti" in e or "gambar" in e:
                    cells[3] = isi_sel(cells[3], e.get("bukti"), e.get("gambar", []))
                awal = row[:row.index("<w:tc>")]
                baru_rows.append(awal + "".join(cells) + "</w:tr>")
            tb_baru = tb[:r0] + "".join(baru_rows) + "</w:tbl>"
            xl = xl.replace(tb, tb_baru, 1)
            log.append(f"logbook: {len(baru_rows)} baris disusun ({sum(1 for e in spek if e.get('baru'))} baris baru)")
            continue
        elif op == "paraf_logbook":
            # Paraf pembimbing (gambar SISIP_LB_ttd) di kolom terakhir logbook, hanya baris yang sudah terlaksana
            # (baris bertanda "Rencana" dilewati). Izin Bu Vivi disampaikan peneliti, 12 Nov 2026.
            tbs = [m for m in re.finditer(r"<w:tbl>.*?</w:tbl>", xl, re.S)
                   if "Paraf Pembimbing" in teks(m.group(0)) and "24–28 Agt 2026" in teks(m.group(0))]
            if len(tbs) != 1:
                raise RuntimeError(f"tabel logbook ditemukan {len(tbs)}")
            tb = tbs[0].group(0)
            ps_s = re.findall(r"<w:p[ >].*?</w:p>", body_s, re.S)
            i_ttd = next(i for i, p in enumerate(ps_s) if teks(p) == "SISIP_LB_ttd")
            rows = [m.group(0) for m in re.finditer(r"<w:tr[ >].*?</w:tr>", tb, re.S)]
            tb_baru, n = tb, 0
            for row in rows[1:]:
                cells = re.findall(r"<w:tc>.*?</w:tc>", row, re.S)
                if "Rencana" in teks(cells[2]) or "<w:drawing" in cells[-1]:
                    continue
                tcpr = re.search(r"<w:tcPr>.*?</w:tcPr>", cells[-1], re.S).group(0)
                sel = f"<w:tc>{tcpr}{bawa_gambar(ps_s[i_ttd + 1])}</w:tc>"
                tb_baru = tb_baru.replace(row, row.replace(cells[-1], sel), 1)
                n += 1
            xl = xl.replace(tb, tb_baru, 1)
            log.append(f"paraf_logbook: {n} baris diparaf")
            continue
        elif op == "foto_bimbingan":
            # ganti paragraf "[ISI: foto bimbingan..." di Lampiran 2 dengan Gambar L.10; gambar L.10–L.14 dinomori ulang +1
            if "Kegiatan bimbingan dengan dosen pembimbing" in xl:
                log.append("foto_bimbingan: sudah ada, dilewati"); continue
            for nmr in range(14, 9, -1):
                xl, k = re.subn(rf"(<w:t[^>]*>)Gambar L\.{nmr}\.", rf"\g<1>Gambar L.{nmr + 1}.", xl)
                if k != 1:
                    raise RuntimeError(f"keterangan Gambar L.{nmr}. ditemukan {k} kali (harus 1)")
            sis = ambil(lambda t: t == "SISIP_BIMBINGAN_MULAI", lambda t: t == "SISIP_BIMBINGAN_SELESAI", termasuk_awal=False)
            m = next(m for m in re.finditer(r"<w:p[ >].*?</w:p>", xl, re.S) if teks(m.group(0)).startswith("[ISI: foto bimbingan"))
            xl = xl[:m.start()] + sis + xl[m.end():]
            log.append("foto_bimbingan: disisipkan, Gambar L.10–L.14 menjadi L.11–L.15")
            continue
        elif op == "tabel42_satu_opsi":
            # Tabel 4.2: buang kolom "Opsi B: Dataset", lebar kolom digabung ke kolom Program Komputer
            m_t = next((m for m in re.finditer(r"<w:tbl>.*?</w:tbl>", xl, re.S) if "Opsi B: Dataset" in teks(m.group(0))), None)
            if not m_t:
                log.append("tabel42_satu_opsi: tabel tidak ditemukan / sudah satu opsi"); continue
            t = m_t.group(0)
            cols = [int(c) for c in re.findall(r'<w:gridCol w:w="(\d+)"/>', t)]
            w2 = cols[1] + cols[2]
            t = re.sub(r"<w:tblGrid>.*?</w:tblGrid>", f'<w:tblGrid><w:gridCol w:w="{cols[0]}"/><w:gridCol w:w="{w2}"/></w:tblGrid>', t, flags=re.S)
            def baris(m_r):
                tr = m_r.group(0)
                tcs = list(re.finditer(r"<w:tc>.*?</w:tc>", tr, re.S))
                tr = tr[:tcs[2].start()] + tr[tcs[2].end():]                 # hapus sel ke-3
                tc2 = tcs[1].group(0)
                tr = tr.replace(tc2, re.sub(r'(<w:tcW w:w=")\d+', lambda q: q.group(1) + str(w2), tc2, count=1), 1)
                return tr
            t = re.sub(r"<w:tr[ >].*?</w:tr>", baris, t, flags=re.S)
            t = t.replace(">Opsi A: Program Komputer<", ">Program Komputer<")
            xl = xl[:m_t.start()] + t + xl[m_t.end():]
            log.append("tabel42_satu_opsi: kolom Opsi B dihapus")
            continue
        elif op == "hapus_vs":
            m_p = next((m for m in re.finditer(r"<w:p[ >].*?</w:p>", xl, re.S) if teks(m.group(0)) == "VSPENGESAHAN"), None)
            if not m_p:
                log.append("hapus_vs: tidak ditemukan"); continue
            p_new = re.sub(r"<w:r[ >](?:(?!</w:r>).)*?<w:t[^>]*>VS</w:t></w:r>", "", m_p.group(0), count=1, flags=re.S)
            xl = xl[:m_p.start()] + p_new + xl[m_p.end():]
            log.append(f"hapus_vs: '{teks(p_new)}'")
            continue
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
                elif e["aksi"] == "depan":       # label tebal di awal paragraf; isi lama tidak diubah
                    if teks(p).startswith(e["teks"].strip()):
                        log.append(f"ganti (depan): sudah ada '{e['teks'][:40]}'"); continue
                    rb = rpr.replace("<w:rPr>", "<w:rPr><w:b/><w:bCs/>", 1) if rpr else "<w:rPr><w:b/></w:rPr>"
                    run_b = f'<w:r>{rb}<w:t xml:space="preserve">{escape(e["teks"])}</w:t></w:r>'
                    m_r = re.search(r"<w:r[ >]", p)
                    baru = p[:m_r.start()] + run_b + p[m_r.start():]
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
