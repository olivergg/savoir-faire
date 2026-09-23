---
name: nrepl-runtime-audit
description: >-
  Audit a running Java/Spring/Hibernate app's real behavior via a connected
  Clojure nREPL and SQL debug logs — verify dependency versions, entity
  mappings, N+1 regressions, and transaction wiring against real dev data,
  going beyond what code diffs or unit tests alone can prove. TRIGGER when:
  nREPL, live verification, runtime audit, connect nrepl, Clojure nrepl,
  Hibernate statistics, N+1, verify live, verify in prod/dev, SQL debug log,
  HHH warning, ground truth, empirical verification, migration regression,
  master vs branch comparison, is this actually a bug.
metadata:
  author: Olivier G
---

Use this when a suspected regression (dependency bump, ORM migration, refactor) needs
proof beyond reading the diff or trusting the test suite — unit tests only exercise
what they were written for; this methodology exercises the actual running app against
real data.

## Guardrails

nREPL `eval` is unrestricted remote code execution against a live JVM — treat every
connection with that weight, even against dev.

- **Confirm the target before connecting.** Ask the user for host/port explicitly (or
  read it from a project doc) — never assume `127.0.0.1:5555` is safe just because it
  is the example below. If there's any doubt whether the target is dev or something
  shared/prod, stop and ask; nREPL servers are not supposed to exist on prod, but
  misconfiguration happens, and eval there is unbounded blast radius.
- **Default to read-only.** Prefer `query`/plain `SELECT`s and getter calls. Only run
  something that writes (`with-session` flushes and **commits** on success — it is not
  automatically safe) when the check genuinely requires it, and say out loud what will
  be written before running it.
- **Never eval code you haven't read.** Don't paste a snippet from a log, an old
  scratchpad script, or a suggestion you didn't fully parse — a wrong bean name fails
  loud, but a plausible-looking mutating call executes for real. Iterating live is cheap
  only when each step is understood before it runs.
- **Recipe 5 (force-instantiating every bean) can trigger real side effects** — a bean's
  constructor or `@PostConstruct` might send a request, schedule a job, or open a
  connection. Fine to run against dev to catch wiring bugs; don't run it against
  anything you're not prepared to have those side effects fire on.
- **Don't print secrets or raw PII into shared output.** Local dev DBs often hold
  prod-derived data that is real PII — mask sensitive
  fields in query results the same way you would against prod, especially before
  saving a finding to memory.
- **One throwaway `@Test` at a time, always reverted** (recipe 6) — never leave
  diagnostic test code committed, and run it in a separate clone/worktree so it can't
  collide with in-progress branch work.

### Never eval these without explicit human confirmation first

