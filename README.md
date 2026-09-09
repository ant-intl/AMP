# Agentic Mobile Protocol (AMP)
 
## Quick start

Prerequisites:

- **Python 3.10+**: A virtual environment is created automatically on first run.
- **Node.js and npm**: Frontend dependencies are installed automatically on first run.
- **bash** and standard CLI tools (`curl`, `lsof`) on macOS or Linux.

AMP provides the following sample scenarios. Each script provisions a fresh virtual environment,
installs dependencies, launches all the role services, and starts the web frontend.
| **Sample scenario** | **Launch script** |
| --- | --- |
| Human Not Present | bash ./samples/python/scenarios/human_not_present/start.sh |
| Human Present | bash ./samples/python/scenarios/human_present/start.sh |

**Note**: These scripts are bash-specific. Invoke them with `bash`, not `sh`.

1. Run one of the sample scenarios. Once the startup completes, the script prints the URL for each service. 
2. Open the printed **Web Frontend** URL in your browser to interact with the Shopping Agent.
3. Press `Ctrl+C` to stop all services. 

**Note**: Structured logs and the temporary databases for each run are written under the scenario's `.logs/` and `.temp-db/` folders.

## Project structure

```
amp/
├── docs/                       # Protocol specification and glossary
├── src/python/                 # Reusable, framework-agnostic libraries
│   ├── common/                 # Shared kernel, including events, evidence logging, HTTP client, SQLite store, and money utils
│   ├── mandate_chain/          # Three-layer SD-JWT generation, validation, and mandate service
│   └── schemas/                # Pydantic models for checkout and mandate objects
├── samples/python/             # Runnable role services with scenario launchers
│   ├── acquirer/               # Acquirer service with CGCP routing
│   ├── alipayplus/             # Alipay+ network and mandate services
│   ├── credential_provider/    # Credential Provider service
│   ├── merchant/               # Merchant service
│   ├── mpp/                    # Mobile Payment Provider service
│   ├── shopping_agent/         # Shopping Agent and Web Frontend (Vite/React SPA)
│   └── scenarios/              # Launch scripts for human-present or human-not-present scenarios
├── tests/python/               # Unit tests and mandate_chain examples
└── requirements.txt            # Python dependencies
```

### Shared libraries

| Module | Path | Purpose |
| --- | --- | --- |
| `common` | `src/python/common` | Shared kernel, including events, evidence logging, HTTP client, SQLite store, and money utils |
| `mandate_chain` | `src/python/mandate_chain` | Three-layer SD-JWT generation, validation, and mandate service |
| `schemas` | `src/python/schemas` | Pydantic models for checkout and mandate objects |

## Sample architecture

| Service | URL | 
| --- | --- |
| Shopping Agent | [http://localhost:8080](http://localhost:8080/) | 
| Merchant | [http://localhost:8081](http://localhost:8081/) | 
| Credential Provider | [http://localhost:8082](http://localhost:8082/) | 
| Alipay+ Network | [http://localhost:8083](http://localhost:8083/) | 
| Alipay+ Mandate | [http://localhost:8084](http://localhost:8084/) | 
| Acquirer | [http://localhost:8085](http://localhost:8085/) | 
| Mobile Payment Provider (MPP) | [http://localhost:8086](http://localhost:8086/) | 
| Web Frontend | [http://localhost:8088](http://localhost:8088/) | 

### Roles at a glance

| Role | Directory | Responsibility |
| --- | --- | --- |
| **Shopping Agent** | `samples/python/shopping_agent` | Parses user intent, plans and drives the shopping steps under the AMP protocol (search → checkout → mandate → credential → pay). Holds an EC P-256 key and signs L3. Serves `/task` SSE endpoints consumed by the web frontend. |
| **Merchant** | `samples/python/merchant` | Provides product catalog, creates checkout, and initiates payments towards the acquirer. |
| **Credential Provider** | `samples/python/credential_provider` | Enrolls payment methods, creates and inquires mandate sessions. |
| **Alipay+ Network** | `samples/python/alipayplus` | Serves as the payment network orchestration and routing layer. |
| **Alipay+ Mandate** | `samples/python/alipayplus` | Manages the mandate lifecycle: creates mandates, applies budget deductions, advances mandate status, and validates mandates against constraints. |
| **Acquirer** | `samples/python/acquirer` | Recognizes CGCP tokens, routes requests by token prefix, and forwards them to the Alipay+ Network. |
| **Mobile Payment Provider (MPP)** | `samples/python/mpp` | Responsible for user authorization, IDV completion, and payment. |
| **Web Frontend** | `samples/python/shopping_agent/web_frontend` | Vite + React + TypeScript SPA that consumes agent SSE events and renders the protocol chain, IDV confirmation, and receipt cards. |

## Tech stack

- **Backend:** Python 3.10+, FastAPI, Starlette, Uvicorn, Pydantic v2
- **Cryptography/tokens:** `cryptography`, `jwcrypto`, `sd-jwt` (SD-JWT per RFC 9901,
  ES256 signatures)
- **HTTP:** `httpx` for inter-service calls
- **Frontend:** Vite + React 18 + TypeScript + SCSS (`lucide-react` icons)
- **Persistence (demo):** per-run SQLite / JSON stores under `.temp-db/`

## Contact

For security issues, please reach out to
alipayplus_amp@ant-intl.com.

## License

See [LICENSE](LICENSE).
