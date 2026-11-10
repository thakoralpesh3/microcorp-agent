# Developer Toolkit: .name Grandfathered
*Enterprise Architecture & Migration Reference Guide*

## 1. Product Title & Value Proposition

### 📧 Product Overview
The **`.name` Grandfathered Domain Architecture Kit** is a comprehensive engineering guide and production-ready toolkit for managing legacy, grandfathered personal namespace domains under the `.name` TLD. This kit provides modern developers, systems architects, and domain operations engineers with the precise patterns, DNS configurations, API automation scripts, and routing layers required to maintain, migrate, or modernize legacy `.name` personal profiles without breaking historical integrations or losing SEO equity.

### 💎 Value Proposition
- **Zero-Downtime Migration Paths:** Safely bridge legacy second-level `.name` addresses (e.g., `first.last.name`) to modern multi-tenant cloud architectures.
- **Automated Registry Operations:** Production-ready scripts for managing Extensible Provisioning Protocol (EPP) integrations and WHOIS privacy compliance.
- **Enterprise-Grade Security:** Hardened DNSSEC configurations, TLS termination recipes, and email routing preservation for legacy mailboxes tied to personal namespaces.
- **Save 40+ Engineering Hours:** Skip the guesswork of archaic TLD specifications, registry-specific constraints, and subdomain routing edge cases.

---

## 2. Quick Start & Core Concepts

### 🧠 Core Architectural Concepts
1. **Grandfathered Status:** Second-level `.name` domains registered during the early phases carry specific registry privileges and renewal protections that must be explicitly preserved during registrar transfers.
2. **Forwarding vs. Hosting:** Legacy setups often relied on simple HTTP 302 redirects. Modern production architectures require edge-terminated reverse proxies with preservation of query parameters and URI paths.
3. **The `_domainkey` and MX Fallback:** Because `.name` domains are fundamentally identity-centric, email deliverability (SPF, DKIM, DMARC) requires strict synchronization between the legacy registrar records and modern mail providers.

### ⚡ Clean Syntax & Configuration Reference

| Component | Legacy Configuration | Modern Production Standard | Action Required |
| :--- | :--- | :--- | :--- |
| **Primary Routing** | `A` record pointing to static IP | `CNAME` or `ALIAS` pointing to CDN edge | Update TTL to 300s before cutover |
| **Email Transport** | Direct server delivery via local Postfix | MX records pointing to Google Workspace / Microsoft 365 | Maintain TXT SPF records (`include:_spf.google.com`) |
| **SSL/TLS Certificate** | Single-domain or wildcards (`*.name`) | Automated ACME via Let's Encrypt / Cloudflare | Enforce Strict HSTS (`max-age=63072000`) |
| **API Automation** | Manual web control panel | Terraform / Registry CLI (EPP/REST) | Store registrar API secrets in HashiCorp Vault |

---

## 3. Production Code Patterns & Architecture Examples

### 🌐 Nginx Edge Routing & Path Preservation
*Use this configuration to catch incoming traffic on a legacy `.name` domain and cleanly route it to a modern identity platform or portfolio API with full path and query string preservation.*

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name alexander.smith.name *.alexander.smith.name;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name alexander.smith.name;

    ssl_certificate /etc/letsencrypt/live/alexander.smith.name/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/alexander.smith.name/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers for Identity Domains
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    location / {
        proxy_pass https://identity-provider.internal.svc.cluster.local;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout tuning for edge microservices
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### ⚙️ Terraform Provider Configuration for DNS Management
*Automate DNS record synchronization for `.name` zones using Cloudflare as an authoritative DNS provider while maintaining registrar locking.*

```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }
}

variable "cloudflare_zone_id" {
  type        = string
  description = "The Cloudflare Zone ID for the .name domain"
}

variable "target_destination_ip" {
  type        = string
  description = "Modern server or load balancer IP address"
}

resource "cloudflare_record" "apex_ipv4" {
  zone_id = var.cloudflare_zone_id
  name    = "@"
  kind    = "A"
  value   = var.target_destination_ip
  ttl     = 300
  proxied = true
}

resource "cloudflare_record" "www_alias" {
  zone_id = var.cloudflare_zone_id
  name    = "www"
  kind    = "CNAME"
  value   = "alexander.smith.name"
  ttl     = 300
  proxied = true
}

resource "cloudflare_record" "email_spf" {
  zone_id = var.cloudflare_zone_id
  name    = "@"
  kind    = "TXT"
  value   = "v=spf1 include:_spf.google.com ~all"
  ttl     = 3600
}
```

---

## 4. Common Anti-Patterns & Gotchas to Avoid

| Anti-Pattern | Why It Fails | Correct Engineering Approach |
| :--- | :--- | :--- |
| **Using Naked CNAMEs at the Apex** | DNS RFC specifications prohibit CNAME records at the root (`@`) of a domain. Doing so breaks mail delivery and causes intermittent resolution failures. | Use an ANAME/ALIAS record provided by modern DNS hosts, or point the apex to an IP running an HTTP-redirect edge. |
| **Neglecting EPP Auth Codes During Lock States** | Grandfathered domains often trigger strict registry fraud-prevention locks. Requesting a transfer auth code at the last minute results in 5-day lockouts. | Request and verify EPP auth codes at least 14 days prior to any planned registrar migration. |
| **Hardcoding Legacy Subdomain Paths** | Assuming standard `www.` prefix structures while ignoring second-level splits (`first.last.name`) breaks multi-tenant routing parsers. | Implement dynamic host header parsing that inspects the full multi-level TLD suffix structure. |
| **Dropping WHOIS Privacy Contacts** | Legacy registries handle personal name data differently; unmasked personal addresses expose engineers to scrapers and spam vectors. | Ensure Registry-Level Privacy Proxy (RLPP) is explicitly toggled on during any renewal cycle. |

---

## 5. Performance & Optimization Tips

- **Edge Caching Static Assets:** Configure Cache-Control headers with `stale-while-revalidate=86400` on your CDN for static profile assets hosted on personal `.name` endpoints.
- **TLS Session Resumption:** Enable TLS 1.3 0-RTT (Zero Round Trip Time) on your edge load balancers to minimize handshake latency for returning visitors accessing portfolio micro-frontends.
- **Anycast DNS Resolution:** Route all `.name` DNS queries through an Anycast network (e.g., Cloudflare, Route53, or DNSimple) to reduce global DNS lookup latency below 30ms.
- **Preload HSTS:** Submit your grandfathered domain to the Chromium HSTS preload list to eliminate the initial HTTP-to-HTTPS redirect round trip on modern browsers.

---

## 6. Commercial License & Attribution Summary

### 📜 MicroCorp AI Enterprise Source License (MASL-v1.0)
*Copyright © 2026 MicroCorp AI. All rights reserved.*

1. **Grant of Rights:** MicroCorp AI grants the purchaser a perpetual, non-exclusive, worldwide license to use, modify, and integrate the code patterns and architectural guidelines contained within this toolkit into internal and commercial software products.
2. **Restrictions:** You may not resell, sublicense, or redistribute this document or its constituent code blocks as a standalone developer reference product or template kit without express written consent from MicroCorp AI.
3. **Warranty Disclaimer:** This software and documentation are provided "as is", without warranty of any kind, express or implied. In no event shall MicroCorp AI be liable for any claim, damages, or liability arising from the deployment of legacy domain routing configurations.