FROM python:3.9-slim

ENV PATH="${PATH}:/home/jenkins/packer/"

RUN \
    pip install --upgrade awscli>=1.16.38 && \
    pip install --upgrade pipenv==2022.3.28 pip==21.1.1

RUN echo "jenkins ALL=(ALL) NOPASSWD: ALL" > /tmp/jenkins_sudoer && \
    chown root:root /tmp/jenkins_sudoer && \
    chmod 0440 /tmp/jenkins_sudoer && \
    mkdir /etc/sudoers.d && \
    mv /tmp/jenkins_sudoer /etc/sudoers.d/ && \
    cat /etc/sudoers.d/jenkins_sudoer


RUN groupadd -g 1006 jenkins && adduser -u 1004 -gid 1006 --disabled-password --gecos "" jenkins && echo jenkins:jenkins | chpasswd -c SHA512

USER jenkins
CMD /bin/bash
