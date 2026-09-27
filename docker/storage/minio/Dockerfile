FROM golang:1.24.7-bookworm@sha256:b8bae5bd9ba9b1f89b635c91c24cc75cea335a16fb5076310f38566fc674b1ec AS builder
WORKDIR /app
ENV TMPDIR=/app/Temp TMP=/app/Temp TEMP=/app/Temp \
    GOMODCACHE=/app/Temp/modules GOCACHE=/app/Temp/build GOTOOLCHAIN=local
RUN mkdir -p /app/Temp /app/src /app/out
ADD --checksum=sha256:c9598dcce3440977e79f787f2ba0e7e4d92c8d556bd51e7cef3785bafd6635f3 https://codeload.github.com/minio/minio/tar.gz/refs/tags/RELEASE.2025-09-07T16-13-09Z /app/Temp/source.tar.gz
RUN tar -xzf /app/Temp/source.tar.gz --strip-components=1 -C /app/src
WORKDIR /app/src
RUN CGO_ENABLED=0 go build -trimpath -ldflags '-s -w' -o /app/out/minio .

FROM public.ecr.aws/docker/library/debian@sha256:6ebd97fa83deb272194a2cf015b3d26a4d538e9ad3a7a79d544c8af5b0a01443
WORKDIR /app
ENV TMPDIR=/app/Temp TMP=/app/Temp TEMP=/app/Temp
RUN mkdir -p /app/Temp /data \
    && apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && chown -R 10001:10001 /app/Temp /data
COPY --from=builder /app/out/minio /usr/local/bin/minio
COPY --from=builder /app/src/LICENSE /usr/share/doc/minio/LICENSE
USER 10001:10001
EXPOSE 9000 9001
ENTRYPOINT ["/usr/local/bin/minio"]
