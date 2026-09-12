# Milestone 4A：本機 AWS 整合與部署手冊

目前 **AWS_DEPLOYMENT_BLOCKED**。本次僅完成本機／mock 驗證，沒有建立、查驗或部署任何 AWS resource。以下 --apply 命令須等待使用者確認 AWS 環境與 Deployment Phase 後執行。

## 本機操作

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-aws.txt
.\.venv\Scripts\python.exe scripts/aws/manage.py capabilities
.\.venv\Scripts\python.exe scripts/aws/manage.py validate-kb
.\.venv\Scripts\python.exe scripts/aws/test_local_aws.py
.\.venv\Scripts\python.exe scripts/aws/manage.py package
.\.venv\Scripts\python.exe scripts/aws/manage.py s3
.\.venv\Scripts\python.exe scripts/aws/manage.py cleanup
```

部署命令未加 --apply 時不建立 AWS session、不連網、不修改雲端。package 只產生 .aws/build 容器 context；不 build 或 push。正式網站仍使用 M3 本機引擎。

## AWS_CONFIG_CONTRACT

讀取 process environment，不自動載入 .env，不寫 credentials。

| 變數 | 契約 |
| --- | --- |
| AWS_PROFILE | 使用既有 profile，未設時使用 SDK credential chain |
| AWS_REGION / AWS_DEFAULT_REGION | 前者優先；必須明確指定並確認服務支援 |
| QINGJU_RESOURCE_PREFIX | 預設 qingju-policy-assistant；限制專案前綴 |
| QINGJU_KB_BUCKET | 明確指定全球唯一、qingju-policy-assistant- 開頭的 bucket |
| QINGJU_KB_PREFIX | 預設 knowledge/，僅 manifest 文件與 sidecar |
| QINGJU_KB_ROLE_ARN | 已驗證的 Bedrock KB execution role |
| QINGJU_GATEWAY_ROLE_ARN | 已驗證的 AgentCore Gateway execution role |
| QINGJU_LAMBDA_ROLE_ARN | 已驗證的 Lambda execution role |
| QINGJU_LAMBDA_IMAGE_URI | 同 region ECR image，固定 @sha256: digest |
| QINGJU_KB_ID / QINGJU_GATEWAY_ID | 可選既有 ID，仍驗證名稱／設定／所有權 |

state 位於忽略版控的 .aws/qingju-state.json，綁定 account/region，記錄 ID/ARN/created/fingerprint/ingestion ID。原子寫入與排他 lock；不保存 key/token。中斷後須先确认無程序持有 lock 才人工處理遺留 lock，不可刪 state 繞過設定衝突。

## 部署前置條件

AWS CLI 未找到；boto3/botocore 已在 isolated venv 檢查。credentials、identity、region 可用性、IAM 與配額未驗證。須由帳號管理者提供三個 execution roles 及 ECR repository。

KB role 信任 Bedrock，限讀指定 S3 prefix 並具 Managed KB 必要權限；Gateway role 信任 AgentCore，限指定 KB 的 bedrock:GetKnowledgeBase/bedrock:Retrieve 及 Lambda 的 lambda:InvokeFunction；Lambda role 信任 Lambda 並具必要 CloudWatch Logs 權限。部署者須有相應 create/get/list/tag、S3 寫入、受限 iam:PassRole、MCP 呼叫權限。依當時官方文件確認 trust policy、region 與帳號限制；程式不建立 IAM roles。

## EXACT_NEXT_COMMANDS

環境及部署授權到位後，在分支根目錄依序執行。先替換所有 <...>；逐項檢查 exit code，失敗立即停止。

```powershell
aws --version
# 若使用 IAM Identity Center：
aws sso login --profile <verified-profile>
$env:AWS_PROFILE='<verified-profile>'
$env:AWS_REGION='<verified-region>'
$env:QINGJU_KB_BUCKET='qingju-policy-assistant-<unique-suffix>'
$env:QINGJU_KB_ROLE_ARN='<verified-kb-role-arn>'
$env:QINGJU_GATEWAY_ROLE_ARN='<verified-gateway-role-arn>'
$env:QINGJU_LAMBDA_ROLE_ARN='<verified-lambda-role-arn>'
aws sts get-caller-identity --profile $env:AWS_PROFILE
.\.venv\Scripts\python.exe scripts/aws/manage.py capabilities
.\.venv\Scripts\python.exe scripts/aws/manage.py access --apply
.\.venv\Scripts\python.exe scripts/aws/manage.py validate-kb
.\.venv\Scripts\python.exe scripts/aws/manage.py s3 --apply
.\.venv\Scripts\python.exe scripts/aws/manage.py kb --apply
.\.venv\Scripts\python.exe scripts/aws/manage.py ingest --apply
.\.venv\Scripts\python.exe scripts/aws/manage.py gateway --apply
.\.venv\Scripts\python.exe scripts/aws/manage.py package
$taskEcrRegistry='<account>.dkr.ecr.<region>.amazonaws.com'
$taskEcrRepository='<existing-project-repository>'
$taskImageTag=$taskEcrRegistry+'/'+$taskEcrRepository+':milestone4a'
aws ecr get-login-password --region $env:AWS_REGION | docker login --username AWS --password-stdin $taskEcrRegistry
docker build --platform linux/amd64 -t $taskImageTag .aws/build
# 完成容器檢查後才 push：
docker push $taskImageTag
$taskImageDigest=aws ecr describe-images --repository-name $taskEcrRepository --image-ids imageTag=milestone4a --query 'imageDetails[0].imageDigest' --output text --region $env:AWS_REGION
$env:QINGJU_LAMBDA_IMAGE_URI=$taskEcrRegistry+'/'+$taskEcrRepository+'@'+$taskImageDigest
.\.venv\Scripts\python.exe scripts/aws/manage.py lambda --apply
.\.venv\Scripts\python.exe scripts/aws/manage.py kb-target --apply
.\.venv\Scripts\python.exe scripts/aws/manage.py policy-target --apply
.\.venv\Scripts\python.exe scripts/aws/manage.py test-kb --apply
.\.venv\Scripts\python.exe scripts/aws/manage.py smoke --apply
```

Docker image build、容器啟動與真實 Lambda 相容性尚未驗證；部署前應完成容器驗證。本流程不含 AgentCore Runtime、Bedrock generation 或前端 production switch。

ensure 重用名稱／設定／標籤一致的資源，衝突拒絕覆寫。KB 等 ACTIVE、DS 等 AVAILABLE、Gateway/target 等 READY、Lambda 等 Active；逾時／失敗不視為成功。ingestion 依 manifest hash 重用工作；失敗工作需診斷並經確認後選擇新 retry token/state，本版不自動重啟 failed ingestion。bucket 建立後若 tagging 中斷，須確認所有權並補標籤後重跑，不會任意接管無標籤 bucket。

## SDK、資料與 grounding 邊界

離線檢查 S3、Lambda、Bedrock KB、AgentCore control Gateway、Retrieve、STS。所有 request 依實際 SDK operation/input shape 驗證；詳 AWS_SDK_CAPABILITIES.json。模型支援不代表 region/IAM 可部署。Gateway inline schema 不支援部分 M3 enum／界限／additionalProperties；轉接器將約束保留在 description，Lambda 每次仍由完整 M3 registry schema 驗證。

Managed KB 使用 type=MANAGED、managed embedding，不另建向量資料庫。Gateway connectorId=bedrock-knowledge-bases，僅 enabled Retrieve。若 SDK 缺 API，明確阻擋；先更新 isolated SDK 並重跑能力檢查及測試。仍缺時，由管理者使用支援的新版 AWS CLI／Console 按官方 schema 手動建立，確認名稱、role、tags、綁定後將 ID 交給 ensure 驗證；不猜 API，不用 VECTOR KB 代替。

KB 僅回答方法、定義、來源、限制及時間方法。正式數值、行政區、比較、排序、data period、policy observations 必須使用 Structured Policy Tools。retrieval 驗證 S3 URI 與 manifest hash。grounding validator 檢查結構化 claims 的數值／來源／行政區／status；拒絕任意 free text，未宣稱自然語言完整語義驗證。

官方依據：[KB configuration](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent_KnowledgeBaseConfiguration.html)、[Managed embeddings](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent_ManagedKnowledgeBaseConfiguration.html)、[Gateway target config](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-add-target-api-target-config.html)、[KB connector](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-target-connector-managed-kb.html)。

## 清理

manage.py cleanup 完全離線。cleanup --apply 驗證 identity 後顯示 state 計畫、不刪除。另獲刪除授權後，cleanup --apply --confirm-delete 僅對 state.created=true 且所有權檢查通過的 target／DS／Lambda 發出 leaf 刪除要求，不代表刪除完成。

等待 leaf 完成後，人工確認沒有共用 target／DS，再用 Console 或 CLI 刪除本次建立的 KB/Gateway。S3 bucket/documents、IAM roles、ECR image/repository 均保留，須另行確認保留／費用需求。重複 cleanup 若 leaf 已不存在會停止，需人工核對 state；不自動修改所有權紀錄。dry-run/mock 不是實際清理結果。
