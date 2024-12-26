#!/bin/bash

set -e

# Ensure script can be run from pipe and current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]:-$0}" )" && pwd )"
cd "${SCRIPT_DIR}" 2>/dev/null || cd "$(pwd)"

GURUBASE_DIR="$HOME/.gurubase"
DOCKER_COMPOSE_FILE="$GURUBASE_DIR/docker-compose.yml"

[ ! -f "$GURUBASE_DIR/.env.frontend" ] && touch "$GURUBASE_DIR/.env.frontend"

remove_gurubase() {
    read -p "Are you sure you want to remove Gurubase? [Y/n] " response
    response=${response:-Y}
    if [[ ! $response =~ ^[Yy]$ ]]; then
        echo "❌ Operation cancelled"
        exit 1
    fi

    echo "🗑️  Removing Gurubase containers and networks..."
    # Use the existing docker-compose.yml from GURUBASE_DIR
    if [ -f "$DOCKER_COMPOSE_FILE" ]; then
        cd "$GURUBASE_DIR"
        if command -v docker compose &> /dev/null; then
            docker compose down
        elif docker-compose version &> /dev/null; then
            docker-compose down
        else
            echo "❌ Neither docker-compose nor docker compose is available"
            exit 1
        fi
    else
        echo "❌ docker-compose.yml not found in $GURUBASE_DIR"
        exit 1
    fi
    
    echo "✅ Gurubase containers and networks have been removed"
    echo "ℹ️  Note: Your data files still exist at $GURUBASE_DIR"
    echo "💡 To completely remove all data, you can manually delete this directory with:"
    echo "   rm -rf $GURUBASE_DIR"
    exit 0
}

wait_for_services() {
    echo ""
    echo "⏳ Waiting for services to be ready..."
    docker pull busybox:1.34.1 >/dev/null 2>&1
    docker run --rm --network gurubase-dc busybox:1.34.1 /bin/sh -c "until nc -z gurubase-backend 8008 && nc -z gurubase-nginx 8029 && nc -z gurubase-postgres 5432 && nc -z gurubase-milvus-standalone 19530 && nc -z gurubase-rabbitmq 5672 && nc -z gurubase-redis 6379; do sleep 5; done"
}

create_config_files() {
    echo "📝 Creating configuration files..."
    
    # Create config directory if it doesn't exist
    mkdir -p "$GURUBASE_DIR/config"
    
    # Create Milvus etcd config
    cat > "$GURUBASE_DIR/config/embedEtcd.yaml" << 'EOF'
listen-client-urls: http://0.0.0.0:2379
advertise-client-urls: http://0.0.0.0:2379
quota-backend-bytes: 4294967296
auto-compaction-mode: revision
auto-compaction-retention: '1000'
EOF

    # Create Nginx config
    cat > "$GURUBASE_DIR/config/nginx.conf" << 'EOF'
upstream frontend {
    server gurubase-frontend:3000;
}

upstream backend {
    server gurubase-backend:8008;
}

server {
    listen 8029;
    client_max_body_size 96M;
    http2_max_field_size 64k;
    http2_max_header_size 512k;

    error_log /var/log/nginx/error.log error;
    access_log off;

    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host:$server_port;
    }

    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host:$server_port;
        
        # Streaming support
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 24h;
        chunked_transfer_encoding on;
    }
    
    location /media/ {
        alias /django_media_files/;
    }
}
EOF

    echo "✅ Configuration files created successfully"
}

