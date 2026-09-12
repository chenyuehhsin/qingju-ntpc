# Nursing to Beauty Phase 5 Stress Test

Source occupation: `Registered Nurses` (`29-1141.00`)
Target domain: `Beauty / Aesthetic / Personal Care`
Observation date for TaiwanJobs/training availability: `2026-09-01`

This is a stress test for user-driven cross-domain exploration. It does not modify the nursing->technology outputs and does not calculate transition success probability, policy recommendations, or a single career score.

## Method

- Candidate generation uses local O*NET occupation title/description, tasks, required skills/knowledge, job titles, and sample reported titles.
- Retrieval is deterministic keyword scoring for beauty, aesthetics, personal care, skin/hair/nail, spa, massage, and beauty sales/management aliases.
- Every generated candidate is passed through the existing evidence dimensions: skill similarity, RN->target directional skill coverage/gap, education/credential/training barriers, O*NET taxonomy distance, O*NET Related Occupations support, TaiwanJobs job-level relevance QA, and training title matching.
- Low `skill_similarity` is not an exclusion rule. If preparation barriers are low and training supply exists, the path is retained as a `Major-reskilling path` for exploration.

## Candidate Evidence Summary

| Candidate | Span | Feasibility | Skill similarity | Coverage | Gap | TW market | Training | High jobs | Medium jobs |
|---|---:|---|---:|---:|---:|---|---|---:|---:|
| First-Line Supervisors of Personal Service Workers | High skill reuse | Adjacent candidate | 0.983 | 0.935 | 0.242 | Insufficient public evidence | Strong | 0 | 0 |
| Hairdressers, Hairstylists, and Cosmetologists | Major reskilling | Bridge candidate | 0.972 | 0.952 | 0.183 | Strong | Moderate | 16 | 0 |
| Barbers | Major reskilling | Bridge candidate | 0.973 | 0.959 | 0.141 | Strong | Moderate | 16 | 0 |
| Shampooers | Major reskilling | Major-reskilling path | 0.971 | 0.962 | 0.148 | Strong | Moderate | 16 | 0 |
| Skincare Specialists | Partial skill reuse | Bridge candidate | 0.979 | 0.957 | 0.156 | Moderate | Strong | 3 | 2 |
| Massage Therapists | Partial skill reuse | Bridge candidate | 0.983 | 0.998 | 0.007 | Moderate | Strong | 2 | 0 |
| Spa Managers | Partial skill reuse | Bridge candidate | 0.967 | 0.865 | 0.522 | Insufficient public evidence | Strong | 0 | 0 |
| Retail Salespersons | Partial skill reuse | Bridge candidate | 0.966 | 0.931 | 0.243 | Insufficient public evidence | Strong | 0 | 2 |
| Door-to-Door Sales Workers, News and Street Vendors, and Related Workers | Partial skill reuse | Bridge candidate | 0.956 | 0.932 | 0.242 | Insufficient public evidence | Strong | 0 | 2 |
| Manicurists and Pedicurists | Major reskilling | Major-reskilling path | 0.974 | 1.000 | 0.000 | Insufficient public evidence | Strong | 0 | 0 |
| Makeup Artists, Theatrical and Performance | Major reskilling | Major-reskilling path | 0.964 | 0.894 | 0.406 | Insufficient public evidence | Strong | 0 | 0 |
| Dermatologists | Partial skill reuse | Infeasible / high-barrier | 0.988 | 0.940 | 0.224 | Insufficient public evidence | Strong | 0 | 0 |

## Representative TaiwanJobs Evidence

Only High relevance jobs are counted in the main market evidence. Medium relevance jobs are retained as review candidates and excluded from salary/demand statistics.

### First-Line Supervisors of Personal Service Workers

- High relevance jobs: 0
- Medium review candidates: 0
- Demand persons counted from High relevance only: 0
- Monthly salary median range from High relevance only: insufficient monthly salary - insufficient monthly salary
- High examples: No High relevance jobs. Current public market data is insufficient; this does not mean the career does not exist.
- Medium examples: none

### Hairdressers, Hairstylists, and Cosmetologists

