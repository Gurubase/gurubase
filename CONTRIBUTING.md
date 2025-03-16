# Contributing to Gurubase

We love your input! We want to make contributing to Gurubase as easy and transparent as possible, whether it's:

- Adding a new feature
- Submitting a fix
- Reporting a bug
- Discussing the current state of the code
- Proposing new features

## Development Setup

We use VSCode devcontainers for development. This ensures a consistent development environment for all contributors.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) `27.3.x` or later.
- [Docker Compose](https://docs.docker.com/compose/install/) (`docker compose` or `docker-compose`) `2.30.x` or later.
- VSCode with the Remote - Containers extension installed.
- Port `8018` and `8019` should be available on your machine.

### Fork and clone the repository

1. Fork the repository by clicking the "Fork" button at the top right of the [Gurubase repository page](https://github.com/Gurubase/gurubase)
2. Clone your forked repository to your local machine:

```bash
git clone https://github.com/YOUR-USERNAME/gurubase.git
```

3. Add the original repository as an upstream remote:

```bash
cd gurubase
git remote add upstream https://github.com/Gurubase/gurubase.git
```

### Start the development environment

The `.dev` folder contains a docker compose file named `selfhosted-dev-docker-compose.yml` for a development environment. This will start the necessary containers for frontend and backend development. These services are:

- Milvus
- RabbitMQ
- PostgreSQL
- Redis
- Nginx

To start the development environment, run the following command in the root of the repository:

```bash
docker compose -f .dev/selfhosted-dev-docker-compose.yml up -d
```

After that, you need to start the backend and frontend services. Frontend code is located in `src/gurubase-frontend` and backend code is located in `src/gurubase-backend`. Open these directories in different VSCode windows.

Open the frontend code in a separate VSCode window:
```bash
cd src/gurubase-frontend
code .
```

Open the backend code in a separate VSCode window:
```bash
cd src/gurubase-backend
code .
```

### Frontend (Next.js)
After you have opened the frontend (src/gurubase-frontend) in a separate VSCode window, follow these steps:

1. Open the devcontainer by pressing `F1` or `Ctrl+Shift+P` and selecting `Remote-Containers: Reopen in Container`
2. Select `Gurubase Selfhosted Dev Container` from the list
3. Wait for the container to start and the project to open in it
4. In the terminal, run `yarn dev-selfhosted`

### Backend (Django)
After you have opened the backend (src/gurubase-backend) in a separate VSCode window, follow these steps:

1. Open the devcontainer by pressing `F1` or `Ctrl+Shift+P` and selecting `Remote-Containers: Reopen in Container`
2. Select `Gurubase Selfhosted Dev Container` from the list
3. Wait for the container to start and the project to open in it
4. If this is the first time you run the backend, you need to run the following command **once** to fill the database with initial data and other initializations. You don't need to run this command again.

    ```bash
    cd backend && ./manage.py migrate && python scripts/1_generate_users.py && python scripts/3_update_site.py && python scripts/5_fill_llm_prices.py && python scripts/4_create_milvus_collections.py && python manage.py collectstatic --noinput --verbosity 0
    ```

5. Run the following command to start the backend server:
    ```bash
    cd backend
    bash migrate_runserver.sh
    ```

6. You also need to start the celery beat and worker in separate terminals:

    - Open a new terminal and run the following command to start the celery beat:
        ```bash
        bash start_scripts/start_celery_beat.sh
        ```

    - Open another terminal and run the following command to start the celery worker:
        ```bash
        bash start_scripts/start_celery_worker.sh
        ```

7. At the end, there will be 3 terminals running. One for the backend, one for the celery beat and one for the celery worker.

8. If you work on the Gurubase Discord bot, you need to start its backend separately. Otherwise, you can ignore this step.

    ```bash
    bash start_scripts/start_discord_listener.sh
    ```

> Note, to be able to use the debuggers,
>    1. Press `F1` or `Ctrl+Shift+P`
>
>    2. Select "Python: Select Interpreter"
>
>    3. Select "Enter interpreter path..."
>
>    4. Type `/workspace/.venv/bin/python` and enter
>
>    5. From Visual Studio Code or Cursor, you can visit the "Run and Debug" section and use it.

### Result

- You should be able to access Gurubase UI at `http://localhost:8019`. 
- You should be able to access Django Admin Panel at `http://localhost:8018/admin`. 
    - The default credentials are:
        - Username: `root@gurubase.io`
        - Password: `ChangeMe`

### Details

- `selfhosted-dev-docker-compose.yml` file creates a Docker network `selfhosted-dev-gurubase` and all the services communicate over this network.
- Nginx is used for serving the frontend, backend and media files.
- Milvus is used for vector search.
- PostgreSQL is used for storing the relational and structured data.
- Redis is used for caching/distributed locking/rate limiting and similar purposes.
- RabbitMQ is used as a broker for Celery.


### Troubleshooting 

- If you face any issues about the development environment, please open an issue on [GitHub Issues](https://github.com/Gurubase/gurubase/issues), or contact us on [Discord](https://discord.gg/9CMRSQPqx6).


## How to Contribute

We would like to discuss the task before you start working on it. You can select one of the open issues or create a new one and discuss it with the team. Once you have the task assigned, you can start working on it. We also use GitHub Projects to manage tasks. You can find the board [here](https://github.com/orgs/Gurubase/projects/1).

### Pull Request Process

- Create a new branch for your changes from `develop` branch
- Branch name should be in the following format: 
    - `feat/your-feature-name` for new features
    - `fix/your-fix-name` for bug fixes
    - `chore/your-chore-name` for chores
    - `refactor/your-refactor-name` for refactoring
    - `task/your-task-name` for tasks that are not fits to any of the above
- Commit messages should be in the following format:
    - Use the present tense ("Add feature" not "Added feature")
    - Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
    - Limit the first line to 72 characters or less
    - Reference issues and pull requests liberally after the first line
- Push your changes to your branch and create a pull request from your branch to `develop` branch
- Once the pull request is approved, it will be merged to `develop` branch


## License

By contributing, you agree that your contributions will be licensed under its Apache License 2.0. 