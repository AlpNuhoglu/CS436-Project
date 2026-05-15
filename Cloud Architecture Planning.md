# Cloud Architecture Planning: Ders Forumu

## System Context
**Project:** A course and professor review platform for Sabancı University students.
**Current Stack:** * Frontend: React (Vite + TS)
* Backend: FastAPI (Python)
* Database: PostgreSQL (SQLAlchemy + Alembic)
* Auth: Dual-mode (AWS Cognito for Production, Local/OTP for Dev)
* Deployment: Currently running via Docker Compose.

**Instructions for the AI:** Please read through the following architectural categories based on our university grading rubric. Answer each question sequentially, providing specific AWS service recommendations, configurations, and justifications to maximize System Design Complexity (30%) and Cloud Service Usage (30%). Do not sacrifice critical system characteristics just to add complexity.

---

## 1. End Goal & Building Blocks
* **Q1.1:** How should we clarify the end goal of moving from Docker Compose to AWS?
* **AI Answer:**
    * **Migration objective.** Today "Ders Forumu" runs as a single-host Docker Compose stack (FastAPI + PostgreSQL + a React dev/build artifact + an inline scraper + an SMTP-based OTP path). This is a *single point of failure*: one EC2 (or laptop) reboot, disk failure, or noisy-neighbor event takes the entire service offline for all ~5,000 Sabancı University students. The end goal of the AWS migration is to convert the monolith into a **horizontally scalable, multi-AZ, managed-service architecture** where every tier (edge, compute, data, auth, mail, scheduled jobs) is independently deployable, observable, and failure-isolated.
    * **Concrete success criteria for SU students.**
        * **High Availability (HA):** 99.9% monthly availability target. No single AZ failure can take the platform down during midterms/finals or course-registration week (peak load). This is achieved with ECS Fargate tasks spread across **eu-central-1a, eu-central-1b, eu-central-1c** behind an Application Load Balancer (ALB), and Aurora PostgreSQL Multi-AZ with automatic failover (RTO ≈ 30–60 s).
        * **Durability:** Student reviews are durable to 99.999999999% (11 9s) — Aurora storage replicates 6 copies across 3 AZs; daily automated snapshots + point-in-time recovery (PITR) up to 35 days; S3 (for static frontend + log archives) provides equivalent durability.
        * **Elasticity:** During Week 1 of a semester (when the scraper repopulates courses *and* students rush to read reviews), the API tier auto-scales horizontally rather than thrashing a single VM.
        * **Security posture:** Move secrets out of `.env` into AWS Secrets Manager / Parameter Store, enforce TLS end-to-end with ACM, and put WAF + Shield in front of the public surface so that the public `@sabanciuniv.edu`-restricted registration endpoint is not abusable.
        * **Operational maturity:** Centralized CloudWatch logs/metrics, alarms with SNS notifications, blue/green deploys via ECS, and reproducible infrastructure (Terraform/CDK).
    * **What "done" looks like.** A student in Tuzla on campus Wi-Fi opens `dersforumu.com`, the React SPA is delivered from a CloudFront edge in Istanbul/Frankfurt in <100 ms; an authenticated API call goes to ALB → ECS Fargate → Aurora reader in <200 ms p95; an OTP email arrives via SES in <5 s; and if one AZ in eu-central-1 fails, none of the above changes from the student's perspective.

* **Q1.2:** What are the main building blocks needed to make this a robust, cloud-native system?
* **AI Answer:**
    * **Edge / Delivery tier.**
        * **Amazon CloudFront** — global CDN fronting both the React SPA (S3 origin) and the API (ALB origin under `/api/*`), with HTTP/2 + HTTP/3 (QUIC), Brotli/gzip compression, and edge caching for static assets.
        * **AWS WAF v2** attached to CloudFront with AWS-managed rule groups (Core Rule Set, Known Bad Inputs, SQLi, Linux, Amazon IP Reputation) plus a custom rate-based rule for `/auth/*`.
        * **AWS Shield Standard** (free, always-on, L3/L4 DDoS).
        * **Amazon Route 53** — public hosted zone for `dersforumu.com`, alias records pointing to CloudFront; health-check-based DNS failover for the API hostname.
        * **AWS Certificate Manager (ACM)** — public TLS certs for CloudFront (us-east-1) and ALB (eu-central-1), auto-renewed.
    * **Compute tier.**
        * **Amazon ECS on AWS Fargate** — runs the FastAPI backend container (no EC2 to patch). One ECS service, multiple tasks across AZs, target-tracking auto-scaling on CPU and ALBRequestCountPerTarget.
        * **Amazon ECR** — private container registry for the FastAPI image and the scraper image.
        * **Application Load Balancer (ALB)** — L7, path-based routing, health checks on `GET /health`, integrated with WAF and ACM.
        * **EventBridge Scheduler + ECS RunTask (Fargate)** — runs the SUIS scraper as a one-shot Fargate task on a cron schedule (e.g., start of each semester + weekly refresh). Chosen specifically to avoid Lambda's 15-minute timeout ceiling.
    * **Data tier.**
        * **Amazon Aurora PostgreSQL (Multi-AZ, PostgreSQL-compatible)** — primary writer + 1–2 reader replicas, 6-way storage replication across 3 AZs, automated backups, PITR, performance insights.
        * **Amazon ElastiCache for Redis (cluster mode disabled, Multi-AZ with automatic failover)** — used for OTP storage (TTL = 5 minutes), session caching, sliding-window rate-limit counters for `/auth/*`, and short-lived caches of "top courses" and `/stats`.
        * **Amazon S3** — three buckets: `dersforumu-frontend` (React build artifacts, private, CloudFront-OAC fronted), `dersforumu-logs` (ALB + WAF logs, lifecycle to Glacier), `dersforumu-backups` (DB exports).
    * **Identity & Mail.**
        * **Amazon Cognito User Pools** — production auth, RS256 JWT validated by FastAPI via JWKS. Pre-sign-up Lambda trigger enforces `@sabanciuniv.edu`.
        * **Amazon SES** — replaces ad-hoc SMTP for OTP and password-reset emails. DKIM/SPF/DMARC on `dersforumu.com`.
    * **Configuration & Secrets.**
        * **AWS Secrets Manager** — DB master credentials (with rotation), JWT signing secret, SES SMTP creds (for fallback), third-party API keys.
        * **AWS Systems Manager Parameter Store** — non-sensitive runtime config (feature flags, Cognito Pool/Client IDs, log levels).
    * **Networking.**
        * **Amazon VPC** with public subnets (ALB, NAT GW), private app subnets (ECS tasks, Lambda), private data subnets (Aurora, ElastiCache), Internet Gateway, NAT Gateway, VPC endpoints for S3/ECR/Secrets Manager/CloudWatch Logs to keep traffic off the public internet.
        * **AWS Systems Manager Session Manager** — replaces a bastion host for break-glass shell access (no SSH keys, no inbound 22).
    * **Observability.**
        * **CloudWatch Logs** (structured JSON from FastAPI), **CloudWatch Metrics** + **Container Insights**, **CloudWatch Alarms**, **AWS X-Ray** for distributed tracing, **SNS** for alarm fan-out to email/SMS, **AWS Health Dashboard** events.
    * **CI/CD & IaC.**
        * **AWS CodePipeline + CodeBuild** (or GitHub Actions with OIDC into IAM) — build → ECR push → ECS blue/green deploy via CodeDeploy.
        * **Terraform or AWS CDK** for reproducible infrastructure.