- High relevance jobs: 16
- Medium review candidates: 0
- Demand persons counted from High relevance only: 33
- Monthly salary median range from High relevance only: 29500 - 32500
- High examples: 培訓設計師 | 景美景華精剪屋 | 台北市松山區 | 月薪 29500-30000 | 1.本科系畢或二年以上助理經驗或準師經驗(有染、洗髮基礎)。 2.若技術不足需接受公司委外培訓課程 (課程另行繳費，工具請自備，另公司有配合的訓練單位協會廠商)。  | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=2436107&HIRE_ID=13927177 || 美髮助理 | 台灣施舒雅美容世界股份有限公司 | 台北市信義區 | 月薪 29500-35000 | 1.美髮助理相關工作 2.洗髮.染髮.燙髮.剪髮等美髮服務工作 上班地點：均在百貨公司內，交通便利、鄰近捷運站，環境優雅 北區有信義新天地A4、SOGO】忠孝店、敦南店 待遇月薪2... | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=65243&HIRE_ID=13735953 || 美髮培訓生 | 唯萬華快速剪髮屋 | 台北市萬華區 | 月薪 29500-29500 | 1.本科系畢或一年以上沙龍助理經驗(有染、洗髮基礎)，但缺乏實務經驗者。 2.協助染髮、洗髮、髮品銷售、迎賓送客、門市環境維護。 3.需接受公司委外培訓課程，公司另有配合的訓練單位... | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=2435771&HIRE_ID=13926637 || 美髮設計師 | 唯重慶快速剪髮屋 | 台北市大同區 | 月薪 29500-60000 | 專業剪髮、染髮，著重服務品質 | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=1054082&HIRE_ID=14048775 || 美髮培訓生 | 景美景華精剪屋 | 台北市松山區 | 月薪 29500-29500 | 1.本科系畢或一年以上沙龍助理經驗(有染、洗髮基礎)，但缺乏實務經驗者。 2.協助染髮、洗髮、髮品銷售、迎賓送客、門市環境維護。 3.需接受公司委外培訓課程，公司另有配合的訓練單位... | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=2436107&HIRE_ID=13927491
- Medium examples: none

### Barbers

- High relevance jobs: 16
- Medium review candidates: 0
- Demand persons counted from High relevance only: 33
- Monthly salary median range from High relevance only: 29500 - 32500
- High examples: 培訓設計師 | 景美景華精剪屋 | 台北市松山區 | 月薪 29500-30000 | 1.本科系畢或二年以上助理經驗或準師經驗(有染、洗髮基礎)。 2.若技術不足需接受公司委外培訓課程 (課程另行繳費，工具請自備，另公司有配合的訓練單位協會廠商)。  | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=2436107&HIRE_ID=13927177 || 美髮助理 | 台灣施舒雅美容世界股份有限公司 | 台北市信義區 | 月薪 29500-35000 | 1.美髮助理相關工作 2.洗髮.染髮.燙髮.剪髮等美髮服務工作 上班地點：均在百貨公司內，交通便利、鄰近捷運站，環境優雅 北區有信義新天地A4、SOGO】忠孝店、敦南店 待遇月薪2... | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=65243&HIRE_ID=13735953 || 美髮培訓生 | 唯萬華快速剪髮屋 | 台北市萬華區 | 月薪 29500-29500 | 1.本科系畢或一年以上沙龍助理經驗(有染、洗髮基礎)，但缺乏實務經驗者。 2.協助染髮、洗髮、髮品銷售、迎賓送客、門市環境維護。 3.需接受公司委外培訓課程，公司另有配合的訓練單位... | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=2435771&HIRE_ID=13926637 || 美髮設計師 | 唯重慶快速剪髮屋 | 台北市大同區 | 月薪 29500-60000 | 專業剪髮、染髮，著重服務品質 | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=1054082&HIRE_ID=14048775 || 美髮培訓生 | 景美景華精剪屋 | 台北市松山區 | 月薪 29500-29500 | 1.本科系畢或一年以上沙龍助理經驗(有染、洗髮基礎)，但缺乏實務經驗者。 2.協助染髮、洗髮、髮品銷售、迎賓送客、門市環境維護。 3.需接受公司委外培訓課程，公司另有配合的訓練單位... | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=2436107&HIRE_ID=13927491
- Medium examples: none

