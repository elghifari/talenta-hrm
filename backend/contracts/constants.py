UNIT_DEFAULT_FIELDS = frozenset(
    """
pihak1_nama alamat_unit unit_kelurahan unit_kecamatan unit_kota unit_provinsi unit_kodepos
hari_kerja_jml hari_kerja_rentang jam_sen_jum jam_sabtu_jam jam_ist jam_ist_jumat
""".split()
)
UNIT_CATALOG_FIELDS = UNIT_DEFAULT_FIELDS | {"key", "unit", "jam_minggu_jml__usang"}
JOB_CATALOG_FIELDS = frozenset(
    ("key", "unit", "division", "title", "pkwt_type", "jobdesk", "source_row")
)

MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
MAX_REQUEST_BYTES = 256 * 1024
BASE_TOKENS = frozenset(
    """
no_urut bulan_romawi tahun hari tgl_surat_teks kota_ttd nama jenis_kelamin tempat_lahir
 tgl_lahir jalan rt_rw kelurahan kecamatan kota provinsi kode_pos nip bidang_keahlian jabatan
uraian_tugas tugas_tambahan nama_unit alamat_unit jangka_waktu tgl_mulai tgl_berakhir gaji_pokok
 tunj_transport_makan tunj_jabatan tunj_kinerja tunj_keahlian lainnya saksi2_nama saksi2_jabatan
pihak1_nama unit_kelurahan unit_kecamatan unit_kota unit_provinsi unit_kodepos
jam_minggu hari_kerja jam_hari istirahat_senin_jumat istirahat_jumat
""".split()
)
TOKENS = {
    "yayasan": BASE_TOKENS | {"jam_senin_jumat", "jam_sabtu"},
    "guru": (BASE_TOKENS - {"bidang_keahlian"}) | {"jam_senin_jumat", "jam_sabtu"},
    "klinik_umum": BASE_TOKENS | {"jam_gabungan"},
}
