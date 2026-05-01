# Risk System Deployment Guide

## Quick Start

### 1. Start the Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Start the Frontend
```bash
cd frontend
npm install
npm run dev
```

### 3. Access the Application
- Frontend: http://localhost:5173
- API: http://localhost:8000/api/v1
- Risk Dashboard: http://localhost:5173/risk

---

## Environment Configuration

### Backend (.env)
```bash
# Trading Mode
TRADING_MODE=paper          # "paper" for simulation, "live" for real
LIVE_TRADING_ENABLED=false  # Must be true for live mode

# Risk Settings
RISK_STORAGE_PATH=./data/risk_history.db  # SQLite database path

# Live Mode Safeguards (only needed for live trading)
LIVE_GUARD_SECRET=your-secret-key
LIVE_GUARD_MAX_SKEW_SECONDS=300
LIVE_MAX_MARKET_DATA_AGE_SECONDS=180
LIVE_CIRCUIT_BREAKER_RISK_THRESHOLD=0.75
LIVE_CIRCUIT_BREAKER_VOLATILITY_PCT=0.08

# x402 Payments (optional)
X402_ENABLED=false
```

### Frontend (.env)
```bash
VITE_API_BASE=/api/v1
```

---

## Deployment Profiles

### Development (Paper Trading)
```bash
TRADING_MODE=paper
LIVE_TRADING_ENABLED=false
```
- Uses mock market data
- No live safeguards required
- Safe for testing

### Production (Live Trading)
```bash
TRADING_MODE=live
LIVE_TRADING_ENABLED=true
LIVE_GUARD_SECRET=<secure-random-key>
```
- Requires real market data from CoinGecko
- Enforces signed request headers
- Circuit breakers active
- Fail-closed on data errors

---

## Safety Checklist

### Before Going Live

- [ ] **Environment Variables**
  - `TRADING_MODE=live`
  - `LIVE_TRADING_ENABLED=true`
  - `LIVE_GUARD_SECRET` is set to a secure random value
  
- [ ] **Market Data**
  - CoinGecko API is accessible
  - Market data freshness validation enabled
  
- [ ] **Risk Storage**
  - `data/risk_history.db` directory exists
  - SQLite database is writable
  
- [ ] **Monitoring**
  - Risk alerting logs are visible
  - Historical metrics are being recorded

### Security Recommendations

1. **Never commit secrets** to version control
2. **Use HTTPS** in production
3. **Rate limit** API endpoints (add nginx rate limiting)
4. **Monitor logs** for CRITICAL risk alerts
5. **Backup** SQLite database regularly

---

## Docker Deployment

### docker-compose.yml
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - TRADING_MODE=paper
      - LIVE_TRADING_ENABLED=false
    volumes:
      - ./data:/app/data  # Persist risk history

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    environment:
      - VITE_API_BASE=/api/v1
    depends_on:
      - backend

  gateway:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./gateway/nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - backend
      - frontend
```

### Start Stack
```bash
docker-compose up -d
```

---

## API Health Checks

### Check Risk Storage
```bash
curl http://localhost:8000/api/v1/trading/risk/metrics
```

### Test Risk Assessment
```bash
curl -X POST http://localhost:8000/api/v1/trading/risk/assess \
  -H "Content-Type: application/json" \
  -d '{"price": 3200, "volume_24h": 5000000000}'
```

### Verify Frontend
```bash
curl http://localhost:3000/risk
```

---

## Monitoring

### Key Log Patterns
```
# Normal trade
INFO: Pre-execution risk assessment: score=25.50, level=low

# High risk (position reduced)
WARNING: HIGH RISK: Position reduced to 75% (score=62.00)

# Critical risk (blocked)
WARNING: CRITICAL RISK BLOCKED: score=85.00, token=ETH/USDT

# Alert patterns
WARNING: RISK ALERT [CRITICAL] CRITICAL risk score detected: 85.3
WARNING: RISK ALERT [WARNING] Consistently high risk: 72.5 avg over 10 trades
```

### Metrics to Track
- Average risk score over time
- Percentage of CRITICAL blocks
- Position multiplier average
- Win rate by risk level

---

## Database Management

### SQLite Location
```
data/risk_history.db
```

### Backup
```bash
cp data/risk_history.db data/risk_history_$(date +%Y%m%d).db
```

### Clear History (Testing)
```bash
rm data/risk_history.db
# Will be recreated on next trade
```

---

## Troubleshooting

### Issue: "Risk assessment error"
- Check market data is available
- Verify CoinGecko API is accessible (live mode)
- Check logs for specific error

### Issue: "CRITICAL RISK BLOCKED"
- This is expected behavior for high risk
- Check `risk_metadata.recommendations` for reasons
- Review market conditions before retrying

### Issue: Risk Dashboard shows no data
- Ensure SQLite database exists
- Check `data/risk_history.db` is writable
- Verify `/trading/risk/metrics` endpoint returns data

### Issue: Frontend not connecting to backend
- Check `VITE_API_BASE` environment variable
- Verify backend is running on correct port
- Check CORS configuration in backend

---

## Performance Notes

- Risk assessment is synchronous and fast (<10ms)
- SQLite handles 100K+ records efficiently
- Frontend caches metrics for 30 days
- Consider PostgreSQL for production scale

---

## Support

For issues or questions:
1. Check logs in backend console
2. Review `risk_metadata` in API responses
3. See `RISK_REFERENCE.md` for quick reference