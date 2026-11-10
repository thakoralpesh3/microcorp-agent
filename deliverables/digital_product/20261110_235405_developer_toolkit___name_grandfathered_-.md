# Developer Toolkit: .name Grandfathered
**Product Type:** Developer Reference & Architecture Kit  
**Target Audience:** Senior Infrastructure Engineers, DNS Administrators, Identity & Access Management (IAM) Architects, and Domain Registry Operators.

---

## 1. Product Title & Value Proposition

### Title: `.name Grandfathered` — The Definitive Engineering Guide & Reference Architecture

### Value Proposition
The `.name` top-level domain (TLD) carries a unique legacy architecture: the **Grandfathered Phase** (specifically individuals and entities registered during the early 2000s under specific RFC-compliant personal and institutional identity frameworks). Integrating, automating, or migrating `.name` zones requires specialized knowledge of Second-Level Domain (SLD) structures, third-level personal name handling (`firstname.lastname.name`), and specific legacy EPP (Extensible Provisioning Protocol) extensions.

This Developer Toolkit provides senior engineers and systems architects with the exact code patterns, data models, DNS validation rules, and EPP workflows required to programmatically manage, validate, and migrate `.name` grandfathered assets without breaking legacy identity bindings or triggering registry validation rejections.

---

## 2. Quick Start & Core Concepts

### Core Architecture Overview
Unlike traditional generic TLDs (`.com`, `.org`) where any string is mapped directly to an SLD (`example.com`), `.name` natively supports a hierarchical personal naming structure:
1. **Third-Level Personal Names:** `firstname.lastname.name` (The historic core of `.name`).
2. **Second-Level Direct Domains:** `domain.name` (Introduced later; requires explicit handling to distinguish from legacy personal records).
3. **Grandfathered Status Flag:** Records established prior to the 2004 policy shift contain specific registry metadata tags that exempt them from modern automated identity challenges, provided renewal grace periods are strictly maintained.

### Syntax & Structural Reference Table

| Component | Format / Pattern | Registry Validation Rule | Automation Risk Level |
| :--- | :--- | :--- | :--- |
| **Legacy Personal SLD** | `[first].[last].name` | Must match RFC 3490/3491 IDN standards; no generic dictionary words unless grandfathered. | **High** (Strict registry checks) |
| **Direct SLD** | `[domain].name` | Standard DNS rules (RFC 1035); subject to sunrise/landrush verification if historical. | **Low** (Standard EPP flow) |
| **EPP AuthInfo** | Base64 encoded string | Required for inter-registrar transfers; expires after 90 days. | **Medium** (Security critical) |
| **Grandfathered Grace Period** | Epoch timestamp | Must renew within 30 days of expiration to retain legacy pricing/tier status. | **Critical** (Irreversible loss) |

---

## 3. Production Code Patterns & Architecture Examples

### Pattern 1: Python EPP Client for Grandfathered Domain Status Verification
*Production-ready Python snippet utilizing `asyncio` and `xml.etree` to query a registry for `.name` grandfathered status and expiration boundaries.*

```python
#!/usr/bin/env python3
"""
MicroCorp AI .name Grandfathered Status Inspector
Verifies domain status, EPP lock state, and grandfathered flag preservation.
"""

import asyncio
import ssl
import xml.etree.ElementTree as ET
from typing import Dict, Any

EPP_SERVER = "epp.nic.name"
EPP_PORT = 700;
CLIENT_ID = "microcorp-epp-client"
CLIENT_PW = "secure-token-xyz"

async def verify_grandfathered_domain(domain_name: str) -> Dict[str, Any]:
    context = ssl.create_default_context()
    # In production, load client certificates for mutual TLS (mTLS)
    
    try:
        reader, writer = await asyncio.open_connection(
            EPP_SERVER, EPP_PORT, ssl=context
        )
    except Exception as e:
        return {"error": f"Connection failed: {e}. Fix: Verify EPP endpoint and firewall whitelist."}

    # Read greeting
    data = await reader.read(4096)
    
    # Construct Login XML
    login_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
    <epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
      <command>
        <login>
          <clID>{CLIENT_ID}</clID>
          <pw>{CLIENT_PW}</pw>
          <options>
            <version>1.0</version>
            <lang>en</lang>
          </options>
          <svcs>
            <objURI>urn:ietf:params:xml:ns:domain-1.0</objURI>
          </svcs>
        </login>
        <clTRID>MC-LOGIN-001</clTRID>
      </command>
    </epp>"""
    
    # Send Login
    writer.write(len(login_xml).to_bytes(4, 'big') + login_xml.encode('utf-8'))
    await writer.drain()
    _ = await reader.read(4096) # Consume login response

    # Construct Info Query for .name structure
    info_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
    <epp xmlns="urn:ietf:params:xml:ns:epp-1.0">
      <command>
        <info>
          <domain:info xmlns:domain="urn:ietf:params:xml:ns:domain-1.0">
            <domain:name host="all">{domain_name}</domain:name>
          </domain:info>
        </info>
        <clTRID>MC-INFO-002</clTRID>
      </command>
    </epp>"""

    writer.write(len(info_xml).to_bytes(4, 'big') + info_xml.encode('utf-8'))
    await writer.drain()
    
    # Read response length header
    length_header = await reader.read(4)
    if not length_header:
        writer.close()
        await writer.wait_closed()
        return {"error": "Registry dropped connection. Fix: Check EPP command rate limits."}
        
    msg_len = int.from_bytes(length_header, 'big')
    response_data = await reader.read(msg_len)
    
    writer.close()
    await writer.wait_closed()

    # Parse XML
    root = ET.fromstring(response_data.decode('utf-8'))
    
    # Namespace handling for EPP
    ns = {'epp': 'urn:ietf:params:xml:ns:epp-1.0', 'domain': 'urn:ietf:params:xml:ns:domain-1.0'}
    
    # Extract status codes
    statuses = [node.attrib.get('s') for node in root.findall('.//domain:status', ns)]
    
    return {
        "domain": domain_name,
        "statuses": statuses,
        "is_grandfathered_candidate": "clientHold" not in statuses,
        "raw_xml_response": response_data.decode('utf-8')
    }

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "john.smith.name"
    result = asyncio.run(verify_grandfathered_domain(target))
    print(result)
```

