# Setting up the server-side helper namespace

If the target app has an nREPL server but no helper namespace yet, these are the
minimum functions worth having loaded server-side (as a `.clj` resource the app loads
at boot, or pasted into the REPL once per session). Adapt bean/table names to the
target app — these are illustrative, not literal requirements.

```clojure
(ns your.helper.namespace
  (:require [clojure.walk :as walk]))

(defn all-contexts
  "Root WebApplicationContext + every DispatcherServlet child context. Spring MVC
   infrastructure beans (RequestMappingHandlerMapping, controllers, ...) commonly
   live in a child context, not the root. WebApplicationContextUtils/getWebApplicationContext
   returns ONLY the root, so enumerate the FrameworkServlet.CONTEXT.* attributes."
  []
  (when-let [root (org.springframework.web.context.ContextLoader/getCurrentWebApplicationContext)]
    (let [sc (.getServletContext root)]
      (cons root (->> (enumeration-seq (.getAttributeNames sc))
                      (filter #(.startsWith % "org.springframework.web.servlet.FrameworkServlet.CONTEXT."))
                      (keep #(.getAttribute sc %)))))))

(defn get-bean
  "Look up a Spring bean by id across root AND child contexts - checking only root
   silently reports 'not found' for MVC beans. NOTE: getBeanNamesForType returns a
   String[], not an Enumeration (don't cast it: ClassCastException)."
  [id]
  (some (fn [ctx] (try (.getBean ctx id) (catch Exception _ nil))) (all-contexts)))

(defn unproxy
  "Strip Spring AOP proxies (@Transactional, @Async...) down to the target object -
   private fields live on the target, not the proxy."
  [bean]
  (if (instance? org.springframework.aop.framework.Advised bean)
    (recur (.getTarget (.getTargetSource bean)))
    bean))

(defn- find-field [^Class c fname]
  (when c
    (or (try (.getDeclaredField c fname) (catch NoSuchFieldException _ nil))
        (recur (.getSuperclass c) fname))))

(defn- accessible-field [obj fname]
  (doto (or (find-field (class obj) fname)
            (throw (ex-info (str "no field " fname " on " (class obj)) {})))
    (.setAccessible true)))

(defn private-field
  "Read a private field of a plain object, searching superclasses too."
  [obj fname]
  (.get (accessible-field obj fname) obj))

(defn get-field-val-from-bean [bean-id fname]
  (private-field (unproxy (get-bean bean-id)) fname))

(defn set-field-val-from-bean
  "Mutates the live singleton - memory-only, gone at next restart, but visible to
   every request until then."
  [bean-id fname v]
  (let [target (unproxy (get-bean bean-id))]
    (.set (accessible-field target fname) target v)))

(defn begin-tx []
  (let [session (.openSession (get-bean "sessionFactory"))
        tx (.beginTransaction session)]
    [session tx]))

(defmacro with-session
  "Opens a plain Hibernate session/transaction directly - NOT registered with
   Spring's TransactionSynchronizationManager. Fine for raw SQL/read-only
   queries via `query` below. Do NOT use this to call a DAO/service method
   that expects a real Spring-managed transaction (it'll throw 'Could not
   obtain transaction-synchronized Session for current thread') - use
   TransactionTemplate for those instead (see the main SKILL.md, recipe 2)."
  [[session tx] & body]
  `(let [[~session ~tx] (begin-tx)]
     (try
       (let [result# (do ~@body)]
         (.flush ~session) (.commit ~tx) result#)
       (catch Exception e#
         (when (and ~tx (.isActive ~tx)) (.rollback ~tx))
         (throw e#))
       (finally (when (and ~session (.isOpen ~session)) (.close ~session))))))

(defn query
  "Run raw SQL, return a seq of keywordized maps."
  [sql-str & {:as params}]
  (with-session [session tx]
    (let [q (-> session (.createNativeQuery sql-str)
                (.unwrap org.hibernate.query.NativeQuery)
                (.setTupleTransformer (org.hibernate.transform.AliasToEntityMapResultTransformer/INSTANCE)))]
      (doseq [[k v] params] (.setParameter q (name k) v))
      (->> (.getResultList q) (map #(into {} %)) (map walk/keywordize-keys)))))
```

## Verifying it's wired up

From the nREPL connection pattern in the main skill, confirm the namespace loads and
`get-bean` resolves something real before trusting any further check:

```clojure
(run client session "sanity check" "(some? (get-bean \"sessionFactory\"))")
```

If this returns `nil`/`false`, the bean name is wrong for this app, or the helper
namespace isn't actually loaded in the REPL's current `*ns*` - fix that before writing
any real check on top of it.