### Shampooers

- High relevance jobs: 16
- Medium review candidates: 0
- Demand persons counted from High relevance only: 33
- Monthly salary median range from High relevance only: 29500 - 32500
- High examples: 培訓設計師 | 景美景華精剪屋 | 台北市松山區 | 月薪 29500-30000 | 1.本科系畢或二年以上助理經驗或準師經驗(有染、洗髮基礎)。 2.若技術不足需接受公司委外培訓課程 (課程另行繳費，工具請自備，另公司有配合的訓練單位協會廠商)。  | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=2436107&HIRE_ID=13927177 || 美髮助理 | 台灣施舒雅美容世界股份有限公司 | 台北市信義區 | 月薪 29500-35000 | 1.美髮助理相關工作 2.洗髮.染髮.燙髮.剪髮等美髮服務工作 上班地點：均在百貨公司內，交通便利、鄰近捷運站，環境優雅 北區有信義新天地A4、SOGO】忠孝店、敦南店 待遇月薪2... | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=65243&HIRE_ID=13735953 || 美髮培訓生 | 唯萬華快速剪髮屋 | 台北市萬華區 | 月薪 29500-29500 | 1.本科系畢或一年以上沙龍助理經驗(有染、洗髮基礎)，但缺乏實務經驗者。 2.協助染髮、洗髮、髮品銷售、迎賓送客、門市環境維護。 3.需接受公司委外培訓課程，公司另有配合的訓練單位... | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=2435771&HIRE_ID=13926637 || 美髮設計師 | 唯重慶快速剪髮屋 | 台北市大同區 | 月薪 29500-60000 | 專業剪髮、染髮，著重服務品質 | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=1054082&HIRE_ID=14048775 || 美髮培訓生 | 景美景華精剪屋 | 台北市松山區 | 月薪 29500-29500 | 1.本科系畢或一年以上沙龍助理經驗(有染、洗髮基礎)，但缺乏實務經驗者。 2.協助染髮、洗髮、髮品銷售、迎賓送客、門市環境維護。 3.需接受公司委外培訓課程，公司另有配合的訓練單位... | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=2436107&HIRE_ID=13927491
- Medium examples: none

### Skincare Specialists

- High relevance jobs: 3
- Medium review candidates: 2
- Demand persons counted from High relevance only: 7
- Monthly salary median range from High relevance only: 30000 - 42000
- High examples: 諮詢美容師 | 凱伊生技有限公司 | 台北市大安區 | 月薪 30000-35000 | 從事肌膚護理、保養、業務等服務並提供美容相關的保養建議。 客戶關係維護 客戶相關業務處理及預約追蹤 具備服務熱忱及敬業精神  | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=2679303&HIRE_ID=14618957 || 美容諮詢師 | 采彤股份有限公司 | 台北市中山區 | 月薪 29500-65000 | 產品介紹銷售、美容/美體技術服務 | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=2417353&HIRE_ID=11161935 || 芳療師(9/18 中徵) | 國亨開發敦北分公司 | 台北市松山區 | 月薪 38000-42000 | 1.芳療設備環境維護及備置  2.提供顧客芳療體驗及諮詢  3.根據酒店政策與程序提供顧客服務  4.協助水療及健身中心營運  5.處理、回應及匯報任何事件以及後續彙整 工作專業知... | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=2700509&HIRE_ID=14626601
- Medium examples: 醫美櫃台行政人員 | 聖宜診所 | 台北市大安區 | 月薪 36000-45000 | 1.客戶資料維護，病歷整理管理  2.每日約客相關業務處理及預約追蹤  3.櫃檯接待及約診作業 4.銷售結帳及退費處理 5.協助相關行政事宜 | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=2372115&HIRE_ID=14211289 || 紓壓艙芳療師(9/18中徵) | 時代國際飯店股份有限公司 | 台北市信義區 | 月薪 35000-- | 1.具備專業的按摩和身體治療，對芳療和按摩的知識有透徹的了解 2.運用專業技能和知識以及好的溝通技巧，提供顧客有效的紓壓方案 3.同時與紓壓艙主任共同負責管理顧客的完整體驗，包括櫃... | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=922007&HIRE_ID=14632207