This methodology deliberately uses deep reflection (`Class/forName`, force-instantiating
beans) — a blanket sandbox blacklist like [clojail's](https://github.com/Raynes/clojail)
would break the whole point of it. Instead, treat these categories as a stop-and-ask
line, not a hard block:

- **JVM/process control** — `System/exit`, `Runtime/getRuntime` + `.exec`/`.halt`,
  `ProcessBuilder`, anything that could kill or restart the JVM the app is running in.
- **The nREPL server itself** — stopping or reassigning the app's nREPL server
  bean/socket (its own shutdown hook / `@PreDestroy` does this on purpose; you shouldn't). Losing
  the connection mid-investigation is recoverable; killing the *server* isn't, without
  someone restarting the app.
- **Filesystem writes/deletes** — `clojure.java.io/delete-file`, `spit` outside a
  scratch path, `clojure.java.shell/sh` (shells out — arbitrary OS command execution,
  not just JVM-scoped).
- **Global, JVM-wide redefinition** — `set!`, `alter-var-root`, `with-redefs-fn` (not
  the test-scoped `with-redefs`), `def`/`intern` into app namespaces. These persist
  across every future REPL session and every other user of the running app, not just
  this investigation — the opposite of the "cheap to iterate, easy to revert" property
  this whole methodology relies on.
- **Outbound network calls** — opening a `Socket`, hitting an external URL, or wiring
  data to leave the host. A dev DB can still hold real-looking PII (see the guardrail
  above); don't let a check become an exfiltration path.

## Prerequisite: what the target app needs

This only works if the app embeds an nREPL server (ask the user to start it if it
isn't running — never start a JVM process for them without asking). Confirm before
starting:

- Host/port (e.g. `127.0.0.1:5555`).
- A Clojure helper namespace loaded server-side with at minimum: a `get-bean` that
  searches **every** WebApplicationContext (root *and* child/servlet contexts — Spring
  MVC infra like `RequestMappingHandlerMapping` commonly lives in a child context, not
  root; a `get-bean` that only checks root will report false "not found"s), and a
  `query`/`with-session` pair for raw SQL. If no such namespace exists yet, read
  `references/setup-helper-namespace.md` for what to add.
- For log-mining recipes: SQL debug logging enabled (`org.hibernate.SQL` → `DEBUG`)
  and console output redirected to a file the shell can read (Eclipse: Run/Debug
  Configuration → `Common` tab → `Standard Input and Output` → check `File`).

## Connecting

```bash
clj -Sdeps '{:deps {nrepl/nrepl {:mvn/version "1.7.0"}}}' -M script.clj
```

`scripts/connect.clj` has this boilerplate ready to copy or run standalone as a
connectivity sanity check (`... -M scripts/connect.clj [host] [port] [namespace]`) —
start new investigation scripts from it instead of retyping the pattern below.

Every script follows this shape — write the check as a `code` string, not inline
Clojure, so failures land as data instead of killing the whole script:

```clojure
(require '[nrepl.core :as nrepl])

(defn eval-remote [client session code]
  (let [msgs (doall (nrepl/message client {:op "eval" :code code :session session}))]
    {:value (some :value msgs) :err (not-empty (apply str (keep :err msgs)))
     :out (not-empty (apply str (keep :out msgs))) :ex (some :ex msgs)}))

(defn run [client session label code]
  (println (str "\n--- " label " ---"))
  (let [{:keys [value err ex out]} (eval-remote client session code)]
    (when out (println "OUT:" out))
    (if (or err ex) (do (println "ERROR:" ex) (when err (println err))) (println value))))

(with-open [conn (nrepl/connect :host "127.0.0.1" :port 5555)]
  (let [client (nrepl/client conn (* 60 1000))
        session (nrepl/new-session client)]
    (eval-remote client session "(in-ns 'your.helper.namespace)")
    (run client session "label" "(+ 1 1)")))
```

Never guess an API and assume it's right — when a check throws, read the actual error
(wrong bean name, wrong accessor, wrong transaction context are the common ones) and
fix the next call. Iterating live against the real JVM is cheap; guessing wrong and
reporting a false finding is not.

When a check's code grows past a few lines, don't hand-escape `\"` inside a Clojure
string literal — write the code as its own `.clj` file, `slurp` it, and send that:
syntax errors surface while reading the local file instead of deep inside an eval
string. Validate locally first with `(read-string (str "(" code ")"))` before shipping
it to the JVM.

## Recipes

Each is a decision: "which one answers the question I actually have."

### 1. Which jar did a class really load from?

Answers "does the pom/dependency-tree claim match the running JVM", not just what
`mvn dependency:tree` says on disk (Maven's tree resolution and Eclipse/IDE-deployed
classpaths can disagree — this caught a `dependencyManagement` pin that applied to one
module but silently not a sibling module that pulled the dependency transitively).

```clojure
(-> (Class/forName "fully.qualified.ClassName") .getProtectionDomain .getCodeSource .getLocation)
```

### 2. Real Spring-managed transaction

Needed for any DAO/service call that expects an active Spring transaction — a raw
`with-session`-style helper opens a Hibernate session directly and is **not**
Spring-synchronized, so calling a `@Transactional`-dependent method through it throws
`Could not obtain transaction-synchronized Session for current thread`. Go through the
real transaction manager instead:

```clojure
(let [tm (get-bean "transactionManager")
      tt (org.springframework.transaction.support.TransactionTemplate. tm)]
  (.execute tt (reify org.springframework.transaction.support.TransactionCallback
                 (doInTransaction [_ status] (your-call-here)))))
```

Calling a **service**-layer bean (not the DAO directly) through `get-bean` also works
without this wrapper if the service class carries its own `@Transactional` — you're
then going through the real Spring AOP proxy, which opens the transaction itself.

### 3. Every entity, one real query each, isolated transactions

Sweeps the whole Hibernate metamodel with one real query per entity — catches schema
drift (a mapped entity whose table no longer exists) across the *entire* model, not
just the classes a specific investigation happens to touch.

```clojure
(let [sf (get-bean "sessionFactory")
      entities (.getEntities (.getMetamodel sf))]
  (doall (for [e entities]
           (let [name (.getName e)]
             (try
               (with-session [session tx]
                 (.uniqueResult (doto (.createQuery session (str "select count(x) from " name " x")) (.setMaxResults 1))))
               [:ok name]
               (catch Exception ex [:fail name (.getMessage ex)]))))))
```

**Each entity's query must run in its own transaction** (`with-session` called *inside*
the loop, not wrapped around it). A shared transaction means Postgres poisons the whole
transaction after the first real failure, so every entity checked *after* that point
falsely reports as broken too — this produced 15 false failures from 1 real one until
isolated per-entity.

### 4. Hibernate statistics — settle "is this actually N+1" with numbers

Don't guess from reading code that a lost eager-fetch join causes N+1 — measure it. A
missing `JOIN FETCH` frequently turns out to cost nothing in practice because
Hibernate's session-level persistence context already holds the entity from earlier in
the same query.

```clojure
(let [sf (get-bean "sessionFactory") stats (.getStatistics sf)]
  (.setStatisticsEnabled stats true) (.clear stats)
  (let [result (your-real-call-here)] ; through the REAL consumer path, not just the DAO —
                                        ; a raw DAO call that never touches lazy fields undercounts
    {:query-count (.getQueryExecutionCount stats)
     :entity-load-count (.getEntityLoadCount stats)
     :entity-fetch-count (.getEntityFetchCount stats)      ; >0 means something lazy-loaded
     :collection-fetch-count (.getCollectionFetchCount stats)
     :max-query-time-ms (.getQueryExecutionMaxTime stats)}))
```

Call through the path a real caller actually uses (service → DTO conversion, not just
`dao.loadX()`), or you'll only be measuring the query itself, not what production code
actually triggers when it reads every returned field.

### 5. Force-instantiate every Spring bean

Catches wiring breakage in beans nothing has exercised since boot. Walks root **and**
every servlet child context (`all-contexts` from the helper namespace) — each context
only lists its own definitions, so no duplicates.

```clojure
(doall (for [ctx (all-contexts), n (.getBeanDefinitionNames ctx)]
         (try (if (.isAbstract (.getBeanDefinition (.getBeanFactory ctx) n)) [:skip n]
                  (do (.getBean ctx n) [:ok n]))
              (catch Exception ex [:fail n (str (class ex)) (.getMessage ex)]))))
```

Expect and discount two false-positive shapes before reporting failures as real bugs:
`@Scope("prototype")` beans needing explicit constructor args (fails with
"no qualifying bean" — not a real wiring bug, just not meant to be looked up bare), and
`@Lazy` beans with a genuine unmet precondition (e.g. a missing env var) — forcing
instantiation here bypasses the laziness that would normally prevent the failure in
production.

### 6. Cross-check against the old code for real proof

When you can't get a confident answer from the framework's own docs (checked
`docs.hibernate.org`'s own javadoc once and it simply didn't document the behavior in
question), don't reason from general framework knowledge — reproduce the old behavior
for real:

1. Check out the pre-change ref in a **separate** worktree/clone, not the one with
   in-progress work (`git status --short` first to confirm it's safe to switch).
2. Add **one** throwaway `@Test` method to an existing test class that already has the
   right context/fixtures wired, calling the same method with the same real data,
   logging the result.
3. Run just that method (`-Dtest=Class#method`), read the output.
4. Revert immediately (`git checkout -- <file>`) — never leave throwaway test code
   committed.

### 7. Ground-truth SQL must match the query's own predicate

When comparing a DAO's returned count against "the real data", replicate the query's
*own* filtering condition exactly (e.g. a date-window `WHERE`) — comparing against raw
unfiltered row counts produces a false mismatch that looks like a bug but is actually
comparing two different questions ("how many rows ever" vs "how many rows match right
now").

### 8. Find every instance of a risky pattern across the whole codebase

Don't manually read files one at a time hunting for a known-risky change shape. Rank
files by **real** churn first (`git diff -w --numstat oldref...newref -- 'path/**/*.java'`
— whitespace-insensitive, because line-ending/reformatting noise can make a
byte-identical file look like a full rewrite), then grep each candidate for
occurrences of the specific risky API before/after
(`git show <ref>:<file> | grep -c '.riskyCall('`) to find every file that made the
exact migration shape you're worried about, not just the ones that happened to have
the biggest raw diff.

### 9. Mine the live log for what code-reading won't surface

With SQL debug logging + file-redirected console output running, grep the accumulated
log for signal categories code review wouldn't catch:

- Framework startup warnings (Hibernate's `HHH` codes: composite-id classes missing
  `equals()`/`hashCode()`, ignored/unrecognized query hints, etc.)
- A recurring error message from shared framework code that fires for *any* caller,
  not just the one under investigation (e.g. a generic lookup-table user-type that logs
  "no value found for code X" — grep the message pattern once, get every occurrence
  across the whole app for free).

Every log-mining finding needs the **same rigor as a code-diff finding**: check whether
the flagged class/query is actually different between old and new refs
(`diff <(git show oldref:file) <(git show newref:file)`) before calling it a
regression — plenty of live warnings turn out to be pre-existing and unrelated to
whatever you're investigating.

### 10. Trace a suspected behavior change to real impact, not just "a caller exists"

Finding a caller isn't the answer. For each real caller: read enough of the call site
to classify it (does it actually read the field/value the way that would expose the
difference, or does it ignore/bypass it — e.g. only reads `.getId()` off a richer
return type). Then trace **up** the call chain to the real entry point (REST
controller, a DB write via `.save()`/`.update()`, a scheduled job) to judge actual
blast radius. "Found 3 callers" is not a conclusion; "2 of 3 read the affected field,
one of those persists it, the third only reads an unrelated id" is.

### 11. Find real trigger data before calling something a live bug

A code-level defect and a live incident are different findings — report them as such.
Write the SQL that matches the *exact* business invariant being checked (e.g. "does
any parent id have more than one row currently matching this app's own 'active' window
predicate") and run it against the real dataset. Zero matches means: real bug in the
code, unproven/currently-inert in practice — say exactly that, don't round it up to
"this is broken" or down to "this doesn't matter."

### 12. Verify a live behavior without redeploying — inject a probe into the running object graph

Redeploying to add a temporary `println` is heavy when the only question is "did the
full payload really arrive intact" or "which branch did this take with real data".
Inject a probe directly into the live beans via reflection instead — memory-only, gone
at the next redeploy, no code change, no restart.

**Use the app's existing helper namespace first.** If the app ships helpers, they already encapsulate the fiddly
reflection — reach for them before writing raw reflection by hand:

- `get-bean` — searches root + every servlet/child context (the #1 source of false
  "not found" when only checking root).
- `get-field-val-from-bean` / `set-field-val-from-bean` — read or mutate a private
  field of a Spring bean, handling AOP proxies (`unproxy`) for you. `private-field`
  for a plain object (searches superclasses too).
- `query` — raw SQL through the app's own session wiring.

If the app has none of these, `references/setup-helper-namespace.md` has them all.

Only fall back to hand-rolled reflection when no helper fits (e.g. you need a bean
from a *specific* DispatcherServlet context that `get-bean` won't disambiguate —
enumerate `org.springframework.web.servlet.FrameworkServlet.CONTEXT.<name>`
attributes on the `ServletContext`; `WebApplicationContextUtils/getWebApplicationContext`
returns only ROOT).

Gotchas that cost real time if not known upfront:

- **`getDeclaredField` is called on the `Class`, not the instance** — `(.getDeclaredField (class handler) "f")`, not `(.getDeclaredField handler "f")` (that resolves the method on the *instance's* class, which doesn't have it → misleading `No matching method`).
- **Match method arity exactly** — `reify` methods take `this` explicitly (`(getMessageClass [_] ...)`), `proxy` methods don't (`(getMessageClass [] ...)`). A mismatch surfaces as the misleading `Can't define method not in interfaces: <name>`, which looks like a generics problem but isn't.
- **When `reify` still fights you** (overloads, bridge methods on a generic interface), use `java.lang.reflect.Proxy` + an `InvocationHandler` that switches on the method name — works for any interface.
- **Read the probe's result from a *separate* nREPL call**: each `eval` is stateless. Have the probe write into `System/setProperty` (or a static field), then a later script reads `System/getProperty`. Don't expect the same connection to return the value from an earlier eval.

## After the audit

Findings worth remembering past this session (a confirmed regression, a false alarm
and why, a useful bean/table name for this specific app) belong in memory, not just in
the conversation — see your memory-saving instructions for the right entry type.
