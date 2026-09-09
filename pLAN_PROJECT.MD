The $0–$5/month AWS Stack (Cost-Optimized)
IMPORTANT

This is the core insight: you do NOT need Aurora, OpenSearch, or ElastiCache. Those services cost $30-100+/month each. Instead, use EC2 free tier + services that are genuinely free.

What You'll Use
Mermaid diagram
Cost Breakdown
AWS Service	What For	Free Tier	Your Cost
EC2 t3.micro	Monarch API server	750 hrs/month (12 months)	$0
EBS	20GB gp3 volume (SQLite + FAISS index)	30 GB free	$0
S3	Document storage + frontend hosting	5 GB + 20K GETs	$0
CloudFront	CDN for frontend	1 TB transfer/month	$0
SSM Parameter Store	API keys (Standard tier)	Free forever	$0
CloudWatch	Logs + basic metrics	5 GB logs + 10 metrics	$0
Amazon Bedrock	LLM calls (Claude/Llama)	None — pay per token	$2–5 depending on usage
Cognito	User auth	50,000 MAU free	$0
ECR	Docker image store	500 MB free	$0
TOTAL	$0–5/month
TIP

Alternative to Bedrock: Keep using Groq (free API with rate limits). The judges want to see AWS architecture, not necessarily AWS LLMs. You can use Groq for LLM calls and AWS for everything else. This drops cost to literally $0.

🏆 Winning Strategy: Target All 3 Tracks
Track 1: "Build It" — Open-source AWS Stack
The hackathon specifically calls out: Strands, Cedar, SAM Local, PartyRock, OpenSearch.

Your angle: Monarch uses open-source AWS technologies:

✅ Amazon OpenSearch (can run locally via Docker for Build It track)
✅ AWS SAM for Lambda-based code sandbox
✅ AWS CDK/CloudFormation for Infrastructure-as-Code
Track 2: "Ship It" — Deployed Live on AWS
"Architecture is a key part of the scoring"

Your angle: Full production deployment:

EC2 running Monarch API with persistent storage
S3 + CloudFront serving the frontend
CloudWatch observability dashboard
Health check endpoint with uptime monitoring
Architecture diagram in README (judges love this)
Track 3: "Best UI"
Your angle: The existing web workbench is decent. Polish it into a beautiful, streaming, responsive UI.

📋 Prep Week Plan (Now → Sept 16)
These are learning and design tasks. No hackathon code.

Day 1–2: AWS Setup & Learning
 Create/verify AWS account with Free Tier
 Create AWS Builder Center profile (required for hackathon)
 Learn EC2 basics: launch a t3.micro, SSH in, install Python
 Learn S3: create a bucket, enable static hosting
 Learn CloudFront: set up distribution pointing to S3
 Learn SSM Parameter Store: store a test secret, retrieve with boto3
 Learn CloudWatch: view EC2 metrics, create a basic dashboard
Day 3–4: Practice Deploying a FastAPI App to EC2
 Practice: deploy a bare FastAPI "hello world" to EC2
 Practice: set up Nginx as reverse proxy on EC2
 Practice: install Docker on EC2, run a container
 Practice: persist a SQLite file on EBS (survives container restart)
 Practice: FAISS index.save() / index.load() to persist vector store to disk
 Practice: use boto3 to upload/download from S3
Day 5–6: Architecture Design & Templates
 Draw final architecture diagram (Mermaid + image export)
 Write deployment scripts (shell scripts for EC2 setup)
 Design the polished UI wireframes (for Best UI track)
 Prepare .env.example template with all AWS config variables
 Write a README skeleton (architecture, features, setup instructions)
Day 7: Rest + Review
 Review all AWS service limits
 Make sure you can launch an EC2 instance in < 5 minutes
 Verify Groq API key is working
 Verify AWS Builder Center profile is complete
🚀 Hackathon Execution Plan (Sept 17–20)
Day 1 (Sept 17, Thursday) — Foundation Sprint
Morning (4h):

 Initialize fresh repo, commit empty project structure
 Build Agents/state.py — LangGraph State schema
 Build utils/config.py — Groq/Bedrock LLM init + SSM Parameter Store integration
 Build Agents/router.py — Orchestrator with structured output routing
 Build Agents/planner.py — General reasoning agent
 Build Agents/research.py — Web search agent (DuckDuckGo)
Afternoon (4h):

 Build RAG/manager.py — FAISS + BM25 hybrid RAG with disk persistence (faiss.write_index())
 Build RAG/retriever.py — RRF fusion
 Build Agents/rag.py — Document RAG agent
 Build Agents/graph.py — LangGraph workflow with reflection loop
 Build Agents/reflection.py — Self-correction critic node
Evening (2h):

 Build guardrails/input_guard.py — PII masking + injection defense
 Build guardrails/output_guard.py — RAG faithfulness check
 Build api.py — FastAPI with all endpoints (/api/chat, /api/ingest, /api/health, /api/memories)
 Test everything locally — should work end to end
Day 2 (Sept 18, Friday) — AWS Deployment + Advanced Features
Morning (4h):

 Build SQL/db.py + SQL/repository.py — SQLite persistence on EBS
 Build SQL/memory_consolidator.py — Background fact distillation
 Add SSE streaming endpoint: POST /api/chat/stream
 Add S3 document upload integration (raw docs stored in S3, chunks in FAISS)