### Massage Therapists

- High relevance jobs: 2
- Medium review candidates: 0
- Demand persons counted from High relevance only: 2
- Monthly salary median range from High relevance only: 36500 - 42000
- High examples: 紓壓艙芳療師(9/18中徵) | 時代國際飯店股份有限公司 | 台北市信義區 | 月薪 35000-- | 1.具備專業的按摩和身體治療，對芳療和按摩的知識有透徹的了解 2.運用專業技能和知識以及好的溝通技巧，提供顧客有效的紓壓方案 3.同時與紓壓艙主任共同負責管理顧客的完整體驗，包括櫃... | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=922007&HIRE_ID=14632207 || 芳療師(9/18 中徵) | 國亨開發敦北分公司 | 台北市松山區 | 月薪 38000-42000 | 1.芳療設備環境維護及備置  2.提供顧客芳療體驗及諮詢  3.根據酒店政策與程序提供顧客服務  4.協助水療及健身中心營運  5.處理、回應及匯報任何事件以及後續彙整 工作專業知... | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=2700509&HIRE_ID=14626601
- Medium examples: none

### Spa Managers

- High relevance jobs: 0
- Medium review candidates: 0
- Demand persons counted from High relevance only: 0
- Monthly salary median range from High relevance only: insufficient monthly salary - insufficient monthly salary
- High examples: No High relevance jobs. Current public market data is insufficient; this does not mean the career does not exist.
- Medium examples: none

### Retail Salespersons

- High relevance jobs: 0
- Medium review candidates: 2
- Demand persons counted from High relevance only: 0
- Monthly salary median range from High relevance only: insufficient monthly salary - insufficient monthly salary
- High examples: No High relevance jobs. Current public market data is insufficient; this does not mean the career does not exist.
- Medium examples: 醫美櫃台行政人員 | 聖宜診所 | 台北市大安區 | 月薪 36000-45000 | 1.客戶資料維護，病歷整理管理  2.每日約客相關業務處理及預約追蹤  3.櫃檯接待及約診作業 4.銷售結帳及退費處理 5.協助相關行政事宜 | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=2372115&HIRE_ID=14211289 || 美容諮詢師 | 采彤股份有限公司 | 台北市中山區 | 月薪 29500-65000 | 產品介紹銷售、美容/美體技術服務 | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=2417353&HIRE_ID=11161935

### Door-to-Door Sales Workers, News and Street Vendors, and Related Workers

- High relevance jobs: 0
- Medium review candidates: 2
- Demand persons counted from High relevance only: 0
- Monthly salary median range from High relevance only: insufficient monthly salary - insufficient monthly salary
- High examples: No High relevance jobs. Current public market data is insufficient; this does not mean the career does not exist.
- Medium examples: 醫美櫃台行政人員 | 聖宜診所 | 台北市大安區 | 月薪 36000-45000 | 1.客戶資料維護，病歷整理管理  2.每日約客相關業務處理及預約追蹤  3.櫃檯接待及約診作業 4.銷售結帳及退費處理 5.協助相關行政事宜 | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=2372115&HIRE_ID=14211289 || 美容諮詢師 | 采彤股份有限公司 | 台北市中山區 | 月薪 29500-65000 | 產品介紹銷售、美容/美體技術服務 | https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?EMPLOYER_ID=2417353&HIRE_ID=11161935

### Manicurists and Pedicurists

- High relevance jobs: 0
- Medium review candidates: 0
- Demand persons counted from High relevance only: 0
- Monthly salary median range from High relevance only: insufficient monthly salary - insufficient monthly salary
- High examples: No High relevance jobs. Current public market data is insufficient; this does not mean the career does not exist.
- Medium examples: none

### Makeup Artists, Theatrical and Performance

- High relevance jobs: 0
- Medium review candidates: 0
- Demand persons counted from High relevance only: 0
- Monthly salary median range from High relevance only: insufficient monthly salary - insufficient monthly salary
- High examples: No High relevance jobs. Current public market data is insufficient; this does not mean the career does not exist.
- Medium examples: none

