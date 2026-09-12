# Temporal boundary

人口參考月、職缺快照日、租金參考月各自保留；未確認的 snapshot_month、jobs_reference_date 與 processed_at 為 null。generated_at 是處理時間，不是 reference month。不同來源不能假定同期；所有實際時間值由 structured tool 取得。

依據：`app/assistant_service.py`、`scripts/employment/build_new_taipei_employment_summary.py`、`outputs/population/ntpc_district_youth_18_35_metadata.json`。
