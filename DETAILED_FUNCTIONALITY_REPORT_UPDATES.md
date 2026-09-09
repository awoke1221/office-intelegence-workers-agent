## Recent changes (QA & enterprise readiness)

- Implemented frontend login token scaffolding (browser-stored bearer token). Frontend includes small token UI and client requests include `Authorization` when a token is saved.
- Updated Next.js API proxy to forward incoming `Authorization` and `Cookie` headers to the backend so protected endpoints can be proxied through the app server.
- Added client-side and server-side upload validation: 10 MB default max file size; allowed file types: PDF, CSV, XLSX, XLS, DOCX, DOC, PNG, JPG, JPEG. Backend returns HTTP 413 for oversize files and 400 for unsupported types.
- Improved proxy JSON parsing and normalized error responses for the frontend.
- Implemented SSE streaming proxy for plan execution, forwarding auth header from client.
- Added UI polish and microcopy improvements across `app/page.tsx` (placeholders, ARIA labels, warnings for irreversible actions, report code execution controls).
- Added minimal test scaffolding (`tests/test_health.py`) and a GitHub Actions CI workflow (`.github/workflows/ci.yml`) to run backend tests.

Next recommended steps:

- Harden code execution: run `python_execute` in an isolated container/sandbox and add runtime resource limits.
- Add per-user role-based access control and session management (OAuth or JWT flows).
- Add monitoring & rate-limiting to protect long-running MCP tools.
- Implement frontend visual refinements: interactive execution timeline, charts, and audit-log viewer.