---

## 2. Compute Resources
* **Q2.1:** Should we use Virtual Machines (EC2) or Containers (ECS/EKS) for the React frontend and FastAPI backend?
* **AI Answer:**
    * **React frontend — neither EC2 nor ECS. Use S3 + CloudFront.**
        * The React app is a Vite-built static bundle (`index.html`, hashed JS/CSS, images). There is no server-side rendering. Running it on EC2 or in a container behind a load balancer would mean paying for idle compute to serve static files — strictly inferior to S3 + CloudFront on cost, latency, and HA.
        * **Configuration:** Build artifacts uploaded to an S3 bucket (`dersforumu-frontend`, Block Public Access ON), exposed only through CloudFront via **Origin Access Control (OAC)**. CloudFront caches with long TTLs on hashed assets and a short TTL on `index.html` so deploys are visible within seconds.
    * **FastAPI backend — ECS on AWS Fargate (not EC2, not EKS).**
        * **EC2 rejected:** the team would have to manage AMIs, patching, autoscaling groups, user-data scripts, Docker daemon, log shipping, and capacity headroom. For a 5,000-user university app, that operational tax is not justifiable.
        * **EKS rejected:** Kubernetes is overkill for one backend service + one scheduled job. EKS adds a $73/month control-plane fee per cluster, a steep operational learning curve (CNI, IRSA, cluster upgrades), and no benefit at this scale.
        * **ECS Fargate chosen because:**
            1. The existing Dockerfile (multi-stage, non-root `appuser`, exposes 8000, `start.sh` runs `alembic upgrade head` then Uvicorn) drops straight into a Fargate task definition with **zero refactor**.
            2. No servers to patch; AWS manages the underlying Firecracker VMs.
            3. Native integration with ALB, IAM task roles, Secrets Manager (injected as env vars), CloudWatch Logs (`awslogs` driver), and ECR.
            4. Per-second billing and right-sized vCPU/memory tuples — cheap at low traffic, scales out cleanly during peak.
            5. Tasks are placed across multiple AZs by ECS automatically, which is exactly what the HA requirement needs.

* **Q2.2:** How many compute instances are required, and what should their specs (CPU, RAM) be?
* **AI Answer:**
    * **FastAPI backend (ECS Fargate service `dersforumu-api`):**
        * **Task size:** 1 vCPU, 2 GB RAM per task (Fargate `cpu=1024`, `memory=2048`). FastAPI + SQLAlchemy + a Uvicorn worker pool (2 workers per task, `--workers 2`) comfortably fits.
        * **Desired count (baseline):** **3 tasks**, one per AZ (eu-central-1a/1b/1c). This satisfies "minimum 2 healthy in any single-AZ outage" and gives N+1 headroom.
        * **Auto Scaling policy:**
            * Target tracking on `ECSServiceAverageCPUUtilization` = 60%.
            * Target tracking on `ALBRequestCountPerTarget` = 200 req/min/task.
            * **Min = 3, Max = 12 tasks.** Peak (course registration day) load is modeled at ~50 RPS sustained, ~200 RPS bursts; 12 tasks × ~50 RPS each easily covers it.
        * **Deployment:** rolling with `minimumHealthyPercent=100`, `maximumPercent=200`, ECS circuit breaker enabled for auto-rollback.
    * **SUIS Scraper (ECS Fargate task `dersforumu-scraper`, scheduled, not a service):**
        * **Task size:** 0.5 vCPU, 1 GB RAM (`cpu=512`, `memory=1024`). The bottleneck is the 1.5-second sleep between SUIS HTTP calls, not CPU.
        * **Invocations:** 1 task per scheduled run; runs for 5–15 minutes and exits.
    * **Frontend:** N/A — S3 + CloudFront, no compute instances.
    * **Aurora PostgreSQL:**
        * **Writer:** `db.r6g.large` (2 vCPU, 16 GB RAM) — Graviton2, generous buffer cache for ~5k users / mostly-read workload.
        * **Reader:** 1 × `db.r6g.large` in a different AZ (can scale to 2 if `/stats` and `/search` get heavy).
    * **ElastiCache Redis:**
        * `cache.t4g.small` (2 vCPU, 1.37 GB) primary + 1 replica in another AZ, Multi-AZ with automatic failover. Plenty for OTP TTL keys and rate-limit counters.
    * **NAT Gateway:** 1 per AZ for HA (2 minimum recommended), AWS-managed.

