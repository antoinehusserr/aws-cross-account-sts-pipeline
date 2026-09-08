# AWS Cross-Account Access via STS — ISS Tracker

![AWS](https://img.shields.io/badge/AWS-232F3E?style=flat&logo=amazon-aws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![IAM](https://img.shields.io/badge/IAM-STS%20%2F%20AssumeRole-D05538?style=flat)
![Status](https://img.shields.io/badge/Status-Working-1D9E75?style=flat)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat)

> How to give an AWS service access to resources in another account  without ever sharing a permanent access key.

## Table of Contents

- [Architecture](#architecture)
- [The Detailed Flow](#the-detailed-flow)
- [Why This Project](#why-this-project)
- [How It Works](#how-it-works)
- [Deployment](#deployment)
- [Result](#result)
- [What I Learned](#what-i-learned)
- [Sources](#sources)

## Architecture

```mermaid
graph LR
    API[("🛰️ Public ISS<br/>API")] -->|HTTPS GET| L

    subgraph A["Account A — source"]
        L["⚡ Lambda<br/>iss-tracker-function"]
    end

    subgraph B["Account B — target"]
        R["🔐 IAM Role<br/>ISSDataWriterRole"]
        S[("🪣 S3 Bucket<br/>iss-tracker-data")]
    end

    L -->|"sts:AssumeRole<br/>+ ExternalId"| R
    R -->|"s3:PutObject<br/>(scoped to this bucket)"| S

    style A fill:#e8f0fe,stroke:#4285f4
    style B fill:#e6f4ea,stroke:#34a853
    style L fill:#4285f4,color:#fff
    style R fill:#a142f4,color:#fff
    style S fill:#34a853,color:#fff
```

## The Detailed Flow

This sequence diagram shows the exact order of calls and — the key point — the moment the credentials change:

```mermaid
sequenceDiagram
    participant API as ISS API
    participant L as Lambda (Account A)
    participant STS as AWS STS
    participant S3 as S3 (Account B)

    L->>API: GET ISS position
    API-->>L: JSON (lat/lon)
    L->>STS: AssumeRole(ISSDataWriterRole, ExternalId)
    STS-->>L: Temporary credentials (15 min)
    Note over L: Switches to the<br/>assumed role's credentials
    L->>S3: PutObject (using temporary creds)
    S3-->>L: 200 OK
    Note over STS,S3: No permanent key<br/>exchanged at any point
```

## Why This Project

| | 🔴 Permanent keys (to avoid) | 🟢 STS AssumeRole (this project) |
|---|---|---|
| **Lifetime** | Unlimited until manually revoked | 15 minutes, automatic expiration |
| **Exposure if leaked** | Full and lasting access | Very short exploitation window |
| **Traceability** | Hard to distinguish per session | Each session has a unique `RoleSessionName`, visible in CloudTrail |
| **Scope of access** | Often too broad | Precisely scoped by the permissions policy |

## How It Works

The target role (`ISSDataWriterRole`, Account B) relies on two independent policies:

| Policy | Answers the question | Content |
|---|---|---|
| **Trust policy** | Who is allowed to assume this role? | Only Account A, and only with the correct `ExternalId` (protection against the "confused deputy problem") |
| **Permissions policy** | What can this role do once assumed? | Only `s3:PutObject` on one specific bucket — nothing else |

On the Account A side, the Lambda has an `sts:AssumeRole` permission scoped to the exact ARN of the target role.

## Deployment

Prerequisites: two separate AWS accounts.

1. **Account B** — create the S3 bucket, then the IAM role using the policies provided in [`policies/`](policies/):
   - `trust_policy_accountB.json`
   - `permissions_policy_accountB.json`
2. **Account A** — create the Lambda execution role with `lambda_execution_policy_accountA.json`.
3. Deploy [`src/lambda_function.py`](src/lambda_function.py) with the environment variables `TARGET_ROLE_ARN`, `BUCKET_NAME`, `EXTERNAL_ID`.
4. Test it from the Lambda console.

Replace `<ACCOUNT_A_ID>` and `<ACCOUNT_B_ID>` with your own account IDs.

## Result

<table>
<tr>
<td width="50%">

**Object written to S3 (Account B)**

![S3 result](screenshots/s3-object.png)

</td>
<td width="50%">

**AssumeRole event in CloudTrail (audit trail)**

![CloudTrail AssumeRole](screenshots/cloudtrail-assumerole-table.png)

</td>
</tr>
</table>

The ARN `assumed-role/ISSDataWriterRole/iss-tracker-lambda` confirms the call genuinely came from this project's Lambda function.

## What I Learned

- The difference between a trust policy (access to the role) and a permissions policy (capabilities of the role), and why both are required independently of each other.
- The role of the `ExternalId` condition in preventing the "confused deputy problem" during cross-account access.
- Why temporary credentials reduce the attack surface, even if the application code itself is compromised.
- Debugging IAM policies from `AccessDenied` error messages.

## Sources

- [AWS IAM — Tutorial: Delegate access across AWS accounts using IAM roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/tutorial_cross-account-with-roles.html)
- [AWS IAM — Cross account resource access](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies-cross-account-resource-access.html)
- [AWS Security Blog — How to use trust policies with IAM roles](https://aws.amazon.com/blogs/security/how-to-use-trust-policies-with-iam-roles/)
- [Where the ISS at? — API documentation](https://wheretheiss.at/w/developer)

---

Project built as part of hands-on cloud security learning. [LinkedIn](#)
