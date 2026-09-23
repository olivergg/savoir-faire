---
name: jmh-microbench
description: >-
  Measure CPU time and memory allocation of a targeted Java code path with a
  standalone JMH microbenchmark, before deciding whether an optimization is
  worth doing — no build-file changes to the target project, no full app
  boot. Works against any Maven or Gradle Java project. Also triggers for:
  JMH, microbenchmark, benchmark, perf test, allocation profiling, gc profiler,
  gc.alloc.rate, -prof gc, measure performance, is X faster than Y, compare
  two implementations, mesurer les perfs, comparer perf.
metadata:
  author: Olivier G
---

## Gotchas

- **Non-default package required** — JMH's annotation processor refuses to generate runner classes for a class in the default package ("Benchmark class should have package other than default"). Always put the benchmark in a named package (e.g. `bench`).
- **`-processorpath` is what makes JMH work** — without passing the same classpath as `-processorpath` to `javac`, no `*_jmhType*`/`*_jmhTest*` classes get generated and `java -cp ... bench.YourBench` fails with `ClassNotFoundException` on a class that "should" exist. Verify generation succeeded: `find classes -name "*jmhType*"` should list several files before running.
- **`@Fork(5)` or more, not 1** — a single JVM's JIT profiling/inlining decisions can bias one run. The signal that matters is whether the confidence intervals across forks are disjoint (no overlap), not a single number. 5 is not arbitrary: it's JMH's own built-in `MEASUREMENT_FORKS` default when no `@Fork` annotation is present at all — matching it means results are directly comparable to any other JMH run you or a teammate produces later.
- **`Mode.AverageTime`, not JMH's own default `Mode.Throughput`** — always set `@BenchmarkMode(Mode.AverageTime)` explicitly. `ns/op` ("how much does one call cost") is the natural unit for "is A faster than B" questions; `Throughput`'s `ops/s` answers a different question (how many calls fit in a second under contention) and is harder to reason about for a single-threaded comparison.
- **1s warmup/measurement iterations here are a speed tradeoff, not the "correct" value** — JMH's own defaults are 5 iterations × 10s each for both warmup and measurement (≈100s per fork, ≈500s for 5 forks, per `@Benchmark` method). 1s iterations (this skill's default, see step 2) get a usably clean signal in a fraction of the time when the two things being compared are meaningfully different (as in every example in this skill). If two candidates are close and the 1s-iteration confidence intervals overlap, re-run with the full 10s iterations before concluding "no difference" — don't just shrug off an ambiguous quick result.
- **Cold-start-dominated code needs `Mode.SingleShotTime`, not `Mode.AverageTime`** — if the real call site never gets JIT-warmed in production (a rarely-invoked batch/admin path, a cold-start-sensitive function), `AverageTime` measures JIT-optimized steady state that the real code will never reach, which misrepresents it. Use `@BenchmarkMode(Mode.SingleShotTime)` with `@Warmup(iterations = 0)` instead — JMH's own defaults already special-case this mode to skip warmup entirely, confirming it's meant for exactly this "measure it cold" situation.
- **Isolate the mechanism, not the whole request** — if the real code path touches a DB or the network, do NOT benchmark that whole round trip: the I/O time (milliseconds) drowns the CPU/allocation signal (nanoseconds) you're actually trying to measure. Extract just the piece under comparison (same types, same shape) into the benchmark, mirroring the real code.
- **`Blackhole.consume(...)` or a non-void return type is mandatory** — otherwise the JIT can prove the computed value is never used and eliminates the whole call, and the benchmark silently measures ~0. Every `@Benchmark` method must either return its result or pass it to `Blackhole.consume(...)`.
- **Don't add JMH to the target project's build file** for a one-off measurement — resolve the jars from the local Maven repo (`mvn dependency:get`, or `gradle` module cache) into a scratch classpath instead, and keep the benchmark `.java` file outside the repo (job tmp dir). This is throwaway measurement tooling, not a permanent test.
- **For allocation questions, add the GC profiler, don't guess from timing alone** — `GCProfiler` ships inside `jmh-core` (no extra dependency), and reports `gc.alloc.rate.norm` (bytes allocated per operation), which is the metric that actually answers "how much garbage does this create."
- **`@State` fields must be non-final (and non-constant-foldable)** — if the JIT can prove an input never changes (a `final` field, or a value it can inline at compile time), it can constant-fold the whole computation and the benchmark measures the folded shortcut, not the real mechanism. Build fixture values in `@Setup` and assign to plain instance fields.
- **Don't loop inside a `@Benchmark` method to "reduce call overhead"** — JMH already amortizes per-invocation overhead correctly (`Mode.AverageTime`/`Throughput` account for it); a hand-rolled loop invites the JIT to hoist/eliminate iterations and biases the result instead of fixing anything.

# JMH — Standalone Java Microbenchmarks

Use this when you need a real, measured answer to "is A faster/lighter than B?" for a small,
well-defined Java mechanism (a field lookup, a row-mapping strategy, a serialization approach)
before spending effort on an optimization — not for end-to-end request latency (use APM/profiling
in that case). Works against any Maven or Gradle Java project; nothing here is specific to a
particular codebase.

## 1. Resolve the classpath (no build-file edits to the target project)

Get the target module's full dependency classpath (matches exactly what the real code compiles
against). If the target project pins a specific JDK version (check its README/CI config/`.sdkmanrc`),
switch to it first — a mismatched JDK can silently change reflection/interface resolution behavior
between the benchmark and the real code path.

