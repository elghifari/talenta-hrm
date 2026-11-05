from rest_framework.exceptions import ValidationError

from .formatting import RANGES
from .references import KINDS

GROUPS = {
    "Surat": [
        ("no_urut", "Nomor Urut Surat"),
        ("tgl_surat", "Tanggal Surat"),
        ("kota_ttd", "Kota Penandatanganan"),
    ],
    "Identitas dan alamat": [
        ("nama", "Nama Lengkap Karyawan"),
        ("jenis_kelamin", "Jenis Kelamin"),
        ("tempat_lahir", "Tempat Lahir"),
        ("tgl_lahir", "Tanggal Lahir"),
        ("jalan", "Alamat Jalan"),
        ("rt_rw", "RT/RW"),
        ("kelurahan", "Kelurahan/Desa"),
        ("kecamatan", "Kecamatan"),
        ("kota", "Kabupaten/Kota"),
        ("provinsi", "Provinsi"),
        ("kode_pos", "Kode Pos"),
        ("nip", "NIP"),
    ],
    "Penempatan dan uraian tugas": [
        ("bidang_keahlian", "Bidang Keahlian"),
        ("jabatan", "Jabatan"),
        ("jobdesk", "Uraian Tugas"),
        ("tambahan_mode", "Penempatan Tugas Tambahan"),
        ("tambahan_text", "Tugas Tambahan"),
        ("nama_unit", "Nama Unit / Lokasi Kerja"),
        ("alamat_unit", "Alamat Unit"),
        ("pihak1_nama", "Nama Pihak Pertama"),
        ("unit_kelurahan", "Kelurahan Pihak Pertama"),
        ("unit_kecamatan", "Kecamatan Pihak Pertama"),
        ("unit_kota", "Kota Pihak Pertama"),
        ("unit_provinsi", "Provinsi Pihak Pertama"),
        ("unit_kodepos", "Kode Pos Pihak Pertama"),
    ],
    "Waktu kerja": [
        ("hari_kerja_jml", "Jumlah Hari Kerja per Minggu"),
        ("hari_kerja_rentang", "Rentang Hari Kerja"),
        ("jam_sen_jum", "Jam Kerja Senin-Jumat"),
        ("jam_sabtu_jam", "Jam Kerja Sabtu (kosongkan kalau sama / libur)"),
        ("jam_ist", "Jam Istirahat Senin-Jumat"),
        ("jam_ist_jumat", "Jam Istirahat Jumat"),
    ],
    "Masa kontrak": [
        ("jangka_waktu", "Jangka Waktu"),
        ("tgl_mulai", "Tanggal Mulai"),
        ("tgl_berakhir", "Tanggal Berakhir"),
    ],
    "Gaji dan tunjangan": [
        ("gaji_pokok", "Gaji Pokok (Rp)"),
        ("tunj_transport_makan", "Transportasi & Makan (Rp)"),
        ("tunj_jabatan", "Tunjangan Jabatan (Rp)"),
        ("tunj_kinerja", "Tunjangan Kinerja (Rp)"),
        ("tunj_keahlian", "Tunjangan Keahlian (Rp)"),
        ("lainnya", "Lainnya (Rp)"),
    ],
    "Saksi": [("saksi2_nama", "Nama Saksi 2"), ("saksi2_jabatan", "Jabatan Saksi 2")],
}
AMOUNTS = frozenset(k for k, _ in GROUPS["Gaji dan tunjangan"])
DATES = frozenset(("tgl_surat", "tgl_lahir", "tgl_mulai", "tgl_berakhir"))
CHOICES = {
    "jenis_kelamin": ["Laki-laki", "Perempuan"],
    "hari_kerja_rentang": list(RANGES),
    "tambahan_mode": ["tambah", "ganti", "pasal3"],
}
OPTIONAL = frozenset(("jam_sabtu_jam", "tambahan_mode", "tambahan_text"))


def field_spec(pkwt_type):
    if pkwt_type not in KINDS:
        raise ValidationError({"pkwt_type": ["Tipe PKWT tidak valid."]})
    fields = []
    for group, entries in GROUPS.items():
        for key, label in entries:
            if key == "bidang_keahlian" and pkwt_type == "guru":
                continue
            kind = (
                "date"
                if key in DATES
                else "number"
                if key in AMOUNTS or key == "hari_kerja_jml"
                else "choice"
                if key in CHOICES
                else "textarea"
                if key in {"jobdesk", "tambahan_text"}
                else "text"
            )
            fields.append(
                {
                    "key": key,
                    "label": label,
                    "group": group,
                    "kind": kind,
                    "max_length": 20000 if kind == "textarea" else 1000,
                    "choices": CHOICES.get(key, []),
                    "required_for_generation": key not in OPTIONAL,
                }
            )
    return fields
