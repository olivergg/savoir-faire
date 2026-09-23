;; Reusable nREPL connection boilerplate for the nrepl-runtime-audit skill.
;;
;; Run standalone as a connectivity sanity check:
;;   clj -Sdeps '{:deps {nrepl/nrepl {:mvn/version "1.7.0"}}}' -M connect.clj [host] [port] [namespace]
;;   clj -Sdeps '{:deps {nrepl/nrepl {:mvn/version "1.7.0"}}}' -M connect.clj 127.0.0.1 5555 my.app.helpers
;;
;; Or copy this whole file as the starting point for a new investigation script,
;; then add your own (run client session "label" "...code...") calls at the bottom
;; instead of just the sanity check.

(require '[nrepl.core :as nrepl])

(defn eval-remote [client session code]
  (let [msgs (doall (nrepl/message client {:op "eval" :code code :session session}))]
    {:value (some :value msgs)
     :err (not-empty (apply str (keep :err msgs)))
     :out (not-empty (apply str (keep :out msgs)))
     :ex (some :ex msgs)}))

(defn run [client session label code]
  (println (str "\n--- " label " ---"))
  (let [{:keys [value err ex out]} (eval-remote client session code)]
    (when out (println "OUT:" out))
    (if (or err ex)
      (do (println "ERROR:" ex) (when err (println err)))
      (println value))))

(let [[host port ns-name] *command-line-args*
      host (or host "127.0.0.1")
      port (Integer/parseInt (or port "5555"))]
  (with-open [conn (nrepl/connect :host host :port port)]
    (let [client (nrepl/client conn (* 60 1000))
          session (nrepl/new-session client)]
      (when ns-name
        (eval-remote client session (str "(in-ns '" ns-name ")")))

      ;; --- sanity check: confirm the connection and (if given) the namespace work ---
      (run client session (str "connected to " host ":" port)
           "(str (java.net.InetAddress/getLocalHost) \" / \" (System/getProperty \"java.version\"))")

      ;; --- add real checks below this line ---
      )))
