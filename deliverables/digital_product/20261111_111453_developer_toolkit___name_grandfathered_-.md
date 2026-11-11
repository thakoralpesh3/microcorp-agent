# Developer Toolkit: .name Grandfathered

## 1. Product Title & Value Proposition
**The Architect’s Guide to Legacy Namespace & Identity Management**

In the modern distributed systems landscape, managing "Grandfathered" identifiers—entities that predate current schema constraints, naming conventions, or global ID policies—is a high-risk operation. This toolkit provides the architectural patterns required to safely migrate, normalize, and interact with legacy namespaces without breaking production dependencies.

**Value Proposition:**
*   **Zero-Downtime Mapping:** Patterns for bridging legacy naming collisions to modern UUID/KSUID schemes.
*   **Resilient Normalization:** Production-tested logic to sanitize and hydrate legacy input.
*   **Schema Stability:** Strategies to prevent regression when modernizing deprecated naming patterns.

---

## 2. Quick Start & Core Concepts

| Concept | Definition | Engineering Priority |
| :--- | :--- | :--- |
| **Shadow Mapping** | Dual-writing legacy names to a `canonical_id` table. | High |
| **Normalization** | Sanitizing legacy input to match new validation constraints. | Critical |
| **Namespace Aliasing** | Providing a soft-migration path for clients using old identifiers. | Medium |
| **Constraint Drift** | The delta between legacy naming rules and modern strict regex. | High |

### Implementation Baseline
```bash
# Verify environment readiness
$ identity-tool check --namespace legacy-alpha --verbose
# Generate mapping schema for migration
$ identity-tool generate-map --input ./legacy.csv --output migration.json
```

---

## 3. Production Code Patterns & Architecture Examples

### Pattern: The "Lookup-Hydrator" Bridge
Use this pattern to resolve legacy names to modern IDs while keeping the legacy identifier as a first-class citizen in your cache.

```go
// Example: Go-based Identity Resolver
func ResolveIdentity(ctx context.Context, input string) (User, error) {
    // 1. Check Cache for legacy mapping
    if id, hit := cache.Get("legacy_map:" + input); hit {
        return db.FetchUser(id)
    }

    // 2. Perform safe lookup on legacy table
    user, err := db.FindByLegacyName(input)
    if err != nil {
        return User{}, fmt.Errorf("identity-lookup: failed to resolve %s: %w", input, err)
    }

    // 3. Update cache asynchronously to keep hot path fast
    go cache.Set("legacy_map:"+input, user.CanonicalID, time.Hour*24)
    
    return user, nil
}
```

### Architecture: Multi-Stage Validation
Never force a legacy identifier directly into a modern column. Use a transformation layer.

1.  **Sanitization:** Trim, case-normalize, and strip invalid characters.
2.  **Lookup:** Verify existence in the `legacy_aliases` look-up table.
3.  **Hydration:** Map to the primary key.

---

## 4. Common Anti-Patterns & Gotchas

*   **The "Direct Update" Trap:** Modifying a legacy name in-place without preserving a reference. *Fix: Always store the legacy-to-canonical mapping in an immutable audit table.*
*   **Over-Reliance on Regex:** Legacy systems often have "special cases" that break strict regex. *Fix: Use a lookup table (whitelist) rather than complex regex patterns for legacy data validation.*
*   **Silent Failures:** Returning `nil` or `404` when an identifier mapping exists but is stale. *Fix: Implement 409 Conflict codes for ambiguous legacy namespaces.*

---

## 5. Performance & Optimization Tips

1.  **Bloom Filters for Membership:** Before hitting your database for a legacy name lookup, query a local Bloom Filter to determine if the name *could* exist. This saves high-latency IO for non-existent legacy requests.
2.  **Lazy Normalization:** Don't clean up all legacy data at once. Normalize on access ("Read-Repair"). This keeps migration loads predictable and manageable.
3.  **Read-Aside Caching:** Legacy naming tables are rarely written to but highly read. Cache these mappings with long TTLs to keep latency sub-10ms.

---

## 6. Commercial License & Attribution Summary

**License: MicroCorp Developer-Use License (MDUL)**
*   **Permitted:** Use this code in private or commercial software, modify for internal needs, and embed within proprietary architectures.
*   **Prohibited:** Redistribution of this toolkit as a standalone product or training course without explicit written permission from The Agency Engineering Division.
*   **Attribution:** Any production code derived from this toolkit should include the following header:
    `// Derived from MicroCorp .name Grandfathered Architecture Kit`

---
*Tooling Tip: If you encounter an "ENOENT" error during deployment of these scripts, run `toolkit --init-env` to ensure your pathing environment is correctly bootstrapped for your specific CI/CD pipeline.*