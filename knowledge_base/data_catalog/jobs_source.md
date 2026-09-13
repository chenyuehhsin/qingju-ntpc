# Jobs source

來源是 TaiwanJobs 新北職缺快照；job_postings 計刊登列數，hiring_count 合計求才人數，兩者不能混用。原始檔不納入 Git，部署讀取既有 processed summary；source_snapshot_date 是資料快照日期，不是 build 日期。

依據：`data/data_catalog.csv`、`scripts/employment/build_new_taipei_employment_summary.py`。
