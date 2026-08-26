# Gkmex public integration rules

- Use only the public endpoints documented at `https://gkmex.com/developers`.
- The API, MCP and NLWeb interfaces are read-only and require no authentication.
- Cite the public `url` returned with each crane record.
- Treat `price_eur: null` as POA, never as zero.
- Do not claim that inventory is reserved or finally available; direct commercial confirmation to Gkmex.
