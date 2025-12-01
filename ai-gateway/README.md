# AI Gateway for Home Assistant

Natural language interface for Home Assistant using local Ollama LLMs. Translates human-friendly commands into Home Assistant service calls without requiring cloud services.

## Features

- **Local LLM Processing**: Uses Ollama running on your hardware (Raspberry Pi 5 compatible)
- **Bilingual Support**: Accepts commands in both English and Polish
- **Deterministic JSON Planning**: Reliable, structured output for automation
- **Home Assistant Integration**: Direct REST API integration
- **Docker Compose Deployment**: Everything runs in containers
- **Type-Safe**: Full Python type hints with MyPy strict mode
- **Production-Ready**: Structured logging, health checks, error handling
- **Well-Tested**: 30%+ test coverage with pytest

## Architecture

```
User → AI Gateway → Ollama (LLM) → JSON Plan → Home Assistant → Action
```

### Flow Example

1. **Input**: "Turn on living room lights"
2. **Ollama Translation**:
   ```json
   {
     "action": "call_service",
     "service": "light.turn_on",
     "entity_id": "light.living_room_main",
     "data": {}
   }
   ```
3. **Home Assistant Execution**: `POST /api/services/light/turn_on`
4. **Response**: Success/error with HA state

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Ollama installed and running on host: `http://localhost:11434`
- Home Assistant instance with API access
- Home Assistant long-lived access token

### 1. Install Ollama and Pull Model

```bash
# Install Ollama (see https://ollama.ai)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull recommended model for Raspberry Pi 5
ollama pull llama3.2:3b

# For more powerful systems, consider:
# ollama pull llama3.1:8b
# ollama pull mistral:7b
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

Required settings in `.env`:
```bash
# Get from HA: Profile → Long-lived access tokens
HA_TOKEN=your_home_assistant_token_here

# Your HA URL (use http://homeassistant:8123 in Docker)
HA_BASE_URL=http://homeassistant:8123

# Ollama URL (use host.docker.internal in Docker)
OLLAMA_BASE_URL=http://host.docker.internal:11434

# Model name
OLLAMA_MODEL=llama3.2:3b
```

### 3. Start Services

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f ai-gateway

# Check health
curl http://localhost:8080/health
```

### 4. Test the Gateway

```bash
# Turn on living room lights
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"text": "Turn on living room lights"}'

# Turn off kitchen lights (Polish)
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"text": "Wyłącz światło w kuchni"}'

# Set bedroom brightness
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"text": "Set bedroom to 50% brightness"}'
```

## API Documentation

Once running, interactive API docs available at:
- **Swagger UI**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

### Endpoints

#### `POST /ask`

Process natural language command.

**Request:**
```json
{
  "text": "Turn on the lights"
}
```

**Response (Success):**
```json
{
  "status": "success",
  "plan": {
    "action": "call_service",
    "service": "light.turn_on",
    "entity_id": "light.living_room_main",
    "data": {}
  },
  "message": "Action executed successfully",
  "ha_response": [
    {
      "entity_id": "light.living_room_main",
      "state": "on"
    }
  ]
}
```

**Response (Unsupported Command):**
```json
{
  "status": "success",
  "plan": {
    "action": "none"
  },
  "message": "Command understood but no action available"
}
```

**Response (Error):**
```json
{
  "status": "error",
  "message": "Failed to translate command to action plan"
}
```

#### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "home_assistant": "connected"
}
```

## Supported Commands

### English Commands

- "Turn on living room lights"
- "Turn off kitchen lights"
- "Turn on bedroom"
- "Set bedroom to 50% brightness"
- "Turn off all lights" (if entity exists)

### Polish Commands

- "Włącz światło w salonie"
- "Wyłącz światło w kuchni"
- "Zapal światło w sypialni"
- "Ustaw jasność sypialni na 50%"

### Entity Mapping

The gateway maps friendly names to Home Assistant entity IDs:

| Friendly Name | Entity ID |
|---------------|-----------|
| living room / salon | light.living_room_main |
| kitchen / kuchnia | light.kitchen |
| bedroom / sypialnia | light.bedroom |

**To add more entities**: Edit `ENTITY_MAPPING` in `app/services/ollama_client.py`

## Development

### Setup Development Environment

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dev dependencies
pip install -e .[dev,test]

# Install pre-commit hooks
pre-commit install
```

### Run Tests

```bash
# Run all tests with coverage
pytest --cov=app --cov-report=term --cov-report=html

# Run specific test file
pytest tests/test_json_validator.py -v

# Run with debug output
pytest -vv --log-cli-level=DEBUG
```

### Code Quality

```bash
# Lint code
ruff check .

# Format code
ruff format .

# Type checking
mypy app/

# Run all pre-commit hooks
pre-commit run --all-files
```

### Run Locally (Without Docker)

