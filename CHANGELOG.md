# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2025-01-22

### Added
- Fix Binge graph. In some cases, the nodes are not visible.

## [0.1.0] - 2025-01-21

### Added
- Modern Next.js 14 frontend with TailwindCSS
- Django REST framework backend
- RAG system with advanced LLM techniques
- Multiple data source support:
  - Website scraping with Firecrawl
  - YouTube video transcription
  - PDF document processing
  - GitHub codebase indexing
- Vector similarity search with Milvus
- Message queue system with RabbitMQ for Celery
- Caching layer with Redis
- PostgreSQL database for data persistence
- Docker Compose based deployment
- Self-hosted installation script
- Binge feature for personalized learning paths
- Context evaluation system to minimize hallucination
- Comprehensive documentation:
  - Installation guide
  - Architecture documentation
  - Development guidelines
- Website widget for embedding Q&A functionality
- Telemetry system with opt-out option

### Infrastructure
- Microservices architecture with Docker Compose
- Nginx for static file serving and reverse proxy
- Celery for asynchronous task processing
- Milvus for vector similarity search
- PostgreSQL for primary data storage
- Redis for caching and rate limiting
- RabbitMQ for message queue

[0.1.0]: https://github.com/Gurubase/gurubase/releases/tag/0.1.0 
[0.1.1]: https://github.com/Gurubase/gurubase/releases/tag/0.1.1 
