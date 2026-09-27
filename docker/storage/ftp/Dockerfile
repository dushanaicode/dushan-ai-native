FROM public.ecr.aws/docker/library/debian@sha256:6ebd97fa83deb272194a2cf015b3d26a4d538e9ad3a7a79d544c8af5b0a01443
WORKDIR /build
ENV TMPDIR=/build/Temp TMP=/build/Temp TEMP=/build/Temp
RUN mkdir -p /build/Temp /var/run/vsftpd/empty /home/vsftpd \
    && apt-get update \
    && apt-get install -y --no-install-recommends dumb-init vsftpd
COPY vsftpd.conf /etc/vsftpd.conf
COPY --chmod=755 entrypoint.sh /usr/local/bin/entrypoint.sh
EXPOSE 21 12100-12110
ENTRYPOINT ["/usr/bin/dumb-init", "--", "/usr/local/bin/entrypoint.sh"]
