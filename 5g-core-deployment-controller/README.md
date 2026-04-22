# 5G Core Deployment Controller

## How to Run the Project

### From the Project Root (Recommended)

```bash
cd 5g-core-deployment-controller
python -m 5g_core_deployment_controller.main
```

**Or alternatively:**

```bash
python src/5g_core_deployment_controller/main.py
```

### ⚠️ DO NOT do this:

```bash
cd src/5g_core_deployment_controller
python main.py  # ❌ This will error: "ImportError: attempted relative import with no known parent package"
```

### Why This Matters

The `main.py` file contains relative imports like `from .routers.core import ...`. These only work when Python recognizes the code as part of a **package**. Running the file directly from its folder causes Python to treat it as a standalone module, not as part of a package.

### Development Mode Installation (Optional)

To install the package in your virtual environment:

```bash
cd 5g-core-deployment-controller
pip install -e .
```

This will allow you to run the project from any directory.

## Environment Variables

You can configure the controller behavior using environment variables:

- `COMPOSE_FILE`: Path to the docker-compose file (default: `data/compose.yaml`)
- `ENV_FILE`: Path to the .env file (default: `data/.env`)
- `API_PORT`: API port (default: `8000`)
- `LOG_LEVEL`: Logging level: DEBUG, INFO, WARNING, ERROR (default: `INFO`)
- `MONGO_HOST`: MongoDB host (default: `mongo`)
- `MONGO_PORT`: MongoDB port (default: `27017`)
- `MONGO_USER`: MongoDB user
- `MONGO_PASSWORD`: MongoDB password
- `MONGO_DB`: MongoDB database (default: `open5gs`)
