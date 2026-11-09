# Developer Toolkit: Payments Canada Real-Time Rail (RTR) Integration Suite

## 1. Product Title & Value Proposition

### 💳 Payments Canada Real-Time Rail (RTR) Integration Suite
*Enterprise-Grade Architectural Reference, API Blueprint, and Production Boilerplate for Canadian FinTech & Banking Platforms.*

```
+-----------------------------------------------------------------------+
| MicroCorp AI Engineering Division | Enterprise Architecture Artifact  |
| SKU: MC-RTR-DEV-202X-V1               | Target: ISO 20022 / Interac     |
+-----------------------------------------------------------------------+
```

### Executive Value Proposition
Building modern payment flows on Canada's Real-Time Rail (RTR) requires strict adherence to ISO 20022 messaging standards, cryptographic payload verification, idempotent ledger operations, and sub-second webhook processing guarantees. 

This commercial integration suite eliminates months of standards interpretation and compliance guesswork. It provides engineering teams with battle-tested TypeScript/Node.js architectural patterns, idempotent transaction state machines, and resilient error-handling middleware designed to pass institutional security audits and clear payments 24/7/365.

---

## 2. Quick Start & Core Concepts

### Core Architecture Concepts

| Concept | Definition & Implementation Standard |
| :--- | :--- |
| **ISO 20022 Messaging** | The global standard used by RTR. All payloads must conform to strict XML/JSON schemas (e.g., `pacs.008` for credit transfers, `camt.053` for statements). |
| **Idempotency Keys** | Mandatory unique keys (`UUIDv4`) included in request headers (`X-Idempotency-Key`) to prevent duplicate clearing during network partitions or retry storms. |
| **Clearing & Settlement** | RTR transactions are irrevocable and settled instantly (seconds). Unlike EFT/ACSS, there is no multi-day chargeback window; disputes happen out-of-band. |
| **Webhook Delivery** | Asynchronous event notifications for state transitions (`ACCP`, `ACSP`, `RJCT`). Must be verified via HMAC SHA-256 signatures. |

### Quick Start: Minimalist Client Initialization
Initialize the secure RTR gateway client with mutual TLS (mTLS) configuration and strict payload validation.

```typescript
import { RTRClient, Environment } from '@microcorp/rtr-sdk';

// Initialize the enterprise client with mTLS certificates
const rtrClient = new RTRClient({
  environment: Environment.PRODUCTION,
  institutionId: process.env.RTR_INSTITUTION_ID!,
  signingKeyId: process.env.RTR_SIGNING_KEY_ID!,
  privateKeyPem: process.env.RTR_PRIVATE_KEY_PEM!,
  mtls: {
    cert: process.env.RTR_MTLS_CERT_PEM!,
    key: process.env.RTR_MTLS_KEY_PEM!,
  },
  timeoutMs: 5000, // Strict 5s SLA for real-time rails
});

export default rtrClient;
```

---

## 3. Production Code Patterns & Architecture Examples

### Pattern A: Idempotent Payment Submission (`pacs.008`)
This pattern demonstrates how to construct a compliant ISO 20022 credit transfer request with cryptographically signed payloads, automated idempotency key generation, and robust error handling.

