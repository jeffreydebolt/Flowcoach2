# Infrastructure & Deployment

## Runtime Stack
| Layer         | Technology Choices                              | Rationale |
|---------------|-------------------------------------------------|-----------|
| Python Runtime| Python 3.11, Slack Bolt, `slack_bolt.adapter.socket_mode`, `TodoistAPI`, `openai` | Mature Slack ecosystem, existing codebase |
| Node Runtime  | Node 20 LTS, TypeScript, `ts-node`, Anthropic SDK, SQLite3 | Rapid iteration for CLI + advanced parsing |
| Database      | SQLite (dev) ➜ Aurora Serverless PostgreSQL     | Simple local dev, managed durability in production |
| Container Base| Distroless Python & Node images (multi-stage)   | Reduce attack surface |

## Infrastructure Topology
```
            +---------------------------+
            | AWS Route53 (CLI endpoint)|
            +-------------+-------------+
                          |
                    +-----v------+
                    | ALB (HTTPS)|  <-- optional for hosted CLI/API
                    +-----+------+
                          |
      +-------------------+-------------------+
      |                                       |
+-----v-----+                         +-------v-------+
| Fargate   |                         | Fargate       |
| Service A |  Python Slack Worker    | Service B     |  Node Orchestrator
+-----+-----+                         +-------+-------+
      |                                       |
      | Secret Manager / Parameter Store      |
      |                                       |
      |          +----------------------------v-------------+
      |          | Aurora Serverless (sessions, workflows)  |
      |          +-----------------+------------------------+
      |                            |
      |                   +--------v--------+
      |                   | CloudWatch Logs |
      |                   +-----------------+
```

## Deployment Pipeline
1. GitHub Actions workflow per runtime.  
2. Lint, unit tests, integration tests.  
3. Build Docker images, push to ECR.  
4. Terraform apply (ECS service updates, database migrations via Flyway/Alembic).  
5. Post-deploy smoke tests (Slack bot handshake, CLI parse script).

Blue/green deployments via ECS CodeDeploy to avoid downtime. Rollback triggered on failed health checks or alarm breaches.