```bash
# Set environment variables
export HA_TOKEN=your_token
export HA_BASE_URL=http://localhost:8123
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=llama3.2:3b
export LOG_LEVEL=DEBUG

# Run application
uvicorn app.main:app --reload --port 8080
```

## Deployment

### Docker Compose (Recommended)

```bash
# Production deployment
docker-compose up -d

# View logs
docker-compose logs -f

# Restart service
docker-compose restart ai-gateway

# Stop all services
docker-compose down
```

### Systemd Service (Alternative)

Create `/etc/systemd/system/ai-gateway.service`:

```ini
[Unit]
Description=AI Gateway for Home Assistant
After=network.target

[Service]
Type=simple
User=gateway
WorkingDirectory=/opt/ai-gateway
EnvironmentFile=/opt/ai-gateway/.env
ExecStart=/opt/ai-gateway/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-gateway
sudo systemctl start ai-gateway
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HA_TOKEN` | *required* | Home Assistant long-lived access token |
| `HA_BASE_URL` | http://homeassistant:8123 | Home Assistant API URL |
| `OLLAMA_BASE_URL` | http://host.docker.internal:11434 | Ollama API URL |
| `OLLAMA_MODEL` | llama3.2:3b | Ollama model name |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Recommended Models

#### Raspberry Pi 5 (4-8GB RAM)
- `llama3.2:3b` - Best balance of performance/accuracy
- `phi3:mini` - Faster, less accurate
- `qwen2.5:3b` - Good multilingual support

#### Desktop/Server
- `llama3.1:8b` - High accuracy
- `mistral:7b` - Fast and capable
- `gemma2:9b` - Google's latest

### System Prompt Customization

The system prompt in `app/services/ollama_client.py` can be customized to:
- Add new entity mappings
- Support additional languages
- Add new service types (climate, covers, switches)
- Adjust tone and behavior

## Monitoring

### Logs

Structured JSON logs with correlation IDs:

```json
{
  "timestamp": "2024-11-19T10:30:45.123Z",
  "level": "INFO",
  "logger": "app.routers.gateway",
  "message": "[abc-123] Processing request: Turn on living room lights"
}
```

### Health Checks

```bash
# Check gateway health
curl http://localhost:8080/health

# Check Docker container health
docker ps
# Look for "healthy" status
```

### Metrics (Optional)

To add Prometheus metrics, install:
```bash
pip install prometheus-fastapi-instrumentator
```

## Troubleshooting

### Gateway Can't Reach Ollama

**Symptom**: "HTTP error calling Ollama" in logs

**Solutions**:
- Verify Ollama is running: `curl http://localhost:11434/api/tags`
- Check Docker networking: `extra_hosts` in docker-compose.yml
- Try `OLLAMA_BASE_URL=http://host.docker.internal:11434`

### Gateway Can't Reach Home Assistant

**Symptom**: "Home Assistant health check failed"

**Solutions**:
- Verify HA is accessible: `curl http://your-ha:8123/api/`
- Check `HA_TOKEN` is valid (not expired)
- Verify `HA_BASE_URL` is correct for container networking

### Ollama Returns Invalid JSON

**Symptom**: "No JSON found in response" warnings

**Solutions**:
- Ensure using `format: "json"` in Ollama request
- Try a different model (some are better at structured output)
- Check system prompt is not being overridden

### Entity Not Found

**Symptom**: HA returns 404 or "entity not found"

**Solutions**:
- Verify entity ID exists in HA: Settings → Devices & Services
- Check entity mapping in `ollama_client.py`
- Ensure entity is not disabled in HA

## Security Considerations

- **Secrets**: Never commit `.env` file (use `.env.example` as template)
- **API Token**: Use Home Assistant long-lived tokens (not admin passwords)
- **Network**: Run on trusted network or behind reverse proxy with auth
- **Input Validation**: All Ollama output is validated before HA execution
- **Rate Limiting**: Consider adding rate limiting for production use

## Performance

### Benchmarks (Raspberry Pi 5, 8GB, llama3.2:3b)

- **First Request**: ~2-3s (model load time)
- **Subsequent Requests**: ~500ms-1s
- **Memory Usage**: ~2-3GB (Ollama model)
- **CPU Usage**: 50-80% during inference

### Optimization Tips

- Use smaller models for faster response (phi3:mini)
- Keep Ollama running to avoid cold starts
- Enable Ollama GPU acceleration if available
- Cache common requests in application layer

## License

This project is part of the ha-enterprise-starter repository.

## Contributing

This is a subproject within the main Home Assistant repository. For development workflow:

1. Follow coding standards in `/CLAUDE.md`
2. Maintain 30% minimum test coverage
3. Run pre-commit hooks before committing
4. Test with actual Ollama and HA instances

## Support

For issues and questions:
- Check troubleshooting section above
- Review logs with `LOG_LEVEL=DEBUG`
- Verify Ollama and HA connectivity independently
- Check FastAPI docs at `/docs` for API details
