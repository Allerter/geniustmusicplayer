# Dockerfile with:
#   - Android build environment
#   - python-for-android dependencies
#
# Build with:
#     docker build --tag=p4a --file Dockerfile .
#
# Run with:
#     docker run -it --rm p4a /bin/sh -c '. venv/bin/activate && p4a apk --help'
#
# Or for interactive shell:
#     docker run -it --rm p4a
#
# Note:
#     Use 'docker run' without '--rm' flag for keeping the container and use
#     'docker commit <container hash> <new image>' to extend the original image

FROM ubuntu:20.04

# configure locale
RUN apt -y update -qq > /dev/null \
    && DEBIAN_FRONTEND=noninteractive apt install -qq --yes --no-install-recommends \
    locales && \
    locale-gen en_US.UTF-8
ENV LANG="en_US.UTF-8" \
    LANGUAGE="en_US.UTF-8" \
    LC_ALL="en_US.UTF-8"

RUN apt -y update -qq > /dev/null \
    && DEBIAN_FRONTEND=noninteractive apt install -qq --yes --no-install-recommends \
    ca-certificates \
    curl \
    && apt -y autoremove \
    && apt -y clean \
    && rm -rf /var/lib/apt/lists/*

# retry helper script, refs:
# https://github.com/kivy/python-for-android/issues/1306
ENV RETRY="retry -t 3 --"
RUN curl https://raw.githubusercontent.com/kadwanev/retry/1.0.1/retry \
    --output /usr/local/bin/retry && chmod +x /usr/local/bin/retry

ENV USER="user"
ENV HOME_DIR="/home/${USER}"
ENV WORK_DIR="${HOME_DIR}/app" \
    PATH="${HOME_DIR}/.local/bin:${PATH}" \
    ANDROID_HOME="${HOME_DIR}/.android" \
    JAVA_HOME="/usr/lib/jvm/java-13-openjdk-amd64"
ENV ANDROID_API_LEVEL="30" \
    ANDROID_SDK_BUILD_TOOLS_VERSION="30.0.0"

# install system dependencies
RUN dpkg --add-architecture i386 \
    && ${RETRY} apt -y update -qq > /dev/null \
    && ${RETRY} DEBIAN_FRONTEND=noninteractive apt install -qq --yes --no-install-recommends \
    autoconf \
    automake \
    autopoint \
    build-essential \
    ccache \
    cmake \
    gettext \
    git \
    lbzip2 \
    libffi-dev \
    libgtk2.0-0:i386 \
    libidn11:i386 \
    libltdl-dev \
    libncurses5:i386 \
    libssl-dev \
    libstdc++6:i386 \
    libtool \
    openjdk-13-jdk \
    patch \
    pkg-config \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    sudo \
    unzip \
    wget \
    zip \
    zlib1g-dev \
    zlib1g:i386 \
    && apt -y autoremove \
    && apt -y clean \
    && rm -rf /var/lib/apt/lists/*

# prepare non root env
RUN useradd --create-home --shell /bin/bash ${USER}

# with sudo access and no password
RUN usermod -append --groups sudo ${USER}
RUN echo "%sudo ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

WORKDIR ${WORK_DIR}
RUN git clone https://github.com/allerter/python-for-android
RUN mkdir ${ANDROID_HOME} && chown --recursive ${USER} ${HOME_DIR} ${ANDROID_HOME}
USER ${USER}

# clone allerter python-for-android fork
WORKDIR ${WORK_DIR}/python-for-android
RUN test -f ci/makefiles/android.mk && echo "android.mk exists"    
COPY ci/makefiles/android.mk /tmp/android.mk \
     && make --file /tmp/android.mk \
     && sudo rm /tmp/android.mk

# install python-for-android from current branch
COPY --chown=user:user Makefile README.md setup.py pythonforandroid/__init__.py ${WORK_DIR}/
RUN mkdir pythonforandroid \
    && mv __init__.py pythonforandroid/ \
    && make virtualenv \
    && rm -rf ~/.cache/

# run build
WORKDIR ${WORK_DIR}
RUN ls
RUN p4a apk \
    --enable-androidx \
    --sdk_dir ${ANDROID_SDK_HOME} \
    --ndk_dir ${ANDROID_NDK_HOME} \
    --android_api ${ANDROID_API_LEVEL} \
    --bootstrap sdl2 \
    --dist_name geniustmusicplayer \
    --name="GeniusT Music Player" \
    --version 0.8 \
    --package org.allerter.geniustmusicplayer \
    --requirements python3,kivy==2.0.0,https://github.com/kivymd/KivyMD/archive/c792038.zip,android,sdl2_ttf==2.0.15,requests,urllib3,idna,chardet,oscpy,pillow \
    --orientation portrait \
    --window \
    --private ${WORK_DIR}/geniustmusicplayer \
    --permission INTERNET \
    --permission ACCESS_NETWORK_STATE \
    --permission FOREGROUND_SERVICE \
    --service gtplayer:${WORK_DIR}/geniustmusicplayer/service.py \
    --depend "com.android.support:support-compat:28.0.0" \
    --depend "androidx.legacy:legacy-support-v4:1.0.0" \
    --depend "com.google.code.gson:gson:2.8.5" \
    --presplash-lottie ${WORK_DIR}/geniustmusicplayer/images/presplash.json \
    --presplash-color white \
    --icon ${WORK_DIR}/geniustmusicplayer/images/icon.png \
    --add-aar ${WORK_DIR}/geniustmusicplayer/spotify-auth-release-1.2.3.aar \
    --add-aar ${WORK_DIR}/geniustmusicplayer/genius-auth-release-1.2.4.aar \
    --intent-filters ${WORK_DIR}/geniustmusicplayer/intent_filters.xml
