# Verification before showing

## Headless render (Chrome)
```bash
CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"   # or google-chrome / chromium
"$CH" --headless=new --enable-logging=stderr --window-size=1600,1100 \
  --virtual-time-budget=20000 --screenshot=/tmp/shot.png "file://$PWD/out.html#state" 2>/tmp/console.log
grep -E 'CONSOLE.*(Error|Uncaught)' /tmp/console.log
```
- **First prove errors are captured**: inject a deliberate `throw` once and check it shows
  up in the log; otherwise "no errors" means nothing.
- A blank chart with no axes usually means a library did not load (CDN blocked) — inline it
  or drop it; with axes but no data, check the data join and time parsing.
- Use the URL hash (or a test copy that pre-selects state) to render specific entity/day/
  mode/excerpt/scrub positions; render several positions per excerpt and per run.
- Animations are caught mid-way by headless capture: check final layouts with
  `--force-prefers-reduced-motion`, and say the animations themselves were not watched.

## Inspect the screenshots
Overlapping labels, axis text colliding between stacked charts, lines bridging idle gaps,
legends wrapping badly, empty states, dark mode contrast, page taller than the viewport.

## Checklist to report
- Fidelity: recomputed rows vs real rows per excerpt and run (n/N), service port vs real
  objects over the period (n/N), any mismatch explained.
- Renders: number of states rendered, JS errors (0), themes, reduced motion.
- What is approximated or didactic, and what could not be verified (real browser smoothness,
  Safari/iOS, very long periods).
