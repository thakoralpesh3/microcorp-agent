# Lithic Technical Role Optimization: Senior Software Engineer (Processing)
## Developer Reference & Architecture Kit

---

## 1. Product Title & Value Proposition

### Title
**Lithic Technical Role Optimization: Senior Software Engineer (Processing)**

### Value Proposition
Preparing for a senior engineering role in fintech card-issuing infrastructure—specifically at a modern API-first issuer processor like **Lithic**—requires mastery of real-time distributed systems, ISO 8583 / financial message translation, idempotent webhook delivery, and ultra-low-latency authorization engines. 

This architecture kit provides the exact production-grade patterns, mental models, domain boundaries, and code boilerplates necessary to ace a senior-level technical interview and successfully architect, scale, and maintain a high-throughput card processing engine. Designed for backend and distributed systems engineers who need to demonstrate immediate competence in handling financial transactions at scale.

---

## 2. Quick Start & Core Concepts

Building a processing engine requires deep familiarity with the card network lifecycle (Authorization, Clearing, Settlement) and the specific primitives used by modern card issuers (such as Lithic's dual-message authorization stream and REST APIs).

### Core Concepts Syntax Reference Table

| Concept | Definition & Role in Processing | Mission-Critical Considerations |
| :--- | :--- | :--- |
| **Dual-Message System** | Separation of transaction authorization (real-time hold) from clearing & settlement (financial posting). | Authorization requires sub-second response times; clearing is batch/asynchronous reconciliation. |
| **ISO 8583 / ISO 20022** | The foundational messaging standard used by Visa/Mastercard networks to communicate with processors. | Bitmaps, field formatting, and strict parsing overhead require high-performance deserializers. |
| **Real-Time Webhook Engine** | The mechanism by which an issuer processor (e.g., Lithic) queries the client’s server to approve/decline an auth. | Must handle network partitions, retries, and maintain strict SLAs (< 200ms round-trip). |
| **Idempotency** | Ensuring that retried webhook deliveries or duplicate network messages never result in double-charging. | Requires distributed locks or atomic database constraints backed by unique transaction IDs. |
| **Tokenization** | Replacing Primary Account Numbers (PANs) with secure tokens for digital wallets (Apple Pay, Google Pay). | Involves token requestors, Token Service Providers (TSPs), and cryptographic key management. |
| **Velocity Checking** | Real-time fraud and risk mitigation evaluating transaction frequency, amount, and geography. | Must execute within the authorization timeout budget, typically using in-memory stores like Redis. |

---

## 3. Production Code Patterns & Architecture Examples

Below is a production-ready, highly resilient TypeScript/Node.js implementation of a **Card Authorization Webhook Handler**. It demonstrates secure signature verification, strict payload parsing, idempotency management, and a deterministic decision state machine designed for sub-200ms response requirements.

### Architecture: Hexagonal / Ports & Adapters Approach
*   **Primary Adapter:** Express.js Webhook Router (HTTP Ingress)
*   **Domain Service:** Authorization Engine (Decision Tree & Rules)
*   **Secondary Adapter:** PostgreSQL / Redis (Persistence & Idempotency Store)

```typescript
// ============================================================================
// File: src/infrastructure/webhooks/lithic-auth-handler.ts
// Description: Production-grade webhook handler for real-time card authorizations.
// ============================================================================

import { Request, Response } from 'express';
import * as crypto from 'crypto';
import { Pool } from 'pg';
import { Redis } from 'ioredis';

// --- 1. Domain Types & Interfaces ---

export interface AuthorizationRequest {
  token: string;
  amount: number; // in cents
  currency: string;
  card_token: string;
  merchant: {
    descriptor: string;
    city: string;
    country: string;
    category_code: string; // MCC
  };
  created_at: string;
}

export enum AuthDecisionResult {
  APPROVED = 'APPROVED',
  DECLINED = 'DECLINED',
}

export interface AuthDecisionResponse {
  result: AuthDecisionResult;
  decline_reason?: string;
}

// --- 2. Security & Verification Service ---

export class WebhookSecurityService {
  constructor(private readonly webhookSecret: string) {}

  public verifySignature(rawBody: string, signatureHeader: string): boolean {
    if (!signatureHeader) return false;
    
    // Lithic-style HMAC SHA256 verification
    const computedSignature = crypto
      .createHmac('sha256', this.webhookSecret)
      .update(rawBody)
      .digest('hex');

    const providedBuffer = Buffer.from(signatureHeader, 'utf-8');
    const computedBuffer = Buffer.from(computedSignature, 'utf-8');

    if (providedBuffer.length !== computedBuffer.length) {
      return false;
    }

    return crypto.timingSafeEqual(providedBuffer, computedBuffer);
  }
}

// --- 3. Idempotency & Persistence Repository ---

export class AuthorizationRepository {
  constructor(
    private readonly db: Pool,
    private readonly redis: Redis
  ) {}

  /**
   * Attempts to acquire an atomic lock for the transaction token to prevent race conditions.
   */
  public async acquireLock(transactionToken: string): Promise<boolean> {
    const result = await this.redis.set(
      `lock:auth:${transactionToken}`,
      'locked',
      'EX',
      10, // 10 second TTL
      'NX'
    );
    return result === 'OK';
  }

  public async releaseLock(transactionToken: string): Promise<void> {
    await this.redis.del(`lock:auth:${transactionToken}`);
  }

  /**
   * Checks if an authorization has already been processed (Idempotency check).
   */
  public async getExistingDecision(transactionToken: string): Promise<AuthDecisionResponse | null> {
    const query = `SELECT decision, decline_reason FROM processed_authorizations WHERE transaction_token = $1;`;
    const { rows } = await this.db.query(query, [transactionToken]);
    if (rows.length === 0) return null;
    return {
      result: rows[0].decision as AuthDecisionResult,
      decline_reason: rows[0].decline_reason,
    };
  }

  public async saveDecision(transactionToken: string, decision: AuthDecisionResponse): Promise<void> {
    const query = `
      INSERT INTO processed_authorizations (transaction_token, decision, decline_reason, created_at)
      VALUES ($1, $2, $3, NOW())
      ON CONFLICT (transaction_token) DO NOTHING;
    `;
    await this.db.query(query, [transactionToken, decision.result, decision.decline_reason || null]);
  }
}

// --- 4. Domain Engine / Business Rules ---

export class AuthorizationEngine {
  public evaluate(request: AuthorizationRequest): AuthDecisionResponse {
    // Rule 1: Hard block on specific Merchant Category Codes (e.g., Gambling MCC 7995)
    if (request.merchant.category_code === '7995') {
      return {
        result: AuthDecisionResult.DECLINED,
        decline_reason: 'RESTRICTED_MCC',
      };
    }

    // Rule 2: Balance check or internal risk parameters (Mocked)
    if (request.amount > 500000) { // $5,000.00 limit check
      return {
        result: AuthDecisionResult.DECLINED,
        decline_reason: 'INSUFFICIENT_FUNDS_OR_LIMIT_EXCEEDED',
      };
    }

    // Default Approve
    return {
      result: AuthDecisionResult.APPROVED,
    };
  }
}

// --- 5. Controller / HTTP Entrypoint ---

export class LithicWebhookController {
  constructor(
    private readonly securityService: WebhookSecurityService,
    private readonly authRepo: AuthorizationRepository,
    private readonly authEngine: AuthorizationEngine
  ) {}

  public async handleWebhook(req: Request, res: Response): Promise<void> {
    const signature = req.headers['lithic-signature'] as string;
    const rawBody = (req as any).rawBody; // Assumes raw body middleware is configured

    // 1. Verify Webhook Authenticity
    if (!this.securityService.verifySignature(rawBody, signature)) {
      res.status(401).json({ error: 'Invalid signature' });
      return;
    }

    const payload: AuthorizationRequest = req.body;
    const txnToken = payload.token;

    // 2. Acquire Distributed Lock to prevent duplicate concurrent delivery races
    const locked = await this.authRepo.acquireLock(txnToken);
    if (!locked) {
      // If locked, another request is processing. Return 429 or check existing status.
      res.status(429).json({ error: 'Concurrent processing for transaction token' });
      return;
    }

    try {
      // 3. Idempotency Check
      const existing = await this.authRepo.getExistingDecision(txnToken);
      if (existing) {
        res.status(200).json(existing);
        return;
      }

      // 4. Execute Core Domain Logic
      const decision = this.authEngine.evaluate(payload);

      // 5. Persist Decision for Future Idempotency Lookups
      await this.authRepo.saveDecision(txnToken, decision);

      // 6. Respond within Network SLA (< 200ms)
      res.status(200).json(decision);
    } catch (error) {
      console.error('Critical authorization processing error:', error);
      // Fail open or closed depending on risk posture; standard is polite decline or retry
      res.status(500).json({ error: 'Internal processing error' });
    } finally {
      await this.authRepo.releaseLock(txnToken);
    }
  }
}
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

When building processing engines for financial networks, subtle implementation flaws can lead to severe operational incidents, regulatory failures, or financial loss.

```
+-------------------------------------------------------------------------+
|                  ARCHITECTURAL ANTI-PATTERNS TO AVOID                   |
+-------------------------------------------------------------------------+
|  [Anti-Pattern 1] Synchronous Third-Party API Calls Inside Auth Flow     |
|  -> Impact: Breaches sub-200ms timeout windows due to network latency.   |
+-------------------------------------------------------------------------+
|  [Anti-Pattern 2] Lack of Distributed Idempotency Locks                  |
|  -> Impact: Network retries trigger double approvals / double debits.   |
+-------------------------------------------------------------------------+
|  [Anti-Pattern 3] Floating-Point Math for Monetary Values               |
|  -> Impact: Rounding errors (e.g., $0.1 + $0.2 = $0.30000000000000004).  |
+-------------------------------------------------------------------------+
```

### 1. Synchronous External API Dependencies
*   **The Mistake:** Calling an external fraud scoring service, KYC provider, or credit bureau synchronously inline with the authorization webhook request.
*   **The Trade-off:** While third-party data improves risk posture, external network calls introduce unpredictable latency spikes. If the third party takes 500ms to respond, the card network times out, causing a decline for the cardholder.
*   **The Fix:** Pre-compute and cache risk scores asynchronously via user-behavior event streams; rely entirely on local, in-memory state or low-latency Redis lookups during the auth decision window.

### 2. Failure to Handle Network Retries (Idempotency Blindness)
*   **The Mistake:** Treating every incoming webhook as a brand-new transaction without checking unique transaction identifiers (`token` or `message_id`).
*   **The Trade-off:** Card networks routinely retry webhooks if they do not receive an HTTP 200 within strict timeout windows (e.g., 2 seconds). Without strict database constraints and distributed locking, retries result in duplicate processing.
*   **The Fix:** Implement database-level unique constraints on transaction tokens and use atomic distributed locks (Redis `SET NX EX`) during the execution block.

### 3. Floating-Point Arithmetic for Currency
*   **The Mistake:** Representing transaction amounts as standard JavaScript numbers (`10.50`).
*   **The Trade-off:** IEEE 754 floating-point representation causes severe precision errors in arithmetic operations.
*   **The Fix:** Always represent currency as **integers representing the smallest currency unit** (e.g., cents for USD, where $10.50 = `1050`). Use `BigInt` for high-volume ledger accumulation.

---

## 5. Performance & Optimization Tips

To consistently pass strict network latency SLAs and handle high-throughput burst traffic (e.g., Flash Sales, Holiday Shopping), engineers must optimize every layer of the stack.

### 1. Connection Pooling & Prepared Statements
*   Maintain persistent connection pools (e.g., using `pg.Pool`) with optimized pool sizes matching your CPU core count and database max connection limits.
*   Use parameterized queries and prepared statements to eliminate SQL parsing overhead on hot authorization paths.

### 2. In-Memory Velocity & Balance Caching
*   Keep user balances, card statuses (active/frozen), and velocity counters in a clustered Redis deployment.
*   Use Redis Lua scripts for atomic read-modify-write operations on velocity counters (e.g., checking if a card has exceeded 5 transactions in the last 60 seconds) without round-trip network overhead between application and cache.

### 3. Asynchronous Clearing & Ledger Posting
*   Never perform heavy database writes, analytics logging, or ledger reconciliation inline within the real-time authorization request handler.
*   Push authorized transaction events to a high-throughput durable message broker (e.g., Apache Kafka, AWS SQS/SNS, or RabbitMQ) for asynchronous clearing, settlement ingestion, and notification dispatch.

```
[Card Network / Lithic] 
       │
       ▼ (HTTP POST / Sub-200ms SLA)
[Webhook Handler] ──(Redis Atomic Check)──> [In-Memory Validation]
       │                                           │
       ├──────(Publish Auth Event)─────────────────┤
       ▼                                           ▼
[Return HTTP 200 OK]                     [Kafka / Message Broker]
                                                   │
                                                   ▼
                                         [Clearing & Ledger Service]
```

---

## 6. Commercial License & Attribution Summary

### License Type: Commercial Developer License (Single-Org / Individual)

*   **Copyright © 2024 MicroCorp AI & The Agency Engineering Division.** All rights reserved.
*   **Permitted Use:** This architectural kit may be used internally within your organization for technical interview preparation, system design reference, and boilerplate implementation for card processing infrastructure.
*   **Restrictions:** Redistribution, resale, public posting of source code in open-source repositories without explicit written consent, or inclusion in commercial training courses is strictly prohibited.
*   **Warranty Disclaimer:** Provided "as is" without warranty of any kind, express or implied. The author and MicroCorp AI shall not be held liable for any financial loss, network timeout penalties, or processing discrepancies arising from the use of this code in production environments.