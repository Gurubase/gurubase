## Gurubase Installation

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) `19.0.3` or later.
- [Docker Compose](https://docs.docker.com/compose/install/) (`docker compose` or `docker-compose`) `2.6.1` or later.
- OpenAI API key (for answer generation and embeddings). Get it from [here](https://platform.openai.com/api-keys).
- Firecrawl API key (for website scraping). Get it from [here](https://www.firecrawl.dev/app/api-keys).

### Quick Install

Run this command to install Gurubase:

```bash
curl -fsSL https://raw.githubusercontent.com/Gurubase/gurubase/refs/heads/develop/gurubase.sh -o gurubase.sh
bash gurubase.sh
```

The installer will:
1. Create a `.gurubase` directory in your home folder
2. Prompt for required API keys
3. Download and start all necessary services
4. Open the web interface at http://localhost:8029

### Upgrade

You can upgrade to the latest version by running the following command:

```bash
curl -sSL https://raw.githubusercontent.com/Gurubase/gurubase/refs/heads/develop/gurubase.sh -o gurubase.sh
bash gurubase.sh upgrade
```

### Remove

You can remove Gurubase by running the following command. This will remove the containers and networks but keep the data files.

```bash
curl -sSL https://raw.githubusercontent.com/Gurubase/gurubase/refs/heads/develop/gurubase.sh -o gurubase.sh
bash gurubase.sh rm
```

> [!CAUTION]
> To remove everything including all data (volumes), you can run the following command:
> ```bash
> cd ~/.gurubase && docker compose down --volumes
> ```

### System Requirements

- **Operating System**
  - macOS 10.15 Catalina or later
  - Linux (Ubuntu 20.04 LTS, Debian 10, CentOS 8 or later)
  - ⚠️ Native Windows is not supported, but you can use WSL2 to run Gurubase on Windows.

- **Processor**
  - Quad-core CPU (4 cores) at 2.5 GHz or higher
  - ARM-based processors supported (e.g., Apple M1, M2, M3, etc.)

- **Memory and Storage**
  - 8GB RAM minimum recommended
  - 10GB available disk space (SSD preferred for better performance)

- **Network**
  - Ports 8028 and 8029 must be available

> [!NOTE]
> Only Linux and MacOS are supported at the moment. Native Windows is not supported, but you can use WSL2 to run Gurubase on Windows.

### Services

The following services are installed as part of Gurubase:

| Service | Version | Description |
|---------|---------|-------------|
| Milvus | v2.4.17 | Vector database for storing and searching embeddings |
| RabbitMQ | 3.13.7 | Message broker for task queue management |
| PostgreSQL | 16.3 | Main database for storing application data |
| Redis | 7.2.6 | In-memory data store for caching, rate limiting, and session management |
| Nginx | 1.23.3 | Web server for routing and serving static files |
| Gurubase Backend | latest | [Django](https://www.djangoproject.com/) based backend application |
| Gurubase Frontend | latest | [Next.js](https://nextjs.org/) based frontend application |
| Celery Workers | latest | Background task processors (2 workers) |
| Celery Beat | latest | Periodic task scheduler |

### Data Storage

All data is stored locally in `~/.gurubase/`:
- PostgreSQL data: `~/.gurubase/postgres/`
- Milvus data: `~/.gurubase/milvus/`
- Redis data: `~/.gurubase/redis/`
- Media files: `~/.gurubase/backend_media/`
- Environment variables: `~/.gurubase/.env`

### Backend Django Admin Access

You can access the Django admin interface with the following credentials:

| URL | Email | Password |
|----------|------------------------|----------|
| `http://localhost:8028/admin` | `root@gurubase.io` | `ChangeMe` |

After logging in, you can change the admin password from `http://localhost:8028/admin/password_change/`.

> [!WARNING]
> This interface is intended for advanced users only. Be cautious when making changes as they can affect your Gurubase installation.

### Telemetry

By default, Gurubase collects anonymous telemetry data using [PostHog](https://posthog.com/) to help improve the product. You can opt out of telemetry by following these steps:

1. Edit the frontend environment file `~/.gurubase/.env.frontend`:
```text
NEXT_PUBLIC_TELEMETRY_ENABLED=false
```

2. Recreate the frontend service to apply the new environment:
```bash
cd ~/.gurubase && docker compose up -d --force-recreate frontend
```

## Gurubase Cloud vs Self-hosted

Here's a detailed comparison between Gurubase Cloud and Self-hosted versions:

| Feature | Gurubase Cloud | Self-hosted |
|---------|---------------|-------------|
| Authentication | ✅ Google & GitHub via Auth0 | ❌ Not available |
| API Support | ✅ Full API access | ✅ Full API access |
| Binge | ✅ Follow-up questions & learning graph | ✅ Follow-up questions & learning graph |
| Knowledge Base Sources | ✅ Websites, YouTube, PDFs | ✅ Websites, YouTube, PDFs |
| GitHub Codebase Indexing | ✅ Available | ✅ Available |
| Website Widget | ✅ Available | ✅ Available |
| Base LLM | ✅ OpenAI GPT-4o | ✅ OpenAI GPT-4o |
