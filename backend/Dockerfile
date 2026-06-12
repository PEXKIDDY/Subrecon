# ---------------------------------------------------------------------------
# SUBRECO backend image.
# Build arg INSTALL_TOOLS=true compiles the Go recon toolchain into the image.
# Set it to false for a fast "passive-only" image (crt.sh/OTX/RapidDNS still work).
# ---------------------------------------------------------------------------
FROM golang:1.23-bookworm AS tools
ARG INSTALL_TOOLS=true
ENV GOBIN=/tools
RUN mkdir -p /tools
RUN if [ "$INSTALL_TOOLS" = "true" ]; then \
      go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest && \
      go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest && \
      go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest && \
      go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest && \
      go install -v github.com/projectdiscovery/katana/cmd/katana@latest && \
      go install -v github.com/projectdiscovery/chaos-client/cmd/chaos@latest && \
      go install -v github.com/tomnomnom/assetfinder@latest && \
      go install -v github.com/tomnomnom/waybackurls@latest && \
      go install -v github.com/lc/gau/v2/cmd/gau@latest && \
      go install -v github.com/sensepost/gowitness@latest ; \
    else echo "Skipping tool build (passive-only image)"; fi

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    dnsutils libpcap0.8 ca-certificates curl chromium \
    && rm -rf /var/lib/apt/lists/*

# Recon binaries (no-op copy is fine if INSTALL_TOOLS=false produced an empty dir)
COPY --from=tools /tools/ /usr/local/bin/

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x entrypoint.sh && mkdir -p /data/screenshots

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
