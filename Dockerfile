# syntax=docker/dockerfile:1

ARG CYHY_COMMANDER_VERSION=0.0.3-rc2
ARG PYTHON_IMAGE_VERSION=2.7.18
ARG VERSION

FROM --platform=$BUILDPLATFORM tonistiigi/xx AS xx

FROM --platform=$BUILDPLATFORM python:${PYTHON_IMAGE_VERSION} as build-stage

ARG CYHY_COMMANDER_VERSION
ENV PATH="/opt/venv/bin:$PATH"

COPY --from=xx / /
RUN apt-get update && apt-get install -y clang lld
ARG TARGETPLATFORM
RUN xx-apt install -y libc6-dev

WORKDIR /root
RUN \
  --mount=type=cache,mode=0777,target=/var/cache/apt \
  --mount=type=cache,mode=0777,target=/root/.cache/pip <<EOF
apt-get update
python -m pip install --upgrade pip
pip install --upgrade virtualenv
virtualenv /opt/venv
EOF

RUN --mount=type=cache,mode=0777,target=/root/.cache/pip \
  pip install https://github.com/cisagov/cyhy-commander/archive/v${CYHY_COMMANDER_VERSION}.zip


FROM python:${PYTHON_IMAGE_VERSION}-slim as final-stage

ARG CYHY_UID=421
ARG VERSION

LABEL org.opencontainers.image.authors="mark.feldhousen@cisa.dhs.gov"
LABEL org.opencontainers.image.vendor="Cybersecurity and Infrastructure Security Agency"

ENV CYHY_HOME="/home/cyhy"
ENV CYHY_COMMANDER_VERSION=${CYHY_COMMANDER_VERSION}
ENV PATH="/opt/venv/bin:$PATH"

RUN <<EOF
groupadd --gid ${CYHY_UID} cyhy
useradd --uid ${CYHY_UID} \
  --gid cyhy \
  --shell /bin/bash \
  --create-home cyhy
mkdir -p /etc/cyhy/
ln -snf /data/commander.conf /etc/cyhy/commander.conf
echo ${VERSION} > image_version.txt
EOF

WORKDIR ${CYHY_HOME}
COPY \
  src/check_health.sh \
  src/entrypoint.sh \
  src/launcher.sh \
  ./
COPY --from=build-stage /opt/venv /opt/venv

VOLUME ["/data"]

ENTRYPOINT ["./entrypoint.sh"]
CMD ["/data"]
HEALTHCHECK --start-period=3m --interval=30s --timeout=5s CMD ./check_health.sh
