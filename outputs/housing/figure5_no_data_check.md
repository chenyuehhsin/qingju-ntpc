# Figure 5 No Data Check

Boundary shapefile: `/Users/yuehchen/Desktop/DSLab/1-Hackathon/qingju-ntpc/data/interim/housing/boundaries/nlsc_town_boundary_twd97/TOWN_MOI_1120317.shp`
Benchmark CSV: `/Users/yuehchen/Desktop/DSLab/1-Hackathon/qingju-ntpc/data/processed/housing/moi_independent_suite_rent_benchmark.csv`

## 1. New Taipei Boundary Districts

Count: 29

三峽區, 三芝區, 三重區, 中和區, 五股區, 八里區, 土城區, 坪林區, 平溪區, 新店區, 新莊區, 板橋區, 林口區, 樹林區, 永和區, 汐止區, 泰山區, 淡水區, 深坑區, 烏來區, 瑞芳區, 石碇區, 石門區, 萬里區, 蘆洲區, 貢寮區, 金山區, 雙溪區, 鶯歌區

## 2. New Taipei Districts With MOI Benchmark Data

Count: 20

三峽區, 三芝區, 三重區, 中和區, 五股區, 八里區, 土城區, 新店區, 新莊區, 板橋區, 林口區, 樹林區, 永和區, 汐止區, 泰山區, 淡水區, 深坑區, 萬里區, 蘆洲區, 鶯歌區

## 3. No Data Districts

Count: 9

坪林區, 平溪區, 烏來區, 瑞芳區, 石碇區, 石門區, 貢寮區, 金山區, 雙溪區

## 4. Join Validation

Benchmark districts not found in boundary: None
Join failures for benchmark districts: None
Districts rendered as No Data after join: 坪林區, 平溪區, 烏來區, 瑞芳區, 石碇區, 石門區, 貢寮區, 金山區, 雙溪區

Conclusion: Gray No Data areas come entirely from benchmark missing values, not district-name join failures.