### Dermatologists

- High relevance jobs: 0
- Medium review candidates: 0
- Demand persons counted from High relevance only: 0
- Monthly salary median range from High relevance only: insufficient monthly salary - insufficient monthly salary
- High examples: No High relevance jobs. Current public market data is insufficient; this does not mean the career does not exist.
- Medium examples: none

## Training Evidence

Training data has course title, hours, fee, provider, location, and dates, but no full syllabus. Course-to-skill mapping is deterministic title matching and should be manually reviewed before learner-facing recommendations.

### First-Line Supervisors of Personal Service Workers

- Missing skills: 2
- Missing skills with matched course evidence: 1
- Training coverage ratio over missing skills: 0.5
- Top matched courses: 香氛保養品調製與化妝品PIF安全建置實務班 (54h, 10500 TWD, High); 保養品與美容皂配方設計班 (78h, 16000 TWD, High); 癒手舒活spa芳療班 (66h, 15700 TWD, High); 挽臉美容專業人員實務班 (45h, 11800 TWD, Medium); 美容技能應用班 (70h, 16660 TWD, Medium); 美容師從業員培訓班 (72h, 15000 TWD, Medium); 美容技術指導師培訓班 (72h, 17100 TWD, Medium); 美容肌膚進階技能實務班 (72h, 17100 TWD, Medium)
- Total hours across top unique courses: 529.0
- Estimated direct course cost: 119860.0
- Learning burden: medium

### Hairdressers, Hairstylists, and Cosmetologists

- Missing skills: 1
- Missing skills with matched course evidence: 1
- Training coverage ratio over missing skills: 1.0
- Top matched courses: 美髮剪燙染應用班 (77h, 18320 TWD, Medium); 時尚美髮設計班 (47h, 12800 TWD, Medium); 時尚剪染美髮流行趨勢進階班 (78h, 18530 TWD, Medium)
- Total hours across top unique courses: 202.0
- Estimated direct course cost: 49650.0
- Learning burden: medium

### Barbers

- Missing skills: 1
- Missing skills with matched course evidence: 1
- Training coverage ratio over missing skills: 1.0
- Top matched courses: 美髮剪燙染應用班 (77h, 18320 TWD, Medium); 時尚美髮設計班 (47h, 12800 TWD, Medium); 時尚剪染美髮流行趨勢進階班 (78h, 18530 TWD, Medium)
- Total hours across top unique courses: 202.0
- Estimated direct course cost: 49650.0
- Learning burden: medium

### Shampooers

- Missing skills: 1
- Missing skills with matched course evidence: 1
- Training coverage ratio over missing skills: 1.0
- Top matched courses: 美髮剪燙染應用班 (77h, 18320 TWD, Medium); 時尚美髮設計班 (47h, 12800 TWD, Medium); 時尚剪染美髮流行趨勢進階班 (78h, 18530 TWD, Medium)
- Total hours across top unique courses: 202.0
- Estimated direct course cost: 49650.0
- Learning burden: medium

### Skincare Specialists

- Missing skills: 1
- Missing skills with matched course evidence: 1
- Training coverage ratio over missing skills: 1.0
- Top matched courses: 護膚及淨膚保養品調製實務班 (42h, 11080 TWD, High); 香氛保養品調製與化妝品PIF安全建置實務班 (54h, 10500 TWD, High); 保養品與美容皂配方設計班 (78h, 16000 TWD, High); 美容彩妝護膚技能班 (85h, 20200 TWD, High); 美容護膚彩粧技巧班 (91h, 19000 TWD, High); 化妝保養品成分功效與調製實務基礎班 (30h, 7860 TWD, Medium); 化妝保養品成分功效與調製實務基礎班 (30h, 7860 TWD, Medium); 保養品調製應用班 (47h, 12400 TWD, Medium)
- Total hours across top unique courses: 457.0
- Estimated direct course cost: 104900.0
- Learning burden: medium

### Massage Therapists