* **Q2.3:** Is it worth using serverless functions (AWS Lambda) for specific tasks, such as the profanity filter or the SU course scraper?
* **AI Answer:**
    * **Profanity Filter — keep inline inside the FastAPI container. Do NOT move to Lambda.**
        * **Why:** It is a pure-Python, CPU-cheap, *synchronous* function on the review-creation hot path (`POST /reviews`). It normalizes Turkish/leet-speak and regex-matches a static word list — sub-millisecond per call.
        * **Lambda would hurt, not help:**
            * Adds a network hop (FastAPI → Lambda Invoke → response), 5–30 ms of added latency per review.
            * Cold-start risk on a function that's invoked sporadically (a few reviews/minute) → first-write-of-the-hour penalty for a student.
            * Extra IAM, packaging, and deployment surface for ~50 lines of Python.
            * The word list lives next to the code; coupling it to a separate deployable creates drift.
        * **Verdict:** It belongs as a module (`app/utils/profanity.py`) inside the API. If the word list grows large or needs ML-based classification later, that's the moment to reconsider (e.g., SageMaker endpoint or Comprehend Custom Classifier), not now.
    * **SUIS Scraper — do NOT use Lambda. Use EventBridge Scheduler → ECS RunTask on Fargate.**
        * **Why Lambda is the wrong fit:**
            * **Timeout ceiling.** Lambda's hard maximum is **15 minutes**. The scraper's *typical* runtime is 5–15 minutes — *exactly* at the ceiling. Any SUIS slowdown, retry, or extra semester load pushes it over and the job is killed mid-write, leaving partial state in PostgreSQL. That's not acceptable for a course catalog that the entire app reads from.
            * **/tmp + memory limits** (10 GB / 10 GB) aren't an issue today but bake in fragility.
            * **VPC ENI cold-start.** A Lambda inside the VPC (required to talk to Aurora privately) adds noticeable cold-start time.
            * **DB connection model.** A long-running scraper holds a SQLAlchemy session, runs sequential writes, and benefits from a persistent connection — Lambda's per-invocation model fights this (or forces RDS Proxy).
        * **Recommended pattern:**
            1. Build the scraper image (`suis_scraper.py` as the ENTRYPOINT) and push to ECR.
            2. Define a separate ECS task definition `dersforumu-scraper` (0.5 vCPU, 1 GB, same VPC/subnets as the API).
            3. **EventBridge Scheduler** rule (e.g., `cron(0 3 1 1,2,6,9 ? *)` — 03:00 UTC on the 1st of January/February/June/September, plus a weekly `cron(0 4 ? * SUN *)` refresh) with target `ECS RunTask` (LaunchType=FARGATE), passing the cluster, task def, subnets, and security group.
            4. Task pulls SUIS creds from Secrets Manager, writes directly to Aurora over the private subnet, emits logs to CloudWatch, exits 0 on success.
            5. CloudWatch Alarm on `ECS TaskExitCode != 0` → SNS → email to the dev team.
        * **Net result:** No 15-minute cliff, full container runtime, identical Python environment to local development, and a clean separation between online API and batch ingest.
    * **Where Lambda *does* earn its place in this architecture:**
        * **Cognito Pre-Sign-Up Lambda trigger** — validates the email ends with `@sabanciuniv.edu` and rejects otherwise. Sub-second, event-driven, perfect Lambda use case.
        * **S3 → Lambda for deployment cache invalidation** — when a new frontend bundle is uploaded, a tiny Lambda issues a `CreateInvalidation` against CloudFront for `/index.html`.
        * **CloudWatch Logs subscription Lambda** — optional: forward structured errors to a Slack webhook.

---

## 3. Storage
* **Q3.1:** Which storage type best fits our needs for the PostgreSQL database (e.g., RDS, Aurora) and why?
* **AI Answer:**
    * **Recommendation: Amazon Aurora PostgreSQL (PostgreSQL-compatible, Multi-AZ cluster).**
    * **Workload profile.** Ders Forumu is **read-heavy** (browsing courses, professors, reviews, search, `/stats`) with bursty writes (review submissions, OTP records, scraper batch inserts). Aurora's separation of compute and storage and its native read-replica fan-out is an exact fit.
    * **Aurora vs. RDS PostgreSQL — why Aurora wins here:**
        | Dimension | RDS PostgreSQL Multi-AZ | **Aurora PostgreSQL** |
        |---|---|---|
        | Replication | Synchronous to *one* standby (not readable) | 6-way replication across 3 AZs at the storage layer; up to 15 readable replicas |
        | Failover RTO | 60–120 s | **~30 s** (DNS endpoint flip) |
        | Read scaling | Manual read replicas, async | Native reader endpoint, sub-100 ms replica lag |
        | Storage | Provisioned EBS (must pre-size) | **Auto-grows** in 10 GB increments up to 128 TiB |
        | Backups | Snapshot-based | Continuous, PITR to the second |
        | Cost | ~20% cheaper at small size | Slightly higher per-hour, but no idle replica waste |
    * **Cluster topology:**
        * Writer: `db.r6g.large` in eu-central-1a (private data subnet).
        * Reader: `db.r6g.large` in eu-central-1b (private data subnet) — serves `GET /professors`, `GET /courses`, `GET /search`, `GET /stats` via a read-only SQLAlchemy engine.
        * **Aurora endpoints:** writer endpoint for `POST` paths, reader endpoint for `GET` paths.
        * **Backup retention:** 14 days automated + PITR; manual snapshots before each Alembic migration.
        * **Encryption:** at rest with KMS CMK; in transit with TLS (`sslmode=require`).
        * **Performance Insights** + **Enhanced Monitoring** enabled.
        * **Parameter group** tuned: `max_connections` ~ 200 (or use RDS Proxy if connection storms appear), `log_min_duration_statement=500ms`.
        * **Alembic migrations:** keep `alembic upgrade head` in `start.sh`, but guarded by an advisory lock so only one ECS task migrates at deploy time.
    * **Cost guardrail:** If budget is tight, start with **Aurora Serverless v2** (`0.5–4 ACU`) — it scales to near-zero between class registration peaks and ramps up in seconds during exam week.

