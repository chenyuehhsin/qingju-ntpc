# Jobs per thousand youth

既有公式為 hiring_count / youth_18_35_count × 1000；分子是求才人數，不是刊登筆數。只有進入既有租金、人口與職缺 inner join 的行政區具有此衍生值；其他區保留 null，不另補算。它不是就業率、錄取機率或就業保證。

依據：`app/components/policy_lens.py`。