- Missing skills: 0
- Missing skills with matched course evidence: 0
- Training coverage ratio over missing skills: 1.0
- Top matched courses: 芳療舒壓與瑞典式按摩班 (84h, 19000 TWD, High); 經絡精油推拿與瑞典式按摩手技實作班 (105h, 18740 TWD, High); 芳療保健人才培訓班 (72h, 15450 TWD, Medium); 經絡調理按摩與牛角輔具運用班 (90h, 15650 TWD, Medium); 傳統整復推拿經絡保健班 (112h, 17630 TWD, Medium); 腳底按摩進階實戰A班 (31h, 6340 TWD, Medium); 腳底按摩調理手法實戰A班 (31h, 6340 TWD, Medium); 紓壓泰式按摩班 (33h, 6720 TWD, Medium)
- Total hours across top unique courses: 558.0
- Estimated direct course cost: 105870.0
- Learning burden: medium

### Spa Managers

- Missing skills: 8
- Missing skills with matched course evidence: 8
- Training coverage ratio over missing skills: 1.0
- Top matched courses: 芳療舒壓與瑞典式按摩班 (84h, 19000 TWD, High); 癒手舒活spa芳療班 (66h, 15700 TWD, High); 腳底按摩進階實戰A班 (31h, 6340 TWD, Medium); 腳底按摩調理手法實戰A班 (31h, 6340 TWD, Medium); 紓壓泰式按摩班 (33h, 6720 TWD, Medium); 腳底按摩專業理論班 (36h, 6000 TWD, Medium); 產後修復按摩及運動訓練班 (42h, 8610 TWD, Medium); 挽臉美容專業人員實務班 (45h, 11800 TWD, Medium)
- Total hours across top unique courses: 368.0
- Estimated direct course cost: 80510.0
- Learning burden: high

### Retail Salespersons

- Missing skills: 2
- Missing skills with matched course evidence: 2
- Training coverage ratio over missing skills: 1.0
- Top matched courses: 香氛保養品調製與化妝品PIF安全建置實務班 (54h, 10500 TWD, High); 保養品與美容皂配方設計班 (78h, 16000 TWD, High); 化妝保養品成分功效與調製實務基礎班 (30h, 7860 TWD, Medium); 化妝保養品成分功效與調製實務基礎班 (30h, 7860 TWD, Medium); 化妝品實作技能班 (36h, 9450 TWD, Medium); 護膚及淨膚保養品調製實務班 (42h, 11080 TWD, Medium); 挽臉美容專業人員實務班 (45h, 11800 TWD, Medium); 保養品調製應用班 (47h, 12400 TWD, Medium)
- Total hours across top unique courses: 362.0
- Estimated direct course cost: 86950.0
- Learning burden: medium

### Door-to-Door Sales Workers, News and Street Vendors, and Related Workers

- Missing skills: 2
- Missing skills with matched course evidence: 2
- Training coverage ratio over missing skills: 1.0
- Top matched courses: 香氛保養品調製與化妝品PIF安全建置實務班 (54h, 10500 TWD, High); 保養品與美容皂配方設計班 (78h, 16000 TWD, High); 化妝保養品成分功效與調製實務基礎班 (30h, 7860 TWD, Medium); 化妝保養品成分功效與調製實務基礎班 (30h, 7860 TWD, Medium); 化妝品實作技能班 (36h, 9450 TWD, Medium); 護膚及淨膚保養品調製實務班 (42h, 11080 TWD, Medium); 挽臉美容專業人員實務班 (45h, 11800 TWD, Medium); 保養品調製應用班 (47h, 12400 TWD, Medium)
- Total hours across top unique courses: 362.0
- Estimated direct course cost: 86950.0
- Learning burden: medium

### Manicurists and Pedicurists

- Missing skills: 0
- Missing skills with matched course evidence: 0
- Training coverage ratio over missing skills: 1.0
- Top matched courses: 凝膠指甲彩繪與AI美甲行銷班 (64h, 13740 TWD, High); 水光凝膠美甲與手部保養實務班 (47h, 12860 TWD, High); 美甲凝膠彩繪設計班 (66h, 14000 TWD, High); 沙龍凝膠彩繪美甲設計班 (77h, 17800 TWD, High); 凝膠美甲彩繪實務班 (84h, 19990 TWD, High); 凝膠彩繪美甲班 (144h, 21000 TWD, High); 凝膠美甲水彩創意設計班 (84h, 16500 TWD, Medium); 凝膠美甲實作班 (84h, 19250 TWD, Medium)
- Total hours across top unique courses: 650.0
- Estimated direct course cost: 135140.0
- Learning burden: medium