* **Q3.2:** How should we handle static file storage (e.g., React build files) and do we expect high read/write disk speeds?
* **AI Answer:**
    * **Static React build files → Amazon S3 + Amazon CloudFront.**
        * **Bucket:** `dersforumu-frontend`, region `eu-central-1`, versioning **on**, Block Public Access **on**.
        * **Access path:** CloudFront distribution with **Origin Access Control (OAC)** signs requests to S3 — the bucket is never public.
        * **Cache behavior:**
            * `/index.html` → `Cache-Control: no-cache, must-revalidate` so new deploys are picked up immediately.
            * `/assets/*.[hash].js|css|svg|png` → `Cache-Control: public, max-age=31536000, immutable` (hashed filenames make this safe).
            * **Compression:** Brotli + gzip automatic at the edge.
            * **HTTP versions:** HTTP/2 and HTTP/3 (QUIC) enabled.
        * **SPA routing:** custom error response 403/404 → `/index.html` (200) so React Router deep links work.
        * **Deploy flow:** CI builds Vite bundle → `aws s3 sync` → Lambda invalidates `/index.html` on CloudFront.
    * **Logs and backups → S3 with lifecycle policies.**
        * `dersforumu-logs` for ALB access logs, WAF logs (via Kinesis Firehose), CloudFront standard logs. Lifecycle: Standard → Standard-IA (30 d) → Glacier Deep Archive (180 d) → expire (730 d).
        * `dersforumu-backups` for manual DB exports.
    * **Do we need EBS or EFS?**
        * **EBS:** Not needed by the application tier — Fargate tasks are stateless. Aurora uses its own distributed storage (not EBS). The only EBS in play is the Aurora cluster volume itself, which is managed for us.
        * **EFS:** Not needed. There is no shared-filesystem requirement between containers. User-uploaded files (none in current scope — no avatar uploads, no attachments) would go to S3 if they were ever added, not EFS.
        * **High disk IOPS?** The workload is **OLTP with small rows** (reviews are short text) — Aurora's default storage IOPS (auto-scaled) is more than sufficient. No need for `io2` Block Express or similar.

---

## 4. Network
* **Q4.1:** Is low latency a requirement, and how do we handle high bandwidth usage for students accessing the site?
* **AI Answer:**
    * **Latency profile.** The audience is geographically concentrated in **Istanbul (Tuzla campus)**, so most clients are in Turkey on home/campus broadband or 4G/5G. The user-perceived target:
        * **Static asset TTFB:** < 50 ms (CDN-served).
        * **API p50:** < 150 ms, **p95:** < 400 ms, **p99:** < 1 s.
        * Anything over ~1 s on review browsing will feel sluggish during exam week.
    * **Region choice: `eu-central-1` (Frankfurt).**
        * RTT from Istanbul to Frankfurt is typically **35–50 ms** — the lowest of all generally-available AWS regions for Turkey today.
        * The newer Istanbul-region (`eu-south-2` Spain / future TR Local Zones) can be considered when GA, but Frankfurt remains the practical default with the broadest service coverage (Aurora, Fargate, Cognito, SES, etc.).
    * **CloudFront strategy.**
        * Distribution price class **PriceClass_100 → PriceClass_All** (we want the Istanbul, Sofia, and Bucharest POPs). Istanbul has an AWS edge presence, so SU students hit a CDN node within ~10–20 ms.
        * Static assets served from edge → near-zero origin bandwidth cost.
        * **API behind CloudFront** (`/api/*` behavior, origin = ALB):
            * Caching disabled for authenticated calls (`Authorization` header forwarded, all cookies forwarded, TTL=0).
            * But we still benefit from **TLS termination at the edge**, TCP/QUIC connection reuse, AWS backbone routing from edge → origin (lower jitter than public internet), and WAF at the edge.
        * **Compression** (Brotli/gzip) on JSON responses cuts review-list payload size ~70%.
    * **Bandwidth handling.**
        * 5,000 students × ~5 MB initial bundle (cached after first load) = ~25 GB cold-cache day; subsequent loads are tens of KB. CloudFront absorbs this.
        * Origin egress (ALB → CloudFront) is **free** within AWS network; CloudFront → internet is metered but ~$0.085/GB in EU edges.