upgrade_gurubase() {
    read -p "Are you sure you want to upgrade Gurubase? [Y/n] " response
    response=${response:-Y}  # Default to Y if empty
    if [[ ! $response =~ ^[Yy]$ ]]; then
        echo "❌ Operation cancelled"
        exit 1
    fi

    echo "🔄 Upgrading Gurubase..."
    
    # Backup existing docker-compose.yml if it exists
    if [ -f "$DOCKER_COMPOSE_FILE" ]; then
        echo "📑 Backing up existing docker-compose.yml..."
        cp "$DOCKER_COMPOSE_FILE" "${DOCKER_COMPOSE_FILE}.backup"
    fi

    # Download the latest docker-compose.yml
    echo "📥 Downloading latest docker-compose.yml..."
    if ! curl -sSL https://raw.githubusercontent.com/Gurubase/gurubase/refs/heads/selfhosted/docker-compose.yml -o "$DOCKER_COMPOSE_FILE"; then
        echo "❌ Failed to download new docker-compose.yml"
        # Restore backup if it exists
        if [ -f "${DOCKER_COMPOSE_FILE}.backup" ]; then
            mv "${DOCKER_COMPOSE_FILE}.backup" "$DOCKER_COMPOSE_FILE"
        fi
        exit 1
    fi

    # Create new config files
    create_config_files

    cd "$GURUBASE_DIR"
    
    # Pull latest images and restart services
    if command -v docker compose &> /dev/null; then
        docker compose pull && docker compose up -d
    elif docker-compose version &> /dev/null; then
        docker-compose pull && docker-compose up -d
    else
        echo "❌ Neither docker-compose nor docker compose is available"
        exit 1
    fi
    
    # Remove backup if upgrade was successful
    [ -f "${DOCKER_COMPOSE_FILE}.backup" ] && rm "${DOCKER_COMPOSE_FILE}.backup"
    
    wait_for_services
    
    echo "✅ Gurubase has been upgraded to the latest version"
    echo "🌐 Open http://localhost:8029 in your browser to access the application."
    exit 0
}

# Update the argument handling section:
case "$1" in
    "rm")
        remove_gurubase
        ;;
    "upgrade")
        upgrade_gurubase
        ;;
    "")
        # Continue with installation
        ;;
    *)
        echo "❌ Unknown argument: $1"
        echo "Usage: $0 [rm|upgrade]"
        echo "  - No argument: Install Gurubase"
        echo "  - rm: Remove Gurubase containers and networks"
        echo "  - upgrade: Upgrade Gurubase to the latest version"
        exit 1
        ;;
esac

echo "⚡ Installing Gurubase Self Hosted..."

echo "🔍 Checking prerequisites..."

is_port_available() {
  local port="$1"

  if ! command -v lsof >/dev/null 2>&1; then
    echo "❌ lsof not found. Please install lsof and try again."
    exit 1
  fi

  if lsof -i :"$port" >/dev/null 2>&1; then
    echo "❌ Port $port is already in use. Free up the current port and try again."
    exit 1
  fi
}

check_milvus_health() {
    docker exec gurubase-milvus-standalone curl -sf http://localhost:9091/healthz > /dev/null 2>&1
    return $?
}

is_port_available 8028
is_port_available 8029

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker before running this script."
    exit 1
fi

# Check for either docker-compose or docker compose
if ! (command -v docker-compose &> /dev/null || docker compose version &> /dev/null); then
    echo "❌ Docker Compose is not installed. Please install Docker Compose before running this script."
    exit 1
fi

# Check if docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker before running this script."
    exit 1
fi

if [ ! -d "$GURUBASE_DIR" ]; then
    mkdir -p "$GURUBASE_DIR/milvus"
    mkdir -p "$GURUBASE_DIR/postgres"
    mkdir -p "$GURUBASE_DIR/backend_media"
    mkdir -p "$GURUBASE_DIR/redis"
    mkdir -p "$GURUBASE_DIR/reranker"
fi

echo "Environment variables location: $GURUBASE_DIR/.env"
echo ""

# Check if POSTGRES_PASSWORD already exists in .env
if ! grep -q "POSTGRES_PASSWORD=" "$GURUBASE_DIR/.env" 2>/dev/null; then
    POSTGRES_PASSWORD=$(openssl rand -base64 32)
    echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD" >> $GURUBASE_DIR/.env
fi