Afternoon (4h):

 Launch EC2 t3.micro, install dependencies
 Deploy Monarch to EC2 with Nginx reverse proxy
 Set up SSM Parameter Store with all secrets
 Persist FAISS index + SQLite DB on EBS volume
 Set up CloudWatch Logs (pipe uvicorn output to CloudWatch)
 Verify: app is live at http://<EC2-IP>:8000, survives restart
Evening (2h):

 Add Cognito user auth (JWT validation middleware)
 Build MCP/server.py — FastMCP tool server
 Build harness/eval_suite.py — Automated evaluation harness
 Build main.py — CLI entrypoint with all modes
Day 3 (Sept 19, Saturday) — UI + Architecture Polish
Morning (4h):

 Build beautiful frontend: index.html + static/app.js + static/style.css
Glassmorphism dark mode ✨
SSE streaming chat with typewriter effect
Document upload with drag-and-drop
Memory inspector sidebar
Mobile responsive
Loading animations
 Deploy frontend to S3 + CloudFront
Afternoon (4h):

 Set up CloudWatch Dashboard:
API latency metrics
Request count by route
Error rate
Memory/CPU utilization
 Add health check monitoring
 Add Agents/vision.py — Groq Vision agent for multimodal
 Run full evaluation harness, fix any failures
Evening (2h):

 Write comprehensive README with:
Architecture diagram (Mermaid)
Screenshots of UI
AWS architecture diagram
Feature list
Deployment instructions
Cost analysis ($0 explanation)
 Create short demo video (2-3 min)
Day 4 (Sept 20, Sunday) — Final Polish + Submit
Morning (3h):

 Final bug fixes and edge case handling
 Add Dockerfile + docker-compose.yml
 Add deploy.sh — one-command EC2 deployment script
 Add infrastructure diagram to README
 Clean up code: docstrings, type hints, remove debug prints
Afternoon (2h):

 Final testing on live EC2 deployment
 Record final demo video showing:
Live deployed URL
Multi-agent routing (planner, research, RAG, vision)
Document ingestion + retrieval
Guardrail blocking injection attempts
Memory distillation
CloudWatch dashboard
Architecture diagram
 Submit 🚀
🏗️ Architecture That Wins "Ship It"
Mermaid diagram
This architecture is simple, clean, and cheap — but it covers all the AWS services the judges want to see:

Compute: EC2
Storage: S3 + EBS
Security: Cognito + SSM Parameter Store
Observability: CloudWatch
CDN: CloudFront
Networking: VPC, Security Groups
🔑 Key Technical Changes from Current Codebase
What Stays the Same (Core Engine)
Your LangGraph multi-agent architecture, hybrid RAG, reflection loops, and guardrails are excellent. Keep the same design.

What Changes (AWS Integration)
Current	Hackathon Version	Why
.env file for secrets	SSM Parameter Store via boto3	AWS-native, judges will check
SQLite monarch.db (ephemeral in Docker)	SQLite on EBS volume (persists across restarts)	Survive EC2 reboot, $0
FAISS in-memory only	FAISS with faiss.write_index() to EBS disk	Persist RAG across restarts, $0
Temp file for ingestion	Upload raw docs to S3 first, then process	Document management, $0
No auth	Cognito JWT validation	Security, $0
print() logging	CloudWatch Logs via watchtower library	Observability, $0
Manual docker run	EC2 deploy script with Nginx	One-command deploy
No CDN	CloudFront → S3 for frontend	Fast, professional
What You Should NOT Do
❌ Aurora PostgreSQL — $30+/month minimum
❌ OpenSearch Serverless — $25+/month minimum
❌ ElastiCache — $15+/month minimum
❌ ECS Fargate — EC2 free tier is better for single-server
❌ Lambda for main API — cold start makes chat unusable
❌ API Gateway — EC2 + Nginx is simpler and free
💡 Bonus Features to Stand Out
These are the "wow factor" features that separate winners from participants:

SSE Streaming Chat — Token-by-token typing effect. Every other team will have "loading... done". You'll have smooth real-time streaming.

Live Architecture Dashboard — A /architecture page that shows the Mermaid diagram of what AWS services are being used, with live health status dots.

Cost Calculator — Show a live "This app costs $0.00/month on AWS" badge in the UI. Judges will LOVE this.

CloudWatch Dashboard Screenshot in README — Proves real observability.

One-Command Deploy — ./deploy.sh that sets up the entire EC2 instance from scratch. Shows you understand DevOps.

Open Questions
IMPORTANT

Q1: Is your current Monarch code prior work that you've already pushed to GitHub? If yes, you'll need to start a fresh repo during the hackathon. You can rewrite the same architecture from your knowledge, but the git commits must be within Sept 17–20.

IMPORTANT

Q2: Do you want to use Groq (free, external API) or Amazon Bedrock (AWS-native, $2-5/month)? Using Bedrock scores higher with judges but costs money. Using Groq is free but isn't an AWS service. My recommendation: Use Groq as primary, add Bedrock as a configurable fallback — best of both worlds.

IMPORTANT

Q3: Solo or team? The hackathon allows teams of 1–4. With a team, you can parallelize: one person on backend, one on AWS infra, one on frontend/UI, one on docs/demo video.