* **Q4.2:** How will we ensure network security? Please specify the configuration of Security Groups, Public/Private Subnets, Internet Gateways (IGW) vs. NAT Gateways, and Access Control Lists (ACLs).
* **AI Answer:**
    * **VPC layout — `dersforumu-vpc`, CIDR `10.20.0.0/16`, 3 AZs (eu-central-1a/1b/1c):**
        | Tier | Subnet | AZ | CIDR | Routes |
        |---|---|---|---|---|
        | Public | `public-1a` | 1a | `10.20.0.0/24` | `0.0.0.0/0 → IGW` |
        | Public | `public-1b` | 1b | `10.20.1.0/24` | `0.0.0.0/0 → IGW` |
        | Public | `public-1c` | 1c | `10.20.2.0/24` | `0.0.0.0/0 → IGW` |
        | Private App | `app-1a` | 1a | `10.20.10.0/24` | `0.0.0.0/0 → NAT-1a` |
        | Private App | `app-1b` | 1b | `10.20.11.0/24` | `0.0.0.0/0 → NAT-1b` |
        | Private App | `app-1c` | 1c | `10.20.12.0/24` | `0.0.0.0/0 → NAT-1c` |
        | Private Data | `data-1a` | 1a | `10.20.20.0/24` | local only |
        | Private Data | `data-1b` | 1b | `10.20.21.0/24` | local only |
        | Private Data | `data-1c` | 1c | `10.20.22.0/24` | local only |
    * **Gateways:**
        * **1 Internet Gateway** attached to the VPC — only public subnets route through it.
        * **NAT Gateway per AZ** (3 total for full HA, or 2 as a cost compromise) in the public subnets — gives private subnets outbound-only access to SES, SUIS HTTP endpoints, Cognito public endpoints, package mirrors.
        * **VPC Endpoints (PrivateLink/Gateway)** to keep east-west AWS traffic off the internet and reduce NAT cost: `com.amazonaws.eu-central-1.s3` (gateway), `ecr.api`, `ecr.dkr`, `logs`, `secretsmanager`, `ssm`, `ssmmessages`, `ec2messages`, `monitoring` (interface).
    * **Security Groups (stateful, default-deny inbound):**
        * `sg-alb` — **ALB**: inbound 443 from `0.0.0.0/0` and `::/0`; inbound 80 from `0.0.0.0/0` (redirect to 443); outbound to `sg-api` on 8000.
        * `sg-api` — **ECS Fargate API tasks + scraper task**: inbound 8000 from `sg-alb` only; outbound 443 to `0.0.0.0/0` (via NAT) for SES/Cognito/SUIS; outbound 5432 to `sg-db`; outbound 6379 to `sg-redis`.
        * `sg-db` — **Aurora**: inbound 5432 from `sg-api` only. No other source. No public endpoint.
        * `sg-redis` — **ElastiCache**: inbound 6379 from `sg-api` only.
        * `sg-endpoints` — **VPC Interface Endpoints**: inbound 443 from `sg-api`.
        * No security group allows inbound from `0.0.0.0/0` except `sg-alb` on 443 (and `sg-alb` 80 → redirect).
    * **Network ACLs (stateless, defense in depth):**
        * Public subnets: allow 80/443 inbound from `0.0.0.0/0`, allow ephemeral (1024–65535) outbound; deny known-bad CIDRs if needed.
        * Private app subnets: allow ephemeral inbound from VPC CIDR, allow 443/5432/6379 outbound to VPC CIDR.
        * Private data subnets: allow only 5432/6379 inbound from `10.20.10.0/22` (app range); deny all else.
    * **Administrative access:**
        * **No bastion EC2.** Use **AWS Systems Manager Session Manager** for shell access into ECS tasks (`aws ecs execute-command`) and into any maintenance EC2 — no inbound SSH port, no key pairs, full IAM auditing in CloudTrail.
    * **Encryption everywhere:**
        * Client → CloudFront: TLS 1.2+ via ACM.
        * CloudFront → ALB: TLS 1.2+ via ACM (custom origin).
        * ALB → ECS: HTTP within the VPC is acceptable, or upgrade to TLS with a self-signed cert if mandated.
        * ECS → Aurora: TLS (`sslmode=require`), KMS-encrypted at rest.
        * ECS → Redis: in-transit encryption + auth token from Secrets Manager.

---

## 5. Security
* **Q5.1:** Based on common web attack types (e.g., DDoS, SQLi, unauthorized registration), what specific AWS security measures should be implemented?
* **AI Answer:**
    * **DDoS — AWS Shield Standard (always-on, free) + Shield Advanced (optional).**
        * Shield Standard automatically protects CloudFront, Route 53, and ALB against common L3/L4 floods (SYN, UDP reflection).
        * Shield Advanced ($3,000/mo) is **not justified** for a 5k-user university app, but can be enabled around exam season if needed — provides 24/7 DRT support and cost protection.
    * **SQL injection / XSS / OWASP Top 10 — AWS WAF v2 on CloudFront.**
        * Attached **managed rule groups:** `AWSManagedRulesCommonRuleSet`, `AWSManagedRulesKnownBadInputsRuleSet`, `AWSManagedRulesSQLiRuleSet`, `AWSManagedRulesAmazonIpReputationList`, `AWSManagedRulesAnonymousIpList`, `AWSManagedRulesLinuxRuleSet`.
        * **Custom rules:**
            * Rate-based rule: **100 requests / 5 min / IP** on `/auth/*` paths → block 15 minutes. This caps OTP brute force at the edge before it hits the API.
            * Geo-match rule: optionally restrict to TR + a small allowlist (DE, US for ops) — easy to relax for traveling students.
            * Size-constraint rule: reject `POST /reviews` bodies > 8 KB.
        * Application layer also uses **SQLAlchemy parameterized queries** (already the case) — defense in depth.
        * **XSS:** React auto-escapes; in addition, set CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy via CloudFront Response Headers Policy.
    * **Unauthorized registration (non-SU emails) — multi-layer enforcement.**
        1. **Cognito Pre-Sign-Up Lambda trigger** rejects any email not matching `^[^@]+@sabanciuniv\.edu$`. This is the authoritative gate.
        2. **FastAPI `/auth/register`** validates the same regex before issuing OTP (cheap, also prevents OTP/SES spend on garbage addresses).
        3. **SES configuration set** with a suppression list to drop bounced/complained addresses.
        4. **WAF rate limit** on `/auth/register` (e.g., 5/min/IP).
    * **Brute-force OTP — defense in depth.**
        * **ElastiCache Redis** stores `otp:{email}` with `EX 300` (5 min TTL) and an attempt counter `otp_attempts:{email}` capped at 5 → forced regeneration.
        * **Application-level lockout** (already present in code) — keep it.
        * **WAF rate-based rule** on `/auth/verify-otp` and `/auth/login` (e.g., 20/min/IP).
        * **CloudWatch alarm** on a custom metric `OTPVerifyFailures > 50 / 5 min` → SNS to ops.
    * **Other hardening:**
        * Cognito with **MFA optional/required for admin pool**, password policy ≥ 10 chars + complexity.
        * **JWT validation** with RS256 + JWKS caching (already in code) — keep, and rotate JWKS-derived keys via Cognito.
        * **CSRF:** SPA uses Authorization header (Bearer JWT), not cookies — CSRF risk is low.
        * **Dependency scanning:** ECR image scanning (Inspector v2) + GitHub Dependabot.
        * **CloudTrail** enabled in all regions; logs to a dedicated S3 bucket with Object Lock for tamper-evidence.
        * **GuardDuty** turned on — anomaly detection on VPC flow logs, DNS, CloudTrail.
        * **AWS Config** to detect drift (e.g., a security group accidentally opened to 0.0.0.0/0).