### Makeup Artists, Theatrical and Performance

- Missing skills: 3
- Missing skills with matched course evidence: 3
- Training coverage ratio over missing skills: 1.0
- Top matched courses: 美容彩妝護膚技能班 (85h, 20200 TWD, High); 整體造型創意彩妝實務班 (70h, 16660 TWD, Medium); 保養品與美容皂配方設計班 (78h, 16000 TWD, Medium); 整體造型彩妝新秘進階班 (98h, 23320 TWD, Medium); 職場形象彩妝造型實務班 (36h, 9850 TWD, Medium); 挽臉美容專業人員實務班 (45h, 11800 TWD, Medium); 彩妝實務應用班 (54h, 12820 TWD, Medium); 創意彩妝與視覺傳達實務班 (60h, 14280 TWD, Medium)
- Total hours across top unique courses: 526.0
- Estimated direct course cost: 124930.0
- Learning burden: high

### Dermatologists

- Missing skills: 1
- Missing skills with matched course evidence: 1
- Training coverage ratio over missing skills: 1.0
- Top matched courses: 護膚及淨膚保養品調製實務班 (42h, 11080 TWD, High); 香氛保養品調製與化妝品PIF安全建置實務班 (54h, 10500 TWD, High); 保養品與美容皂配方設計班 (78h, 16000 TWD, High); 美容彩妝護膚技能班 (85h, 20200 TWD, High); 美容護膚彩粧技巧班 (91h, 19000 TWD, High); 化妝保養品成分功效與調製實務基礎班 (30h, 7860 TWD, Medium); 化妝保養品成分功效與調製實務基礎班 (30h, 7860 TWD, Medium); 保養品調製應用班 (47h, 12400 TWD, Medium)
- Total hours across top unique courses: 457.0
- Estimated direct course cost: 104900.0
- Learning burden: medium

## Nursing -> Tech vs Nursing -> Beauty

- Nursing->tech candidate rows: 37; span counts: Partial skill reuse: 32; Major reskilling: 4; High skill reuse: 1; median skill similarity: 0.95.
- Nursing->beauty candidate rows: 12; span counts: Partial skill reuse: 6; Major reskilling: 5; High skill reuse: 1; median skill similarity: 0.973.
- Nursing->beauty market evidence counts: Insufficient public evidence: 7; Strong: 3; Moderate: 2.
- Nursing->beauty training availability counts: Strong: 9; Moderate: 3.

Reusable nursing abilities in beauty paths: client trust, care communication, service orientation, anatomy/skin/body knowledge for skincare or massage-related work, and clinical credibility for medical-aesthetic contexts.

Skills usually needing relearning: hands-on beauty techniques, hair/nail/makeup craft, spa/salon operations, beauty product sales, aesthetic service consultation, and business/retail execution.

Algorithm stress-test finding: global O*NET similarity would naturally favor healthcare-adjacent roles and under-surface low-similarity but low-barrier beauty service paths. Target-domain candidate generation plus training/market evidence is necessary when the user intentionally wants to cross domains.

Suggested method adjustments: keep `skill_similarity` as evidence, not a gate; add a transition-intent mode that can retain low-similarity/low-barrier candidates; require job-level market QA; distinguish High relevance jobs from Medium review candidates; and add Taiwan-specific occupation aliases for domains where O*NET titles do not localize cleanly.

## Limitations

- O*NET is a US occupation taxonomy and may not map cleanly to Taiwan beauty/aesthetic titles.
- TaiwanJobs sample size and occupation labels can miss localized roles, especially medical aesthetics and beauty consulting.
- Training data has course titles but no complete syllabus, so course-skill coverage is potential evidence, not proof that a skill is fully covered.
- This output is not a transition success probability and does not rank final recommendations.
