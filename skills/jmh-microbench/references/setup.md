# Resolving the JMH + target-dependency classpath reliably

Guessing matching jar versions by browsing `~/.m2/repository` directly (e.g. picking
`jackson-databind-2.22.1.jar` and `jackson-annotations-2.22.0.jar` because they're both "2.22-ish")
is fragile — Jackson (and most multi-artifact libraries) ship `databind`/`core`/`annotations` at
independently-bumped version numbers, and a mismatched trio compiles fine but fails at runtime with
a confusing `NoClassDefFoundError` deep in a class you didn't write (e.g.
`JacksonAnnotationIntrospector.<clinit>` failing because `annotations` is older than `databind`
expects). Let Maven resolve the compatible set instead.

## Recipe: a throwaway pom, resolved once

```bash
mkdir -p /tmp/bench
cat > /tmp/bench/jmh-pom.xml <<'EOF'
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>tmp</groupId>
  <artifactId>jmh-bench</artifactId>
  <version>1.0</version>
  <dependencies>
    <dependency>
      <groupId>org.openjdk.jmh</groupId>
      <artifactId>jmh-core</artifactId>
      <version>1.37</version>
    </dependency>
    <dependency>
      <groupId>org.openjdk.jmh</groupId>
      <artifactId>jmh-generator-annprocess</artifactId>
      <version>1.37</version>
    </dependency>
    <!-- add whatever the benchmark itself needs, matching the target module's actual version -->
    <dependency>
      <groupId>com.fasterxml.jackson.core</groupId>
      <artifactId>jackson-databind</artifactId>
      <version>2.22.1</version>
    </dependency>
  </dependencies>
</project>
EOF

mvn -f /tmp/bench/jmh-pom.xml dependency:build-classpath -Dmdep.outputFile=/tmp/bench/jmh-cp.txt -q
```

`jmh-cp.txt` now contains a single colon-separated classpath with every jar at a mutually-compatible
version, ready to pass to both `javac -cp`/`-processorpath` and `java -cp`.

If the benchmark needs to call real project code (not just simulate a mechanism), also resolve the
target module's own classpath and concatenate the two files' contents with `:`:

```bash
mvn -pl <module> dependency:build-classpath -Dmdep.outputFile=/tmp/bench/module-cp.txt -q
CP="$(cat /tmp/bench/jmh-cp.txt):$(cat /tmp/bench/module-cp.txt)"
```

For a Gradle project, resolve the module's runtime classpath the same way you did in step 1 and
concatenate it instead.

## Finding the right JMH version

`1.37` is a known-good recent JMH release as of this writing. If `dependency:get` fails to resolve
it (JMH cuts new releases occasionally), check what's already cached locally first:

```bash
find ~/.m2/repository/org/openjdk/jmh -maxdepth 2 -type d
```

and fall back to whatever version is already present, or the latest on Maven Central, rather than
insisting on 1.37 specifically — the API used by this skill (`@Benchmark`, `@Fork`, `Blackhole`,
`GCProfiler`, `OptionsBuilder`) has been stable across JMH 1.2x-1.3x.
