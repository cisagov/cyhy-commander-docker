ARG CYHY_COMMANDER_VERSION=0.0.3-rc2
ARG PYTHON_IMAGE_VERSION=2.7.18
ARG VERSION

FROM python:${PYTHON_IMAGE_VERSION} as build-stage

ARG CYHY_COMMANDER_VERSION
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /root
RUN apt-get update
RUN python -m pip install --upgrade pip
RUN pip install --upgrade virtualenv
RUN virtualenv /opt/venv
RUN pip install git+https://github.com/cisagov/cyhy-commander@v${CYHY_COMMANDER_VERSION}

FROM python:${PYTHON_IMAGE_VERSION}-slim as final-stage

ARG CYHY_UID=421
ARG VERSION

LABEL org.opencontainers.image.authors="mark.feldhousen@cisa.dhs.gov"
LABEL org.opencontainers.image.vendor="Cybersecurity and Infrastructure Security Agency"

ENV CYHY_HOME="/home/cyhy"
ENV CYHY_COMMANDER_VERSION=${CYHY_COMMANDER_VERSION}
ENV PATH="/opt/venv/bin:$PATH"

COPY --from=build-stage /opt/venv /opt/venv

RUN groupadd --gid ${CYHY_UID} cyhy && \
  useradd --uid ${CYHY_UID} \
  --gid cyhy \
  --shell /bin/bash \
  --create-home cyhy && \
  mkdir -p /etc/cyhy/ && \
  ln -snf /data/commander.conf /etc/cyhy/commander.conf && \
  echo ${VERSION} > image_version.txt

WORKDIR ${CYHY_HOME}
COPY \
  src/check_health.sh \
  src/entrypoint.sh \
  src/launcher.sh \
  ./

VOLUME ["/data"]

ENTRYPOINT ["./entrypoint.sh"]
CMD ["/data"]
HEALTHCHECK --start-period=3m --interval=30s --timeout=5s CMD ./check_health.sh
