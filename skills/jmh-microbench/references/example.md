# Worked examples

Two real benchmarks from a JSON-heavy endpoint perf pass (JSON round-trip removal). Copy the closer one and adapt field names/types rather than starting blank.

## Example 1 — timing only: two ways to read a flat JSON field

Question: is `JsonNode#path("state")` (direct field-map lookup) cheaper than `JsonNode#at("/state")`
(compiles a `JsonPointer` on every call) for a flat, non-nested key? Answer found: yes, ~2.5x.

```java
package bench;

import java.util.concurrent.TimeUnit;

import org.openjdk.jmh.annotations.*;
import org.openjdk.jmh.infra.Blackhole;
import org.openjdk.jmh.runner.Runner;
import org.openjdk.jmh.runner.RunnerException;
import org.openjdk.jmh.runner.options.Options;
import org.openjdk.jmh.runner.options.OptionsBuilder;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

@State(Scope.Thread)
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.NANOSECONDS)
@Warmup(iterations = 5, time = 1, timeUnit = TimeUnit.SECONDS)
@Measurement(iterations = 5, time = 1, timeUnit = TimeUnit.SECONDS)
@Fork(value = 5)
public class JsonAccessJmhBench
{
    private JsonNode node;

    @Setup
    public void setup() throws Exception
    {
        node = new ObjectMapper().readTree(
            "{\"state\":1,\"reason\":42,\"use_case\":3,\"start_date\":\"2026-08-12T08:40:53\"}");
    }

    @Benchmark
    public void at(Blackhole bh) { bh.consume(node.at("/state").asInt()); }

    @Benchmark
    public void path(Blackhole bh) { bh.consume(node.path("state").asInt()); }

    public static void main(String[] args) throws RunnerException
    {
        new Runner(new OptionsBuilder().include(JsonAccessJmhBench.class.getSimpleName()).build()).run();
    }
}
```

Result (25 samples, 5 forks x 5 iterations): `at` 5.93 ± 0.08 ns/op, `path` 2.39 ± 0.07 ns/op — CIs
disjoint, real and reproducible.

## Example 2 — timing + allocation: intermediate Map vs direct object construction

Question: how much extra garbage does building a `HashMap<String,Object>` per row (Hibernate's
`Transformers.ALIAS_TO_ENTITY_MAP`) cost versus mapping a JDBC/tuple row directly into the target
object (a custom `ResultTransformer`/`TupleTransformer`)? Isolates just the mapping mechanism — no
real Hibernate/JDBC round trip, which would drown the allocation signal in network/DB time.

```java
package bench;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

import org.openjdk.jmh.annotations.*;
import org.openjdk.jmh.profile.GCProfiler;
import org.openjdk.jmh.runner.Runner;
import org.openjdk.jmh.runner.RunnerException;
import org.openjdk.jmh.runner.options.Options;
import org.openjdk.jmh.runner.options.OptionsBuilder;

@State(Scope.Thread)
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.NANOSECONDS)
@Warmup(iterations = 5, time = 1, timeUnit = TimeUnit.SECONDS)
@Measurement(iterations = 5, time = 1, timeUnit = TimeUnit.SECONDS)
@Fork(value = 5)
public class RowMappingAllocBench
{
    // pre-boxed fixture values, shared by both benchmarks, built once in @Setup - see SKILL.md
    // step 2 for why: avoids incidental (un)boxing differences skewing the comparison.
    private Long id;
    private String name;

    @Setup
    public void setup() { id = 42L; name = "ACME"; }

    static final class TargetRow
    {
        final Long id;
        final String name;
        TargetRow(Long id, String name) { this.id = id; this.name = name; }
    }

    /** Mechanism A: row -> intermediate Map -> read back into the target (current pattern). */
    @Benchmark
    public TargetRow viaIntermediateMap()
    {
        Map<String, Object> row = new HashMap<>();
        row.put("id", id);
        row.put("name", name);
        return new TargetRow((Long) row.get("id"), (String) row.get("name"));
    }

    /** Mechanism B: row -> target object directly, no intermediate Map. */
    @Benchmark
    public TargetRow directToObject()
    {
        return new TargetRow(id, name);
    }

    public static void main(String[] args) throws RunnerException
    {
        Options opt = new OptionsBuilder()
            .include(RowMappingAllocBench.class.getSimpleName())
            .addProfiler(GCProfiler.class)   // this is what unlocks gc.alloc.rate.norm
            .build();
        new Runner(opt).run();
    }
}
```

Real result (18-column version of this exact benchmark, matching a real DAO row shape): `viaIntermediateMap`
142.0 ns/op, 936 B/op allocated; `directToObject` 12.4 ns/op, 88 B/op allocated — ~10.6x more garbage
and ~11.5x more time for the intermediate `Map`, 25 samples, tight CIs. Scales linearly with row
count returned by the query.

## Reading the output

The run prints per-fork iterations first (noise, skim past it), then a `Result "bench.X.method"`
block per benchmark with `min/avg/max` and a confidence interval, and finally a summary table:

```
Benchmark                                                   Mode  Cnt     Score     Error   Units
RowMappingAllocBench.directToObject                         avgt   25    12,381 ±   0,896   ns/op
RowMappingAllocBench.directToObject:gc.alloc.rate.norm      avgt   25    88,000 ±   0,001    B/op
RowMappingAllocBench.viaIntermediateMap                     avgt   25   142,028 ±   2,278   ns/op
RowMappingAllocBench.viaIntermediateMap:gc.alloc.rate.norm  avgt   25   936,001 ±   0,001    B/op
```

Report this table (or the relevant rows) verbatim when summarizing results — don't hand-copy just
the average, the `± Error` is part of the claim.