Maven:

```bash
mkdir -p /tmp/bench && cd /path/to/target-project
mvn -pl <module> dependency:build-classpath -Dmdep.outputFile=/tmp/bench/module-cp.txt -q
```

Gradle — a throwaway init script prints the resolved runtime classpath without touching the
project's build files:

```bash
mkdir -p /tmp/bench && cd /path/to/target-project
cat > /tmp/bench/print-cp.gradle <<'EOF'
allprojects {
  tasks.register('printBenchCp') { doLast { println sourceSets.main.runtimeClasspath.asPath } }
}
EOF
./gradlew -q --no-configuration-cache -I /tmp/bench/print-cp.gradle :<module>:printBenchCp \
  > /tmp/bench/module-cp.txt
```

Pull JMH itself (core + the annotation processor that generates the runner classes) into the local
`.m2`, via a throwaway pom rather than touching the project's:

```bash
mvn dependency:get -Dartifact=org.openjdk.jmh:jmh-core:1.37 -q
mvn dependency:get -Dartifact=org.openjdk.jmh:jmh-generator-annprocess:1.37 -q
```

Then build a combined classpath (JMH + whatever the benchmark itself needs, e.g. `jackson-databind`)
with a scratch pom — see `references/setup.md` for the exact throwaway-pom recipe used to resolve
this reliably (plain `find ~/.m2` guessing at matching Jackson/JMH sub-versions is fragile — Jackson
ships `databind`/`core`/`annotations` at slightly offset version numbers, and mismatches produce
confusing `NoClassDefFoundError`s at runtime, not at compile time).

## 2. Write the benchmark

Read `references/example.md` for two full worked templates (timing-only, and timing+allocation via
`-prof gc`) before writing a new one — copy the closer one and adapt rather than starting blank.

Non-negotiable shape:

```java
package bench;   // MUST NOT be the default package

@State(Scope.Thread)
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.NANOSECONDS)
@Warmup(iterations = 5, time = 1, timeUnit = TimeUnit.SECONDS)
@Measurement(iterations = 5, time = 1, timeUnit = TimeUnit.SECONDS)
@Fork(value = 5)
public class YourBench
{
    @Setup
    public void setup() { /* build fixtures once, shared by all @Benchmark methods */ }

    @Benchmark
    public SomeType approachA() { ...; return result; }   // returned value is consumed by JMH

    @Benchmark
    public void approachB(Blackhole bh) { ...; bh.consume(a); bh.consume(b); }   // several results

    public static void main(String[] args) throws RunnerException
    {
        Options opt = new OptionsBuilder()
            .include(YourBench.class.getSimpleName())
            // .addProfiler(GCProfiler.class)   // uncomment for allocation numbers, see step 4
            .build();
        new Runner(opt).run();
    }
}
```

Feed every `@Benchmark` method the *exact same* pre-built fixture values (built once in `@Setup`,
shared via instance fields) — if two approaches consume different objects, an incidental
(un)boxing or object-identity difference can skew the comparison in ways that have nothing to do
with the mechanism you're actually testing.

## 3. Compile and run

```bash
CP="$(cat /tmp/bench/jmh-cp.txt):$(cat /tmp/bench/module-cp.txt)"   # from step 1 / references/setup.md
mkdir -p /tmp/bench/classes
javac -cp "$CP" -d /tmp/bench/classes -processorpath "$CP" /tmp/bench/bench/YourBench.java
find /tmp/bench/classes -name "*jmhType*"   # sanity check: must NOT be empty

java -cp "/tmp/bench/classes:$CP" bench.YourBench > /tmp/bench/output.log 2>&1
```

Run this as a background command (`run_in_background: true`) — 5 forks × (5 warmup + 5 measured
iterations × 1s) per `@Benchmark` method easily takes 1-3 minutes. Watch for completion with a
Monitor tool call polling for the line `^Benchmark ` in the log (that's the final results table
header), not a fixed sleep.

## 4. For memory/allocation questions: add the GC profiler

Add `.addProfiler(GCProfiler.class)` to the `OptionsBuilder` in `main()` (import
`org.openjdk.jmh.profile.GCProfiler` — already on the classpath via `jmh-core`, no new dependency).
This adds secondary results per benchmark: `gc.alloc.rate.norm` (bytes/op — the number that answers
"how much garbage per call") alongside `gc.alloc.rate`, `gc.count`, `gc.time`.

## 5. Read the results honestly

- Report the full table (`Score ± Error`), not a cherry-picked run — the summary table at the end
  already aggregates all forks×iterations correctly.
- Before claiming "A is faster/lighter than B", check the confidence intervals don't overlap
  (e.g. A's `[min, max]` range vs B's). If they do overlap, the difference is noise, say so.
- Scale the per-op number to the real call site's volume (rows per request, calls per second) before
  deciding whether the difference is worth acting on — a 10x allocation difference measured in tens
  of bytes per call is usually still negligible; the same ratio at kilobytes per call, over
  thousands of calls, is not. Don't optimize a cost that's dwarfed by the I/O (DB/network) the real
  code path already pays on every call.

## 6. Clean up

Benchmark `.java`/`.class` files are throwaway — keep them under a scratch/job tmp dir, never commit
them to the project repo, unless the user explicitly asks to keep one as a permanent regression
benchmark.