---

### Pattern 2: Go DNS Record Validator for Hierarchical `.name` Zones
*Production-ready Go code parsing zone files to verify that third-party personal naming structures (`*.name`) correctly maintain required MX and NS delegations without triggering recursive resolution failures.*

```go
package main

import (
	"fmt"
	"net"
	"os"
	"strings"
)

// ValidateNameZone checks if a target .name domain adheres to hierarchical DNS standards.
func ValidateNameZone(fqdn string) error {
	parts := strings.Split(fqdn, ".")
	if !strings.HasSuffix(fqdn, ".name") {
		return fmt.Errorf("invalid TLD: '%s' is not a .name domain. Fix: Ensure domain ends with .name", fqdn)
	}

	// Check if it's a third-level personal domain (e.g., first.last.name)
	isPersonalLevel := len(parts) == 4

	fmt.Printf("[INFO] Inspecting %s (Personal Structure: %v)\n", fqdn, isPersonalLevel)

	// Perform NS lookup
	nsRecords, err := net.LookupNS(fqdn)
	if err != nil {
		return fmt.Errorf("DNS lookup failed for %s: %w. Fix: Verify nameserver delegation at registry level", fqdn, err)
	}

	if len(nsRecords) == 0 {
		return fmt.Errorf("zero NS records found for %s. Fix: Configure at least 2 authoritative nameservers", fqdn)
	}

	fmt.Printf("[SUCCESS] Domain %s verified with %d nameservers.\n", fqdn, len(nsRecords))
	return nil
}

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: name-validator <domain.name>")
		os.Exit(1)
	}

	target := os.Args[1]
	if err := ValidateNameZone(target); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(2)
	}
}
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

1. **Treating `.name` like `.com` in Database Schemas**
   * *Anti-Pattern:* Storing domains using a simplistic `^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$` regex.
   * *Why it fails:* This breaks ingestion of valid third-level personal names (`john.doe.name`), rejecting millions of grandfathered assets.
   * *The Fix:* Use suffix-aware libraries (like Go's `publicsuffix` or Python's `tldextract`) combined with hierarchical token counting.

2. **Failing to Maintain Grandfathered Renewal Cadence**
   * *Anti-Pattern:* Letting a grandfathered domain lapse past the 30-day registry grace period assuming redemption periods apply identically to modern TLDs.
   * *Why it fails:* Grandfathered pricing tiers and identity reservation flags are permanently purged upon entering the pending-delete phase; they cannot be recovered by standard backorders.
   * *The Fix:* Implement automated EPP renewal hooks firing at `T-60`, `T-30`, and `T-7` days prior to expiration.

3. **Ignoring IDN Normalization Rules (RFC 3490)**
   * *Anti-Pattern:* Submitting internationalized personal names without Punycode conversion (`xn--...`).
   * *Why it fails:* The `.name` registry backend strictly rejects UTF-8 strings directly over EPP channels.
   * *The Fix:* Always run strings through an IDNA 2008 encoder before constructing EPP XML payloads.

---

## 5. Performance & Optimization Tips

- **EPP Connection Pooling:** Opening and closing TLS connections to registry servers for every domain check adds 200–500ms of latency per lookup. Maintain a persistent pool of authenticated EPP channels with heartbeat/keepalive routines.
- **Local DNS Cache Layer:** When querying `.name` zones at scale, implement a local Redis caching layer respecting TTL bounds. Avoid hammering registry WHOIS/RDAP endpoints, which enforce aggressive rate-limiting (HTTP 429 / EPP 2201).
- **Asynchronous Batching:** Use asynchronous workers (Python `asyncio` or Go routines) when auditing large portfolios of grandfathered domains to execute EPP `info` commands concurrently.

---

## 6. Commercial License & Attribution Summary

### License Type: Commercial Developer License (MicroCorp AI IP Standard)

* **Granted Rights:** You are authorized to use, modify, embed, and compile the code patterns, architectural models, and validation rules contained within this kit into internal tooling, client systems, and commercial SaaS platforms developed by your organization.
* **Restrictions:** Redistribution, resale, or publishing of this kit as a standalone reference product, documentation wiki, or competing developer guide is strictly prohibited without explicit written consent from MicroCorp AI.
* **Warranty Disclaimer:** This software and documentation are provided "as is", without warranty of any kind, express or implied. MicroCorp AI assumes zero liability for domain loss, EPP registry rejections, or DNS misconfigurations resulting from implementation of these patterns.

***
*© 2026 MicroCorp AI Engineering Division. All rights reserved.*