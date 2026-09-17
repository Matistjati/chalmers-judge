set -v

sudo apt install python3 dh-virtualenv build-essential debhelper devscripts equivs libffi-dev \
    automake g++ make python3 python3-pytest python3-setuptools python3-yaml python3-plastex \
    ghostscript python3-minimal python-pkg-resources python3-plastex python3-yaml texlive-fonts-recommended texlive-lang-cyrillic texlive-latex-extra texlive-plain-generic tidy
curl -sSL https://install.python-poetry.org | python3 -