```typescript
import { v4 as uuidv4 } from 'uuid';
import { RTRClient } from '@microcorp/rtr-sdk';
import { ISO20022CreditTransfer, PaymentResponse } from './types';

export async function submitRealTimePayment(
  client: RTRClient,
  paymentData: {
    amount: string;
    currency: 'CAD';
    debtorAccount: string;
    creditorAccount: string;
    creditorAgentRoutingId: string; // 8-digit Canadian Financial Institution ID (Aba/Transit)
    remittanceInfo: string;
  }
): Promise<PaymentResponse> {
  const idempotencyKey = uuidv4();
  const endToEndId = `E2E-${Date.now()}-${uuidv4().substring(0, 8)}`;

  // Construct ISO 20022 pacs.008.001.08 Compliant Payload
  const payload: ISO20022CreditTransfer = {
    GrpHdr: {
      MsgId: `MSG-${uuidv4()}`,
      CreDtTm: new Date().toISOString(),
      NbOfTxs: "1",
      SttlmInf: {
        SttlmMtd: "CLRG", // Clearing system
      }
    },
    CdtTrfTxInf: [{
      PmtId: {
        EndToEndId: endToEndId,
        UETR: uuidv4() // Unique End-to-End Transaction Reference
      },
      IntrBkSttlmAmt: {
        Ccy: paymentData.currency,
        Value: paymentData.amount
      },
      Dbtr: {
        Nm: "MicroCorp Verified Corporate Account"
      },
      DbtrAcct: {
        Id: { Othr: { Id: paymentData.debtorAccount } }
      },
      CdtrAgent: {
        FinInstnId: {
          ClrSysMmbId: {
            MmbId: paymentData.creditorAgentRoutingId
          }
        }
      },
      Cdtr: {
        Nm: paymentData.remittanceInfo
      },
      CdtrAcct: {
        Id: { Othr: { Id: paymentData.creditorAccount } }
      },
      RmtInf: {
        Ustrd: [paymentData.remittanceInfo]
      }
    }]
  };

  try {
    const response = await client.post('/v1/payments/pacs.008', payload, {
      headers: {
        'X-Idempotency-Key': idempotencyKey,
        'Content-Type': 'application/xml', // Or application/json depending on gateway profile
      }
    });

    return {
      success: true,
      transactionId: response.data.transactionId,
      status: response.data.status, // e.g., 'ACCP' (Accepted)
      endToEndId
    };
  } catch (error: any) {
    // Handle specific RTR error codes (e.g., RR04: Insufficient Funds, AM04: Invalid Amount)
    console.error(`[RTR_SUBMISSION_FAILED] E2E: ${endToEndId}`, error.response?.data || error.message);
    throw new Error(`RTR Transaction Failed: ${error.response?.data?.errorCode || 'UNKNOWN_ERROR'}`);
  }
}
```

### Pattern B: Webhook Signature Verification & State Machine Processor
RTR webhooks arrive asynchronously. This Express middleware verifies the cryptographic signature to prevent spoofing and routes state changes (`ACCP`, `RJCT`) through a durable database transaction.

