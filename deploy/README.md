# Deploy — Oracle Cloud (free tier) + Vercel

End state:
```
  Browser  →  https://gas.yourdomain    →  Vercel (Next.js frontend)
                                              │ (fetch)
                                              ▼
                       https://api.yourdomain  →  Oracle VM (Caddy → FastAPI)
                                                              │
                                                              ▼
                                                       /data volume (DuckDB + parquet + raw)
```

Time: ~30 min if you have a domain pointing at the VM. ~15 min if you use a free DuckDNS subdomain.

---

## 1. Provision the Oracle VM (one-time)

1. In Oracle Cloud Console → **Compute → Instances → Create Instance**.
2. Image: **Canonical Ubuntu 24.04**.
3. Shape: **VM.Standard.A1.Flex** (Ampere ARM, the "Always Free" one). Take **2 OCPU + 12 GB RAM**. You can scale up to 4/24 if you have headroom.
4. Networking: keep the default VCN; **make sure "Assign a public IPv4 address" is checked**.
5. SSH keys: upload your public key.
6. Create. Note the **Public IPv4** address.

**Open ports 80 and 443 in the VCN** (this is the part most people miss):
- VCN → Security Lists → Default Security List → Add **Ingress Rule**:
  - Source 0.0.0.0/0 · Protocol TCP · Destination port range `80`
  - Source 0.0.0.0/0 · Protocol TCP · Destination port range `443`

## 2. Point a domain at the VM

Cheapest free path — **DuckDNS**:
1. Sign in at https://www.duckdns.org with GitHub.
2. Create a subdomain e.g. `gas-mike`. Set the IP to your Oracle public IP. You'll get `gas-mike.duckdns.org` → done.

If you have a real domain (Cloudflare Registrar, $13/yr for `.energy`):
- Add an A record `api.yourdomain` → Oracle public IP. TTL 300.

## 3. SSH in and run bootstrap

```bash
ssh ubuntu@<oracle-public-ip>

# Quick test of inbound network — should show "1" if 80 opens correctly later
sudo ss -tlnp | head

# Pull the bootstrap script (works because the repo is public — if it's still
# private and your push isn't done yet, scp the file over instead)
curl -fsSL https://raw.githubusercontent.com/mikeLackovcan/gas-analytics/main/deploy/bootstrap_oracle.sh -o bootstrap.sh
sudo DOMAIN=gas-mike.duckdns.org bash bootstrap.sh
```

The script will stop and ask you to create `backend/.env`. Do this once:

```bash
sudo nano /opt/gas-analytics/backend/.env
# paste the same .env you have locally:
# AGSI_API_KEY=...
# ALSI_API_KEY=...
# ENTSOE_API_TOKEN=...
# CORS_ORIGINS=https://your-vercel-app.vercel.app
```

Then re-run:
```bash
sudo DOMAIN=gas-mike.duckdns.org bash bootstrap.sh
```

## 4. Verify

```bash
curl https://gas-mike.duckdns.org/healthz
# -> {"ok":true}

# Browse:
# https://gas-mike.duckdns.org/docs      ← FastAPI Swagger
# https://gas-mike.duckdns.org/api/storage/country?days=1
```

Caddy auto-issues a Let's Encrypt cert on first request to your domain.

## 5. Backfill data on the VM

The scheduler will start ingesting tomorrow on schedule, but for an immediate trader-useful dataset, run the 2y backfill once:

```bash
cd /opt/gas-analytics
docker compose -f docker-compose.prod.yml exec backend python -m app.ingest.agsi --from 2024-06-01 --to "$(date -I -d 'yesterday')"
docker compose -f docker-compose.prod.yml exec backend python -m app.ingest.entsog --from 2024-06-01 --to "$(date -I -d 'yesterday')" --chunk 30
docker compose -f docker-compose.prod.yml exec backend python -m app.ingest.hdd --from 2024-06-01 --to "$(date -I -d 'yesterday')"
docker compose -f docker-compose.prod.yml exec backend python -m app.ingest.demand_nowcast --from 2024-06-01 --to "$(date -I -d 'yesterday')"
docker compose -f docker-compose.prod.yml exec backend python -m app.forecast.ldz --train-years 2
```

## 6. Deploy the frontend to Vercel

1. https://vercel.com/new → Import the GitHub repo.
2. Set **Root Directory** = `frontend`.
3. Set env var: `NEXT_PUBLIC_API_BASE=https://gas-mike.duckdns.org`
4. Deploy. You get `https://gas-analytics-<hash>.vercel.app`.
5. Add that Vercel URL to your `backend/.env` CORS_ORIGINS and restart:
   ```bash
   cd /opt/gas-analytics
   sudo docker compose -f docker-compose.prod.yml restart backend
   ```

## 7. Operational

Logs:
```bash
cd /opt/gas-analytics
sudo docker compose -f docker-compose.prod.yml logs -f --tail 200
```

Update after a git push:
```bash
cd /opt/gas-analytics
sudo git pull
sudo docker compose -f docker-compose.prod.yml up -d --build
```

Backup DuckDB nightly (optional):
```bash
sudo crontab -e
# add:
# 0 3 * * * docker run --rm -v gas-analytics_gas-data:/d -v /opt/backups:/b alpine sh -c 'cp /d/gas.duckdb /b/gas-$(date +\%F).duckdb'
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `curl: connection refused on 80/443` | VCN security list didn't open the ports — see step 1. |
| `cannot allocate memory` during pip install pyarrow | Bump Oracle shape to 12 GB RAM (still free). |
| Caddy can't get cert | Domain isn't pointing at the VM yet, or ports 80/443 aren't open externally. |
| `Permission denied (publickey)` on SSH | Wrong key path — `ssh -i ~/.ssh/<your-key>` ubuntu@... |
| Forecast endpoint returns empty | Run the backfill block in §5 once. |
| Schedule jobs don't fire | Container time zone — bake `TZ=Europe/Berlin` into docker-compose env if needed. |
