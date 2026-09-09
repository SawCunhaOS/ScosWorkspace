# Review — Version & Reality Check

**Target:** `ARCHITECTURE-SPINE.md` (jdempotent — Qualidade de Teste Redis, 2026-08-29)
**Method:** Maven Central / Sonatype lookups (search.maven.org solrsearch API + central.sonatype.com) for every named library/version, cross-checked against the repository's actual dependency-managing POM (`scos-bom`) and the actual test source files under `jdempotent/src/test`.

## Verdict

All version and brownfield claims in the spine check out against the web and the repository; no corrections needed, only two minor observations worth a footnote.

## 1. `maven-failsafe-plugin:3.5.4` — CONFIRMED

- Exists on Maven Central. Full version list (search.maven.org, `g:org.apache.maven.plugins AND a:maven-failsafe-plugin`): `3.6.0-M1, 3.5.6, 3.5.5, 3.5.4, 3.5.3, 3.5.2, 3.5.1, 3.5.0, 3.4.0, 3.3.1, 3.3.0, 3.2.5, 3.2.3, 3.2.2, 3.2.1, 3.1.2, 3.1.0, 3.0.0, 3.0.0-M9, 3.0.0-M8`.
- **Lockstep claim verified**: the same query against `maven-surefire-plugin` returns the *identical* version list, in the identical order. Both plugins live in the same `apache/maven-surefire` repo and are released together — the spine's "mesma linha de release... liberados em lockstep" is accurate, not asserted from memory.
- **Minor observation**: 3.5.4 is not the newest GA on either plugin — `3.5.5` and `3.5.6` are newer patch releases (plus a `3.6.0-M1` milestone). The spine's rationale for picking 3.5.4 is deliberate consistency with the `maven-surefire-plugin` version **already pinned in `scos-bom` 1.4.4-SNAPSHOT** (confirmed by reading `~/.m2/repository/br/com/sawcunhaos/scos-bom/1.4.4-SNAPSHOT/scos-bom-1.4.4-SNAPSHOT.pom`, line 421-423: `<artifactId>maven-surefire-plugin</artifactId><version>3.5.4</version>`), not an attempt to track the latest release. This is a sound, internally-consistent choice — flagging only so the reader knows 3.5.4 is "match-the-BOM," not "latest available."

## 2. `testcontainers-bom:2.0.5` — CONFIRMED

- `central.sonatype.com/artifact/org.testcontainers/testcontainers-bom/2.0.5` exists and resolves.
- Note: `search.maven.org`'s solr index (as queried) only surfaced the legacy `1.x` line (up to `1.21.3`) — its index appears stale/incomplete for this artifact. `central.sonatype.com` and web search both confirm the `2.0.x` line (2.0.0–2.0.5) is real and current; Testcontainers-Java's 2.0 major release dropped JUnit 4 support and renamed modules to a `testcontainers-<module>` prefix.
- **Cross-check against the actual repo strengthens confidence**: `jdempotent/pom.xml` depends on `testcontainers-junit-jupiter` (the 2.0-style renamed artifact, not the pre-2.0 `junit-jupiter`), and `audit/pom.xml` depends on `testcontainers-mysql` / `testcontainers-postgresql` (also 2.0-style prefixed names). The repo's own already-resolved dependencies are consistent with the 2.0.5 BOM the spine cites — this isn't a version invented in isolation, it matches what's actually in `~/.m2` and building today.
- Confirmed already governed by `scos-bom` (`testcontainers-bom.version` = `2.0.5` at line 81, imported at line 321-326 of the BOM's POM) — the spine's "já gerenciado pelo scos-bom, sem mudança" claim is accurate, not a new decision.

## 3. Other Stack-table entries

The Stack table in the spine has exactly these two rows; no other named technology/version appears in it. Nothing else to check in that table.

## 4. Brownfield facts cross-checked against the repository — ALL CONFIRMED

| Claim in spine | Verified against | Result |
| --- | --- | --- |
| `PrimeNumbersJdempotentEnableTest` / `...DisableTest` currently lack the `IT` suffix and rely on Testcontainers/Docker Compose | Read both files under `jdempotent/src/test/java/.../redis/test/` | Confirmed: both are `@Testcontainers` classes using `ComposeContainer` against `src/test/resources/docker-compose.yml` (Redis + Redis Sentinel), filenames end in plain `Test`, not `IT`/`ITTest` |
| `InMemoryIdempotentRepositoryTryAcquireTest` does not use Testcontainers | Read the file under `jdempotent/src/test/java/.../core/datasource/` | Confirmed: pure JUnit 5, `ExecutorService`/`CountDownLatch` against `InMemoryIdempotentRepository` (in-memory `ConcurrentHashMap`-backed), no Testcontainers import |
| `RedisIdempotentRepositoryTryAcquireITTest` exists | Read the file under `jdempotent/src/test/java/.../redis/repository/` | Confirmed: exists, already carries the `ITTest` suffix, uses a `@Testcontainers` `GenericContainer` (`bitnami/redis:latest`) |
| Failsafe not yet added / no unit-vs-IT split exists today | Read `jdempotent/pom.xml` | Confirmed: only `maven-compiler-plugin`, `maven-release-plugin`, and a bare `maven-surefire-plugin` (no `<excludes>`) are configured — no Failsafe plugin, no exclusion of `*IT.java`/`*ITTest.java`. Everything, including the already-`ITTest`-suffixed Redis class and the Compose-based Prime Number tests, currently runs under plain `mvn test`/Surefire. This matters beyond naming: Surefire's own default include pattern is `**/*Test.java` (among others), which *also* matches files ending in `ITTest.java` — so today's `RedisIdempotentRepositoryTryAcquireITTest` is swept into Surefire's default inclusion incidentally, by suffix collision, not by any exclusion Surefire applies to `IT`-named files (that behavior belongs to Failsafe, not Surefire). This is exactly the gap AD-6's explicit `<excludes>**/*IT.java,**/*ITTest.java</excludes>` is meant to close, and it's a materially correct diagnosis, not just a naming nitpick. |

## Sources

- [maven-failsafe-plugin — search.maven.org solrsearch](https://search.maven.org/solrsearch/select?q=g:org.apache.maven.plugins+AND+a:maven-failsafe-plugin&core=gav&rows=20&wt=json)
- [maven-surefire-plugin — search.maven.org solrsearch](https://search.maven.org/solrsearch/select?q=g:org.apache.maven.plugins+AND+a:maven-surefire-plugin&core=gav&rows=20&wt=json)
- [org.testcontainers:testcontainers-bom:2.0.5 — Maven Central](https://central.sonatype.com/artifact/org.testcontainers/testcontainers-bom/2.0.5)
- [Releases · testcontainers/testcontainers-java](https://github.com/testcontainers/testcontainers-java/releases)
- Local: `~/.m2/repository/br/com/sawcunhaos/scos-bom/1.4.4-SNAPSHOT/scos-bom-1.4.4-SNAPSHOT.pom`
- Local: `jdempotent/pom.xml`, `jdempotent/src/test/java/br/com/sawcunhaos/foundation/jdempotent/{core/datasource,redis/repository,redis/test}/*.java`
