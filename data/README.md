# Optional stopping data (not bundled)

The source repository does not redistribute downloaded datasets or caches.
Public accessibility does not imply that GSRIM can relicense them under MIT.

- IAEA stopping database: https://www-nds.iaea.org/stopping/
  Obtain the bulk tuples CSV from the provider and place StoppingPower.csv at
  data/stopping/extracted/StoppingPower.csv. The existing parser expects the
  provider's CSV schema; upstream schema changes may require updates.
- NIST PSTAR/ASTAR: https://physics.nist.gov/PhysRefData/Star/Text/
  The loader accepts numeric HTML tables under data/stopping/nist/, named
  PSTAR_<material-id>_<symbol>.html or ASTAR_<material-id>_<symbol>.html
  (for example PSTAR_014_Si.html). A form page or error page is not a table.

Check provider terms before downloading, using or redistributing data. Keep
the source URL, retrieval date and original file hash with research results.

Without suitable tables, the default table mode falls back to analytic BV
stopping; LS is also selectable. Results are NOT guaranteed to match a local
installation with datasets. Inspect reported stopping_sources and warnings.
Data-dependent tests skip when their required files are absent.