# Check if OPENAI_API_KEY exists and is not empty
if ! grep -q "^OPENAI_API_KEY=.\+" "$GURUBASE_DIR/.env" 2>/dev/null; then
    echo "ℹ️  OpenAI API Key Security Notice:"
    echo "   - Your API key will be stored locally in $GURUBASE_DIR/.env"
    echo "   - It never leaves your machine and is not shared with any external services"
    echo "   - This key is used for text generation (gpt-4o, gpt-4o-mini, etc.) and embeddings (text-embedding-3-small, etc.)"
    echo "   - You can get an API key from https://platform.openai.com/api-keys"
    echo ""
    read -p "Enter your OpenAI API key: " OPENAI_API_KEY
    echo "OPENAI_API_KEY=$OPENAI_API_KEY" >> $GURUBASE_DIR/.env
fi

echo ""
echo ""

# Check if FIRECRAWL_API_KEY exists and is not empty
if ! grep -q "^FIRECRAWL_API_KEY=.\+" "$GURUBASE_DIR/.env" 2>/dev/null; then
    echo "ℹ️  Firecrawl API Key Security Notice:"
    echo "   - Your API key will be stored locally in $GURUBASE_DIR/.env"
    echo "   - It never leaves your machine and is not shared with any external services"
    echo "   - This key is used for website scraping"
    echo "   - You can get an API key from https://www.firecrawl.dev/app/api-keys"
    echo ""
    read -p "Enter your Firecrawl API key: " FIRECRAWL_API_KEY
    echo "FIRECRAWL_API_KEY=$FIRECRAWL_API_KEY" >> $GURUBASE_DIR/.env
fi

# Create .env.frontend file
if [ ! -f "$GURUBASE_DIR/.env.frontend" ] || ! grep -q "^NEXT_PUBLIC_TELEMETRY_ENABLED=" "$GURUBASE_DIR/.env.frontend" 2>/dev/null; then
    echo "📝 Creating .env.frontend file..."
    echo "NEXT_PUBLIC_TELEMETRY_ENABLED=true" > "$GURUBASE_DIR/.env.frontend"
fi

export $(cat $GURUBASE_DIR/.env | xargs)

docker network inspect gurubase > /dev/null 2>&1 || docker network create gurubase

# Create configuration files before starting services
create_config_files

echo "🚀 Deploying Gurubase Self Hosted..."
# Start all services using docker compose
if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
    echo "📥 Downloading docker-compose.yml..."
    curl -sSL https://raw.githubusercontent.com/Gurubase/gurubase/refs/heads/selfhosted/docker-compose.yml -o "$DOCKER_COMPOSE_FILE"
fi

cd "$GURUBASE_DIR"
if command -v docker compose &> /dev/null; then
    docker compose up -d
elif docker-compose version &> /dev/null; then
    docker-compose up -d
else
    echo "❌ Neither docker-compose nor docker compose is available"
    exit 1
fi

wait_for_services
docker exec gurubase-milvus-standalone bash -c "curl -s -X PUT localhost:9091/log/level -d level=warn" > /dev/null 2>&1

show_installation_summary() {
    echo "
📝 Installation Summary
----------------------
🏠 Installation Directory: $GURUBASE_DIR
🔑 Environment File: $GURUBASE_DIR/.env

🌐 Web Interface: http://localhost:8029
📚 Documentation: https://github.com/Gurubase/gurubase
🆘 Support: https://github.com/Gurubase/gurubase/issues

Next Steps:
1. Open http://localhost:8029 in your browser
2. Follow the quick start guide: https://github.com/Gurubase/gurubase/blob/main/docs/quickstart.md
"
}

show_installation_summary

# Ask user before opening the web interface
read -p "Would you like to open Gurubase in your browser? [Y/n] " open_browser
open_browser=${open_browser:-Y}

if [[ $open_browser =~ ^[Yy]$ ]]; then
    if command -v xdg-open &> /dev/null && xdg-open http://localhost:8029 2>/dev/null; then
        :  # Command succeeded, do nothing
    elif command -v open &> /dev/null && open http://localhost:8029 2>/dev/null; then
        :  # Command succeeded, do nothing
    else
        echo "ℹ️  Could not automatically open browser. Please visit http://localhost:8029 manually."
    fi
fi
