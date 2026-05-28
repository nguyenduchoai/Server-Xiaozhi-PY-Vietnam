# Rollback Procedures - py-server-xiaozhi

This document provides step-by-step rollback procedures for different failure scenarios.

## Quick Rollback Commands

```bash
# Docker Compose - Rollback to previous version
docker-compose down
docker-compose pull
docker-compose up -d

# Docker - Rollback single container
docker-compose down backend
docker-compose pull backend
docker-compose up -d backend

# Kubernetes - Rollback deployment
kubectl rollout undo deployment/xiaozhi-backend -n xiaozhi
kubectl rollout status deployment/xiaozhi-backend -n xiaozhi

# Rollback to specific revision
kubectl rollout undo deployment/xiaozhi-backend --to-revision=2 -n xiaozhi
```

## Scenario 1: Database Connection Pool Exhaustion

**Symptoms:**
- "Connection timeout" errors in logs
- High database connection wait times
- Application unresponsive

**Immediate Actions:**
1. Scale down backend instances:
```bash
kubectl scale deployment xiaozhi-backend --replicas=1 -n xiaozhi
```
2. Verify connection recovery:
```bash
kubectl exec -it xiaozhi-backend-xxx -- python -c "
from app.core.db.database import async_engine
print(f'Pool: size={async_engine.pool.size()}, overflow={async_engine.pool.overflow()}')
"
```

**Rollback Configuration (database.py):**
```bash
# Edit the database.py and restore previous pool settings
# Previous: pool_size=3, max_overflow=5
# Current (optimized): pool_size=10, max_overflow=20

# If issue persists, reduce to intermediate values
pool_size=6
max_overflow=10
```

**Verification:**
```bash
# Check Prometheus metrics for recovery
curl -s http://localhost:9090/api/v1/query?query=db_pool_size{state="overflow"} | jq
```

---

## Scenario 2: Memory Leak in WebSocket Handler

**Symptoms:**
- Memory usage continuously increasing
- OOM (Out of Memory) kills
- ASR audio buffer warnings in logs

**Immediate Actions:**
1. Identify affected pods:
```bash
kubectl top pods -n xiaozhi --sort-by=memory
```

2. Force restart affected pods:
```bash
kubectl rollout restart deployment/xiaozhi-backend -n xiaozhi
```

3. Monitor memory after restart:
```bash
watch -n 5 'kubectl top pods -n xiaozhi -l app=xiaozhi-backend'
```

**Verify Fix is Working:**
```bash
# Check for buffer overflow warnings
kubectl logs -f deployment/xiaozhi-backend -n xiaozhi | grep "ASR audio buffer overflow"
```

**If fix doesn't work, rollback connection.py changes:**
```bash
# The bounded buffer was added in _bound_asr_audio()
# To rollback, simply not call _bound_asr_audio() in reset_vad_states()

# In connection.py, modify reset_vad_states():
def reset_vad_states(self, _preserve_manual: Optional[bool] = None):
    self.client_audio_buffer = bytearray()
    self.client_have_voice = False
    self.client_voice_stop = False
    # REMOVE: self._bound_asr_audio()  # Comment out or remove
    self.logger.bind(tag=TAG).debug("VAD states reset.")
```

---

## Scenario 3: Cache-Related Issues

**Symptoms:**
- Stale data being served
- Cache connection errors
- High cache miss rate

**Immediate Actions:**

1. Clear all caches:
```bash
# Python - Clear via Redis CLI
redis-cli -a $REDIS_PASSWORD FLUSHDB

# Or from within the app
kubectl exec -it xiaozhi-backend-xxx -- python -c "
from app.core.utils.cache import client
import asyncio
async def clear():
    await client.flushdb()
asyncio.run(clear())
"
```

2. Disable caching temporarily:
```python
# In subscription.py and providers.py, comment out cache logic
# This forces fresh data from database

# For example in list_subscription_plans():
# OLD (with caching):
# cached_data = await cache_manager.get(cache_key)
# if cached_data:
#     return [SubscriptionPlanPublic(**p) for p in cached_data]

# NEW (bypass cache):
# Always fetch from database
```

3. Restart to rebuild cache:
```bash
kubectl rollout restart deployment/xiaozhi-backend -n xiaozhi
```

**Verification:**
```bash
# Monitor cache hit ratio
curl -s http://localhost:9090/api/v1/query?query=cache_hit_ratio | jq

# Expected: hit_ratio > 0.5 after warm-up
```

---

## Scenario 4: High API Response Times

**Symptoms:**
- P95 response time > 500ms
- Timeout errors on client side
- Service level objective (SLO) violations

**Immediate Actions:**

1. Check for cache-related issues (Scenario 3)

