from contracts.formatting import compile_tokens


def test_compilation_preserves_reviewed_city_and_formats_date_money(contract_values):
    values = {**contract_values, "kota_ttd": "Reviewed City", "gaji_pokok": "1250000"}
    result = compile_tokens("yayasan", values)
    assert result["kota_ttd"] == "Reviewed City"
    assert result["gaji_pokok"] == "Rp 1.250.000"
    assert result["hari"] == "Kamis"
    assert result["bulan_romawi"] == "XI"
    assert result["tgl_mulai"] == "1 Desember 2026"
    assert "jobdesk" not in result