* **Q5.2:** How should we secure our environment variables, DB credentials, and Cognito configurations?
* **AI Answer:**
    * **Goal:** Eliminate the current `.env` file from production entirely. The ECS task should boot with zero plaintext secrets baked into the image and zero secrets in the task definition's `environment` block.
    * **AWS Secrets Manager (rotated, encrypted with a customer KMS key `kms/dersforumu`):**
        * `dersforumu/db/master` — Aurora master user + password, **rotation enabled** every 30 days via the AWS-provided Lambda rotation template.
        * `dersforumu/jwt/secret` — JWT signing key (for the local OTP/dev path; in production RS256 keys are managed by Cognito).
        * `dersforumu/ses/smtp` — SES SMTP credentials (if using SMTP interface; with the API it's just an IAM permission on the task role).
        * `dersforumu/cognito/client` — Cognito App Client secret (if confidential client).
        * `dersforumu/redis/authtoken` — ElastiCache auth token.
        * `dersforumu/suis/credentials` — SUIS scraper login credentials.
    * **AWS Systems Manager Parameter Store (free for Standard tier):**
        * `/dersforumu/cognito/user_pool_id` (String)
        * `/dersforumu/cognito/client_id` (String)
        * `/dersforumu/cognito/region` (String)
        * `/dersforumu/log_level` (String)
        * `/dersforumu/feature_flags/*` (String, hot-reloadable)
    * **Injection into ECS Fargate task:**
        * The ECS task definition references secrets via the `secrets` field (not `environment`):
            ```json
            "secrets": [
              {"name": "DATABASE_URL", "valueFrom": "arn:aws:secretsmanager:...:dersforumu/db/master:url::"},
              {"name": "JWT_SECRET",  "valueFrom": "arn:aws:secretsmanager:...:dersforumu/jwt/secret:value::"}
            ]
            ```
        * ECS resolves these at task start and exposes them as environment variables — they never appear in `docker inspect`, console UI, or CloudTrail values.
    * **IAM roles (least privilege):**
        * **Task execution role** (`ecsTaskExecutionRole-dersforumu`): permission to pull from ECR, write to CloudWatch Logs, read the *specific* Secrets Manager ARNs above, and `kms:Decrypt` on the CMK.
        * **Task role** (`ecsTaskRole-dersforumu-api`): the runtime IAM identity inside the container — permission to `ses:SendEmail` on `*@dersforumu.com` only, `cognito-idp:AdminInitiateAuth` on the specific pool, `elasticache:Connect` (if using IAM auth), and nothing else.
        * **Scraper task role:** read SUIS secret, write to Aurora (via DB user, not IAM), put logs.
        * **EventBridge Scheduler role:** `ecs:RunTask` + `iam:PassRole` on the scraper roles only.
    * **No hardcoded credentials anywhere:**
        * `.env` is `.gitignore`d and only used for local Docker Compose dev.
        * CI/CD uses **GitHub Actions OIDC → IAM role** (no long-lived AWS keys in GitHub secrets).
        * **`git-secrets` / `gitleaks`** pre-commit hook to catch accidental leaks.
    * **Rotation & audit:**
        * Secrets Manager rotation logs to CloudTrail.
        * `iam-credential-report` reviewed monthly.
        * KMS key has a key policy that only the task execution role + ops admins can `Decrypt`.

---

## 6. Service Availability
* **Q6.1:** How should the system be designed to ensure it is highly available, durable, and always accessible? (Detail any Multi-AZ or Load Balancing strategies).
* **AI Answer:**
    * **Target SLO.** 99.9% monthly availability (≤ 43 min downtime/month), zero data loss tolerance for committed reviews (RPO = 0 for the writer, RPO ≤ 1 s via PITR).
    * **Multi-AZ everywhere:**
        * **ECS Fargate API service:** desired count = 3 (one per AZ), `placement_strategy=spread` on `attribute:ecs.availability-zone`. Loss of one AZ → 2 tasks still serve traffic, and auto-scaling launches replacements in the surviving AZs within ~30 s.
        * **Aurora PostgreSQL:** writer in AZ-a, reader in AZ-b. Storage layer replicates 6 ways across 3 AZs by default. Failover: Aurora promotes the reader and flips the writer endpoint DNS within ~30 s.
        * **ElastiCache Redis:** primary + replica in different AZs, automatic failover on.
        * **NAT Gateways:** one per AZ so a single-AZ NAT failure doesn't blackhole egress.
        * **ALB:** AZ-aware, registered with subnets in all 3 AZs; cross-zone load balancing **on**.
    * **Load balancing strategy:**
        * **CloudFront** is the global front door — it itself is multi-region by design.
        * **ALB** with:
            * Listeners: 80 (redirect → 443), 443 (HTTPS, ACM cert, TLS 1.2+).
            * Target group `tg-api` over HTTP 8000 with health check `GET /health`, healthy threshold 2, unhealthy threshold 2, interval 15 s, timeout 5 s.
            * **Deregistration delay** 30 s (graceful drain on rolling deploys).
            * **Stickiness off** — FastAPI is stateless (sessions live in Redis/JWT), so any task can serve any request.
    * **Auto Scaling:**
        * **ECS Service Auto Scaling** with two target-tracking policies (CPU 60%, ALBRequestCountPerTarget 200/min), min 3 / max 12.
        * **Scheduled scaling** to pre-warm to 6 tasks at 08:00 TR time on add/drop days.
        * **Aurora Auto Scaling** for read replicas (target ~70% reader CPU, min 1 / max 4) — only enabled if `/stats` and `/search` become hot.
    * **Read scaling pattern:**
        * SQLAlchemy uses **two engines** — `engine_writer` → Aurora writer endpoint (for `POST/PUT/DELETE`), `engine_reader` → Aurora reader endpoint (for `GET`). Implemented via a small session router.
        * Cacheable `GET /stats` and `GET /professors` (popular ones) are wrapped in a 60-second Redis cache.
    * **Durability mechanisms:**
        * Aurora: 6-copy / 3-AZ replication, continuous backup to S3, 14-day PITR, daily snapshots (35-day retention), cross-region snapshot copy weekly to `eu-west-1` (DR).
        * S3 frontend bucket: versioning on, MFA-delete on production bucket.
        * CloudTrail logs: S3 Object Lock (governance mode, 365 d) — tamper-evident audit trail.
    * **Disaster recovery posture:**
        * **In-region failure (AZ):** automatic, sub-minute, transparent to students.
        * **Region failure:** RPO ≈ 1 hour (last cross-region snapshot), RTO ≈ 2 hours via Terraform re-apply in `eu-west-1` and snapshot restore. Documented runbook.
    * **Deployment safety:**
        * ECS blue/green via CodeDeploy: 10% canary for 5 min → 100%. Auto-rollback on ALB 5xx alarm.
        * Alembic migrations gated by an advisory lock and run **before** new tasks become healthy; backwards-compatible migrations only (expand/contract pattern).

---

## 7. Monitoring & Notifications
* **Q7.1:** How will we set up the system to ensure there is nothing wrong at runtime? Which tools will handle logging and metrics?
* **AI Answer:**
    * **Logging — Amazon CloudWatch Logs (structured JSON).**
        * Log groups:
            * `/ecs/dersforumu-api` — FastAPI app logs (one stream per task), retention 30 days.
            * `/ecs/dersforumu-scraper` — scraper logs, retention 90 days.
            * `/aws/rds/cluster/dersforumu/postgresql` — Aurora slow query + error logs.
            * `/aws/applicationelb/dersforumu` — ALB access logs (also mirrored to S3).
            * `/aws/wafv2/dersforumu` — WAF sampled/blocked requests via Kinesis Firehose → S3 + CloudWatch.
            * `/aws/cloudfront/dersforumu` — CloudFront real-time logs (optional, sampled).
        * FastAPI emits **structured JSON** (`request_id`, `user_id`, `route`, `latency_ms`, `status`) so CloudWatch Logs Insights queries are trivial: `fields @timestamp, route, latency_ms | filter status >= 500 | sort latency_ms desc`.
        * Long-term archive: S3 with lifecycle to Glacier; queryable via Athena.
    * **Metrics — CloudWatch Metrics + Container Insights.**
        * **Container Insights** on the ECS cluster gives per-task CPU, memory, network, disk, task counts.
        * **ALB metrics:** `RequestCount`, `TargetResponseTime` (p50/p90/p99), `HTTPCode_Target_5XX_Count`, `UnHealthyHostCount`.
        * **Aurora metrics:** `CPUUtilization`, `DatabaseConnections`, `FreeableMemory`, `ReadLatency`, `WriteLatency`, `Deadlocks`, `AuroraReplicaLag`.
        * **ElastiCache metrics:** `EngineCPUUtilization`, `CacheMisses`, `Evictions`, `CurrConnections`.
        * **Custom application metrics** via CloudWatch Embedded Metric Format (EMF):
            * `OTPSent`, `OTPVerifyFailures`, `ReviewsCreated`, `ProfanityRejections`, `ScraperRowsInserted`, `ScraperDurationSeconds`, `LoginSuccess`, `LoginFailure`.
    * **Tracing — AWS X-Ray.**
        * X-Ray daemon as a sidecar in the ECS task; FastAPI uses `aws-xray-sdk` middleware. Traces stitch CloudFront → ALB → ECS → Aurora calls — invaluable for diagnosing a slow `GET /search`.
    * **Dashboards.**
        * **CloudWatch Dashboard `Dersforumu-Prod`**: 4xx/5xx rates, p99 latency, task count, DB CPU, Redis hit ratio, OTP rate, scraper last-success age.
        * Optional **Amazon Managed Grafana** workspace for nicer visualization (data source = CloudWatch + X-Ray + Prometheus exporter if added later).
    * **Synthetic monitoring — CloudWatch Synthetics canary.**
        * `dersforumu-canary-login`: every 5 min, hits `/health` and a read-only `/courses`. Failure → alarm.
    * **Health checks.**
        * ALB target health (`/health` returns 200 + DB ping).
        * Route 53 health check on the public CloudFront endpoint.
        * AWS Health Dashboard subscribed for service events.

* **Q7.2:** How will we configure alarms and notifications (e.g., Pushed notifications, Emails) if a server goes down or traffic spikes?
* **AI Answer:**
    * **Notification fan-out — Amazon SNS.**
        * **Topic `dersforumu-alerts-critical`** — paging-level. Subscribers:
            * Email subscription to the on-call distribution list (`oncall@dersforumu.com`).
            * **SMS subscription** to the on-call phone (Pinpoint for TR numbers if needed).
            * **AWS Chatbot → Slack** channel `#dersforumu-alerts` for rich notifications.
            * Optional: **PagerDuty** integration via SNS→HTTPS endpoint.
        * **Topic `dersforumu-alerts-warn`** — non-paging (email + Slack only).
        * **Topic `dersforumu-alerts-info`** — Slack only (e.g., scraper completed, deploy finished).
    * **CloudWatch Alarms (representative set):**
        | Alarm | Metric | Threshold | Topic |
        |---|---|---|---|
        | API high CPU | ECS service avg CPU | > 80% for 10 min | warn |
        | API 5xx surge | ALB `HTTPCode_Target_5XX_Count` | > 5% of requests over 5 min | **critical** |
        | API latency degradation | ALB `TargetResponseTime` p99 | > 3 s for 10 min | warn |
        | No healthy targets | ALB `HealthyHostCount` | < 2 for 2 min | **critical** |
        | DB CPU | Aurora `CPUUtilization` | > 85% for 10 min | warn |
        | DB connections | Aurora `DatabaseConnections` | > 80% of max | warn |
        | DB replica lag | Aurora `AuroraReplicaLag` | > 1 s for 5 min | warn |
        | DB failover | Aurora event `failover` | any | **critical** |
        | Redis evictions | ElastiCache `Evictions` | > 0 sustained | warn |
        | OTP brute-force | custom `OTPVerifyFailures` | > 50 / 5 min | **critical** |
        | WAF blocked surge | WAF `BlockedRequests` | > 1000 / 5 min | warn |
        | Scraper failed | EventBridge target failure / task exit ≠ 0 | any | **critical** |
        | Scraper stale | `ScraperLastSuccessAge` | > 8 days | warn |
        | Certificate expiry | ACM `DaysToExpiry` | < 30 days | warn |
        | Budget overrun | AWS Budgets | > 80% monthly forecast | warn |
    * **AWS Health events** are forwarded via EventBridge → SNS critical, so any AWS-side issue affecting `eu-central-1` (EC2, RDS, Fargate) pages on-call.
    * **Composite alarms** to reduce noise (e.g., only page if `HealthyHostCount<2` *and* `5XX>threshold` simultaneously).
    * **Runbook links** included in every alarm description so the responder gets a Confluence/Notion URL directly in the SMS/email.

---

## 8. Compatibility
* **Q8.1:** Since this system serves multiple device types (desktop, mobile browsers), how does the cloud architecture ensure high-performance compatibility across these various endpoints?
* **AI Answer:**
    * **Responsive SPA, single codebase.** The React + Vite frontend is a responsive PWA-grade SPA — one bundle serves desktops, laptops, tablets, iOS Safari, Android Chrome. No per-device build.
    * **Edge delivery tuned for mobile networks (CloudFront):**
        * **HTTP/2 and HTTP/3 (QUIC)** enabled. QUIC's 0-RTT and connection migration are a big win on mobile (subway/Wi-Fi handoff at Tuzla campus).
        * **TLS 1.3** for fast handshakes.
        * **Automatic Brotli/gzip compression** on text assets — typical 70–80% reduction on JSON.
        * **Connection reuse** between CloudFront edge → ALB origin via the AWS backbone reduces TLS handshake overhead.
        * **CloudFront Functions / Lambda@Edge** (optional) can serve a `Vary: Accept` header for content negotiation and set device-aware cache keys (`CloudFront-Is-Mobile-Viewer`, `CloudFront-Is-Tablet-Viewer`, `CloudFront-Is-SmartTV-Viewer`) if we ever fork code paths.
    * **Asset strategy for varied bandwidth:**
        * Hashed, immutable, long-cache JS/CSS chunks (Vite code-splitting per route → small initial payload).
        * Images stored in S3, served via CloudFront, with **responsive `<picture>`/`srcset`** and modern formats (WebP/AVIF). Optional **Lambda@Edge image resizer** if user-uploaded images are introduced later.
        * Fonts subsetted and `font-display: swap` to avoid render blocking on slow mobile networks.
    * **API compatibility across devices:**
        * REST/JSON over HTTPS — universally supported by any browser, native iOS/Android HTTP client, and future mobile-app wrappers (React Native / Flutter).
        * CORS configured on the ALB origin (`Access-Control-Allow-Origin: https://dersforumu.com`) and surfaced via CloudFront response headers policy.
        * **Bearer JWT** auth — works identically in web and native (no cookie/CSRF complications).
        * **Future mobile native app**: if/when iOS/Android apps are built, the same ALB endpoint works; optionally place **Amazon API Gateway (HTTP API)** in front for usage plans / API keys / device throttling, or expose via **AppSync (GraphQL)** if richer mobile data needs emerge. For now, ALB is sufficient and cheaper.
    * **Progressive enhancement & resilience:**
        * Service Worker (Vite PWA plugin) caches the shell so the app loads instantly on flaky campus Wi-Fi.
        * Skeleton screens during `GET /reviews` fetch to mask latency.
        * Mobile-first responsive CSS (Tailwind or CSS Grid) — all interactive targets ≥ 44 px.
    * **Cross-region/cross-device session continuity:**
        * Stateless JWT + Cognito means a student can log in on desktop and seamlessly continue on mobile.
        * OTPs stored in Redis with email-keyed TTL — same OTP works regardless of device that completes verification.
    * **Accessibility & internationalization (forward-looking):**
        * Turkish + English locale via React-Intl; CloudFront `Accept-Language` header forwarded only where necessary.
        * WCAG AA target — sufficient color contrast, keyboard navigation, ARIA on review forms.
    * **Result:** A Sabancı student on an old Android in a basement classroom or a MacBook in the library both get a sub-second first paint and consistent API performance because every layer (edge protocol, compression, caching, responsive design, stateless API, multi-AZ backend) is tuned for variability.