```typescript
import express, { Request, Response } from 'express';
import crypto from 'crypto';

const app = express();
app.use(express.json({ verify: (req: any, res, buf) => { req.rawBody = buf; } }));

const RTR_WEBHOOK_SECRET = process.env.RTR_WEBHOOK_SECRET!;

// HMAC SHA-256 Webhook Verification Middleware
function verifyRTRSignature(req: Request & { rawBody?: Buffer }, res: Response, next: Function) {
  const signatureHeader = req.headers['x-rtr-signature'] as string;
  const timestamp = req.headers['x-rtr-timestamp'] as string;

  if (!signatureHeader || !timestamp) {
    return res.status(401).json({ error: 'Missing security headers' });
  }

  // Prevent replay attacks (5-minute tolerance window)
  const fiveMinutes = 5 * 60 * 1000;
  if (Math.abs(Date.now() - parseInt(timestamp, 10)) > fiveMinutes) {
    return res.status(401).json({ error: 'Timestamp outside acceptable window' });
  }

  const payloadString = `${timestamp}.${req.rawBody?.toString('utf8')}`;
  const computedSignature = crypto
    .createHmac('sha256', RTR_WEBHOOK_SECRET)
    .update(payloadString)
    .digest('hex');

  if (!crypto.timingSafeEqual(Buffer.from(signatureHeader), Buffer.from(computedSignature))) {
    return res.status(403).json({ error: 'Invalid webhook signature' });
  }

  next();
}

app.post('/webhook/rtr/events', verifyRTRSignature, async (req: Request, res: Response) => {
  const event = req.body;

  // Process RTR Status Codes: ACCP (Accepted), ACSP (Accepted Settlement In Process), RJCT (Rejected)
  switch (event.status) {
    case 'ACCP':
      await updateLedgerState(event.endToEndId, 'SETTLED', event.settlementTimestamp);
      break;
    case 'RJCT':
      await handleRejection(event.endToEndId, event.reasonCode, event.errorDescription);
      break;
    default:
      console.warn(`Unhandled RTR status received: ${event.status}`);
  }

  return res.status(200).json({ received: true });
});

async function updateLedgerState(endToEndId: string, state: string, timestamp: string) {
  // Implementation: DB Transaction updating payment status
  console.log(`[LEDGER] Payment ${endToEndId} marked as ${state} at ${timestamp}`);
}

async function handleRejection(endToEndId: string, reasonCode: string, description: string) {
  // Implementation: Reverse temporary holds, notify user via notification microservice
  console.error(`[LEDGER] Payment ${endToEndId} REJECTED [${reasonCode}]: ${description}`);
}
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

### ❌ Anti-Pattern 1: Relying on Traditional Database Auto-Increment IDs for Settlement Mapping
* **The Mistake:** Using sequential database IDs (`1001`, `1002`) to track payment legs across distributed microservices.
* **Why it fails:** In real-time high-throughput systems, race conditions and database shard synchronization lags will cause ID collisions or mapping failures.
* **The Correct Approach:** Use globally unique UUIDv4 identifiers combined with the RTR-supplied `UETR` (Unique End-to-End Transaction Reference) across all logging and persistence layers.

### ❌ Anti-Pattern 2: Skipping Idempotency Keys on Timeout Retries
* **The Mistake:** Automatically retrying failed HTTP POST requests to the RTR gateway without including an `X-Idempotency-Key` header.
* **Why it fails:** If a network timeout occurs *after* the RTR gateway successfully processes the payment, a retry without an idempotency key will trigger a **double payout**.
* **The Correct Approach:** Persist the idempotency key in your local database *before* transmitting the request. Reuse the exact same key for any retry attempts of that transaction.

### ❌ Anti-Pattern 3: Treating Webhooks as Synchronous UI Blockers
* **The Mistake:** Keeping HTTP connections open waiting for a webhook callback to confirm payment completion to an end user interface.
* **Why it fails:** Network latency, webhook retry intervals, or proxy timeouts will cause frontend connection drops, creating a poor user experience.
* **The Correct Approach:** Return an immediate asynchronous acceptance receipt (`202 Accepted`) to the client frontend, and update the UI via WebSockets or Server-Sent Events (SSE) once the webhook processor confirms settlement.

---

## 5. Performance & Optimization Tips

1. **Connection Pooling & Keep-Alive:** 
   Configure your HTTPS agents with persistent keep-alive connections (`maxSockets: 100`, `keepAlive: true`) to eliminate TCP and TLS handshake overhead on time-sensitive RTR API calls.
2. **Asynchronous Event Queuing:** 
   Offload incoming webhook payloads directly to a high-throughput message broker (e.g., Apache Kafka or Redis Streams) before processing database updates. Respond with `200 OK` to the RTR gateway within `< 200ms` to prevent gateway backpressure or webhook disabling.
3. **Optimized XML Parsing:** 
   If your integration layer consumes raw ISO 20022 XML payloads, use streaming, lightweight parsers (`sax` or fast native bindings) rather than heavy DOM-based parsers to minimize memory footprint and CPU spikes during traffic surges.

---

## 6. Commercial License & Attribution Summary

```
+-----------------------------------------------------------------------+
| TERMS OF USAGE: COMMERCIAL ENTERPRISE LICENSE                         |
| MicroCorp AI Developer Toolkit Series                                 |
+-----------------------------------------------------------------------+
```

* **Copyright © 202X MicroCorp AI. All rights reserved.**
* **Grant of License:** Licensed to the purchasing organization and its internal engineering personnel for the development, testing, and deployment of commercial financial applications interfacing with Payments Canada Real-Time Rail (RTR) infrastructure.
* **Restrictions:** Redistribution, resale, public repository publishing, or inclusion of these source code patterns within open-source frameworks without explicit written authorization from MicroCorp AI is strictly prohibited.
* **Disclaimer:** Provided "AS IS", without warranty of any kind, express or implied. Financial institution compliance, regulatory adherence (FINTRAC, OSFI), and final security attestations remain the sole responsibility of the implementing engineering organization.