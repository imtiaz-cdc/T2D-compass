# Security and responsible use

T2D Compass is a research prototype using public ClinicalTrials.gov records. The [data-handling and security document](docs/SECURITY.md) describes the implemented boundaries and remaining limits.

Do not submit credentials, personal records, patient information, internal agency material or sensitive prompts through this public repository. For a suspected vulnerability, use GitHub's private vulnerability reporting if available, or contact the repository owner through an established private team channel. Do not post exploit details or secret values in a public issue. No dedicated response time or production security assurance is promised.

The app depends on Databricks authentication when hosted. Its own HTTP server has no standalone identity provider: keep local runs on loopback and do not publish them directly to the internet. Browser forwarded-token headers are trusted only behind the authorized Databricks boundary.