2. Check database pool status:
```bash
kubectl exec -it xiaozhi-backend-xxx -- python -c "
from app.core.db.database import async_engine
print(f'Pool status: size={async_engine.pool.size()}, overflow={async_engine.pool.overflow()}')
print(f'Checked out: {async_engine.pool.checkedout()}')
"
```

3. If pool is exhausted, temporarily increase:
```python
# In database.py
pool_size=15  # Increased from 10
max_overflow=30  # Increased from 20
```

4. Scale up instances:
```bash
kubectl scale deployment xiaozhi-backend --replicas=5 -n xiaozhi
```

**Long-term Fix:**
- Review N+1 queries
- Add database indexes
- Implement request coalescing

---

## Scenario 5: N+1 Query Problem Resurfacing

**Symptoms:**
- High database query rate
- Slow user quota checks
- Database CPU > 80%

**Immediate Actions:**

1. Check quota service logs:
```bash
kubectl logs -f deployment/xiaozhi-backend -n xiaozhi | grep "quota"
```

2. Verify batch query is working:
```bash
# Enable SQL logging temporarily
kubectl exec -it xiaozhi-backend-xxx -- python -c "
from app.core.db.database import async_engine
async_engine.echo = True  # Enable SQL logging
"
```

3. If N+1 is back, restore batch query:
```python
# In quota_service.py, ensure get_all_counts() is used
# NOT individual count methods

# CORRECT (batch):
async def get_user_quotas(user_id: str) -> UserQuotas:
    counts = await self.get_all_counts(user_id)  # Single query
    ...

# WRONG (N+1):
async def get_user_quotas(user_id: str) -> UserQuotas:
    agents = await self.count_agents(user_id)  # Query 1
    devices = await self.count_devices(user_id)  # Query 2
    mcps = await self.count_mcps(user_id)  # Query 3
    ...
```

---

## Scenario 6: Prometheus/Grafana Issues

**Symptoms:**
- Metrics not being collected
- Dashboard panels empty
- Alerts not firing

**Immediate Actions:**

1. Check Prometheus status:
```bash
kubectl exec -it xiaozhi-prometheus-xxx -- promtool check config
```

2. Check target status:
```bash
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets'
```

3. Restart Prometheus:
```bash
kubectl rollout restart statefulset xiaozhi-prometheus -n xiaozhi
```

4. Recreate Grafana datasource:
```bash
# Via Grafana UI: Configuration > Data Sources > Add > Prometheus
# URL: http://xiaozhi-prometheus:9090
```

**Rebuild Dashboard:**
```bash
# Import from backup
kubectl create configmap xiaozhi-grafana-import --from-file=dashboard.json=/path/to/backup/dashboard.json

# Or via curl
curl -X POST -H "Content-Type: application/json" \
  -d @monitoring/grafana/dashboard.json \
  http://admin:admin@localhost:3000/api/dashboards/db
```

---

## Rollback Decision Matrix

| Scenario | Severity | Immediate Action | Rollback Time |
|----------|----------|-------------------|---------------|
| DB Pool | Critical | Scale down | 5 min |
| Memory Leak | Critical | Restart pods | 2 min |
| Cache Issue | High | Flush cache | 3 min |
| High Latency | High | Scale up | 5 min |
| N+1 Query | Medium | Fix queries | 10 min |
| Monitoring | Low | Restart services | 5 min |

---

## Pre-Deployment Checklist

Before deploying changes, always:

1. **Create backup of current state:**
```bash
kubectl get deployment xiaozhi-backend -n xiaozhi -o yaml > backup-deployment.yaml
kubectl get configmap xiaozhi-config -n xiaozhi -o yaml > backup-configmap.yaml
```

2. **Tag current image:**
```bash
docker tag ghcr.io/xiaozhi-ai/py-server-xiaozhi:latest \
  ghcr.io/xiaozhi-ai/py-server-xiaozhi:rollback-$(date +%Y%m%d-%H%M%S)
```

3. **Document current metrics:**
```bash
curl -s http://localhost:9090/api/v1/query?query=up > metrics-before.json
```

4. **Prepare rollback commands:**
```bash
# Store these in a rollback script
#!/bin/bash
kubectl rollout undo deployment/xiaozhi-backend -n xiaozhi
sleep 30
kubectl rollout status deployment/xiaozhi-backend -n xiaozhi
```

---

## Emergency Contacts

If issues persist after rollback:

1. **Database Team:** Escalate for pool tuning
2. **SRE Team:** Engage for infrastructure support
3. **Development Team:** Create bug ticket with logs

---

## Post-Incident Review

After resolving any issue:

1. Document what happened
2. Update this runbook if procedures changed
3. Add monitoring for early detection
4. Schedule post-mortem if severity was Critical