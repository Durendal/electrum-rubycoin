#!/bin/bash

# You probably need to update only this link
ELECTRUM_GIT_URL=git://github.com/Durendal/electrum-rubycoin.git
BRANCH=master
NAME_ROOT=electrum-rubycoin


# These settings probably don't need any change
export WINEPREFIX=/opt/wine64

PYHOME=c:/python27
PYTHON="wine $PYHOME/python.exe -OO -B"


# Let's begin!
cd `dirname $0`
set -e

cd tmp

if [ -d "electrum-rubycoin-git" ]; then
    # GIT repository found, update it
    echo "Pull"
    cd electrum-rubycoin-git
    git checkout $BRANCH
    git pull
    cd ..
else
    # GIT repository not found, clone it
    echo "Clone"
    git clone -b $BRANCH $ELECTRUM_GIT_URL electrum-rubycoin-git
fi

cd electrum-rubycoin-git
VERSION=`git describe --tags`
echo "Last commit: $VERSION"

cd ..

rm -rf $WINEPREFIX/drive_c/electrum-rubycoin
cp -r electrum-rubycoin-git $WINEPREFIX/drive_c/electrum-rubycoin
cp electrum-rubycoin-git/LICENCE .

# add python packages (built with make_packages)
cp -r ../../../packages $WINEPREFIX/drive_c/electrum-rubycoin/

# add locale dir
cp -r ../../../lib/locale $WINEPREFIX/drive_c/electrum-rubycoin/lib/

# Build Qt resources
wine $WINEPREFIX/drive_c/Python27/Lib/site-packages/PyQt4/pyrcc4.exe C:/electrum-rubycoin/icons.qrc -o C:/electrum-rubycoin/lib/icons_rc.py
wine $WINEPREFIX/drive_c/Python27/Lib/site-packages/PyQt4/pyrcc4.exe C:/electrum-rubycoin/icons.qrc -o C:/electrum-rubycoin/gui/qt/icons_rc.py

cd ..

rm -rf dist/

# build standalone version
$PYTHON "C:/pyinstaller/pyinstaller.py" --noconfirm --ascii -w deterministic.spec

# build NSIS installer
# $VERSION could be passed to the electrum.nsi script, but this would require some rewriting in the script iself.
wine "$WINEPREFIX/drive_c/Program Files (x86)/NSIS/makensis.exe" /DPRODUCT_VERSION=$VERSION electrum.nsi

cd dist
mv electrum-rubycoin.exe $NAME_ROOT-$VERSION.exe
mv electrum-rubycoin-setup.exe $NAME_ROOT-$VERSION-setup.exe
mv electrum-rubycoin $NAME_ROOT-$VERSION
zip -r $NAME_ROOT-$VERSION.zip $NAME_ROOT-$VERSION
cd ..

# build portable version
cp portable.patch $WINEPREFIX/drive_c/electrum-rubycoin
pushd $WINEPREFIX/drive_c/electrum-rubycoin
patch < portable.patch
popd
$PYTHON "C:/pyinstaller/pyinstaller.py" --noconfirm --ascii -w deterministic.spec
cd dist
mv electrum-rubycoin.exe $NAME_ROOT-$VERSION-portable.exe
cd ..

echo "Done."
