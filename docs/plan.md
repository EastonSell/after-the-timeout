# Implementation plan
1. Define operation outcome and deterministic mock-service contracts.
2. Test committed timeout, uncommitted timeout, explicit denial and missing status semantics.
3. Implement bounded recovery with operation IDs and read-only status inspection; compare a blind-retry baseline.
4. Run reproducible synthetic fault corpus and save outcome/call counts.
5. Author an original reusable skill and public interface atlas, validate files and sanitization. No proprietary skill text is copied.
